from __future__ import annotations

from src.api_contract import build_checkout_response
from src.persistence import save_order_record
from src.pricing import calculate_total


def create_checkout(order_id: str, base_price_cents: int, is_premium: bool, coupon_percent: int = 0) -> dict[str, object]:
    total = calculate_total(base_price_cents, is_premium, coupon_percent)
    save_order_record(order_id, total)
    return build_checkout_response(order_id, total)
