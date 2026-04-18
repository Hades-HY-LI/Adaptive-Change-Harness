from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.checkout_service import create_checkout


response = create_checkout("ord_contract", 1000, True, 10)
expected_root_keys = {"status", "data", "error"}
expected_data_keys = {"order_id", "total_cents"}

if set(response.keys()) != expected_root_keys:
    raise SystemExit(f"Contract mismatch: root keys are {sorted(response.keys())}, expected {sorted(expected_root_keys)}")

payload = response.get("data")
if not isinstance(payload, dict):
    raise SystemExit("Contract mismatch: data payload must be a dictionary")

if set(payload.keys()) != expected_data_keys:
    raise SystemExit(f"Contract mismatch: data keys are {sorted(payload.keys())}, expected {sorted(expected_data_keys)}")

print("Contract check passed")
