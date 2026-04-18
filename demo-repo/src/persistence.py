from __future__ import annotations


def save_order_record(order_id: str, total_cents: int) -> dict[str, object]:
    return {
        "order_id": order_id,
        "total_cents": total_cents,
        "write_path": "service",
    }
