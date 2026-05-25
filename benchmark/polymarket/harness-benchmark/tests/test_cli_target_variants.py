import unittest
from types import SimpleNamespace

from polypaper.cli import _run_metadata_config
from polypaper.strategies.paper.target import (
    CryptoIntervalCloseEdgePaperStrategy,
    CryptoIntervalAnchorPaperStrategy,
    CryptoIntervalBookSkewPaperStrategy,
    MakerRebateRotationStrategy,
    target_strategy_from_config,
    target_variant_configs,
)


def target_args(**overrides):
    values = {
        "target_variants": "balanced,compound_quality,low_friction_compound,volatile_compound,micro_compound,convex_tick,convex_basket_goal,maker_convex_basket_goal,rolling_momentum_maker_goal,breakout_goal,breakout_relaxed_goal,basket_goal,low_distance_goal,momentum_scalper_goal,crypto_directional_goal,crypto_interval_anchor_goal,crypto_interval_close_edge_goal,crypto_interval_book_skew_goal,spread_capture_maker_goal,maker_rebate_rotation_goal,outcome_basket_arb_goal,compound",
        "initial_cash": 100.0,
        "portfolio_target_roi": 0.10,
        "target_capital_fraction": 0.95,
        "take_profit_pct": 0.10,
        "target_allow_take_profit_before_target": False,
        "target_entry_notional": 0.0,
        "target_entry_execution_style": "taker",
        "target_adaptive_entry_sizing": False,
        "target_min_entry_notional": 1.0,
        "target_max_spread_pct": 0.05,
        "target_max_entry_impact_pct": 0.05,
        "target_max_exit_price": 0.99,
        "target_min_book_imbalance": 0.05,
        "target_depth_window_pct": 0.03,
        "target_imbalance_weight": 0.10,
        "target_min_bid_price": None,
        "target_max_bid_price": None,
        "target_max_entry_mark_to_bid_loss_pct": None,
        "target_max_required_exit_distance_pct": None,
        "target_required_exit_distance_weight": 0.0,
        "target_min_score": None,
        "target_history_change_weight": 0.0,
        "target_min_momentum_observations": 2,
        "target_min_bid_improvement_pct": 0.001,
        "target_min_mid_improvement_pct": 0.001,
        "target_max_spread_widen_pct": 0.01,
        "target_cooldown_cycles_after_sell": 3,
        "target_max_hold_cycles": 0,
        "target_max_hold_min_progress_pct": 0.0,
        "target_max_hold_cooldown_cycles": 0,
        "target_max_positions": 1,
        "target_max_entries_per_cycle": 1,
        "target_diversify_by": "none",
        "target_max_positions_per_group": 0,
        "target_watchlist_size": 0,
        "target_allowed_assets": "",
        "stop_loss_pct": 0.03,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class CliTargetVariantTests(unittest.TestCase):
    def test_compound_quality_variant_is_strict_by_default(self):
        variants = dict(target_variant_configs(target_args(target_variants="compound_quality")))

        quality = variants["compound_quality"]
        self.assertEqual(quality["take_profit_pct"], 0.01)
        self.assertTrue(quality["allow_take_profit_before_target"])
        self.assertEqual(quality["max_spread_pct"], 0.01)
        self.assertEqual(quality["max_entry_impact_pct"], 0.01)
        self.assertEqual(quality["max_entry_mark_to_bid_loss_pct"], 0.005)
        self.assertEqual(quality["max_required_exit_distance_pct"], 0.02)
        self.assertEqual(quality["required_exit_distance_weight"], 4.0)
        self.assertEqual(quality["min_score"], 0.0)
        self.assertEqual(quality["max_hold_cycles"], 5)
        self.assertEqual(quality["max_hold_cooldown_cycles"], 8)

    def test_volatile_compound_targets_midpriced_high_movement_markets(self):
        variants = dict(target_variant_configs(target_args(target_variants="volatile_compound")))

        volatile = variants["volatile_compound"]
        self.assertEqual(volatile["capital_fraction"], 0.50)
        self.assertEqual(volatile["take_profit_pct"], 0.10)
        self.assertTrue(volatile["allow_take_profit_before_target"])
        self.assertEqual(volatile["stop_loss_pct"], 0.15)
        self.assertEqual(volatile["max_spread_pct"], 0.03)
        self.assertEqual(volatile["max_entry_impact_pct"], 0.12)
        self.assertEqual(volatile["min_bid_price"], 0.20)
        self.assertEqual(volatile["max_bid_price"], 0.80)
        self.assertEqual(volatile["max_entry_mark_to_bid_loss_pct"], 0.05)
        self.assertEqual(volatile["max_required_exit_distance_pct"], 0.30)
        self.assertEqual(volatile["min_score"], 0.0)
        self.assertTrue(volatile["adaptive_entry_sizing"])
        self.assertEqual(volatile["min_entry_notional"], 25.0)
        self.assertEqual(volatile["min_momentum_observations"], 1)
        self.assertEqual(volatile["min_bid_improvement_pct"], 0.0)
        self.assertEqual(volatile["min_mid_improvement_pct"], 0.0)
        self.assertEqual(volatile["max_hold_cycles"], 12)
        self.assertEqual(volatile["max_hold_min_progress_pct"], 0.0)
        self.assertEqual(volatile["max_hold_cooldown_cycles"], 8)
        self.assertEqual(volatile["max_positions"], 3)
        self.assertEqual(volatile["diversify_by"], "title_prefix")
        self.assertEqual(volatile["max_positions_per_group"], 1)

    def test_volatile_compound_respects_explicit_diversification(self):
        variants = dict(
            target_variant_configs(
                target_args(
                    target_variants="volatile_compound",
                    target_diversify_by="condition",
                    target_max_positions_per_group=2,
                )
            )
        )

        volatile = variants["volatile_compound"]
        self.assertEqual(volatile["diversify_by"], "condition")
        self.assertEqual(volatile["max_positions_per_group"], 2)

    def test_volatile_compound_respects_explicit_price_band(self):
        variants = dict(
            target_variant_configs(
                target_args(
                    target_variants="volatile_compound",
                    target_min_bid_price=0.35,
                    target_max_bid_price=0.65,
                )
            )
        )

        volatile = variants["volatile_compound"]
        self.assertEqual(volatile["min_bid_price"], 0.35)
        self.assertEqual(volatile["max_bid_price"], 0.65)

    def test_low_friction_compound_uses_sweep_observed_middle_ground_defaults(self):
        variants = dict(target_variant_configs(target_args(target_variants="low_friction_compound")))

        low_friction = variants["low_friction_compound"]
        self.assertEqual(low_friction["capital_fraction"], 0.10)
        self.assertEqual(low_friction["take_profit_pct"], 0.01)
        self.assertTrue(low_friction["allow_take_profit_before_target"])
        self.assertEqual(low_friction["stop_loss_pct"], 0.08)
        self.assertTrue(low_friction["adaptive_entry_sizing"])
        self.assertEqual(low_friction["min_entry_notional"], 25.0)
        self.assertEqual(low_friction["max_spread_pct"], 0.03)
        self.assertEqual(low_friction["max_entry_impact_pct"], 0.05)
        self.assertEqual(low_friction["min_book_imbalance"], 0.0)
        self.assertEqual(low_friction["min_bid_price"], 0.20)
        self.assertEqual(low_friction["max_bid_price"], 0.80)
        self.assertEqual(low_friction["max_entry_mark_to_bid_loss_pct"], 0.05)
        self.assertEqual(low_friction["max_required_exit_distance_pct"], 0.10)
        self.assertEqual(low_friction["required_exit_distance_weight"], 1.0)
        self.assertEqual(low_friction["min_score"], 0.0)
        self.assertEqual(low_friction["min_momentum_observations"], 2)
        self.assertEqual(low_friction["min_bid_improvement_pct"], 0.001)
        self.assertEqual(low_friction["min_mid_improvement_pct"], 0.001)
        self.assertEqual(low_friction["max_hold_cycles"], 20)
        self.assertEqual(low_friction["max_positions"], 3)
        self.assertEqual(low_friction["diversify_by"], "title_prefix")

    def test_micro_compound_uses_sweep_informed_defaults(self):
        variants = dict(target_variant_configs(target_args(target_variants="micro_compound")))

        micro = variants["micro_compound"]
        self.assertEqual(micro["capital_fraction"], 0.20)
        self.assertEqual(micro["take_profit_pct"], 0.01)
        self.assertTrue(micro["allow_take_profit_before_target"])
        self.assertTrue(micro["adaptive_entry_sizing"])
        self.assertEqual(micro["max_spread_pct"], 0.03)
        self.assertEqual(micro["max_entry_impact_pct"], 0.08)
        self.assertEqual(micro["max_entry_mark_to_bid_loss_pct"], 0.08)
        self.assertEqual(micro["max_required_exit_distance_pct"], 0.20)
        self.assertEqual(micro["required_exit_distance_weight"], 2.0)
        self.assertEqual(micro["min_score"], 0.0)
        self.assertEqual(micro["max_hold_cycles"], 20)
        self.assertEqual(micro["max_positions"], 3)
        self.assertEqual(micro["diversify_by"], "title_prefix")

    def test_strategy_v1_selected_group_matches_final_report_families(self):
        variants = target_variant_configs(target_args(target_variants="strategy_v1_selected"))
        names = [name for name, _config in variants]

        self.assertEqual(len(names), 72)
        self.assertEqual(
            sum(name.startswith("crypto_interval_anchor_grid_") for name in names),
            24,
        )
        self.assertEqual(
            sum(name.startswith("crypto_interval_book_skew_grid_") for name in names),
            48,
        )
        self.assertEqual(names[0], "crypto_interval_anchor_grid_01")
        self.assertEqual(names[23], "crypto_interval_anchor_grid_24")
        self.assertEqual(names[24], "crypto_interval_book_skew_grid_01")
        self.assertIn("crypto_interval_book_skew_grid_72", names)
        self.assertNotIn("crypto_interval_anchor_grid_25", names)
        self.assertNotIn("crypto_interval_book_skew_grid_03", names)

    def test_convex_tick_uses_low_price_high_movement_defaults(self):
        variants = dict(target_variant_configs(target_args(target_variants="convex_tick")))

        convex = variants["convex_tick"]
        self.assertEqual(convex["capital_fraction"], 0.95)
        self.assertEqual(convex["take_profit_pct"], 0.10)
        self.assertTrue(convex["allow_take_profit_before_target"])
        self.assertEqual(convex["stop_loss_pct"], 0.60)
        self.assertTrue(convex["adaptive_entry_sizing"])
        self.assertEqual(convex["min_entry_notional"], 5.0)
        self.assertEqual(convex["max_spread_pct"], 0.15)
        self.assertEqual(convex["max_entry_impact_pct"], 0.25)
        self.assertEqual(convex["min_book_imbalance"], -1.0)
        self.assertEqual(convex["min_bid_price"], 0.005)
        self.assertEqual(convex["max_bid_price"], 0.20)
        self.assertEqual(convex["max_entry_mark_to_bid_loss_pct"], 0.25)
        self.assertEqual(convex["max_required_exit_distance_pct"], 0.75)
        self.assertEqual(convex["required_exit_distance_weight"], 0.5)
        self.assertEqual(convex["min_score"], -1.0)
        self.assertEqual(convex["min_momentum_observations"], 2)
        self.assertEqual(convex["max_hold_cycles"], 6)
        self.assertEqual(convex["max_positions"], 5)
        self.assertEqual(convex["diversify_by"], "condition")

    def test_convex_basket_goal_splits_low_price_convex_exposure(self):
        args = target_args(target_variants="convex_basket_goal")
        variants = dict(target_variant_configs(args))

        convex = variants["convex_basket_goal"]
        self.assertAlmostEqual(convex["entry_notional"], args.initial_cash / 4.0)
        self.assertEqual(convex["capital_fraction"], 1.0)
        self.assertEqual(convex["take_profit_pct"], 0.20)
        self.assertTrue(convex["allow_take_profit_before_target"])
        self.assertEqual(convex["stop_loss_pct"], 0.60)
        self.assertTrue(convex["adaptive_entry_sizing"])
        self.assertEqual(convex["min_entry_notional"], 5.0)
        self.assertEqual(convex["max_spread_pct"], 0.15)
        self.assertEqual(convex["max_entry_impact_pct"], 0.25)
        self.assertEqual(convex["min_bid_price"], 0.02)
        self.assertEqual(convex["max_bid_price"], 0.25)
        self.assertEqual(convex["max_entry_mark_to_bid_loss_pct"], 0.08)
        self.assertEqual(convex["max_required_exit_distance_pct"], 0.35)
        self.assertEqual(convex["max_positions"], 4)
        self.assertEqual(convex["max_entries_per_cycle"], 4)
        self.assertEqual(convex["diversify_by"], "condition")
        self.assertEqual(convex["watchlist_size"], 24)
        self.assertEqual(convex["history_change_weight"], 3.0)

    def test_maker_convex_basket_goal_uses_passive_entry(self):
        args = target_args(target_variants="maker_convex_basket_goal")
        variants = dict(target_variant_configs(args))

        maker = variants["maker_convex_basket_goal"]
        self.assertAlmostEqual(maker["entry_notional"], args.initial_cash / 4.0)
        self.assertEqual(maker["entry_execution_style"], "maker")
        self.assertEqual(maker["max_entry_mark_to_bid_loss_pct"], 0.01)
        self.assertEqual(maker["max_positions"], 4)
        self.assertEqual(maker["max_entries_per_cycle"], 4)
        self.assertEqual(maker["watchlist_size"], 24)
        self.assertEqual(maker["history_change_weight"], 3.0)

        strategy = target_strategy_from_config(args, "maker_convex_basket_goal", maker)
        self.assertEqual(strategy.entry_execution_style, "maker")
        self.assertEqual(strategy.max_entries_per_cycle, 4)

    def test_rolling_momentum_maker_goal_rotates_stale_passive_positions(self):
        args = target_args(target_variants="rolling_momentum_maker_goal")
        variants = dict(target_variant_configs(args))

        rolling = variants["rolling_momentum_maker_goal"]
        self.assertEqual(rolling["entry_execution_style"], "maker")
        self.assertEqual(rolling["entry_notional"], args.initial_cash)
        self.assertTrue(rolling["adaptive_entry_sizing"])
        self.assertEqual(rolling["min_entry_notional"], 50.0)
        self.assertEqual(rolling["max_positions"], 1)
        self.assertEqual(rolling["max_entries_per_cycle"], 1)
        self.assertEqual(rolling["max_hold_cycles"], 4)
        self.assertEqual(rolling["max_hold_min_progress_pct"], 0.10)
        self.assertEqual(rolling["max_hold_cooldown_cycles"], 6)
        self.assertEqual(rolling["cooldown_cycles_after_sell"], 0)
        self.assertEqual(rolling["history_change_weight"], 10.0)

        strategy = target_strategy_from_config(args, "rolling_momentum_maker_goal", rolling)
        self.assertEqual(strategy.entry_execution_style, "maker")
        self.assertEqual(strategy.max_hold_min_progress_pct, 0.10)

    def test_low_distance_goal_uses_full_capital_tight_high_price_defaults(self):
        variants = dict(target_variant_configs(target_args(target_variants="low_distance_goal")))

        low_distance = variants["low_distance_goal"]
        self.assertEqual(low_distance["capital_fraction"], 1.0)
        self.assertEqual(low_distance["take_profit_pct"], 0.10)
        self.assertFalse(low_distance["allow_take_profit_before_target"])
        self.assertEqual(low_distance["stop_loss_pct"], 0.30)
        self.assertTrue(low_distance["adaptive_entry_sizing"])
        self.assertEqual(low_distance["min_entry_notional"], 5.0)
        self.assertEqual(low_distance["max_spread_pct"], 0.05)
        self.assertEqual(low_distance["max_entry_impact_pct"], 0.05)
        self.assertEqual(low_distance["min_book_imbalance"], -1.0)
        self.assertEqual(low_distance["min_bid_price"], 0.50)
        self.assertEqual(low_distance["max_bid_price"], 0.85)
        self.assertEqual(low_distance["max_entry_mark_to_bid_loss_pct"], 0.03)
        self.assertEqual(low_distance["max_required_exit_distance_pct"], 0.15)
        self.assertEqual(low_distance["required_exit_distance_weight"], 10.0)
        self.assertEqual(low_distance["min_score"], -1.0)
        self.assertEqual(low_distance["min_momentum_observations"], 1)

    def test_breakout_goal_requires_momentum_and_uses_watchlist(self):
        variants = dict(target_variant_configs(target_args(target_variants="breakout_goal")))

        breakout = variants["breakout_goal"]
        self.assertEqual(breakout["capital_fraction"], 1.0)
        self.assertTrue(breakout["adaptive_entry_sizing"])
        self.assertEqual(breakout["min_bid_price"], 0.50)
        self.assertEqual(breakout["max_bid_price"], 0.85)
        self.assertEqual(breakout["max_entry_mark_to_bid_loss_pct"], 0.03)
        self.assertEqual(breakout["max_required_exit_distance_pct"], 0.15)
        self.assertEqual(breakout["min_momentum_observations"], 2)
        self.assertEqual(breakout["min_bid_improvement_pct"], 0.001)
        self.assertEqual(breakout["min_mid_improvement_pct"], 0.001)
        self.assertEqual(breakout["watchlist_size"], 12)

    def test_breakout_relaxed_goal_allows_flat_confirmation(self):
        variants = dict(
            target_variant_configs(
                target_args(
                    target_variants="breakout_relaxed_goal",
                    target_min_bid_improvement_pct=0.0,
                    target_min_mid_improvement_pct=0.0,
                )
            )
        )

        relaxed = variants["breakout_relaxed_goal"]
        self.assertEqual(relaxed["capital_fraction"], 1.0)
        self.assertTrue(relaxed["adaptive_entry_sizing"])
        self.assertEqual(relaxed["min_momentum_observations"], 2)
        self.assertEqual(relaxed["min_bid_improvement_pct"], 0.0)
        self.assertEqual(relaxed["min_mid_improvement_pct"], 0.0)
        self.assertEqual(relaxed["watchlist_size"], 12)

    def test_basket_goal_splits_capital_across_diversified_positions(self):
        args = target_args(
            target_variants="basket_goal",
            target_min_bid_improvement_pct=0.0,
            target_min_mid_improvement_pct=0.0,
        )
        variants = dict(target_variant_configs(args))

        basket = variants["basket_goal"]
        self.assertAlmostEqual(basket["entry_notional"], args.initial_cash / 3.0)
        self.assertEqual(basket["capital_fraction"], 1.0)
        self.assertEqual(basket["take_profit_pct"], 0.12)
        self.assertTrue(basket["allow_take_profit_before_target"])
        self.assertTrue(basket["adaptive_entry_sizing"])
        self.assertEqual(basket["min_entry_notional"], 5.0)
        self.assertEqual(basket["max_spread_pct"], 0.05)
        self.assertEqual(basket["min_bid_price"], 0.20)
        self.assertEqual(basket["max_bid_price"], 0.85)
        self.assertEqual(basket["max_entry_mark_to_bid_loss_pct"], 0.03)
        self.assertEqual(basket["max_required_exit_distance_pct"], 0.18)
        self.assertEqual(basket["required_exit_distance_weight"], 3.0)
        self.assertEqual(basket["min_score"], -1.0)
        self.assertEqual(basket["min_momentum_observations"], 2)
        self.assertEqual(basket["max_positions"], 3)
        self.assertEqual(basket["diversify_by"], "condition")
        self.assertEqual(basket["max_positions_per_group"], 1)
        self.assertEqual(basket["watchlist_size"], 18)
        self.assertEqual(basket["history_change_weight"], 2.0)

        strategy = target_strategy_from_config(args, "basket_goal", basket)
        self.assertAlmostEqual(strategy.entry_notional, args.initial_cash / 3.0)
        self.assertEqual(strategy.history_change_weight, 2.0)

    def test_basket_goal_respects_explicit_entry_notional(self):
        variants = dict(
            target_variant_configs(
                target_args(
                    target_variants="basket_goal",
                    target_entry_notional=25.0,
                )
            )
        )

        self.assertEqual(variants["basket_goal"]["entry_notional"], 25.0)

    def test_balanced_variant_respects_adaptive_sizing_args(self):
        variants = dict(
            target_variant_configs(
                target_args(
                    target_variants="balanced",
                    target_adaptive_entry_sizing=True,
                    target_min_entry_notional=50.0,
                )
            )
        )

        balanced = variants["balanced"]
        self.assertTrue(balanced["adaptive_entry_sizing"])
        self.assertEqual(balanced["min_entry_notional"], 50.0)

    def test_balanced_variant_respects_explicit_min_score(self):
        variants = dict(
            target_variant_configs(
                target_args(
                    target_variants="balanced",
                    target_min_score=0.05,
                )
            )
        )

        balanced = variants["balanced"]
        self.assertEqual(balanced["min_score"], 0.05)

    def test_target_variant_respects_allowed_assets_scope(self):
        strategy = target_strategy_from_config(
            target_args(target_allowed_assets="TOKEN-A,TOKEN-B"),
            "balanced",
            dict(target_variant_configs(target_args(target_variants="balanced")))["balanced"],
        )

        self.assertEqual(strategy.allowed_assets, {"TOKEN-A", "TOKEN-B"})

    def test_target_variant_without_allowed_assets_is_unrestricted(self):
        strategy = target_strategy_from_config(
            target_args(target_allowed_assets=""),
            "balanced",
            dict(target_variant_configs(target_args(target_variants="balanced")))["balanced"],
        )

        self.assertIsNone(strategy.allowed_assets)

    def test_compound_quality_respects_explicit_quality_overrides(self):
        variants = dict(
            target_variant_configs(
                target_args(
                    target_variants="compound_quality",
                    target_max_entry_mark_to_bid_loss_pct=0.003,
                    target_max_required_exit_distance_pct=0.015,
                    target_required_exit_distance_weight=6.0,
                    target_min_score=0.02,
                    target_max_hold_cycles=7,
                    target_max_hold_cooldown_cycles=11,
                )
            )
        )

        quality = variants["compound_quality"]
        self.assertEqual(quality["max_entry_mark_to_bid_loss_pct"], 0.003)
        self.assertEqual(quality["max_required_exit_distance_pct"], 0.015)
        self.assertEqual(quality["required_exit_distance_weight"], 6.0)
        self.assertEqual(quality["min_score"], 0.02)
        self.assertEqual(quality["max_hold_cycles"], 7)
        self.assertEqual(quality["max_hold_cooldown_cycles"], 11)

    def test_requested_order_includes_compound_quality(self):
        variants = target_variant_configs(target_args())
        self.assertEqual(
            [name for name, _ in variants],
            [
                "balanced",
                "compound_quality",
                "low_friction_compound",
                "volatile_compound",
                "micro_compound",
                "convex_tick",
                "convex_basket_goal",
                "maker_convex_basket_goal",
                "rolling_momentum_maker_goal",
                "breakout_goal",
                "breakout_relaxed_goal",
                "basket_goal",
                "low_distance_goal",
                "momentum_scalper_goal",
                "crypto_directional_goal",
                "crypto_interval_anchor_goal",
                "crypto_interval_close_edge_goal",
                "crypto_interval_book_skew_goal",
                "spread_capture_maker_goal",
                "maker_rebate_rotation_goal",
                "outcome_basket_arb_goal",
                "compound",
            ],
        )

    def test_online_goal_grid_expands_scalper_maker_and_basket_candidates(self):
        variants = target_variant_configs(target_args(target_variants="online_goal_grid"))
        names = [name for name, _ in variants]
        configs = dict(variants)

        self.assertEqual(len(names), 272)
        self.assertEqual(len(set(names)), 272)
        self.assertTrue(names[0].startswith("momentum_scalper_grid_"))
        self.assertTrue(any(name.startswith("crypto_directional_grid_") for name in names))
        self.assertTrue(any(name.startswith("crypto_interval_anchor_grid_") for name in names))
        self.assertTrue(any(name.startswith("crypto_interval_close_edge_grid_") for name in names))
        self.assertTrue(any(name.startswith("crypto_interval_book_skew_grid_") for name in names))
        self.assertTrue(any(name.startswith("spread_capture_maker_grid_") for name in names))
        self.assertTrue(any(name.startswith("maker_rebate_rotation_grid_") for name in names))
        self.assertTrue(any(name.startswith("outcome_basket_arb_grid_") for name in names))
        self.assertEqual(configs["momentum_scalper_grid_01"]["strategy_type"], "momentum_scalper")
        self.assertEqual(configs["crypto_directional_grid_01"]["strategy_type"], "crypto_directional")
        self.assertEqual(configs["crypto_interval_anchor_grid_01"]["strategy_type"], "crypto_interval_anchor")
        self.assertEqual(configs["crypto_interval_anchor_grid_03"]["max_anchor_lag_seconds"], 180)
        self.assertEqual(configs["crypto_interval_close_edge_grid_01"]["strategy_type"], "crypto_interval_close_edge")
        self.assertEqual(configs["crypto_interval_close_edge_grid_01"]["max_seconds_to_close"], 45)
        self.assertEqual(configs["crypto_interval_book_skew_grid_01"]["strategy_type"], "crypto_interval_book_skew")
        self.assertEqual(configs["crypto_interval_book_skew_grid_01"]["max_seconds_to_close"], 180)
        self.assertEqual(configs["spread_capture_maker_grid_01"]["strategy_type"], "spread_capture_maker")
        self.assertEqual(configs["spread_capture_maker_grid_02"]["max_positions"], 3)
        self.assertEqual(configs["spread_capture_maker_grid_02"]["max_entries_per_cycle"], 2)
        self.assertEqual(configs["spread_capture_maker_grid_01"]["take_profit_pct"], 0.003)
        self.assertEqual(configs["maker_rebate_rotation_grid_01"]["strategy_type"], "maker_rebate_rotation")
        self.assertEqual(configs["maker_rebate_rotation_grid_01"]["min_round_trip_edge_pct"], 0.006)
        self.assertEqual(configs["maker_rebate_rotation_grid_01"]["min_touch_depth_notional"], 50.0)
        self.assertEqual(configs["outcome_basket_arb_grid_01"]["strategy_type"], "outcome_basket_arb")
        self.assertEqual(configs["momentum_scalper_grid_01"]["diagnostic_limit"], 5)

    def test_grid_variants_build_dedicated_strategies(self):
        args = target_args(target_variants="online_goal_grid")
        variants = dict(target_variant_configs(args))

        momentum = target_strategy_from_config(args, "momentum_scalper_grid_01", variants["momentum_scalper_grid_01"])
        crypto = target_strategy_from_config(args, "crypto_directional_grid_01", variants["crypto_directional_grid_01"])
        interval = target_strategy_from_config(
            args,
            "crypto_interval_anchor_grid_01",
            variants["crypto_interval_anchor_grid_01"],
        )
        close_edge = target_strategy_from_config(
            args,
            "crypto_interval_close_edge_grid_01",
            variants["crypto_interval_close_edge_grid_01"],
        )
        book_skew = target_strategy_from_config(
            args,
            "crypto_interval_book_skew_grid_01",
            variants["crypto_interval_book_skew_grid_01"],
        )
        maker = target_strategy_from_config(
            args,
            "spread_capture_maker_grid_01",
            variants["spread_capture_maker_grid_01"],
        )
        rebate_rotation = target_strategy_from_config(
            args,
            "maker_rebate_rotation_grid_01",
            variants["maker_rebate_rotation_grid_01"],
        )
        basket = target_strategy_from_config(
            args,
            "outcome_basket_arb_grid_01",
            variants["outcome_basket_arb_grid_01"],
        )

        self.assertEqual(momentum.name, "paper_target_momentum_scalper_grid_01")
        self.assertEqual(momentum.diagnostic_limit, 5)
        self.assertEqual(crypto.name, "paper_target_crypto_directional_grid_01")
        self.assertEqual(crypto.diagnostic_limit, 5)
        self.assertIsInstance(interval, CryptoIntervalAnchorPaperStrategy)
        self.assertEqual(interval.name, "paper_target_crypto_interval_anchor_grid_01")
        self.assertEqual(interval.diagnostic_limit, 5)
        self.assertIsInstance(close_edge, CryptoIntervalCloseEdgePaperStrategy)
        self.assertEqual(close_edge.name, "paper_target_crypto_interval_close_edge_grid_01")
        self.assertEqual(close_edge.max_seconds_to_close, 45)
        self.assertIsInstance(book_skew, CryptoIntervalBookSkewPaperStrategy)
        self.assertEqual(book_skew.name, "paper_target_crypto_interval_book_skew_grid_01")
        self.assertEqual(book_skew.max_seconds_to_close, 180)
        self.assertEqual(maker.entry_execution_style, "maker")
        self.assertEqual(maker.diagnostic_limit, 5)
        self.assertIsInstance(rebate_rotation, MakerRebateRotationStrategy)
        self.assertEqual(rebate_rotation.name, "paper_target_maker_rebate_rotation_grid_01")
        self.assertEqual(rebate_rotation.diagnostic_limit, 5)
        self.assertEqual(basket.diagnostic_limit, 5)

    def test_variant_groups_can_be_combined_with_named_variants(self):
        variants = target_variant_configs(target_args(target_variants="momentum_scalper_goal,spread_capture_maker_grid"))
        names = [name for name, _ in variants]

        self.assertEqual(names[0], "momentum_scalper_goal")
        self.assertEqual(len(names), 37)
        self.assertTrue(all(name == "momentum_scalper_goal" or name.startswith("spread_capture_maker_grid_") for name in names))

    def test_run_metadata_config_records_execution_profile(self):
        config = _run_metadata_config(
            SimpleNamespace(
                max_cycles=1,
                min_passing_strategies=2,
                detection_delay_seconds=1,
                polling_delay_seconds=5,
                decision_delay_seconds=1,
                execution_delay_seconds=2,
                slippage_bps=0.5,
                fee_rate=0.03,
                fee_exponent=1.0,
                tick_size=0.001,
                min_order_size=5,
            ),
            ["paper_target_a", "paper_target_b"],
        )

        self.assertEqual(config["detection_delay_seconds"], 1)
        self.assertEqual(config["polling_delay_seconds"], 5)
        self.assertEqual(config["decision_delay_seconds"], 1)
        self.assertEqual(config["execution_delay_seconds"], 2)
        self.assertEqual(config["slippage_bps"], 0.5)
        self.assertEqual(config["fee_rate"], 0.03)
        self.assertEqual(config["fee_exponent"], 1.0)
        self.assertEqual(config["tick_size"], 0.001)
        self.assertEqual(config["min_order_size"], 5)


if __name__ == "__main__":
    unittest.main()
