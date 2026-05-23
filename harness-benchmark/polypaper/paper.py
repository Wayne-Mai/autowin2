from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Dict, List, Optional, Sequence, Tuple

from .marketdata import order_book_from_clob, token_ids_from_market
from .models import MarketSnapshot, OrderBook, PaperFill, PaperOrder, Portfolio, Quote, Signal, StrategyResult
from .simulator import ConservativeFillModel, MarketRules
from .storage import (
    insert_order_books,
    insert_paper_fills,
    insert_portfolio_snapshot,
    insert_quotes,
    insert_signal_rows,
)
from .strategies.paper import PaperStrategy


@dataclass
class _PaperState:
    strategy: PaperStrategy
    portfolio: Portfolio
    orders: List[PaperOrder] = field(default_factory=list)
    pending: List[PaperOrder] = field(default_factory=list)
    fills: List[PaperFill] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)


@dataclass(frozen=True)
class CollectionResult:
    snapshots: List[MarketSnapshot]
    rules_by_asset: Dict[str, MarketRules]


class MarketDataCollector:
    def __init__(
        self,
        client,
        market_limit: int = 5,
        max_assets: int = 10,
        market_order: str = "volume_24hr",
        market_ascending: bool = False,
        market_active: bool = True,
    ):
        self.client = client
        self.market_limit = market_limit
        self.max_assets = max_assets
        self.market_order = market_order
        self.market_ascending = market_ascending
        self.market_active = market_active
        self.collection_count = 0

    def collect(self) -> CollectionResult:
        self.collection_count += 1
        snapshots: List[MarketSnapshot] = []
        rules_by_asset: Dict[str, MarketRules] = {}
        markets = self.client.markets(
            limit=self.market_limit,
            closed=False,
            active=self.market_active,
            order=self.market_order,
            ascending=self.market_ascending,
        )
        for market in markets:
            rules = MarketRules.from_gamma_market(market)
            token_ids = token_ids_from_market(market)
            outcomes = _parse_json_list(market.get("outcomes"))
            condition_id = str(market.get("conditionId", ""))
            for outcome_index, token_id in enumerate(token_ids):
                if len(snapshots) >= self.max_assets:
                    break
                try:
                    book = order_book_from_clob(self.client.book(token_id), source="paper_run")
                except Exception:
                    continue
                if book is None:
                    continue
                rules_by_asset[book.asset] = rules
                snapshots.append(
                    MarketSnapshot(
                        asset=book.asset,
                        condition_id=condition_id,
                        timestamp=book.timestamp,
                        book=book,
                        title=str(market.get("question", "") or ""),
                        slug=str(market.get("slug", "") or ""),
                        outcome=str(outcomes[outcome_index]) if outcome_index < len(outcomes) else "",
                        outcome_index=outcome_index,
                    )
                )
            if len(snapshots) >= self.max_assets:
                break
        return CollectionResult(snapshots=snapshots, rules_by_asset=rules_by_asset)


class AgentBatch:
    def __init__(self, strategies: Sequence[PaperStrategy], initial_cash: float):
        self.states = [
            _PaperState(strategy=strategy, portfolio=Portfolio(initial_cash), equity_curve=[initial_cash])
            for strategy in strategies
        ]

    def __iter__(self):
        return iter(self.states)

    def __len__(self) -> int:
        return len(self.states)


class PaperExecutionEngine:
    def __init__(
        self,
        run_id: str,
        fill_model: ConservativeFillModel,
        latest_quotes: Dict[str, Quote],
    ):
        self.run_id = run_id
        self.fill_model = fill_model
        self.latest_quotes = latest_quotes
        self.order_counter = 0

    def try_pending_for_book(self, state: _PaperState, book: OrderBook) -> List[PaperFill]:
        fills: List[PaperFill] = []
        still_pending: List[PaperOrder] = []
        for order in state.pending:
            if order.signal.asset != book.asset:
                still_pending.append(order)
                continue
            fill = self.fill_model.try_fill(order, book, state.portfolio)
            if fill is None:
                still_pending.append(order)
                continue
            fills.append(fill)
            state.fills.append(fill)
            state.strategy.on_fill(fill)
        state.pending = still_pending
        return fills

    def create_orders(self, state: _PaperState, signals: Sequence[Signal]) -> List[PaperOrder]:
        orders: List[PaperOrder] = []
        for signal in signals:
            self.order_counter += 1
            order = PaperOrder(
                order_id=f"{self.run_id}-{signal.strategy}-{self.order_counter}",
                signal=signal,
                created_at=signal.timestamp,
                eligible_at=self.fill_model.eligible_at(signal),
            )
            state.orders.append(order)
            state.pending.append(order)
            orders.append(order)
        return orders


class PaperRunner:
    def __init__(
        self,
        client,
        conn,
        run_id: str,
        strategies: Sequence[PaperStrategy],
        fill_model: ConservativeFillModel,
        initial_cash: float = 10000.0,
        market_limit: int = 5,
        max_assets: int = 10,
        market_order: str = "volume_24hr",
        market_ascending: bool = False,
        market_active: bool = True,
        collector: Optional[MarketDataCollector] = None,
        clock=None,
    ):
        self.client = client
        self.conn = conn
        self.run_id = run_id
        self.fill_model = fill_model
        self.initial_cash = initial_cash
        self.collector = collector or MarketDataCollector(
            client,
            market_limit=market_limit,
            max_assets=max_assets,
            market_order=market_order,
            market_ascending=market_ascending,
            market_active=market_active,
        )
        self.clock = clock or time.time
        self.agent_batch = AgentBatch(list(strategies), initial_cash=initial_cash)
        self.latest_quotes: Dict[str, Quote] = {}
        self.execution = PaperExecutionEngine(run_id, fill_model, self.latest_quotes)
        self._initial_snapshots_persisted = False

    def run(self, cycles: int = 1, interval_seconds: float = 0.0) -> List[StrategyResult]:
        for index in range(cycles):
            self.run_once()
            if interval_seconds > 0 and index < cycles - 1:
                time.sleep(interval_seconds)
        return self.results()

    def run_once(self) -> List[MarketSnapshot]:
        collection = self.collector.collect()
        snapshots, rules_by_asset = collection.snapshots, collection.rules_by_asset
        self._persist_initial_snapshots(snapshots)
        self.fill_model.rules_by_asset.update(rules_by_asset)
        books = [snapshot.book for snapshot in snapshots]
        quotes = [book.to_quote() for book in books]
        insert_order_books(self.conn, books)
        insert_quotes(self.conn, quotes)
        for quote in quotes:
            self.latest_quotes[quote.asset] = quote

        new_fills: List[PaperFill] = []
        for snapshot in snapshots:
            for state in self.agent_batch:
                new_fills.extend(self.execution.try_pending_for_book(state, snapshot.book))

        new_signals: List[Signal] = []
        for state in self.agent_batch:
            signals = state.strategy.on_snapshots(snapshots, state.portfolio, rules_by_asset=rules_by_asset)
            for signal in signals:
                new_signals.append(signal)
            self.execution.create_orders(state, signals)

        for snapshot in snapshots:
            for state in self.agent_batch:
                new_fills.extend(self.execution.try_pending_for_book(state, snapshot.book))

        if new_signals:
            insert_signal_rows(self.conn, self.run_id, new_signals)
        if new_fills:
            insert_paper_fills(self.conn, self.run_id, new_fills)

        timestamp = max((snapshot.timestamp for snapshot in snapshots), default=int(self.clock()))
        for state in self.agent_batch:
            equity = state.portfolio.equity(self.latest_quotes)
            state.equity_curve.append(equity)
            insert_portfolio_snapshot(
                self.conn,
                self.run_id,
                state.strategy.name,
                timestamp,
                state.portfolio.cash,
                equity,
                dict(state.portfolio.positions),
            )
        return snapshots

    def _persist_initial_snapshots(self, snapshots: Sequence[MarketSnapshot]) -> None:
        if self._initial_snapshots_persisted:
            return
        timestamp = min((snapshot.timestamp for snapshot in snapshots), default=int(self.clock())) - 1
        for state in self.agent_batch:
            insert_portfolio_snapshot(
                self.conn,
                self.run_id,
                state.strategy.name,
                timestamp,
                state.portfolio.cash,
                state.portfolio.equity(self.latest_quotes),
                dict(state.portfolio.positions),
            )
        self._initial_snapshots_persisted = True

    def fetch_snapshots(self) -> Tuple[List[MarketSnapshot], Dict[str, MarketRules]]:
        collection = self.collector.collect()
        return collection.snapshots, collection.rules_by_asset

    def results(self) -> List[StrategyResult]:
        return [self._result(state) for state in self.agent_batch]

    def _result(self, state: _PaperState) -> StrategyResult:
        equity = state.portfolio.equity(self.latest_quotes)
        fill_like = [fill for fill in state.fills if fill.status in {"FILLED", "PARTIAL"}]
        filled = [fill for fill in state.fills if fill.status == "FILLED"]
        partial = [fill for fill in state.fills if fill.status == "PARTIAL"]
        missed = [fill for fill in state.fills if fill.status == "MISSED"]
        return StrategyResult(
            strategy=state.strategy.name,
            orders=state.orders,
            fills=state.fills,
            metrics={
                "initial_cash": self.initial_cash,
                "ending_equity": equity,
                "cash": state.portfolio.cash,
                "pnl": equity - self.initial_cash,
                "roi": (equity - self.initial_cash) / self.initial_cash if self.initial_cash else 0.0,
                "orders": float(len(state.orders)),
                "filled_orders": float(len(filled)),
                "partial_orders": float(len(partial)),
                "missed_orders": float(len(missed)),
                "turnover": sum(fill.notional for fill in fill_like),
                "fees": sum(fill.fee for fill in fill_like),
                "pending_orders": float(len(state.pending)),
                "max_drawdown": _max_drawdown(state.equity_curve),
            },
        )


def _parse_json_list(raw) -> List[object]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            parsed = __import__("json").loads(raw)
        except ValueError:
            return []
        return parsed if isinstance(parsed, list) else []
    return []


def _max_drawdown(equity_curve: Sequence[float]) -> float:
    peak = None
    worst = 0.0
    for value in equity_curve:
        peak = value if peak is None else max(peak, value)
        if peak and peak > 0:
            worst = min(worst, (value - peak) / peak)
    return worst
