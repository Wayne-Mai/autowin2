"""Backward-compatible imports for replay baseline strategies.

New code should import from `polypaper.strategies.replay`.
"""

from .strategies.replay import (  # noqa: F401
    BaselineStrategy,
    ConsensusMirrorBaseline,
    NoTradeBaseline,
    RandomSameTurnoverBaseline,
    SingleTraderMirrorBaseline,
    SpecialistMirrorBaseline,
)

__all__ = [
    "BaselineStrategy",
    "ConsensusMirrorBaseline",
    "NoTradeBaseline",
    "RandomSameTurnoverBaseline",
    "SingleTraderMirrorBaseline",
    "SpecialistMirrorBaseline",
]
