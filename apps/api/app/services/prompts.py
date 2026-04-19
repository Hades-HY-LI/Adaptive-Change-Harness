from __future__ import annotations

from pathlib import Path

from app.models.schemas import BreakType, EvaluatorResult, FailureCase, RepairSkill, RepoProfile
from app.providers.base import RepairProposal


RELEVANT_FILES = [
    "src/pricing.py",
    "src/api_contract.py",
    "src/persistence.py",
    "src/checkout_service.py",
]


def build_repair_prompt(workspace: Path, break_type: BreakType, evaluator_results: list[EvaluatorResult]) -> str:
    failing = [result for result in evaluator_results if not result.passed]
    context_sections: list[str] = []
    for file_path in RELEVANT_FILES:
        context_sections.append(f"FILE: {file_path}\n```python\n{(workspace / file_path).read_text()}\n```")
    failure_sections = [
        f"EVALUATOR: {result.name}\nSUMMARY: {result.summary}\nDETAILS:\n{result.details}"
        for result in failing
    ]
    return "\n\n".join(
        [
            "You are repairing a small Python codebase inside an adaptive change harness.",
            f"The injected or detected break type is: {break_type.value}.",
            "Use the failing evaluator evidence to propose the smallest valid repair.",
            "Return JSON only with this exact schema:",
            '{"root_cause_summary": "...", "patch_summary": "...", "merge_confidence": "safe|needs_review|unsafe", "patches": [{"file_path": "src/file.py", "search": "exact existing text", "replace": "new text"}]}',
            "Do not include markdown fences.",
            "If you are unsure, return merge_confidence as needs_review and the minimal patches you believe are necessary.",
            "\n\nFAILURES:\n" + "\n\n".join(failure_sections),
            "\n\nCODEBASE CONTEXT:\n" + "\n\n".join(context_sections),
        ]
    )


def build_failure_case_repair_prompt(
    workspace: Path,
    failure_case: FailureCase,
    repo_profile: RepoProfile,
    reproduction_result: EvaluatorResult,
    matched_skill: RepairSkill | None = None,
) -> str:
    context_sections: list[str] = []
    for file_path in _collect_context_files(failure_case, repo_profile):
        target = workspace / file_path
        if not target.exists():
            continue
        context_sections.append(f"FILE: {file_path}\n```python\n{target.read_text()}\n```")

    skill_section = "No existing repair skill matched this failure case."
    if matched_skill is not None:
        skill_section = "\n".join(
            [
                f"MATCHED SKILL: {matched_skill.title}",
                f"BUG FAMILY: {matched_skill.bug_family}",
                "INVESTIGATION FLOW:",
                *[f"- {step}" for step in matched_skill.investigation_flow],
                "REPAIR STRATEGY:",
                *[f"- {step}" for step in matched_skill.repair_strategy],
                "VERIFICATION RECIPE:",
                *[f"- {step}" for step in matched_skill.verification_recipe],
            ]
        )

    return "\n\n".join(
        [
            "You are repairing a reproducible Python service failure inside an adaptive change harness.",
            "Use the exact failing repro as the primary deterministic gate and propose the smallest valid repair.",
            "Prefer edits in suspect files and do not broaden scope without evidence.",
            "Return JSON only with this exact schema:",
            '{"root_cause_summary": "...", "patch_summary": "...", "merge_confidence": "safe|needs_review|unsafe", "patches": [{"file_path": "app/file.py", "search": "exact existing text", "replace": "new text"}]}',
            "Do not include markdown fences.",
            f"FAILURE TITLE: {failure_case.title}",
            f"FAILURE TYPE: {failure_case.failure_type}",
            f"FAILING COMMAND: {failure_case.failing_command}",
            "REPRODUCTION STEPS:\n" + "\n".join(f"- {step}" for step in failure_case.reproduction_steps),
            "SUSPECT FILES:\n" + "\n".join(f"- {path}" for path in failure_case.suspect_files),
            f"REPO PROFILE: language={repo_profile.language}, framework={repo_profile.framework}, test_command={repo_profile.test_command or 'unknown'}",
            "DETERMINISTIC REPRO OUTPUT:\n"
            f"EVALUATOR: {reproduction_result.name}\nSUMMARY: {reproduction_result.summary}\nDETAILS:\n{reproduction_result.details}",
            "MATCHED SKILL GUIDANCE:\n" + skill_section,
            "CODEBASE CONTEXT:\n" + "\n\n".join(context_sections),
        ]
    )


def _collect_context_files(failure_case: FailureCase, repo_profile: RepoProfile) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for file_path in [*failure_case.suspect_files, *repo_profile.entrypoints]:
        normalized = file_path.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered[:6]
