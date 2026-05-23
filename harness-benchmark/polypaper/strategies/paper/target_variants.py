"""Compatibility imports for target-agent variants.

New code should import from `polypaper.strategies.paper.target`.
"""

from .target import (
    DEFAULT_TARGET_VARIANTS,
    DEFAULT_TARGET_VARIANTS_ARG,
    TARGET_VARIANT_HELP,
    target_strategy_from_args,
    target_strategy_from_config,
    target_variant_configs,
)

__all__ = [
    "DEFAULT_TARGET_VARIANTS",
    "DEFAULT_TARGET_VARIANTS_ARG",
    "TARGET_VARIANT_HELP",
    "target_strategy_from_args",
    "target_strategy_from_config",
    "target_variant_configs",
]
