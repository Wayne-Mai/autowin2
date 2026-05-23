import unittest
from types import SimpleNamespace

from polypaper.cli import _parse_float_list, _target_strategy_from_sweep_result, _unique_sweep_assets
from polypaper.models import BookLevel, MarketSnapshot, OrderBook
from polypaper.simulator import MarketRules
from polypaper.strategies.paper.target import (
    sweep_target_opportunities,
    target_sweep_configs,
)


def snapshot_with_book(bid, ask):
    return MarketSnapshot(
        asset="TOKEN-YES",
        condition_id="0xcondition",
        timestamp=1000,
        book=OrderBook(
            asset="TOKEN-YES",
            timestamp=1000,
            bids=(BookLevel(price=bid, size=1000),),
            asks=(BookLevel(price=ask, size=1000),),
        ),
        title="Sweep fixture",
        outcome="Yes",
    )


class TargetSweepTests(unittest.TestCase):
    def test_target_sweep_configs_expands_grid(self):
        configs = target_sweep_configs(
            take_profit_pcts=[0.01, 0.02],
            capital_fractions=[0.1],
            max_entry_mark_to_bid_loss_pcts=[0.03],
            max_required_exit_distance_pcts=[0.05, 0.10],
            required_exit_distance_weights=[1.0],
            min_scores=[0.0],
        )

        self.assertEqual(len(configs), 4)
        self.assertEqual(configs[0].take_profit_pct, 0.01)
        self.assertEqual(configs[-1].max_required_exit_distance_pct, 0.10)

    def test_sweep_target_opportunities_finds_viable_current_book_config(self):
        configs = target_sweep_configs(
            take_profit_pcts=[0.02],
            capital_fractions=[0.5],
            max_entry_mark_to_bid_loss_pcts=[0.05],
            max_required_exit_distance_pcts=[0.10],
            required_exit_distance_weights=[1.0],
            min_scores=[0.0],
        )

        results = sweep_target_opportunities(
            snapshots=[snapshot_with_book(0.49, 0.50)],
            rules_by_asset={"TOKEN-YES": MarketRules()},
            configs=configs,
            initial_cash=1000,
            portfolio_target_roi=0.10,
            min_entry_notional=25,
            max_spread_pct=0.05,
            max_entry_impact_pct=0.05,
            max_exit_price=0.99,
            min_book_imbalance=-1.0,
            depth_window_pct=0.03,
            imbalance_weight=0.10,
            min_bid_price=0.20,
            max_bid_price=0.80,
            top=10,
        )

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].opportunity.viable)
        self.assertEqual(results[0].config.take_profit_pct, 0.02)

    def test_parse_float_list_rejects_empty_values(self):
        self.assertEqual(_parse_float_list("0.01, 0.02"), [0.01, 0.02])
        with self.assertRaises(ValueError):
            _parse_float_list(" , ")

    def test_sweep_result_builds_runnable_target_strategy(self):
        configs = target_sweep_configs(
            take_profit_pcts=[0.02],
            capital_fractions=[0.5],
            max_entry_mark_to_bid_loss_pcts=[0.05],
            max_required_exit_distance_pcts=[0.10],
            required_exit_distance_weights=[1.0],
            min_scores=[0.0],
        )
        result = sweep_target_opportunities(
            snapshots=[snapshot_with_book(0.49, 0.50)],
            rules_by_asset={"TOKEN-YES": MarketRules()},
            configs=configs,
            initial_cash=1000,
            portfolio_target_roi=0.10,
            min_entry_notional=25,
            max_spread_pct=0.05,
            max_entry_impact_pct=0.05,
            max_exit_price=0.99,
            min_book_imbalance=-1.0,
            depth_window_pct=0.03,
            imbalance_weight=0.10,
            min_bid_price=0.20,
            max_bid_price=0.80,
            top=1,
        )[0]

        strategy = _target_strategy_from_sweep_result(
            SimpleNamespace(
                initial_cash=1000,
                portfolio_target_roi=0.10,
                stop_loss_pct=0.15,
                target_min_entry_notional=25,
                target_max_spread_pct=0.05,
                target_max_entry_impact_pct=0.05,
                target_max_exit_price=0.99,
                target_min_book_imbalance=-1.0,
                target_depth_window_pct=0.03,
                target_imbalance_weight=0.10,
                target_min_bid_price=0.20,
                target_max_bid_price=0.80,
                target_min_momentum_observations=1,
                target_min_bid_improvement_pct=0.0,
                target_min_mid_improvement_pct=0.0,
                target_max_spread_widen_pct=0.01,
                target_cooldown_cycles_after_sell=1,
                target_max_hold_cycles=0,
                target_max_hold_min_progress_pct=0.0,
                target_max_hold_cooldown_cycles=0,
            ),
            result,
            index=3,
        )

        self.assertTrue(strategy.name.startswith("paper_sweep_003"))
        self.assertEqual(strategy.take_profit_pct, 0.02)
        self.assertEqual(strategy.capital_fraction, 0.5)
        self.assertTrue(strategy.adaptive_entry_sizing)
        self.assertEqual(strategy.max_entry_mark_to_bid_loss_pct, 0.05)
        self.assertEqual(strategy.allowed_assets, {"TOKEN-YES"})

    def test_unique_sweep_assets_selects_distinct_assets(self):
        configs = target_sweep_configs(
            take_profit_pcts=[0.02],
            capital_fractions=[0.5],
            max_entry_mark_to_bid_loss_pcts=[0.05],
            max_required_exit_distance_pcts=[0.10],
            required_exit_distance_weights=[1.0],
            min_scores=[0.0],
        )
        first = sweep_target_opportunities(
            snapshots=[snapshot_with_book(0.49, 0.50)],
            rules_by_asset={"TOKEN-YES": MarketRules()},
            configs=configs,
            initial_cash=1000,
            portfolio_target_roi=0.10,
            min_entry_notional=25,
            max_spread_pct=0.05,
            max_entry_impact_pct=0.05,
            max_exit_price=0.99,
            min_book_imbalance=-1.0,
            depth_window_pct=0.03,
            imbalance_weight=0.10,
            min_bid_price=0.20,
            max_bid_price=0.80,
            top=1,
        )[0]
        other_snapshot = MarketSnapshot(
            asset="TOKEN-NO",
            condition_id="0xcondition2",
            timestamp=1000,
            book=OrderBook(
                asset="TOKEN-NO",
                timestamp=1000,
                bids=(BookLevel(price=0.49, size=1000),),
                asks=(BookLevel(price=0.50, size=1000),),
            ),
            title="Other fixture",
            outcome="No",
        )
        second = sweep_target_opportunities(
            snapshots=[other_snapshot],
            rules_by_asset={"TOKEN-NO": MarketRules()},
            configs=configs,
            initial_cash=1000,
            portfolio_target_roi=0.10,
            min_entry_notional=25,
            max_spread_pct=0.05,
            max_entry_impact_pct=0.05,
            max_exit_price=0.99,
            min_book_imbalance=-1.0,
            depth_window_pct=0.03,
            imbalance_weight=0.10,
            min_bid_price=0.20,
            max_bid_price=0.80,
            top=1,
        )[0]

        selected = _unique_sweep_assets([first, first, second], limit=2)

        self.assertEqual([item.opportunity.asset for item in selected], ["TOKEN-YES", "TOKEN-NO"])


if __name__ == "__main__":
    unittest.main()
