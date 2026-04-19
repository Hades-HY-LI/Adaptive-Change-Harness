from __future__ import annotations

from pathlib import Path
import shlex
import traceback

from app.core.config import Settings
from app.evaluators.engine import EvaluatorEngine
from app.models.schemas import (
    EvidencePacket,
    EvaluatorResult,
    FailureCase,
    ReplayComparison,
    RepoProfile,
    RunCreateRequest,
    RunMode,
    RunStatus,
    SkillDecision,
    Verdict,
)
from app.providers.registry import ProviderRegistry
from app.services.break_engine import BreakEngine
from app.services.discovery_engine import DiscoveryEngine
from app.services.patcher import PatchService
from app.services.prompts import build_failure_case_repair_prompt, build_repair_prompt
from app.services.shell import ShellRunner
from app.services.skill_library import SkillLibraryService
from app.services.workspace import WorkspaceService
from app.storage.repository import RunRepository


class HarnessOrchestrator:
    def __init__(self, settings: Settings, repository: RunRepository) -> None:
        self.settings = settings
        self.repository = repository
        self.shell_runner = ShellRunner(settings.request_timeout_seconds)
        self.break_engine = BreakEngine()
        self.workspace_service = WorkspaceService(settings.artifact_root, settings.demo_repo_root)
        self.discovery_engine = DiscoveryEngine(self.shell_runner, repository)
        self.evaluator_engine = EvaluatorEngine(self.shell_runner)
        self.patch_service = PatchService()
        self.skill_library = SkillLibraryService(settings.skill_assets_root, repository)
        self.providers = ProviderRegistry(settings)

    def execute(self, run_id: str, payload: RunCreateRequest) -> None:
        try:
            self.repository.update_run(run_id, status=RunStatus.running)
            if payload.mode is RunMode.discover:
                self._execute_discover(run_id, payload)
                return
            if payload.mode is RunMode.replay:
                self._execute_replay(run_id, payload)
                return
            self._execute_inject(run_id, payload)
        except Exception as exc:
            self.repository.add_event(
                run_id,
                event_type="run_failed",
                stage="error",
                summary="The run failed before completion.",
                metadata={"error": str(exc), "traceback": traceback.format_exc()},
            )
            self.repository.update_run(run_id, status=RunStatus.failed, verdict=Verdict.needs_review, error=str(exc))

    def _execute_discover(self, run_id: str, payload: RunCreateRequest) -> None:
        if not payload.codebase_id:
            raise ValueError("discover mode requires codebase_id")
        codebase = self.repository.get_codebase(payload.codebase_id)
        workspace = self.workspace_service.create_from_codebase(run_id, Path(codebase.extracted_path))
        self.repository.update_run(run_id, workspace_path=str(workspace))
        self.repository.add_event(
            run_id,
            event_type="run_created",
            stage="setup",
            summary="Created isolated workspace for codebase discovery.",
            metadata={"workspace_path": str(workspace), "codebase_id": codebase.id},
        )
        self.repository.add_event(
            run_id,
            event_type="codebase_profiled",
            stage="profile",
            summary=f"Detected {codebase.repo_profile.language} / {codebase.repo_profile.framework} repository profile.",
            metadata=codebase.repo_profile.model_dump(mode="json"),
        )
        self.repository.add_event(
            run_id,
            event_type="discovery_started",
            stage="discover",
            summary="Running deterministic baseline discovery before adaptive probing is added.",
            metadata={"test_command": codebase.repo_profile.test_command},
        )
        outcome = self.discovery_engine.run(workspace, codebase.repo_profile)
        self.repository.add_event(
            run_id,
            event_type="evaluation_failed" if outcome.failure_case else "evaluation_passed",
            stage="discover",
            summary=outcome.baseline_result.summary,
            metadata={"result": outcome.baseline_result.model_dump(mode="json")},
        )
        for probe_result in outcome.probe_results:
            self.repository.add_event(
                run_id,
                event_type="probe_executed",
                stage="discover",
                summary=probe_result.summary,
                metadata={
                    "probe_id": probe_result.probe_id,
                    "title": probe_result.title,
                    "passed": probe_result.passed,
                    "severity": probe_result.severity,
                    "confidence": probe_result.confidence,
                    "command": probe_result.failing_command,
                    "details_excerpt": self._excerpt(probe_result.details),
                    "details": probe_result.details,
                },
            )
        if outcome.failure_case is None:
            evidence = EvidencePacket(
                passed_evaluators_after=[outcome.baseline_result],
                root_cause_summary="No reproducible failure was found after baseline validation and deterministic probe execution.",
                patch_summary="No patch was applied.",
                merge_confidence=Verdict.no_reproducible_failure_found.value,
                repo_profile_summary=f"{codebase.repo_profile.language} / {codebase.repo_profile.framework}",
                artifact_manifest={"workspace_path": str(workspace), "codebase_id": codebase.id},
            )
            self.repository.add_event(
                run_id,
                event_type="verdict_ready",
                stage="complete",
                summary="No reproducible failure was found in this slice.",
            )
            self.repository.update_run(
                run_id,
                status=RunStatus.completed,
                verdict=Verdict.no_reproducible_failure_found,
                evidence=evidence,
            )
            return

        self.repository.add_event(
            run_id,
            event_type="failure_case_captured",
            stage="discover",
            summary=outcome.failure_case.title,
            metadata=outcome.failure_case.model_dump(mode="json"),
        )
        failing_signal = next(
            (
                EvaluatorResult(
                    name=probe_result.probe_id,
                    passed=False,
                    summary=probe_result.summary,
                    details=probe_result.details,
                )
                for probe_result in outcome.probe_results
                if probe_result.title == outcome.failure_case.title
            ),
            outcome.baseline_result,
        )
        evidence = EvidencePacket(
            failed_evaluators_before=[failing_signal],
            root_cause_summary="A reproducible failure was captured from deterministic discovery probes against the uploaded codebase.",
            patch_summary="Repair is not yet enabled for discover mode in this implementation slice.",
            merge_confidence=Verdict.unsafe.value,
            repo_profile_summary=f"{codebase.repo_profile.language} / {codebase.repo_profile.framework}",
            failure_case_summary=outcome.failure_case.title,
            artifact_manifest={
                "workspace_path": str(workspace),
                "codebase_id": codebase.id,
                "failure_case_id": outcome.failure_case.id,
            },
        )
        self.repository.add_event(
            run_id,
            event_type="verdict_ready",
            stage="complete",
            summary="Captured a reproducible failure case from baseline discovery.",
        )
        self.repository.update_run(
            run_id,
            status=RunStatus.completed,
            verdict=Verdict.unsafe,
            evidence=evidence,
        )

    def _execute_replay(self, run_id: str, payload: RunCreateRequest) -> None:
        if not payload.failure_case_id:
            raise ValueError("replay mode requires failure_case_id")
        self._execute_failure_case_repair(run_id, payload)

    def _execute_failure_case_repair(self, run_id: str, payload: RunCreateRequest) -> None:
        failure_case = self.repository.get_failure_case(payload.failure_case_id)
        codebase = self.repository.get_codebase(failure_case.codebase_id)
        workspace = self.workspace_service.create_from_codebase(run_id, Path(codebase.extracted_path))
        self.repository.update_run(run_id, workspace_path=str(workspace))
        self.repository.add_event(
            run_id,
            event_type="run_created",
            stage="setup",
            summary="Created isolated workspace for saved failure-case repair.",
            metadata={"workspace_path": str(workspace), "failure_case_id": failure_case.id},
        )
        self._restore_failure_case_artifacts(workspace, failure_case)
        repro_before = self._run_command_evaluator(
            name="saved_repro",
            command=failure_case.failing_command,
            cwd=workspace,
            success_summary="Saved failure case no longer reproduces.",
            failure_summary="Saved failure case reproduced successfully.",
        )
        self.repository.add_event(
            run_id,
            event_type="evaluation_passed" if repro_before.passed else "evaluation_failed",
            stage="replay",
            summary=repro_before.summary,
            metadata={"result": repro_before.model_dump(mode="json"), "failure_case_id": failure_case.id},
        )
        if repro_before.passed:
            evidence = EvidencePacket(
                passed_evaluators_after=[repro_before],
                root_cause_summary="The stored failure case did not reproduce, so the repair loop did not run.",
                patch_summary="No patch was applied because the saved repro no longer failed.",
                merge_confidence=Verdict.no_reproducible_failure_found.value,
                repo_profile_summary=f"{codebase.repo_profile.language} / {codebase.repo_profile.framework}",
                failure_case_summary=failure_case.title,
                artifact_manifest={"workspace_path": str(workspace), "failure_case_id": failure_case.id},
                replay_comparison=self._build_replay_comparison(
                    failure_case=failure_case,
                    before_result=repro_before,
                    after_result=repro_before,
                    validation_commands=[failure_case.failing_command],
                ),
            )
            self.repository.add_event(
                run_id,
                event_type="verdict_ready",
                stage="complete",
                summary="Saved failure case no longer reproduces.",
            )
            self.repository.update_run(
                run_id,
                status=RunStatus.completed,
                verdict=Verdict.no_reproducible_failure_found,
                evidence=evidence,
            )
            return

        self.repository.update_run(run_id, status=RunStatus.repairing)
        skill_match = self.skill_library.match_failure_case(failure_case)
        skill_decision = SkillDecision(action="none", rationale="No existing skill matched this failure case.")
        if skill_match is not None:
            skill_decision = SkillDecision(
                matched_skill_id=skill_match.skill.id,
                matched_skill_title=skill_match.skill.title,
                action="matched",
                rationale=skill_match.rationale,
            )
            self.repository.update_run(run_id, skill_match_id=skill_match.skill.id)
            self.repository.add_event(
                run_id,
                event_type="skill_matched",
                stage="repair",
                summary=f"Matched repair skill: {skill_match.skill.title}.",
                metadata={
                    "skill_id": skill_match.skill.id,
                    "score": skill_match.score,
                    "rationale": skill_match.rationale,
                },
            )

        provider = self.providers.require(payload.provider)
        repair_prompt = build_failure_case_repair_prompt(
            workspace,
            failure_case,
            codebase.repo_profile,
            repro_before,
            matched_skill=skill_match.skill if skill_match else None,
        )
        proposal = provider.generate_repair(model=payload.model or self.settings.openai_model, prompt=repair_prompt)
        self.repository.add_event(
            run_id,
            event_type="diagnosis_ready",
            stage="diagnose",
            summary=proposal.root_cause_summary,
            metadata={
                "patch_summary": proposal.patch_summary,
                "merge_confidence": proposal.merge_confidence,
                "skill_decision": skill_decision.model_dump(mode="json"),
            },
        )

        changed_files = self.patch_service.apply(workspace, proposal)
        self.repository.add_event(
            run_id,
            event_type="patch_applied",
            stage="repair",
            summary=f"Applied {len(changed_files)} patch operation(s) for the saved failure case.",
            metadata={"changed_files": changed_files},
        )

        validation_results = self._validate_failure_case_repair(workspace, failure_case, codebase.repo_profile)
        failing_after = [result for result in validation_results if not result.passed]
        verdict = Verdict.safe if not failing_after else Verdict.unsafe

        if verdict is Verdict.safe:
            skill_decision = self.skill_library.record_validated_repair(
                failure_case=failure_case,
                repo_profile=codebase.repo_profile,
                proposal=proposal,
                matched_skill=skill_match.skill if skill_match else None,
            )
            self.repository.update_run(run_id, skill_match_id=skill_decision.matched_skill_id)
            event_type = {
                "created": "skill_created",
                "updated": "skill_updated",
                "reused": "skill_reused",
            }.get(skill_decision.action, "skill_updated")
            self.repository.add_event(
                run_id,
                event_type=event_type,
                stage="learn",
                summary=skill_decision.rationale,
                metadata=skill_decision.model_dump(mode="json"),
            )

        evidence = EvidencePacket(
            failed_evaluators_before=[repro_before],
            passed_evaluators_after=[result for result in validation_results if result.passed],
            root_cause_summary=proposal.root_cause_summary,
            patch_summary=proposal.patch_summary,
            merge_confidence=proposal.merge_confidence if verdict is Verdict.safe else Verdict.unsafe.value,
            repo_profile_summary=f"{codebase.repo_profile.language} / {codebase.repo_profile.framework}",
            failure_case_summary=failure_case.title,
            artifact_manifest={
                "workspace_path": str(workspace),
                "failure_case_id": failure_case.id,
                "codebase_id": codebase.id,
            },
            skill_decision=skill_decision,
            replay_comparison=self._build_replay_comparison(
                failure_case=failure_case,
                before_result=repro_before,
                after_result=validation_results[0],
                validation_commands=self._validation_commands(failure_case, codebase.repo_profile),
            ),
        )
        self.repository.add_event(
            run_id,
            event_type="verdict_ready",
            stage="validate",
            summary="Saved repro and baseline checks passed after repair."
            if verdict is Verdict.safe
            else "The repair still failed deterministic validation.",
            metadata={"results": [result.model_dump(mode="json") for result in validation_results]},
        )
        self.repository.update_run(run_id, status=RunStatus.completed, verdict=verdict, evidence=evidence)

    def _execute_inject(self, run_id: str, payload: RunCreateRequest) -> None:
        if payload.break_type is None:
            raise ValueError("inject mode requires break_type")

        self.repository.update_run(run_id, status=RunStatus.running)
        workspace = self.workspace_service.create_from_demo(run_id)
        self.repository.update_run(run_id, workspace_path=str(workspace))
        self.repository.add_event(
            run_id,
            event_type="run_created",
            stage="setup",
            summary="Created isolated workspace for this run.",
            metadata={"workspace_path": str(workspace)},
        )

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
            merge_confidence=proposal.merge_confidence if verdict is Verdict.safe else Verdict.unsafe.value,
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

    def _validate_failure_case_repair(
        self,
        workspace: Path,
        failure_case: FailureCase,
        repo_profile: RepoProfile,
    ) -> list[EvaluatorResult]:
        results = [
            self._run_command_evaluator(
                name="saved_repro",
                command=failure_case.failing_command,
                cwd=workspace,
                success_summary="Saved repro no longer fails after repair.",
                failure_summary="Saved repro still fails after repair.",
            )
        ]
        if repo_profile.test_command and repo_profile.test_command != failure_case.failing_command:
            results.append(
                self._run_command_evaluator(
                    name="baseline_tests",
                    command=repo_profile.test_command,
                    cwd=workspace,
                    success_summary="Baseline tests passed after repair.",
                    failure_summary="Baseline tests failed after repair.",
                )
            )
        return results

    def _run_command_evaluator(
        self,
        *,
        name: str,
        command: str,
        cwd: Path,
        success_summary: str,
        failure_summary: str,
    ) -> EvaluatorResult:
        result = self.shell_runner.run(shlex.split(command), cwd=cwd)
        details = (result.stdout + "\n" + result.stderr).strip()
        return EvaluatorResult(
            name=name,
            passed=result.exit_code == 0,
            summary=success_summary if result.exit_code == 0 else failure_summary,
            details=details,
        )

    def _restore_failure_case_artifacts(self, workspace: Path, failure_case: FailureCase) -> None:
        script_path = failure_case.probe_input.get("script_path")
        script_contents = failure_case.probe_input.get("script_contents")
        if not script_path or not script_contents:
            return
        target = (workspace / script_path).resolve()
        if workspace.resolve() not in target.parents and target != workspace.resolve():
            raise ValueError(f"Failure case artifact escapes workspace: {script_path}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(script_contents)

    def _build_replay_comparison(
        self,
        *,
        failure_case: FailureCase,
        before_result: EvaluatorResult,
        after_result: EvaluatorResult,
        validation_commands: list[str],
    ) -> ReplayComparison:
        return ReplayComparison(
            failure_case_id=failure_case.id,
            original_failing_command=failure_case.failing_command,
            original_failure_type=failure_case.failure_type,
            original_failure_excerpt=self._excerpt(failure_case.failing_output),
            reproduced_before_repair=not before_result.passed,
            reproduced_after_repair=not after_result.passed,
            latest_repro_excerpt=self._excerpt(after_result.details),
            validation_commands=validation_commands,
        )

    def _excerpt(self, details: str, limit: int = 240) -> str:
        compact = " ".join(details.split())
        if len(compact) <= limit:
            return compact
        return compact[: limit - 3] + "..."

    def _validation_commands(self, failure_case: FailureCase, repo_profile: RepoProfile) -> list[str]:
        commands = [failure_case.failing_command]
        if repo_profile.test_command and repo_profile.test_command != failure_case.failing_command:
            commands.append(repo_profile.test_command)
        return commands
