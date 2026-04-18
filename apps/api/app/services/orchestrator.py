from __future__ import annotations

from pathlib import Path
import traceback

from app.core.config import Settings
from app.evaluators.engine import EvaluatorEngine
from app.models.schemas import EvidencePacket, RunCreateRequest, RunStatus, Verdict
from app.providers.registry import ProviderRegistry
from app.services.break_engine import BreakEngine
from app.services.patcher import PatchService
from app.services.prompts import build_repair_prompt
from app.services.shell import ShellRunner
from app.services.workspace import WorkspaceService
from app.storage.repository import RunRepository


class HarnessOrchestrator:
    def __init__(self, settings: Settings, repository: RunRepository) -> None:
        self.settings = settings
        self.repository = repository
        self.break_engine = BreakEngine()
        self.workspace_service = WorkspaceService(settings.artifact_root, settings.demo_repo_root)
        self.evaluator_engine = EvaluatorEngine(ShellRunner(settings.request_timeout_seconds))
        self.patch_service = PatchService()
        self.providers = ProviderRegistry(settings)

    def execute(self, run_id: str, payload: RunCreateRequest) -> None:
        try:
            self.repository.update_run(run_id, status=RunStatus.running)
            workspace = self.workspace_service.create(run_id)
            self.repository.update_run(run_id, workspace_path=str(workspace))
            self.repository.add_event(
                run_id,
                event_type="run_created",
                stage="setup",
                summary="Created isolated workspace for this run.",
                metadata={"workspace_path": str(workspace)},
            )

            if payload.mode.value == "inject":
                mutation = self.break_engine.apply(workspace, payload.break_type)
                self.repository.add_event(
                    run_id,
                    event_type="break_applied",
                    stage="break",
                    summary=mutation.summary,
                    metadata={"file_path": mutation.file_path, "details": mutation.details},
                )

            initial_results = self.evaluator_engine.evaluate(workspace)
            failing_before = [result for result in initial_results if not result.passed]
            self.repository.add_event(
                run_id,
                event_type="evaluation_failed" if failing_before else "evaluation_passed",
                stage="evaluate",
                summary=(
                    f"{len(failing_before)} evaluators failed before repair."
                    if failing_before
                    else "All evaluators passed before repair."
                ),
                metadata={"results": [result.model_dump() for result in initial_results]},
            )

            if not failing_before:
                evidence = EvidencePacket(
                    failed_evaluators_before=[],
                    passed_evaluators_after=initial_results,
                    root_cause_summary="No failure detected.",
                    patch_summary="No patch was needed.",
                    merge_confidence="safe",
                )
                self.repository.update_run(run_id, status=RunStatus.completed, verdict=Verdict.safe, evidence=evidence)
                return

            self.repository.update_run(run_id, status=RunStatus.repairing)
            provider = self.providers.require(payload.provider)
            repair_prompt = build_repair_prompt(workspace, payload.break_type, initial_results)
            proposal = provider.generate_repair(model=payload.model or self.settings.openai_model, prompt=repair_prompt)
            self.repository.add_event(
                run_id,
                event_type="diagnosis_ready",
                stage="diagnose",
                summary=proposal.root_cause_summary,
                metadata={"patch_summary": proposal.patch_summary, "merge_confidence": proposal.merge_confidence},
            )

            changed_files = self.patch_service.apply(workspace, proposal)
            self.repository.add_event(
                run_id,
                event_type="patch_applied",
                stage="repair",
                summary=f"Applied {len(changed_files)} patch operation(s).",
                metadata={"changed_files": changed_files},
            )

            final_results = self.evaluator_engine.evaluate(workspace)
            failing_after = [result for result in final_results if not result.passed]
            verdict = Verdict.safe if not failing_after else Verdict.unsafe
            evidence = EvidencePacket(
                failed_evaluators_before=failing_before,
                passed_evaluators_after=[result for result in final_results if result.passed],
                root_cause_summary=proposal.root_cause_summary,
                patch_summary=proposal.patch_summary,
                merge_confidence=proposal.merge_confidence if verdict is Verdict.safe else "unsafe",
                artifact_manifest={"workspace_path": str(workspace)},
            )
            self.repository.add_event(
                run_id,
                event_type="verdict_ready",
                stage="validate",
                summary="All evaluators passed after repair." if verdict is Verdict.safe else "The repair still failed one or more evaluators.",
                metadata={"results": [result.model_dump() for result in final_results]},
            )
            self.repository.update_run(run_id, status=RunStatus.completed, verdict=verdict, evidence=evidence)
        except Exception as exc:
            self.repository.add_event(
                run_id,
                event_type="run_failed",
                stage="error",
                summary="The run failed before completion.",
                metadata={"error": str(exc), "traceback": traceback.format_exc()},
            )
            self.repository.update_run(run_id, status=RunStatus.failed, verdict=Verdict.needs_review, error=str(exc))
