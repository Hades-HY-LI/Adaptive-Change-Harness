from __future__ import annotations

from pathlib import Path

from app.models.schemas import EvaluatorResult
from app.services.shell import ShellRunner


class EvaluatorEngine:
    def __init__(self, shell_runner: ShellRunner) -> None:
        self.shell_runner = shell_runner

    def evaluate(self, workspace: Path) -> list[EvaluatorResult]:
        return [
            self._run_unit_tests(workspace),
            self._run_contract_check(workspace),
            self._run_invariant_check(workspace),
        ]

    def _run_unit_tests(self, workspace: Path) -> EvaluatorResult:
        result = self.shell_runner.run(
            self.shell_runner.python_command("-m", "unittest", "discover", "-s", "tests", "-v"),
            cwd=workspace,
        )
        passed = result.exit_code == 0
        return EvaluatorResult(
            name="unit_tests",
            passed=passed,
            summary="Demo repo unit tests passed." if passed else "Unit tests failed.",
            details=(result.stdout + "\n" + result.stderr).strip(),
        )

    def _run_contract_check(self, workspace: Path) -> EvaluatorResult:
        result = self.shell_runner.run(self.shell_runner.python_command("checks/check_contract.py"), cwd=workspace)
        passed = result.exit_code == 0
        return EvaluatorResult(
            name="contract_check",
            passed=passed,
            summary="Contract check passed." if passed else "Contract check failed.",
            details=(result.stdout + "\n" + result.stderr).strip(),
        )

    def _run_invariant_check(self, workspace: Path) -> EvaluatorResult:
        result = self.shell_runner.run(self.shell_runner.python_command("checks/check_invariants.py"), cwd=workspace)
        passed = result.exit_code == 0
        return EvaluatorResult(
            name="invariant_check",
            passed=passed,
            summary="Invariant check passed." if passed else "Invariant check failed.",
            details=(result.stdout + "\n" + result.stderr).strip(),
        )
