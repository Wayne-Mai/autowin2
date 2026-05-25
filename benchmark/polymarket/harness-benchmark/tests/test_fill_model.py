from dataclasses import replace
import unittest

from polypaper.models import BookLevel, OrderBook, PaperOrder, Portfolio, Quote, Signal, TraderTrade
from polypaper.simulator import (
    ConservativeFillModel,
    LatencyModel,
    MarketRules,
    PolymarketFeeModel,
    ReplaySimulator,
)
from polypaper.strategies.replay import BaselineStrategy, SingleTraderMirrorBaseline


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

    def test_maker_buy_waits_for_later_quote_and_charges_no_taker_fee(self):
        signal = Signal(
            strategy="maker-test",
            timestamp=100,
            side="BUY",
            asset="YES-C1",
            condition_id="C1",
            target_notional=50,
            reason="maker entry",
            execution_style="maker",
            limit_price=0.49,
        )
        order = PaperOrder(order_id="maker-1", signal=signal, created_at=100, eligible_at=100)
        same_quote = OrderBook(
            asset="YES-C1",
            timestamp=100,
            bids=(BookLevel(0.49, 1000),),
            asks=(BookLevel(0.50, 1000),),
        )
        later_quote = OrderBook(
            asset="YES-C1",
            timestamp=160,
            bids=(BookLevel(0.49, 1000),),
            asks=(BookLevel(0.50, 1000),),
        )
        fill_model = ConservativeFillModel(
            default_rules=MarketRules(fee_model=PolymarketFeeModel(fee_rate=0.05, exponent=1))
        )
        portfolio = Portfolio(100)

        self.assertIsNone(fill_model.try_fill(order, same_quote, portfolio))
        fill = fill_model.try_fill(replace(order, attempts=1), later_quote, portfolio)

        self.assertEqual(fill.status, "FILLED")
        self.assertFalse(fill.taker)
        self.assertEqual(fill.reason, "passive_bid_fill_proxy")
        self.assertAlmostEqual(fill.price, 0.49)
        self.assertAlmostEqual(fill.fee, 0.0)
        self.assertAlmostEqual(portfolio.cash, 50.0)

    def test_maker_buy_does_not_fill_when_bid_moves_below_limit(self):
        signal = Signal(
            strategy="maker-test",
            timestamp=100,
            side="BUY",
            asset="YES-C1",
            condition_id="C1",
            target_notional=50,
            reason="maker entry",
            execution_style="maker",
            limit_price=0.49,
        )
        order = PaperOrder(order_id="maker-1", signal=signal, created_at=100, eligible_at=100)
        book = OrderBook(
            asset="YES-C1",
            timestamp=160,
            bids=(BookLevel(0.48, 1000),),
            asks=(BookLevel(0.50, 1000),),
        )

        fill = ConservativeFillModel().try_fill(replace(order, attempts=1), book, Portfolio(100))

        self.assertIsNone(fill)

    def test_queue_proxy_maker_buy_waits_for_queue_decay(self):
        signal = Signal(
            strategy="maker-test",
            timestamp=100,
            side="BUY",
            asset="YES-C1",
            condition_id="C1",
            target_notional=50,
            reason="maker entry",
            execution_style="maker",
            limit_price=0.49,
        )
        order = PaperOrder(order_id="maker-queue-1", signal=signal, created_at=100, eligible_at=100)
        book = OrderBook(
            asset="YES-C1",
            timestamp=160,
            bids=(BookLevel(0.49, 1000),),
            asks=(BookLevel(0.50, 1000),),
        )
        fill_model = ConservativeFillModel(
            maker_fill_mode="queue_proxy",
            maker_queue_ahead_fraction=1.0,
            maker_queue_decay=0.5,
        )
        portfolio = Portfolio(100)

        self.assertIsNone(fill_model.try_fill(replace(order, attempts=2), book, portfolio))
        fill = fill_model.try_fill(replace(order, attempts=3), book, portfolio)

        self.assertEqual(fill.status, "FILLED")
        self.assertEqual(fill.reason, "passive_bid_queue_proxy")
        self.assertAlmostEqual(fill.price, 0.49)
        self.assertAlmostEqual(portfolio.cash, 50.0)

    def test_queue_proxy_maker_buy_can_partial_fill(self):
        signal = Signal(
            strategy="maker-test",
            timestamp=100,
            side="BUY",
            asset="YES-C1",
            condition_id="C1",
            target_notional=50,
            reason="maker entry",
            execution_style="maker",
            limit_price=0.50,
        )
        order = PaperOrder(order_id="maker-queue-partial", signal=signal, created_at=100, eligible_at=100)
        book = OrderBook(
            asset="YES-C1",
            timestamp=160,
            bids=(BookLevel(0.50, 20),),
            asks=(BookLevel(0.51, 1000),),
        )
        fill_model = ConservativeFillModel(
            maker_fill_mode="queue_proxy",
            maker_queue_ahead_fraction=1.0,
            maker_queue_decay=0.5,
        )
        portfolio = Portfolio(100)

        fill = fill_model.try_fill(replace(order, attempts=3), book, portfolio)

        self.assertEqual(fill.status, "PARTIAL")
        self.assertEqual(fill.reason, "passive_bid_queue_proxy")
        self.assertAlmostEqual(fill.notional, 5.0)
        self.assertAlmostEqual(fill.shares, 10.0)
        self.assertAlmostEqual(portfolio.cash, 95.0)

    def test_replay_keeps_maker_partial_residual_pending_until_complete(self):
        class MakerLimitBaseline(BaselineStrategy):
            name = "maker_limit"

            def on_trade(self, trade, portfolio):
                return [
                    Signal(
                        strategy=self.name,
                        timestamp=trade.timestamp,
                        side="BUY",
                        asset=trade.asset,
                        condition_id=trade.condition_id,
                        target_notional=50.0,
                        reason="fixture maker entry",
                        execution_style="maker",
                        limit_price=0.50,
                    )
                ]

        trades = [
            TraderTrade(
                wallet="0xaaa",
                timestamp=100,
                side="BUY",
                asset="YES-C1",
                condition_id="C1",
                price=0.50,
                size=100,
                tx_hash="maker-entry",
            )
        ]
        books = [
            OrderBook(
                asset="YES-C1",
                timestamp=101,
                bids=(BookLevel(0.50, 20),),
                asks=(BookLevel(0.51, 1000),),
            ),
            OrderBook(
                asset="YES-C1",
                timestamp=102,
                bids=(BookLevel(0.50, 20),),
                asks=(BookLevel(0.51, 1000),),
            ),
            OrderBook(
                asset="YES-C1",
                timestamp=103,
                bids=(BookLevel(0.50, 80),),
                asks=(BookLevel(0.51, 1000),),
            ),
        ]
        sim = ReplaySimulator(
            strategies=[MakerLimitBaseline()],
            fill_model=ConservativeFillModel(
                delay_seconds=0,
                maker_fill_mode="queue_proxy",
                maker_queue_ahead_fraction=0.0,
                maker_queue_decay=1.0,
            ),
            initial_cash=100,
        )

        result = sim.run(trades, books)[0]

        self.assertEqual([fill.status for fill in result.fills], ["PARTIAL", "FILLED"])
        self.assertEqual(result.fills[0].order_id, result.fills[1].order_id)
        self.assertAlmostEqual(result.fills[0].notional, 10.0)
        self.assertAlmostEqual(result.fills[1].notional, 40.0)
        self.assertEqual(result.metrics["partial_orders"], 1.0)
        self.assertEqual(result.metrics["filled_orders"], 1.0)
        self.assertAlmostEqual(result.metrics["turnover"], 50.0)

    def test_maker_order_expires_after_max_attempts(self):
        signal = Signal(
            strategy="maker-test",
            timestamp=100,
            side="BUY",
            asset="YES-C1",
            condition_id="C1",
            target_notional=50,
            reason="maker entry",
            execution_style="maker",
            limit_price=0.49,
        )
        order = PaperOrder(order_id="maker-expire", signal=signal, created_at=100, eligible_at=100)
        book = OrderBook(
            asset="YES-C1",
            timestamp=160,
            bids=(BookLevel(0.49, 1000),),
            asks=(BookLevel(0.50, 1000),),
        )
        fill_model = ConservativeFillModel(maker_max_order_age_attempts=2)

        fill = fill_model.try_fill(replace(order, attempts=2), book, Portfolio(100))

        self.assertEqual(fill.status, "MISSED")
        self.assertEqual(fill.reason, "maker_order_expired")

    def test_maker_buy_can_cancel_when_price_moves_away(self):
        signal = Signal(
            strategy="maker-test",
            timestamp=100,
            side="BUY",
            asset="YES-C1",
            condition_id="C1",
            target_notional=50,
            reason="maker entry",
            execution_style="maker",
            limit_price=0.49,
        )
        order = PaperOrder(order_id="maker-cancel", signal=signal, created_at=100, eligible_at=100)
        book = OrderBook(
            asset="YES-C1",
            timestamp=160,
            bids=(BookLevel(0.48, 1000),),
            asks=(BookLevel(0.50, 1000),),
        )
        fill_model = ConservativeFillModel(maker_cancel_on_price_move=True)

        fill = fill_model.try_fill(replace(order, attempts=1), book, Portfolio(100))

        self.assertEqual(fill.status, "MISSED")
        self.assertEqual(fill.reason, "maker_price_moved_away")

    def test_maker_buy_adverse_selection_proxy_fills_when_price_moves_through(self):
        signal = Signal(
            strategy="maker-test",
            timestamp=100,
            side="BUY",
            asset="YES-C1",
            condition_id="C1",
            target_notional=50,
            reason="maker entry",
            execution_style="maker",
            limit_price=0.50,
        )
        order = PaperOrder(order_id="maker-adverse", signal=signal, created_at=100, eligible_at=100)
        book = OrderBook(
            asset="YES-C1",
            timestamp=160,
            bids=(BookLevel(0.48, 1000),),
            asks=(BookLevel(0.51, 1000),),
        )
        fill_model = ConservativeFillModel(
            maker_adverse_fill_on_price_move=True,
            maker_adverse_fill_fraction=0.25,
        )
        portfolio = Portfolio(100)

        fill = fill_model.try_fill(replace(order, attempts=1), book, portfolio)

        self.assertEqual(fill.status, "PARTIAL")
        self.assertEqual(fill.reason, "passive_bid_adverse_selection_proxy")
        self.assertAlmostEqual(fill.notional, 12.5)
        self.assertAlmostEqual(fill.price, 0.50)
        self.assertAlmostEqual(portfolio.cash, 87.5)

    def test_maker_sell_waits_for_later_quote_and_charges_no_taker_fee(self):
        signal = Signal(
            strategy="maker-test",
            timestamp=100,
            side="SELL",
            asset="YES-C1",
            condition_id="C1",
            target_notional=60,
            reason="maker exit",
            execution_style="maker",
            limit_price=0.60,
        )
        order = PaperOrder(order_id="maker-sell-1", signal=signal, created_at=100, eligible_at=100)
        same_quote = OrderBook(
            asset="YES-C1",
            timestamp=100,
            bids=(BookLevel(0.58, 1000),),
            asks=(BookLevel(0.60, 1000),),
        )
        later_quote = OrderBook(
            asset="YES-C1",
            timestamp=160,
            bids=(BookLevel(0.58, 1000),),
            asks=(BookLevel(0.60, 1000),),
        )
        fill_model = ConservativeFillModel(
            default_rules=MarketRules(fee_model=PolymarketFeeModel(fee_rate=0.05, exponent=1))
        )
        portfolio = Portfolio(100)
        portfolio.buy("YES-C1", shares=100, price=0.50)

        self.assertIsNone(fill_model.try_fill(order, same_quote, portfolio))
        fill = fill_model.try_fill(replace(order, attempts=1), later_quote, portfolio)

        self.assertEqual(fill.status, "FILLED")
        self.assertFalse(fill.taker)
        self.assertEqual(fill.reason, "passive_ask_fill_proxy")
        self.assertAlmostEqual(fill.price, 0.60)
        self.assertAlmostEqual(fill.fee, 0.0)
        self.assertAlmostEqual(portfolio.cash, 110.0)
        self.assertEqual(portfolio.positions, {})

    def test_maker_sell_does_not_fill_when_ask_moves_above_limit(self):
        signal = Signal(
            strategy="maker-test",
            timestamp=100,
            side="SELL",
            asset="YES-C1",
            condition_id="C1",
            target_notional=60,
            reason="maker exit",
            execution_style="maker",
            limit_price=0.60,
        )
        order = PaperOrder(order_id="maker-sell-1", signal=signal, created_at=100, eligible_at=100)
        book = OrderBook(
            asset="YES-C1",
            timestamp=160,
            bids=(BookLevel(0.58, 1000),),
            asks=(BookLevel(0.61, 1000),),
        )
        portfolio = Portfolio(100)
        portfolio.buy("YES-C1", shares=100, price=0.50)

        fill = ConservativeFillModel().try_fill(replace(order, attempts=1), book, portfolio)

        self.assertIsNone(fill)

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
                "feeSchedule": {"rate": 0.05, "exponent": 1, "takerOnly": True, "rebateRate": 0.2},
            }
        )
        self.assertAlmostEqual(rules.tick_size, 0.001)
        self.assertAlmostEqual(rules.min_order_size, 5)
        self.assertAlmostEqual(rules.fee_model.fee_for(100, 0.5, taker=True), 1.25)
        self.assertAlmostEqual(rules.fee_model.fee_for(100, 0.5, taker=False), -0.25)

    def test_market_rules_parse_gamma_market_fee_schedule_json_string(self):
        rules = MarketRules.from_gamma_market(
            {
                "orderPriceMinTickSize": 0.001,
                "orderMinSize": 5,
                "feeSchedule": '{"rate": 0.07, "exponent": 1, "takerOnly": true, "rebateRate": 0.25}',
            }
        )
        self.assertAlmostEqual(rules.fee_model.fee_for(100, 0.5, taker=True), 1.75)
        self.assertAlmostEqual(rules.fee_model.fee_for(100, 0.5, taker=False), -0.4375)

    def test_maker_rebate_is_recorded_as_negative_fee(self):
        signal = Signal(
            strategy="maker-rebate-test",
            timestamp=100,
            side="BUY",
            asset="YES-C1",
            condition_id="C1",
            target_notional=50,
            reason="maker entry",
            execution_style="maker",
            limit_price=0.50,
        )
        order = PaperOrder(order_id="maker-rebate-1", signal=signal, created_at=100, eligible_at=100)
        book = OrderBook(
            asset="YES-C1",
            timestamp=160,
            bids=(BookLevel(0.50, 1000),),
            asks=(BookLevel(0.51, 1000),),
        )
        fill_model = ConservativeFillModel(
            default_rules=MarketRules(
                fee_model=PolymarketFeeModel(
                    fee_rate=0.07,
                    exponent=1,
                    taker_only=True,
                    maker_rebate_rate=0.2,
                )
            )
        )
        portfolio = Portfolio(100)

        fill = fill_model.try_fill(replace(order, attempts=1), book, portfolio)

        self.assertEqual(fill.status, "FILLED")
        self.assertFalse(fill.taker)
        self.assertLess(fill.fee, 0.0)
        self.assertAlmostEqual(fill.fee, -0.35)
        self.assertAlmostEqual(portfolio.cash, 50.35)


if __name__ == "__main__":
    unittest.main()
