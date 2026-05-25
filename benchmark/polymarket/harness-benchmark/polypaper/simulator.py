from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field, replace
import hashlib
import json
import math
from typing import DefaultDict, Dict, Iterable, List, Optional, Sequence, Union

from .models import BookLevel, OrderBook, PaperFill, PaperOrder, Portfolio, Quote, Signal, StrategyResult, TraderTrade
from .strategies.replay import BaselineStrategy


MAKER_FILL_MODES = {"optimistic", "queue_proxy", "probabilistic_queue"}


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
    maker_rebate_rate: float = 0.0
    min_fee: float = 0.00001
    precision: int = 5

    def fee_for(self, shares: float, price: float, taker: bool = True) -> float:
        if shares <= 0 or price <= 0:
            return 0.0
        if self.fee_rate <= 0:
            return 0.0
        raw_fee = shares * self.fee_rate * ((price * (1.0 - price)) ** self.exponent)
        if not taker:
            if self.maker_rebate_rate <= 0:
                return 0.0
            rebate = round(raw_fee * self.maker_rebate_rate, self.precision)
            return -rebate if rebate >= self.min_fee else 0.0
        rounded = round(raw_fee, self.precision)
        return rounded if rounded >= self.min_fee else 0.0

    def fee_per_share(self, price: float, taker: bool = True) -> float:
        if self.fee_rate <= 0 or price <= 0:
            return 0.0
        fee = self.fee_rate * ((price * (1.0 - price)) ** self.exponent)
        if not taker:
            return -fee * self.maker_rebate_rate if self.maker_rebate_rate > 0 else 0.0
        return fee


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
                maker_rebate_rate=float(
                    fee_details.get("rr", fee_details.get("rebateRate", 0.0)) or 0.0
                ),
            ),
        )

    @classmethod
    def from_gamma_market(cls, market: Dict[str, object]) -> "MarketRules":
        fee_schedule = market.get("feeSchedule") or {}
        if isinstance(fee_schedule, str):
            try:
                fee_schedule = json.loads(fee_schedule)
            except ValueError:
                fee_schedule = {}
        if not isinstance(fee_schedule, dict):
            fee_schedule = {}
        return cls(
            tick_size=float(market.get("orderPriceMinTickSize", 0.01) or 0.01),
            min_order_size=float(market.get("orderMinSize", 1.0) or 1.0),
            fee_model=PolymarketFeeModel(
                fee_rate=float(fee_schedule.get("rate", fee_schedule.get("r", 0.0)) or 0.0),
                exponent=float(fee_schedule.get("exponent", fee_schedule.get("e", 1.0)) or 1.0),
                taker_only=bool(fee_schedule.get("takerOnly", fee_schedule.get("to", True))),
                maker_rebate_rate=float(
                    fee_schedule.get("rebateRate", fee_schedule.get("rr", 0.0)) or 0.0
                ),
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
    maker_fill_mode: str = "optimistic"
    maker_queue_ahead_fraction: float = 1.0
    maker_queue_decay: float = 0.5
    maker_fill_probability: float = 1.0
    maker_seed: int = 0
    maker_max_order_age_attempts: int = 0
    maker_cancel_on_price_move: bool = False
    maker_adverse_fill_on_price_move: bool = False
    maker_adverse_fill_fraction: float = 1.0

    def __post_init__(self) -> None:
        if self.latency_model is None:
            self.latency_model = LatencyModel(execution_delay_seconds=self.delay_seconds)
        if self.maker_fill_mode not in MAKER_FILL_MODES:
            raise ValueError(f"maker_fill_mode must be one of {sorted(MAKER_FILL_MODES)}")
        self.maker_queue_ahead_fraction = max(0.0, self.maker_queue_ahead_fraction)
        self.maker_queue_decay = max(0.0, self.maker_queue_decay)
        self.maker_fill_probability = self._clamp_probability(self.maker_fill_probability)
        self.maker_seed = int(self.maker_seed)
        self.maker_max_order_age_attempts = max(0, int(self.maker_max_order_age_attempts))
        self.maker_adverse_fill_fraction = self._clamp_probability(self.maker_adverse_fill_fraction)

    def eligible_at(self, signal: Signal) -> int:
        return signal.timestamp + self.latency_model.total_seconds

    def try_fill(self, order: PaperOrder, book: OrderBook, portfolio: Portfolio) -> Optional[PaperFill]:
        if book.timestamp < order.eligible_at:
            return None
        signal = order.signal
        side = signal.side.upper()
        if side == "BUY":
            if signal.execution_style == "maker":
                return self._fill_maker_buy(order, book, portfolio)
            return self._fill_buy(order, book, portfolio)
        if side == "SELL":
            if signal.execution_style == "maker":
                return self._fill_maker_sell(order, book, portfolio)
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

    def _fill_maker_buy(self, order: PaperOrder, book: OrderBook, portfolio: Portfolio) -> Optional[PaperFill]:
        signal = order.signal
        rules = self._rules_for(signal.asset)
        if order.attempts <= 0:
            return None
        if self._maker_order_expired(order):
            return self._miss_with_book(order, book, "maker_order_expired")
        if signal.target_notional < self.min_notional:
            return self._miss_with_book(order, book, "notional_below_minimum")
        if portfolio.cash < self.min_notional:
            return self._miss_with_book(order, book, "insufficient_cash")
        limit_price = signal.limit_price or 0.0
        if limit_price <= 0:
            return self._miss_with_book(order, book, "missing_limit_price")
        fill_price = self._round_buy_price(limit_price, rules.tick_size)
        if book.bid + 1e-12 < fill_price:
            if self.maker_adverse_fill_on_price_move:
                fillable_fraction = self.maker_adverse_fill_fraction
                reason = "passive_bid_adverse_selection_proxy"
            elif self.maker_cancel_on_price_move:
                return self._miss_with_book(order, book, "maker_price_moved_away")
            else:
                return None
        else:
            if not self._maker_price_is_touch("BUY", fill_price, book, rules) and self.maker_fill_mode != "optimistic":
                return None
            fillable_fraction = self._maker_fillable_fraction(order, book)
            if fillable_fraction <= 0:
                return None
            reason = self._maker_reason("BUY")
        levels = [level for level in sorted(book.bids, key=lambda level: level.price, reverse=True) if level.price >= fill_price]
        requested_gross_cap = min(signal.target_notional, portfolio.cash)
        available_gross = sum(fill_price * level.size for level in levels) * fillable_fraction
        if self.maker_adverse_fill_on_price_move and reason == "passive_bid_adverse_selection_proxy":
            available_gross = max(available_gross, requested_gross_cap * fillable_fraction)
        gross = min(requested_gross_cap, available_gross)
        if gross <= 1e-9:
            return None
        shares = gross / fill_price
        fee = rules.fee_model.fee_for(shares, fill_price, taker=False)
        if shares < rules.min_order_size:
            return self._miss_with_book(order, book, "below_min_order_size")
        if gross + fee > portfolio.cash + 1e-9:
            return self._miss_with_book(order, book, "insufficient_cash_after_fee")
        portfolio.buy(signal.asset, shares, fill_price, fee=fee)
        status = "FILLED" if gross >= requested_gross_cap - 1e-9 else "PARTIAL"
        return PaperFill(
            order_id=order.order_id,
            strategy=signal.strategy,
            asset=signal.asset,
            side="BUY",
            status=status,
            timestamp=book.timestamp,
            price=fill_price,
            shares=shares,
            notional=gross,
            reason=reason,
            quote_timestamp=book.timestamp,
            fee=fee,
            taker=False,
            requested_notional=signal.target_notional,
            filled_notional=gross,
            average_price=fill_price,
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

    def _fill_maker_sell(self, order: PaperOrder, book: OrderBook, portfolio: Portfolio) -> Optional[PaperFill]:
        signal = order.signal
        rules = self._rules_for(signal.asset)
        if order.attempts <= 0:
            return None
        if self._maker_order_expired(order):
            return self._miss_with_book(order, book, "maker_order_expired")
        current_shares = portfolio.positions.get(signal.asset, 0.0)
        if current_shares <= 1e-9:
            return self._miss_with_book(order, book, "no_inventory_no_shorting")
        limit_price = signal.limit_price or 0.0
        if limit_price <= 0:
            return self._miss_with_book(order, book, "missing_limit_price")
        fill_price = self._round_sell_price(limit_price, rules.tick_size)
        if fill_price <= 0:
            return self._miss_with_book(order, book, "invalid_limit_price")
        if book.ask <= 0 or book.ask - 1e-12 > fill_price:
            if self.maker_adverse_fill_on_price_move and book.ask > 0:
                fillable_fraction = self.maker_adverse_fill_fraction
                reason = "passive_ask_adverse_selection_proxy"
            elif self.maker_cancel_on_price_move:
                return self._miss_with_book(order, book, "maker_price_moved_away")
            else:
                return None
        else:
            if not self._maker_price_is_touch("SELL", fill_price, book, rules) and self.maker_fill_mode != "optimistic":
                return None
            fillable_fraction = self._maker_fillable_fraction(order, book)
            if fillable_fraction <= 0:
                return None
            reason = self._maker_reason("SELL")
        levels = [level for level in sorted(book.asks, key=lambda level: level.price) if level.price <= fill_price]
        requested_shares = min(current_shares, signal.target_notional / fill_price)
        available_shares = sum(level.size for level in levels) * fillable_fraction
        if self.maker_adverse_fill_on_price_move and reason == "passive_ask_adverse_selection_proxy":
            available_shares = max(available_shares, requested_shares * fillable_fraction)
        shares = min(requested_shares, available_shares)
        if shares <= 1e-9:
            return None
        gross = shares * fill_price
        if shares < rules.min_order_size:
            return self._miss_with_book(order, book, "below_min_order_size")
        if gross < self.min_notional:
            return self._miss_with_book(order, book, "notional_below_minimum")
        fee = rules.fee_model.fee_for(shares, fill_price, taker=False)
        portfolio.sell(signal.asset, shares, fill_price, fee=fee)
        status = "FILLED" if shares >= requested_shares - 1e-9 else "PARTIAL"
        return PaperFill(
            order_id=order.order_id,
            strategy=signal.strategy,
            asset=signal.asset,
            side="SELL",
            status=status,
            timestamp=book.timestamp,
            price=fill_price,
            shares=shares,
            notional=gross,
            reason=reason,
            quote_timestamp=book.timestamp,
            fee=fee,
            taker=False,
            requested_notional=signal.target_notional,
            filled_notional=gross,
            average_price=fill_price,
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

    def _maker_order_expired(self, order: PaperOrder) -> bool:
        return (
            self.maker_max_order_age_attempts > 0
            and order.attempts >= self.maker_max_order_age_attempts
        )

    def _maker_fillable_fraction(self, order: PaperOrder, book: OrderBook) -> float:
        if self.maker_fill_mode == "optimistic":
            return 1.0
        fraction = min(
            1.0,
            max(0.0, order.attempts * self.maker_queue_decay - self.maker_queue_ahead_fraction),
        )
        if fraction <= 0:
            return 0.0
        if self.maker_fill_mode == "probabilistic_queue":
            probability = fraction * self.maker_fill_probability
            if self._deterministic_unit_interval(
                str(self.maker_seed),
                order.order_id,
                order.signal.asset,
                str(order.attempts),
                str(book.timestamp),
            ) > probability:
                return 0.0
        return fraction

    def _maker_reason(self, side: str) -> str:
        if side == "BUY":
            if self.maker_fill_mode == "optimistic":
                return "passive_bid_fill_proxy"
            if self.maker_fill_mode == "queue_proxy":
                return "passive_bid_queue_proxy"
            return "passive_bid_probabilistic_queue_proxy"
        if self.maker_fill_mode == "optimistic":
            return "passive_ask_fill_proxy"
        if self.maker_fill_mode == "queue_proxy":
            return "passive_ask_queue_proxy"
        return "passive_ask_probabilistic_queue_proxy"

    @staticmethod
    def _maker_price_is_touch(side: str, fill_price: float, book: OrderBook, rules: MarketRules) -> bool:
        tolerance = max(1e-12, rules.tick_size / 2.0)
        if side == "BUY":
            return abs(book.bid - fill_price) <= tolerance
        return book.ask > 0 and abs(book.ask - fill_price) <= tolerance

    @staticmethod
    def _deterministic_unit_interval(*parts: str) -> float:
        payload = "|".join(parts).encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        return int(digest[:16], 16) / float(0xFFFFFFFFFFFFFFFF)

    @staticmethod
    def _clamp_probability(value: float) -> float:
        return min(1.0, max(0.0, float(value)))

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


def residual_maker_order_after_partial(
    order: PaperOrder,
    fill: PaperFill,
    min_notional: float,
) -> Optional[PaperOrder]:
    if order.signal.execution_style != "maker" or fill.status != "PARTIAL":
        return None
    remaining_notional = max(0.0, order.signal.target_notional - fill.notional)
    if remaining_notional < min_notional:
        return None
    residual_signal = replace(order.signal, target_notional=remaining_notional)
    return replace(
        order,
        signal=residual_signal,
        eligible_at=max(order.eligible_at, fill.timestamp + 1),
        attempts=order.attempts + 1,
    )


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
                attempts = order.attempts + 1 if book.timestamp >= order.eligible_at else order.attempts
                still_pending.append(replace(order, attempts=attempts))
                continue
            state.fills.append(fill)
            residual_order = residual_maker_order_after_partial(order, fill, self.fill_model.min_notional)
            if residual_order is not None:
                still_pending.append(residual_order)
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
