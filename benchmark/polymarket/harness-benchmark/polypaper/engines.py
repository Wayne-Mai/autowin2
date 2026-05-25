from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import time
from typing import Any, Iterable, List, Optional, Protocol, Sequence, Union, runtime_checkable

from .models import OrderBook, Quote, StrategyResult, TraderTrade
from .simulator import ReplaySimulator


class EngineKind(str, Enum):
    BACKTEST = "backtest"
    PAPER = "paper"
    LIVE = "live"


@dataclass(frozen=True)
class EngineMetadata:
    kind: EngineKind
    name: str
    description: str = ""
    uses_live_market_data: bool = False
    live_order_capable: bool = False
    persists_results: bool = False


@runtime_checkable
class TradingEngine(Protocol):
    metadata: EngineMetadata

    def run_once(self) -> Any:
        ...

    def results(self) -> List[StrategyResult]:
        ...


class ReplayBacktestEngine:
    """Offline, deterministic replay over a fixed historical market stream."""

    def __init__(
        self,
        simulator: ReplaySimulator,
        trades: Iterable[TraderTrade],
        quotes: Iterable[Union[Quote, OrderBook]],
        name: str = "replay-backtest",
        start_ts: Optional[int] = None,
        end_ts: Optional[int] = None,
    ):
        self.metadata = EngineMetadata(
            kind=EngineKind.BACKTEST,
            name=name,
            description="Offline replay over fixed public trades and quote/order-book snapshots.",
            uses_live_market_data=False,
            live_order_capable=False,
            persists_results=False,
        )
        self.simulator = simulator
        self.trades = list(trades)
        self.quotes = list(quotes)
        self.start_ts = start_ts
        self.end_ts = end_ts
        self._has_run = False
        self._results: List[StrategyResult] = []

    def run_once(self) -> List[StrategyResult]:
        if not self._has_run:
            self._results = self.simulator.run(
                self.trades,
                self.quotes,
                start_ts=self.start_ts,
                end_ts=self.end_ts,
            )
            self._has_run = True
        return list(self._results)

    def results(self) -> List[StrategyResult]:
        return list(self._results)


class PaperTradingEngine:
    """Online or recorded paper engine with simulated execution and no live orders."""

    def __init__(
        self,
        runner: Any,
        name: str = "paper",
        uses_live_market_data: bool = True,
        persists_results: bool = True,
        description: str = "Paper trading over market snapshots with local simulated fills.",
    ):
        self.metadata = EngineMetadata(
            kind=EngineKind.PAPER,
            name=name,
            description=description,
            uses_live_market_data=uses_live_market_data,
            live_order_capable=False,
            persists_results=persists_results,
        )
        self.runner = runner

    def run(self, cycles: int = 1, interval_seconds: float = 0.0) -> List[StrategyResult]:
        run = getattr(self.runner, "run", None)
        if callable(run):
            return list(run(cycles=cycles, interval_seconds=interval_seconds))
        for index in range(cycles):
            self.run_once()
            if interval_seconds > 0 and index < cycles - 1:
                time.sleep(interval_seconds)
        return self.results()

    def run_once(self) -> Any:
        return self.runner.run_once()

    def results(self) -> List[StrategyResult]:
        return list(self.runner.results())


class LiveTradingDisabledError(RuntimeError):
    pass


class DisabledLiveTradingEngine:
    """Safety placeholder for the future real-order engine."""

    def __init__(self, name: str = "live-disabled"):
        self.metadata = EngineMetadata(
            kind=EngineKind.LIVE,
            name=name,
            description="Real-order engine placeholder; intentionally disabled in this benchmark.",
            uses_live_market_data=True,
            live_order_capable=False,
            persists_results=False,
        )

    def run_once(self) -> None:
        raise LiveTradingDisabledError(
            "Live trading is not implemented in this academic harness. "
            "Use ReplayBacktestEngine or PaperTradingEngine."
        )

    def results(self) -> List[StrategyResult]:
        return []


def replay_backtest_engine(
    simulator: ReplaySimulator,
    trades: Iterable[TraderTrade],
    quotes: Iterable[Union[Quote, OrderBook]],
    name: str = "replay-backtest",
    start_ts: Optional[int] = None,
    end_ts: Optional[int] = None,
) -> ReplayBacktestEngine:
    return ReplayBacktestEngine(
        simulator=simulator,
        trades=trades,
        quotes=quotes,
        name=name,
        start_ts=start_ts,
        end_ts=end_ts,
    )


def paper_engine(
    runner: Any,
    name: str = "paper",
    uses_live_market_data: bool = True,
    persists_results: bool = True,
    description: str = "Paper trading over market snapshots with local simulated fills.",
) -> PaperTradingEngine:
    return PaperTradingEngine(
        runner=runner,
        name=name,
        uses_live_market_data=uses_live_market_data,
        persists_results=persists_results,
        description=description,
    )


def disabled_live_engine(name: str = "live-disabled") -> DisabledLiveTradingEngine:
    return DisabledLiveTradingEngine(name=name)
