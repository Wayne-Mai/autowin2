"""Target-profit paper strategy family.

This package keeps the target agent implementation, named presets, and sweep
helpers together so benchmark runs can add variants without growing CLI code.
"""

from .profit import TargetProfitPaperStrategy
from .basket import OutcomeBasketArbPaperStrategy
from .crypto import (
    CoinbaseSpotProvider,
    CryptoDirectionalPaperStrategy,
    CryptoIntervalAnchorPaperStrategy,
    CryptoIntervalBookSkewPaperStrategy,
    CryptoIntervalCloseEdgePaperStrategy,
)
from .scalpers import MakerRebateRotationStrategy, MomentumScalperPaperStrategy, SpreadCaptureMakerStrategy
from .sweep import (
    TargetSweepConfig,
    TargetSweepResult,
    sweep_target_opportunities,
    target_strategy_from_sweep_result,
    target_sweep_configs,
)
from .variants import (
    DEFAULT_TARGET_VARIANTS,
    DEFAULT_TARGET_VARIANTS_ARG,
    TARGET_VARIANT_GROUPS,
    TARGET_VARIANT_HELP,
    target_strategy_from_args,
    target_strategy_from_config,
    target_variant_configs,
)

__all__ = [
    "DEFAULT_TARGET_VARIANTS",
    "DEFAULT_TARGET_VARIANTS_ARG",
    "TARGET_VARIANT_GROUPS",
    "TARGET_VARIANT_HELP",
    "CoinbaseSpotProvider",
    "CryptoDirectionalPaperStrategy",
    "CryptoIntervalAnchorPaperStrategy",
    "CryptoIntervalBookSkewPaperStrategy",
    "CryptoIntervalCloseEdgePaperStrategy",
    "TargetProfitPaperStrategy",
    "OutcomeBasketArbPaperStrategy",
    "MomentumScalperPaperStrategy",
    "MakerRebateRotationStrategy",
    "SpreadCaptureMakerStrategy",
    "TargetSweepConfig",
    "TargetSweepResult",
    "sweep_target_opportunities",
    "target_strategy_from_args",
    "target_strategy_from_config",
    "target_strategy_from_sweep_result",
    "target_sweep_configs",
    "target_variant_configs",
]
