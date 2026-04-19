from __future__ import annotations

from app.providers.base import PatchOperation, ProviderError, RepairProposal, RepairProvider


class FakeProvider(RepairProvider):
    id = "fake"

    def generate_repair(self, *, model: str, prompt: str) -> RepairProposal:
        if "negative_total_quote" in prompt or "app/services/pricing.py" in prompt:
            return RepairProposal(
                root_cause_summary="Flat discounts are not bounded, so quote totals can become negative.",
                patch_summary="Clamp the taxable total to zero before tax is calculated.",
                merge_confidence="safe",
                patches=[
                    PatchOperation(
                        file_path="app/services/pricing.py",
                        search="    taxable_total = subtotal - discount_cents\n",
                        replace="    taxable_total = max(subtotal - discount_cents, 0)\n",
                    )
                ],
            )
        if "logic_regression" in prompt or "src/pricing.py" in prompt:
            return RepairProposal(
                root_cause_summary="The premium pricing branch was inverted.",
                patch_summary="Restore the premium fee conditional to its original logic.",
                merge_confidence="safe",
                patches=[
                    PatchOperation(
                        file_path="src/pricing.py",
                        search="premium_fee = 0 if is_premium else 500",
                        replace="premium_fee = 500 if is_premium else 0",
                    )
                ],
            )
        if "contract_violation" in prompt or "src/api_contract.py" in prompt:
            return RepairProposal(
                root_cause_summary="The API response key was renamed away from the expected contract.",
                patch_summary="Restore the response payload key to total_cents.",
                merge_confidence="safe",
                patches=[
                    PatchOperation(
                        file_path="src/api_contract.py",
                        search='"amount_cents": total_cents',
                        replace='"total_cents": total_cents',
                    )
                ],
            )
        if "invariant_violation" in prompt or "src/checkout_service.py" in prompt:
            return RepairProposal(
                root_cause_summary="Checkout bypassed the persistence helper, breaking the repo invariant.",
                patch_summary="Route writes back through save_order_record.",
                merge_confidence="safe",
                patches=[
                    PatchOperation(
                        file_path="src/checkout_service.py",
                        search='    persisted = {"order_id": order_id, "total_cents": total}\n',
                        replace="    save_order_record(order_id, total)\n",
                    )
                ],
            )
        raise ProviderError(f"No deterministic fake repair is defined for model '{model}'.")
