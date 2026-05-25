"""Compatibility imports for replay baseline strategies.

New code should import from `polypaper.strategies.replay.baseline`.
"""

from .baseline import (
    ConsensusMirrorBaseline,
    NoTradeBaseline,
    RandomSameTurnoverBaseline,
    SingleTraderMirrorBaseline,
    SpecialistMirrorBaseline,
)

__all__ = [
    "ConsensusMirrorBaseline",
    "NoTradeBaseline",
    "RandomSameTurnoverBaseline",
    "SingleTraderMirrorBaseline",
    "SpecialistMirrorBaseline",
]
