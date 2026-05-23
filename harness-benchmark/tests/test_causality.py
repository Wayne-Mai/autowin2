import unittest

from polypaper.models import Quote, TraderTrade
from polypaper.simulator import ConservativeFillModel, ReplaySimulator
from polypaper.strategies.replay import SingleTraderMirrorBaseline


class CausalityTests(unittest.TestCase):
    def test_order_does_not_fill_before_delay(self):
        trades = [
            TraderTrade(
                wallet="0xaaa",
                timestamp=100,
                side="BUY",
                asset="YES-C1",
                condition_id="C1",
                price=0.4,
                size=100,
                tx_hash="tx",
            )
        ]
        quotes = [
            Quote(asset="YES-C1", timestamp=110, bid=0.1, ask=0.11),
            Quote(asset="YES-C1", timestamp=160, bid=0.8, ask=0.9),
        ]
        sim = ReplaySimulator(
            strategies=[SingleTraderMirrorBaseline(wallets=["0xaaa"], max_notional=50)],
            fill_model=ConservativeFillModel(delay_seconds=60),
        )
        result = sim.run(trades, quotes)[0]
        fills = [fill for fill in result.fills if fill.status == "FILLED"]
        self.assertEqual(len(fills), 1)
        self.assertEqual(fills[0].timestamp, 160)
        self.assertEqual(fills[0].quote_timestamp, 160)
        self.assertAlmostEqual(fills[0].price, 0.9)

    def test_trade_outside_replay_window_is_invisible(self):
        trades = [
            TraderTrade(
                wallet="0xaaa",
                timestamp=500,
                side="BUY",
                asset="YES-C1",
                condition_id="C1",
                price=0.4,
                size=100,
                tx_hash="future",
            )
        ]
        quotes = [Quote(asset="YES-C1", timestamp=100, bid=0.4, ask=0.5)]
        sim = ReplaySimulator(
            strategies=[SingleTraderMirrorBaseline(wallets=["0xaaa"])],
            fill_model=ConservativeFillModel(delay_seconds=60),
        )
        result = sim.run(trades, quotes, start_ts=0, end_ts=200)[0]
        self.assertEqual(result.metrics["orders"], 0)


if __name__ == "__main__":
    unittest.main()
