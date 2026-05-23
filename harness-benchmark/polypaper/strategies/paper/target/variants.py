from __future__ import annotations

from .profit import TargetProfitPaperStrategy

DEFAULT_TARGET_VARIANTS = (
    "balanced",
    "compound_quality",
    "low_friction_compound",
    "volatile_compound",
    "micro_compound",
    "convex_tick",
    "compound",
    "near_target",
    "aggressive",
    "conservative",
)

DEFAULT_TARGET_VARIANTS_ARG = ",".join(DEFAULT_TARGET_VARIANTS)
TARGET_VARIANT_HELP = f"Comma-separated target variants: {', '.join(DEFAULT_TARGET_VARIANTS)}"


def target_strategy_from_args(args, name: str) -> TargetProfitPaperStrategy:
    return TargetProfitPaperStrategy(
        initial_cash=args.initial_cash,
        portfolio_target_roi=args.portfolio_target_roi,
        take_profit_pct=args.take_profit_pct,
        allow_take_profit_before_target=args.target_allow_take_profit_before_target,
        stop_loss_pct=args.stop_loss_pct,
        entry_notional=args.target_entry_notional,
        capital_fraction=args.target_capital_fraction,
        adaptive_entry_sizing=args.target_adaptive_entry_sizing,
        min_entry_notional=args.target_min_entry_notional,
        max_spread_pct=args.target_max_spread_pct,
        max_entry_impact_pct=args.target_max_entry_impact_pct,
        max_exit_price=args.target_max_exit_price,
        min_book_imbalance=args.target_min_book_imbalance,
        depth_window_pct=args.target_depth_window_pct,
        imbalance_weight=args.target_imbalance_weight,
        min_bid_price=args.target_min_bid_price,
        max_bid_price=args.target_max_bid_price,
        max_entry_mark_to_bid_loss_pct=args.target_max_entry_mark_to_bid_loss_pct,
        max_required_exit_distance_pct=args.target_max_required_exit_distance_pct,
        required_exit_distance_weight=args.target_required_exit_distance_weight,
        min_score=args.target_min_score,
        min_momentum_observations=args.target_min_momentum_observations,
        min_bid_improvement_pct=args.target_min_bid_improvement_pct,
        min_mid_improvement_pct=args.target_min_mid_improvement_pct,
        max_spread_widen_pct=args.target_max_spread_widen_pct,
        cooldown_cycles_after_sell=args.target_cooldown_cycles_after_sell,
        max_hold_cycles=args.target_max_hold_cycles,
        max_hold_min_progress_pct=args.target_max_hold_min_progress_pct,
        max_hold_cooldown_cycles=args.target_max_hold_cooldown_cycles,
        max_positions=args.target_max_positions,
        diversify_by=args.target_diversify_by,
        max_positions_per_group=args.target_max_positions_per_group,
        name=name,
    )


def target_strategy_from_config(args, name: str, config: dict) -> TargetProfitPaperStrategy:
    return TargetProfitPaperStrategy(
        initial_cash=args.initial_cash,
        portfolio_target_roi=args.portfolio_target_roi,
        take_profit_pct=config["take_profit_pct"],
        allow_take_profit_before_target=config["allow_take_profit_before_target"],
        stop_loss_pct=config["stop_loss_pct"],
        entry_notional=args.target_entry_notional,
        capital_fraction=config["capital_fraction"],
        adaptive_entry_sizing=config["adaptive_entry_sizing"],
        min_entry_notional=config["min_entry_notional"],
        max_spread_pct=config["max_spread_pct"],
        max_entry_impact_pct=config["max_entry_impact_pct"],
        max_exit_price=args.target_max_exit_price,
        min_book_imbalance=config["min_book_imbalance"],
        depth_window_pct=args.target_depth_window_pct,
        imbalance_weight=args.target_imbalance_weight,
        min_bid_price=config["min_bid_price"],
        max_bid_price=config["max_bid_price"],
        max_entry_mark_to_bid_loss_pct=config["max_entry_mark_to_bid_loss_pct"],
        max_required_exit_distance_pct=config["max_required_exit_distance_pct"],
        required_exit_distance_weight=config["required_exit_distance_weight"],
        min_score=config["min_score"],
        min_momentum_observations=config["min_momentum_observations"],
        min_bid_improvement_pct=config["min_bid_improvement_pct"],
        min_mid_improvement_pct=config["min_mid_improvement_pct"],
        max_spread_widen_pct=args.target_max_spread_widen_pct,
        cooldown_cycles_after_sell=config["cooldown_cycles_after_sell"],
        max_hold_cycles=config["max_hold_cycles"],
        max_hold_min_progress_pct=config["max_hold_min_progress_pct"],
        max_hold_cooldown_cycles=config["max_hold_cooldown_cycles"],
        max_positions=config["max_positions"],
        diversify_by=config["diversify_by"],
        max_positions_per_group=config["max_positions_per_group"],
        name=f"paper_target_{name}",
    )


def target_variant_configs(args) -> list:
    requested = [item.strip() for item in args.target_variants.split(",") if item.strip()]
    configs = {
        "balanced": {
            "capital_fraction": args.target_capital_fraction,
            "take_profit_pct": args.take_profit_pct,
            "allow_take_profit_before_target": args.target_allow_take_profit_before_target,
            "stop_loss_pct": args.stop_loss_pct,
            "adaptive_entry_sizing": args.target_adaptive_entry_sizing,
            "min_entry_notional": args.target_min_entry_notional,
            "max_spread_pct": args.target_max_spread_pct,
            "max_entry_impact_pct": args.target_max_entry_impact_pct,
            "min_book_imbalance": args.target_min_book_imbalance,
            "min_bid_price": args.target_min_bid_price,
            "max_bid_price": args.target_max_bid_price,
            "max_entry_mark_to_bid_loss_pct": args.target_max_entry_mark_to_bid_loss_pct,
            "max_required_exit_distance_pct": args.target_max_required_exit_distance_pct,
            "required_exit_distance_weight": args.target_required_exit_distance_weight,
            "min_score": args.target_min_score,
            "min_momentum_observations": args.target_min_momentum_observations,
            "min_bid_improvement_pct": args.target_min_bid_improvement_pct,
            "min_mid_improvement_pct": args.target_min_mid_improvement_pct,
            "cooldown_cycles_after_sell": args.target_cooldown_cycles_after_sell,
            "max_hold_cycles": args.target_max_hold_cycles,
            "max_hold_min_progress_pct": args.target_max_hold_min_progress_pct,
            "max_hold_cooldown_cycles": args.target_max_hold_cooldown_cycles,
            "max_positions": args.target_max_positions,
            "diversify_by": args.target_diversify_by,
            "max_positions_per_group": args.target_max_positions_per_group,
        },
        "compound_quality": {
            "capital_fraction": min(0.98, max(args.target_capital_fraction, 0.95)),
            "take_profit_pct": min(args.take_profit_pct, 0.01),
            "allow_take_profit_before_target": True,
            "stop_loss_pct": args.stop_loss_pct,
            "adaptive_entry_sizing": args.target_adaptive_entry_sizing,
            "min_entry_notional": args.target_min_entry_notional,
            "max_spread_pct": min(args.target_max_spread_pct, 0.01),
            "max_entry_impact_pct": min(args.target_max_entry_impact_pct, 0.01),
            "min_book_imbalance": min(args.target_min_book_imbalance, -0.10),
            "min_bid_price": args.target_min_bid_price,
            "max_bid_price": args.target_max_bid_price,
            "max_entry_mark_to_bid_loss_pct": (
                args.target_max_entry_mark_to_bid_loss_pct
                if args.target_max_entry_mark_to_bid_loss_pct is not None
                else 0.005
            ),
            "max_required_exit_distance_pct": (
                args.target_max_required_exit_distance_pct
                if args.target_max_required_exit_distance_pct is not None
                else 0.02
            ),
            "required_exit_distance_weight": max(args.target_required_exit_distance_weight, 4.0),
            "min_score": args.target_min_score if args.target_min_score is not None else 0.0,
            "min_momentum_observations": 1,
            "min_bid_improvement_pct": min(args.target_min_bid_improvement_pct, 0.0),
            "min_mid_improvement_pct": min(args.target_min_mid_improvement_pct, 0.0),
            "cooldown_cycles_after_sell": 0,
            "max_hold_cycles": args.target_max_hold_cycles if args.target_max_hold_cycles > 0 else 5,
            "max_hold_min_progress_pct": args.target_max_hold_min_progress_pct,
            "max_hold_cooldown_cycles": (
                args.target_max_hold_cooldown_cycles
                if args.target_max_hold_cooldown_cycles > 0
                else 8
            ),
            "max_positions": args.target_max_positions,
            "diversify_by": args.target_diversify_by,
            "max_positions_per_group": args.target_max_positions_per_group,
        },
        "low_friction_compound": {
            "capital_fraction": min(args.target_capital_fraction, 0.10),
            "take_profit_pct": min(args.take_profit_pct, 0.01),
            "allow_take_profit_before_target": True,
            "stop_loss_pct": max(args.stop_loss_pct, 0.08),
            "adaptive_entry_sizing": True,
            "min_entry_notional": max(args.target_min_entry_notional, 25.0),
            "max_spread_pct": min(args.target_max_spread_pct, 0.03),
            "max_entry_impact_pct": min(max(args.target_max_entry_impact_pct, 0.05), 0.08),
            "min_book_imbalance": min(args.target_min_book_imbalance, 0.0),
            "min_bid_price": (
                args.target_min_bid_price
                if args.target_min_bid_price is not None
                else 0.20
            ),
            "max_bid_price": (
                args.target_max_bid_price
                if args.target_max_bid_price is not None
                else 0.80
            ),
            "max_entry_mark_to_bid_loss_pct": (
                args.target_max_entry_mark_to_bid_loss_pct
                if args.target_max_entry_mark_to_bid_loss_pct is not None
                else 0.05
            ),
            "max_required_exit_distance_pct": (
                args.target_max_required_exit_distance_pct
                if args.target_max_required_exit_distance_pct is not None
                else 0.10
            ),
            "required_exit_distance_weight": max(args.target_required_exit_distance_weight, 1.0),
            "min_score": args.target_min_score if args.target_min_score is not None else 0.0,
            "min_momentum_observations": max(args.target_min_momentum_observations, 2),
            "min_bid_improvement_pct": max(args.target_min_bid_improvement_pct, 0.001),
            "min_mid_improvement_pct": max(args.target_min_mid_improvement_pct, 0.001),
            "cooldown_cycles_after_sell": 1,
            "max_hold_cycles": args.target_max_hold_cycles if args.target_max_hold_cycles > 0 else 20,
            "max_hold_min_progress_pct": args.target_max_hold_min_progress_pct,
            "max_hold_cooldown_cycles": (
                args.target_max_hold_cooldown_cycles
                if args.target_max_hold_cooldown_cycles > 0
                else 10
            ),
            "max_positions": max(args.target_max_positions, 3),
            "diversify_by": (
                args.target_diversify_by
                if args.target_diversify_by != "none"
                else "title_prefix"
            ),
            "max_positions_per_group": max(args.target_max_positions_per_group, 1),
        },
        "volatile_compound": {
            "capital_fraction": min(args.target_capital_fraction, 0.50),
            "take_profit_pct": min(args.take_profit_pct, 0.10),
            "allow_take_profit_before_target": True,
            "stop_loss_pct": max(args.stop_loss_pct, 0.15),
            "adaptive_entry_sizing": True,
            "min_entry_notional": max(args.target_min_entry_notional, 25.0),
            "max_spread_pct": min(args.target_max_spread_pct, 0.03),
            "max_entry_impact_pct": max(args.target_max_entry_impact_pct, 0.12),
            "min_book_imbalance": min(args.target_min_book_imbalance, -0.60),
            "min_bid_price": (
                args.target_min_bid_price
                if args.target_min_bid_price is not None
                else 0.20
            ),
            "max_bid_price": (
                args.target_max_bid_price
                if args.target_max_bid_price is not None
                else 0.80
            ),
            "max_entry_mark_to_bid_loss_pct": (
                args.target_max_entry_mark_to_bid_loss_pct
                if args.target_max_entry_mark_to_bid_loss_pct is not None
                else 0.05
            ),
            "max_required_exit_distance_pct": (
                args.target_max_required_exit_distance_pct
                if args.target_max_required_exit_distance_pct is not None
                else 0.30
            ),
            "required_exit_distance_weight": max(args.target_required_exit_distance_weight, 1.0),
            "min_score": args.target_min_score if args.target_min_score is not None else 0.0,
            "min_momentum_observations": 1,
            "min_bid_improvement_pct": min(args.target_min_bid_improvement_pct, 0.0),
            "min_mid_improvement_pct": min(args.target_min_mid_improvement_pct, 0.0),
            "cooldown_cycles_after_sell": 1,
            "max_hold_cycles": args.target_max_hold_cycles if args.target_max_hold_cycles > 0 else 12,
            "max_hold_min_progress_pct": args.target_max_hold_min_progress_pct,
            "max_hold_cooldown_cycles": (
                args.target_max_hold_cooldown_cycles
                if args.target_max_hold_cooldown_cycles > 0
                else 8
            ),
            "max_positions": max(args.target_max_positions, 3),
            "diversify_by": (
                args.target_diversify_by
                if args.target_diversify_by != "none"
                else "title_prefix"
            ),
            "max_positions_per_group": max(args.target_max_positions_per_group, 1),
        },
        "micro_compound": {
            "capital_fraction": min(args.target_capital_fraction, 0.20),
            "take_profit_pct": min(args.take_profit_pct, 0.01),
            "allow_take_profit_before_target": True,
            "stop_loss_pct": max(args.stop_loss_pct, 0.15),
            "adaptive_entry_sizing": True,
            "min_entry_notional": max(args.target_min_entry_notional, 25.0),
            "max_spread_pct": min(args.target_max_spread_pct, 0.03),
            "max_entry_impact_pct": max(args.target_max_entry_impact_pct, 0.08),
            "min_book_imbalance": min(args.target_min_book_imbalance, -0.60),
            "min_bid_price": (
                args.target_min_bid_price
                if args.target_min_bid_price is not None
                else 0.20
            ),
            "max_bid_price": (
                args.target_max_bid_price
                if args.target_max_bid_price is not None
                else 0.80
            ),
            "max_entry_mark_to_bid_loss_pct": (
                args.target_max_entry_mark_to_bid_loss_pct
                if args.target_max_entry_mark_to_bid_loss_pct is not None
                else 0.08
            ),
            "max_required_exit_distance_pct": (
                args.target_max_required_exit_distance_pct
                if args.target_max_required_exit_distance_pct is not None
                else 0.20
            ),
            "required_exit_distance_weight": max(args.target_required_exit_distance_weight, 2.0),
            "min_score": args.target_min_score if args.target_min_score is not None else 0.0,
            "min_momentum_observations": 1,
            "min_bid_improvement_pct": min(args.target_min_bid_improvement_pct, 0.0),
            "min_mid_improvement_pct": min(args.target_min_mid_improvement_pct, 0.0),
            "cooldown_cycles_after_sell": 1,
            "max_hold_cycles": args.target_max_hold_cycles if args.target_max_hold_cycles > 0 else 20,
            "max_hold_min_progress_pct": args.target_max_hold_min_progress_pct,
            "max_hold_cooldown_cycles": (
                args.target_max_hold_cooldown_cycles
                if args.target_max_hold_cooldown_cycles > 0
                else 10
            ),
            "max_positions": max(args.target_max_positions, 3),
            "diversify_by": (
                args.target_diversify_by
                if args.target_diversify_by != "none"
                else "title_prefix"
            ),
            "max_positions_per_group": max(args.target_max_positions_per_group, 1),
        },
        "convex_tick": {
            "capital_fraction": min(args.target_capital_fraction, 0.50),
            "take_profit_pct": max(args.take_profit_pct, 0.20),
            "allow_take_profit_before_target": True,
            "stop_loss_pct": max(args.stop_loss_pct, 0.60),
            "adaptive_entry_sizing": True,
            "min_entry_notional": max(args.target_min_entry_notional, 5.0),
            "max_spread_pct": max(args.target_max_spread_pct, 0.15),
            "max_entry_impact_pct": max(args.target_max_entry_impact_pct, 0.25),
            "min_book_imbalance": min(args.target_min_book_imbalance, -1.0),
            "min_bid_price": (
                args.target_min_bid_price
                if args.target_min_bid_price is not None
                else 0.005
            ),
            "max_bid_price": (
                args.target_max_bid_price
                if args.target_max_bid_price is not None
                else 0.20
            ),
            "max_entry_mark_to_bid_loss_pct": (
                args.target_max_entry_mark_to_bid_loss_pct
                if args.target_max_entry_mark_to_bid_loss_pct is not None
                else 0.25
            ),
            "max_required_exit_distance_pct": (
                args.target_max_required_exit_distance_pct
                if args.target_max_required_exit_distance_pct is not None
                else 0.75
            ),
            "required_exit_distance_weight": max(args.target_required_exit_distance_weight, 0.5),
            "min_score": args.target_min_score if args.target_min_score is not None else -1.0,
            "min_momentum_observations": max(args.target_min_momentum_observations, 2),
            "min_bid_improvement_pct": max(args.target_min_bid_improvement_pct, 0.001),
            "min_mid_improvement_pct": max(args.target_min_mid_improvement_pct, 0.001),
            "cooldown_cycles_after_sell": max(args.target_cooldown_cycles_after_sell, 2),
            "max_hold_cycles": args.target_max_hold_cycles if args.target_max_hold_cycles > 0 else 6,
            "max_hold_min_progress_pct": args.target_max_hold_min_progress_pct,
            "max_hold_cooldown_cycles": (
                args.target_max_hold_cooldown_cycles
                if args.target_max_hold_cooldown_cycles > 0
                else 6
            ),
            "max_positions": max(args.target_max_positions, 5),
            "diversify_by": (
                args.target_diversify_by
                if args.target_diversify_by != "none"
                else "condition"
            ),
            "max_positions_per_group": max(args.target_max_positions_per_group, 1),
        },
        "compound": {
            "capital_fraction": min(0.98, max(args.target_capital_fraction, 0.95)),
            "take_profit_pct": min(args.take_profit_pct, 0.01),
            "allow_take_profit_before_target": True,
            "stop_loss_pct": args.stop_loss_pct,
            "adaptive_entry_sizing": args.target_adaptive_entry_sizing,
            "min_entry_notional": args.target_min_entry_notional,
            "max_spread_pct": min(args.target_max_spread_pct, 0.02),
            "max_entry_impact_pct": min(args.target_max_entry_impact_pct, 0.02),
            "min_book_imbalance": min(args.target_min_book_imbalance, -0.25),
            "min_bid_price": args.target_min_bid_price,
            "max_bid_price": args.target_max_bid_price,
            "max_entry_mark_to_bid_loss_pct": (
                args.target_max_entry_mark_to_bid_loss_pct
                if args.target_max_entry_mark_to_bid_loss_pct is not None
                else args.stop_loss_pct
            ),
            "max_required_exit_distance_pct": (
                args.target_max_required_exit_distance_pct
                if args.target_max_required_exit_distance_pct is not None
                else 0.025
            ),
            "required_exit_distance_weight": max(args.target_required_exit_distance_weight, 2.0),
            "min_score": args.target_min_score if args.target_min_score is not None else 0.0,
            "min_momentum_observations": 1,
            "min_bid_improvement_pct": min(args.target_min_bid_improvement_pct, 0.0),
            "min_mid_improvement_pct": min(args.target_min_mid_improvement_pct, 0.0),
            "cooldown_cycles_after_sell": 0,
            "max_hold_cycles": args.target_max_hold_cycles if args.target_max_hold_cycles > 0 else 3,
            "max_hold_min_progress_pct": args.target_max_hold_min_progress_pct,
            "max_hold_cooldown_cycles": (
                args.target_max_hold_cooldown_cycles
                if args.target_max_hold_cooldown_cycles > 0
                else 6
            ),
            "max_positions": args.target_max_positions,
            "diversify_by": args.target_diversify_by,
            "max_positions_per_group": args.target_max_positions_per_group,
        },
        "near_target": {
            "capital_fraction": min(0.98, max(args.target_capital_fraction, 0.95)),
            "take_profit_pct": args.take_profit_pct,
            "allow_take_profit_before_target": args.target_allow_take_profit_before_target,
            "stop_loss_pct": args.stop_loss_pct,
            "adaptive_entry_sizing": args.target_adaptive_entry_sizing,
            "min_entry_notional": args.target_min_entry_notional,
            "max_spread_pct": min(args.target_max_spread_pct, 0.02),
            "max_entry_impact_pct": min(args.target_max_entry_impact_pct, 0.02),
            "min_book_imbalance": min(args.target_min_book_imbalance, -0.25),
            "min_bid_price": args.target_min_bid_price,
            "max_bid_price": args.target_max_bid_price,
            "max_entry_mark_to_bid_loss_pct": args.target_max_entry_mark_to_bid_loss_pct,
            "max_required_exit_distance_pct": (
                args.target_max_required_exit_distance_pct
                if args.target_max_required_exit_distance_pct is not None
                else 0.12
            ),
            "required_exit_distance_weight": max(args.target_required_exit_distance_weight, 2.0),
            "min_score": args.target_min_score,
            "min_momentum_observations": 1,
            "min_bid_improvement_pct": min(args.target_min_bid_improvement_pct, 0.0),
            "min_mid_improvement_pct": min(args.target_min_mid_improvement_pct, 0.0),
            "cooldown_cycles_after_sell": args.target_cooldown_cycles_after_sell,
            "max_hold_cycles": args.target_max_hold_cycles,
            "max_hold_min_progress_pct": args.target_max_hold_min_progress_pct,
            "max_hold_cooldown_cycles": args.target_max_hold_cooldown_cycles,
            "max_positions": args.target_max_positions,
            "diversify_by": args.target_diversify_by,
            "max_positions_per_group": args.target_max_positions_per_group,
        },
        "aggressive": {
            "capital_fraction": min(0.98, max(args.target_capital_fraction, 0.95)),
            "take_profit_pct": args.take_profit_pct,
            "allow_take_profit_before_target": args.target_allow_take_profit_before_target,
            "stop_loss_pct": args.stop_loss_pct,
            "adaptive_entry_sizing": args.target_adaptive_entry_sizing,
            "min_entry_notional": args.target_min_entry_notional,
            "max_spread_pct": max(args.target_max_spread_pct, 0.05),
            "max_entry_impact_pct": max(args.target_max_entry_impact_pct, 0.06),
            "min_book_imbalance": min(args.target_min_book_imbalance, -0.05),
            "min_bid_price": args.target_min_bid_price,
            "max_bid_price": args.target_max_bid_price,
            "max_entry_mark_to_bid_loss_pct": args.target_max_entry_mark_to_bid_loss_pct,
            "max_required_exit_distance_pct": args.target_max_required_exit_distance_pct,
            "required_exit_distance_weight": args.target_required_exit_distance_weight,
            "min_score": args.target_min_score,
            "min_momentum_observations": 1,
            "min_bid_improvement_pct": min(args.target_min_bid_improvement_pct, 0.0),
            "min_mid_improvement_pct": min(args.target_min_mid_improvement_pct, 0.0),
            "cooldown_cycles_after_sell": args.target_cooldown_cycles_after_sell,
            "max_hold_cycles": args.target_max_hold_cycles,
            "max_hold_min_progress_pct": args.target_max_hold_min_progress_pct,
            "max_hold_cooldown_cycles": args.target_max_hold_cooldown_cycles,
            "max_positions": args.target_max_positions,
            "diversify_by": args.target_diversify_by,
            "max_positions_per_group": args.target_max_positions_per_group,
        },
        "conservative": {
            "capital_fraction": min(args.target_capital_fraction, 0.75),
            "take_profit_pct": args.take_profit_pct,
            "allow_take_profit_before_target": args.target_allow_take_profit_before_target,
            "stop_loss_pct": args.stop_loss_pct,
            "adaptive_entry_sizing": args.target_adaptive_entry_sizing,
            "min_entry_notional": args.target_min_entry_notional,
            "max_spread_pct": min(args.target_max_spread_pct, 0.03),
            "max_entry_impact_pct": min(args.target_max_entry_impact_pct, 0.03),
            "min_book_imbalance": max(args.target_min_book_imbalance, 0.15),
            "min_bid_price": args.target_min_bid_price,
            "max_bid_price": args.target_max_bid_price,
            "max_entry_mark_to_bid_loss_pct": args.target_max_entry_mark_to_bid_loss_pct,
            "max_required_exit_distance_pct": args.target_max_required_exit_distance_pct,
            "required_exit_distance_weight": args.target_required_exit_distance_weight,
            "min_score": args.target_min_score,
            "min_momentum_observations": max(args.target_min_momentum_observations, 3),
            "min_bid_improvement_pct": max(args.target_min_bid_improvement_pct, 0.002),
            "min_mid_improvement_pct": max(args.target_min_mid_improvement_pct, 0.002),
            "cooldown_cycles_after_sell": args.target_cooldown_cycles_after_sell,
            "max_hold_cycles": args.target_max_hold_cycles,
            "max_hold_min_progress_pct": args.target_max_hold_min_progress_pct,
            "max_hold_cooldown_cycles": args.target_max_hold_cooldown_cycles,
            "max_positions": args.target_max_positions,
            "diversify_by": args.target_diversify_by,
            "max_positions_per_group": args.target_max_positions_per_group,
        },
    }
    unknown = [name for name in requested if name not in configs]
    if unknown:
        raise ValueError(f"unknown target variants: {', '.join(unknown)}")
    if not requested:
        raise ValueError("at least one target variant is required")
    return [(name, configs[name]) for name in requested]
