from __future__ import annotations

import hashlib
from typing import List, Optional

from ...models import MarketSnapshot, Portfolio, Signal
from .base import PaperStrategy


class NoTradePaperStrategy(PaperStrategy):
    name = "paper_no_trade"

    def on_snapshot(self, snapshot: MarketSnapshot, portfolio: Portfolio) -> List[Signal]:
        return []


class RandomMarketTakerStrategy(PaperStrategy):
    def __init__(
        self,
        seed: int = 42,
        trade_probability: float = 0.05,
        max_notional: float = 25.0,
        allow_sells: bool = True,
        name: Optional[str] = None,
    ):
        self.name = name or "paper_random_market_taker"
        self.seed = seed
        self.trade_probability = trade_probability
        self.max_notional = max_notional
        self.allow_sells = allow_sells

    def on_snapshot(self, snapshot: MarketSnapshot, portfolio: Portfolio) -> List[Signal]:
        if self._unit_float("take", snapshot) >= self.trade_probability:
            return []
        position = portfolio.positions.get(snapshot.asset, 0.0)
        side_roll = self._unit_float("side", snapshot)
        side = "SELL" if self.allow_sells and position > 0 and side_roll > 0.7 else "BUY"
        return [
            Signal(
                strategy=self.name,
                timestamp=snapshot.timestamp,
                side=side,
                asset=snapshot.asset,
                condition_id=snapshot.condition_id,
                target_notional=self.max_notional,
                reason="deterministic random market taker baseline",
            )
        ]

    def _unit_float(self, label: str, snapshot: MarketSnapshot) -> float:
        key = f"{self.seed}:{label}:{snapshot.timestamp}:{snapshot.asset}:{snapshot.condition_id}"
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return int(digest[:16], 16) / float(16**16)
