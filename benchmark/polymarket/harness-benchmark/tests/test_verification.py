import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from polypaper.online_status import format_online_goal_status, online_goal_status_from_path
from polypaper.storage import init_db, insert_portfolio_snapshot, upsert_paper_run
from polypaper.verification import verify_online_goal, verify_target_run


class VerificationCliTests(unittest.TestCase):
    def test_verify_target_cli_passes_and_fails_from_sqlite_roi(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "paper.sqlite"
            conn = sqlite3.connect(db_path)
            init_db(conn)
            insert_portfolio_snapshot(conn, "run-1", "paper_target_profit_10pct", 100, 100.0, 100.0, {})
            insert_portfolio_snapshot(conn, "run-1", "paper_target_profit_10pct", 200, 111.0, 111.0, {})
            conn.close()

            passing = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "polypaper.cli",
                    "verify-target",
                    "--db",
                    str(db_path),
                    "--run-id",
                    "run-1",
                    "--target-roi",
                    "0.10",
                    "--require-flat",
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(passing.returncode, 0, passing.stderr)
            self.assertIn("PASS", passing.stdout)

            failing = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "polypaper.cli",
                    "verify-target",
                    "--db",
                    str(db_path),
                    "--run-id",
                    "run-1",
                    "--target-roi",
                    "0.20",
                    "--require-flat",
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(failing.returncode, 1, failing.stdout)
            self.assertIn("FAIL", failing.stdout)

    def test_verify_target_reports_remaining_gap_for_open_positions(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        insert_portfolio_snapshot(conn, "run-1", "paper_target_profit_10pct", 100, 100.0, 100.0, {})
        insert_portfolio_snapshot(
            conn,
            "run-1",
            "paper_target_profit_10pct",
            200,
            10.0,
            101.0,
            {"TOKEN-YES": 100.0},
        )

        verification = verify_target_run(
            conn,
            run_id="run-1",
            strategy="paper_target_profit_10pct",
            target_roi=0.10,
            require_flat=True,
        )

        self.assertFalse(verification.passed)
        self.assertAlmostEqual(verification.equity_gap, 9.0)
        self.assertAlmostEqual(verification.roi_gap, 0.09)
        self.assertAlmostEqual(verification.open_position_value, 91.0)
        self.assertAlmostEqual(verification.required_position_gain_pct, 9.0 / 91.0)

    def test_verify_online_goal_requires_two_online_strategies_and_runtime(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        upsert_paper_run(conn, "run-1", "online_target", {"strategies": ["s1", "s2"]}, timestamp=100)
        for strategy in ("s1", "s2"):
            insert_portfolio_snapshot(conn, "run-1", strategy, 1000, 100.0, 100.0, {})
            insert_portfolio_snapshot(conn, "run-1", strategy, 22601, 111.0, 111.0, {})

        verification = verify_online_goal(
            conn,
            run_id="run-1",
            target_roi=0.10,
            require_flat=True,
            min_runtime_seconds=21600,
            min_strategies=2,
        )

        self.assertTrue(verification.passed)
        self.assertEqual(verification.reason, "online_goal_reached")
        self.assertEqual(verification.runtime_seconds, 21601)
        self.assertEqual(verification.passed_strategies, 2)

    def test_verify_online_goal_can_require_two_strategy_families(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        strategies = [
            "paper_target_spread_capture_maker_grid_01",
            "paper_target_spread_capture_maker_grid_02",
            "paper_target_maker_rebate_rotation_grid_01",
        ]
        upsert_paper_run(conn, "run-1", "online_target", {"strategies": strategies}, timestamp=100)
        for strategy in strategies:
            insert_portfolio_snapshot(conn, "run-1", strategy, 1000, 100.0, 100.0, {})
            insert_portfolio_snapshot(conn, "run-1", strategy, 22601, 111.0, 111.0, {})

        verification = verify_online_goal(
            conn,
            run_id="run-1",
            strategies=strategies[:2],
            target_roi=0.10,
            require_flat=True,
            min_runtime_seconds=21600,
            min_strategies=2,
            min_strategy_families=2,
        )

        self.assertFalse(verification.passed)
        self.assertEqual(verification.reason, "too_few_strategy_families_passed")
        self.assertEqual(verification.passed_strategy_families, 1)

        verification = verify_online_goal(
            conn,
            run_id="run-1",
            strategies=strategies,
            target_roi=0.10,
            require_flat=True,
            min_runtime_seconds=21600,
            min_strategies=2,
            min_strategy_families=2,
        )

        self.assertTrue(verification.passed)
        self.assertEqual(verification.passed_strategy_families, 2)

    def test_verify_online_goal_rejects_recording_replay_mode(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        upsert_paper_run(conn, "run-1", "recording_replay", {"strategies": ["s1", "s2"]}, timestamp=100)
        for strategy in ("s1", "s2"):
            insert_portfolio_snapshot(conn, "run-1", strategy, 1000, 100.0, 100.0, {})
            insert_portfolio_snapshot(conn, "run-1", strategy, 22601, 111.0, 111.0, {})

        verification = verify_online_goal(
            conn,
            run_id="run-1",
            target_roi=0.10,
            require_flat=True,
            min_runtime_seconds=21600,
            min_strategies=2,
        )

        self.assertFalse(verification.passed)
        self.assertEqual(verification.reason, "run_mode_not_online")

    def test_verify_online_goal_rejects_short_runtime(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        upsert_paper_run(conn, "run-1", "online_target", {"strategies": ["s1", "s2"]}, timestamp=100)
        for strategy in ("s1", "s2"):
            insert_portfolio_snapshot(conn, "run-1", strategy, 1000, 100.0, 100.0, {})
            insert_portfolio_snapshot(conn, "run-1", strategy, 2000, 111.0, 111.0, {})

        verification = verify_online_goal(
            conn,
            run_id="run-1",
            target_roi=0.10,
            require_flat=True,
            min_runtime_seconds=21600,
            min_strategies=2,
        )

        self.assertFalse(verification.passed)
        self.assertEqual(verification.reason, "runtime_below_minimum")

    def test_verify_online_goal_uses_paper_run_wall_clock_runtime(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        upsert_paper_run(conn, "run-1", "online_target", {"strategies": ["s1", "s2"]}, timestamp=100)
        upsert_paper_run(conn, "run-1", "online_target", {}, timestamp=160)
        for strategy in ("s1", "s2"):
            insert_portfolio_snapshot(conn, "run-1", strategy, 1000, 100.0, 100.0, {})
            insert_portfolio_snapshot(conn, "run-1", strategy, 50000, 111.0, 111.0, {})

        verification = verify_online_goal(
            conn,
            run_id="run-1",
            target_roi=0.10,
            require_flat=True,
            min_runtime_seconds=21600,
            min_strategies=2,
        )

        self.assertFalse(verification.passed)
        self.assertEqual(verification.reason, "runtime_below_minimum")
        self.assertEqual(verification.runtime_seconds, 60)

    def test_verify_online_goal_cli_passes_from_sqlite(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "paper.sqlite"
            conn = sqlite3.connect(db_path)
            init_db(conn)
            upsert_paper_run(conn, "run-1", "online_target", {"strategies": ["s1", "s2"]}, timestamp=100)
            for strategy in ("s1", "s2"):
                insert_portfolio_snapshot(conn, "run-1", strategy, 1000, 100.0, 100.0, {})
                insert_portfolio_snapshot(conn, "run-1", strategy, 22601, 111.0, 111.0, {})
            conn.close()

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "polypaper.cli",
                    "verify-online-goal",
                    "--db",
                    str(db_path),
                    "--run-id",
                    "run-1",
                    "--target-roi",
                    "0.10",
                    "--require-flat",
                    "--min-runtime-seconds",
                    "21600",
                    "--min-strategies",
                    "2",
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_online_goal_status_reports_progress_counts_and_top_strategy(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "paper.sqlite"
            conn = sqlite3.connect(db_path)
            init_db(conn)
            upsert_paper_run(
                conn,
                "run-1",
                "online_target",
                {
                    "strategies": ["s1", "s2"],
                    "cycles_completed": 4320,
                    "min_cycles_before_pass": 4320,
                },
                timestamp=100,
            )
            insert_portfolio_snapshot(conn, "run-1", "s1", 1000, 100.0, 100.0, {})
            insert_portfolio_snapshot(conn, "run-1", "s1", 22601, 111.0, 111.0, {})
            insert_portfolio_snapshot(conn, "run-1", "s2", 1000, 100.0, 100.0, {})
            insert_portfolio_snapshot(conn, "run-1", "s2", 22601, 105.0, 105.0, {})
            conn.execute(
                """
                INSERT INTO signals
                (run_id, strategy, timestamp, side, asset, condition_id, target_notional, reason, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("run-1", "s1", 1200, "BUY", "TOKEN", "C1", 50.0, "entry", "{}"),
            )
            conn.execute(
                """
                INSERT INTO paper_fills
                (run_id, strategy, order_id, timestamp, side, asset, status, price, shares, notional, reason, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("run-1", "s1", "o1", 1201, "BUY", "TOKEN", "FILLED", 0.5, 100.0, 50.0, "filled", "{}"),
            )
            conn.execute(
                """
                INSERT INTO strategy_diagnostics
                (run_id, strategy, timestamp, asset, condition_id, reason, score, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("run-1", "s2", 1200, "TOKEN", "C1", "edge_too_small", 0.0, "{}"),
            )
            conn.commit()
            conn.close()

            status = online_goal_status_from_path(
                str(db_path),
                run_id="run-1",
                target_roi=0.10,
                require_flat=True,
                min_runtime_seconds=21600,
                min_strategies=2,
                top=1,
            )
            text = format_online_goal_status(status)

            self.assertFalse(status.verification.passed)
            self.assertEqual(status.verification.passed_strategies, 1)
            self.assertEqual(status.cycles_completed, 4320)
            self.assertEqual(status.min_cycles_before_pass, 4320)
            self.assertEqual(status.snapshot_count, 4)
            self.assertEqual(status.signal_count, 1)
            self.assertEqual(status.fill_status_counts["FILLED"], 1)
            self.assertEqual(status.top_strategies[0].strategy, "s1")
            self.assertEqual(status.top_diagnostics[0], ("edge_too_small", 1))
            self.assertIn("ACTIVE run_id=run-1", text)
            self.assertIn("cycles=4320/4320", text)

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "polypaper.cli",
                    "online-goal-status",
                    "--db",
                    str(db_path),
                    "--run-id",
                    "run-1",
                    "--target-roi",
                    "0.10",
                    "--require-flat",
                    "--min-runtime-seconds",
                    "21600",
                    "--min-strategies",
                    "2",
                    "--top",
                    "1",
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ACTIVE run_id=run-1", result.stdout)
        self.assertIn("top_strategies", result.stdout)


if __name__ == "__main__":
    unittest.main()
