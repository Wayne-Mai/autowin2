import sqlite3
import unittest

from polypaper.models import BookLevel, MarketSnapshot, OrderBook
from polypaper.cli import _resume_gate_offsets
from polypaper.paper import CollectionResult, PaperRunner
from polypaper.simulator import ConservativeFillModel, LatencyModel, MarketRules
from polypaper.storage import init_db, insert_portfolio_snapshot, upsert_paper_run
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


def make_runner(conn, run_id, snapshots, entry_notional=90):
    return PaperRunner(
        client=None,
        conn=conn,
        run_id=run_id,
        strategies=[
            TargetProfitPaperStrategy(
                initial_cash=100,
                portfolio_target_roi=0.10,
                take_profit_pct=0.10,
                entry_notional=entry_notional,
                min_book_imbalance=-1.0,
                min_momentum_observations=1,
            )
        ],
        fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
        initial_cash=100,
        collector=SequenceCollector(snapshots),
    )


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
        self.assertEqual([item.strategy for item in result.latest_verifications], ["paper_target_profit_10pct"])

    def test_run_until_target_can_require_min_cycles_before_pass(self):
        conn, runner = runner_for(
            [
                snapshot_at(1000, bid=0.49, ask=0.50),
                snapshot_at(1010, bid=0.62, ask=0.63),
                snapshot_at(1020, bid=0.62, ask=0.63),
            ]
        )
        result = run_until_target(
            runner=runner,
            conn=conn,
            run_id="target-until",
            strategy_names=["paper_target_profit_10pct"],
            target_roi=0.10,
            max_cycles=3,
            min_cycles_before_pass=3,
            require_flat=True,
            sleeper=lambda seconds: None,
        )
        self.assertTrue(result.passed)
        self.assertEqual(result.cycles_completed, 3)
        self.assertGreaterEqual(result.best_verification.final_roi, 0.10)

    def test_run_until_target_counts_resume_cycles_toward_min_cycles(self):
        conn, runner = runner_for(
            [
                snapshot_at(1000, bid=0.49, ask=0.50),
                snapshot_at(1010, bid=0.62, ask=0.63),
            ]
        )
        result = run_until_target(
            runner=runner,
            conn=conn,
            run_id="target-until",
            strategy_names=["paper_target_profit_10pct"],
            target_roi=0.10,
            max_cycles=2,
            min_cycles_before_pass=3,
            initial_cycles_completed=1,
            require_flat=True,
            sleeper=lambda seconds: None,
        )
        self.assertTrue(result.passed)
        self.assertEqual(result.cycles_completed, 3)

    def test_run_until_target_counts_resume_runtime_toward_min_elapsed(self):
        conn, runner = runner_for(
            [
                snapshot_at(1000, bid=0.49, ask=0.50),
                snapshot_at(1010, bid=0.62, ask=0.63),
            ]
        )
        times = iter([100.0, 101.0, 102.0])
        result = run_until_target(
            runner=runner,
            conn=conn,
            run_id="target-until",
            strategy_names=["paper_target_profit_10pct"],
            target_roi=0.10,
            max_cycles=2,
            min_elapsed_seconds_before_pass=60.0,
            initial_elapsed_seconds=59.5,
            require_flat=True,
            sleeper=lambda seconds: None,
            clock=lambda: next(times),
        )
        self.assertTrue(result.passed)
        self.assertEqual(result.cycles_completed, 2)

    def test_resume_gate_offsets_prefers_paper_run_wall_clock_elapsed(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        upsert_paper_run(
            conn,
            "resume-run",
            "online_target",
            {"cycles_completed": 12},
            timestamp=100,
        )
        upsert_paper_run(conn, "resume-run", "online_target", {}, timestamp=160)
        insert_portfolio_snapshot(conn, "resume-run", "paper_target_a", 1000, 100.0, 100.0, {})
        insert_portfolio_snapshot(conn, "resume-run", "paper_target_a", 50000, 111.0, 111.0, {})

        cycles, elapsed = _resume_gate_offsets(conn, "resume-run")

        self.assertEqual(cycles, 12)
        self.assertEqual(elapsed, 60.0)

    def test_run_until_target_does_not_pass_before_min_cycles(self):
        conn, runner = runner_for(
            [
                snapshot_at(1000, bid=0.49, ask=0.50),
                snapshot_at(1010, bid=0.62, ask=0.63),
            ]
        )
        result = run_until_target(
            runner=runner,
            conn=conn,
            run_id="target-until",
            strategy_names=["paper_target_profit_10pct"],
            target_roi=0.10,
            max_cycles=2,
            min_cycles_before_pass=3,
            require_flat=True,
            sleeper=lambda seconds: None,
        )
        self.assertFalse(result.passed)
        self.assertEqual(result.cycles_completed, 2)
        self.assertIsNotNone(result.best_verification)
        self.assertTrue(result.best_verification.passed)

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
        self.assertEqual(result.latest_verifications[0].reason, "final_roi_below_target")

    def test_run_until_target_invokes_cycle_callback(self):
        conn, runner = runner_for(
            [
                snapshot_at(1000, bid=0.49, ask=0.50),
                snapshot_at(1010, bid=0.62, ask=0.63),
            ]
        )
        calls = []

        def on_cycle(cycles_completed, latest_verifications, best_verification, passed):
            calls.append(
                (
                    cycles_completed,
                    [item.strategy for item in latest_verifications],
                    best_verification.strategy if best_verification else None,
                    passed,
                )
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
            on_cycle=on_cycle,
        )

        self.assertTrue(result.passed)
        self.assertEqual(
            calls,
            [
                (1, ["paper_target_profit_10pct"], "paper_target_profit_10pct", False),
                (2, ["paper_target_profit_10pct"], "paper_target_profit_10pct", True),
            ],
        )

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
        self.assertEqual(
            [item.strategy for item in result.latest_verifications],
            ["paper_target_strict", "paper_target_relaxed"],
        )
        self.assertEqual(collector.collection_count, 2)

    def test_run_until_target_can_require_multiple_passing_strategies(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        collector = SequenceCollector(
            [
                snapshot_at(1000, bid=0.49, ask=0.50),
                snapshot_at(1010, bid=0.62, ask=0.63),
            ]
        )
        runner = PaperRunner(
            client=None,
            conn=conn,
            run_id="target-two-required",
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
            run_id="target-two-required",
            strategy_names=["paper_target_strict", "paper_target_relaxed"],
            target_roi=0.10,
            max_cycles=2,
            min_passing_strategies=2,
            require_flat=True,
            sleeper=lambda seconds: None,
        )

        self.assertFalse(result.passed)
        self.assertEqual(result.cycles_completed, 2)
        self.assertIsNotNone(result.best_verification)
        self.assertTrue(result.best_verification.passed)
        self.assertEqual(sum(item.passed for item in result.latest_verifications), 1)

    def test_run_until_target_passes_when_multiple_strategies_reach_target(self):
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
            run_id="target-two-pass",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.10,
                    entry_notional=90,
                    min_book_imbalance=-1.0,
                    min_momentum_observations=1,
                    name="paper_target_relaxed_a",
                ),
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.10,
                    entry_notional=80,
                    min_book_imbalance=-1.0,
                    min_momentum_observations=1,
                    name="paper_target_relaxed_b",
                ),
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            collector=collector,
        )

        result = run_until_target(
            runner=runner,
            conn=conn,
            run_id="target-two-pass",
            strategy_names=["paper_target_relaxed_a", "paper_target_relaxed_b"],
            target_roi=0.10,
            max_cycles=3,
            min_passing_strategies=2,
            require_flat=True,
            sleeper=lambda seconds: None,
        )

        self.assertTrue(result.passed)
        self.assertEqual(result.cycles_completed, 2)
        self.assertEqual(sum(item.passed for item in result.latest_verifications), 2)

    def test_run_until_target_can_require_multiple_passing_families(self):
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
            run_id="target-two-family-pass",
            strategies=[
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.10,
                    entry_notional=90,
                    min_book_imbalance=-1.0,
                    min_momentum_observations=1,
                    name="paper_target_spread_capture_maker_grid_01",
                ),
                TargetProfitPaperStrategy(
                    initial_cash=100,
                    portfolio_target_roi=0.10,
                    take_profit_pct=0.10,
                    entry_notional=80,
                    min_book_imbalance=-1.0,
                    min_momentum_observations=1,
                    name="paper_target_spread_capture_maker_grid_02",
                ),
            ],
            fill_model=ConservativeFillModel(latency_model=LatencyModel(execution_delay_seconds=0)),
            initial_cash=100,
            collector=collector,
        )

        result = run_until_target(
            runner=runner,
            conn=conn,
            run_id="target-two-family-pass",
            strategy_names=[
                "paper_target_spread_capture_maker_grid_01",
                "paper_target_spread_capture_maker_grid_02",
            ],
            target_roi=0.10,
            max_cycles=3,
            min_passing_strategies=2,
            min_passing_families=2,
            require_flat=True,
            sleeper=lambda seconds: None,
        )

        self.assertFalse(result.passed)
        self.assertEqual(sum(item.passed for item in result.latest_verifications), 2)

    def test_resume_from_db_continues_existing_position_until_target(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        first_runner = make_runner(
            conn,
            "resume-target",
            [snapshot_at(1000, bid=0.49, ask=0.50)],
            entry_notional=90,
        )
        first_runner.run_once()

        resumed_runner = make_runner(
            conn,
            "resume-target",
            [snapshot_at(1010, bid=0.62, ask=0.63)],
            entry_notional=90,
        )
        resumed_runner.resume_from_db()
        result = run_until_target(
            runner=resumed_runner,
            conn=conn,
            run_id="resume-target",
            strategy_names=["paper_target_profit_10pct"],
            target_roi=0.10,
            max_cycles=1,
            require_flat=True,
            sleeper=lambda seconds: None,
        )

        self.assertTrue(result.passed)
        self.assertEqual(result.cycles_completed, 1)
        self.assertEqual(result.best_verification.strategy, "paper_target_profit_10pct")
        self.assertEqual(result.best_verification.final_positions, {})
        self.assertGreater(result.best_verification.final_roi, 0.10)


if __name__ == "__main__":
    unittest.main()
