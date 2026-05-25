from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from ...models import MarketSnapshot, PaperFill, Portfolio, Signal, StrategyDiagnostic


class PaperStrategy:
    name = "paper_strategy"

    def on_snapshot(self, snapshot: MarketSnapshot, portfolio: Portfolio) -> List[Signal]:
        raise NotImplementedError

    def on_snapshots(
        self,
        snapshots: Sequence[MarketSnapshot],
        portfolio: Portfolio,
        rules_by_asset: Optional[Dict[str, object]] = None,
    ) -> List[Signal]:
        signals: List[Signal] = []
        for snapshot in snapshots:
            signals.extend(self.on_snapshot(snapshot, portfolio))
        return signals

    def on_fill(self, fill: PaperFill) -> None:
        return None

    def set_cycle_wall_time(self, timestamp: Optional[int]) -> None:
        return None

    def watched_assets(self) -> Sequence[str]:
        return ()

    def pop_diagnostics(self) -> List[StrategyDiagnostic]:
        return []
