from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import product
from typing import Iterable, List, Optional, Sequence

from ....models import MarketSnapshot
from ....opportunity import TargetOpportunity, score_adaptive_target_opportunity, target_entry_notional
from .profit import TargetProfitPaperStrategy


@dataclass(frozen=True)
class TargetSweepConfig:
    take_profit_pct: float
    capital_fraction: float
    max_entry_mark_to_bid_loss_pct: float
    max_required_exit_distance_pct: float
    required_exit_distance_weight: float
    min_score: float

    def name(self) -> str:
        return (
            f"tp={self.take_profit_pct:.3f} cap={self.capital_fraction:.2f} "
            f"mark={self.max_entry_mark_to_bid_loss_pct:.3f} "
            f"exit={self.max_required_exit_distance_pct:.3f} "
            f"w={self.required_exit_distance_weight:.1f} score={self.min_score:.3f}"
        )


@dataclass(frozen=True)
class TargetSweepResult:
    config: TargetSweepConfig
    opportunity: TargetOpportunity
    fee_rate: float = 0.0
    fee_exponent: float = 1.0

    def to_dict(self) -> dict:
        return {
            "config": asdict(self.config),
            "fee_rate": self.fee_rate,
            "fee_exponent": self.fee_exponent,
            "opportunity": self.opportunity.to_dict(),
        }


def target_sweep_configs(
    take_profit_pcts: Sequence[float],
    capital_fractions: Sequence[float],
    max_entry_mark_to_bid_loss_pcts: Sequence[float],
    max_required_exit_distance_pcts: Sequence[float],
    required_exit_distance_weights: Sequence[float],
    min_scores: Sequence[float],
) -> List[TargetSweepConfig]:
    return [
        TargetSweepConfig(
            take_profit_pct=take_profit_pct,
            capital_fraction=capital_fraction,
            max_entry_mark_to_bid_loss_pct=max_entry_mark_to_bid_loss_pct,
            max_required_exit_distance_pct=max_required_exit_distance_pct,
            required_exit_distance_weight=required_exit_distance_weight,
            min_score=min_score,
        )
        for (
            take_profit_pct,
            capital_fraction,
            max_entry_mark_to_bid_loss_pct,
            max_required_exit_distance_pct,
            required_exit_distance_weight,
            min_score,
        ) in product(
            take_profit_pcts,
            capital_fractions,
            max_entry_mark_to_bid_loss_pcts,
            max_required_exit_distance_pcts,
            required_exit_distance_weights,
            min_scores,
        )
    ]


def sweep_target_opportunities(
    snapshots: Sequence[MarketSnapshot],
    rules_by_asset: dict,
    configs: Iterable[TargetSweepConfig],
    initial_cash: float,
    portfolio_target_roi: float,
    min_entry_notional: float,
    max_spread_pct: float,
    max_entry_impact_pct: float,
    max_exit_price: float,
    min_book_imbalance: float,
    depth_window_pct: float,
    imbalance_weight: float,
    min_bid_price: Optional[float],
    max_bid_price: Optional[float],
    top: int,
) -> List[TargetSweepResult]:
    results: List[TargetSweepResult] = []
    for config in configs:
        max_notional = target_entry_notional(
            initial_cash=initial_cash,
            current_cash=initial_cash,
            portfolio_target_roi=portfolio_target_roi,
            take_profit_pct=config.take_profit_pct,
            entry_notional=0.0,
            capital_fraction=config.capital_fraction,
        )
        if max_notional < min_entry_notional:
            continue
        for snapshot in snapshots:
            rules = rules_by_asset.get(snapshot.asset)
            fee_model = getattr(rules, "fee_model", None)
            opportunity = score_adaptive_target_opportunity(
                snapshot=snapshot,
                initial_cash=initial_cash,
                current_cash=initial_cash,
                max_target_notional=max_notional,
                min_target_notional=min_entry_notional,
                portfolio_target_roi=portfolio_target_roi,
                take_profit_pct=config.take_profit_pct,
                allow_take_profit_before_target=True,
                max_spread_pct=max_spread_pct,
                max_entry_impact_pct=max_entry_impact_pct,
                max_exit_price=max_exit_price,
                min_book_imbalance=min_book_imbalance,
                depth_window_pct=depth_window_pct,
                imbalance_weight=imbalance_weight,
                min_bid_price=min_bid_price,
                max_bid_price=max_bid_price,
                max_entry_mark_to_bid_loss_pct=config.max_entry_mark_to_bid_loss_pct,
                max_required_exit_distance_pct=config.max_required_exit_distance_pct,
                required_exit_distance_weight=config.required_exit_distance_weight,
                min_score=config.min_score,
                fee_model=fee_model,
            )
            if opportunity.viable:
                results.append(
                    TargetSweepResult(
                        config=config,
                        opportunity=opportunity,
                        fee_rate=float(getattr(fee_model, "fee_rate", 0.0) or 0.0),
                        fee_exponent=float(getattr(fee_model, "exponent", 1.0) or 1.0),
                    )
                )
    results.sort(
        key=lambda result: (
            result.opportunity.score,
            -result.opportunity.required_exit_distance_pct,
            -result.opportunity.entry_mark_to_bid_loss_pct,
            result.opportunity.exit_headroom,
        ),
        reverse=True,
    )
    deduped: List[TargetSweepResult] = []
    seen = set()
    for result in results:
        key = (
            result.opportunity.asset,
            result.config.take_profit_pct,
            result.config.required_exit_distance_weight,
            round(result.opportunity.target_notional, 2),
            round(result.opportunity.required_exit_bid, 4),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(result)
        if len(deduped) >= top:
            break
    return deduped


def target_strategy_from_sweep_result(args, result: TargetSweepResult, index: int) -> TargetProfitPaperStrategy:
    config = result.config
    asset_suffix = result.opportunity.asset[-6:] if result.opportunity.asset else "unknown"
    name = (
        f"paper_sweep_{index:03d}"
        f"_tp{int(round(config.take_profit_pct * 10000)):04d}"
        f"_cap{int(round(config.capital_fraction * 100)):02d}"
        f"_{asset_suffix}"
    )
    return TargetProfitPaperStrategy(
        initial_cash=args.initial_cash,
        portfolio_target_roi=args.portfolio_target_roi,
        take_profit_pct=config.take_profit_pct,
        allow_take_profit_before_target=True,
        stop_loss_pct=args.stop_loss_pct,
        entry_notional=0.0,
        capital_fraction=config.capital_fraction,
        adaptive_entry_sizing=True,
        min_entry_notional=args.target_min_entry_notional,
        max_spread_pct=args.target_max_spread_pct,
        max_entry_impact_pct=args.target_max_entry_impact_pct,
        max_exit_price=args.target_max_exit_price,
        min_book_imbalance=args.target_min_book_imbalance,
        depth_window_pct=args.target_depth_window_pct,
        imbalance_weight=args.target_imbalance_weight,
        min_bid_price=args.target_min_bid_price,
        max_bid_price=args.target_max_bid_price,
        max_entry_mark_to_bid_loss_pct=config.max_entry_mark_to_bid_loss_pct,
        max_required_exit_distance_pct=config.max_required_exit_distance_pct,
        required_exit_distance_weight=config.required_exit_distance_weight,
        min_score=config.min_score,
        min_momentum_observations=args.target_min_momentum_observations,
        min_bid_improvement_pct=args.target_min_bid_improvement_pct,
        min_mid_improvement_pct=args.target_min_mid_improvement_pct,
        max_spread_widen_pct=args.target_max_spread_widen_pct,
        cooldown_cycles_after_sell=args.target_cooldown_cycles_after_sell,
        max_hold_cycles=args.target_max_hold_cycles,
        max_hold_min_progress_pct=args.target_max_hold_min_progress_pct,
        max_hold_cooldown_cycles=args.target_max_hold_cooldown_cycles,
        watchlist_size=getattr(args, "target_watchlist_size", 0),
        allowed_assets=[result.opportunity.asset],
        name=name,
    )
