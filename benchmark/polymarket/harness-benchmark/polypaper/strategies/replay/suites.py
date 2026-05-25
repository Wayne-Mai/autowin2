from __future__ import annotations

from typing import List, Sequence

from ...models import TraderTrade
from .base import BaselineStrategy
from .baseline import (
    ConsensusMirrorBaseline,
    MakerSingleTraderMirrorBaseline,
    NoTradeBaseline,
    RandomSameTurnoverBaseline,
    SingleTraderMirrorBaseline,
    SpecialistMirrorBaseline,
)


def default_replay_strategies(trades: Sequence[TraderTrade], seed: int) -> List[BaselineStrategy]:
    wallets = sorted({trade.wallet for trade in trades})
    first_wallet = wallets[:1] or ["none"]
    specialist_map = {}
    for trade in trades:
        if trade.category:
            specialist_map.setdefault(trade.wallet, set()).add(trade.category)
    return [
        NoTradeBaseline(),
        RandomSameTurnoverBaseline(seed=seed, trade_probability=0.5, max_notional=50.0),
        SingleTraderMirrorBaseline(wallets=first_wallet, max_notional=50.0),
        ConsensusMirrorBaseline(wallets=wallets, threshold=min(2, len(wallets) or 2), max_notional=50.0),
        SpecialistMirrorBaseline(wallet_categories=specialist_map, max_notional=50.0),
    ]


def replay_strategies_for_suite(
    trades: Sequence[TraderTrade],
    seed: int,
    suite: str = "default",
) -> List[BaselineStrategy]:
    wallets = sorted({trade.wallet for trade in trades})
    first_wallet = wallets[:1] or ["none"]
    if suite == "default":
        return default_replay_strategies(trades, seed=seed)
    if suite == "default_with_maker":
        return default_replay_strategies(trades, seed=seed) + [
            MakerSingleTraderMirrorBaseline(wallets=first_wallet, max_notional=50.0)
        ]
    if suite == "maker_only":
        return [MakerSingleTraderMirrorBaseline(wallets=first_wallet, max_notional=50.0)]
    raise ValueError(f"unknown replay strategy suite: {suite}")
