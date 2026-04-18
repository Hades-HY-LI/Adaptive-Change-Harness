from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.models.schemas import BreakType


@dataclass
class Mutation:
    file_path: str
    search: str
    replace: str
    summary: str
    details: str


MUTATIONS: dict[BreakType, Mutation] = {
    BreakType.logic_regression: Mutation(
        file_path="src/pricing.py",
        search="premium_fee = 500 if is_premium else 0",
        replace="premium_fee = 0 if is_premium else 500",
        summary="Flipped the premium pricing condition.",
        details="Premium customers will be undercharged while non-premium customers get the fee.",
    ),
    BreakType.contract_violation: Mutation(
        file_path="src/api_contract.py",
        search='"total_cents": total_cents',
        replace='"amount_cents": total_cents',
        summary="Changed the response payload key.",
        details="The API contract now returns amount_cents instead of total_cents.",
    ),
    BreakType.invariant_violation: Mutation(
        file_path="src/checkout_service.py",
        search="    save_order_record(order_id, total)\n",
        replace='    persisted = {"order_id": order_id, "total_cents": total}\n',
        summary="Bypassed the persistence service call.",
        details="The handler no longer routes writes through save_order_record.",
    ),
}


class BreakEngine:
    def apply(self, workspace: Path, break_type: BreakType) -> Mutation:
        mutation = MUTATIONS[break_type]
        target_file = workspace / mutation.file_path
        content = target_file.read_text()
        if mutation.search not in content:
            raise ValueError(f"Expected pattern not found in {mutation.file_path}")
        updated = content.replace(mutation.search, mutation.replace, 1)
        target_file.write_text(updated)
        return mutation
