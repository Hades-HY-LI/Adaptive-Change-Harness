from __future__ import annotations


def calculate_total(base_price_cents: int, is_premium: bool, coupon_percent: int = 0) -> int:
    premium_fee = 500 if is_premium else 0
    subtotal = base_price_cents + premium_fee
    discount = subtotal * coupon_percent // 100
    total = subtotal - discount
    return max(total, 0)
