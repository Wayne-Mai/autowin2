"""Compatibility imports for target-agent sweep helpers.

New code should import from `polypaper.strategies.paper.target`.
"""

from .target import (
    TargetSweepConfig,
    TargetSweepResult,
    sweep_target_opportunities,
    target_strategy_from_sweep_result,
    target_sweep_configs,
)

__all__ = [
    "TargetSweepConfig",
    "TargetSweepResult",
    "sweep_target_opportunities",
    "target_strategy_from_sweep_result",
    "target_sweep_configs",
]
