import unittest

from polypaper.strategies.replay import (
    ConsensusMirrorBaseline,
    NoTradeBaseline,
    SingleTraderMirrorBaseline,
    SpecialistMirrorBaseline,
)
from polypaper.simulator import ConservativeFillModel, ReplaySimulator
from tests.helpers import load_small_fixture


class BaselineTests(unittest.TestCase):
    def test_no_trade_baseline_is_flat(self):
        trades, quotes = load_small_fixture()
        sim = ReplaySimulator(
            strategies=[NoTradeBaseline()],
            fill_model=ConservativeFillModel(delay_seconds=60),
        )
        result = sim.run(trades, quotes)[0]
        self.assertEqual(result.metrics["orders"], 0)
        self.assertAlmostEqual(result.metrics["pnl"], 0.0)

    def test_single_trader_mirror_traces_source_wallet(self):
        trades, quotes = load_small_fixture()
        sim = ReplaySimulator(
            strategies=[SingleTraderMirrorBaseline(wallets=["0xaaa"], max_notional=50)],
            fill_model=ConservativeFillModel(delay_seconds=60),
        )
        result = sim.run(trades, quotes)[0]
        self.assertGreaterEqual(result.metrics["orders"], 1)
        self.assertEqual(result.orders[0].signal.source_wallets, ("0xaaa",))

    def test_consensus_requires_multiple_wallets(self):
        trades, quotes = load_small_fixture()
        sim = ReplaySimulator(
            strategies=[ConsensusMirrorBaseline(wallets=["0xaaa", "0xbbb"], threshold=2, max_notional=50)],
            fill_model=ConservativeFillModel(delay_seconds=60),
        )
        result = sim.run(trades, quotes)[0]
        self.assertEqual(result.metrics["orders"], 1)
        self.assertEqual(set(result.orders[0].signal.source_wallets), {"0xaaa", "0xbbb"})

    def test_specialist_only_follows_matching_category(self):
        trades, quotes = load_small_fixture()
        sim = ReplaySimulator(
            strategies=[SpecialistMirrorBaseline({"0xaaa": ["politics"]}, max_notional=50)],
            fill_model=ConservativeFillModel(delay_seconds=60),
        )
        result = sim.run(trades, quotes)[0]
        self.assertEqual(result.metrics["orders"], 2)
        for order in result.orders:
            self.assertEqual(order.signal.source_wallets, ("0xaaa",))


if __name__ == "__main__":
    unittest.main()
