from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Set

from ....models import MarketSnapshot, PaperFill, Portfolio, Signal, StrategyDiagnostic
from ..base import PaperStrategy


@dataclass(frozen=True)
class _BasketCandidate:
    condition_id: str
    snapshots: Sequence[MarketSnapshot]
    total_notional: float
    set_count: float
    cost_per_set: float
    bid_value_per_set: float
    settlement_roi: float
    mark_roi: float
    score: float


class OutcomeBasketArbPaperStrategy(PaperStrategy):
    """Buy a complete outcome set when the ask basket has a settlement edge."""

    def __init__(
        self,
        initial_cash: float,
        portfolio_target_roi: float = 0.10,
        take_profit_pct: float = 0.04,
        stop_loss_pct: float = 0.08,
        entry_notional: float = 250.0,
        capital_fraction: float = 0.25,
        min_entry_notional: float = 5.0,
        min_settlement_roi: float = 0.02,
        min_mark_roi: float = -0.08,
        max_outcomes: int = 2,
        max_positions: int = 2,
        max_entries_per_cycle: int = 1,
        max_hold_cycles: int = 72,
        cooldown_cycles_after_sell: int = 12,
        name: str = "paper_goal_outcome_basket_arb",
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
        self.min_settlement_roi = min_settlement_roi
        self.min_mark_roi = min_mark_roi
        self.max_outcomes = max(2, int(max_outcomes))
        self.max_positions = max(1, int(max_positions))
        self.max_entries_per_cycle = max(1, int(max_entries_per_cycle))
        self.max_hold_cycles = max(0, int(max_hold_cycles))
        self.cooldown_cycles_after_sell = max(0, int(cooldown_cycles_after_sell))
        self.diagnostic_limit = diagnostic_limit

        self.avg_cost_by_asset: Dict[str, float] = {}
        self.position_shares_by_asset: Dict[str, float] = {}
        self.condition_by_asset: Dict[str, str] = {}
        self.assets_by_condition: Dict[str, Set[str]] = {}
        self.pending_assets: Dict[str, str] = {}
        self.pending_conditions: Set[str] = set()
        self.hold_cycles_by_condition: Dict[str, int] = {}
        self.cooldowns_by_condition: Dict[str, int] = {}
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
        exits = self._exit_signals(snapshots, portfolio, target_equity)
        if exits:
            self._finish_cycle(portfolio)
            return exits
        if self.target_reached:
            self._add_cycle_diagnostic(snapshots, "target_reached_waiting_flat")
            self._finish_cycle(portfolio)
            return []

        active_conditions = self._active_conditions(portfolio)
        if len(active_conditions) + len(self.pending_conditions) >= self.max_positions:
            self._add_cycle_diagnostic(snapshots, "condition_budget_full")
            self._finish_cycle(portfolio)
            return []
        max_total_notional = self._entry_notional(portfolio.cash)
        if max_total_notional < self.min_entry_notional:
            self._add_cycle_diagnostic(snapshots, "no_entry_notional")
            self._finish_cycle(portfolio)
            return []
        candidates = self._entry_candidates(snapshots, portfolio.cash, max_total_notional, active_conditions)
        if not candidates:
            self._finish_cycle(portfolio)
            return []
        selected = sorted(candidates, key=lambda item: item.score, reverse=True)[: self.max_entries_per_cycle]
        signals: List[Signal] = []
        for candidate in selected:
            signals.extend(self._entry_signals(candidate))
            self.pending_conditions.add(candidate.condition_id)
            self.assets_by_condition[candidate.condition_id] = {snapshot.asset for snapshot in candidate.snapshots}
            for snapshot in candidate.snapshots:
                self.condition_by_asset[snapshot.asset] = candidate.condition_id
                self.pending_assets[snapshot.asset] = "BUY"
        self._finish_cycle(portfolio)
        return signals

    def pop_diagnostics(self) -> List[StrategyDiagnostic]:
        diagnostics = self._diagnostics
        self._diagnostics = []
        return diagnostics

    def _exit_signals(
        self,
        snapshots: Sequence[MarketSnapshot],
        portfolio: Portfolio,
        target_equity: float,
    ) -> List[Signal]:
        snapshots_by_asset = {snapshot.asset: snapshot for snapshot in snapshots}
        signals: List[Signal] = []
        for condition_id in sorted(self._active_conditions(portfolio)):
            assets = sorted(self.assets_by_condition.get(condition_id, ()))
            positioned_assets = [asset for asset in assets if portfolio.positions.get(asset, 0.0) > 1e-9]
            if not positioned_assets or any(asset not in snapshots_by_asset for asset in positioned_assets):
                continue
            if any(self.pending_assets.get(asset) == "SELL" for asset in positioned_assets):
                continue
            cost = sum(
                self.avg_cost_by_asset.get(asset, 0.0) * portfolio.positions.get(asset, 0.0)
                for asset in positioned_assets
            )
            bid_value = sum(
                snapshots_by_asset[asset].book.bid * portfolio.positions.get(asset, 0.0)
                for asset in positioned_assets
            )
            if cost <= 1e-9:
                continue
            take_profit = bid_value >= cost * (1.0 + self.take_profit_pct)
            stop_loss = bid_value <= cost * (1.0 - self.stop_loss_pct)
            stale = self.max_hold_cycles > 0 and self.hold_cycles_by_condition.get(condition_id, 0) >= self.max_hold_cycles
            portfolio_target = self.target_reached and portfolio.cash + bid_value >= target_equity
            if not (take_profit or stop_loss or stale or portfolio_target):
                continue
            reason = (
                "portfolio_target_reached"
                if portfolio_target
                else "basket_take_profit"
                if take_profit
                else "basket_stop_loss"
                if stop_loss
                else "basket_max_hold_exit"
            )
            for asset in positioned_assets:
                snapshot = snapshots_by_asset[asset]
                shares = portfolio.positions.get(asset, 0.0)
                self.pending_assets[asset] = "SELL"
                signals.append(
                    Signal(
                        strategy=self.name,
                        timestamp=snapshot.timestamp,
                        side="SELL",
                        asset=asset,
                        condition_id=condition_id,
                        target_notional=shares * snapshot.book.bid,
                        reason=reason,
                        execution_style="taker",
                    )
                )
            if stale and self.cooldown_cycles_after_sell > 0:
                self.cooldowns_by_condition[condition_id] = self.cooldown_cycles_after_sell
            return signals
        return signals

    def _entry_candidates(
        self,
        snapshots: Sequence[MarketSnapshot],
        cash: float,
        max_total_notional: float,
        active_conditions: Set[str],
    ) -> List[_BasketCandidate]:
        grouped: Dict[str, List[MarketSnapshot]] = {}
        for snapshot in snapshots:
            if not snapshot.condition_id:
                self._add_diagnostic(snapshot, "missing_condition_id")
                continue
            grouped.setdefault(snapshot.condition_id, []).append(snapshot)

        candidates: List[_BasketCandidate] = []
        for condition_id, group in grouped.items():
            group = sorted(group, key=lambda item: item.outcome_index)
            if condition_id in active_conditions or condition_id in self.pending_conditions:
                for snapshot in group:
                    self._add_diagnostic(snapshot, "condition_unavailable")
                continue
            if self.cooldowns_by_condition.get(condition_id, 0) > 0:
                for snapshot in group:
                    self._add_diagnostic(snapshot, "condition_cooldown_active")
                continue
            if len(group) != self.max_outcomes:
                for snapshot in group:
                    self._add_diagnostic(snapshot, "outcome_count_mismatch", details={"outcomes": len(group)})
                continue
            if any(snapshot.book.ask <= 0 or snapshot.book.bid <= 0 for snapshot in group):
                for snapshot in group:
                    self._add_diagnostic(snapshot, "missing_bid_or_ask")
                continue
            cost_per_set = sum(snapshot.book.ask for snapshot in group)
            bid_value_per_set = sum(snapshot.book.bid for snapshot in group)
            if cost_per_set <= 0:
                continue
            settlement_roi = 1.0 / cost_per_set - 1.0
            mark_roi = bid_value_per_set / cost_per_set - 1.0
            if settlement_roi < self.min_settlement_roi:
                for snapshot in group:
                    self._add_diagnostic(snapshot, "settlement_edge_too_small", details={"settlement_roi": settlement_roi})
                continue
            if mark_roi < self.min_mark_roi:
                for snapshot in group:
                    self._add_diagnostic(snapshot, "mark_value_too_weak", details={"mark_roi": mark_roi})
                continue
            max_sets_by_depth = min(snapshot.book.asks[0].size for snapshot in group)
            max_sets_by_cash = min(max_total_notional, cash) / cost_per_set
            set_count = min(max_sets_by_depth, max_sets_by_cash)
            total_notional = set_count * cost_per_set
            if total_notional < self.min_entry_notional or set_count <= 1e-9:
                for snapshot in group:
                    self._add_diagnostic(snapshot, "insufficient_basket_size", details={"total_notional": total_notional})
                continue
            score = settlement_roi + max(mark_roi, -0.50) * 0.25
            candidates.append(
                _BasketCandidate(
                    condition_id=condition_id,
                    snapshots=group,
                    total_notional=total_notional,
                    set_count=set_count,
                    cost_per_set=cost_per_set,
                    bid_value_per_set=bid_value_per_set,
                    settlement_roi=settlement_roi,
                    mark_roi=mark_roi,
                    score=score,
                )
            )
        return candidates

    def _entry_signals(self, candidate: _BasketCandidate) -> List[Signal]:
        signals: List[Signal] = []
        for snapshot in candidate.snapshots:
            signals.append(
                Signal(
                    strategy=self.name,
                    timestamp=snapshot.timestamp,
                    side="BUY",
                    asset=snapshot.asset,
                    condition_id=candidate.condition_id,
                    target_notional=candidate.set_count * snapshot.book.ask,
                    reason=(
                        f"basket_settlement_edge settlement_roi={candidate.settlement_roi:.2%} "
                        f"mark_roi={candidate.mark_roi:.2%} cost_per_set={candidate.cost_per_set:.4f}"
                    ),
                    execution_style="taker",
                )
            )
        return signals

    def _entry_notional(self, cash: float) -> float:
        if self.entry_notional > 0:
            return min(self.entry_notional, cash)
        return min(cash * min(max(self.capital_fraction, 0.0), 1.0), cash)

    def _current_equity(self, snapshots: Sequence[MarketSnapshot], portfolio: Portfolio) -> float:
        bids = {snapshot.asset: snapshot.book.bid for snapshot in snapshots}
        return portfolio.cash + sum(shares * bids.get(asset, 0.0) for asset, shares in portfolio.positions.items())

    def _active_conditions(self, portfolio: Portfolio) -> Set[str]:
        conditions = set()
        for asset, shares in portfolio.positions.items():
            if shares <= 1e-9:
                continue
            condition_id = self.condition_by_asset.get(asset)
            if condition_id:
                conditions.add(condition_id)
        return conditions

    def _finish_cycle(self, portfolio: Portfolio) -> None:
        for condition_id in self._active_conditions(portfolio):
            if any(self.pending_assets.get(asset) == "SELL" for asset in self.assets_by_condition.get(condition_id, ())):
                continue
            self.hold_cycles_by_condition[condition_id] = self.hold_cycles_by_condition.get(condition_id, 0) + 1
        self._decrement_cooldowns()

    def on_fill(self, fill: PaperFill) -> None:
        self.pending_assets.pop(fill.asset, None)
        condition_id = fill.order_id and self.condition_by_asset.get(fill.asset, fill.asset)
        if condition_id in self.pending_conditions:
            pending_assets = self.assets_by_condition.get(condition_id, set())
            if not any(asset in self.pending_assets for asset in pending_assets):
                self.pending_conditions.discard(condition_id)
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
        elif fill.side == "SELL":
            previous_shares = self.position_shares_by_asset.get(fill.asset, 0.0)
            if fill.status == "PARTIAL" and previous_shares > fill.shares + 1e-9:
                self.position_shares_by_asset[fill.asset] = previous_shares - fill.shares
                return
            condition_id = self.condition_by_asset.get(fill.asset)
            self.position_shares_by_asset.pop(fill.asset, None)
            self.avg_cost_by_asset.pop(fill.asset, None)
            if condition_id and not any(
                asset in self.position_shares_by_asset
                for asset in self.assets_by_condition.get(condition_id, ())
            ):
                self.assets_by_condition.pop(condition_id, None)
                self.hold_cycles_by_condition.pop(condition_id, None)

    def _decrement_cooldowns(self) -> None:
        expired = []
        for condition_id, cycles in self.cooldowns_by_condition.items():
            next_cycles = cycles - 1
            if next_cycles <= 0:
                expired.append(condition_id)
            else:
                self.cooldowns_by_condition[condition_id] = next_cycles
        for condition_id in expired:
            self.cooldowns_by_condition.pop(condition_id, None)

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
