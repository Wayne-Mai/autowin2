"""Simple online paper-run baseline strategies."""

from .simple import NoTradePaperStrategy, RandomMarketTakerStrategy

__all__ = [
    "NoTradePaperStrategy",
    "RandomMarketTakerStrategy",
]
