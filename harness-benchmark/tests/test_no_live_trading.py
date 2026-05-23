import inspect
import unittest

from polypaper.client import PublicPolymarketClient, ReadOnlyViolation


class NoLiveTradingTests(unittest.TestCase):
    def test_rejects_order_like_endpoint(self):
        with self.assertRaises(ReadOnlyViolation):
            PublicPolymarketClient._validate_get("clob.polymarket.com", "/order")

    def test_rejects_non_allowlisted_endpoint(self):
        with self.assertRaises(ReadOnlyViolation):
            PublicPolymarketClient._validate_get("clob.polymarket.com", "/auth/api-key")

    def test_allowed_public_endpoints_pass(self):
        PublicPolymarketClient._validate_get("data-api.polymarket.com", "/v1/leaderboard")
        PublicPolymarketClient._validate_get("data-api.polymarket.com", "/trades")
        PublicPolymarketClient._validate_get("gamma-api.polymarket.com", "/markets")
        PublicPolymarketClient._validate_get("clob.polymarket.com", "/prices-history")
        PublicPolymarketClient._validate_get("clob.polymarket.com", "/clob-markets/0xabc")

    def test_client_has_no_post_method(self):
        public_methods = {
            name
            for name, value in inspect.getmembers(PublicPolymarketClient, predicate=inspect.isfunction)
            if not name.startswith("_")
        }
        self.assertNotIn("post", public_methods)
        self.assertNotIn("order", public_methods)
        self.assertNotIn("cancel", public_methods)


if __name__ == "__main__":
    unittest.main()
