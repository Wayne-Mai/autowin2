import sqlite3
import unittest

from polypaper.models import BookLevel, MarketSnapshot, OrderBook
from polypaper.paper import CollectionResult, PaperRunner
from polypaper.simulator import ConservativeFillModel, LatencyModel, MarketRules
from polypaper.storage import init_db
from polypaper.strategies.paper import TargetProfitPaperStrategy
from polypaper.target_runner import run_until_target


class SequenceCollector:
    def __init__(self, snapshots):
        self.snapshots = list(snapshots)
        self.collection_count = 0

    def collect(self):
        index = min(self.collection_count, len(self.snapshots) - 1)
        snapshot = self.snapshots[index]
        self.collection_count += 1
        return CollectionResult(snapshots=[snapshot], rules_by_asset={snapshot.asset: MarketRules()})


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
    )


def runner_for(snapshots):
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    runner = PaperRunner(
        client=None,
        conn=conn,
        run_id="target-until",
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
        collector=SequenceCollector(snapshots),
    )
    return conn, runner


class TargetRunnerTests(unittest.TestCase):
    def test_run_until_target_stops_after_verified_roi(self):
        conn, runner = runner_for(
            [
                snapshot_at(1000, bid=0.49, ask=0.50),
                snapshot_at(1010, bid=0.62, ask=0.63),
                snapshot_at(1020, bid=0.40, ask=0.41),
            ]
        )
        result = run_until_target(
            runner=runner,
            conn=conn,
            run_id="target-until",
            strategy_names=["paper_target_profit_10pct"],
            target_roi=0.10,
            max_cycles=3,
            require_flat=True,
            sleeper=lambda seconds: None,
        )
        self.assertTrue(result.passed)
        self.assertEqual(result.cycles_completed, 2)
        self.assertIsNotNone(result.best_verification)
        self.assertGreaterEqual(result.best_verification.final_roi, 0.10)

    def test_run_until_target_returns_failure_after_max_cycles(self):
        conn, runner = runner_for(
            [
                snapshot_at(1000, bid=0.49, ask=0.50),
                snapshot_at(1010, bid=0.50, ask=0.51),
            ]
        )
        result = run_until_target(
            runner=runner,
            conn=conn,
            run_id="target-until",
            strategy_names=["paper_target_profit_10pct"],
            target_roi=0.10,
            max_cycles=2,
            require_flat=True,
            sleeper=lambda seconds: None,
        )
        self.assertFalse(result.passed)
        self.assertEqual(result.cycles_completed, 2)
        self.assertIsNotNone(result.best_verification)
        self.assertLess(result.best_verification.final_roi, 0.10)

    def test_run_until_target_tracks_winning_strategy_across_variants(self):
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
            client=None,
            conn=conn,
            run_id="target-variants",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.10,
                    entry_notional=90,
                    min_book_imbalance=1.0,
                    min_momentum_observations=1,
                    name="paper_target_strict",
                ),
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.10,
                    entry_notional=90,
                    min_book_imbalance=-1.0,
                    min_momentum_observations=1,
                    name="paper_target_relaxed",
                ),
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            collector=collector,
        )
        result = run_until_target(
            runner=runner,
            conn=conn,
            run_id="target-variants",
            strategy_names=["paper_target_strict", "paper_target_relaxed"],
            target_roi=0.10,
            max_cycles=3,
            require_flat=True,
            sleeper=lambda seconds: None,
        )
        self.assertTrue(result.passed)
        self.assertEqual(result.best_verification.strategy, "paper_target_relaxed")
        self.assertEqual(collector.collection_count, 2)


if __name__ == "__main__":
    unittest.main()
