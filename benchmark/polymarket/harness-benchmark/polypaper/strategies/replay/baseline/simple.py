from __future__ import annotations

import hashlib
from collections import deque
from typing import Deque, Dict, Iterable, List, Mapping, Sequence, Set

from ....models import Portfolio, Signal, TraderTrade
from ..base import BaselineStrategy


class NoTradeBaseline(BaselineStrategy):
    name = "no_trade"

    def on_trade(self, trade: TraderTrade, portfolio: Portfolio) -> List[Signal]:
        return []


class RandomSameTurnoverBaseline(BaselineStrategy):
    name = "random_same_turnover"

    def __init__(
        self,
        seed: int = 42,
        trade_probability: float = 0.25,
        max_notional: float = 50.0,
    ):
        self.seed = seed
        self.trade_probability = trade_probability
        self.max_notional = max_notional

    def on_trade(self, trade: TraderTrade, portfolio: Portfolio) -> List[Signal]:
        if self._unit_float("take", trade) >= self.trade_probability:
            return []
        side = "BUY" if self._unit_float("side", trade) < 0.5 else "SELL"
        notional = max(0.0, min(self.max_notional, trade.notional or self.max_notional))
        return [
            Signal(
                strategy=self.name,
                timestamp=trade.timestamp,
                side=side,
                asset=trade.asset,
                condition_id=trade.condition_id,
                target_notional=notional,
                reason="deterministic random same-turnover control",
                source_wallets=(trade.wallet,),
                source_tx_hashes=(trade.tx_hash,),
            )
        ]

    def _unit_float(self, label: str, trade: TraderTrade) -> float:
        key = f"{self.seed}:{label}:{trade.timestamp}:{trade.wallet}:{trade.tx_hash}:{trade.asset}"
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return int(digest[:16], 16) / float(16**16)


class SingleTraderMirrorBaseline(BaselineStrategy):
    name = "single_trader_mirror"

    def __init__(
        self,
        wallets: Iterable[str],
        max_notional: float = 50.0,
        sides: Sequence[str] = ("BUY", "SELL"),
    ):
        self.wallets: Set[str] = {w.lower() for w in wallets}
        self.max_notional = max_notional
        self.sides = {s.upper() for s in sides}

    def on_trade(self, trade: TraderTrade, portfolio: Portfolio) -> List[Signal]:
        if trade.wallet.lower() not in self.wallets:
            return []
        if trade.side.upper() not in self.sides:
            return []
        notional = max(0.0, min(self.max_notional, trade.notional or self.max_notional))
        return [
            Signal(
                strategy=self.name,
                timestamp=trade.timestamp,
                side=trade.side.upper(),
                asset=trade.asset,
                condition_id=trade.condition_id,
                target_notional=notional,
                reason="mirror selected public trader trade",
                source_wallets=(trade.wallet,),
                source_tx_hashes=(trade.tx_hash,),
            )
        ]


class MakerSingleTraderMirrorBaseline(SingleTraderMirrorBaseline):
    name = "maker_single_trader_mirror"

    def on_trade(self, trade: TraderTrade, portfolio: Portfolio) -> List[Signal]:
        signals = super().on_trade(trade, portfolio)
        maker_signals: List[Signal] = []
        for signal in signals:
            maker_signals.append(
                Signal(
                    strategy=self.name,
                    timestamp=signal.timestamp,
                    side=signal.side,
                    asset=signal.asset,
                    condition_id=signal.condition_id,
                    target_notional=signal.target_notional,
                    reason="maker mirror selected public trader trade",
                    source_wallets=signal.source_wallets,
                    source_tx_hashes=signal.source_tx_hashes,
                    execution_style="maker",
                    limit_price=min(0.99, max(0.01, trade.price)),
                )
            )
        return maker_signals


class ConsensusMirrorBaseline(BaselineStrategy):
    name = "consensus_mirror"

    def __init__(
        self,
        wallets: Iterable[str],
        threshold: int = 2,
        window_seconds: int = 3600,
        max_notional: float = 50.0,
    ):
        self.wallets: Set[str] = {w.lower() for w in wallets}
        self.threshold = threshold
        self.window_seconds = window_seconds
        self.max_notional = max_notional
        self._recent: Deque[TraderTrade] = deque()

    def on_trade(self, trade: TraderTrade, portfolio: Portfolio) -> List[Signal]:
        if trade.wallet.lower() not in self.wallets or trade.side.upper() not in {"BUY", "SELL"}:
            self._expire(trade.timestamp)
            return []

        self._expire(trade.timestamp)
        self._recent.append(trade)
        same_flow = [
            item
            for item in self._recent
            if item.asset == trade.asset and item.side.upper() == trade.side.upper()
        ]
        wallets = tuple(sorted({item.wallet for item in same_flow}))
        if len(wallets) < self.threshold:
            return []

        tx_hashes = tuple(item.tx_hash for item in same_flow[-self.threshold :])
        return [
            Signal(
                strategy=self.name,
                timestamp=trade.timestamp,
                side=trade.side.upper(),
                asset=trade.asset,
                condition_id=trade.condition_id,
                target_notional=self.max_notional,
                reason=f"{len(wallets)} selected traders same-direction within {self.window_seconds}s",
                source_wallets=wallets,
                source_tx_hashes=tx_hashes,
            )
        ]

    def _expire(self, now: int) -> None:
        cutoff = now - self.window_seconds
        while self._recent and self._recent[0].timestamp < cutoff:
            self._recent.popleft()


class SpecialistMirrorBaseline(BaselineStrategy):
    name = "specialist_mirror"

    def __init__(
        self,
        wallet_categories: Mapping[str, Iterable[str]],
        max_notional: float = 50.0,
    ):
        self.wallet_categories: Dict[str, Set[str]] = {
            wallet.lower(): {category.lower() for category in categories}
            for wallet, categories in wallet_categories.items()
        }
        self.max_notional = max_notional

    def on_trade(self, trade: TraderTrade, portfolio: Portfolio) -> List[Signal]:
        categories = self.wallet_categories.get(trade.wallet.lower())
        if not categories:
            return []
        if trade.category.lower() not in categories:
            return []
        notional = max(0.0, min(self.max_notional, trade.notional or self.max_notional))
        return [
            Signal(
                strategy=self.name,
                timestamp=trade.timestamp,
                side=trade.side.upper(),
                asset=trade.asset,
                condition_id=trade.condition_id,
                target_notional=notional,
                reason=f"mirror selected trader inside specialist category {trade.category}",
                source_wallets=(trade.wallet,),
                source_tx_hashes=(trade.tx_hash,),
            )
        ]
