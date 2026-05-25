from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest

from polypaper.cli import main
from polypaper.models import BookLevel, MarketSnapshot, OrderBook, Portfolio
from polypaper.recording import MarketRecording, RecordedCollection, save_recording
from polypaper.simulator import MarketRules, PolymarketFeeModel
from polypaper.strategies.paper.target import (
    CoinbaseSpotProvider,
    CryptoDirectionalPaperStrategy,
    CryptoIntervalAnchorPaperStrategy,
    CryptoIntervalBookSkewPaperStrategy,
    CryptoIntervalCloseEdgePaperStrategy,
    MakerRebateRotationStrategy,
    MomentumScalperPaperStrategy,
    OutcomeBasketArbPaperStrategy,
    SpreadCaptureMakerStrategy,
    target_strategy_from_config,
    target_variant_configs,
)
from polypaper.verification import verify_target_run_from_path


def snapshot_at(timestamp, bid, ask, asset="TOKEN-YES"):
    return MarketSnapshot(
        asset=asset,
        condition_id="0xcondition",
        timestamp=timestamp,
        book=OrderBook(
            asset=asset,
            timestamp=timestamp,
            bids=(BookLevel(price=bid, size=1000),),
            asks=(BookLevel(price=ask, size=1000),),
        ),
        title="Goal scalper fixture",
        slug="goal-scalper-fixture",
        outcome="Yes",
    )


def recording_for_prices(prices):
    collections = []
    for index, row in enumerate(prices):
        snapshot = snapshot_at(*row)
        collections.append(
            RecordedCollection(
                cycle=index + 1,
                collected_at=snapshot.timestamp,
                snapshots=[snapshot],
                rules_by_asset={snapshot.asset: MarketRules()},
            )
        )
    return MarketRecording(
        recording_id="goal-scalpers",
        created_at=999,
        metadata={"source": "unit"},
        collections=collections,
    )


def paired_recording_for_prices(cycles):
    collections = []
    for index, (timestamp, yes_bid, yes_ask, no_bid, no_ask) in enumerate(cycles):
        snapshots = [
            MarketSnapshot(
                asset="TOKEN-YES",
                condition_id="0xpaired",
                timestamp=timestamp,
                book=OrderBook(
                    asset="TOKEN-YES",
                    timestamp=timestamp,
                    bids=(BookLevel(price=yes_bid, size=1000),),
                    asks=(BookLevel(price=yes_ask, size=1000),),
                ),
                title="Paired basket fixture",
                slug="paired-basket-fixture",
                outcome="Yes",
                outcome_index=0,
            ),
            MarketSnapshot(
                asset="TOKEN-NO",
                condition_id="0xpaired",
                timestamp=timestamp,
                book=OrderBook(
                    asset="TOKEN-NO",
                    timestamp=timestamp,
                    bids=(BookLevel(price=no_bid, size=1000),),
                    asks=(BookLevel(price=no_ask, size=1000),),
                ),
                title="Paired basket fixture",
                slug="paired-basket-fixture",
                outcome="No",
                outcome_index=1,
            ),
        ]
        collections.append(
            RecordedCollection(
                cycle=index + 1,
                collected_at=timestamp,
                snapshots=snapshots,
                rules_by_asset={snapshot.asset: MarketRules() for snapshot in snapshots},
            )
        )
    return MarketRecording(
        recording_id="goal-basket",
        created_at=999,
        metadata={"source": "unit"},
        collections=collections,
    )


def crypto_pair_snapshots(
    timestamp,
    up_bid,
    up_ask,
    down_bid,
    down_ask,
    symbol="Bitcoin",
    slug_symbol="btc",
    interval="5m",
):
    return [
        MarketSnapshot(
            asset="TOKEN-UP",
            condition_id="0xcrypto",
            timestamp=timestamp,
            book=OrderBook(
                asset="TOKEN-UP",
                timestamp=timestamp,
                bids=(BookLevel(price=up_bid, size=1000),),
                asks=(BookLevel(price=up_ask, size=1000),),
            ),
            title=f"{symbol} Up or Down - May 24, 3:40AM-3:45AM ET",
            slug=f"{slug_symbol}-updown-{interval}-1779608400",
            outcome="Up",
            outcome_index=0,
        ),
        MarketSnapshot(
            asset="TOKEN-DOWN",
            condition_id="0xcrypto",
            timestamp=timestamp,
            book=OrderBook(
                asset="TOKEN-DOWN",
                timestamp=timestamp,
                bids=(BookLevel(price=down_bid, size=1000),),
                asks=(BookLevel(price=down_ask, size=1000),),
            ),
            title=f"{symbol} Up or Down - May 24, 3:40AM-3:45AM ET",
            slug=f"{slug_symbol}-updown-{interval}-1779608400",
            outcome="Down",
            outcome_index=1,
        ),
    ]


class FakeSpotProvider:
    def __init__(self, prices):
        self.prices_by_call = list(prices)
        self.calls = []

    def prices(self, symbols):
        self.calls.append(tuple(symbols))
        index = min(len(self.calls) - 1, len(self.prices_by_call) - 1)
        price = self.prices_by_call[index]
        return {symbol: price for symbol in symbols}


def run_replay(recording, variant, extra_args=None):
    with tempfile.TemporaryDirectory() as tmpdir:
        recording_path = Path(tmpdir) / "recording.json"
        db_path = Path(tmpdir) / "paper.sqlite"
        save_recording(recording, str(recording_path))
        args = [
            "target-replay-recording",
            "--recording",
            str(recording_path),
            "--db",
            str(db_path),
            "--run-id",
            f"{variant}-run",
            "--initial-cash",
            "100",
            "--portfolio-target-roi",
            "0.10",
            "--target-entry-notional",
            "90",
            "--target-variants",
            variant,
            "--require-flat",
        ]
        args.extend(extra_args or [])
        with redirect_stdout(StringIO()):
            exit_code = main(args)
        strategy = f"paper_target_{variant}"
        verification = verify_target_run_from_path(
            str(db_path),
            run_id=f"{variant}-run",
            strategy=strategy,
            target_roi=0.10,
            require_flat=True,
        )
        return exit_code, verification


class GoalScalperTests(unittest.TestCase):
    def test_coinbase_spot_provider_negative_caches_failures(self):
        now = [100.0]
        provider = CoinbaseSpotProvider(ttl_seconds=30, clock=lambda: now[0])
        calls = []

        def failing_fetch(symbol):
            calls.append(symbol)
            return None

        provider._fetch_spot = failing_fetch

        self.assertEqual(provider.prices(["BTC", "ETH"]), {})
        self.assertEqual(provider.prices(["BTC"]), {})
        self.assertEqual(calls, ["BTC", "ETH"])

        now[0] = 131.0
        self.assertEqual(provider.prices(["BTC"]), {})
        self.assertEqual(calls, ["BTC", "ETH", "BTC"])

    def test_momentum_scalper_variant_builds_dedicated_strategy(self):
        config = dict(_variant_configs("momentum_scalper_goal"))["momentum_scalper_goal"]
        strategy = target_strategy_from_config(_args(), "momentum_scalper_goal", config)

        self.assertIsInstance(strategy, MomentumScalperPaperStrategy)
        self.assertEqual(strategy.entry_execution_style, "taker")
        self.assertEqual(strategy.take_profit_pct, 0.04)
        self.assertEqual(strategy.stop_loss_pct, 0.04)

    def test_spread_capture_variant_builds_dedicated_maker_strategy(self):
        config = dict(_variant_configs("spread_capture_maker_goal"))["spread_capture_maker_goal"]
        strategy = target_strategy_from_config(_args(), "spread_capture_maker_goal", config)

        self.assertIsInstance(strategy, SpreadCaptureMakerStrategy)
        self.assertEqual(strategy.entry_execution_style, "maker")
        self.assertTrue(strategy.maker_exit)
        self.assertEqual(strategy.take_profit_pct, 0.02)
        self.assertEqual(strategy.stop_loss_pct, 0.04)
        self.assertEqual(strategy.min_spread_pct, 0.02)
        self.assertAlmostEqual(strategy.entry_notional, 25.0)

    def test_maker_rebate_rotation_variant_builds_dedicated_strategy(self):
        config = dict(_variant_configs("maker_rebate_rotation_goal"))["maker_rebate_rotation_goal"]
        strategy = target_strategy_from_config(_args(), "maker_rebate_rotation_goal", config)

        self.assertIsInstance(strategy, MakerRebateRotationStrategy)
        self.assertEqual(strategy.entry_execution_style, "maker")
        self.assertTrue(strategy.maker_exit)
        self.assertEqual(strategy.min_round_trip_edge_pct, 0.004)
        self.assertEqual(strategy.min_touch_depth_notional, 25.0)
        self.assertAlmostEqual(strategy.entry_notional, 20.0)

    def test_spread_capture_uses_maker_exit_for_stale_position(self):
        strategy = SpreadCaptureMakerStrategy(
            initial_cash=100,
            entry_notional=20,
            take_profit_pct=0.05,
            max_hold_cycles=1,
            max_hold_min_progress_pct=0.05,
            name="paper_target_spread_stale_test",
        )
        strategy.avg_cost_by_asset["TOKEN-YES"] = 0.49
        strategy.position_shares_by_asset["TOKEN-YES"] = 20.0
        strategy.entry_bid_by_asset["TOKEN-YES"] = 0.49
        strategy.hold_cycles_by_asset["TOKEN-YES"] = 1

        signal = strategy.on_snapshot(
            snapshot_at(1000, bid=0.49, ask=0.50),
            Portfolio(100, positions={"TOKEN-YES": 20.0}),
        )[0]

        self.assertEqual(signal.side, "SELL")
        self.assertEqual(signal.execution_style, "maker")
        self.assertEqual(signal.limit_price, 0.50)
        self.assertEqual(signal.reason, "stale_position_exit")

    def test_spread_capture_overrides_pending_maker_exit_after_target_reached(self):
        strategy = SpreadCaptureMakerStrategy(
            initial_cash=100,
            entry_notional=20,
            portfolio_target_roi=0.10,
            take_profit_pct=0.05,
            name="paper_target_spread_target_flatten_test",
        )
        strategy.avg_cost_by_asset["TOKEN-YES"] = 0.50
        strategy.position_shares_by_asset["TOKEN-YES"] = 20.0
        strategy.pending_assets["TOKEN-YES"] = "SELL"

        signal = strategy.on_snapshot(
            snapshot_at(1000, bid=0.50, ask=0.51),
            Portfolio(101, positions={"TOKEN-YES": 20.0}),
        )[0]

        self.assertEqual(signal.side, "SELL")
        self.assertEqual(signal.execution_style, "taker")
        self.assertIsNone(signal.limit_price)
        self.assertEqual(signal.reason, "portfolio_target_reached")

    def test_maker_rebate_rotation_enters_on_round_trip_edge(self):
        strategy = MakerRebateRotationStrategy(
            initial_cash=100,
            entry_notional=20,
            min_round_trip_edge_pct=0.005,
            min_maker_rebate_pct=0.0001,
            name="paper_target_rebate_rotation_test",
        )
        rules = {
            "TOKEN-YES": MarketRules(
                fee_model=PolymarketFeeModel(
                    fee_rate=0.02,
                    exponent=1.0,
                    maker_rebate_rate=0.2,
                )
            )
        }

        signals = strategy.on_snapshots([snapshot_at(1000, 0.49, 0.51)], Portfolio(100), rules)

        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].side, "BUY")
        self.assertEqual(signals[0].execution_style, "maker")
        self.assertEqual(signals[0].limit_price, 0.49)
        self.assertIn("maker_rebate_rotation_entry", signals[0].reason)

    def test_outcome_basket_arb_variant_builds_dedicated_strategy(self):
        config = dict(_variant_configs("outcome_basket_arb_goal"))["outcome_basket_arb_goal"]
        strategy = target_strategy_from_config(_args(), "outcome_basket_arb_goal", config)

        self.assertIsInstance(strategy, OutcomeBasketArbPaperStrategy)
        self.assertEqual(strategy.min_settlement_roi, 0.02)
        self.assertEqual(strategy.max_outcomes, 2)
        self.assertAlmostEqual(strategy.entry_notional, 25.0)

    def test_crypto_directional_variant_builds_dedicated_strategy(self):
        config = dict(_variant_configs("crypto_directional_goal"))["crypto_directional_goal"]
        strategy = target_strategy_from_config(_args(), "crypto_directional_goal", config)

        self.assertIsInstance(strategy, CryptoDirectionalPaperStrategy)
        self.assertEqual(strategy.min_spot_observations, 2)
        self.assertEqual(strategy.max_positions, 2)

    def test_crypto_interval_anchor_variant_builds_dedicated_strategy(self):
        config = dict(_variant_configs("crypto_interval_anchor_goal"))["crypto_interval_anchor_goal"]
        strategy = target_strategy_from_config(_args(), "crypto_interval_anchor_goal", config)

        self.assertIsInstance(strategy, CryptoIntervalAnchorPaperStrategy)
        self.assertEqual(strategy.max_anchor_lag_seconds, 45)
        self.assertEqual(strategy.min_seconds_to_close, 15)

    def test_crypto_interval_close_edge_variant_builds_dedicated_strategy(self):
        config = dict(_variant_configs("crypto_interval_close_edge_goal"))["crypto_interval_close_edge_goal"]
        strategy = target_strategy_from_config(_args(), "crypto_interval_close_edge_goal", config)

        self.assertIsInstance(strategy, CryptoIntervalCloseEdgePaperStrategy)
        self.assertEqual(strategy.min_market_age_seconds, 210)
        self.assertEqual(strategy.max_seconds_to_close, 75)

    def test_crypto_directional_buys_matching_up_outcome_after_spot_momentum(self):
        strategy = CryptoDirectionalPaperStrategy(
            initial_cash=100,
            min_spot_move_pct=0.001,
            take_profit_pct=0.05,
            stop_loss_pct=0.03,
            entry_notional=40,
            max_spread_pct=0.05,
            spot_provider=FakeSpotProvider([100.0, 100.25]),
            name="paper_target_crypto_test",
        )
        portfolio = Portfolio(100)

        first = strategy.on_snapshots(
            crypto_pair_snapshots(1000, up_bid=0.49, up_ask=0.50, down_bid=0.49, down_ask=0.50),
            portfolio,
        )
        second = strategy.on_snapshots(
            crypto_pair_snapshots(1010, up_bid=0.50, up_ask=0.51, down_bid=0.48, down_ask=0.49),
            portfolio,
        )

        self.assertEqual(first, [])
        self.assertEqual(len(second), 1)
        self.assertEqual(second[0].asset, "TOKEN-UP")
        self.assertEqual(second[0].side, "BUY")
        self.assertIn("crypto_directional_entry", second[0].reason)

    def test_crypto_interval_anchor_enters_matching_outcome_after_anchor_move(self):
        strategy = CryptoIntervalAnchorPaperStrategy(
            initial_cash=100,
            entry_notional=20,
            min_anchor_move_pct=0.001,
            min_market_age_seconds=20,
            min_seconds_to_close=15,
            min_net_settlement_roi=0.02,
            spot_provider=FakeSpotProvider([100.0, 100.2]),
            clock=lambda: 0,
            name="paper_target_crypto_interval_test",
        )
        portfolio = Portfolio(100)

        first = strategy.on_snapshots(
            crypto_pair_snapshots(1779608405, up_bid=0.48, up_ask=0.50, down_bid=0.50, down_ask=0.52),
            portfolio,
            rules_by_asset={"TOKEN-UP": MarketRules(), "TOKEN-DOWN": MarketRules()},
        )
        second = strategy.on_snapshots(
            crypto_pair_snapshots(1779608440, up_bid=0.68, up_ask=0.70, down_bid=0.30, down_ask=0.32),
            portfolio,
            rules_by_asset={"TOKEN-UP": MarketRules(), "TOKEN-DOWN": MarketRules()},
        )

        self.assertEqual(first, [])
        self.assertEqual(len(second), 1)
        self.assertEqual(second[0].asset, "TOKEN-UP")
        self.assertEqual(second[0].side, "BUY")
        self.assertIn("crypto_interval_anchor_entry", second[0].reason)
        self.assertIn("direction=UP", second[0].reason)

    def test_crypto_interval_anchor_rejects_late_first_observation(self):
        strategy = CryptoIntervalAnchorPaperStrategy(
            initial_cash=100,
            entry_notional=20,
            max_anchor_lag_seconds=30,
            spot_provider=FakeSpotProvider([100.0]),
            clock=lambda: 0,
            name="paper_target_crypto_interval_late_test",
        )

        signals = strategy.on_snapshots(
            crypto_pair_snapshots(1779608500, up_bid=0.68, up_ask=0.70, down_bid=0.30, down_ask=0.32),
            Portfolio(100),
            rules_by_asset={"TOKEN-UP": MarketRules(), "TOKEN-DOWN": MarketRules()},
        )

        self.assertEqual(signals, [])
        self.assertEqual(strategy.anchors_by_condition, {})

    def test_crypto_interval_anchor_supports_bnb_updown_slug(self):
        strategy = CryptoIntervalAnchorPaperStrategy(
            initial_cash=100,
            entry_notional=20,
            min_anchor_move_pct=0.001,
            min_market_age_seconds=20,
            min_net_settlement_roi=0.02,
            spot_provider=FakeSpotProvider([600.0, 601.0]),
            clock=lambda: 0,
            name="paper_target_crypto_interval_bnb_test",
        )
        portfolio = Portfolio(100)

        strategy.on_snapshots(
            crypto_pair_snapshots(
                1779608405,
                up_bid=0.48,
                up_ask=0.50,
                down_bid=0.50,
                down_ask=0.52,
                symbol="BNB",
                slug_symbol="bnb",
                interval="15m",
            ),
            portfolio,
            rules_by_asset={"TOKEN-UP": MarketRules(), "TOKEN-DOWN": MarketRules()},
        )
        signals = strategy.on_snapshots(
            crypto_pair_snapshots(
                1779608440,
                up_bid=0.68,
                up_ask=0.70,
                down_bid=0.30,
                down_ask=0.32,
                symbol="BNB",
                slug_symbol="bnb",
                interval="15m",
            ),
            portfolio,
            rules_by_asset={"TOKEN-UP": MarketRules(), "TOKEN-DOWN": MarketRules()},
        )

        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].asset, "TOKEN-UP")
        self.assertEqual(strategy.symbol_by_asset["TOKEN-UP"], "BNB")

    def test_crypto_interval_close_edge_waits_until_near_settlement(self):
        strategy = CryptoIntervalCloseEdgePaperStrategy(
            initial_cash=100,
            entry_notional=20,
            min_anchor_move_pct=0.001,
            min_market_age_seconds=210,
            min_seconds_to_close=5,
            max_seconds_to_close=60,
            min_net_settlement_roi=0.02,
            spot_provider=FakeSpotProvider([100.0, 100.1, 100.3]),
            clock=lambda: 0,
            name="paper_target_crypto_close_edge_test",
        )
        portfolio = Portfolio(100)
        rules = {"TOKEN-UP": MarketRules(), "TOKEN-DOWN": MarketRules()}

        anchor = strategy.on_snapshots(
            crypto_pair_snapshots(1779608405, up_bid=0.49, up_ask=0.50, down_bid=0.49, down_ask=0.50),
            portfolio,
            rules_by_asset=rules,
        )
        early = strategy.on_snapshots(
            crypto_pair_snapshots(1779608580, up_bid=0.64, up_ask=0.66, down_bid=0.34, down_ask=0.36),
            portfolio,
            rules_by_asset=rules,
        )
        near_close = strategy.on_snapshots(
            crypto_pair_snapshots(1779608660, up_bid=0.66, up_ask=0.68, down_bid=0.32, down_ask=0.34),
            portfolio,
            rules_by_asset=rules,
        )

        self.assertEqual(anchor, [])
        self.assertEqual(early, [])
        self.assertEqual(len(near_close), 1)
        self.assertEqual(near_close[0].asset, "TOKEN-UP")
        self.assertIn("crypto_interval_close_edge_entry", near_close[0].reason)

    def test_crypto_interval_book_skew_enters_dominant_active_outcome(self):
        strategy = CryptoIntervalBookSkewPaperStrategy(
            initial_cash=100,
            entry_notional=20,
            min_bid_price=0.65,
            max_ask_price=0.85,
            min_net_settlement_roi=0.10,
            min_market_age_seconds=20,
            max_seconds_to_close=240,
            clock=lambda: 0,
            name="paper_target_crypto_book_skew_test",
        )

        signals = strategy.on_snapshots(
            crypto_pair_snapshots(
                1779608460,
                up_bid=0.20,
                up_ask=0.22,
                down_bid=0.78,
                down_ask=0.80,
            ),
            Portfolio(100),
            rules_by_asset={"TOKEN-UP": MarketRules(), "TOKEN-DOWN": MarketRules()},
        )

        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].asset, "TOKEN-DOWN")
        self.assertIn("crypto_interval_book_skew_entry", signals[0].reason)
        self.assertIn("direction=DOWN", signals[0].reason)

    def test_crypto_directional_adapts_notional_to_l2_depth(self):
        def shallow_up_snapshot(timestamp):
            return [
                MarketSnapshot(
                    asset="TOKEN-UP",
                    condition_id="0xcrypto",
                    timestamp=timestamp,
                    book=OrderBook(
                        asset="TOKEN-UP",
                        timestamp=timestamp,
                        bids=(BookLevel(price=0.50, size=1000),),
                        asks=(
                            BookLevel(price=0.51, size=100),
                            BookLevel(price=0.65, size=5000),
                        ),
                    ),
                    title="Bitcoin Up or Down - May 24, 3:40AM-3:45AM ET",
                    slug="btc-updown-5m-1779608400",
                    outcome="Up",
                    outcome_index=0,
                )
            ]

        strategy = CryptoDirectionalPaperStrategy(
            initial_cash=2000,
            min_spot_move_pct=0.001,
            entry_notional=1000,
            capital_fraction=1.0,
            min_entry_notional=50,
            max_spread_pct=0.05,
            max_entry_impact_pct=0.05,
            spot_provider=FakeSpotProvider([100.0, 100.25]),
            name="paper_target_crypto_adaptive_test",
        )
        portfolio = Portfolio(2000)

        strategy.on_snapshots(shallow_up_snapshot(1000), portfolio)
        signals = strategy.on_snapshots(shallow_up_snapshot(1010), portfolio)

        self.assertEqual(len(signals), 1)
        self.assertLess(signals[0].target_notional, 1000)
        self.assertGreaterEqual(signals[0].target_notional, 50)

    def test_momentum_scalper_can_pass_target_verifier_on_synthetic_recording(self):
        recording = recording_for_prices([
            (1000, 0.50, 0.51),
            (1010, 0.53, 0.54),
            (1020, 0.62, 0.63),
        ])

        exit_code, verification = run_replay(recording, "momentum_scalper_goal")

        self.assertEqual(exit_code, 0)
        self.assertTrue(verification.passed, verification.to_dict())
        self.assertGreaterEqual(verification.final_roi, 0.10)
        self.assertTrue(verification.flat)

    def test_spread_capture_maker_can_pass_target_verifier_with_queue_proxy(self):
        recording = recording_for_prices([
            (1000, 0.50, 0.60),
            (1010, 0.50, 0.60),
            (1020, 0.50, 0.60),
            (1030, 0.50, 0.60),
        ])

        exit_code, verification = run_replay(
            recording,
            "spread_capture_maker_goal",
            extra_args=[
                "--maker-fill-mode",
                "queue_proxy",
                "--maker-queue-ahead-fraction",
                "0",
                "--maker-queue-decay",
                "1",
                "--maker-max-order-age-attempts",
                "4",
            ],
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue(verification.passed, verification.to_dict())
        self.assertGreaterEqual(verification.final_roi, 0.10)
        self.assertTrue(verification.flat)

    def test_outcome_basket_arb_can_pass_target_verifier_on_synthetic_recording(self):
        recording = paired_recording_for_prices([
            (1000, 0.43, 0.44, 0.43, 0.44),
            (1010, 0.50, 0.51, 0.50, 0.51),
        ])

        exit_code, verification = run_replay(recording, "outcome_basket_arb_goal")

        self.assertEqual(exit_code, 0)
        self.assertTrue(verification.passed, verification.to_dict())
        self.assertGreaterEqual(verification.final_roi, 0.10)
        self.assertTrue(verification.flat)


def _args():
    class Args:
        initial_cash = 100.0
        portfolio_target_roi = 0.10
        target_capital_fraction = 0.95
        take_profit_pct = 0.10
        target_allow_take_profit_before_target = False
        target_entry_notional = 0.0
        target_entry_execution_style = "taker"
        target_adaptive_entry_sizing = False
        target_min_entry_notional = 1.0
        target_max_spread_pct = 0.05
        target_max_entry_impact_pct = 0.05
        target_max_exit_price = 0.99
        target_min_book_imbalance = 0.05
        target_depth_window_pct = 0.03
        target_imbalance_weight = 0.10
        target_min_bid_price = None
        target_max_bid_price = None
        target_max_entry_mark_to_bid_loss_pct = None
        target_max_required_exit_distance_pct = None
        target_required_exit_distance_weight = 0.0
        target_min_score = None
        target_history_change_weight = 0.0
        target_min_momentum_observations = 2
        target_min_bid_improvement_pct = 0.001
        target_min_mid_improvement_pct = 0.001
        target_max_spread_widen_pct = 0.01
        target_cooldown_cycles_after_sell = 3
        target_max_hold_cycles = 0
        target_max_hold_min_progress_pct = 0.0
        target_max_hold_cooldown_cycles = 0
        target_max_positions = 1
        target_max_entries_per_cycle = 1
        target_diversify_by = "none"
        target_max_positions_per_group = 0
        target_watchlist_size = 0
        target_allowed_assets = ""
        stop_loss_pct = 0.03

    return Args()


def _variant_configs(variants):
    args = _args()
    args.target_variants = variants
    return target_variant_configs(args)


if __name__ == "__main__":
    unittest.main()
