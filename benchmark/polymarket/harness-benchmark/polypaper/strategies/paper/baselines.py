"""Compatibility imports for paper baseline strategies.

New code should import from `polypaper.strategies.paper.baseline`.
"""

from .baseline import NoTradePaperStrategy, RandomMarketTakerStrategy

__all__ = [
    "NoTradePaperStrategy",
    "RandomMarketTakerStrategy",
]
