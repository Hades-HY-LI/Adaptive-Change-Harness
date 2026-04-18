from __future__ import annotations


def build_checkout_response(order_id: str, total_cents: int) -> dict[str, object]:
    return {
        "status": "ok",
        "data": {
            "order_id": order_id,
            "total_cents": total_cents,
        },
        "error": None,
    }
