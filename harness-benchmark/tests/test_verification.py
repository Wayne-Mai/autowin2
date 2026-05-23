import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from polypaper.storage import init_db, insert_portfolio_snapshot
from polypaper.verification import verify_target_run


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


if __name__ == "__main__":
    unittest.main()
