"""Historical replay strategies.

Replay strategies consume public trade events from fixtures or collected data.
They are kept separate from online paper strategies because their inputs,
latency assumptions, and reproducibility requirements are different.
"""

from .base import BaselineStrategy
from .baseline import (
    ConsensusMirrorBaseline,
    MakerSingleTraderMirrorBaseline,
    NoTradeBaseline,
    RandomSameTurnoverBaseline,
    SingleTraderMirrorBaseline,
    SpecialistMirrorBaseline,
)
from .suites import default_replay_strategies, replay_strategies_for_suite

__all__ = [
    "BaselineStrategy",
    "ConsensusMirrorBaseline",
    "MakerSingleTraderMirrorBaseline",
    "NoTradeBaseline",
    "RandomSameTurnoverBaseline",
    "SingleTraderMirrorBaseline",
    "SpecialistMirrorBaseline",
    "default_replay_strategies",
    "replay_strategies_for_suite",
]
