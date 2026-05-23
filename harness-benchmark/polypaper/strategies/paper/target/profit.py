from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

from ....models import MarketSnapshot, PaperFill, Portfolio, Signal
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
        diversify_by: str = "none",
        max_positions_per_group: int = 0,
        allowed_assets: Optional[Sequence[str]] = None,
        name: str = "paper_target_profit_10pct",
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
        self.diversify_by = diversify_by
        self.max_positions_per_group = max_positions_per_group
        self.allowed_assets = set(allowed_assets) if allowed_assets is not None else None
        self.avg_cost_by_asset: Dict[str, float] = {}
        self.entry_bid_by_asset: Dict[str, float] = {}
        self.hold_cycles_by_asset: Dict[str, int] = {}
        self.group_by_asset: Dict[str, str] = {}
        self.pending_assets: Dict[str, str] = {}
        self.market_state_by_asset: Dict[str, _MarketState] = {}
        self.cooldowns_by_asset: Dict[str, int] = {}
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
            self._finish_cycle(snapshots)
            return []
        unavailable_assets = set(portfolio.positions) | set(self.pending_assets)
        if len(unavailable_assets) >= self.max_positions:
            self._finish_cycle(snapshots)
            return []
        group_counts = self._group_counts(snapshots, unavailable_assets)
        notional = self._entry_notional(portfolio.cash)
        if notional <= 0:
            self._finish_cycle(snapshots)
            return []
        candidates = [
            self._score_snapshot(snapshot, portfolio.cash, notional, rules_by_asset=rules_by_asset)
            for snapshot in snapshots
            if (
                snapshot.asset not in unavailable_assets
                and self._asset_allowed(snapshot.asset)
                and self._group_allows(snapshot, group_counts)
                and self._momentum_passes(snapshot)
                and not self._cooldown_active(snapshot.asset)
            )
        ]
        viable = [candidate for candidate in candidates if candidate.viable]
        if not viable:
            self._finish_cycle(snapshots)
            return []
        best = max(viable, key=lambda candidate: candidate.score)
        self.pending_assets[best.asset] = "BUY"
        self.group_by_asset[best.asset] = self._group_key_for_opportunity(best)
        self._finish_cycle(snapshots)
        return [self._entry_signal(best)]

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
                    target_notional=position * snapshot.book.bid,
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
        }
        if self.adaptive_entry_sizing:
            kwargs["max_target_notional"] = notional
            kwargs["min_target_notional"] = self.min_entry_notional
        else:
            kwargs["target_notional"] = notional
        return scorer(**kwargs)

    def _entry_signal(self, opportunity: TargetOpportunity) -> Signal:
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
            ),
        )

    def _momentum_passes(self, snapshot: MarketSnapshot) -> bool:
        if self.min_momentum_observations <= 1:
            return True
        previous = self.market_state_by_asset.get(snapshot.asset)
        if previous is None:
            return False
        if previous.observations + 1 < self.min_momentum_observations:
            return False
        current = self._market_state(snapshot, previous.observations + 1)
        bid_improvement = self._relative_change(current.bid, previous.bid)
        mid_improvement = self._relative_change(current.mid, previous.mid)
        spread_widen = current.spread_pct - previous.spread_pct
        return (
            bid_improvement >= self.min_bid_improvement_pct
            and mid_improvement >= self.min_mid_improvement_pct
            and spread_widen <= self.max_spread_widen_pct
        )

    def _record_snapshots(self, snapshots: Sequence[MarketSnapshot]) -> None:
        for snapshot in snapshots:
            previous = self.market_state_by_asset.get(snapshot.asset)
            observations = 1 if previous is None else previous.observations + 1
            self.market_state_by_asset[snapshot.asset] = self._market_state(snapshot, observations)
            if snapshot.asset in self.avg_cost_by_asset and self.pending_assets.get(snapshot.asset) != "SELL":
                self.hold_cycles_by_asset[snapshot.asset] = self.hold_cycles_by_asset.get(snapshot.asset, 0) + 1

    def _finish_cycle(self, snapshots: Sequence[MarketSnapshot]) -> None:
        self._record_snapshots(snapshots)
        self._decrement_cooldowns()

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
            cost_per_share = (fill.notional + fill.fee) / fill.shares
            self.avg_cost_by_asset[fill.asset] = cost_per_share
            market_state = self.market_state_by_asset.get(fill.asset)
            self.entry_bid_by_asset[fill.asset] = market_state.bid if market_state is not None else fill.price
            self.hold_cycles_by_asset[fill.asset] = 0
        elif fill.side == "SELL":
            self.avg_cost_by_asset.pop(fill.asset, None)
            self.entry_bid_by_asset.pop(fill.asset, None)
            self.hold_cycles_by_asset.pop(fill.asset, None)
            self.group_by_asset.pop(fill.asset, None)
            if self.cooldown_cycles_after_sell > 0:
                self.cooldowns_by_asset[fill.asset] = self.cooldown_cycles_after_sell
                self.global_cooldown_cycles = max(self.global_cooldown_cycles, self.cooldown_cycles_after_sell)
