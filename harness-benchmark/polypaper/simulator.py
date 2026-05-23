from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
import math
from typing import DefaultDict, Dict, Iterable, List, Optional, Sequence, Union

from .models import BookLevel, OrderBook, PaperFill, PaperOrder, Portfolio, Quote, Signal, StrategyResult, TraderTrade
from .strategies.replay import BaselineStrategy


@dataclass(frozen=True)
class LatencyModel:
    detection_delay_seconds: int = 0
    polling_delay_seconds: int = 0
    decision_delay_seconds: int = 0
    execution_delay_seconds: int = 60

    @property
    def total_seconds(self) -> int:
        return (
            self.detection_delay_seconds
            + self.polling_delay_seconds
            + self.decision_delay_seconds
            + self.execution_delay_seconds
        )


@dataclass(frozen=True)
class PolymarketFeeModel:
    fee_rate: float = 0.0
    exponent: float = 1.0
    taker_only: bool = True
    min_fee: float = 0.00001
    precision: int = 5

    def fee_for(self, shares: float, price: float, taker: bool = True) -> float:
        if shares <= 0 or price <= 0:
            return 0.0
        if self.taker_only and not taker:
            return 0.0
        if self.fee_rate <= 0:
            return 0.0
        raw_fee = shares * self.fee_rate * ((price * (1.0 - price)) ** self.exponent)
        rounded = round(raw_fee, self.precision)
        return rounded if rounded >= self.min_fee else 0.0

    def fee_per_share(self, price: float, taker: bool = True) -> float:
        if self.taker_only and not taker:
            return 0.0
        if self.fee_rate <= 0 or price <= 0:
            return 0.0
        return self.fee_rate * ((price * (1.0 - price)) ** self.exponent)


@dataclass(frozen=True)
class MarketRules:
    tick_size: float = 0.01
    min_order_size: float = 1.0
    minimum_order_age_seconds: int = 0
    fee_model: PolymarketFeeModel = field(default_factory=PolymarketFeeModel)

    @classmethod
    def from_clob_market_info(cls, info: Dict[str, object]) -> "MarketRules":
        fee_details = info.get("fd") or {}
        if not isinstance(fee_details, dict):
            fee_details = {}
        return cls(
            tick_size=float(info.get("mts", 0.01) or 0.01),
            min_order_size=float(info.get("mos", 1.0) or 1.0),
            minimum_order_age_seconds=int(info.get("oas", 0) or 0),
            fee_model=PolymarketFeeModel(
                fee_rate=float(fee_details.get("r", fee_details.get("rate", 0.0)) or 0.0),
                exponent=float(fee_details.get("e", fee_details.get("exponent", 1.0)) or 1.0),
                taker_only=bool(fee_details.get("to", fee_details.get("takerOnly", True))),
            ),
        )

    @classmethod
    def from_gamma_market(cls, market: Dict[str, object]) -> "MarketRules":
        fee_schedule = market.get("feeSchedule") or {}
        if not isinstance(fee_schedule, dict):
            fee_schedule = {}
        return cls(
            tick_size=float(market.get("orderPriceMinTickSize", 0.01) or 0.01),
            min_order_size=float(market.get("orderMinSize", 1.0) or 1.0),
            fee_model=PolymarketFeeModel(
                fee_rate=float(fee_schedule.get("rate", fee_schedule.get("r", 0.0)) or 0.0),
                exponent=float(fee_schedule.get("exponent", fee_schedule.get("e", 1.0)) or 1.0),
                taker_only=bool(fee_schedule.get("takerOnly", fee_schedule.get("to", True))),
            ),
        )


@dataclass
class ConservativeFillModel:
    delay_seconds: int = 60
    slippage_bps: float = 0.0
    min_notional: float = 1.0
    latency_model: Optional[LatencyModel] = None
    default_rules: MarketRules = field(default_factory=MarketRules)
    rules_by_asset: Dict[str, MarketRules] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.latency_model is None:
            self.latency_model = LatencyModel(execution_delay_seconds=self.delay_seconds)

    def eligible_at(self, signal: Signal) -> int:
        return signal.timestamp + self.latency_model.total_seconds

    def try_fill(self, order: PaperOrder, book: OrderBook, portfolio: Portfolio) -> Optional[PaperFill]:
        if book.timestamp < order.eligible_at:
            return None
        signal = order.signal
        side = signal.side.upper()
        if side == "BUY":
            return self._fill_buy(order, book, portfolio)
        if side == "SELL":
            return self._fill_sell(order, book, portfolio)
        return PaperFill(
            order_id=order.order_id,
            strategy=signal.strategy,
            asset=signal.asset,
            side=side,
            status="MISSED",
            timestamp=book.timestamp,
            price=0.0,
            shares=0.0,
            notional=0.0,
            reason="unsupported_side",
            quote_timestamp=book.timestamp,
            requested_notional=signal.target_notional,
            liquidity_source=book.source,
        )

    def missed(self, order: PaperOrder, timestamp: int, reason: str) -> PaperFill:
        signal = order.signal
        return PaperFill(
            order_id=order.order_id,
            strategy=signal.strategy,
            asset=signal.asset,
            side=signal.side,
            status="MISSED",
            timestamp=timestamp,
            price=0.0,
            shares=0.0,
            notional=0.0,
            reason=reason,
            quote_timestamp=None,
            requested_notional=signal.target_notional,
        )

    def _fill_buy(self, order: PaperOrder, book: OrderBook, portfolio: Portfolio) -> PaperFill:
        signal = order.signal
        rules = self._rules_for(signal.asset)
        if signal.target_notional < self.min_notional:
            return self._miss_with_book(order, book, "notional_below_minimum")
        if portfolio.cash < self.min_notional:
            return self._miss_with_book(order, book, "insufficient_cash")
        levels = sorted(book.asks, key=lambda level: level.price)
        requested_gross_cap = min(signal.target_notional, portfolio.cash)
        shares, gross, fee = self._walk_buy_levels(levels, requested_gross_cap, portfolio.cash, rules)
        if shares <= 0:
            return self._miss_with_book(order, book, "insufficient_ask_depth")
        if shares < rules.min_order_size:
            return self._miss_with_book(order, book, "below_min_order_size")
        if gross + fee > portfolio.cash + 1e-9:
            return self._miss_with_book(order, book, "insufficient_cash_after_fee")
        average_price = gross / shares
        portfolio.buy(signal.asset, shares, average_price, fee=fee)
        status = "FILLED" if gross >= requested_gross_cap - 1e-9 else "PARTIAL"
        return PaperFill(
            order_id=order.order_id,
            strategy=signal.strategy,
            asset=signal.asset,
            side="BUY",
            status=status,
            timestamp=book.timestamp,
            price=average_price,
            shares=shares,
            notional=gross,
            reason="depth_fill_at_asks_plus_slippage",
            quote_timestamp=book.timestamp,
            fee=fee,
            taker=True,
            requested_notional=signal.target_notional,
            filled_notional=gross,
            average_price=average_price,
            liquidity_source=book.source,
        )

    def _fill_sell(self, order: PaperOrder, book: OrderBook, portfolio: Portfolio) -> PaperFill:
        signal = order.signal
        rules = self._rules_for(signal.asset)
        current_shares = portfolio.positions.get(signal.asset, 0.0)
        if current_shares <= 1e-9:
            return self._miss_with_book(order, book, "no_inventory_no_shorting")
        levels = sorted(book.bids, key=lambda level: level.price, reverse=True)
        shares, gross, fee = self._walk_sell_levels(levels, signal.target_notional, current_shares, rules)
        if shares <= 0:
            return self._miss_with_book(order, book, "insufficient_bid_depth")
        if shares < rules.min_order_size:
            return self._miss_with_book(order, book, "below_min_order_size")
        if gross < self.min_notional:
            return self._miss_with_book(order, book, "notional_below_minimum")
        average_price = gross / shares
        portfolio.sell(signal.asset, shares, average_price, fee=fee)
        status = "FILLED" if gross >= min(signal.target_notional, current_shares * average_price) - 1e-9 else "PARTIAL"
        return PaperFill(
            order_id=order.order_id,
            strategy=signal.strategy,
            asset=signal.asset,
            side="SELL",
            status=status,
            timestamp=book.timestamp,
            price=average_price,
            shares=shares,
            notional=gross,
            reason="depth_fill_at_bids_minus_slippage",
            quote_timestamp=book.timestamp,
            fee=fee,
            taker=True,
            requested_notional=signal.target_notional,
            filled_notional=gross,
            average_price=average_price,
            liquidity_source=book.source,
        )

    def _miss_with_book(self, order: PaperOrder, book: OrderBook, reason: str) -> PaperFill:
        signal = order.signal
        return PaperFill(
            order_id=order.order_id,
            strategy=signal.strategy,
            asset=signal.asset,
            side=signal.side,
            status="MISSED",
            timestamp=book.timestamp,
            price=0.0,
            shares=0.0,
            notional=0.0,
            reason=reason,
            quote_timestamp=book.timestamp,
            requested_notional=signal.target_notional,
            liquidity_source=book.source,
        )

    def _walk_buy_levels(
        self,
        levels: Sequence[BookLevel],
        max_gross_notional: float,
        max_cash: float,
        rules: MarketRules,
    ) -> tuple:
        shares = 0.0
        gross = 0.0
        fee = 0.0
        for level in levels:
            price = self._round_buy_price(level.price * (1.0 + self.slippage_bps / 10000.0), rules.tick_size)
            if price <= 0 or price > 1.0:
                continue
            remaining_gross = max_gross_notional - gross
            remaining_cash = max_cash - gross - fee
            if remaining_gross <= 1e-9 or remaining_cash <= 1e-9:
                break
            fee_per_share = rules.fee_model.fee_per_share(price, taker=True)
            max_by_gross = remaining_gross / price
            max_by_cash = remaining_cash / (price + fee_per_share)
            level_shares = min(level.size, max_by_gross, max_by_cash)
            if level_shares <= 1e-9:
                continue
            level_gross = level_shares * price
            level_fee = rules.fee_model.fee_for(level_shares, price, taker=True)
            shares += level_shares
            gross += level_gross
            fee += level_fee
        return shares, gross, fee

    def _walk_sell_levels(
        self,
        levels: Sequence[BookLevel],
        target_gross_notional: float,
        available_shares: float,
        rules: MarketRules,
    ) -> tuple:
        shares = 0.0
        gross = 0.0
        fee = 0.0
        for level in levels:
            price = self._round_sell_price(level.price * (1.0 - self.slippage_bps / 10000.0), rules.tick_size)
            if price <= 0 or price > 1.0:
                continue
            remaining_gross = target_gross_notional - gross
            remaining_shares = available_shares - shares
            if remaining_gross <= 1e-9 or remaining_shares <= 1e-9:
                break
            level_shares = min(level.size, remaining_shares, remaining_gross / price)
            if level_shares <= 1e-9:
                continue
            level_gross = level_shares * price
            level_fee = rules.fee_model.fee_for(level_shares, price, taker=True)
            shares += level_shares
            gross += level_gross
            fee += level_fee
        return shares, gross, fee

    def _rules_for(self, asset: str) -> MarketRules:
        return self.rules_by_asset.get(asset, self.default_rules)

    @staticmethod
    def _round_buy_price(price: float, tick_size: float) -> float:
        if tick_size <= 0:
            return price
        return min(1.0, math.ceil((price - 1e-12) / tick_size) * tick_size)

    @staticmethod
    def _round_sell_price(price: float, tick_size: float) -> float:
        if tick_size <= 0:
            return price
        return max(0.0, math.floor((price + 1e-12) / tick_size) * tick_size)


@dataclass
class _RunState:
    strategy: BaselineStrategy
    portfolio: Portfolio
    orders: List[PaperOrder] = field(default_factory=list)
    pending: List[PaperOrder] = field(default_factory=list)
    fills: List[PaperFill] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)


class ReplaySimulator:
    def __init__(
        self,
        strategies: Sequence[BaselineStrategy],
        fill_model: ConservativeFillModel,
        initial_cash: float = 10000.0,
    ):
        self.strategies = list(strategies)
        self.fill_model = fill_model
        self.initial_cash = initial_cash

    def run(
        self,
        trades: Iterable[TraderTrade],
        quotes: Iterable[Union[Quote, OrderBook]],
        start_ts: Optional[int] = None,
        end_ts: Optional[int] = None,
    ) -> List[StrategyResult]:
        sorted_trades = sorted(trades, key=lambda trade: (trade.timestamp, trade.tx_hash))
        sorted_books = sorted((_as_order_book(item) for item in quotes), key=lambda book: (book.timestamp, book.asset))
        if start_ts is None:
            start_ts = min(
                [item.timestamp for item in sorted_trades + sorted_books],
                default=0,
            )
        if end_ts is None:
            end_ts = max(
                [item.timestamp for item in sorted_trades + sorted_books],
                default=start_ts,
            )

        trades_by_ts: DefaultDict[int, List[TraderTrade]] = defaultdict(list)
        books_by_ts: DefaultDict[int, List[OrderBook]] = defaultdict(list)
        for trade in sorted_trades:
            if start_ts <= trade.timestamp <= end_ts:
                trades_by_ts[trade.timestamp].append(trade)
        for book in sorted_books:
            if start_ts <= book.timestamp <= end_ts:
                books_by_ts[book.timestamp].append(book)

        timestamps = sorted(set(trades_by_ts) | set(books_by_ts))
        latest_quotes: Dict[str, Quote] = {}
        states = [
            _RunState(strategy=strategy, portfolio=Portfolio(self.initial_cash))
            for strategy in self.strategies
        ]
        for state in states:
            state.equity_curve.append(self.initial_cash)

        order_counter = 0
        for ts in timestamps:
            for book in books_by_ts.get(ts, []):
                latest_quotes[book.asset] = book.to_quote()
                for state in states:
                    self._try_pending_fills(state, book)

            for state in states:
                state.equity_curve.append(state.portfolio.equity(latest_quotes))

            for trade in trades_by_ts.get(ts, []):
                for state in states:
                    signals = state.strategy.on_trade(trade, state.portfolio)
                    for signal in signals:
                        order_counter += 1
                        order = PaperOrder(
                            order_id=f"{signal.strategy}-{order_counter}",
                            signal=signal,
                            created_at=signal.timestamp,
                            eligible_at=self.fill_model.eligible_at(signal),
                        )
                        state.orders.append(order)
                        state.pending.append(order)

        for state in states:
            for order in state.pending:
                state.fills.append(self.fill_model.missed(order, end_ts, "no_quote_after_execution"))
            state.pending.clear()
            state.equity_curve.append(state.portfolio.equity(latest_quotes))

        return [self._result_from_state(state, latest_quotes) for state in states]

    def _try_pending_fills(self, state: _RunState, book: OrderBook) -> None:
        still_pending: List[PaperOrder] = []
        for order in state.pending:
            if order.signal.asset != book.asset:
                still_pending.append(order)
                continue
            fill = self.fill_model.try_fill(order, book, state.portfolio)
            if fill is None:
                still_pending.append(order)
                continue
            state.fills.append(fill)
        state.pending = still_pending

    def _result_from_state(self, state: _RunState, latest_quotes: Dict[str, Quote]) -> StrategyResult:
        ending_equity = state.portfolio.equity(latest_quotes)
        pnl = ending_equity - self.initial_cash
        filled = [fill for fill in state.fills if fill.status == "FILLED"]
        fill_like = [fill for fill in state.fills if fill.status in {"FILLED", "PARTIAL"}]
        partial = [fill for fill in state.fills if fill.status == "PARTIAL"]
        missed = [fill for fill in state.fills if fill.status == "MISSED"]
        return StrategyResult(
            strategy=state.strategy.name,
            orders=state.orders,
            fills=state.fills,
            metrics={
                "initial_cash": self.initial_cash,
                "ending_equity": ending_equity,
                "cash": state.portfolio.cash,
                "pnl": pnl,
                "roi": pnl / self.initial_cash if self.initial_cash else 0.0,
                "orders": float(len(state.orders)),
                "filled_orders": float(len(filled)),
                "partial_orders": float(len(partial)),
                "missed_orders": float(len(missed)),
                "turnover": sum(fill.notional for fill in fill_like),
                "fees": sum(fill.fee for fill in fill_like),
                "max_drawdown": _max_drawdown(state.equity_curve),
            },
        )


def _max_drawdown(equity_curve: Sequence[float]) -> float:
    peak = None
    worst = 0.0
    for value in equity_curve:
        peak = value if peak is None else max(peak, value)
        if peak and peak > 0:
            worst = min(worst, (value - peak) / peak)
    return worst


def _as_order_book(item: Union[Quote, OrderBook]) -> OrderBook:
    if isinstance(item, OrderBook):
        return item
    if isinstance(item, Quote):
        return OrderBook.from_quote(item)
    raise TypeError(f"unsupported market data type: {type(item)!r}")
