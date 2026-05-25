import inspect
import unittest
from unittest.mock import patch
from urllib.error import URLError

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
        PublicPolymarketClient._validate_post("clob.polymarket.com", "/books")

    def test_rejects_non_allowlisted_post_endpoint(self):
        with self.assertRaises(ReadOnlyViolation):
            PublicPolymarketClient._validate_post("clob.polymarket.com", "/order")

    def test_batch_books_uses_allowlisted_public_post_shape(self):
        client = PublicPolymarketClient()
        calls = []

        def fake_post(host, path, payload):
            calls.append((host, path, payload))
            return [{"asset_id": payload[0]["token_id"], "bids": [], "asks": []}]

        client._post_json = fake_post

        result = client.books(["TOKEN-A"])

        self.assertEqual(len(result), 1)
        self.assertEqual(
            calls,
            [
                (
                    "clob.polymarket.com",
                    "/books",
                    [{"token_id": "TOKEN-A"}],
                )
            ],
        )

    def test_markets_by_condition_id_uses_public_gamma_markets_endpoint(self):
        client = PublicPolymarketClient()
        calls = []

        def fake_get(host, path, params):
            calls.append((host, path, params))
            return [{"conditionId": params["condition_ids"]}]

        client._get_json = fake_get

        result = client.markets_by_condition_id("0xcondition", closed=True, active=None, limit=3)

        self.assertEqual(result, [{"conditionId": "0xcondition"}])
        self.assertEqual(
            calls,
            [
                (
                    "gamma-api.polymarket.com",
                    "/markets",
                    {
                        "condition_ids": "0xcondition",
                        "limit": 3,
                        "closed": "true",
                    },
                )
            ],
        )

    def test_public_get_retries_transient_url_errors(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{"ok": true}'

        client = PublicPolymarketClient(retries=1, retry_backoff=0)
        with patch("polypaper.client.urlopen", side_effect=[URLError("temporary eof"), FakeResponse()]) as mocked:
            result = client._get_json("gamma-api.polymarket.com", "/markets", {"limit": 1})

        self.assertEqual(result, {"ok": True})
        self.assertEqual(mocked.call_count, 2)

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
