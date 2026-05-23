import unittest

from polypaper.marketdata import quote_from_book, token_ids_from_market


class MarketDataTests(unittest.TestCase):
    def test_quote_from_book_uses_best_bid_and_best_ask(self):
        quote = quote_from_book(
            {
                "asset_id": "TOKEN",
                "timestamp": "1779532204340",
                "bids": [{"price": "0.10"}, {"price": "0.51"}, {"price": "0.30"}],
                "asks": [{"price": "0.99"}, {"price": "0.53"}, {"price": "0.75"}],
            }
        )
        self.assertEqual(quote.asset, "TOKEN")
        self.assertEqual(quote.timestamp, 1779532204)
        self.assertAlmostEqual(quote.bid, 0.51)
        self.assertAlmostEqual(quote.ask, 0.53)

    def test_token_ids_from_market_parses_gamma_string(self):
        self.assertEqual(token_ids_from_market({"clobTokenIds": "[\"A\", \"B\"]"}), ["A", "B"])


if __name__ == "__main__":
    unittest.main()
