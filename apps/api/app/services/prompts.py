from __future__ import annotations

from pathlib import Path

from app.models.schemas import BreakType, EvaluatorResult
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
