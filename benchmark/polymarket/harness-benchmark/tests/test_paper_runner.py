from dataclasses import replace
import sqlite3
import unittest

from polypaper.models import BookLevel, MarketSnapshot, OrderBook, Portfolio, Signal
from polypaper.paper import (
    CollectionResult,
    MarketDataCollector,
    PaperRunner,
    PublicMarketSettlementResolver,
)
from polypaper.report import markdown_report
from polypaper.simulator import ConservativeFillModel, LatencyModel, MarketRules, PolymarketFeeModel
from polypaper.storage import init_db
from polypaper.strategies.paper import (
    CryptoIntervalAnchorPaperStrategy,
    NoTradePaperStrategy,
    PaperStrategy,
    RandomMarketTakerStrategy,
    TargetProfitPaperStrategy,
)
from polypaper.verification import verify_target_run


class FakePolymarketClient:
    def __init__(self):
        self.book_calls = 0
        self.market_call_kwargs = None

    def markets(self, limit=5, closed=False, **kwargs):
        self.market_call_kwargs = {"limit": limit, "closed": closed, **kwargs}
        return [
            {
                "conditionId": "0xcondition",
                "question": "Fixture paper market?",
                "slug": "fixture-paper-market",
                "outcomes": '["Yes"]',
                "clobTokenIds": '["TOKEN-YES"]',
                "orderPriceMinTickSize": 0.01,
                "orderMinSize": 1,
                "feeSchedule": {"rate": 0.05, "exponent": 1, "takerOnly": True},
            }
        ]

    def book(self, token_id):
        self.book_calls += 1
        return {
            "asset_id": token_id,
            "timestamp": str(1000 + self.book_calls),
            "bids": [{"price": "0.49", "size": "100"}],
            "asks": [{"price": "0.50", "size": "100"}],
        }


class SettlementClient:
    def __init__(self, outcome_prices='["1", "0"]'):
        self.outcome_prices = outcome_prices
        self.market_calls = 0
        self.book_calls = 0
        self.settlement_calls = []

    def markets(self, limit=5, closed=False, **kwargs):
        self.market_calls += 1
        if self.market_calls > 1:
            return []
        return [
            {
                "conditionId": "0xsettle",
                "question": "Bitcoin Up or Down?",
                "slug": "bitcoin-up-or-down",
                "outcomes": '["Up", "Down"]',
                "clobTokenIds": '["TOKEN-UP", "TOKEN-DOWN"]',
                "orderPriceMinTickSize": 0.01,
                "orderMinSize": 1,
            }
        ]

    def book(self, token_id):
        self.book_calls += 1
        if self.book_calls > 1:
            raise RuntimeError("closed book unavailable")
        return {
            "asset_id": token_id,
            "timestamp": "1000",
            "bids": [{"price": "0.49", "size": "100"}],
            "asks": [{"price": "0.50", "size": "100"}],
        }

    def markets_by_condition_id(self, condition_id, closed=None, active=None, limit=10):
        self.settlement_calls.append((condition_id, closed, active, limit))
        return [
            {
                "conditionId": condition_id,
                "closed": True,
                "outcomes": '["Up", "Down"]',
                "clobTokenIds": '["TOKEN-UP", "TOKEN-DOWN"]',
                "outcomePrices": self.outcome_prices,
            }
        ]


class AlreadyClosedSettlementClient(SettlementClient):
    def markets(self, limit=5, closed=False, **kwargs):
        self.market_calls += 1
        return []

    def book(self, token_id):
        self.book_calls += 1
        raise RuntimeError("closed book unavailable")


class BuyOncePaperStrategy(PaperStrategy):
    name = "paper_buy_once"

    def __init__(self):
        self.bought = False
        self.seen_fills = []

    def on_snapshot(self, snapshot, portfolio):
        return []

    def on_snapshots(self, snapshots, portfolio, rules_by_asset=None):
        if self.bought or not snapshots:
            return []
        self.bought = True
        snapshot = snapshots[0]
        return [
            Signal(
                strategy=self.name,
                timestamp=snapshot.timestamp,
                side="BUY",
                asset=snapshot.asset,
                condition_id=snapshot.condition_id,
                target_notional=50.0,
                reason="test_entry",
                execution_style="taker",
            )
        ]

    def on_fill(self, fill):
        self.seen_fills.append(fill)


class FlakyBookClient(FakePolymarketClient):
    def markets(self, limit=5, closed=False, **kwargs):
        self.market_call_kwargs = {"limit": limit, "closed": closed, **kwargs}
        return [
            {
                "conditionId": "0xcondition",
                "question": "Fixture paper market?",
                "slug": "fixture-paper-market",
                "outcomes": '["Bad", "Good"]',
                "clobTokenIds": '["TOKEN-BAD", "TOKEN-GOOD"]',
                "orderPriceMinTickSize": 0.01,
                "orderMinSize": 1,
                "feeSchedule": {"rate": 0.05, "exponent": 1, "takerOnly": True},
            }
        ]

    def book(self, token_id):
        self.book_calls += 1
        if token_id == "TOKEN-BAD":
            raise RuntimeError("stale token")
        return {
            "asset_id": token_id,
            "timestamp": str(1000 + self.book_calls),
            "bids": [{"price": "0.49", "size": "100"}],
            "asks": [{"price": "0.50", "size": "100"}],
        }


class BatchBookClient(FakePolymarketClient):
    def __init__(self):
        super().__init__()
        self.batch_calls = []

    def markets(self, limit=5, closed=False, **kwargs):
        self.market_call_kwargs = {"limit": limit, "closed": closed, **kwargs}
        return [
            {
                "conditionId": "0xbatch",
                "question": "Batch fixture?",
                "slug": "batch-fixture",
                "outcomes": '["Alpha", "Bravo", "Charlie"]',
                "clobTokenIds": '["TOKEN-A", "TOKEN-B", "TOKEN-C"]',
                "orderPriceMinTickSize": 0.01,
                "orderMinSize": 1,
            }
        ]

    def books(self, token_ids):
        ids = list(token_ids)
        self.batch_calls.append(ids)
        return [
            {
                "asset_id": token_id,
                "timestamp": str(1000 + index),
                "bids": [{"price": "0.49", "size": "100"}],
                "asks": [{"price": "0.50", "size": "100"}],
            }
            for index, token_id in enumerate(ids, start=1)
        ]


class BatchBookFailureClient(BatchBookClient):
    def books(self, token_ids):
        self.batch_calls.append(list(token_ids))
        raise RuntimeError("batch unavailable")


class BatchBookMissingClient(BatchBookClient):
    def books(self, token_ids):
        ids = list(token_ids)
        self.batch_calls.append(ids)
        return [
            {
                "asset_id": token_id,
                "timestamp": str(1000 + index),
                "bids": [{"price": "0.49", "size": "100"}],
                "asks": [{"price": "0.50", "size": "100"}],
            }
            for index, token_id in enumerate(ids, start=1)
            if token_id != "TOKEN-A"
        ]


class KeywordMarketClient(FakePolymarketClient):
    def __init__(self):
        super().__init__()
        self.batch_calls = []

    def markets(self, limit=5, closed=False, **kwargs):
        self.market_call_kwargs = {"limit": limit, "closed": closed, **kwargs}
        return [
            {
                "conditionId": "0xboring",
                "question": "Will the fixture resolve yes?",
                "slug": "fixture-resolves-yes",
                "category": "Politics",
                "outcomes": '["Yes"]',
                "clobTokenIds": '["TOKEN-BORING"]',
                "orderPriceMinTickSize": 0.01,
                "orderMinSize": 1,
            },
            {
                "conditionId": "0xcrypto",
                "question": "Bitcoin Up or Down on May 24?",
                "slug": "bitcoin-updown-may-24",
                "categorySlug": "crypto",
                "outcomes": '["Up", "Down"]',
                "clobTokenIds": '["TOKEN-UP", "TOKEN-DOWN"]',
                "orderPriceMinTickSize": 0.01,
                "orderMinSize": 1,
            },
            {
                "conditionId": "0xsports",
                "question": "Will the fixture team win?",
                "slug": "fixture-team-win",
                "category": "Sports",
                "outcomes": '["Yes"]',
                "clobTokenIds": '["TOKEN-SPORTS"]',
                "orderPriceMinTickSize": 0.01,
                "orderMinSize": 1,
            },
        ]

    def books(self, token_ids):
        ids = list(token_ids)
        self.batch_calls.append(ids)
        return [
            {
                "asset_id": token_id,
                "timestamp": str(1000 + index),
                "bids": [{"price": "0.49", "size": "100"}],
                "asks": [{"price": "0.50", "size": "100"}],
            }
            for index, token_id in enumerate(ids, start=1)
        ]


class ShortCryptoIntervalClient(KeywordMarketClient):
    def markets(self, limit=5, closed=False, **kwargs):
        self.market_call_kwargs = {"limit": limit, "closed": closed, **kwargs}
        return [
            {
                "conditionId": "0xgeneric",
                "question": "Bitcoin Up or Down on May 24?",
                "slug": "bitcoin-updown-may-24",
                "categorySlug": "crypto",
                "outcomes": '["Up", "Down"]',
                "clobTokenIds": '["TOKEN-GENERIC-UP", "TOKEN-GENERIC-DOWN"]',
                "orderPriceMinTickSize": 0.01,
                "orderMinSize": 1,
            },
            {
                "conditionId": "0xfuture",
                "question": "Bitcoin Up or Down - future",
                "slug": "btc-updown-5m-1779608700",
                "categorySlug": "crypto",
                "outcomes": '["Up", "Down"]',
                "clobTokenIds": '["TOKEN-FUTURE-UP", "TOKEN-FUTURE-DOWN"]',
                "orderPriceMinTickSize": 0.01,
                "orderMinSize": 1,
            },
            {
                "conditionId": "0xactive",
                "question": "Ethereum Up or Down - active",
                "slug": "eth-updown-5m-1779608400",
                "categorySlug": "crypto",
                "outcomes": '["Up", "Down"]',
                "clobTokenIds": '["TOKEN-ACTIVE-UP", "TOKEN-ACTIVE-DOWN"]',
                "orderPriceMinTickSize": 0.01,
                "orderMinSize": 1,
            },
        ]


class PaginatedKeywordMarketClient(KeywordMarketClient):
    def __init__(self):
        super().__init__()
        self.market_call_kwargs_by_call = []

    def markets(self, limit=5, closed=False, **kwargs):
        call = {"limit": limit, "closed": closed, **kwargs}
        self.market_call_kwargs = call
        self.market_call_kwargs_by_call.append(call)
        offset = int(kwargs.get("offset", 0))
        if offset <= 0:
            return [
                {
                    "conditionId": "0xboring",
                    "question": "Will the fixture resolve yes?",
                    "slug": "fixture-resolves-yes",
                    "category": "Politics",
                    "outcomes": '["Yes"]',
                    "clobTokenIds": '["TOKEN-BORING"]',
                    "orderPriceMinTickSize": 0.01,
                    "orderMinSize": 1,
                }
            ]
        return [
            {
                "conditionId": "0xcrypto",
                "question": "Bitcoin Up or Down - next",
                "slug": "btc-updown-5m-1779608400",
                "categorySlug": "crypto",
                "outcomes": '["Up", "Down"]',
                "clobTokenIds": '["TOKEN-PAGED-UP", "TOKEN-PAGED-DOWN"]',
                "orderPriceMinTickSize": 0.01,
                "orderMinSize": 1,
            }
        ]


class HistoryMomentumClient(FakePolymarketClient):
    def __init__(self):
        super().__init__()
        self.history_calls = []

    def markets(self, limit=5, closed=False, **kwargs):
        self.market_call_kwargs = {"limit": limit, "closed": closed, **kwargs}
        return [
            {
                "conditionId": "0xcondition",
                "question": "Fixture paper market?",
                "slug": "fixture-paper-market",
                "outcomes": '["Alpha", "Bravo", "Charlie"]',
                "clobTokenIds": '["TOKEN-A", "TOKEN-B", "TOKEN-C"]',
                "orderPriceMinTickSize": 0.01,
                "orderMinSize": 1,
                "feeSchedule": {"rate": 0.05, "exponent": 1, "takerOnly": True},
            }
        ]

    def book(self, token_id):
        self.book_calls += 1
        return {
            "asset_id": token_id,
            "timestamp": str(1000 + self.book_calls),
            "bids": [{"price": "0.49", "size": "100"}],
            "asks": [{"price": "0.50", "size": "100"}],
        }

    def price_history(self, token_id, start_ts, end_ts, interval="1h"):
        self.history_calls.append((token_id, start_ts, end_ts, interval))
        histories = {
            "TOKEN-A": [0.50, 0.60],
            "TOKEN-B": [0.50, 0.80],
            "TOKEN-C": [0.50, 0.51],
        }
        return {"history": [{"p": value} for value in histories[token_id]]}


class HistoryPrefilterClient(HistoryMomentumClient):
    def book(self, token_id):
        self.book_calls += 1
        books = {
            "TOKEN-A": ("0.20", "0.21"),
            "TOKEN-B": ("0.49", "0.50"),
            "TOKEN-C": ("0.49", "0.60"),
        }
        bid, ask = books[token_id]
        return {
            "asset_id": token_id,
            "timestamp": str(1000 + self.book_calls),
            "bids": [{"price": bid, "size": "100"}],
            "asks": [{"price": ask, "size": "100"}],
        }


class RotatingPinnedClient(FakePolymarketClient):
    def __init__(self):
        super().__init__()
        self.market_calls = 0
        self.book_call_tokens = []

    def markets(self, limit=5, closed=False, **kwargs):
        self.market_call_kwargs = {"limit": limit, "closed": closed, **kwargs}
        self.market_calls += 1
        token = "TOKEN-A" if self.market_calls == 1 else "TOKEN-B"
        return [
            {
                "conditionId": f"0xcondition-{token}",
                "question": f"{token} fixture?",
                "slug": f"{token.lower()}-fixture",
                "outcomes": '["Yes"]',
                "clobTokenIds": f'["{token}"]',
                "orderPriceMinTickSize": 0.01,
                "orderMinSize": 1,
            }
        ]

    def book(self, token_id):
        self.book_calls += 1
        self.book_call_tokens.append(token_id)
        if token_id == "TOKEN-A" and self.book_call_tokens.count("TOKEN-A") > 1:
            bid, ask = "0.62", "0.63"
        elif token_id == "TOKEN-A":
            bid, ask = "0.49", "0.50"
        else:
            bid, ask = "0.10", "0.11"
        return {
            "asset_id": token_id,
            "timestamp": str(1000 + self.book_calls),
            "bids": [{"price": bid, "size": "100"}],
            "asks": [{"price": ask, "size": "100"}],
        }


class SequenceCollector:
    def __init__(self, snapshots, rules=None):
        self.snapshots = list(snapshots)
        self.rules = rules or {}
        self.collection_count = 0

    def collect(self):
        index = min(self.collection_count, len(self.snapshots) - 1)
        snapshot = self.snapshots[index]
        self.collection_count += 1
        return CollectionResult(
            snapshots=[snapshot],
            rules_by_asset={snapshot.asset: self.rules.get(snapshot.asset, MarketRules())},
        )


class StaticCollector:
    def __init__(self, snapshots):
        self.snapshots = list(snapshots)
        self.collection_count = 0

    def collect(self):
        self.collection_count += 1
        return CollectionResult(
            snapshots=self.snapshots,
            rules_by_asset={snapshot.asset: MarketRules() for snapshot in self.snapshots},
        )


class BatchSequenceCollector:
    def __init__(self, batches):
        self.batches = [list(batch) for batch in batches]
        self.collection_count = 0

    def collect(self):
        index = min(self.collection_count, len(self.batches) - 1)
        snapshots = self.batches[index]
        self.collection_count += 1
        return CollectionResult(
            snapshots=snapshots,
            rules_by_asset={snapshot.asset: MarketRules() for snapshot in snapshots},
        )


class StaticSpotProvider:
    def __init__(self, price):
        self.price = price
        self.calls = []

    def prices(self, symbols):
        self.calls.append(tuple(symbols))
        return {str(symbol).upper(): self.price for symbol in symbols}


def snapshot_at(timestamp, bid, ask, bid_size=1000, ask_size=1000):
    return MarketSnapshot(
        asset="TOKEN-YES",
        condition_id="0xcondition",
        timestamp=timestamp,
        book=OrderBook(
            asset="TOKEN-YES",
            timestamp=timestamp,
            bids=(BookLevel(price=bid, size=bid_size),),
            asks=(BookLevel(price=ask, size=ask_size),),
        ),
        title="Target fixture",
        outcome="Yes",
    )


def named_snapshot(asset, timestamp, bid, ask, title):
    return MarketSnapshot(
        asset=asset,
        condition_id=f"0xcondition-{asset}",
        timestamp=timestamp,
        book=OrderBook(
            asset=asset,
            timestamp=timestamp,
            bids=(BookLevel(price=bid, size=1000),),
            asks=(BookLevel(price=ask, size=1000),),
        ),
        title=title,
        outcome="Yes",
    )


def depth_snapshot(timestamp, bid, bid_size, ask, ask_size):
    return MarketSnapshot(
        asset="TOKEN-YES",
        condition_id="0xcondition",
        timestamp=timestamp,
        book=OrderBook(
            asset="TOKEN-YES",
            timestamp=timestamp,
            bids=(BookLevel(price=bid, size=bid_size),),
            asks=(BookLevel(price=ask, size=ask_size),),
        ),
        title="Depth fixture",
        outcome="Yes",
    )


def crypto_interval_snapshot(asset, outcome, timestamp=1779608405):
    return MarketSnapshot(
        asset=asset,
        condition_id="0xcrypto",
        timestamp=timestamp,
        book=OrderBook(
            asset=asset,
            timestamp=timestamp,
            bids=(BookLevel(price=0.49, size=1000),),
            asks=(BookLevel(price=0.50, size=1000),),
        ),
        title="Ethereum Up or Down - May 24, 3:40AM-3:45AM ET",
        slug="eth-updown-5m-1779608400",
        outcome=outcome,
        outcome_index=0 if outcome == "Up" else 1,
    )


class PaperRunnerTests(unittest.TestCase):
    def test_market_collector_orders_active_markets_by_default(self):
        client = FakePolymarketClient()
        collector = MarketDataCollector(client, market_limit=7, max_assets=1)

        collector.collect()

        self.assertEqual(
            client.market_call_kwargs,
            {
                "limit": 7,
                "closed": False,
                "active": True,
                "order": "volume_24hr",
                "ascending": False,
            },
        )

    def test_market_collector_accepts_custom_market_ordering(self):
        client = FakePolymarketClient()
        collector = MarketDataCollector(
            client,
            market_limit=7,
            max_assets=1,
            market_order="liquidity",
            market_ascending=True,
        )

        collector.collect()

        self.assertEqual(client.market_call_kwargs["order"], "liquidity")
        self.assertTrue(client.market_call_kwargs["ascending"])

    def test_market_collector_prioritizes_keyword_markets_before_asset_cap(self):
        client = KeywordMarketClient()
        collector = MarketDataCollector(
            client,
            market_limit=3,
            max_assets=2,
            market_prefer_keywords=["up or down", "updown"],
        )

        collection = collector.collect()

        self.assertEqual([snapshot.asset for snapshot in collection.snapshots], ["TOKEN-UP", "TOKEN-DOWN"])
        self.assertEqual(client.batch_calls, [["TOKEN-UP", "TOKEN-DOWN"]])

    def test_market_collector_prioritizes_active_short_crypto_intervals(self):
        client = ShortCryptoIntervalClient()
        collector = MarketDataCollector(
            client,
            market_limit=3,
            max_assets=2,
            market_prefer_keywords=["up or down", "updown"],
            clock=lambda: 1779608460,
        )

        collection = collector.collect()

        self.assertEqual([snapshot.asset for snapshot in collection.snapshots], ["TOKEN-ACTIVE-UP", "TOKEN-ACTIVE-DOWN"])
        self.assertEqual(client.batch_calls, [["TOKEN-ACTIVE-UP", "TOKEN-ACTIVE-DOWN"]])

    def test_market_collector_can_scan_paginated_keyword_markets(self):
        client = PaginatedKeywordMarketClient()
        collector = MarketDataCollector(
            client,
            market_limit=1,
            market_pages=2,
            max_assets=2,
            market_filter_keywords=["up or down", "updown"],
        )

        collection = collector.collect()

        self.assertEqual([snapshot.asset for snapshot in collection.snapshots], ["TOKEN-PAGED-UP", "TOKEN-PAGED-DOWN"])
        self.assertEqual([call.get("offset", 0) for call in client.market_call_kwargs_by_call], [0, 1])
        self.assertEqual(client.batch_calls, [["TOKEN-PAGED-UP", "TOKEN-PAGED-DOWN"]])

    def test_market_collector_filters_keyword_markets(self):
        client = KeywordMarketClient()
        collector = MarketDataCollector(
            client,
            market_limit=3,
            max_assets=4,
            market_filter_keywords=["up or down"],
        )

        collection = collector.collect()

        self.assertEqual([snapshot.asset for snapshot in collection.snapshots], ["TOKEN-UP", "TOKEN-DOWN"])
        self.assertEqual(client.batch_calls, [["TOKEN-UP", "TOKEN-DOWN"]])

    def test_market_collector_skips_tokens_with_book_errors(self):
        client = FlakyBookClient()
        collector = MarketDataCollector(client, market_limit=1, max_assets=2)

        collection = collector.collect()

        self.assertEqual([snapshot.asset for snapshot in collection.snapshots], ["TOKEN-GOOD"])
        self.assertEqual(client.book_calls, 2)

    def test_market_collector_prefers_batch_books(self):
        client = BatchBookClient()
        collector = MarketDataCollector(client, market_limit=1, max_assets=2)

        collection = collector.collect()

        self.assertEqual([snapshot.asset for snapshot in collection.snapshots], ["TOKEN-A", "TOKEN-B"])
        self.assertEqual(client.batch_calls, [["TOKEN-A", "TOKEN-B"]])
        self.assertEqual(client.book_calls, 0)

    def test_market_collector_falls_back_when_batch_books_fail(self):
        client = BatchBookFailureClient()
        collector = MarketDataCollector(client, market_limit=1, max_assets=2)

        collection = collector.collect()

        self.assertEqual([snapshot.asset for snapshot in collection.snapshots], ["TOKEN-A", "TOKEN-B"])
        self.assertEqual(client.batch_calls, [["TOKEN-A", "TOKEN-B"]])
        self.assertEqual(client.book_calls, 2)

    def test_market_collector_backfills_when_batch_omits_books(self):
        client = BatchBookMissingClient()
        collector = MarketDataCollector(client, market_limit=1, max_assets=2)

        collection = collector.collect()

        self.assertEqual([snapshot.asset for snapshot in collection.snapshots], ["TOKEN-B", "TOKEN-C"])
        self.assertEqual(client.batch_calls, [["TOKEN-A", "TOKEN-B"], ["TOKEN-C"]])
        self.assertEqual(client.book_calls, 0)

    def test_market_collector_history_filter_expands_and_ranks_candidate_assets(self):
        client = HistoryMomentumClient()
        collector = MarketDataCollector(
            client,
            market_limit=1,
            max_assets=1,
            history_window_seconds=1000,
            history_min_change_pct=0.05,
            history_candidate_assets=3,
            clock=lambda: 2000,
        )

        collection = collector.collect()

        self.assertEqual([snapshot.asset for snapshot in collection.snapshots], ["TOKEN-B"])
        self.assertAlmostEqual(collection.snapshots[0].history_change_pct, 0.60)
        self.assertEqual(list(collection.rules_by_asset), ["TOKEN-B"])
        self.assertEqual(client.book_calls, 3)
        self.assertEqual(
            client.history_calls,
            [
                ("TOKEN-A", 1000, 2000, "1h"),
                ("TOKEN-B", 1000, 2000, "1h"),
                ("TOKEN-C", 1000, 2000, "1h"),
            ],
        )

    def test_market_collector_caches_history_changes_within_ttl(self):
        client = HistoryMomentumClient()
        collector = MarketDataCollector(
            client,
            market_limit=1,
            max_assets=1,
            history_window_seconds=1000,
            history_min_change_pct=0.05,
            history_candidate_assets=3,
            history_cache_seconds=60,
            clock=lambda: 2000,
        )

        first = collector.collect()
        second = collector.collect()

        self.assertEqual([snapshot.asset for snapshot in first.snapshots], ["TOKEN-B"])
        self.assertEqual([snapshot.asset for snapshot in second.snapshots], ["TOKEN-B"])
        self.assertEqual(client.book_calls, 6)
        self.assertEqual(len(client.history_calls), 3)

    def test_market_collector_prefilters_history_queries_by_current_book(self):
        client = HistoryPrefilterClient()
        collector = MarketDataCollector(
            client,
            market_limit=1,
            max_assets=1,
            history_window_seconds=1000,
            history_candidate_assets=3,
            history_min_bid_price=0.45,
            history_max_bid_price=0.55,
            history_max_spread_pct=0.03,
            clock=lambda: 2000,
        )

        collection = collector.collect()

        self.assertEqual([snapshot.asset for snapshot in collection.snapshots], ["TOKEN-B"])
        self.assertEqual(
            client.history_calls,
            [
                ("TOKEN-B", 1000, 2000, "1h"),
            ],
        )

    def test_market_collector_caps_history_queries_per_cycle(self):
        client = HistoryMomentumClient()
        collector = MarketDataCollector(
            client,
            market_limit=1,
            max_assets=1,
            history_window_seconds=1000,
            history_candidate_assets=3,
            history_max_queries=2,
            clock=lambda: 2000,
        )

        collection = collector.collect()

        self.assertEqual([snapshot.asset for snapshot in collection.snapshots], ["TOKEN-B"])
        self.assertEqual(len(client.history_calls), 2)

    def test_market_collector_keeps_pinned_assets_after_history_filter(self):
        client = HistoryMomentumClient()
        collector = MarketDataCollector(
            client,
            market_limit=1,
            max_assets=1,
            history_window_seconds=1000,
            history_min_change_pct=0.05,
            history_candidate_assets=3,
            pinned_assets=["TOKEN-C"],
            clock=lambda: 2000,
        )

        collection = collector.collect()

        self.assertEqual([snapshot.asset for snapshot in collection.snapshots], ["TOKEN-B", "TOKEN-C"])
        self.assertEqual(list(collection.rules_by_asset), ["TOKEN-B", "TOKEN-C"])

    def test_market_collector_refreshes_cached_pinned_asset_outside_candidate_set(self):
        client = RotatingPinnedClient()
        collector = MarketDataCollector(client, market_limit=1, max_assets=1)

        first = collector.collect()
        collector.pinned_assets.add("TOKEN-A")
        second = collector.collect()

        self.assertEqual([snapshot.asset for snapshot in first.snapshots], ["TOKEN-A"])
        self.assertEqual([snapshot.asset for snapshot in second.snapshots], ["TOKEN-B", "TOKEN-A"])
        self.assertEqual(second.snapshots[1].title, "TOKEN-A fixture?")
        self.assertEqual(second.snapshots[1].book.bid, 0.62)
        self.assertEqual(list(second.rules_by_asset), ["TOKEN-B", "TOKEN-A"])

    def test_market_collector_fetches_pinned_asset_without_cached_metadata(self):
        client = RotatingPinnedClient()
        collector = MarketDataCollector(client, market_limit=1, max_assets=0, pinned_assets=["TOKEN-A"])

        collection = collector.collect()

        self.assertEqual([snapshot.asset for snapshot in collection.snapshots], ["TOKEN-A"])
        self.assertEqual(collection.snapshots[0].title, "pinned asset TOKEN-A")
        self.assertEqual(collection.snapshots[0].condition_id, "")
        self.assertEqual(client.market_calls, 0)
        self.assertEqual(client.book_call_tokens, ["TOKEN-A"])

    def test_pinned_only_runner_uses_default_fee_rules_when_market_rules_missing(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        client = RotatingPinnedClient()
        runner = PaperRunner(
            client=client,
            conn=conn,
            run_id="pinned-fee-run",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.10,
                    entry_notional=40,
                    min_book_imbalance=-1.0,
                    max_entry_mark_to_bid_loss_pct=0.05,
                    min_momentum_observations=1,
                    allowed_assets=["TOKEN-A"],
                )
            ],
            fill_model=ConservativeFillModel(
                latency_model=LatencyModel(execution_delay_seconds=0),
                default_rules=MarketRules(fee_model=PolymarketFeeModel(fee_rate=0.05)),
            ),
            initial_cash=100,
            market_limit=0,
            max_assets=0,
            pinned_assets=["TOKEN-A"],
        )

        result = runner.run(cycles=1)[0]

        self.assertEqual(client.market_calls, 0)
        self.assertEqual(result.metrics["filled_orders"], 1)
        self.assertGreater(result.metrics["fees"], 0)

    def test_runner_uses_one_cycle_wall_time_for_interval_anchor_agents(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        snapshots = [
            crypto_interval_snapshot("TOKEN-UP", "Up"),
            crypto_interval_snapshot("TOKEN-DOWN", "Down"),
        ]
        strategies = [
            CryptoIntervalAnchorPaperStrategy(
                initial_cash=100,
                entry_notional=20,
                max_anchor_lag_seconds=30,
                min_market_age_seconds=20,
                spot_provider=StaticSpotProvider(100.0),
                clock=lambda: 1779608500,
                name=f"paper_interval_anchor_{index}",
            )
            for index in range(2)
        ]
        runner = PaperRunner(
            client=None,
            conn=conn,
            run_id="shared-cycle-wall-run",
            strategies=strategies,
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            collector=StaticCollector(snapshots),
            settlement_check_seconds=-1,
            clock=lambda: 1779608410,
        )

        runner.run_once()

        for strategy in strategies:
            self.assertIn("0xcrypto", strategy.anchors_by_condition)
            self.assertEqual(strategy.anchors_by_condition["0xcrypto"].anchored_at, 1779608410)
        reasons = [
            row[0]
            for row in conn.execute(
                "SELECT reason FROM strategy_diagnostics WHERE run_id = ?",
                ("shared-cycle-wall-run",),
            ).fetchall()
        ]
        self.assertIn("market_too_young", reasons)
        self.assertNotIn("anchor_late", reasons)

    def test_runner_settles_closed_binary_market_from_public_metadata(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        client = SettlementClient()
        strategy = BuyOncePaperStrategy()
        runner = PaperRunner(
            client=client,
            conn=conn,
            run_id="settlement-run",
            strategies=[strategy],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            market_limit=1,
            max_assets=1,
            settlement_check_seconds=0,
        )

        runner.run_once()
        runner.run_once()

        state = list(runner.agent_batch)[0]
        result = runner.results()[0]
        self.assertEqual(state.portfolio.positions, {})
        self.assertAlmostEqual(state.portfolio.cash, 150.0)
        self.assertAlmostEqual(result.metrics["ending_equity"], 150.0)
        self.assertAlmostEqual(result.metrics["roi"], 0.50)
        self.assertTrue(any(fill.reason == "settled_winning_outcome" for fill in result.fills))
        self.assertTrue(any(fill.liquidity_source == "gamma_settlement" for fill in result.fills))
        self.assertTrue(any(fill.reason == "settled_winning_outcome" for fill in strategy.seen_fills))
        self.assertGreaterEqual(len(client.settlement_calls), 1)

    def test_runner_does_not_settle_closed_market_until_outcome_prices_are_binary(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        client = SettlementClient(outcome_prices='["0.60", "0.40"]')
        runner = PaperRunner(
            client=client,
            conn=conn,
            run_id="unresolved-settlement-run",
            strategies=[BuyOncePaperStrategy()],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            market_limit=1,
            max_assets=1,
            settlement_check_seconds=0,
        )

        runner.run_once()
        runner.run_once()

        state = list(runner.agent_batch)[0]
        result = runner.results()[0]
        self.assertEqual(state.portfolio.positions, {"TOKEN-UP": 100.0})
        self.assertAlmostEqual(state.portfolio.cash, 50.0)
        self.assertFalse(any(fill.liquidity_source == "gamma_settlement" for fill in result.fills))

    def test_public_settlement_resolver_uses_condition_cache_interval(self):
        client = SettlementClient()
        resolver = PublicMarketSettlementResolver(client, check_interval_seconds=60, clock=lambda: 1000)

        first = resolver.settlement_for("0xsettle")
        second = resolver.settlement_for("0xsettle", now=1010)

        self.assertIsNotNone(first)
        self.assertEqual(first, second)
        self.assertEqual(len(client.settlement_calls), 2)

    def test_resume_restores_asset_metadata_needed_for_late_settlement(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        first_runner = PaperRunner(
            client=SettlementClient(),
            conn=conn,
            run_id="resume-settlement-run",
            strategies=[BuyOncePaperStrategy()],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            market_limit=1,
            max_assets=1,
            settlement_check_seconds=0,
        )
        first_runner.run_once()
        resumed_runner = PaperRunner(
            client=AlreadyClosedSettlementClient(),
            conn=conn,
            run_id="resume-settlement-run",
            strategies=[BuyOncePaperStrategy()],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            market_limit=1,
            max_assets=1,
            settlement_check_seconds=0,
        )

        resumed_runner.resume_from_db()
        resumed_runner.run_once()

        result = resumed_runner.results()[0]
        self.assertAlmostEqual(result.metrics["ending_equity"], 150.0)
        self.assertTrue(any(fill.reason == "settled_winning_outcome" for fill in result.fills))

    def test_runner_switches_to_pinned_only_collection_after_entry(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        client = RotatingPinnedClient()
        runner = PaperRunner(
            client=client,
            conn=conn,
            run_id="pinned-after-entry",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.10,
                    entry_notional=40,
                    min_book_imbalance=-1.0,
                    max_entry_mark_to_bid_loss_pct=0.05,
                    min_momentum_observations=1,
                    allowed_assets=["TOKEN-A"],
                )
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            market_limit=1,
            max_assets=1,
            pinned_only_after_entry=True,
        )

        runner.run(cycles=2)

        self.assertEqual(client.market_calls, 1)
        self.assertEqual(client.book_call_tokens, ["TOKEN-A", "TOKEN-A"])

    def test_runner_pins_strategy_watchlist_for_breakout_confirmation(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        client = RotatingPinnedClient()
        runner = PaperRunner(
            client=client,
            conn=conn,
            run_id="watchlist-breakout",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.10,
                    entry_notional=40,
                    min_book_imbalance=-1.0,
                    max_entry_mark_to_bid_loss_pct=0.05,
                    min_momentum_observations=2,
                    min_bid_improvement_pct=0.001,
                    min_mid_improvement_pct=0.001,
                    watchlist_size=5,
                    allowed_assets=["TOKEN-A"],
                )
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            market_limit=1,
            max_assets=1,
        )

        result = runner.run(cycles=2)[0]

        self.assertEqual(client.market_calls, 2)
        self.assertEqual(client.book_call_tokens, ["TOKEN-A", "TOKEN-B", "TOKEN-A"])
        self.assertEqual(result.metrics["filled_orders"], 1)
        self.assertEqual(result.fills[0].asset, "TOKEN-A")

    def test_runner_can_switch_to_pinned_only_after_watchlist_observation(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        client = RotatingPinnedClient()
        runner = PaperRunner(
            client=client,
            conn=conn,
            run_id="watchlist-pinned-only",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.10,
                    entry_notional=40,
                    min_book_imbalance=-1.0,
                    max_entry_mark_to_bid_loss_pct=0.05,
                    min_momentum_observations=2,
                    min_bid_improvement_pct=0.001,
                    min_mid_improvement_pct=0.001,
                    watchlist_size=5,
                    allowed_assets=["TOKEN-A"],
                )
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            market_limit=1,
            max_assets=1,
            pinned_only_after_watchlist=True,
        )

        result = runner.run(cycles=2)[0]

        self.assertEqual(client.market_calls, 1)
        self.assertEqual(client.book_call_tokens, ["TOKEN-A", "TOKEN-A"])
        self.assertEqual(result.metrics["filled_orders"], 1)

    def test_watchlist_pinned_only_periodically_restores_market_scan(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        client = RotatingPinnedClient()
        runner = PaperRunner(
            client=client,
            conn=conn,
            run_id="watchlist-rescan",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.10,
                    entry_notional=40,
                    min_book_imbalance=-1.0,
                    max_entry_mark_to_bid_loss_pct=0.05,
                    min_momentum_observations=2,
                    min_bid_improvement_pct=0.001,
                    min_mid_improvement_pct=0.001,
                    watchlist_size=5,
                    allowed_assets=["TOKEN-C"],
                )
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            market_limit=1,
            max_assets=1,
            pinned_only_after_watchlist=True,
            pinned_watchlist_rescan_cycles=2,
        )

        result = runner.run(cycles=3)[0]

        self.assertEqual(client.market_calls, 2)
        self.assertEqual(client.book_call_tokens, ["TOKEN-A", "TOKEN-A", "TOKEN-B", "TOKEN-A"])
        self.assertEqual(result.metrics["orders"], 0)

    def test_watchlist_rescan_can_add_positions_without_entry_pinned_only(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        client = RotatingPinnedClient()
        runner = PaperRunner(
            client=client,
            conn=conn,
            run_id="watchlist-rescan-active",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.10,
                    allow_take_profit_before_target=True,
                    entry_notional=10,
                    min_book_imbalance=-1.0,
                    max_spread_pct=0.15,
                    max_entry_impact_pct=0.25,
                    max_entry_mark_to_bid_loss_pct=0.12,
                    min_momentum_observations=1,
                    cooldown_cycles_after_sell=0,
                    max_positions=2,
                    watchlist_size=5,
                )
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            market_limit=1,
            max_assets=1,
            pinned_only_after_watchlist=True,
            pinned_watchlist_rescan_cycles=2,
        )

        result = runner.run(cycles=4)[0]

        buy_fills = [fill for fill in result.fills if fill.side == "BUY" and fill.status == "FILLED"]
        self.assertEqual(client.market_calls, 2)
        self.assertEqual({fill.asset for fill in buy_fills}, {"TOKEN-A", "TOKEN-B"})

    def test_paper_run_executes_basic_baselines_and_persists_outputs(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        runner = PaperRunner(
            client=FakePolymarketClient(),
            conn=conn,
            run_id="test-run",
            strategies=[
                NoTradePaperStrategy(),
                RandomMarketTakerStrategy(seed=1, trade_probability=1.0, max_notional=10),
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=1000,
            market_limit=1,
            max_assets=1,
        )
        results = runner.run(cycles=1)
        by_name = {result.strategy: result for result in results}

        self.assertEqual(by_name["paper_no_trade"].metrics["orders"], 0)
        self.assertEqual(by_name["paper_random_market_taker"].metrics["orders"], 1)
        self.assertEqual(by_name["paper_random_market_taker"].metrics["filled_orders"], 1)
        self.assertGreater(by_name["paper_random_market_taker"].metrics["fees"], 0)
        self.assertIn("max_drawdown", by_name["paper_random_market_taker"].metrics)
        self.assertIn("paper_random_market_taker", markdown_report(results))

        self.assertEqual(conn.execute("select count(*) from signals").fetchone()[0], 1)
        self.assertEqual(conn.execute("select count(*) from paper_fills").fetchone()[0], 1)
        self.assertEqual(conn.execute("select count(*) from order_book_snapshots").fetchone()[0], 1)
        self.assertEqual(conn.execute("select count(*) from portfolio_snapshots").fetchone()[0], 4)

    def test_paper_run_keeps_order_pending_until_latency_elapsed(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        runner = PaperRunner(
            client=FakePolymarketClient(),
            conn=conn,
            run_id="latency-run",
            strategies=[RandomMarketTakerStrategy(seed=1, trade_probability=1.0, max_notional=10)],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=10)),
            initial_cash=1000,
            market_limit=1,
            max_assets=1,
        )
        result = runner.run(cycles=1)[0]
        self.assertEqual(result.metrics["orders"], 1)
        self.assertEqual(result.metrics["filled_orders"], 0)
        self.assertEqual(result.metrics["pending_orders"], 1)

    def test_online_wall_time_drives_order_latency_when_book_timestamp_is_stale(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        stale_snapshot = depth_snapshot(1000, bid=0.49, bid_size=1000, ask=0.50, ask_size=1000)
        clock_values = iter([2000, 2012, 2012, 2012])
        runner = PaperRunner(
            client=None,
            conn=conn,
            run_id="wall-time-run",
            strategies=[BuyOncePaperStrategy()],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=10)),
            initial_cash=100,
            collector=StaticCollector([stale_snapshot]),
            settlement_check_seconds=-1,
            use_wall_time_timestamps=True,
            clock=lambda: next(clock_values),
        )

        results = runner.run(cycles=2)

        self.assertEqual(results[0].metrics["filled_orders"], 1)
        self.assertEqual(
            conn.execute("SELECT timestamp FROM signals WHERE run_id = ?", ("wall-time-run",)).fetchone()[0],
            2000,
        )
        self.assertEqual(
            conn.execute("SELECT timestamp FROM paper_fills WHERE run_id = ?", ("wall-time-run",)).fetchone()[0],
            2012,
        )
        snapshot_timestamps = [
            row[0]
            for row in conn.execute(
                "SELECT timestamp FROM portfolio_snapshots WHERE run_id = ? ORDER BY timestamp",
                ("wall-time-run",),
            ).fetchall()
        ]
        self.assertEqual(snapshot_timestamps[-2:], [2000, 2012])

    def test_many_agents_share_one_market_data_collection(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        client = FakePolymarketClient()
        collector = MarketDataCollector(client, market_limit=1, max_assets=1)
        strategies = [
            RandomMarketTakerStrategy(
                seed=index,
                trade_probability=1.0,
                max_notional=1,
                name=f"agent_{index:03d}",
            )
            for index in range(200)
        ]
        runner = PaperRunner(
            client=client,
            conn=conn,
            run_id="many-agents",
            strategies=strategies,
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=1000,
            market_limit=1,
            max_assets=1,
            collector=collector,
        )
        results = runner.run(cycles=1)
        self.assertEqual(len(results), 200)
        self.assertEqual(collector.collection_count, 1)
        self.assertEqual(client.book_calls, 1)
        self.assertEqual(conn.execute("select count(*) from signals").fetchone()[0], 200)
        self.assertEqual(conn.execute("select count(*) from order_book_snapshots").fetchone()[0], 1)

    def test_target_profit_strategy_reaches_10pct_roi_on_favorable_path(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        collector = SequenceCollector(
            [
                snapshot_at(1000, bid=0.49, ask=0.50),
                snapshot_at(1010, bid=0.62, ask=0.63),
                snapshot_at(1020, bid=0.40, ask=0.41),
            ]
        )
        runner = PaperRunner(
            client=FakePolymarketClient(),
            conn=conn,
            run_id="target-profit",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.10,
                    entry_notional=90,
                    min_book_imbalance=-1.0,
                    min_momentum_observations=1,
                )
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            collector=collector,
        )
        result = runner.run(cycles=3)[0]
        self.assertGreaterEqual(result.metrics["roi"], 0.10)
        self.assertAlmostEqual(result.metrics["ending_equity"], 121.6)
        self.assertEqual(result.metrics["orders"], 2)
        self.assertEqual(result.metrics["filled_orders"], 2)
        reasons = [order.signal.reason for order in result.orders]
        self.assertIn("portfolio_target_reached", reasons)

        verification = verify_target_run(
            conn,
            run_id="target-profit",
            strategy="paper_target_profit_10pct",
            target_roi=0.10,
            require_flat=True,
        )
        self.assertTrue(verification.passed)
        self.assertTrue(verification.flat)
        self.assertGreaterEqual(verification.final_roi, 0.10)

    def test_target_profit_strategy_auto_sizes_entry_for_portfolio_goal(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        collector = SequenceCollector(
            [
                snapshot_at(1000, bid=0.49, ask=0.50),
                snapshot_at(1010, bid=0.56, ask=0.57),
                snapshot_at(1020, bid=0.56, ask=0.57),
            ]
        )
        runner = PaperRunner(
            client=FakePolymarketClient(),
            conn=conn,
            run_id="target-profit-auto-size",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.10,
                    entry_notional=0,
                    capital_fraction=1.0,
                    min_book_imbalance=-1.0,
                    min_momentum_observations=1,
                )
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            collector=collector,
        )
        result = runner.run(cycles=3)[0]
        self.assertEqual(result.orders[0].signal.target_notional, 100)
        self.assertGreaterEqual(result.metrics["roi"], 0.10)

    def test_target_profit_strategy_can_compound_take_profit_exits_to_10pct(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        collector = SequenceCollector(
            [
                snapshot_at(1000, bid=0.49, ask=0.50),
                snapshot_at(1010, bid=0.536, ask=0.537),
                snapshot_at(1020, bid=0.49, ask=0.50),
                snapshot_at(1030, bid=0.537, ask=0.538),
            ]
        )
        runner = PaperRunner(
            client=FakePolymarketClient(),
            conn=conn,
            run_id="target-compound-profit",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.05,
                    allow_take_profit_before_target=True,
                    entry_notional=95,
                    min_book_imbalance=-1.0,
                    min_momentum_observations=1,
                    cooldown_cycles_after_sell=0,
                )
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            collector=collector,
        )
        result = runner.run(cycles=4)[0]
        self.assertGreaterEqual(result.metrics["roi"], 0.10)
        self.assertEqual([order.signal.side for order in result.orders], ["BUY", "SELL", "BUY", "SELL"])
        self.assertIn("take_profit_reinvest", [order.signal.reason for order in result.orders])

        verification = verify_target_run(
            conn,
            run_id="target-compound-profit",
            strategy="paper_target_profit_10pct",
            target_roi=0.10,
            require_flat=True,
        )
        self.assertTrue(verification.passed)
        self.assertTrue(verification.flat)

    def test_target_profit_strategy_compound_exit_is_fee_aware(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        fee_rules = MarketRules(fee_model=PolymarketFeeModel(fee_rate=0.05, exponent=1.0))
        collector = SequenceCollector(
            [
                snapshot_at(1000, bid=0.49, ask=0.50),
                snapshot_at(1010, bid=0.528, ask=0.529),
            ],
            rules={"TOKEN-YES": fee_rules},
        )
        runner = PaperRunner(
            client=FakePolymarketClient(),
            conn=conn,
            run_id="target-compound-fee-aware",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.03,
                    allow_take_profit_before_target=True,
                    entry_notional=95,
                    max_entry_mark_to_bid_loss_pct=0.05,
                    min_book_imbalance=-1.0,
                    min_momentum_observations=1,
                    cooldown_cycles_after_sell=0,
                )
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            collector=collector,
        )
        result = runner.run(cycles=2)[0]
        self.assertEqual([order.signal.side for order in result.orders], ["BUY"])
        self.assertEqual(result.metrics["filled_orders"], 1)
        self.assertFalse(result.metrics["roi"] >= 0.10)

    def test_target_profit_strategy_exits_stale_position_after_max_hold(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        collector = SequenceCollector(
            [
                snapshot_at(1000, bid=0.49, ask=0.50),
                snapshot_at(1010, bid=0.489, ask=0.50),
                snapshot_at(1020, bid=0.489, ask=0.50),
            ]
        )
        runner = PaperRunner(
            client=FakePolymarketClient(),
            conn=conn,
            run_id="target-max-hold-exit",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.01,
                    allow_take_profit_before_target=True,
                    entry_notional=50,
                    min_book_imbalance=-1.0,
                    min_momentum_observations=1,
                    cooldown_cycles_after_sell=0,
                    max_hold_cycles=1,
                )
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            collector=collector,
        )
        result = runner.run(cycles=3)[0]
        self.assertEqual([order.signal.side for order in result.orders], ["BUY", "SELL"])
        self.assertIn("max_hold_exit", [order.signal.reason for order in result.orders])
        self.assertEqual(result.metrics["pending_orders"], 0)

    def test_target_profit_strategy_does_not_max_hold_exit_when_progressing(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        collector = SequenceCollector(
            [
                snapshot_at(1000, bid=0.49, ask=0.50),
                snapshot_at(1010, bid=0.50, ask=0.51),
                snapshot_at(1020, bid=0.50, ask=0.51),
            ]
        )
        runner = PaperRunner(
            client=FakePolymarketClient(),
            conn=conn,
            run_id="target-max-hold-progress",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.01,
                    allow_take_profit_before_target=True,
                    entry_notional=50,
                    min_book_imbalance=-1.0,
                    min_momentum_observations=1,
                    cooldown_cycles_after_sell=0,
                    max_hold_cycles=1,
                    max_hold_min_progress_pct=0.0,
                )
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            collector=collector,
        )
        result = runner.run(cycles=3)[0]
        self.assertEqual([order.signal.side for order in result.orders], ["BUY"])
        self.assertEqual(result.metrics["pending_orders"], 0)

    def test_target_profit_strategy_can_switch_after_max_hold_exit(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        collector = BatchSequenceCollector(
            [
                [named_snapshot("TOKEN-A", 1000, bid=0.49, ask=0.50, title="Stale A")],
                [named_snapshot("TOKEN-A", 1010, bid=0.489, ask=0.50, title="Stale A")],
                [named_snapshot("TOKEN-A", 1020, bid=0.489, ask=0.50, title="Stale A")],
                [
                    named_snapshot("TOKEN-A", 1030, bid=0.49, ask=0.50, title="Still cooling A"),
                    named_snapshot("TOKEN-B", 1030, bid=0.49, ask=0.50, title="Fresh B"),
                ],
            ]
        )
        runner = PaperRunner(
            client=FakePolymarketClient(),
            conn=conn,
            run_id="target-max-hold-switch",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.01,
                    allow_take_profit_before_target=True,
                    entry_notional=50,
                    min_book_imbalance=-1.0,
                    min_momentum_observations=1,
                    cooldown_cycles_after_sell=0,
                    max_hold_cycles=1,
                    max_hold_cooldown_cycles=3,
                )
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            collector=collector,
        )
        result = runner.run(cycles=4)[0]
        self.assertEqual([order.signal.side for order in result.orders], ["BUY", "SELL", "BUY"])
        self.assertEqual([order.signal.asset for order in result.orders], ["TOKEN-A", "TOKEN-A", "TOKEN-B"])

    def test_target_profit_strategy_rotates_unchanged_position_when_min_progress_required(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        collector = BatchSequenceCollector(
            [
                [named_snapshot("TOKEN-A", 1000, bid=0.49, ask=0.50, title="Stale A")],
                [named_snapshot("TOKEN-A", 1010, bid=0.49, ask=0.50, title="Stale A")],
                [named_snapshot("TOKEN-A", 1020, bid=0.49, ask=0.50, title="Stale A")],
                [
                    named_snapshot("TOKEN-A", 1030, bid=0.49, ask=0.50, title="Still cooling A"),
                    named_snapshot("TOKEN-B", 1030, bid=0.49, ask=0.50, title="Fresh B"),
                ],
            ]
        )
        runner = PaperRunner(
            client=FakePolymarketClient(),
            conn=conn,
            run_id="target-min-progress-rotation",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.10,
                    allow_take_profit_before_target=True,
                    entry_notional=50,
                    min_book_imbalance=-1.0,
                    min_momentum_observations=1,
                    cooldown_cycles_after_sell=0,
                    max_hold_cycles=1,
                    max_hold_min_progress_pct=0.10,
                    max_hold_cooldown_cycles=3,
                )
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            collector=collector,
        )
        result = runner.run(cycles=4)[0]

        self.assertEqual([order.signal.side for order in result.orders], ["BUY", "SELL", "BUY"])
        self.assertEqual([order.signal.asset for order in result.orders], ["TOKEN-A", "TOKEN-A", "TOKEN-B"])

    def test_target_profit_strategy_uses_maker_exit_for_stale_maker_position(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        collector = SequenceCollector(
            [
                snapshot_at(1000, bid=0.49, ask=0.50),
                snapshot_at(1010, bid=0.49, ask=0.50),
                snapshot_at(1020, bid=0.49, ask=0.50),
                snapshot_at(1030, bid=0.49, ask=0.50),
            ]
        )
        runner = PaperRunner(
            client=FakePolymarketClient(),
            conn=conn,
            run_id="target-maker-stale-exit",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.10,
                    allow_take_profit_before_target=True,
                    entry_notional=50,
                    min_book_imbalance=-1.0,
                    min_momentum_observations=1,
                    cooldown_cycles_after_sell=0,
                    max_hold_cycles=1,
                    max_hold_min_progress_pct=0.10,
                    max_hold_cooldown_cycles=3,
                    entry_execution_style="maker",
                )
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            collector=collector,
        )
        result = runner.run(cycles=4)[0]

        sell_order = [order for order in result.orders if order.signal.side == "SELL"][0]
        sell_fill = [fill for fill in result.fills if fill.side == "SELL"][0]
        self.assertEqual(sell_order.signal.execution_style, "maker")
        self.assertEqual(sell_order.signal.limit_price, 0.50)
        self.assertFalse(sell_fill.taker)
        self.assertEqual(sell_fill.reason, "passive_ask_fill_proxy")

    def test_target_profit_strategy_skips_wide_spreads(self):
        strategy = TargetProfitPaperStrategy(
            initial_cash=100,
            portfolio_target_roi=0.10,
            take_profit_pct=0.10,
            entry_notional=0,
            max_spread_pct=0.05,
        )
        signals = strategy.on_snapshot(snapshot_at(1000, bid=0.40, ask=0.50), portfolio=Portfolio(100))
        self.assertEqual(signals, [])

    def test_target_profit_strategy_skips_high_market_impact_entries(self):
        strategy = TargetProfitPaperStrategy(
            initial_cash=100,
            portfolio_target_roi=0.10,
            take_profit_pct=0.10,
            entry_notional=100,
            max_spread_pct=0.05,
            max_entry_impact_pct=0.05,
        )
        snapshot = MarketSnapshot(
            asset="TOKEN-YES",
            condition_id="0xcondition",
            timestamp=1000,
            book=OrderBook(
                asset="TOKEN-YES",
                timestamp=1000,
                bids=(BookLevel(price=0.49, size=1000),),
                asks=(BookLevel(price=0.50, size=5), BookLevel(price=0.80, size=1000)),
            ),
            title="High impact fixture",
            outcome="Yes",
        )
        signals = strategy.on_snapshot(snapshot, portfolio=Portfolio(100))
        self.assertEqual(signals, [])

    def test_target_profit_strategy_selects_best_viable_candidate_per_cycle(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        weak = named_snapshot("TOKEN-WEAK", 1000, bid=0.79, ask=0.80, title="Weak headroom")
        strong = named_snapshot("TOKEN-STRONG", 1000, bid=0.49, ask=0.50, title="Strong headroom")
        runner = PaperRunner(
            client=FakePolymarketClient(),
            conn=conn,
            run_id="target-best-candidate",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.10,
                    entry_notional=100,
                    capital_fraction=1.0,
                    min_book_imbalance=-1.0,
                    min_momentum_observations=1,
                )
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            collector=StaticCollector([weak, strong]),
        )
        result = runner.run(cycles=1)[0]
        self.assertEqual(result.orders[0].signal.asset, "TOKEN-STRONG")

    def test_target_profit_strategy_can_weight_history_momentum(self):
        low_history = replace(
            named_snapshot("TOKEN-A", 1000, bid=0.50, ask=0.51, title="Low history"),
            history_change_pct=0.01,
        )
        high_history = replace(
            named_snapshot("TOKEN-B", 1000, bid=0.50, ask=0.51, title="High history"),
            history_change_pct=0.08,
        )
        strategy = TargetProfitPaperStrategy(
            initial_cash=100,
            portfolio_target_roi=0.10,
            take_profit_pct=0.10,
            entry_notional=20,
            min_book_imbalance=-1.0,
            max_entry_mark_to_bid_loss_pct=0.05,
            min_momentum_observations=1,
            history_change_weight=10.0,
        )

        signals = strategy.on_snapshots([low_history, high_history], Portfolio(100))

        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].asset, "TOKEN-B")

    def test_target_profit_strategy_can_emit_maker_entry_signal(self):
        strategy = TargetProfitPaperStrategy(
            initial_cash=100,
            portfolio_target_roi=0.10,
            take_profit_pct=0.10,
            entry_notional=20,
            min_book_imbalance=-1.0,
            max_entry_mark_to_bid_loss_pct=0.01,
            min_momentum_observations=1,
            entry_execution_style="maker",
        )

        signals = strategy.on_snapshot(snapshot_at(1000, bid=0.49, ask=0.50), Portfolio(100))

        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].execution_style, "maker")
        self.assertEqual(signals[0].limit_price, 0.49)

    def test_target_maker_partial_fill_keeps_residual_pending(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        strategy = TargetProfitPaperStrategy(
            initial_cash=100,
            portfolio_target_roi=0.10,
            take_profit_pct=0.10,
            entry_notional=50,
            min_book_imbalance=-1.0,
            min_momentum_observations=1,
            entry_execution_style="maker",
        )
        runner = PaperRunner(
            client=None,
            conn=conn,
            run_id="target-maker-partial-residual",
            strategies=[strategy],
            fill_model=ConservativeFillModel(
                latency_model=LatencyModel(execution_delay_seconds=0),
                maker_fill_mode="queue_proxy",
                maker_queue_ahead_fraction=0.0,
                maker_queue_decay=1.0,
            ),
            initial_cash=100,
            collector=SequenceCollector(
                [
                    snapshot_at(1000, bid=0.49, ask=0.50, bid_size=1000),
                    snapshot_at(1001, bid=0.49, ask=0.50, bid_size=20),
                    snapshot_at(1002, bid=0.49, ask=0.50, bid_size=100),
                ]
            ),
        )

        result = runner.run(cycles=3)[0]

        buy_fills = [fill for fill in result.fills if fill.side == "BUY"]
        self.assertEqual([fill.status for fill in buy_fills], ["PARTIAL", "FILLED"])
        self.assertEqual(buy_fills[0].order_id, buy_fills[1].order_id)
        self.assertAlmostEqual(buy_fills[0].notional, 9.8)
        self.assertAlmostEqual(buy_fills[1].notional, 40.2)
        self.assertEqual(result.metrics["pending_orders"], 0.0)
        self.assertEqual(strategy.pending_assets, {})
        self.assertAlmostEqual(strategy.avg_cost_by_asset["TOKEN-YES"], 0.49)
        self.assertAlmostEqual(
            strategy.position_shares_by_asset["TOKEN-YES"],
            result.orders[0].signal.target_notional / 0.49,
        )

    def test_target_profit_strategy_can_build_multiple_positions_when_allowed(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        snapshots = [
            named_snapshot("TOKEN-A", 1000, bid=0.49, ask=0.50, title="Target fixture A"),
            named_snapshot("TOKEN-B", 1000, bid=0.49, ask=0.50, title="Target fixture B"),
        ]
        runner = PaperRunner(
            client=None,
            conn=conn,
            run_id="target-multi-position",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=200,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.10,
                    allow_take_profit_before_target=True,
                    entry_notional=50,
                    min_book_imbalance=-1.0,
                    min_momentum_observations=1,
                    max_positions=2,
                )
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=200,
            collector=BatchSequenceCollector([snapshots, snapshots]),
        )
        result = runner.run(cycles=2)[0]

        buy_fills = [fill for fill in result.fills if fill.side == "BUY" and fill.status == "FILLED"]
        self.assertEqual(len(buy_fills), 2)
        self.assertEqual({fill.asset for fill in buy_fills}, {"TOKEN-A", "TOKEN-B"})

    def test_target_profit_strategy_can_enter_multiple_positions_per_cycle(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        snapshots = [
            named_snapshot("TOKEN-A", 1000, bid=0.49, ask=0.50, title="Target fixture A"),
            named_snapshot("TOKEN-B", 1000, bid=0.49, ask=0.50, title="Target fixture B"),
            named_snapshot("TOKEN-C", 1000, bid=0.49, ask=0.50, title="Target fixture C"),
        ]
        runner = PaperRunner(
            client=None,
            conn=conn,
            run_id="target-multi-entry-cycle",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=120,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.10,
                    allow_take_profit_before_target=True,
                    entry_notional=40,
                    min_book_imbalance=-1.0,
                    min_momentum_observations=1,
                    max_positions=3,
                    max_entries_per_cycle=2,
                )
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=120,
            collector=StaticCollector(snapshots),
        )
        result = runner.run(cycles=1)[0]

        buy_fills = [fill for fill in result.fills if fill.side == "BUY" and fill.status == "FILLED"]
        self.assertEqual(len(buy_fills), 2)
        self.assertEqual({fill.asset for fill in buy_fills}, {"TOKEN-A", "TOKEN-B"})

    def test_target_profit_strategy_diversifies_by_title_prefix(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        snapshots = [
            named_snapshot("BTC-A", 1000, bid=0.49, ask=0.50, title="Bitcoin Up or Down - Window A"),
            named_snapshot("BTC-B", 1000, bid=0.49, ask=0.50, title="Bitcoin Up or Down - Window B"),
            named_snapshot("ETH-A", 1000, bid=0.49, ask=0.50, title="Ethereum Up or Down - Window A"),
        ]
        runner = PaperRunner(
            client=None,
            conn=conn,
            run_id="target-diversify-prefix",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=300,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.10,
                    allow_take_profit_before_target=True,
                    entry_notional=50,
                    min_book_imbalance=-1.0,
                    min_momentum_observations=1,
                    max_positions=3,
                    diversify_by="title_prefix",
                    max_positions_per_group=1,
                )
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=300,
            collector=BatchSequenceCollector([snapshots, snapshots, snapshots]),
        )
        result = runner.run(cycles=3)[0]

        buy_fills = [fill for fill in result.fills if fill.side == "BUY" and fill.status == "FILLED"]
        self.assertEqual(len(buy_fills), 2)
        self.assertEqual({fill.asset for fill in buy_fills}, {"BTC-A", "ETH-A"})

    def test_target_profit_strategy_waits_for_positive_momentum_before_entry(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        collector = SequenceCollector(
            [
                snapshot_at(1000, bid=0.49, ask=0.50),
                snapshot_at(1010, bid=0.50, ask=0.51),
            ]
        )
        runner = PaperRunner(
            client=FakePolymarketClient(),
            conn=conn,
            run_id="target-momentum-entry",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.10,
                    entry_notional=50,
                    min_book_imbalance=-1.0,
                    min_momentum_observations=2,
                    min_bid_improvement_pct=0.001,
                    min_mid_improvement_pct=0.001,
                )
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            collector=collector,
        )
        result = runner.run(cycles=2)[0]
        self.assertEqual(result.metrics["orders"], 1)
        self.assertEqual(result.orders[0].created_at, 1010)
        self.assertIn("target_opportunity_momentum", result.orders[0].signal.reason)

    def test_target_profit_strategy_rejects_negative_momentum(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        collector = SequenceCollector(
            [
                snapshot_at(1000, bid=0.50, ask=0.51),
                snapshot_at(1010, bid=0.49, ask=0.50),
            ]
        )
        runner = PaperRunner(
            client=FakePolymarketClient(),
            conn=conn,
            run_id="target-negative-momentum",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.10,
                    entry_notional=50,
                    min_book_imbalance=-1.0,
                    min_momentum_observations=2,
                    min_bid_improvement_pct=0.001,
                    min_mid_improvement_pct=0.001,
                )
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            collector=collector,
        )
        result = runner.run(cycles=2)[0]
        self.assertEqual(result.metrics["orders"], 0)
        reasons = [
            row[0]
            for row in conn.execute(
                """
                SELECT reason
                FROM strategy_diagnostics
                WHERE run_id = ? AND strategy = ?
                ORDER BY timestamp
                """,
                ("target-negative-momentum", "paper_target_profit_10pct"),
            ).fetchall()
        ]
        self.assertIn("momentum_no_previous_observation", reasons)
        self.assertIn("momentum_bid_not_improving", reasons)

    def test_target_profit_strategy_persists_scoring_diagnostics(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        collector = SequenceCollector(
            [snapshot_at(1000, bid=0.49, ask=0.50)],
            rules={"TOKEN-YES": MarketRules(fee_model=PolymarketFeeModel(fee_rate=0.05, exponent=1.0))},
        )
        runner = PaperRunner(
            client=FakePolymarketClient(),
            conn=conn,
            run_id="target-score-diagnostics",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.10,
                    entry_notional=95,
                    stop_loss_pct=0.03,
                    min_book_imbalance=-1.0,
                    min_momentum_observations=1,
                )
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            collector=collector,
        )

        result = runner.run(cycles=1)[0]

        self.assertEqual(result.metrics["orders"], 0)
        row = conn.execute(
            """
            SELECT reason, score, raw_json
            FROM strategy_diagnostics
            WHERE run_id = ? AND strategy = ?
            """,
            ("target-score-diagnostics", "paper_target_profit_10pct"),
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "entry_mark_to_bid_loss_too_high")
        self.assertIsNotNone(row[1])
        self.assertIn("entry_mark_to_bid_loss_pct", row[2])

    def test_target_profit_strategy_skips_entries_already_inside_stop_loss(self):
        strategy = TargetProfitPaperStrategy(
            initial_cash=100,
            portfolio_target_roi=0.10,
            take_profit_pct=0.10,
            stop_loss_pct=0.03,
            entry_notional=95,
            min_book_imbalance=-1.0,
            min_momentum_observations=1,
        )
        rules = {"TOKEN-YES": MarketRules(fee_model=PolymarketFeeModel(fee_rate=0.05, exponent=1.0))}
        signals = strategy.on_snapshots([snapshot_at(1000, bid=0.49, ask=0.50)], Portfolio(100), rules_by_asset=rules)
        self.assertEqual(signals, [])

    def test_target_profit_strategy_exits_on_stop_loss(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        collector = SequenceCollector(
            [
                snapshot_at(1000, bid=0.49, ask=0.50),
                snapshot_at(1010, bid=0.47, ask=0.48),
            ]
        )
        runner = PaperRunner(
            client=FakePolymarketClient(),
            conn=conn,
            run_id="target-stop-loss",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.10,
                    stop_loss_pct=0.03,
                    entry_notional=50,
                    min_book_imbalance=-1.0,
                    min_momentum_observations=1,
                )
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            collector=collector,
        )
        result = runner.run(cycles=2)[0]
        self.assertEqual(result.metrics["orders"], 2)
        self.assertEqual(result.metrics["filled_orders"], 2)
        self.assertIn("stop_loss", [order.signal.reason for order in result.orders])
        self.assertEqual(result.metrics["pending_orders"], 0)

    def test_target_profit_strategy_cools_down_after_sell(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        collector = SequenceCollector(
            [
                snapshot_at(1000, bid=0.49, ask=0.50),
                snapshot_at(1010, bid=0.47, ask=0.48),
                snapshot_at(1020, bid=0.50, ask=0.51),
            ]
        )
        runner = PaperRunner(
            client=FakePolymarketClient(),
            conn=conn,
            run_id="target-cooldown",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.10,
                    stop_loss_pct=0.03,
                    entry_notional=50,
                    min_book_imbalance=-1.0,
                    min_momentum_observations=1,
                    cooldown_cycles_after_sell=2,
                )
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            collector=collector,
        )
        result = runner.run(cycles=3)[0]
        self.assertEqual(result.metrics["orders"], 2)
        self.assertEqual([order.signal.side for order in result.orders], ["BUY", "SELL"])

    def test_target_profit_strategy_global_cooldown_blocks_new_asset_after_sell(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        collector = BatchSequenceCollector(
            [
                [named_snapshot("TOKEN-A", 1000, bid=0.49, ask=0.50, title="Entry")],
                [named_snapshot("TOKEN-A", 1010, bid=0.47, ask=0.48, title="Stop")],
                [named_snapshot("TOKEN-B", 1020, bid=0.50, ask=0.51, title="Other candidate")],
            ]
        )
        runner = PaperRunner(
            client=FakePolymarketClient(),
            conn=conn,
            run_id="target-global-cooldown",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.10,
                    stop_loss_pct=0.03,
                    entry_notional=50,
                    min_book_imbalance=-1.0,
                    min_momentum_observations=1,
                    cooldown_cycles_after_sell=2,
                )
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            collector=collector,
        )
        result = runner.run(cycles=3)[0]
        self.assertEqual(result.metrics["orders"], 2)
        self.assertEqual([order.signal.asset for order in result.orders], ["TOKEN-A", "TOKEN-A"])

    def test_target_profit_strategy_rejects_score_below_minimum(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        collector = SequenceCollector([snapshot_at(1000, bid=0.49, ask=0.50)])
        runner = PaperRunner(
            client=FakePolymarketClient(),
            conn=conn,
            run_id="target-min-score",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.10,
                    entry_notional=100,
                    min_book_imbalance=-1.0,
                    min_momentum_observations=1,
                    required_exit_distance_weight=10.0,
                    min_score=0.0,
                )
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            collector=collector,
        )
        result = runner.run(cycles=1)[0]
        self.assertEqual(result.metrics["orders"], 0)

    def test_target_profit_strategy_only_enters_allowed_assets(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        collector = StaticCollector(
            [
                named_snapshot("TOKEN-A", 1000, bid=0.49, ask=0.50, title="Blocked"),
                named_snapshot("TOKEN-B", 1000, bid=0.49, ask=0.50, title="Allowed"),
            ]
        )
        runner = PaperRunner(
            client=FakePolymarketClient(),
            conn=conn,
            run_id="target-allowed-assets",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.10,
                    entry_notional=50,
                    min_book_imbalance=-1.0,
                    min_momentum_observations=1,
                    allowed_assets=["TOKEN-B"],
                )
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            collector=collector,
        )
        result = runner.run(cycles=1)[0]
        self.assertEqual(result.metrics["orders"], 1)
        self.assertEqual(result.orders[0].signal.asset, "TOKEN-B")

    def test_target_profit_strategy_requires_positive_book_imbalance(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        collector = SequenceCollector(
            [
                depth_snapshot(1000, bid=0.49, bid_size=100, ask=0.50, ask_size=1000),
                depth_snapshot(1010, bid=0.50, bid_size=100, ask=0.51, ask_size=1000),
            ]
        )
        runner = PaperRunner(
            client=FakePolymarketClient(),
            conn=conn,
            run_id="target-weak-imbalance",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.10,
                    entry_notional=50,
                    min_book_imbalance=0.05,
                    min_momentum_observations=2,
                    min_bid_improvement_pct=0.001,
                    min_mid_improvement_pct=0.001,
                )
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            collector=collector,
        )
        result = runner.run(cycles=2)[0]
        self.assertEqual(result.metrics["orders"], 0)

    def test_target_profit_strategy_accepts_positive_book_imbalance(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        collector = SequenceCollector(
            [
                depth_snapshot(1000, bid=0.49, bid_size=1000, ask=0.50, ask_size=100),
                depth_snapshot(1010, bid=0.50, bid_size=1000, ask=0.51, ask_size=100),
            ]
        )
        runner = PaperRunner(
            client=FakePolymarketClient(),
            conn=conn,
            run_id="target-strong-imbalance",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.10,
                    entry_notional=50,
                    min_book_imbalance=0.05,
                    min_momentum_observations=2,
                    min_bid_improvement_pct=0.001,
                    min_mid_improvement_pct=0.001,
                )
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            collector=collector,
        )
        result = runner.run(cycles=2)[0]
        self.assertEqual(result.metrics["orders"], 1)
        self.assertIn("imbalance=", result.orders[0].signal.reason)


if __name__ == "__main__":
    unittest.main()
