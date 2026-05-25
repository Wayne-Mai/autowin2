from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest

from polypaper.cli import main
from polypaper.models import BookLevel, MarketSnapshot, OrderBook
from polypaper.recording import (
    MarketRecording,
    RecordedCollection,
    RecordedMarketDataCollector,
    load_recording,
    save_recording,
)
from polypaper.simulator import MarketRules
from polypaper.verification import verify_target_run_from_path


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
        title="Recorded target fixture",
        slug="recorded-target-fixture",
        outcome="Yes",
    )


def recording_for_prices(prices):
    return MarketRecording(
        recording_id="recording-test",
        created_at=999,
        metadata={"source": "unit"},
        collections=[
            RecordedCollection(
                cycle=index + 1,
                collected_at=snapshot.timestamp,
                snapshots=[snapshot],
                rules_by_asset={snapshot.asset: MarketRules()},
            )
            for index, snapshot in enumerate(snapshot_at(ts, bid, ask) for ts, bid, ask in prices)
        ],
    )


class RecordingTests(unittest.TestCase):
    def test_recording_round_trips_json_and_gzip(self):
        recording = recording_for_prices([(1000, 0.49, 0.50), (1010, 0.62, 0.63)])

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "recording.json"
            gzip_path = Path(tmpdir) / "recording.json.gz"
            save_recording(recording, str(json_path))
            save_recording(recording, str(gzip_path))

            loaded_json = load_recording(str(json_path))
            loaded_gzip = load_recording(str(gzip_path))

        self.assertEqual(loaded_json.recording_id, "recording-test")
        self.assertEqual(loaded_json.collections[0].snapshots[0].book.bid, 0.49)
        self.assertEqual(loaded_gzip.collections[1].snapshots[0].book.ask, 0.63)

    def test_recorded_collector_replays_collections_in_order(self):
        recording = recording_for_prices([(1000, 0.49, 0.50), (1010, 0.62, 0.63)])
        collector = RecordedMarketDataCollector(recording)

        first = collector.collect()
        second = collector.collect()
        exhausted = collector.collect()

        self.assertEqual(first.snapshots[0].timestamp, 1000)
        self.assertEqual(second.snapshots[0].timestamp, 1010)
        self.assertEqual(exhausted.snapshots, [])

    def test_target_replay_recording_can_verify_profit(self):
        recording = recording_for_prices([
            (1000, 0.49, 0.50),
            (1010, 0.62, 0.63),
            (1020, 0.40, 0.41),
        ])

        with tempfile.TemporaryDirectory() as tmpdir:
            recording_path = Path(tmpdir) / "recording.json"
            db_path = Path(tmpdir) / "recording.sqlite"
            report_path = Path(tmpdir) / "report.md"
            save_recording(recording, str(recording_path))
            with redirect_stdout(StringIO()):
                exit_code = main(
                    [
                        "target-replay-recording",
                        "--recording",
                        str(recording_path),
                        "--db",
                        str(db_path),
                        "--run-id",
                        "recording-profit",
                        "--initial-cash",
                        "100",
                        "--portfolio-target-roi",
                        "0.10",
                        "--take-profit-pct",
                        "0.10",
                        "--target-entry-notional",
                        "90",
                        "--target-min-book-imbalance",
                        "-1",
                        "--target-min-momentum-observations",
                        "1",
                        "--target-variants",
                        "balanced",
                        "--require-flat",
                        "--out",
                        str(report_path),
                    ]
                )
            verification = verify_target_run_from_path(
                str(db_path),
                run_id="recording-profit",
                strategy="paper_target_balanced",
                target_roi=0.10,
                require_flat=True,
            )
            report_exists = report_path.exists()

        self.assertEqual(exit_code, 0)
        self.assertTrue(verification.passed, json.dumps(verification.to_dict(), sort_keys=True))
        self.assertTrue(report_exists)


if __name__ == "__main__":
    unittest.main()
