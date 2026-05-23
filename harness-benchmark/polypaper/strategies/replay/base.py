from __future__ import annotations

from typing import List

from ...models import Portfolio, Signal, TraderTrade


class BaselineStrategy:
    name = "baseline"

    def on_trade(self, trade: TraderTrade, portfolio: Portfolio) -> List[Signal]:
        raise NotImplementedError
