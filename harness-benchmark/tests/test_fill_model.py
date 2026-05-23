import unittest

from polypaper.models import BookLevel, OrderBook, Quote, TraderTrade
from polypaper.simulator import (
    ConservativeFillModel,
    LatencyModel,
    MarketRules,
    PolymarketFeeModel,
    ReplaySimulator,
)
from polypaper.strategies.replay import SingleTraderMirrorBaseline


class FillModelTests(unittest.TestCase):
    def test_buy_uses_ask_plus_slippage(self):
        trades = [
            TraderTrade(
                wallet="0xaaa",
                timestamp=100,
                side="BUY",
                asset="YES-C1",
                condition_id="C1",
                price=0.3,
                size=100,
                tx_hash="buy",
            )
        ]
        quotes = [Quote(asset="YES-C1", timestamp=160, bid=0.49, ask=0.5)]
        sim = ReplaySimulator(
            strategies=[SingleTraderMirrorBaseline(wallets=["0xaaa"], max_notional=50)],
            fill_model=ConservativeFillModel(delay_seconds=60, slippage_bps=100),
        )
        result = sim.run(trades, quotes)[0]
        fill = result.fills[0]
        self.assertEqual(fill.status, "FILLED")
        self.assertAlmostEqual(fill.price, 0.51)

    def test_sell_without_inventory_is_missed(self):
        trades = [
            TraderTrade(
                wallet="0xaaa",
                timestamp=100,
                side="SELL",
                asset="YES-C1",
                condition_id="C1",
                price=0.6,
                size=100,
                tx_hash="sell",
            )
        ]
        quotes = [Quote(asset="YES-C1", timestamp=160, bid=0.55, ask=0.56)]
        sim = ReplaySimulator(
            strategies=[SingleTraderMirrorBaseline(wallets=["0xaaa"], max_notional=50)],
            fill_model=ConservativeFillModel(delay_seconds=60),
        )
        result = sim.run(trades, quotes)[0]
        self.assertEqual(result.fills[0].status, "MISSED")
        self.assertEqual(result.fills[0].reason, "no_inventory_no_shorting")

    def test_buy_walks_ask_depth_and_calculates_vwap(self):
        trades = [
            TraderTrade(
                wallet="0xaaa",
                timestamp=100,
                side="BUY",
                asset="YES-C1",
                condition_id="C1",
                price=0.5,
                size=200,
                tx_hash="depth-buy",
            )
        ]
        books = [
            OrderBook(
                asset="YES-C1",
                timestamp=160,
                bids=(BookLevel(0.49, 1000),),
                asks=(BookLevel(0.5, 50), BookLevel(0.6, 125)),
            )
        ]
        sim = ReplaySimulator(
            strategies=[SingleTraderMirrorBaseline(wallets=["0xaaa"], max_notional=100)],
            fill_model=ConservativeFillModel(delay_seconds=60),
        )
        fill = sim.run(trades, books)[0].fills[0]
        self.assertEqual(fill.status, "FILLED")
        self.assertAlmostEqual(fill.notional, 100.0)
        self.assertAlmostEqual(fill.shares, 175.0)
        self.assertAlmostEqual(fill.average_price, 100.0 / 175.0)
        self.assertTrue(fill.taker)

    def test_insufficient_depth_becomes_partial_fill(self):
        trades = [
            TraderTrade(
                wallet="0xaaa",
                timestamp=100,
                side="BUY",
                asset="YES-C1",
                condition_id="C1",
                price=0.5,
                size=200,
                tx_hash="partial-buy",
            )
        ]
        books = [
            OrderBook(
                asset="YES-C1",
                timestamp=160,
                bids=(BookLevel(0.49, 1000),),
                asks=(BookLevel(0.5, 50),),
            )
        ]
        sim = ReplaySimulator(
            strategies=[SingleTraderMirrorBaseline(wallets=["0xaaa"], max_notional=100)],
            fill_model=ConservativeFillModel(delay_seconds=60),
        )
        fill = sim.run(trades, books)[0].fills[0]
        self.assertEqual(fill.status, "PARTIAL")
        self.assertAlmostEqual(fill.notional, 25.0)

    def test_taker_fee_is_charged_with_polymarket_curve(self):
        trades = [
            TraderTrade(
                wallet="0xaaa",
                timestamp=100,
                side="BUY",
                asset="YES-C1",
                condition_id="C1",
                price=0.5,
                size=100,
                tx_hash="fee-buy",
            )
        ]
        quotes = [Quote(asset="YES-C1", timestamp=160, bid=0.49, ask=0.5)]
        rules = MarketRules(fee_model=PolymarketFeeModel(fee_rate=0.05, exponent=1))
        sim = ReplaySimulator(
            strategies=[SingleTraderMirrorBaseline(wallets=["0xaaa"], max_notional=50)],
            fill_model=ConservativeFillModel(delay_seconds=60, default_rules=rules),
        )
        result = sim.run(trades, quotes)[0]
        fill = result.fills[0]
        self.assertEqual(fill.status, "FILLED")
        self.assertAlmostEqual(fill.fee, 1.25)
        self.assertAlmostEqual(result.metrics["fees"], 1.25)

    def test_min_order_size_is_enforced_in_shares(self):
        trades = [
            TraderTrade(
                wallet="0xaaa",
                timestamp=100,
                side="BUY",
                asset="YES-C1",
                condition_id="C1",
                price=0.5,
                size=2,
                tx_hash="small-buy",
            )
        ]
        quotes = [Quote(asset="YES-C1", timestamp=160, bid=0.49, ask=0.5)]
        rules = MarketRules(min_order_size=10)
        sim = ReplaySimulator(
            strategies=[SingleTraderMirrorBaseline(wallets=["0xaaa"], max_notional=1)],
            fill_model=ConservativeFillModel(delay_seconds=60, default_rules=rules),
        )
        fill = sim.run(trades, quotes)[0].fills[0]
        self.assertEqual(fill.status, "MISSED")
        self.assertEqual(fill.reason, "below_min_order_size")

    def test_split_latency_model_controls_eligibility(self):
        trades = [
            TraderTrade(
                wallet="0xaaa",
                timestamp=100,
                side="BUY",
                asset="YES-C1",
                condition_id="C1",
                price=0.5,
                size=100,
                tx_hash="latency-buy",
            )
        ]
        quotes = [
            Quote(asset="YES-C1", timestamp=160, bid=0.49, ask=0.5),
            Quote(asset="YES-C1", timestamp=175, bid=0.6, ask=0.61),
        ]
        latency = LatencyModel(
            detection_delay_seconds=20,
            polling_delay_seconds=10,
            decision_delay_seconds=5,
            execution_delay_seconds=40,
        )
        sim = ReplaySimulator(
            strategies=[SingleTraderMirrorBaseline(wallets=["0xaaa"], max_notional=50)],
            fill_model=ConservativeFillModel(latency_model=latency),
        )
        fill = sim.run(trades, quotes)[0].fills[0]
        self.assertEqual(fill.timestamp, 175)
        self.assertAlmostEqual(fill.price, 0.61)

    def test_market_rules_parse_gamma_market_fee_schedule(self):
        rules = MarketRules.from_gamma_market(
            {
                "orderPriceMinTickSize": 0.001,
                "orderMinSize": 5,
                "feeSchedule": {"rate": 0.05, "exponent": 1, "takerOnly": True},
            }
        )
        self.assertAlmostEqual(rules.tick_size, 0.001)
        self.assertAlmostEqual(rules.min_order_size, 5)
        self.assertAlmostEqual(rules.fee_model.fee_for(100, 0.5, taker=True), 1.25)


if __name__ == "__main__":
    unittest.main()
