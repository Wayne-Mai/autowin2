"""Online paper-run strategies.

This package is the public import surface for strategies that consume live
market snapshots and produce paper orders. Keep concrete implementations in
small modules so large agent sweeps can add strategies without growing a
single strategy file indefinitely.
"""

from .base import PaperStrategy
from .baselines import NoTradePaperStrategy, RandomMarketTakerStrategy
from .target import (
    DEFAULT_TARGET_VARIANTS,
    DEFAULT_TARGET_VARIANTS_ARG,
    TARGET_VARIANT_HELP,
    TargetProfitPaperStrategy,
    TargetSweepConfig,
    TargetSweepResult,
    sweep_target_opportunities,
    target_strategy_from_args,
    target_strategy_from_config,
    target_sweep_configs,
    target_variant_configs,
)

__all__ = [
    "DEFAULT_TARGET_VARIANTS",
    "DEFAULT_TARGET_VARIANTS_ARG",
    "NoTradePaperStrategy",
    "PaperStrategy",
    "RandomMarketTakerStrategy",
    "TARGET_VARIANT_HELP",
    "TargetSweepConfig",
    "TargetSweepResult",
    "TargetProfitPaperStrategy",
    "sweep_target_opportunities",
    "target_strategy_from_args",
    "target_strategy_from_config",
    "target_sweep_configs",
    "target_variant_configs",
]
