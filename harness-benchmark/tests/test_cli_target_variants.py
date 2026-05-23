import unittest
from types import SimpleNamespace

from polypaper.strategies.paper.target import target_variant_configs


def target_args(**overrides):
    values = {
        "target_variants": "balanced,compound_quality,low_friction_compound,volatile_compound,micro_compound,convex_tick,compound",
        "target_capital_fraction": 0.95,
        "take_profit_pct": 0.10,
        "target_allow_take_profit_before_target": False,
        "target_adaptive_entry_sizing": False,
        "target_min_entry_notional": 1.0,
        "target_max_spread_pct": 0.05,
        "target_max_entry_impact_pct": 0.05,
        "target_min_book_imbalance": 0.05,
        "target_min_bid_price": None,
        "target_max_bid_price": None,
        "target_max_entry_mark_to_bid_loss_pct": None,
        "target_max_required_exit_distance_pct": None,
        "target_required_exit_distance_weight": 0.0,
        "target_min_score": None,
        "target_min_momentum_observations": 2,
        "target_min_bid_improvement_pct": 0.001,
        "target_min_mid_improvement_pct": 0.001,
        "target_cooldown_cycles_after_sell": 3,
        "target_max_hold_cycles": 0,
        "target_max_hold_min_progress_pct": 0.0,
        "target_max_hold_cooldown_cycles": 0,
        "target_max_positions": 1,
        "target_diversify_by": "none",
        "target_max_positions_per_group": 0,
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

    def test_convex_tick_uses_low_price_high_movement_defaults(self):
        variants = dict(target_variant_configs(target_args(target_variants="convex_tick")))

        convex = variants["convex_tick"]
        self.assertEqual(convex["capital_fraction"], 0.50)
        self.assertEqual(convex["take_profit_pct"], 0.20)
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
                "compound",
            ],
        )


if __name__ == "__main__":
    unittest.main()
