from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

from ....models import MarketSnapshot, PaperFill, Portfolio, Signal, StrategyDiagnostic
from ....opportunity import (
    average_buy_price,
    book_depth_imbalance,
    required_exit_price_for_net_proceeds,
)
from ..base import PaperStrategy


@dataclass(frozen=True)
class _MarketState:
    bid: float
    ask: float
    mid: float
    spread_pct: float
    observations: int


@dataclass(frozen=True)
class _EntryCandidate:
    snapshot: MarketSnapshot
    notional: float
    score: float
    bid_improvement: float
    mid_improvement: float
    spread_pct: float
    book_imbalance: float


class MomentumScalperPaperStrategy(PaperStrategy):
    """Short-horizon taker momentum strategy for realistic paper validation."""

    def __init__(
        self,
        initial_cash: float,
        portfolio_target_roi: float = 0.10,
        take_profit_pct: float = 0.04,
        stop_loss_pct: float = 0.04,
        entry_notional: float = 0.0,
        capital_fraction: float = 0.50,
        min_entry_notional: float = 5.0,
        max_spread_pct: float = 0.04,
        min_spread_pct: float = 0.0,
        max_entry_impact_pct: float = 0.05,
        min_book_imbalance: float = -1.0,
        depth_window_pct: float = 0.03,
        min_bid_price: Optional[float] = 0.10,
        max_bid_price: Optional[float] = 0.90,
        min_momentum_observations: int = 2,
        min_bid_improvement_pct: float = 0.001,
        min_mid_improvement_pct: float = 0.001,
        max_spread_widen_pct: float = 0.02,
        max_positions: int = 2,
        max_entries_per_cycle: int = 1,
        cooldown_cycles_after_sell: int = 2,
        max_hold_cycles: int = 18,
        max_hold_min_progress_pct: float = 0.0,
        max_hold_cooldown_cycles: int = 4,
        entry_execution_style: str = "taker",
        maker_exit: bool = False,
        name: str = "paper_goal_momentum_scalper",
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
        self.min_spread_pct = min_spread_pct
        self.max_entry_impact_pct = max_entry_impact_pct
        self.min_book_imbalance = min_book_imbalance
        self.depth_window_pct = depth_window_pct
        self.min_bid_price = min_bid_price
        self.max_bid_price = max_bid_price
        self.min_momentum_observations = max(1, int(min_momentum_observations))
        self.min_bid_improvement_pct = min_bid_improvement_pct
        self.min_mid_improvement_pct = min_mid_improvement_pct
        self.max_spread_widen_pct = max_spread_widen_pct
        self.max_positions = max(1, int(max_positions))
        self.max_entries_per_cycle = max(1, int(max_entries_per_cycle))
        self.cooldown_cycles_after_sell = max(0, int(cooldown_cycles_after_sell))
        self.max_hold_cycles = max(0, int(max_hold_cycles))
        self.max_hold_min_progress_pct = max_hold_min_progress_pct
        self.max_hold_cooldown_cycles = max(0, int(max_hold_cooldown_cycles))
        self.entry_execution_style = entry_execution_style
        self.maker_exit = maker_exit
        self.diagnostic_limit = diagnostic_limit

        self.avg_cost_by_asset: Dict[str, float] = {}
        self.position_shares_by_asset: Dict[str, float] = {}
        self.entry_bid_by_asset: Dict[str, float] = {}
        self.hold_cycles_by_asset: Dict[str, int] = {}
        self.pending_assets: Dict[str, str] = {}
        self.market_state_by_asset: Dict[str, _MarketState] = {}
        self.cooldowns_by_asset: Dict[str, int] = {}
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

        target_equity = self.initial_cash * (1.0 + self.portfolio_target_roi)
        current_equity = self._current_equity(snapshots, portfolio)
        if current_equity >= target_equity:
            self.target_reached = True

        exits: List[Signal] = []
        for snapshot in snapshots:
            signal = self._exit_signal(snapshot, portfolio, target_equity, rules_by_asset or {})
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
        if not candidates:
            self._finish_cycle(snapshots)
            return []

        selected = sorted(candidates, key=lambda candidate: candidate.score, reverse=True)[
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

    def _exit_signal(
        self,
        snapshot: MarketSnapshot,
        portfolio: Portfolio,
        target_equity: float,
        rules_by_asset: Dict[str, object],
    ) -> Optional[Signal]:
        position = portfolio.positions.get(snapshot.asset, 0.0)
        pending_side = self.pending_assets.get(snapshot.asset)
        if position <= 1e-9 or (pending_side == "SELL" and not self.target_reached):
            return None
        avg_cost = self.avg_cost_by_asset.get(snapshot.asset)
        if avg_cost is None:
            return None
        rules = rules_by_asset.get(snapshot.asset)
        fee_model = getattr(rules, "fee_model", None)
        take_profit_bid = required_exit_price_for_net_proceeds(
            shares=position,
            required_net_proceeds=position * avg_cost * (1.0 + self.take_profit_pct),
            max_exit_price=1.0,
            fee_model=fee_model,
        )
        portfolio_target_bid = required_exit_price_for_net_proceeds(
            shares=position,
            required_net_proceeds=target_equity - portfolio.cash,
            max_exit_price=1.0,
            fee_model=fee_model,
        )
        required_bid = min(take_profit_bid, portfolio_target_bid) if self.target_reached else take_profit_bid
        stop_loss = snapshot.book.bid <= avg_cost * (1.0 - self.stop_loss_pct)
        stale_exit = self._stale_exit(snapshot.asset, snapshot.book.bid, required_bid)
        taker_profit = snapshot.book.bid >= required_bid
        maker_profit = self.maker_exit and snapshot.book.ask >= required_bid
        should_exit = self.target_reached or taker_profit or maker_profit or stop_loss or stale_exit
        if not should_exit:
            return None
        maker_stale_exit = self.maker_exit and stale_exit and not taker_profit and not stop_loss
        execution_style = (
            "taker"
            if self.target_reached
            else "maker"
            if (maker_profit or maker_stale_exit) and not taker_profit and not stop_loss
            else "taker"
        )
        limit_price = snapshot.book.ask if execution_style == "maker" else None
        exit_price = limit_price or snapshot.book.bid
        reason = (
            "portfolio_target_reached"
            if self.target_reached
            else "take_profit"
            if taker_profit or maker_profit
            else "stop_loss"
            if stop_loss
            else "stale_position_exit"
        )
        self.pending_assets[snapshot.asset] = "SELL"
        if stale_exit and self.max_hold_cooldown_cycles > 0:
            self.cooldowns_by_asset[snapshot.asset] = self.max_hold_cooldown_cycles
        return Signal(
            strategy=self.name,
            timestamp=snapshot.timestamp,
            side="SELL",
            asset=snapshot.asset,
            condition_id=snapshot.condition_id,
            target_notional=position * exit_price,
            reason=reason,
            execution_style=execution_style,
            limit_price=limit_price,
        )

    def _entry_candidate(
        self,
        snapshot: MarketSnapshot,
        target_notional: float,
        unavailable: set,
        rules_by_asset: Optional[Dict[str, object]] = None,
    ) -> Optional[_EntryCandidate]:
        if snapshot.asset in unavailable:
            self._add_diagnostic(snapshot, "asset_unavailable")
            return None
        if self.cooldowns_by_asset.get(snapshot.asset, 0) > 0:
            self._add_diagnostic(snapshot, "cooldown_active")
            return None
        bid = snapshot.book.bid
        ask = snapshot.book.ask
        if bid <= 0 or ask <= 0:
            self._add_diagnostic(snapshot, "missing_bid_or_ask")
            return None
        if self.min_bid_price is not None and bid < self.min_bid_price:
            self._add_diagnostic(snapshot, "bid_below_min_price")
            return None
        if self.max_bid_price is not None and bid > self.max_bid_price:
            self._add_diagnostic(snapshot, "bid_above_max_price")
            return None
        spread_pct = (ask - bid) / ask
        if spread_pct > self.max_spread_pct:
            self._add_diagnostic(snapshot, "spread_too_wide", details={"spread_pct": spread_pct})
            return None
        if spread_pct < self.min_spread_pct:
            self._add_diagnostic(snapshot, "spread_too_tight", details={"spread_pct": spread_pct})
            return None
        previous = self.market_state_by_asset.get(snapshot.asset)
        if previous is None:
            self._add_diagnostic(snapshot, "momentum_no_previous_observation")
            return None
        observations = previous.observations + 1
        if observations < self.min_momentum_observations:
            self._add_diagnostic(
                snapshot,
                "momentum_insufficient_observations",
                details={"observations": observations, "required_observations": self.min_momentum_observations},
            )
            return None
        mid = (bid + ask) / 2.0
        bid_improvement = self._relative_change(bid, previous.bid)
        mid_improvement = self._relative_change(mid, previous.mid)
        spread_widen = spread_pct - previous.spread_pct
        if bid_improvement < self.min_bid_improvement_pct:
            self._add_diagnostic(snapshot, "momentum_bid_not_improving", details={"bid_improvement_pct": bid_improvement})
            return None
        if mid_improvement < self.min_mid_improvement_pct:
            self._add_diagnostic(snapshot, "momentum_mid_not_improving", details={"mid_improvement_pct": mid_improvement})
            return None
        if spread_widen > self.max_spread_widen_pct:
            self._add_diagnostic(snapshot, "momentum_spread_widened", details={"spread_widen_pct": spread_widen})
            return None
        average_entry = (
            bid if self.entry_execution_style == "maker" else average_buy_price(snapshot.book, target_notional)
        )
        if average_entry is None:
            self._add_diagnostic(snapshot, "insufficient_ask_depth")
            return None
        entry_impact = max(0.0, (average_entry - bid) / average_entry)
        if entry_impact > self.max_entry_impact_pct:
            self._add_diagnostic(snapshot, "entry_impact_too_high", details={"entry_impact_pct": entry_impact})
            return None
        _, _, book_imbalance = book_depth_imbalance(snapshot.book, self.depth_window_pct)
        if book_imbalance < self.min_book_imbalance:
            self._add_diagnostic(snapshot, "book_imbalance_too_weak", details={"book_imbalance": book_imbalance})
            return None
        score = bid_improvement + mid_improvement + max(book_imbalance, -1.0) * 0.02 - spread_pct
        return _EntryCandidate(
            snapshot=snapshot,
            notional=target_notional,
            score=score,
            bid_improvement=bid_improvement,
            mid_improvement=mid_improvement,
            spread_pct=spread_pct,
            book_imbalance=book_imbalance,
        )

    def _entry_signal(self, candidate: _EntryCandidate) -> Signal:
        snapshot = candidate.snapshot
        limit_price = snapshot.book.bid if self.entry_execution_style == "maker" else None
        return Signal(
            strategy=self.name,
            timestamp=snapshot.timestamp,
            side="BUY",
            asset=snapshot.asset,
            condition_id=snapshot.condition_id,
            target_notional=candidate.notional,
            reason=(
                f"scalper_entry score={candidate.score:.4f} "
                f"bid_momentum={candidate.bid_improvement:.2%} "
                f"mid_momentum={candidate.mid_improvement:.2%} "
                f"spread={candidate.spread_pct:.2%} "
                f"imbalance={candidate.book_imbalance:.2f}"
            ),
            execution_style=self.entry_execution_style,
            limit_price=limit_price,
        )

    def _entry_notional(self, cash: float, slots: int) -> float:
        if cash <= 0 or slots <= 0:
            return 0.0
        if self.entry_notional > 0:
            return min(self.entry_notional, cash)
        return min(cash * min(max(self.capital_fraction, 0.0), 1.0) / slots, cash)

    def _current_equity(self, snapshots: Sequence[MarketSnapshot], portfolio: Portfolio) -> float:
        bids = {snapshot.asset: snapshot.book.bid for snapshot in snapshots}
        return portfolio.cash + sum(shares * bids.get(asset, 0.0) for asset, shares in portfolio.positions.items())

    def _stale_exit(self, asset: str, bid: float, target_bid: float) -> bool:
        if self.max_hold_cycles <= 0:
            return False
        if self.hold_cycles_by_asset.get(asset, 0) < self.max_hold_cycles:
            return False
        entry_bid = self.entry_bid_by_asset.get(asset, bid)
        required_move = target_bid - entry_bid
        if required_move <= 1e-9:
            progress = 1.0 if bid >= target_bid else 0.0
        else:
            progress = (bid - entry_bid) / required_move
        return progress < self.max_hold_min_progress_pct

    def _finish_cycle(self, snapshots: Sequence[MarketSnapshot]) -> None:
        for snapshot in snapshots:
            previous = self.market_state_by_asset.get(snapshot.asset)
            observations = 1 if previous is None else previous.observations + 1
            bid = snapshot.book.bid
            ask = snapshot.book.ask
            mid = (bid + ask) / 2.0 if bid > 0 and ask > 0 else 0.0
            spread_pct = (ask - bid) / ask if ask > 0 else math.inf
            self.market_state_by_asset[snapshot.asset] = _MarketState(
                bid=bid,
                ask=ask,
                mid=mid,
                spread_pct=spread_pct,
                observations=observations,
            )
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
            if previous_shares <= 1e-9:
                state = self.market_state_by_asset.get(fill.asset)
                self.entry_bid_by_asset[fill.asset] = state.bid if state is not None else fill.price
                self.hold_cycles_by_asset[fill.asset] = 0
        if fill.side == "SELL":
            previous_shares = self.position_shares_by_asset.get(fill.asset, 0.0)
            if fill.status == "PARTIAL" and previous_shares > fill.shares + 1e-9:
                self.position_shares_by_asset[fill.asset] = previous_shares - fill.shares
                return
            self.position_shares_by_asset.pop(fill.asset, None)
            self.avg_cost_by_asset.pop(fill.asset, None)
            self.entry_bid_by_asset.pop(fill.asset, None)
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

    @staticmethod
    def _relative_change(current: float, previous: float) -> float:
        if previous <= 0:
            return 0.0
        return (current - previous) / previous


class SpreadCaptureMakerStrategy(MomentumScalperPaperStrategy):
    """Passive spread-capture strategy that uses the queue-aware maker fill proxy."""

    def __init__(self, **kwargs):
        kwargs.setdefault("entry_execution_style", "maker")
        kwargs.setdefault("maker_exit", True)
        kwargs.setdefault("take_profit_pct", 0.02)
        kwargs.setdefault("stop_loss_pct", 0.04)
        kwargs.setdefault("capital_fraction", 0.25)
        kwargs.setdefault("min_spread_pct", 0.02)
        kwargs.setdefault("max_spread_pct", 0.30)
        kwargs.setdefault("max_entry_impact_pct", 0.0)
        kwargs.setdefault("min_book_imbalance", -0.50)
        kwargs.setdefault("min_momentum_observations", 2)
        kwargs.setdefault("min_bid_improvement_pct", 0.0)
        kwargs.setdefault("min_mid_improvement_pct", 0.0)
        kwargs.setdefault("max_positions", 1)
        kwargs.setdefault("max_entries_per_cycle", 1)
        kwargs.setdefault("max_hold_cycles", 12)
        kwargs.setdefault("name", "paper_goal_spread_capture_maker")
        super().__init__(**kwargs)


class MakerRebateRotationStrategy(SpreadCaptureMakerStrategy):
    """Passive maker rotation scored by round-trip spread plus maker rebate edge."""

    def __init__(
        self,
        min_round_trip_edge_pct: float = 0.004,
        min_maker_rebate_pct: float = 0.0,
        min_touch_depth_notional: float = 25.0,
        **kwargs,
    ):
        kwargs.setdefault("entry_execution_style", "maker")
        kwargs.setdefault("maker_exit", True)
        kwargs.setdefault("take_profit_pct", 0.004)
        kwargs.setdefault("stop_loss_pct", 0.06)
        kwargs.setdefault("capital_fraction", 0.20)
        kwargs.setdefault("min_spread_pct", 0.0)
        kwargs.setdefault("max_spread_pct", 0.30)
        kwargs.setdefault("max_entry_impact_pct", 0.0)
        kwargs.setdefault("min_book_imbalance", -1.0)
        kwargs.setdefault("min_momentum_observations", 1)
        kwargs.setdefault("min_bid_improvement_pct", 0.0)
        kwargs.setdefault("min_mid_improvement_pct", 0.0)
        kwargs.setdefault("max_positions", 2)
        kwargs.setdefault("max_entries_per_cycle", 1)
        kwargs.setdefault("max_hold_cycles", 10)
        kwargs.setdefault("max_hold_min_progress_pct", 0.0)
        kwargs.setdefault("name", "paper_goal_maker_rebate_rotation")
        super().__init__(**kwargs)
        self.min_round_trip_edge_pct = min_round_trip_edge_pct
        self.min_maker_rebate_pct = min_maker_rebate_pct
        self.min_touch_depth_notional = min_touch_depth_notional

    def _entry_candidate(
        self,
        snapshot: MarketSnapshot,
        target_notional: float,
        unavailable: set,
        rules_by_asset: Optional[Dict[str, object]] = None,
    ) -> Optional[_EntryCandidate]:
        if snapshot.asset in unavailable:
            self._add_diagnostic(snapshot, "asset_unavailable")
            return None
        if self.cooldowns_by_asset.get(snapshot.asset, 0) > 0:
            self._add_diagnostic(snapshot, "cooldown_active")
            return None
        bid = snapshot.book.bid
        ask = snapshot.book.ask
        if bid <= 0 or ask <= 0:
            self._add_diagnostic(snapshot, "missing_bid_or_ask")
            return None
        if self.min_bid_price is not None and bid < self.min_bid_price:
            self._add_diagnostic(snapshot, "bid_below_min_price")
            return None
        if self.max_bid_price is not None and bid > self.max_bid_price:
            self._add_diagnostic(snapshot, "bid_above_max_price")
            return None
        spread_pct = (ask - bid) / ask
        if spread_pct > self.max_spread_pct:
            self._add_diagnostic(snapshot, "spread_too_wide", details={"spread_pct": spread_pct})
            return None
        if spread_pct < self.min_spread_pct:
            self._add_diagnostic(snapshot, "spread_too_tight", details={"spread_pct": spread_pct})
            return None
        bid_touch_notional = sum(level.price * level.size for level in snapshot.book.bids if level.price >= bid)
        ask_touch_notional = sum(level.price * level.size for level in snapshot.book.asks if level.price <= ask)
        if bid_touch_notional < self.min_touch_depth_notional:
            self._add_diagnostic(
                snapshot,
                "bid_touch_depth_too_thin",
                details={"bid_touch_notional": bid_touch_notional},
            )
            return None
        if ask_touch_notional < self.min_touch_depth_notional:
            self._add_diagnostic(
                snapshot,
                "ask_touch_depth_too_thin",
                details={"ask_touch_notional": ask_touch_notional},
            )
            return None
        _, _, book_imbalance = book_depth_imbalance(snapshot.book, self.depth_window_pct)
        if book_imbalance < self.min_book_imbalance:
            self._add_diagnostic(snapshot, "book_imbalance_too_weak", details={"book_imbalance": book_imbalance})
            return None

        rules = (rules_by_asset or {}).get(snapshot.asset)
        fee_model = getattr(rules, "fee_model", None)
        fee_per_share = getattr(fee_model, "fee_per_share", None)
        entry_fee = fee_per_share(bid, taker=False) if callable(fee_per_share) else 0.0
        exit_fee = fee_per_share(ask, taker=False) if callable(fee_per_share) else 0.0
        entry_rebate = max(0.0, -entry_fee)
        exit_rebate = max(0.0, -exit_fee)
        maker_rebate_pct = entry_rebate / bid if bid > 0 else 0.0
        round_trip_edge_pct = ((ask - bid) + entry_rebate + exit_rebate) / bid
        if maker_rebate_pct < self.min_maker_rebate_pct:
            self._add_diagnostic(
                snapshot,
                "maker_rebate_too_small",
                details={"maker_rebate_pct": maker_rebate_pct},
            )
            return None
        if round_trip_edge_pct < self.min_round_trip_edge_pct:
            self._add_diagnostic(
                snapshot,
                "round_trip_edge_too_small",
                details={"round_trip_edge_pct": round_trip_edge_pct},
            )
            return None
        score = round_trip_edge_pct + max(book_imbalance, -1.0) * 0.01
        return _EntryCandidate(
            snapshot=snapshot,
            notional=target_notional,
            score=score,
            bid_improvement=maker_rebate_pct,
            mid_improvement=round_trip_edge_pct,
            spread_pct=spread_pct,
            book_imbalance=book_imbalance,
        )

    def _entry_signal(self, candidate: _EntryCandidate) -> Signal:
        snapshot = candidate.snapshot
        return Signal(
            strategy=self.name,
            timestamp=snapshot.timestamp,
            side="BUY",
            asset=snapshot.asset,
            condition_id=snapshot.condition_id,
            target_notional=candidate.notional,
            reason=(
                f"maker_rebate_rotation_entry score={candidate.score:.4f} "
                f"rebate={candidate.bid_improvement:.2%} "
                f"round_trip_edge={candidate.mid_improvement:.2%} "
                f"spread={candidate.spread_pct:.2%} "
                f"imbalance={candidate.book_imbalance:.2f}"
            ),
            execution_style="maker",
            limit_price=snapshot.book.bid,
        )
