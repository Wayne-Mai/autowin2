from __future__ import annotations

from dataclasses import dataclass
import json
import re
import time
from typing import Dict, List, Optional, Sequence
from urllib.parse import quote
from urllib.request import Request, urlopen

from ....models import MarketSnapshot, PaperFill, Portfolio, Signal, StrategyDiagnostic
from ....opportunity import average_buy_price
from ..base import PaperStrategy


CRYPTO_SYMBOL_ALIASES = {
    "BITCOIN": "BTC",
    "BTC": "BTC",
    "ETHEREUM": "ETH",
    "ETH": "ETH",
    "SOLANA": "SOL",
    "SOL": "SOL",
    "XRP": "XRP",
    "RIPPLE": "XRP",
    "BNB": "BNB",
    "BINANCE COIN": "BNB",
}

BINANCE_USDT_SYMBOLS = {
    "BNB": "BNBUSDT",
}


class CoinbaseSpotProvider:
    """Read-only public crypto spot provider with a short shared cache."""

    USER_AGENT = "harness-benchmark/0.1 academic paper trading"
    HOST = "api.coinbase.com"

    def __init__(self, ttl_seconds: float = 30.0, timeout: int = 2, clock=None):
        self.ttl_seconds = ttl_seconds
        self.timeout = timeout
        self.clock = clock or time.time
        self._cache: Dict[str, tuple] = {}

    def prices(self, symbols: Sequence[str]) -> Dict[str, float]:
        result: Dict[str, float] = {}
        now = self.clock()
        for symbol in symbols:
            symbol = str(symbol).upper()
            cached = self._cache.get(symbol)
            if cached is not None and now - float(cached[0]) <= self.ttl_seconds:
                if cached[1] is not None:
                    result[symbol] = float(cached[1])
                continue
            try:
                price = self._fetch_spot(symbol)
            except Exception:
                price = None
            self._cache[symbol] = (now, price)
            if price is None:
                continue
            result[symbol] = price
        return result

    def _fetch_spot(self, symbol: str) -> Optional[float]:
        product = quote(f"{symbol}-USD")
        url = f"https://{self.HOST}/v2/prices/{product}/spot"
        try:
            req = Request(url, method="GET", headers={"User-Agent": self.USER_AGENT})
            with urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read())
            return float(data["data"]["amount"])
        except Exception:
            return self._fetch_binance_spot(symbol)

    def _fetch_binance_spot(self, symbol: str) -> Optional[float]:
        pair = BINANCE_USDT_SYMBOLS.get(symbol)
        if pair is None:
            return None
        url = f"https://data-api.binance.vision/api/v3/ticker/price?symbol={quote(pair)}"
        req = Request(url, method="GET", headers={"User-Agent": self.USER_AGENT})
        with urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read())
        try:
            return float(data["price"])
        except (KeyError, TypeError, ValueError):
            return None


_DEFAULT_SPOT_PROVIDER = CoinbaseSpotProvider()


@dataclass(frozen=True)
class _SpotState:
    current: float
    prior: float
    change_pct: float
    observations: int


@dataclass(frozen=True)
class _CryptoCandidate:
    snapshot: MarketSnapshot
    symbol: str
    direction: str
    spot_change_pct: float
    spread_pct: float
    entry_impact_pct: float
    score: float
    notional: float


@dataclass(frozen=True)
class _IntervalSpec:
    symbol: str
    start_ts: int
    end_ts: int


@dataclass(frozen=True)
class _IntervalAnchor:
    symbol: str
    start_ts: int
    end_ts: int
    anchor_price: float
    anchored_at: int


@dataclass(frozen=True)
class _IntervalCandidate:
    snapshot: MarketSnapshot
    anchor: _IntervalAnchor
    direction: str
    spot_change_pct: float
    seconds_to_close: int
    spread_pct: float
    net_settlement_roi: float
    score: float
    notional: float


class CryptoDirectionalPaperStrategy(PaperStrategy):
    """Trade short crypto up/down markets from public spot momentum."""

    def __init__(
        self,
        initial_cash: float,
        portfolio_target_roi: float = 0.10,
        take_profit_pct: float = 0.03,
        stop_loss_pct: float = 0.02,
        entry_notional: float = 0.0,
        capital_fraction: float = 0.35,
        min_entry_notional: float = 5.0,
        max_spread_pct: float = 0.04,
        max_entry_impact_pct: float = 0.03,
        min_bid_price: float = 0.05,
        max_ask_price: float = 0.90,
        min_spot_move_pct: float = 0.0006,
        lookback_observations: int = 2,
        min_spot_observations: int = 2,
        exit_reversal_pct: float = 0.0004,
        max_positions: int = 2,
        max_entries_per_cycle: int = 1,
        max_hold_cycles: int = 36,
        cooldown_cycles_after_sell: int = 2,
        symbols: Sequence[str] = ("BTC", "ETH", "SOL", "XRP", "BNB"),
        spot_provider=None,
        name: str = "paper_goal_crypto_directional",
        diagnostic_limit: int = 50,
    ):
        self.name = name
        self.initial_cash = initial_cash
        self.portfolio_target_roi = portfolio_target_roi
        self.take_profit_pct = take_profit_pct
        self.stop_loss_pct = stop_loss_pct
        self.entry_notional = entry_notional
        self.capital_fraction = capital_fraction
        self.min_entry_notional = min_entry_notional
        self.max_spread_pct = max_spread_pct
        self.max_entry_impact_pct = max_entry_impact_pct
        self.min_bid_price = min_bid_price
        self.max_ask_price = max_ask_price
        self.min_spot_move_pct = min_spot_move_pct
        self.lookback_observations = max(1, int(lookback_observations))
        self.min_spot_observations = max(2, int(min_spot_observations))
        self.exit_reversal_pct = exit_reversal_pct
        self.max_positions = max(1, int(max_positions))
        self.max_entries_per_cycle = max(1, int(max_entries_per_cycle))
        self.max_hold_cycles = max(0, int(max_hold_cycles))
        self.cooldown_cycles_after_sell = max(0, int(cooldown_cycles_after_sell))
        self.symbols = {str(symbol).upper() for symbol in symbols}
        self.spot_provider = spot_provider or _DEFAULT_SPOT_PROVIDER
        self.diagnostic_limit = diagnostic_limit

        self.avg_cost_by_asset: Dict[str, float] = {}
        self.position_shares_by_asset: Dict[str, float] = {}
        self.symbol_by_asset: Dict[str, str] = {}
        self.direction_by_asset: Dict[str, str] = {}
        self.hold_cycles_by_asset: Dict[str, int] = {}
        self.pending_assets: Dict[str, str] = {}
        self.cooldowns_by_asset: Dict[str, int] = {}
        self.spot_history_by_symbol: Dict[str, List[float]] = {}
        self.latest_spot_state: Dict[str, _SpotState] = {}
        self._diagnostics: List[StrategyDiagnostic] = []
        self.target_reached = False

    def on_snapshot(self, snapshot: MarketSnapshot, portfolio: Portfolio) -> List[Signal]:
        return self.on_snapshots([snapshot], portfolio)

    def on_snapshots(
        self,
        snapshots: Sequence[MarketSnapshot],
        portfolio: Portfolio,
        rules_by_asset: Optional[Dict[str, object]] = None,
    ) -> List[Signal]:
        self._diagnostics = []
        if not snapshots:
            return []
        self._refresh_spot_state(snapshots)
        target_equity = self.initial_cash * (1.0 + self.portfolio_target_roi)
        if self._current_equity(snapshots, portfolio) >= target_equity:
            self.target_reached = True

        exits = []
        for snapshot in snapshots:
            signal = self._exit_signal(snapshot, portfolio, target_equity)
            if signal is not None:
                exits.append(signal)
                if len(exits) >= self.max_entries_per_cycle:
                    self._finish_cycle(snapshots)
                    return exits
        if exits:
            self._finish_cycle(snapshots)
            return exits

        if self.target_reached:
            self._add_cycle_diagnostic(snapshots, "target_reached_waiting_flat")
            self._finish_cycle(snapshots)
            return []

        unavailable = set(portfolio.positions) | set(self.pending_assets)
        if len(unavailable) >= self.max_positions:
            self._add_cycle_diagnostic(snapshots, "position_budget_full")
            self._finish_cycle(snapshots)
            return []
        slots = self.max_positions - len(unavailable)
        entry_notional = self._entry_notional(portfolio.cash, slots)
        if entry_notional < self.min_entry_notional:
            self._add_cycle_diagnostic(snapshots, "no_entry_notional")
            self._finish_cycle(snapshots)
            return []

        candidates = [
            candidate
            for snapshot in snapshots
            for candidate in [self._entry_candidate(snapshot, entry_notional, unavailable)]
            if candidate is not None
        ]
        selected = sorted(candidates, key=lambda item: item.score, reverse=True)[
            : min(slots, self.max_entries_per_cycle)
        ]
        signals = [self._entry_signal(candidate) for candidate in selected]
        for signal in signals:
            self.pending_assets[signal.asset] = signal.side
        self._finish_cycle(snapshots)
        return signals

    def pop_diagnostics(self) -> List[StrategyDiagnostic]:
        diagnostics = self._diagnostics
        self._diagnostics = []
        return diagnostics

    def _refresh_spot_state(self, snapshots: Sequence[MarketSnapshot]) -> None:
        symbols = sorted({symbol for snapshot in snapshots for symbol in [self._symbol_for_snapshot(snapshot)] if symbol})
        if not symbols:
            return
        try:
            prices = self.spot_provider.prices(symbols)
        except Exception:
            prices = {}
        for symbol, price in prices.items():
            if price <= 0:
                continue
            history = self.spot_history_by_symbol.setdefault(symbol, [])
            history.append(price)
            if len(history) > 256:
                del history[:-256]
            if len(history) < self.min_spot_observations:
                continue
            prior_index = max(0, len(history) - 1 - self.lookback_observations)
            prior = history[prior_index]
            change_pct = (price - prior) / prior if prior > 0 else 0.0
            self.latest_spot_state[symbol] = _SpotState(
                current=price,
                prior=prior,
                change_pct=change_pct,
                observations=len(history),
            )

    def _entry_candidate(
        self,
        snapshot: MarketSnapshot,
        target_notional: float,
        unavailable: set,
    ) -> Optional[_CryptoCandidate]:
        if snapshot.asset in unavailable:
            self._add_diagnostic(snapshot, "asset_unavailable")
            return None
        if self.cooldowns_by_asset.get(snapshot.asset, 0) > 0:
            self._add_diagnostic(snapshot, "cooldown_active")
            return None
        symbol = self._symbol_for_snapshot(snapshot)
        if symbol is None:
            return None
        state = self.latest_spot_state.get(symbol)
        if state is None:
            self._add_diagnostic(snapshot, "spot_insufficient_observations")
            return None
        if abs(state.change_pct) < self.min_spot_move_pct:
            self._add_diagnostic(snapshot, "spot_move_too_small", details={"spot_change_pct": state.change_pct})
            return None
        direction = "UP" if state.change_pct > 0 else "DOWN"
        outcome_direction = _direction_from_outcome(snapshot.outcome)
        if outcome_direction != direction:
            self._add_diagnostic(
                snapshot,
                "wrong_outcome_for_spot_direction",
                details={"spot_direction": direction, "outcome_direction": outcome_direction or ""},
            )
            return None
        bid = snapshot.book.bid
        ask = snapshot.book.ask
        if bid < self.min_bid_price:
            self._add_diagnostic(snapshot, "bid_below_min_price")
            return None
        if ask > self.max_ask_price:
            self._add_diagnostic(snapshot, "ask_above_max_price")
            return None
        spread_pct = (ask - bid) / ask if ask > 0 else 1.0
        if spread_pct > self.max_spread_pct:
            self._add_diagnostic(snapshot, "spread_too_wide", details={"spread_pct": spread_pct})
            return None
        sized_entry = self._sized_entry(snapshot, target_notional)
        if sized_entry is None:
            return None
        notional, average_entry, entry_impact_pct = sized_entry
        score = abs(state.change_pct) * 100.0 - spread_pct - entry_impact_pct
        return _CryptoCandidate(
            snapshot=snapshot,
            symbol=symbol,
            direction=direction,
            spot_change_pct=state.change_pct,
            spread_pct=spread_pct,
            entry_impact_pct=entry_impact_pct,
            score=score,
            notional=notional,
        )

    def _sized_entry(self, snapshot: MarketSnapshot, target_notional: float) -> Optional[tuple]:
        ask = snapshot.book.ask
        saw_depth = False
        last_impact = None
        for notional in self._notional_ladder(target_notional):
            average_entry = average_buy_price(snapshot.book, notional)
            if average_entry is None:
                continue
            saw_depth = True
            entry_impact_pct = max(0.0, (average_entry - ask) / average_entry)
            last_impact = entry_impact_pct
            if entry_impact_pct <= self.max_entry_impact_pct:
                return notional, average_entry, entry_impact_pct
        if saw_depth:
            self._add_diagnostic(
                snapshot,
                "entry_impact_too_high",
                details={
                    "entry_impact_pct": last_impact,
                    "target_notional": target_notional,
                    "min_entry_notional": self.min_entry_notional,
                },
            )
        else:
            self._add_diagnostic(
                snapshot,
                "insufficient_ask_depth",
                details={
                    "target_notional": target_notional,
                    "min_entry_notional": self.min_entry_notional,
                },
            )
        return None

    def _notional_ladder(self, target_notional: float) -> List[float]:
        target = min(max(target_notional, 0.0), max(self.min_entry_notional, target_notional))
        if target < self.min_entry_notional:
            return []
        notionals: List[float] = []
        current = target
        while current >= self.min_entry_notional:
            notionals.append(current)
            current *= 0.5
        if notionals and notionals[-1] > self.min_entry_notional:
            notionals.append(self.min_entry_notional)
        return notionals

    def _entry_signal(self, candidate: _CryptoCandidate) -> Signal:
        snapshot = candidate.snapshot
        self.symbol_by_asset[snapshot.asset] = candidate.symbol
        self.direction_by_asset[snapshot.asset] = candidate.direction
        return Signal(
            strategy=self.name,
            timestamp=snapshot.timestamp,
            side="BUY",
            asset=snapshot.asset,
            condition_id=snapshot.condition_id,
            target_notional=candidate.notional,
            reason=(
                f"crypto_directional_entry symbol={candidate.symbol} "
                f"direction={candidate.direction} spot_change={candidate.spot_change_pct:.3%} "
                f"spread={candidate.spread_pct:.2%} impact={candidate.entry_impact_pct:.2%}"
            ),
            execution_style="taker",
        )

    def _exit_signal(
        self,
        snapshot: MarketSnapshot,
        portfolio: Portfolio,
        target_equity: float,
    ) -> Optional[Signal]:
        position = portfolio.positions.get(snapshot.asset, 0.0)
        if position <= 1e-9 or self.pending_assets.get(snapshot.asset) == "SELL":
            return None
        avg_cost = self.avg_cost_by_asset.get(snapshot.asset)
        if avg_cost is None:
            return None
        symbol = self.symbol_by_asset.get(snapshot.asset)
        direction = self.direction_by_asset.get(snapshot.asset)
        state = self.latest_spot_state.get(symbol or "")
        bid = snapshot.book.bid
        take_profit = bid >= avg_cost * (1.0 + self.take_profit_pct)
        stop_loss = bid <= avg_cost * (1.0 - self.stop_loss_pct)
        stale = self.max_hold_cycles > 0 and self.hold_cycles_by_asset.get(snapshot.asset, 0) >= self.max_hold_cycles
        portfolio_target = self.target_reached and portfolio.cash + position * bid >= target_equity
        reversal = False
        if state is not None and direction:
            reversal = (
                direction == "UP" and state.change_pct <= -self.exit_reversal_pct
            ) or (
                direction == "DOWN" and state.change_pct >= self.exit_reversal_pct
            )
        if not (take_profit or stop_loss or stale or portfolio_target or reversal):
            return None
        reason = (
            "portfolio_target_reached"
            if portfolio_target
            else "crypto_take_profit"
            if take_profit
            else "crypto_stop_loss"
            if stop_loss
            else "crypto_spot_reversal"
            if reversal
            else "crypto_max_hold_exit"
        )
        self.pending_assets[snapshot.asset] = "SELL"
        return Signal(
            strategy=self.name,
            timestamp=snapshot.timestamp,
            side="SELL",
            asset=snapshot.asset,
            condition_id=snapshot.condition_id,
            target_notional=position * bid,
            reason=reason,
            execution_style="taker",
        )

    def _entry_notional(self, cash: float, slots: int) -> float:
        if cash <= 0 or slots <= 0:
            return 0.0
        max_capital = cash * min(max(self.capital_fraction, 0.0), 1.0)
        if self.entry_notional > 0:
            return min(self.entry_notional, max_capital, cash)
        return min(max_capital / slots, cash)

    def _current_equity(self, snapshots: Sequence[MarketSnapshot], portfolio: Portfolio) -> float:
        bids = {snapshot.asset: snapshot.book.bid for snapshot in snapshots}
        return portfolio.cash + sum(shares * bids.get(asset, 0.0) for asset, shares in portfolio.positions.items())

    def _finish_cycle(self, snapshots: Sequence[MarketSnapshot]) -> None:
        for snapshot in snapshots:
            if snapshot.asset in self.avg_cost_by_asset and self.pending_assets.get(snapshot.asset) != "SELL":
                self.hold_cycles_by_asset[snapshot.asset] = self.hold_cycles_by_asset.get(snapshot.asset, 0) + 1
        self._decrement_cooldowns()

    def on_fill(self, fill: PaperFill) -> None:
        self.pending_assets.pop(fill.asset, None)
        if fill.status not in {"FILLED", "PARTIAL"}:
            return
        if fill.side == "BUY" and fill.shares > 0:
            previous_shares = self.position_shares_by_asset.get(fill.asset, 0.0)
            previous_cost = self.avg_cost_by_asset.get(fill.asset, 0.0) * previous_shares
            total_shares = previous_shares + fill.shares
            if total_shares <= 1e-9:
                return
            self.position_shares_by_asset[fill.asset] = total_shares
            self.avg_cost_by_asset[fill.asset] = (previous_cost + fill.notional + fill.fee) / total_shares
            self.hold_cycles_by_asset.setdefault(fill.asset, 0)
        elif fill.side == "SELL":
            previous_shares = self.position_shares_by_asset.get(fill.asset, 0.0)
            if fill.status == "PARTIAL" and previous_shares > fill.shares + 1e-9:
                self.position_shares_by_asset[fill.asset] = previous_shares - fill.shares
                return
            self.position_shares_by_asset.pop(fill.asset, None)
            self.avg_cost_by_asset.pop(fill.asset, None)
            self.symbol_by_asset.pop(fill.asset, None)
            self.direction_by_asset.pop(fill.asset, None)
            self.hold_cycles_by_asset.pop(fill.asset, None)
            if self.cooldown_cycles_after_sell > 0:
                self.cooldowns_by_asset[fill.asset] = self.cooldown_cycles_after_sell

    def _decrement_cooldowns(self) -> None:
        expired = []
        for asset, cycles in self.cooldowns_by_asset.items():
            next_cycles = cycles - 1
            if next_cycles <= 0:
                expired.append(asset)
            else:
                self.cooldowns_by_asset[asset] = next_cycles
        for asset in expired:
            self.cooldowns_by_asset.pop(asset, None)

    def _symbol_for_snapshot(self, snapshot: MarketSnapshot) -> Optional[str]:
        text = f"{snapshot.title} {snapshot.slug}".upper()
        if "UP OR DOWN" not in text and "UP-OR-DOWN" not in text and "UPDOWN" not in text:
            return None
        for alias, symbol in CRYPTO_SYMBOL_ALIASES.items():
            if symbol not in self.symbols:
                continue
            if alias in text:
                return symbol
        return None

    def _add_cycle_diagnostic(self, snapshots: Sequence[MarketSnapshot], reason: str) -> None:
        for snapshot in snapshots:
            self._add_diagnostic(snapshot, reason)

    def _add_diagnostic(
        self,
        snapshot: MarketSnapshot,
        reason: str,
        score: Optional[float] = None,
        details: Optional[Dict[str, object]] = None,
    ) -> None:
        if len(self._diagnostics) >= self.diagnostic_limit:
            return
        self._diagnostics.append(
            StrategyDiagnostic(
                strategy=self.name,
                timestamp=snapshot.timestamp,
                asset=snapshot.asset,
                condition_id=snapshot.condition_id,
                reason=reason,
                score=score,
                title=snapshot.title,
                outcome=snapshot.outcome,
                details=details or {},
            )
        )


class CryptoIntervalAnchorPaperStrategy(PaperStrategy):
    """Trade short-window crypto Up/Down markets from an online interval anchor."""

    def __init__(
        self,
        initial_cash: float,
        portfolio_target_roi: float = 0.10,
        take_profit_pct: float = 0.04,
        stop_loss_pct: float = 0.12,
        entry_notional: float = 0.0,
        capital_fraction: float = 0.50,
        min_entry_notional: float = 5.0,
        max_spread_pct: float = 0.08,
        max_entry_impact_pct: float = 0.04,
        min_bid_price: float = 0.03,
        max_ask_price: float = 0.95,
        min_anchor_move_pct: float = 0.0010,
        exit_reversal_pct: float = 0.0004,
        min_net_settlement_roi: float = 0.02,
        max_anchor_lag_seconds: int = 45,
        min_market_age_seconds: int = 20,
        min_seconds_to_close: int = 15,
        hold_to_settlement_after_seconds: int = 210,
        max_positions: int = 2,
        max_entries_per_cycle: int = 1,
        max_hold_cycles: int = 96,
        cooldown_cycles_after_sell: int = 1,
        symbols: Sequence[str] = ("BTC", "ETH", "SOL", "XRP", "BNB"),
        spot_provider=None,
        clock=None,
        name: str = "paper_goal_crypto_interval_anchor",
        diagnostic_limit: int = 50,
    ):
        self.name = name
        self.initial_cash = initial_cash
        self.portfolio_target_roi = portfolio_target_roi
        self.take_profit_pct = take_profit_pct
        self.stop_loss_pct = stop_loss_pct
        self.entry_notional = entry_notional
        self.capital_fraction = capital_fraction
        self.min_entry_notional = min_entry_notional
        self.max_spread_pct = max_spread_pct
        self.max_entry_impact_pct = max_entry_impact_pct
        self.min_bid_price = min_bid_price
        self.max_ask_price = max_ask_price
        self.min_anchor_move_pct = min_anchor_move_pct
        self.exit_reversal_pct = exit_reversal_pct
        self.min_net_settlement_roi = min_net_settlement_roi
        self.max_anchor_lag_seconds = max(0, int(max_anchor_lag_seconds))
        self.min_market_age_seconds = max(0, int(min_market_age_seconds))
        self.min_seconds_to_close = max(0, int(min_seconds_to_close))
        self.hold_to_settlement_after_seconds = max(0, int(hold_to_settlement_after_seconds))
        self.max_positions = max(1, int(max_positions))
        self.max_entries_per_cycle = max(1, int(max_entries_per_cycle))
        self.max_hold_cycles = max(0, int(max_hold_cycles))
        self.cooldown_cycles_after_sell = max(0, int(cooldown_cycles_after_sell))
        self.symbols = {str(symbol).upper() for symbol in symbols}
        self.spot_provider = spot_provider or _DEFAULT_SPOT_PROVIDER
        self.clock = clock or time.time
        self.diagnostic_limit = diagnostic_limit
        self._cycle_wall_time: Optional[int] = None

        self.anchors_by_condition: Dict[str, _IntervalAnchor] = {}
        self.latest_spot_by_symbol: Dict[str, float] = {}
        self.avg_cost_by_asset: Dict[str, float] = {}
        self.position_shares_by_asset: Dict[str, float] = {}
        self.condition_by_asset: Dict[str, str] = {}
        self.symbol_by_asset: Dict[str, str] = {}
        self.direction_by_asset: Dict[str, str] = {}
        self.hold_cycles_by_asset: Dict[str, int] = {}
        self.pending_assets: Dict[str, str] = {}
        self.cooldowns_by_asset: Dict[str, int] = {}
        self._diagnostics: List[StrategyDiagnostic] = []
        self.target_reached = False

    def on_snapshot(self, snapshot: MarketSnapshot, portfolio: Portfolio) -> List[Signal]:
        return self.on_snapshots([snapshot], portfolio)

    def set_cycle_wall_time(self, timestamp: Optional[int]) -> None:
        self._cycle_wall_time = int(timestamp) if timestamp is not None else None

    def on_snapshots(
        self,
        snapshots: Sequence[MarketSnapshot],
        portfolio: Portfolio,
        rules_by_asset: Optional[Dict[str, object]] = None,
    ) -> List[Signal]:
        self._diagnostics = []
        if not snapshots:
            return []
        self._refresh_spot_and_anchors(snapshots)
        target_equity = self.initial_cash * (1.0 + self.portfolio_target_roi)
        if self._current_equity(snapshots, portfolio) >= target_equity:
            self.target_reached = True

        exits = []
        for snapshot in snapshots:
            signal = self._exit_signal(snapshot, portfolio, target_equity)
            if signal is not None:
                exits.append(signal)
                if len(exits) >= self.max_entries_per_cycle:
                    self._finish_cycle(snapshots)
                    return exits
        if exits:
            self._finish_cycle(snapshots)
            return exits
        if self.target_reached:
            self._add_cycle_diagnostic(snapshots, "target_reached_waiting_flat")
            self._finish_cycle(snapshots)
            return []

        unavailable = set(portfolio.positions) | set(self.pending_assets)
        if len(unavailable) >= self.max_positions:
            self._add_cycle_diagnostic(snapshots, "position_budget_full")
            self._finish_cycle(snapshots)
            return []
        slots = self.max_positions - len(unavailable)
        entry_notional = self._entry_notional(portfolio.cash, slots)
        if entry_notional < self.min_entry_notional:
            self._add_cycle_diagnostic(snapshots, "no_entry_notional")
            self._finish_cycle(snapshots)
            return []

        candidates = [
            candidate
            for snapshot in snapshots
            for candidate in [self._entry_candidate(snapshot, entry_notional, unavailable, rules_by_asset or {})]
            if candidate is not None
        ]
        selected = sorted(candidates, key=lambda item: item.score, reverse=True)[
            : min(slots, self.max_entries_per_cycle)
        ]
        signals = [self._entry_signal(candidate) for candidate in selected]
        for signal in signals:
            self.pending_assets[signal.asset] = signal.side
        self._finish_cycle(snapshots)
        return signals

    def pop_diagnostics(self) -> List[StrategyDiagnostic]:
        diagnostics = self._diagnostics
        self._diagnostics = []
        return diagnostics

    def _refresh_spot_and_anchors(self, snapshots: Sequence[MarketSnapshot]) -> None:
        specs_by_condition = {}
        for snapshot in snapshots:
            spec = _interval_spec_from_snapshot(snapshot)
            if spec is None or spec.symbol not in self.symbols:
                continue
            specs_by_condition[snapshot.condition_id] = spec
        symbols = sorted({spec.symbol for spec in specs_by_condition.values()})
        if not symbols:
            return
        try:
            prices = self.spot_provider.prices(symbols)
        except Exception:
            prices = {}
        for symbol, price in prices.items():
            if price > 0:
                self.latest_spot_by_symbol[symbol] = price
        for snapshot in snapshots:
            spec = specs_by_condition.get(snapshot.condition_id)
            if spec is None or snapshot.condition_id in self.anchors_by_condition:
                continue
            spot = self.latest_spot_by_symbol.get(spec.symbol)
            if spot is None:
                self._add_diagnostic(snapshot, "spot_price_unavailable")
                continue
            observed_at = self._observed_at(snapshot, spec)
            age = observed_at - spec.start_ts
            if age < 0:
                self._add_diagnostic(snapshot, "market_not_started")
                continue
            if age > self.max_anchor_lag_seconds:
                self._add_diagnostic(snapshot, "anchor_late", details={"market_age_seconds": age})
                continue
            self.anchors_by_condition[snapshot.condition_id] = _IntervalAnchor(
                symbol=spec.symbol,
                start_ts=spec.start_ts,
                end_ts=spec.end_ts,
                anchor_price=spot,
                anchored_at=observed_at,
            )

    def _entry_candidate(
        self,
        snapshot: MarketSnapshot,
        target_notional: float,
        unavailable: set,
        rules_by_asset: Dict[str, object],
    ) -> Optional[_IntervalCandidate]:
        if snapshot.asset in unavailable:
            self._add_diagnostic(snapshot, "asset_unavailable")
            return None
        if self.cooldowns_by_asset.get(snapshot.asset, 0) > 0:
            self._add_diagnostic(snapshot, "cooldown_active")
            return None
        anchor = self.anchors_by_condition.get(snapshot.condition_id)
        if anchor is None:
            self._add_diagnostic(snapshot, "missing_interval_anchor")
            return None
        spot = self.latest_spot_by_symbol.get(anchor.symbol)
        if spot is None or anchor.anchor_price <= 0:
            self._add_diagnostic(snapshot, "spot_price_unavailable")
            return None
        observed_at = self._observed_at(snapshot, anchor)
        age = observed_at - anchor.start_ts
        seconds_to_close = anchor.end_ts - observed_at
        if age < self.min_market_age_seconds:
            self._add_diagnostic(snapshot, "market_too_young", details={"market_age_seconds": age})
            return None
        if seconds_to_close < self.min_seconds_to_close:
            self._add_diagnostic(snapshot, "market_too_close_to_end", details={"seconds_to_close": seconds_to_close})
            return None
        spot_change_pct = (spot - anchor.anchor_price) / anchor.anchor_price
        if abs(spot_change_pct) < self.min_anchor_move_pct:
            self._add_diagnostic(snapshot, "anchor_move_too_small", details={"spot_change_pct": spot_change_pct})
            return None
        direction = "UP" if spot_change_pct > 0 else "DOWN"
        outcome_direction = _direction_from_outcome(snapshot.outcome)
        if outcome_direction != direction:
            self._add_diagnostic(
                snapshot,
                "wrong_outcome_for_anchor_direction",
                details={"spot_direction": direction, "outcome_direction": outcome_direction or ""},
            )
            return None
        bid = snapshot.book.bid
        ask = snapshot.book.ask
        if bid < self.min_bid_price:
            self._add_diagnostic(snapshot, "bid_below_min_price")
            return None
        if ask <= 0 or ask > self.max_ask_price:
            self._add_diagnostic(snapshot, "ask_above_max_price")
            return None
        spread_pct = (ask - bid) / ask if ask > 0 else 1.0
        if spread_pct > self.max_spread_pct:
            self._add_diagnostic(snapshot, "spread_too_wide", details={"spread_pct": spread_pct})
            return None
        sized_entry = self._sized_entry(snapshot, target_notional, rules_by_asset.get(snapshot.asset))
        if sized_entry is None:
            return None
        notional, _, entry_impact_pct, net_settlement_roi = sized_entry
        if entry_impact_pct > self.max_entry_impact_pct:
            self._add_diagnostic(snapshot, "entry_impact_too_high", details={"entry_impact_pct": entry_impact_pct})
            return None
        if net_settlement_roi < self.min_net_settlement_roi:
            self._add_diagnostic(
                snapshot,
                "settlement_roi_too_small",
                details={"net_settlement_roi": net_settlement_roi},
            )
            return None
        score = abs(spot_change_pct) * 100.0 + net_settlement_roi * 0.25 - spread_pct
        return _IntervalCandidate(
            snapshot=snapshot,
            anchor=anchor,
            direction=direction,
            spot_change_pct=spot_change_pct,
            seconds_to_close=seconds_to_close,
            spread_pct=spread_pct,
            net_settlement_roi=net_settlement_roi,
            score=score,
            notional=notional,
        )

    def _sized_entry(self, snapshot: MarketSnapshot, target_notional: float, rules) -> Optional[tuple]:
        ask = snapshot.book.ask
        saw_depth = False
        last_impact = None
        fee_model = getattr(rules, "fee_model", None)
        for notional in self._notional_ladder(target_notional):
            average_entry = average_buy_price(snapshot.book, notional)
            if average_entry is None or average_entry <= 0:
                continue
            saw_depth = True
            shares = notional / average_entry
            entry_impact_pct = max(0.0, (average_entry - ask) / average_entry)
            last_impact = entry_impact_pct
            fee = fee_model.fee_for(shares, average_entry, taker=True) if fee_model is not None else 0.0
            net_settlement_roi = shares / (notional + fee) - 1.0 if notional + fee > 0 else -1.0
            if entry_impact_pct <= self.max_entry_impact_pct and net_settlement_roi >= self.min_net_settlement_roi:
                return notional, average_entry, entry_impact_pct, net_settlement_roi
        if saw_depth:
            self._add_diagnostic(
                snapshot,
                "entry_not_viable_after_sizing",
                details={
                    "entry_impact_pct": last_impact,
                    "target_notional": target_notional,
                    "min_entry_notional": self.min_entry_notional,
                },
            )
        else:
            self._add_diagnostic(
                snapshot,
                "insufficient_ask_depth",
                details={
                    "target_notional": target_notional,
                    "min_entry_notional": self.min_entry_notional,
                },
            )
        return None

    def _notional_ladder(self, target_notional: float) -> List[float]:
        target = min(max(target_notional, 0.0), max(self.min_entry_notional, target_notional))
        if target < self.min_entry_notional:
            return []
        notionals: List[float] = []
        current = target
        while current >= self.min_entry_notional:
            notionals.append(current)
            current *= 0.5
        if notionals and notionals[-1] > self.min_entry_notional:
            notionals.append(self.min_entry_notional)
        return notionals

    def _entry_signal(self, candidate: _IntervalCandidate) -> Signal:
        snapshot = candidate.snapshot
        self.condition_by_asset[snapshot.asset] = snapshot.condition_id
        self.symbol_by_asset[snapshot.asset] = candidate.anchor.symbol
        self.direction_by_asset[snapshot.asset] = candidate.direction
        return Signal(
            strategy=self.name,
            timestamp=snapshot.timestamp,
            side="BUY",
            asset=snapshot.asset,
            condition_id=snapshot.condition_id,
            target_notional=candidate.notional,
            reason=(
                f"crypto_interval_anchor_entry symbol={candidate.anchor.symbol} "
                f"direction={candidate.direction} spot_from_anchor={candidate.spot_change_pct:.3%} "
                f"settlement_roi={candidate.net_settlement_roi:.2%} "
                f"seconds_to_close={candidate.seconds_to_close}"
            ),
            execution_style="taker",
        )

    def _exit_signal(
        self,
        snapshot: MarketSnapshot,
        portfolio: Portfolio,
        target_equity: float,
    ) -> Optional[Signal]:
        position = portfolio.positions.get(snapshot.asset, 0.0)
        if position <= 1e-9 or self.pending_assets.get(snapshot.asset) == "SELL":
            return None
        avg_cost = self.avg_cost_by_asset.get(snapshot.asset)
        if avg_cost is None:
            return None
        condition_id = self.condition_by_asset.get(snapshot.asset, snapshot.condition_id)
        anchor = self.anchors_by_condition.get(condition_id)
        symbol = self.symbol_by_asset.get(snapshot.asset)
        direction = self.direction_by_asset.get(snapshot.asset)
        spot = self.latest_spot_by_symbol.get(symbol or "")
        bid = snapshot.book.bid
        age = self._observed_at(snapshot, anchor) - anchor.start_ts if anchor is not None else 0
        take_profit = bid >= avg_cost * (1.0 + self.take_profit_pct)
        stop_loss = bid <= avg_cost * (1.0 - self.stop_loss_pct)
        stale = self.max_hold_cycles > 0 and self.hold_cycles_by_asset.get(snapshot.asset, 0) >= self.max_hold_cycles
        portfolio_target = self.target_reached and portfolio.cash + position * bid >= target_equity
        reversal = False
        if anchor is not None and spot is not None and direction and age < self.hold_to_settlement_after_seconds:
            spot_change_pct = (spot - anchor.anchor_price) / anchor.anchor_price if anchor.anchor_price > 0 else 0.0
            reversal = (
                direction == "UP" and spot_change_pct <= -self.exit_reversal_pct
            ) or (
                direction == "DOWN" and spot_change_pct >= self.exit_reversal_pct
            )
        if not (take_profit or stop_loss or stale or portfolio_target or reversal):
            return None
        reason = (
            "portfolio_target_reached"
            if portfolio_target
            else "crypto_interval_take_profit"
            if take_profit
            else "crypto_interval_stop_loss"
            if stop_loss
            else "crypto_interval_anchor_reversal"
            if reversal
            else "crypto_interval_max_hold_exit"
        )
        self.pending_assets[snapshot.asset] = "SELL"
        return Signal(
            strategy=self.name,
            timestamp=snapshot.timestamp,
            side="SELL",
            asset=snapshot.asset,
            condition_id=condition_id,
            target_notional=position * bid,
            reason=reason,
            execution_style="taker",
        )

    def _entry_notional(self, cash: float, slots: int) -> float:
        if cash <= 0 or slots <= 0:
            return 0.0
        max_capital = cash * min(max(self.capital_fraction, 0.0), 1.0)
        if self.entry_notional > 0:
            return min(self.entry_notional, max_capital, cash)
        return min(max_capital / slots, cash)

    def _current_equity(self, snapshots: Sequence[MarketSnapshot], portfolio: Portfolio) -> float:
        bids = {snapshot.asset: snapshot.book.bid for snapshot in snapshots}
        return portfolio.cash + sum(shares * bids.get(asset, 0.0) for asset, shares in portfolio.positions.items())

    def _finish_cycle(self, snapshots: Sequence[MarketSnapshot]) -> None:
        for snapshot in snapshots:
            if snapshot.asset in self.avg_cost_by_asset and self.pending_assets.get(snapshot.asset) != "SELL":
                self.hold_cycles_by_asset[snapshot.asset] = self.hold_cycles_by_asset.get(snapshot.asset, 0) + 1
        self._decrement_cooldowns()

    def on_fill(self, fill: PaperFill) -> None:
        self.pending_assets.pop(fill.asset, None)
        if fill.status not in {"FILLED", "PARTIAL"}:
            return
        if fill.side == "BUY" and fill.shares > 0:
            previous_shares = self.position_shares_by_asset.get(fill.asset, 0.0)
            previous_cost = self.avg_cost_by_asset.get(fill.asset, 0.0) * previous_shares
            total_shares = previous_shares + fill.shares
            if total_shares <= 1e-9:
                return
            self.position_shares_by_asset[fill.asset] = total_shares
            self.avg_cost_by_asset[fill.asset] = (previous_cost + fill.notional + fill.fee) / total_shares
            self.hold_cycles_by_asset.setdefault(fill.asset, 0)
        elif fill.side == "SELL":
            previous_shares = self.position_shares_by_asset.get(fill.asset, 0.0)
            if fill.status == "PARTIAL" and previous_shares > fill.shares + 1e-9:
                self.position_shares_by_asset[fill.asset] = previous_shares - fill.shares
                return
            self.position_shares_by_asset.pop(fill.asset, None)
            self.avg_cost_by_asset.pop(fill.asset, None)
            self.condition_by_asset.pop(fill.asset, None)
            self.symbol_by_asset.pop(fill.asset, None)
            self.direction_by_asset.pop(fill.asset, None)
            self.hold_cycles_by_asset.pop(fill.asset, None)
            if self.cooldown_cycles_after_sell > 0:
                self.cooldowns_by_asset[fill.asset] = self.cooldown_cycles_after_sell

    def _decrement_cooldowns(self) -> None:
        expired = []
        for asset, cycles in self.cooldowns_by_asset.items():
            next_cycles = cycles - 1
            if next_cycles <= 0:
                expired.append(asset)
            else:
                self.cooldowns_by_asset[asset] = next_cycles
        for asset in expired:
            self.cooldowns_by_asset.pop(asset, None)

    def _observed_at(self, snapshot: MarketSnapshot, interval) -> int:
        timestamp = int(snapshot.timestamp)
        if interval is None:
            return timestamp
        wall = int(self._cycle_wall_time if self._cycle_wall_time is not None else self.clock())
        if int(interval.start_ts) - 30 <= wall <= int(interval.end_ts) + 300:
            return max(timestamp, wall)
        return timestamp

    def _add_cycle_diagnostic(self, snapshots: Sequence[MarketSnapshot], reason: str) -> None:
        for snapshot in snapshots:
            self._add_diagnostic(snapshot, reason)

    def _add_diagnostic(
        self,
        snapshot: MarketSnapshot,
        reason: str,
        score: Optional[float] = None,
        details: Optional[Dict[str, object]] = None,
    ) -> None:
        if len(self._diagnostics) >= self.diagnostic_limit:
            return
        self._diagnostics.append(
            StrategyDiagnostic(
                strategy=self.name,
                timestamp=snapshot.timestamp,
                asset=snapshot.asset,
                condition_id=snapshot.condition_id,
                reason=reason,
                score=score,
                title=snapshot.title,
                outcome=snapshot.outcome,
                details=details or {},
            )
        )


class CryptoIntervalCloseEdgePaperStrategy(CryptoIntervalAnchorPaperStrategy):
    """Trade anchored crypto Up/Down markets only near the settlement window."""

    def __init__(
        self,
        initial_cash: float,
        portfolio_target_roi: float = 0.10,
        take_profit_pct: float = 0.02,
        stop_loss_pct: float = 0.20,
        entry_notional: float = 0.0,
        capital_fraction: float = 0.50,
        min_entry_notional: float = 5.0,
        max_spread_pct: float = 0.08,
        max_entry_impact_pct: float = 0.04,
        min_bid_price: float = 0.03,
        max_ask_price: float = 0.95,
        min_anchor_move_pct: float = 0.0005,
        exit_reversal_pct: float = 0.0003,
        min_net_settlement_roi: float = 0.04,
        max_anchor_lag_seconds: int = 90,
        min_market_age_seconds: int = 210,
        min_seconds_to_close: int = 5,
        max_seconds_to_close: int = 75,
        hold_to_settlement_after_seconds: int = 0,
        max_positions: int = 2,
        max_entries_per_cycle: int = 1,
        max_hold_cycles: int = 96,
        cooldown_cycles_after_sell: int = 1,
        symbols: Sequence[str] = ("BTC", "ETH", "SOL", "XRP", "BNB"),
        spot_provider=None,
        clock=None,
        name: str = "paper_goal_crypto_interval_close_edge",
        diagnostic_limit: int = 50,
    ):
        super().__init__(
            initial_cash=initial_cash,
            portfolio_target_roi=portfolio_target_roi,
            take_profit_pct=take_profit_pct,
            stop_loss_pct=stop_loss_pct,
            entry_notional=entry_notional,
            capital_fraction=capital_fraction,
            min_entry_notional=min_entry_notional,
            max_spread_pct=max_spread_pct,
            max_entry_impact_pct=max_entry_impact_pct,
            min_bid_price=min_bid_price,
            max_ask_price=max_ask_price,
            min_anchor_move_pct=min_anchor_move_pct,
            exit_reversal_pct=exit_reversal_pct,
            min_net_settlement_roi=min_net_settlement_roi,
            max_anchor_lag_seconds=max_anchor_lag_seconds,
            min_market_age_seconds=min_market_age_seconds,
            min_seconds_to_close=min_seconds_to_close,
            hold_to_settlement_after_seconds=hold_to_settlement_after_seconds,
            max_positions=max_positions,
            max_entries_per_cycle=max_entries_per_cycle,
            max_hold_cycles=max_hold_cycles,
            cooldown_cycles_after_sell=cooldown_cycles_after_sell,
            symbols=symbols,
            spot_provider=spot_provider,
            clock=clock,
            name=name,
            diagnostic_limit=diagnostic_limit,
        )
        self.max_seconds_to_close = max(0, int(max_seconds_to_close))

    def _entry_candidate(
        self,
        snapshot: MarketSnapshot,
        target_notional: float,
        unavailable: set,
        rules_by_asset: Dict[str, object],
    ) -> Optional[_IntervalCandidate]:
        candidate = super()._entry_candidate(snapshot, target_notional, unavailable, rules_by_asset)
        if candidate is None:
            return None
        if self.max_seconds_to_close and candidate.seconds_to_close > self.max_seconds_to_close:
            self._add_diagnostic(
                snapshot,
                "not_close_enough_to_settlement",
                details={"seconds_to_close": candidate.seconds_to_close},
            )
            return None
        close_score = candidate.score + (self.max_seconds_to_close - candidate.seconds_to_close) / max(
            self.max_seconds_to_close,
            1,
        )
        return _IntervalCandidate(
            snapshot=candidate.snapshot,
            anchor=candidate.anchor,
            direction=candidate.direction,
            spot_change_pct=candidate.spot_change_pct,
            seconds_to_close=candidate.seconds_to_close,
            spread_pct=candidate.spread_pct,
            net_settlement_roi=candidate.net_settlement_roi,
            score=close_score,
            notional=candidate.notional,
        )

    def _entry_signal(self, candidate: _IntervalCandidate) -> Signal:
        snapshot = candidate.snapshot
        self.condition_by_asset[snapshot.asset] = snapshot.condition_id
        self.symbol_by_asset[snapshot.asset] = candidate.anchor.symbol
        self.direction_by_asset[snapshot.asset] = candidate.direction
        return Signal(
            strategy=self.name,
            timestamp=snapshot.timestamp,
            side="BUY",
            asset=snapshot.asset,
            condition_id=snapshot.condition_id,
            target_notional=candidate.notional,
            reason=(
                f"crypto_interval_close_edge_entry symbol={candidate.anchor.symbol} "
                f"direction={candidate.direction} spot_from_anchor={candidate.spot_change_pct:.3%} "
                f"settlement_roi={candidate.net_settlement_roi:.2%} "
                f"seconds_to_close={candidate.seconds_to_close}"
            ),
            execution_style="taker",
        )


class CryptoIntervalBookSkewPaperStrategy(CryptoIntervalAnchorPaperStrategy):
    """Trade active crypto Up/Down intervals from order-book implied direction."""

    def __init__(
        self,
        initial_cash: float,
        portfolio_target_roi: float = 0.10,
        take_profit_pct: float = 0.03,
        stop_loss_pct: float = 0.35,
        entry_notional: float = 0.0,
        capital_fraction: float = 0.60,
        min_entry_notional: float = 5.0,
        max_spread_pct: float = 0.06,
        max_entry_impact_pct: float = 0.04,
        min_bid_price: float = 0.58,
        max_ask_price: float = 0.88,
        min_net_settlement_roi: float = 0.08,
        min_market_age_seconds: int = 20,
        min_seconds_to_close: int = 20,
        max_seconds_to_close: int = 240,
        max_positions: int = 2,
        max_entries_per_cycle: int = 1,
        max_hold_cycles: int = 96,
        cooldown_cycles_after_sell: int = 1,
        symbols: Sequence[str] = ("BTC", "ETH", "SOL", "XRP", "BNB"),
        clock=None,
        name: str = "paper_goal_crypto_interval_book_skew",
        diagnostic_limit: int = 50,
    ):
        super().__init__(
            initial_cash=initial_cash,
            portfolio_target_roi=portfolio_target_roi,
            take_profit_pct=take_profit_pct,
            stop_loss_pct=stop_loss_pct,
            entry_notional=entry_notional,
            capital_fraction=capital_fraction,
            min_entry_notional=min_entry_notional,
            max_spread_pct=max_spread_pct,
            max_entry_impact_pct=max_entry_impact_pct,
            min_bid_price=min_bid_price,
            max_ask_price=max_ask_price,
            min_anchor_move_pct=0.0,
            exit_reversal_pct=0.0,
            min_net_settlement_roi=min_net_settlement_roi,
            max_anchor_lag_seconds=0,
            min_market_age_seconds=min_market_age_seconds,
            min_seconds_to_close=min_seconds_to_close,
            hold_to_settlement_after_seconds=0,
            max_positions=max_positions,
            max_entries_per_cycle=max_entries_per_cycle,
            max_hold_cycles=max_hold_cycles,
            cooldown_cycles_after_sell=cooldown_cycles_after_sell,
            symbols=symbols,
            spot_provider=None,
            clock=clock,
            name=name,
            diagnostic_limit=diagnostic_limit,
        )
        self.max_seconds_to_close = max(0, int(max_seconds_to_close))

    def _refresh_spot_and_anchors(self, snapshots: Sequence[MarketSnapshot]) -> None:
        return None

    def _entry_candidate(
        self,
        snapshot: MarketSnapshot,
        target_notional: float,
        unavailable: set,
        rules_by_asset: Dict[str, object],
    ) -> Optional[_IntervalCandidate]:
        if snapshot.asset in unavailable:
            self._add_diagnostic(snapshot, "asset_unavailable")
            return None
        if self.cooldowns_by_asset.get(snapshot.asset, 0) > 0:
            self._add_diagnostic(snapshot, "cooldown_active")
            return None
        spec = _interval_spec_from_snapshot(snapshot)
        if spec is None or spec.symbol not in self.symbols:
            self._add_diagnostic(snapshot, "not_crypto_interval")
            return None
        observed_at = self._observed_at(snapshot, spec)
        age = observed_at - spec.start_ts
        seconds_to_close = spec.end_ts - observed_at
        if age < 0:
            self._add_diagnostic(snapshot, "market_not_started")
            return None
        if age < self.min_market_age_seconds:
            self._add_diagnostic(snapshot, "market_too_young", details={"market_age_seconds": age})
            return None
        if seconds_to_close < self.min_seconds_to_close:
            self._add_diagnostic(snapshot, "market_too_close_to_end", details={"seconds_to_close": seconds_to_close})
            return None
        if self.max_seconds_to_close and seconds_to_close > self.max_seconds_to_close:
            self._add_diagnostic(snapshot, "not_close_enough_to_settlement", details={"seconds_to_close": seconds_to_close})
            return None
        direction = _direction_from_outcome(snapshot.outcome)
        if direction is None:
            self._add_diagnostic(snapshot, "unsupported_outcome_direction")
            return None
        bid = snapshot.book.bid
        ask = snapshot.book.ask
        if bid < self.min_bid_price:
            self._add_diagnostic(snapshot, "bid_below_min_price")
            return None
        if ask <= 0 or ask > self.max_ask_price:
            self._add_diagnostic(snapshot, "ask_above_max_price")
            return None
        spread_pct = (ask - bid) / ask if ask > 0 else 1.0
        if spread_pct > self.max_spread_pct:
            self._add_diagnostic(snapshot, "spread_too_wide", details={"spread_pct": spread_pct})
            return None
        sized_entry = self._sized_entry(snapshot, target_notional, rules_by_asset.get(snapshot.asset))
        if sized_entry is None:
            return None
        notional, _, entry_impact_pct, net_settlement_roi = sized_entry
        if entry_impact_pct > self.max_entry_impact_pct:
            self._add_diagnostic(snapshot, "entry_impact_too_high", details={"entry_impact_pct": entry_impact_pct})
            return None
        if net_settlement_roi < self.min_net_settlement_roi:
            self._add_diagnostic(
                snapshot,
                "settlement_roi_too_small",
                details={"net_settlement_roi": net_settlement_roi},
            )
            return None
        anchor = _IntervalAnchor(
            symbol=spec.symbol,
            start_ts=spec.start_ts,
            end_ts=spec.end_ts,
            anchor_price=1.0,
            anchored_at=observed_at,
        )
        score = bid + net_settlement_roi * 0.5 - spread_pct + (
            self.max_seconds_to_close - seconds_to_close
        ) / max(self.max_seconds_to_close, 1)
        return _IntervalCandidate(
            snapshot=snapshot,
            anchor=anchor,
            direction=direction,
            spot_change_pct=0.0,
            seconds_to_close=seconds_to_close,
            spread_pct=spread_pct,
            net_settlement_roi=net_settlement_roi,
            score=score,
            notional=notional,
        )

    def _entry_signal(self, candidate: _IntervalCandidate) -> Signal:
        snapshot = candidate.snapshot
        self.condition_by_asset[snapshot.asset] = snapshot.condition_id
        self.symbol_by_asset[snapshot.asset] = candidate.anchor.symbol
        self.direction_by_asset[snapshot.asset] = candidate.direction
        return Signal(
            strategy=self.name,
            timestamp=snapshot.timestamp,
            side="BUY",
            asset=snapshot.asset,
            condition_id=snapshot.condition_id,
            target_notional=candidate.notional,
            reason=(
                f"crypto_interval_book_skew_entry symbol={candidate.anchor.symbol} "
                f"direction={candidate.direction} bid={snapshot.book.bid:.3f} ask={snapshot.book.ask:.3f} "
                f"settlement_roi={candidate.net_settlement_roi:.2%} "
                f"seconds_to_close={candidate.seconds_to_close}"
            ),
            execution_style="taker",
        )


def _direction_from_outcome(outcome: str) -> Optional[str]:
    normalized = str(outcome or "").strip().upper()
    if normalized in {"UP", "YES"}:
        return "UP"
    if normalized in {"DOWN", "NO"}:
        return "DOWN"
    return None


def _interval_spec_from_snapshot(snapshot: MarketSnapshot) -> Optional[_IntervalSpec]:
    text = f"{snapshot.slug} {snapshot.title}".lower()
    match = re.search(r"\b(btc|eth|sol|xrp|bnb)-updown-(5|15)m-(\d{9,12})\b", text)
    if not match:
        return None
    symbol = CRYPTO_SYMBOL_ALIASES.get(match.group(1).upper())
    if symbol is None:
        return None
    minutes = int(match.group(2))
    start_ts = int(match.group(3))
    return _IntervalSpec(symbol=symbol, start_ts=start_ts, end_ts=start_ts + minutes * 60)
