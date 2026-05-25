"""Online paper-run strategies.

This package is the public import surface for strategies that consume live
market snapshots and produce paper orders. Keep concrete implementations in
small modules so large agent sweeps can add strategies without growing a
single strategy file indefinitely.
"""

from .base import PaperStrategy
from .baseline import NoTradePaperStrategy, RandomMarketTakerStrategy
from .suites import default_paper_strategies
from .target import (
    DEFAULT_TARGET_VARIANTS,
    DEFAULT_TARGET_VARIANTS_ARG,
    TARGET_VARIANT_GROUPS,
    TARGET_VARIANT_HELP,
    CoinbaseSpotProvider,
    CryptoDirectionalPaperStrategy,
    CryptoIntervalAnchorPaperStrategy,
    MakerRebateRotationStrategy,
    MomentumScalperPaperStrategy,
    OutcomeBasketArbPaperStrategy,
    SpreadCaptureMakerStrategy,
    TargetProfitPaperStrategy,
    TargetSweepConfig,
    TargetSweepResult,
    sweep_target_opportunities,
    target_strategy_from_args,
    target_strategy_from_config,
    target_strategy_from_sweep_result,
    target_sweep_configs,
    target_variant_configs,
)

__all__ = [
    "DEFAULT_TARGET_VARIANTS",
    "DEFAULT_TARGET_VARIANTS_ARG",
    "TARGET_VARIANT_GROUPS",
    "CoinbaseSpotProvider",
    "CryptoDirectionalPaperStrategy",
    "CryptoIntervalAnchorPaperStrategy",
    "NoTradePaperStrategy",
    "OutcomeBasketArbPaperStrategy",
    "PaperStrategy",
    "RandomMarketTakerStrategy",
    "MakerRebateRotationStrategy",
    "MomentumScalperPaperStrategy",
    "SpreadCaptureMakerStrategy",
    "TARGET_VARIANT_HELP",
    "TargetSweepConfig",
    "TargetSweepResult",
    "TargetProfitPaperStrategy",
    "default_paper_strategies",
    "sweep_target_opportunities",
    "target_strategy_from_args",
    "target_strategy_from_config",
    "target_strategy_from_sweep_result",
    "target_sweep_configs",
    "target_variant_configs",
]
