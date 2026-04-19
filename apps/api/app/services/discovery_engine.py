from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import shlex

from app.models.schemas import EvaluatorResult, FailureCase, RepoProfile
from app.services.probe_runner import ProbeResult, ProbeRunner
from app.services.shell import ShellRunner
from app.storage.repository import RunRepository


@dataclass
class DiscoveryOutcome:
    baseline_result: EvaluatorResult
    probe_results: list[ProbeResult] = field(default_factory=list)
    failure_case: FailureCase | None = None


class DiscoveryEngine:
    def __init__(self, shell_runner: ShellRunner, repository: RunRepository) -> None:
        self.shell_runner = shell_runner
        self.repository = repository
        self.probe_runner = ProbeRunner(shell_runner)

    def run(self, workspace: Path, repo_profile: RepoProfile) -> DiscoveryOutcome:
        baseline_result = self._run_baseline(workspace, repo_profile)
        if not baseline_result.passed:
            failure_case = self.repository.create_failure_case(
                codebase_id=repo_profile.id,
                failure_type="baseline_test_failure",
                title="Baseline test failure discovered",
                probe_input={"test_command": repo_profile.test_command},
                failing_command=repo_profile.test_command or "",
                failing_output=baseline_result.details,
                reproduction_steps=[repo_profile.test_command] if repo_profile.test_command else [],
                suspect_files=repo_profile.source_dirs or repo_profile.entrypoints,
                severity="high",
                confidence=0.98,
                deterministic_check_ids=["baseline_tests"],
            )
            return DiscoveryOutcome(baseline_result=baseline_result, failure_case=failure_case)

        probe_results = self.probe_runner.run(workspace, repo_profile)
        failing_probes = [probe for probe in probe_results if not probe.passed]
        if not failing_probes:
            return DiscoveryOutcome(baseline_result=baseline_result, probe_results=probe_results)

        selected_probe = sorted(
            failing_probes,
            key=lambda probe: (self._severity_score(probe.severity), probe.confidence),
            reverse=True,
        )[0]
        failure_case = self.repository.create_failure_case(
            codebase_id=repo_profile.id,
            failure_type=selected_probe.probe_id,
            title=selected_probe.title,
            probe_input={
                "probe_id": selected_probe.probe_id,
                "script_path": selected_probe.script_path,
                "script_contents": selected_probe.script_contents,
            },
            failing_command=selected_probe.failing_command,
            failing_output=selected_probe.details,
            reproduction_steps=selected_probe.reproduction_steps,
            suspect_files=selected_probe.suspect_files,
            severity=selected_probe.severity,
            confidence=selected_probe.confidence,
            deterministic_check_ids=[selected_probe.probe_id],
        )
        return DiscoveryOutcome(
            baseline_result=baseline_result,
            probe_results=probe_results,
            failure_case=failure_case,
        )

    def _run_baseline(self, workspace: Path, repo_profile: RepoProfile) -> EvaluatorResult:
        if not repo_profile.test_command:
            return EvaluatorResult(
                name="baseline_tests",
                passed=True,
                summary="No baseline test command was detected.",
                details="The profiler could not infer a deterministic baseline test command for this repo.",
            )

        result = self.shell_runner.run(shlex.split(repo_profile.test_command), cwd=workspace)
        details = (result.stdout + "\n" + result.stderr).strip()
        return EvaluatorResult(
            name="baseline_tests",
            passed=result.exit_code == 0,
            summary="Baseline tests passed." if result.exit_code == 0 else "Baseline tests failed.",
            details=details,
        )

    def _severity_score(self, severity: str) -> int:
        return {
            "critical": 4,
            "high": 3,
            "medium": 2,
            "low": 1,
        }.get(severity, 0)
