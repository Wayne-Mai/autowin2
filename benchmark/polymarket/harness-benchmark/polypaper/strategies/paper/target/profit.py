from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Dict, List, Optional, Sequence

from ....models import MarketSnapshot, PaperFill, Portfolio, Signal, StrategyDiagnostic
from ....opportunity import (
    TargetOpportunity,
    required_exit_price_for_net_proceeds,
    score_adaptive_target_opportunity,
    score_target_opportunity,
    target_entry_notional,
)
from ..base import PaperStrategy


@dataclass(frozen=True)
class _MarketState:
    bid: float
    ask: float
    mid: float
    spread_pct: float
    observations: int


class TargetProfitPaperStrategy(PaperStrategy):
    def __init__(
        self,
        initial_cash: float,
        portfolio_target_roi: float = 0.10,
        take_profit_pct: float = 0.10,
        allow_take_profit_before_target: bool = False,
        stop_loss_pct: float = 0.03,
        entry_notional: float = 0.0,
        capital_fraction: float = 0.95,
        adaptive_entry_sizing: bool = False,
        min_entry_notional: float = 1.0,
        max_spread_pct: float = 0.05,
        max_entry_impact_pct: float = 0.05,
        max_exit_price: float = 0.99,
        min_book_imbalance: float = 0.05,
        depth_window_pct: float = 0.03,
        imbalance_weight: float = 0.10,
        min_bid_price: Optional[float] = None,
        max_bid_price: Optional[float] = None,
        max_entry_mark_to_bid_loss_pct: Optional[float] = None,
        max_required_exit_distance_pct: Optional[float] = None,
        required_exit_distance_weight: float = 0.0,
        min_score: Optional[float] = None,
        min_momentum_observations: int = 2,
        min_bid_improvement_pct: float = 0.001,
        min_mid_improvement_pct: float = 0.001,
        max_spread_widen_pct: float = 0.01,
        cooldown_cycles_after_sell: int = 3,
        max_hold_cycles: int = 0,
        max_hold_min_progress_pct: float = 0.0,
        max_hold_cooldown_cycles: int = 0,
        max_positions: int = 1,
        max_entries_per_cycle: int = 1,
        diversify_by: str = "none",
        max_positions_per_group: int = 0,
        allowed_assets: Optional[Sequence[str]] = None,
        watchlist_size: int = 0,
        history_change_weight: float = 0.0,
        entry_execution_style: str = "taker",
        name: str = "paper_target_profit_10pct",
        diagnostic_limit: int = 50,
    ):
        self.name = name
        self.initial_cash = initial_cash
        self.portfolio_target_roi = portfolio_target_roi
        self.take_profit_pct = take_profit_pct
        self.allow_take_profit_before_target = allow_take_profit_before_target
        self.stop_loss_pct = stop_loss_pct
        self.entry_notional = entry_notional
        self.capital_fraction = capital_fraction
        self.adaptive_entry_sizing = adaptive_entry_sizing
        self.min_entry_notional = min_entry_notional
        self.max_spread_pct = max_spread_pct
        self.max_entry_impact_pct = max_entry_impact_pct
        self.max_exit_price = max_exit_price
        self.min_book_imbalance = min_book_imbalance
        self.depth_window_pct = depth_window_pct
        self.imbalance_weight = imbalance_weight
        self.min_bid_price = min_bid_price
        self.max_bid_price = max_bid_price
        self.max_entry_mark_to_bid_loss_pct = (
            stop_loss_pct if max_entry_mark_to_bid_loss_pct is None else max_entry_mark_to_bid_loss_pct
        )
        self.max_required_exit_distance_pct = max_required_exit_distance_pct
        self.required_exit_distance_weight = required_exit_distance_weight
        self.min_score = min_score
        self.min_momentum_observations = min_momentum_observations
        self.min_bid_improvement_pct = min_bid_improvement_pct
        self.min_mid_improvement_pct = min_mid_improvement_pct
        self.max_spread_widen_pct = max_spread_widen_pct
        self.cooldown_cycles_after_sell = cooldown_cycles_after_sell
        self.max_hold_cycles = max_hold_cycles
        self.max_hold_min_progress_pct = max_hold_min_progress_pct
        self.max_hold_cooldown_cycles = max_hold_cooldown_cycles
        self.max_positions = max_positions
        self.max_entries_per_cycle = max_entries_per_cycle
        self.diversify_by = diversify_by
        self.max_positions_per_group = max_positions_per_group
        self.allowed_assets = set(allowed_assets) if allowed_assets is not None else None
        self.watchlist_size = watchlist_size
        self.history_change_weight = history_change_weight
        self.entry_execution_style = entry_execution_style
        self.diagnostic_limit = diagnostic_limit
        self.avg_cost_by_asset: Dict[str, float] = {}
        self.position_shares_by_asset: Dict[str, float] = {}
        self.entry_bid_by_asset: Dict[str, float] = {}
        self.hold_cycles_by_asset: Dict[str, int] = {}
        self.group_by_asset: Dict[str, str] = {}
        self.pending_assets: Dict[str, str] = {}
        self.market_state_by_asset: Dict[str, _MarketState] = {}
        self.watchlist_assets: List[str] = []
        self.cooldowns_by_asset: Dict[str, int] = {}
        self._diagnostics: List[StrategyDiagnostic] = []
        self.global_cooldown_cycles = 0
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
        for snapshot in snapshots:
            signal = self._exit_signal(
                snapshot,
                portfolio,
                target_equity,
                current_equity,
                rules_by_asset=rules_by_asset,
            )
            if signal is not None:
                self._finish_cycle(snapshots)
                return [signal]

        if self.target_reached:
            self._add_cycle_diagnostic(snapshots, "target_reached")
            self._finish_cycle(snapshots)
            return []
        unavailable_assets = set(portfolio.positions) | set(self.pending_assets)
        if len(unavailable_assets) >= self.max_positions:
            self._add_cycle_diagnostic(snapshots, "position_budget_full")
            self._finish_cycle(snapshots)
            return []
        group_counts = self._group_counts(snapshots, unavailable_assets)
        notional = self._entry_notional(portfolio.cash)
        if notional < self.min_entry_notional:
            self._add_cycle_diagnostic(snapshots, "no_entry_notional")
            self._finish_cycle(snapshots)
            return []
        viable: List[TargetOpportunity] = []
        for snapshot in snapshots:
            if snapshot.asset in unavailable_assets:
                self._add_diagnostic(snapshot, "asset_unavailable")
                continue
            if not self._asset_allowed(snapshot.asset):
                self._add_diagnostic(snapshot, "asset_not_allowed")
                continue
            if not self._group_allows(snapshot, group_counts):
                self._add_diagnostic(snapshot, "group_position_budget_full")
                continue
            if self._cooldown_active(snapshot.asset):
                self._add_diagnostic(snapshot, "cooldown_active")
                continue
            momentum_ok, momentum_reason, momentum_details = self._momentum_status(snapshot)
            if not momentum_ok:
                self._add_diagnostic(snapshot, momentum_reason, details=momentum_details)
                continue
            candidate = self._score_snapshot(snapshot, portfolio.cash, notional, rules_by_asset=rules_by_asset)
            if candidate.viable:
                viable.append(candidate)
            else:
                self._add_opportunity_diagnostic(candidate)
        if not viable:
            self._finish_cycle(snapshots)
            return []
        remaining_slots = self.max_positions - len(unavailable_assets)
        selected = self._select_entries(viable, portfolio.cash, group_counts, remaining_slots)
        selected_assets = {candidate.asset for candidate in selected}
        for candidate in viable:
            if candidate.asset not in selected_assets:
                self._add_opportunity_diagnostic(candidate, reason="viable_not_selected")
        if not selected:
            self._finish_cycle(snapshots)
            return []
        for candidate in selected:
            self.pending_assets[candidate.asset] = "BUY"
            self.group_by_asset[candidate.asset] = self._group_key_for_opportunity(candidate)
        self._finish_cycle(snapshots)
        return [self._entry_signal(candidate) for candidate in selected]

    def pop_diagnostics(self) -> List[StrategyDiagnostic]:
        diagnostics = self._diagnostics
        self._diagnostics = []
        return diagnostics

    def watched_assets(self) -> Sequence[str]:
        if self.watchlist_size <= 0:
            return ()
        return tuple(self.watchlist_assets[-self.watchlist_size :])

    def _exit_signal(
        self,
        snapshot: MarketSnapshot,
        portfolio: Portfolio,
        target_equity: float,
        current_equity: float,
        rules_by_asset: Optional[Dict[str, object]] = None,
    ) -> Optional[Signal]:
        position = portfolio.positions.get(snapshot.asset, 0.0)
        if current_equity >= target_equity:
            self.target_reached = True

        if position > 0:
            avg_cost = self.avg_cost_by_asset.get(snapshot.asset)
            stop_loss = avg_cost is not None and snapshot.book.bid <= avg_cost * (1.0 - self.stop_loss_pct)
            rules = (rules_by_asset or {}).get(snapshot.asset)
            fee_model = getattr(rules, "fee_model", None)
            exit_bid = self._exit_bid_for_target(avg_cost, position, portfolio.cash, target_equity, fee_model)
            max_hold_exit = self._max_hold_exit(snapshot.asset, snapshot.book.bid, exit_bid)
            should_exit = self.target_reached or snapshot.book.bid >= exit_bid or stop_loss or max_hold_exit
            if should_exit and self.pending_assets.get(snapshot.asset) != "SELL":
                self.pending_assets[snapshot.asset] = "SELL"
                execution_style = "taker"
                limit_price = None
                exit_price = snapshot.book.bid
                if max_hold_exit and self.entry_execution_style == "maker" and snapshot.book.ask > 0:
                    execution_style = "maker"
                    limit_price = snapshot.book.ask
                    exit_price = limit_price
                if max_hold_exit and self.max_hold_cooldown_cycles > 0:
                    self.cooldowns_by_asset[snapshot.asset] = max(
                        self.cooldowns_by_asset.get(snapshot.asset, 0),
                        self.max_hold_cooldown_cycles,
                    )
                return Signal(
                    strategy=self.name,
                    timestamp=snapshot.timestamp,
                    side="SELL",
                    asset=snapshot.asset,
                    condition_id=snapshot.condition_id,
                    target_notional=position * exit_price,
                    reason=(
                        "portfolio_target_reached"
                        if self.target_reached
                        else "stop_loss"
                        if stop_loss
                        else "max_hold_exit"
                        if max_hold_exit
                        else "take_profit_reinvest"
                        if self.allow_take_profit_before_target
                        else f"exit_at_{self.portfolio_target_roi:.2%}_portfolio_target"
                    ),
                    execution_style=execution_style,
                    limit_price=limit_price,
                )
        return None

    @staticmethod
    def _current_equity(snapshots: Sequence[MarketSnapshot], portfolio: Portfolio) -> float:
        bids_by_asset = {snapshot.asset: snapshot.book.bid for snapshot in snapshots}
        return portfolio.cash + sum(
            shares * bids_by_asset.get(asset, 0.0)
            for asset, shares in portfolio.positions.items()
        )

    def _group_counts(self, snapshots: Sequence[MarketSnapshot], assets: set) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        if self.max_positions_per_group <= 0 or self.diversify_by == "none":
            return counts
        snapshots_by_asset = {snapshot.asset: snapshot for snapshot in snapshots}
        for asset in assets:
            group = self.group_by_asset.get(asset)
            if group is None and asset in snapshots_by_asset:
                group = self._group_key(snapshots_by_asset[asset])
            if group:
                counts[group] = counts.get(group, 0) + 1
        return counts

    def _asset_allowed(self, asset: str) -> bool:
        return self.allowed_assets is None or asset in self.allowed_assets

    def _group_allows(self, snapshot: MarketSnapshot, group_counts: Dict[str, int]) -> bool:
        if self.max_positions_per_group <= 0 or self.diversify_by == "none":
            return True
        group = self._group_key(snapshot)
        if not group:
            return True
        return group_counts.get(group, 0) < self.max_positions_per_group

    def _opportunity_group_allows(
        self,
        opportunity: TargetOpportunity,
        group_counts: Dict[str, int],
    ) -> bool:
        if self.max_positions_per_group <= 0 or self.diversify_by == "none":
            return True
        group = self._group_key_for_opportunity(opportunity)
        if not group:
            return True
        return group_counts.get(group, 0) < self.max_positions_per_group

    def _select_entries(
        self,
        viable: Sequence[TargetOpportunity],
        cash: float,
        group_counts: Dict[str, int],
        remaining_slots: int,
    ) -> List[TargetOpportunity]:
        if remaining_slots <= 0:
            return []
        limit = min(remaining_slots, max(1, self.max_entries_per_cycle))
        available_cash = cash
        selected: List[TargetOpportunity] = []
        mutable_group_counts = dict(group_counts)
        for opportunity in sorted(viable, key=lambda candidate: candidate.score, reverse=True):
            if len(selected) >= limit:
                break
            if not self._opportunity_group_allows(opportunity, mutable_group_counts):
                self._add_opportunity_diagnostic(opportunity, reason="group_position_budget_full")
                continue
            required_cash = opportunity.target_notional + opportunity.estimated_entry_fee
            if required_cash > available_cash + 1e-9:
                self._add_opportunity_diagnostic(opportunity, reason="cash_reserved_by_selected_entries")
                continue
            selected.append(opportunity)
            available_cash -= required_cash
            group = self._group_key_for_opportunity(opportunity)
            if group:
                mutable_group_counts[group] = mutable_group_counts.get(group, 0) + 1
        return selected

    def _group_key(self, snapshot: MarketSnapshot) -> str:
        if self.diversify_by == "condition":
            return snapshot.condition_id
        if self.diversify_by == "slug":
            return snapshot.slug or snapshot.condition_id
        if self.diversify_by == "title":
            return self._normalize_group_text(snapshot.title or snapshot.slug or snapshot.condition_id)
        if self.diversify_by == "title_prefix":
            raw = snapshot.title or snapshot.slug or snapshot.condition_id
            for separator in (" - ", " – ", " — "):
                if separator in raw:
                    raw = raw.split(separator, 1)[0]
                    break
            return self._normalize_group_text(raw)
        return snapshot.asset

    def _group_key_for_opportunity(self, opportunity: TargetOpportunity) -> str:
        if self.diversify_by == "condition":
            return opportunity.condition_id
        if self.diversify_by == "slug":
            return opportunity.slug or opportunity.condition_id
        if self.diversify_by in {"title", "title_prefix"}:
            raw = opportunity.title or opportunity.condition_id
            if self.diversify_by == "title_prefix":
                for separator in (" - ", " – ", " — "):
                    if separator in raw:
                        raw = raw.split(separator, 1)[0]
                        break
            return self._normalize_group_text(raw)
        return opportunity.asset

    @staticmethod
    def _normalize_group_text(value: str) -> str:
        return " ".join(value.lower().replace("_", " ").replace("-", " ").split())

    def _entry_notional(self, cash: float) -> float:
        return target_entry_notional(
            initial_cash=self.initial_cash,
            current_cash=cash,
            portfolio_target_roi=self.portfolio_target_roi,
            take_profit_pct=self.take_profit_pct,
            entry_notional=self.entry_notional,
            capital_fraction=self.capital_fraction,
        )

    def _score_snapshot(
        self,
        snapshot: MarketSnapshot,
        cash: float,
        notional: float,
        rules_by_asset: Optional[Dict[str, object]] = None,
    ) -> TargetOpportunity:
        rules = (rules_by_asset or {}).get(snapshot.asset)
        fee_model = getattr(rules, "fee_model", None)
        scorer = score_adaptive_target_opportunity if self.adaptive_entry_sizing else score_target_opportunity
        kwargs = {
            "snapshot": snapshot,
            "initial_cash": self.initial_cash,
            "current_cash": cash,
            "portfolio_target_roi": self.portfolio_target_roi,
            "take_profit_pct": self.take_profit_pct,
            "allow_take_profit_before_target": self.allow_take_profit_before_target,
            "max_spread_pct": self.max_spread_pct,
            "max_entry_impact_pct": self.max_entry_impact_pct,
            "max_exit_price": self.max_exit_price,
            "min_book_imbalance": self.min_book_imbalance,
            "depth_window_pct": self.depth_window_pct,
            "imbalance_weight": self.imbalance_weight,
            "min_bid_price": self.min_bid_price,
            "max_bid_price": self.max_bid_price,
            "max_entry_mark_to_bid_loss_pct": self.max_entry_mark_to_bid_loss_pct,
            "max_required_exit_distance_pct": self.max_required_exit_distance_pct,
            "required_exit_distance_weight": self.required_exit_distance_weight,
            "min_score": self.min_score,
            "fee_model": fee_model,
            "entry_price_mode": "maker_bid" if self.entry_execution_style == "maker" else "taker",
        }
        if self.adaptive_entry_sizing:
            kwargs["max_target_notional"] = notional
            kwargs["min_target_notional"] = self.min_entry_notional
        else:
            kwargs["target_notional"] = notional
        opportunity = scorer(**kwargs)
        history_change = getattr(snapshot, "history_change_pct", None)
        if history_change is None or self.history_change_weight == 0.0:
            return opportunity
        return replace(opportunity, score=opportunity.score + self.history_change_weight * history_change)

    def _entry_signal(self, opportunity: TargetOpportunity) -> Signal:
        history_part = (
            f" history={opportunity.history_change_pct:.2%}"
            if opportunity.history_change_pct is not None
            else ""
        )
        return Signal(
            strategy=self.name,
            timestamp=opportunity.timestamp,
            side="BUY",
            asset=opportunity.asset,
            condition_id=opportunity.condition_id,
            target_notional=opportunity.target_notional,
            reason=(
                f"target_opportunity_momentum score={opportunity.score:.4f} "
                f"exit_bid={opportunity.required_exit_bid:.4f} "
                f"exit_distance={opportunity.required_exit_distance_pct:.2%} "
                f"imbalance={opportunity.book_imbalance:.2f} "
                f"mark_loss={opportunity.entry_mark_to_bid_loss_pct:.2%}"
                f"{history_part}"
            ),
            execution_style=self.entry_execution_style,
            limit_price=opportunity.bid if self.entry_execution_style == "maker" else None,
        )

    def _momentum_passes(self, snapshot: MarketSnapshot) -> bool:
        return self._momentum_status(snapshot)[0]

    def _momentum_status(self, snapshot: MarketSnapshot) -> tuple:
        if self.min_momentum_observations <= 1:
            return True, "momentum_disabled", {}
        previous = self.market_state_by_asset.get(snapshot.asset)
        if previous is None:
            return False, "momentum_no_previous_observation", {
                "required_observations": self.min_momentum_observations,
                "observations": 0,
            }
        if previous.observations + 1 < self.min_momentum_observations:
            return False, "momentum_insufficient_observations", {
                "required_observations": self.min_momentum_observations,
                "observations": previous.observations + 1,
            }
        current = self._market_state(snapshot, previous.observations + 1)
        bid_improvement = self._relative_change(current.bid, previous.bid)
        mid_improvement = self._relative_change(current.mid, previous.mid)
        spread_widen = current.spread_pct - previous.spread_pct
        details = {
            "observations": current.observations,
            "previous_bid": previous.bid,
            "current_bid": current.bid,
            "bid_improvement_pct": bid_improvement,
            "min_bid_improvement_pct": self.min_bid_improvement_pct,
            "previous_mid": previous.mid,
            "current_mid": current.mid,
            "mid_improvement_pct": mid_improvement,
            "min_mid_improvement_pct": self.min_mid_improvement_pct,
            "spread_widen_pct": spread_widen,
            "max_spread_widen_pct": self.max_spread_widen_pct,
        }
        if bid_improvement < self.min_bid_improvement_pct:
            return False, "momentum_bid_not_improving", details
        if mid_improvement < self.min_mid_improvement_pct:
            return False, "momentum_mid_not_improving", details
        if spread_widen > self.max_spread_widen_pct:
            return False, "momentum_spread_widened", details
        return True, "momentum_passed", details

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

    def _add_opportunity_diagnostic(
        self,
        opportunity: TargetOpportunity,
        reason: Optional[str] = None,
    ) -> None:
        if len(self._diagnostics) >= self.diagnostic_limit:
            return
        self._diagnostics.append(
            StrategyDiagnostic(
                strategy=self.name,
                timestamp=opportunity.timestamp,
                asset=opportunity.asset,
                condition_id=opportunity.condition_id,
                reason=reason or opportunity.reason,
                score=opportunity.score,
                title=opportunity.title,
                outcome=opportunity.outcome,
                details={
                    "bid": opportunity.bid,
                    "ask": opportunity.ask,
                    "target_notional": opportunity.target_notional,
                    "required_exit_bid": opportunity.required_exit_bid,
                    "required_exit_distance_pct": opportunity.required_exit_distance_pct,
                    "entry_mark_to_bid_loss_pct": opportunity.entry_mark_to_bid_loss_pct,
                    "spread_pct": opportunity.spread_pct,
                    "entry_impact_pct": opportunity.entry_impact_pct,
                    "book_imbalance": opportunity.book_imbalance,
                    "history_change_pct": opportunity.history_change_pct,
                },
            )
        )

    def _record_snapshots(self, snapshots: Sequence[MarketSnapshot]) -> None:
        for snapshot in snapshots:
            previous = self.market_state_by_asset.get(snapshot.asset)
            observations = 1 if previous is None else previous.observations + 1
            self.market_state_by_asset[snapshot.asset] = self._market_state(snapshot, observations)
            self._remember_watchlist_asset(snapshot.asset)
            if snapshot.asset in self.avg_cost_by_asset and self.pending_assets.get(snapshot.asset) != "SELL":
                self.hold_cycles_by_asset[snapshot.asset] = self.hold_cycles_by_asset.get(snapshot.asset, 0) + 1

    def _finish_cycle(self, snapshots: Sequence[MarketSnapshot]) -> None:
        self._record_snapshots(snapshots)
        self._decrement_cooldowns()

    def _remember_watchlist_asset(self, asset: str) -> None:
        if self.watchlist_size <= 0:
            return
        if asset in self.watchlist_assets:
            self.watchlist_assets.remove(asset)
        self.watchlist_assets.append(asset)
        overflow = len(self.watchlist_assets) - self.watchlist_size
        if overflow > 0:
            del self.watchlist_assets[:overflow]

    def _cooldown_active(self, asset: str) -> bool:
        return self.global_cooldown_cycles > 0 or self.cooldowns_by_asset.get(asset, 0) > 0

    def _decrement_cooldowns(self) -> None:
        if self.global_cooldown_cycles > 0:
            self.global_cooldown_cycles -= 1
        expired = []
        for asset, cycles in self.cooldowns_by_asset.items():
            next_cycles = cycles - 1
            if next_cycles <= 0:
                expired.append(asset)
            else:
                self.cooldowns_by_asset[asset] = next_cycles
        for asset in expired:
            self.cooldowns_by_asset.pop(asset, None)

    def _market_state(self, snapshot: MarketSnapshot, observations: int) -> _MarketState:
        bid = snapshot.book.bid
        ask = snapshot.book.ask
        mid = (bid + ask) / 2.0 if bid > 0 and ask > 0 else 0.0
        spread_pct = (ask - bid) / ask if ask > 0 else math.inf
        return _MarketState(bid=bid, ask=ask, mid=mid, spread_pct=spread_pct, observations=observations)

    def _max_hold_exit(self, asset: str, current_bid: float, exit_bid: float) -> bool:
        if self.max_hold_cycles <= 0 or self.hold_cycles_by_asset.get(asset, 0) < self.max_hold_cycles:
            return False
        progress = self._exit_progress(asset, current_bid, exit_bid)
        return progress < self.max_hold_min_progress_pct

    def _exit_progress(self, asset: str, current_bid: float, exit_bid: float) -> float:
        entry_bid = self.entry_bid_by_asset.get(asset)
        if entry_bid is None:
            return 0.0
        required_move = exit_bid - entry_bid
        if required_move <= 1e-9:
            return 1.0 if current_bid >= exit_bid else 0.0
        return (current_bid - entry_bid) / required_move

    @staticmethod
    def _relative_change(current: float, previous: float) -> float:
        if previous <= 0:
            return 0.0
        return (current - previous) / previous

    def _exit_bid_for_target(
        self,
        avg_cost: Optional[float],
        position: float,
        cash: float,
        target_equity: float,
        fee_model: object = None,
    ) -> float:
        if position <= 0:
            return math.inf
        target_bid = max(0.0, (target_equity - cash) / position)
        if avg_cost is None:
            return target_bid
        take_profit_bid = required_exit_price_for_net_proceeds(
            shares=position,
            required_net_proceeds=position * avg_cost * (1.0 + self.take_profit_pct),
            max_exit_price=self.max_exit_price,
            fee_model=fee_model,
        )
        if self.allow_take_profit_before_target:
            return min(target_bid, take_profit_bid)
        return max(target_bid, take_profit_bid)

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
                market_state = self.market_state_by_asset.get(fill.asset)
                self.entry_bid_by_asset[fill.asset] = market_state.bid if market_state is not None else fill.price
                self.hold_cycles_by_asset[fill.asset] = 0
        elif fill.side == "SELL":
            previous_shares = self.position_shares_by_asset.get(fill.asset, 0.0)
            if fill.status == "PARTIAL" and previous_shares > fill.shares + 1e-9:
                self.position_shares_by_asset[fill.asset] = previous_shares - fill.shares
                return
            if fill.status == "PARTIAL" and previous_shares <= 1e-9:
                return
            self.position_shares_by_asset.pop(fill.asset, None)
            self.avg_cost_by_asset.pop(fill.asset, None)
            self.entry_bid_by_asset.pop(fill.asset, None)
            self.hold_cycles_by_asset.pop(fill.asset, None)
            self.group_by_asset.pop(fill.asset, None)
            if self.cooldown_cycles_after_sell > 0:
                self.cooldowns_by_asset[fill.asset] = self.cooldown_cycles_after_sell
                self.global_cooldown_cycles = max(self.global_cooldown_cycles, self.cooldown_cycles_after_sell)
