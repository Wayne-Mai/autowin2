import sqlite3
import unittest

from polypaper.models import BookLevel, MarketSnapshot, OrderBook, Portfolio
from polypaper.paper import (
    CollectionResult,
    MarketDataCollector,
    PaperRunner,
)
from polypaper.report import markdown_report
from polypaper.simulator import ConservativeFillModel, LatencyModel, MarketRules, PolymarketFeeModel
from polypaper.storage import init_db
from polypaper.strategies.paper import NoTradePaperStrategy, RandomMarketTakerStrategy, TargetProfitPaperStrategy
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


def snapshot_at(timestamp, bid, ask):
    return MarketSnapshot(
        asset="TOKEN-YES",
        condition_id="0xcondition",
        timestamp=timestamp,
        book=OrderBook(
            asset="TOKEN-YES",
            timestamp=timestamp,
            bids=(BookLevel(price=bid, size=1000),),
            asks=(BookLevel(price=ask, size=1000),),
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

    def test_market_collector_skips_tokens_with_book_errors(self):
        client = FlakyBookClient()
        collector = MarketDataCollector(client, market_limit=1, max_assets=2)

        collection = collector.collect()

        self.assertEqual([snapshot.asset for snapshot in collection.snapshots], ["TOKEN-GOOD"])
        self.assertEqual(client.book_calls, 2)

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
