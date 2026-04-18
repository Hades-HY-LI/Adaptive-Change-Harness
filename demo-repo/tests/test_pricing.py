from __future__ import annotations

import unittest

from src.pricing import calculate_total


class PricingTests(unittest.TestCase):
    def test_premium_customers_pay_the_service_fee(self) -> None:
        self.assertEqual(calculate_total(1000, True, 0), 1500)

    def test_coupon_applies_after_fee(self) -> None:
        self.assertEqual(calculate_total(1000, True, 10), 1350)


if __name__ == '__main__':
    unittest.main()
