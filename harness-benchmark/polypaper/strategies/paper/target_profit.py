"""Compatibility import for the target-profit strategy.

New code should import from `polypaper.strategies.paper.target`.
"""

from .target import TargetProfitPaperStrategy

__all__ = ["TargetProfitPaperStrategy"]
