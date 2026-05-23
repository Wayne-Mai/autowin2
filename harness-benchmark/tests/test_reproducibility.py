import json
import unittest

from polypaper.strategies.replay import (
    ConsensusMirrorBaseline,
    NoTradeBaseline,
    RandomSameTurnoverBaseline,
    SingleTraderMirrorBaseline,
    SpecialistMirrorBaseline,
)
from polypaper.simulator import ConservativeFillModel, ReplaySimulator
from tests.helpers import load_small_fixture


class ReproducibilityTests(unittest.TestCase):
    def test_same_seed_same_results(self):
        first = self._run(seed=42)
        second = self._run(seed=42)
        self.assertEqual(
            json.dumps([result.to_dict() for result in first], sort_keys=True),
            json.dumps([result.to_dict() for result in second], sort_keys=True),
        )

    def test_different_seed_changes_random_baseline(self):
        first = self._run(seed=1)
        second = self._run(seed=2)
        random_first = [result for result in first if result.strategy == "random_same_turnover"][0]
        random_second = [result for result in second if result.strategy == "random_same_turnover"][0]
        self.assertNotEqual(
            json.dumps(random_first.to_dict(), sort_keys=True),
            json.dumps(random_second.to_dict(), sort_keys=True),
        )

    def _run(self, seed):
        trades, quotes = load_small_fixture()
        strategies = [
            NoTradeBaseline(),
            RandomSameTurnoverBaseline(seed=seed, trade_probability=0.5, max_notional=50),
            SingleTraderMirrorBaseline(wallets=["0xaaa"], max_notional=50),
            ConsensusMirrorBaseline(wallets=["0xaaa", "0xbbb"], threshold=2, max_notional=50),
            SpecialistMirrorBaseline({"0xaaa": ["politics"]}, max_notional=50),
        ]
        sim = ReplaySimulator(strategies=strategies, fill_model=ConservativeFillModel(delay_seconds=60))
        return sim.run(trades, quotes)


if __name__ == "__main__":
    unittest.main()
