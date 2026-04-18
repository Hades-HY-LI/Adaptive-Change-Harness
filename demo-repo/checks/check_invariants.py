from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

checkout_service = Path("src/checkout_service.py").read_text()
required_patterns = [
    "save_order_record(order_id, total)",
    "return build_checkout_response(order_id, total)",
]

missing = [pattern for pattern in required_patterns if pattern not in checkout_service]
if missing:
    raise SystemExit(f"Invariant violation: missing required patterns {missing}")

print("Invariant check passed")
