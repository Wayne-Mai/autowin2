from __future__ import annotations

import unittest

from polypaper.engines import (
    EngineKind,
    LiveTradingDisabledError,
    TradingEngine,
    disabled_live_engine,
    paper_engine,
)


class DummyRunner:
    def __init__(self):
        self.calls = 0
        self._results = []

    def run_once(self):
        self.calls += 1
        return ["snapshot"]

    def results(self):
        return self._results


class EngineTests(unittest.TestCase):
    def test_paper_engine_delegates_runner_interface(self):
        runner = DummyRunner()
        engine = paper_engine(runner, name="online-paper")

        self.assertIsInstance(engine, TradingEngine)
        self.assertEqual(engine.metadata.kind, EngineKind.PAPER)
        self.assertTrue(engine.metadata.uses_live_market_data)
        self.assertFalse(engine.metadata.live_order_capable)
        self.assertEqual(engine.run_once(), ["snapshot"])
        self.assertEqual(runner.calls, 1)
        self.assertEqual(engine.results(), [])

    def test_disabled_live_engine_refuses_to_run(self):
        engine = disabled_live_engine()

        self.assertIsInstance(engine, TradingEngine)
        self.assertEqual(engine.metadata.kind, EngineKind.LIVE)
        self.assertFalse(engine.metadata.live_order_capable)
        with self.assertRaises(LiveTradingDisabledError):
            engine.run_once()


if __name__ == "__main__":
    unittest.main()
