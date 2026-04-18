from __future__ import annotations

import unittest

from src.checkout_service import create_checkout


class CheckoutTests(unittest.TestCase):
    def test_checkout_returns_total_cents(self) -> None:
        response = create_checkout("ord_123", 1000, True, 10)
        self.assertEqual(response["data"]["total_cents"], 1350)
        self.assertEqual(response["status"], "ok")


if __name__ == '__main__':
    unittest.main()
