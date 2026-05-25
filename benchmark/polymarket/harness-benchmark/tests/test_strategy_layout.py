import unittest
from types import SimpleNamespace

from polypaper.models import TraderTrade
from polypaper.strategies.paper import (
    NoTradePaperStrategy as PublicNoTradePaperStrategy,
    RandomMarketTakerStrategy as PublicRandomMarketTakerStrategy,
    TargetProfitPaperStrategy as PublicTargetProfitPaperStrategy,
    default_paper_strategies,
)
from polypaper.strategies.paper.baseline import (
    NoTradePaperStrategy,
    RandomMarketTakerStrategy,
)
from polypaper.strategies.paper.baselines import (
    NoTradePaperStrategy as LegacyNoTradePaperStrategy,
    RandomMarketTakerStrategy as LegacyRandomMarketTakerStrategy,
)
from polypaper.strategies.paper.target import TargetProfitPaperStrategy
from polypaper.strategies.paper.target_profit import (
    TargetProfitPaperStrategy as LegacyTargetProfitPaperStrategy,
)
from polypaper.baselines import NoTradeBaseline as RootNoTradeBaseline
from polypaper.strategies.replay import (
    NoTradeBaseline as PublicReplayNoTradeBaseline,
    RandomSameTurnoverBaseline as PublicRandomSameTurnoverBaseline,
    default_replay_strategies,
)
from polypaper.strategies.replay.baseline import (
    NoTradeBaseline,
    RandomSameTurnoverBaseline,
)
from polypaper.strategies.replay.baselines import (
    NoTradeBaseline as LegacyReplayNoTradeBaseline,
    RandomSameTurnoverBaseline as LegacyRandomSameTurnoverBaseline,
)


def _paper_args(**overrides):
    values = {
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
        "target_profit_agents": 1,
        "random_agents": 1,
        "seed": 1,
        "trade_probability": 0.5,
        "max_notional": 10.0,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class StrategyLayoutTests(unittest.TestCase):
    def test_paper_baseline_package_is_public_import_surface(self):
        self.assertIs(PublicNoTradePaperStrategy, NoTradePaperStrategy)
        self.assertIs(PublicRandomMarketTakerStrategy, RandomMarketTakerStrategy)

    def test_legacy_paper_baseline_module_is_compatibility_shim(self):
        self.assertIs(LegacyNoTradePaperStrategy, NoTradePaperStrategy)
        self.assertIs(LegacyRandomMarketTakerStrategy, RandomMarketTakerStrategy)

    def test_target_strategy_package_remains_public_import_surface(self):
        self.assertIs(PublicTargetProfitPaperStrategy, TargetProfitPaperStrategy)
        self.assertIs(LegacyTargetProfitPaperStrategy, TargetProfitPaperStrategy)

    def test_replay_baseline_package_is_public_import_surface(self):
        self.assertIs(PublicReplayNoTradeBaseline, NoTradeBaseline)
        self.assertIs(PublicRandomSameTurnoverBaseline, RandomSameTurnoverBaseline)

    def test_legacy_replay_baseline_modules_are_compatibility_shims(self):
        self.assertIs(LegacyReplayNoTradeBaseline, NoTradeBaseline)
        self.assertIs(LegacyRandomSameTurnoverBaseline, RandomSameTurnoverBaseline)
        self.assertIs(RootNoTradeBaseline, NoTradeBaseline)

    def test_paper_suite_factory_lives_in_strategy_package(self):
        strategies = default_paper_strategies(_paper_args(target_profit_agents=2, random_agents=2))

        self.assertEqual(
            [strategy.name for strategy in strategies],
            [
                "paper_no_trade",
                "paper_target_profit_0001",
                "paper_target_profit_0002",
                "paper_random_market_taker_0001",
                "paper_random_market_taker_0002",
            ],
        )

    def test_replay_suite_factory_lives_in_strategy_package(self):
        strategies = default_replay_strategies(
            [
                TraderTrade(
                    wallet="0xaaa",
                    timestamp=1000,
                    side="BUY",
                    asset="TOKEN",
                    condition_id="0xcondition",
                    price=0.5,
                    size=10,
                    category="politics",
                )
            ],
            seed=7,
        )

        self.assertEqual(
            [strategy.name for strategy in strategies],
            [
                "no_trade",
                "random_same_turnover",
                "single_trader_mirror",
                "consensus_mirror",
                "specialist_mirror",
            ],
        )


if __name__ == "__main__":
    unittest.main()
