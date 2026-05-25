import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

from polypaper.benchmark import (
    benchmark_markdown_report,
    load_fill_scenarios,
    run_replay_benchmark,
)
from polypaper.cli import main


class BenchmarkSuiteTests(unittest.TestCase):
    def test_load_default_fill_scenarios(self):
        scenarios = load_fill_scenarios("configs/fill_scenarios.yml")

        self.assertEqual([scenario.name for scenario in scenarios], ["optimistic", "realistic", "pessimistic"])
        self.assertEqual(scenarios[0].params["maker_fill_mode"], "optimistic")
        self.assertEqual(scenarios[1].params["maker_fill_mode"], "queue_proxy")
        self.assertTrue(scenarios[2].params["maker_cancel_on_price_move"])

    def test_run_replay_benchmark_summarizes_scenarios(self):
        scenarios = load_fill_scenarios("configs/fill_scenarios.yml", ["optimistic", "realistic"])

        result = run_replay_benchmark(
            fixture_path="tests/fixtures/small_replay.json",
            scenarios=scenarios,
            strategy_suite="default_with_maker",
            seed=42,
            initial_cash=10000,
        )

        strategies = {row["strategy"] for row in result.summary_rows}
        scenario_names = {row["scenario"] for row in result.summary_rows}
        maker_rows = [
            row for row in result.summary_rows
            if row["strategy"] == "maker_single_trader_mirror"
        ]
        self.assertEqual(result.baseline_scenario, "optimistic")
        self.assertIn("maker_single_trader_mirror", strategies)
        self.assertEqual(scenario_names, {"optimistic", "realistic"})
        self.assertEqual(len(maker_rows), 2)
        self.assertIsNotNone(maker_rows[1]["roi_delta_vs_baseline"])
        self.assertIn("Polymarket Benchmark Suite Report", benchmark_markdown_report(result))

    def test_cli_benchmark_suite_writes_outputs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with redirect_stdout(StringIO()):
                exit_code = main(
                    [
                        "benchmark-suite",
                        "--fixture",
                        "tests/fixtures/small_replay.json",
                        "--scenarios",
                        "optimistic,realistic",
                        "--strategy-suite",
                        "maker_only",
                        "--out-dir",
                        tmpdir,
                    ]
                )

            self.assertEqual(exit_code, 0)
            output_dir = Path(tmpdir)
            summary = json.loads((output_dir / "benchmark_summary.json").read_text(encoding="utf-8"))
            self.assertTrue((output_dir / "benchmark_summary.csv").exists())
            self.assertTrue((output_dir / "benchmark_summary.md").exists())
            self.assertEqual(summary["strategy_suite"], "maker_only")
            self.assertEqual([item["name"] for item in summary["scenarios"]], ["optimistic", "realistic"])


if __name__ == "__main__":
    unittest.main()
