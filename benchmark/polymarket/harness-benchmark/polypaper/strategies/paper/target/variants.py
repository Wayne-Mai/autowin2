from __future__ import annotations

from .basket import OutcomeBasketArbPaperStrategy
from .crypto import (
    CryptoDirectionalPaperStrategy,
    CryptoIntervalAnchorPaperStrategy,
    CryptoIntervalBookSkewPaperStrategy,
    CryptoIntervalCloseEdgePaperStrategy,
)
from .profit import TargetProfitPaperStrategy
from .scalpers import MakerRebateRotationStrategy, MomentumScalperPaperStrategy, SpreadCaptureMakerStrategy

DEFAULT_TARGET_VARIANTS = (
    "balanced",
    "compound_quality",
    "low_friction_compound",
    "volatile_compound",
    "micro_compound",
    "convex_tick",
    "convex_basket_goal",
    "maker_convex_basket_goal",
    "rolling_momentum_maker_goal",
    "breakout_goal",
    "breakout_relaxed_goal",
    "basket_goal",
    "low_distance_goal",
    "momentum_scalper_goal",
    "crypto_directional_goal",
    "crypto_interval_anchor_goal",
    "crypto_interval_close_edge_goal",
    "crypto_interval_book_skew_goal",
    "spread_capture_maker_goal",
    "maker_rebate_rotation_goal",
    "outcome_basket_arb_goal",
    "compound",
    "near_target",
    "aggressive",
    "conservative",
)

TARGET_VARIANT_GROUPS = (
    "strategy_v1_selected",
    "online_goal_grid",
    "momentum_scalper_grid",
    "crypto_directional_grid",
    "crypto_interval_anchor_grid",
    "crypto_interval_close_edge_grid",
    "crypto_interval_book_skew_grid",
    "spread_capture_maker_grid",
    "maker_rebate_rotation_grid",
    "outcome_basket_arb_grid",
)
DEFAULT_TARGET_VARIANTS_ARG = ",".join(DEFAULT_TARGET_VARIANTS)
TARGET_VARIANT_HELP = (
    f"Comma-separated target variants: {', '.join(DEFAULT_TARGET_VARIANTS)}. "
    f"Expandable groups: {', '.join(TARGET_VARIANT_GROUPS)}"
)

STRATEGY_V1_ANCHOR_GRID_INDEXES = tuple(range(1, 25))
STRATEGY_V1_BOOK_SKEW_GRID_INDEXES = (
    1,
    2,
    4,
    5,
    7,
    8,
    10,
    11,
    13,
    14,
    16,
    17,
    19,
    21,
    22,
    24,
    25,
    27,
    28,
    30,
    31,
    33,
    34,
    36,
    37,
    40,
    43,
    46,
    49,
    52,
    55,
    56,
    57,
    58,
    59,
    60,
    61,
    62,
    63,
    64,
    65,
    66,
    67,
    68,
    69,
    70,
    71,
    72,
)


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
        max_entries_per_cycle=getattr(args, "target_max_entries_per_cycle", 1),
        diversify_by=args.target_diversify_by,
        max_positions_per_group=args.target_max_positions_per_group,
        allowed_assets=_target_allowed_assets(args),
        watchlist_size=getattr(args, "target_watchlist_size", 0),
        history_change_weight=getattr(args, "target_history_change_weight", 0.0),
        entry_execution_style=getattr(args, "target_entry_execution_style", "taker"),
        name=name,
    )


def target_strategy_from_config(args, name: str, config: dict) -> TargetProfitPaperStrategy:
    strategy_type = config.get("strategy_type", "target_profit")
    if strategy_type == "momentum_scalper":
        return MomentumScalperPaperStrategy(
            initial_cash=args.initial_cash,
            portfolio_target_roi=args.portfolio_target_roi,
            take_profit_pct=config["take_profit_pct"],
            stop_loss_pct=config["stop_loss_pct"],
            entry_notional=config.get("entry_notional", args.target_entry_notional),
            capital_fraction=config["capital_fraction"],
            min_entry_notional=config["min_entry_notional"],
            max_spread_pct=config["max_spread_pct"],
            min_spread_pct=config["min_spread_pct"],
            max_entry_impact_pct=config["max_entry_impact_pct"],
            min_book_imbalance=config["min_book_imbalance"],
            depth_window_pct=args.target_depth_window_pct,
            min_bid_price=config["min_bid_price"],
            max_bid_price=config["max_bid_price"],
            min_momentum_observations=config["min_momentum_observations"],
            min_bid_improvement_pct=config["min_bid_improvement_pct"],
            min_mid_improvement_pct=config["min_mid_improvement_pct"],
            max_spread_widen_pct=config["max_spread_widen_pct"],
            max_positions=config["max_positions"],
            max_entries_per_cycle=config["max_entries_per_cycle"],
            cooldown_cycles_after_sell=config["cooldown_cycles_after_sell"],
            max_hold_cycles=config["max_hold_cycles"],
            max_hold_min_progress_pct=config["max_hold_min_progress_pct"],
            max_hold_cooldown_cycles=config["max_hold_cooldown_cycles"],
            entry_execution_style=config["entry_execution_style"],
            maker_exit=config["maker_exit"],
            diagnostic_limit=config.get("diagnostic_limit", 50),
            name=f"paper_target_{name}",
        )
    if strategy_type == "spread_capture_maker":
        return SpreadCaptureMakerStrategy(
            initial_cash=args.initial_cash,
            portfolio_target_roi=args.portfolio_target_roi,
            take_profit_pct=config["take_profit_pct"],
            stop_loss_pct=config["stop_loss_pct"],
            entry_notional=config.get("entry_notional", args.target_entry_notional),
            capital_fraction=config["capital_fraction"],
            min_entry_notional=config["min_entry_notional"],
            max_spread_pct=config["max_spread_pct"],
            min_spread_pct=config["min_spread_pct"],
            max_entry_impact_pct=config["max_entry_impact_pct"],
            min_book_imbalance=config["min_book_imbalance"],
            depth_window_pct=args.target_depth_window_pct,
            min_bid_price=config["min_bid_price"],
            max_bid_price=config["max_bid_price"],
            min_momentum_observations=config["min_momentum_observations"],
            min_bid_improvement_pct=config["min_bid_improvement_pct"],
            min_mid_improvement_pct=config["min_mid_improvement_pct"],
            max_spread_widen_pct=config["max_spread_widen_pct"],
            max_positions=config["max_positions"],
            max_entries_per_cycle=config["max_entries_per_cycle"],
            cooldown_cycles_after_sell=config["cooldown_cycles_after_sell"],
            max_hold_cycles=config["max_hold_cycles"],
            max_hold_min_progress_pct=config["max_hold_min_progress_pct"],
            max_hold_cooldown_cycles=config["max_hold_cooldown_cycles"],
            diagnostic_limit=config.get("diagnostic_limit", 50),
            name=f"paper_target_{name}",
        )
    if strategy_type == "maker_rebate_rotation":
        return MakerRebateRotationStrategy(
            initial_cash=args.initial_cash,
            portfolio_target_roi=args.portfolio_target_roi,
            take_profit_pct=config["take_profit_pct"],
            stop_loss_pct=config["stop_loss_pct"],
            entry_notional=config.get("entry_notional", args.target_entry_notional),
            capital_fraction=config["capital_fraction"],
            min_entry_notional=config["min_entry_notional"],
            max_spread_pct=config["max_spread_pct"],
            min_spread_pct=config["min_spread_pct"],
            max_entry_impact_pct=config["max_entry_impact_pct"],
            min_book_imbalance=config["min_book_imbalance"],
            depth_window_pct=args.target_depth_window_pct,
            min_bid_price=config["min_bid_price"],
            max_bid_price=config["max_bid_price"],
            min_momentum_observations=config["min_momentum_observations"],
            min_bid_improvement_pct=config["min_bid_improvement_pct"],
            min_mid_improvement_pct=config["min_mid_improvement_pct"],
            max_spread_widen_pct=config["max_spread_widen_pct"],
            max_positions=config["max_positions"],
            max_entries_per_cycle=config["max_entries_per_cycle"],
            cooldown_cycles_after_sell=config["cooldown_cycles_after_sell"],
            max_hold_cycles=config["max_hold_cycles"],
            max_hold_min_progress_pct=config["max_hold_min_progress_pct"],
            max_hold_cooldown_cycles=config["max_hold_cooldown_cycles"],
            min_round_trip_edge_pct=config["min_round_trip_edge_pct"],
            min_maker_rebate_pct=config["min_maker_rebate_pct"],
            min_touch_depth_notional=config["min_touch_depth_notional"],
            diagnostic_limit=config.get("diagnostic_limit", 50),
            name=f"paper_target_{name}",
        )
    if strategy_type == "outcome_basket_arb":
        return OutcomeBasketArbPaperStrategy(
            initial_cash=args.initial_cash,
            portfolio_target_roi=args.portfolio_target_roi,
            take_profit_pct=config["take_profit_pct"],
            stop_loss_pct=config["stop_loss_pct"],
            entry_notional=config["entry_notional"],
            capital_fraction=config["capital_fraction"],
            min_entry_notional=config["min_entry_notional"],
            min_settlement_roi=config["min_settlement_roi"],
            min_mark_roi=config["min_mark_roi"],
            max_outcomes=config["max_outcomes"],
            max_positions=config["max_positions"],
            max_entries_per_cycle=config["max_entries_per_cycle"],
            max_hold_cycles=config["max_hold_cycles"],
            cooldown_cycles_after_sell=config["cooldown_cycles_after_sell"],
            diagnostic_limit=config.get("diagnostic_limit", 50),
            name=f"paper_target_{name}",
        )
    if strategy_type == "crypto_directional":
        return CryptoDirectionalPaperStrategy(
            initial_cash=args.initial_cash,
            portfolio_target_roi=args.portfolio_target_roi,
            take_profit_pct=config["take_profit_pct"],
            stop_loss_pct=config["stop_loss_pct"],
            entry_notional=config.get("entry_notional", args.target_entry_notional),
            capital_fraction=config["capital_fraction"],
            min_entry_notional=config["min_entry_notional"],
            max_spread_pct=config["max_spread_pct"],
            max_entry_impact_pct=config["max_entry_impact_pct"],
            min_bid_price=config["min_bid_price"],
            max_ask_price=config["max_ask_price"],
            min_spot_move_pct=config["min_spot_move_pct"],
            lookback_observations=config["lookback_observations"],
            min_spot_observations=config["min_spot_observations"],
            exit_reversal_pct=config["exit_reversal_pct"],
            max_positions=config["max_positions"],
            max_entries_per_cycle=config["max_entries_per_cycle"],
            max_hold_cycles=config["max_hold_cycles"],
            cooldown_cycles_after_sell=config["cooldown_cycles_after_sell"],
            diagnostic_limit=config.get("diagnostic_limit", 50),
            name=f"paper_target_{name}",
        )
    if strategy_type == "crypto_interval_anchor":
        return CryptoIntervalAnchorPaperStrategy(
            initial_cash=args.initial_cash,
            portfolio_target_roi=args.portfolio_target_roi,
            take_profit_pct=config["take_profit_pct"],
            stop_loss_pct=config["stop_loss_pct"],
            entry_notional=config.get("entry_notional", args.target_entry_notional),
            capital_fraction=config["capital_fraction"],
            min_entry_notional=config["min_entry_notional"],
            max_spread_pct=config["max_spread_pct"],
            max_entry_impact_pct=config["max_entry_impact_pct"],
            min_bid_price=config["min_bid_price"],
            max_ask_price=config["max_ask_price"],
            min_anchor_move_pct=config["min_anchor_move_pct"],
            exit_reversal_pct=config["exit_reversal_pct"],
            min_net_settlement_roi=config["min_net_settlement_roi"],
            max_anchor_lag_seconds=config["max_anchor_lag_seconds"],
            min_market_age_seconds=config["min_market_age_seconds"],
            min_seconds_to_close=config["min_seconds_to_close"],
            hold_to_settlement_after_seconds=config["hold_to_settlement_after_seconds"],
            max_positions=config["max_positions"],
            max_entries_per_cycle=config["max_entries_per_cycle"],
            max_hold_cycles=config["max_hold_cycles"],
            cooldown_cycles_after_sell=config["cooldown_cycles_after_sell"],
            diagnostic_limit=config.get("diagnostic_limit", 50),
            name=f"paper_target_{name}",
        )
    if strategy_type == "crypto_interval_close_edge":
        return CryptoIntervalCloseEdgePaperStrategy(
            initial_cash=args.initial_cash,
            portfolio_target_roi=args.portfolio_target_roi,
            take_profit_pct=config["take_profit_pct"],
            stop_loss_pct=config["stop_loss_pct"],
            entry_notional=config.get("entry_notional", args.target_entry_notional),
            capital_fraction=config["capital_fraction"],
            min_entry_notional=config["min_entry_notional"],
            max_spread_pct=config["max_spread_pct"],
            max_entry_impact_pct=config["max_entry_impact_pct"],
            min_bid_price=config["min_bid_price"],
            max_ask_price=config["max_ask_price"],
            min_anchor_move_pct=config["min_anchor_move_pct"],
            exit_reversal_pct=config["exit_reversal_pct"],
            min_net_settlement_roi=config["min_net_settlement_roi"],
            max_anchor_lag_seconds=config["max_anchor_lag_seconds"],
            min_market_age_seconds=config["min_market_age_seconds"],
            min_seconds_to_close=config["min_seconds_to_close"],
            max_seconds_to_close=config["max_seconds_to_close"],
            hold_to_settlement_after_seconds=config["hold_to_settlement_after_seconds"],
            max_positions=config["max_positions"],
            max_entries_per_cycle=config["max_entries_per_cycle"],
            max_hold_cycles=config["max_hold_cycles"],
            cooldown_cycles_after_sell=config["cooldown_cycles_after_sell"],
            diagnostic_limit=config.get("diagnostic_limit", 50),
            name=f"paper_target_{name}",
        )
    if strategy_type == "crypto_interval_book_skew":
        return CryptoIntervalBookSkewPaperStrategy(
            initial_cash=args.initial_cash,
            portfolio_target_roi=args.portfolio_target_roi,
            take_profit_pct=config["take_profit_pct"],
            stop_loss_pct=config["stop_loss_pct"],
            entry_notional=config.get("entry_notional", args.target_entry_notional),
            capital_fraction=config["capital_fraction"],
            min_entry_notional=config["min_entry_notional"],
            max_spread_pct=config["max_spread_pct"],
            max_entry_impact_pct=config["max_entry_impact_pct"],
            min_bid_price=config["min_bid_price"],
            max_ask_price=config["max_ask_price"],
            min_net_settlement_roi=config["min_net_settlement_roi"],
            min_market_age_seconds=config["min_market_age_seconds"],
            min_seconds_to_close=config["min_seconds_to_close"],
            max_seconds_to_close=config["max_seconds_to_close"],
            max_positions=config["max_positions"],
            max_entries_per_cycle=config["max_entries_per_cycle"],
            max_hold_cycles=config["max_hold_cycles"],
            cooldown_cycles_after_sell=config["cooldown_cycles_after_sell"],
            diagnostic_limit=config.get("diagnostic_limit", 50),
            name=f"paper_target_{name}",
        )
    return TargetProfitPaperStrategy(
        initial_cash=args.initial_cash,
        portfolio_target_roi=args.portfolio_target_roi,
        take_profit_pct=config["take_profit_pct"],
        allow_take_profit_before_target=config["allow_take_profit_before_target"],
        stop_loss_pct=config["stop_loss_pct"],
        entry_notional=config.get("entry_notional", args.target_entry_notional),
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
        max_entries_per_cycle=config.get(
            "max_entries_per_cycle",
            getattr(args, "target_max_entries_per_cycle", 1),
        ),
        diversify_by=config["diversify_by"],
        max_positions_per_group=config["max_positions_per_group"],
        allowed_assets=_target_allowed_assets(args),
        watchlist_size=config.get("watchlist_size", getattr(args, "target_watchlist_size", 0)),
        history_change_weight=config.get(
            "history_change_weight",
            getattr(args, "target_history_change_weight", 0.0),
        ),
        entry_execution_style=config.get(
            "entry_execution_style",
            getattr(args, "target_entry_execution_style", "taker"),
        ),
        diagnostic_limit=config.get("diagnostic_limit", 50),
        name=f"paper_target_{name}",
    )


def _target_allowed_assets(args):
    raw = getattr(args, "target_allowed_assets", "") or ""
    if isinstance(raw, str):
        assets = [item.strip() for item in raw.split(",") if item.strip()]
        return assets or None
    assets = list(raw)
    return assets or None


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
            "min_momentum_observations": args.target_min_momentum_observations,
            "min_bid_improvement_pct": args.target_min_bid_improvement_pct,
            "min_mid_improvement_pct": args.target_min_mid_improvement_pct,
            "cooldown_cycles_after_sell": 1,
            "max_hold_cycles": args.target_max_hold_cycles if args.target_max_hold_cycles > 0 else 20,
            "max_hold_min_progress_pct": args.target_max_hold_min_progress_pct,
            "max_hold_cooldown_cycles": (
                args.target_max_hold_cooldown_cycles
                if args.target_max_hold_cooldown_cycles > 0
                else 10
            ),
            "max_positions": max(args.target_max_positions, 3),
            "max_entries_per_cycle": max(getattr(args, "target_max_entries_per_cycle", 1), 3),
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
            "max_entries_per_cycle": max(getattr(args, "target_max_entries_per_cycle", 1), 3),
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
            "capital_fraction": min(args.target_capital_fraction, 0.95),
            "take_profit_pct": max(args.take_profit_pct, 0.10),
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
            "min_momentum_observations": args.target_min_momentum_observations,
            "min_bid_improvement_pct": args.target_min_bid_improvement_pct,
            "min_mid_improvement_pct": args.target_min_mid_improvement_pct,
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
        "convex_basket_goal": {
            "entry_notional": (
                args.target_entry_notional
                if args.target_entry_notional > 0
                else args.initial_cash / 4.0
            ),
            "capital_fraction": 1.0,
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
                else 0.02
            ),
            "max_bid_price": (
                args.target_max_bid_price
                if args.target_max_bid_price is not None
                else 0.25
            ),
            "max_entry_mark_to_bid_loss_pct": (
                args.target_max_entry_mark_to_bid_loss_pct
                if args.target_max_entry_mark_to_bid_loss_pct is not None
                else 0.08
            ),
            "max_required_exit_distance_pct": (
                args.target_max_required_exit_distance_pct
                if args.target_max_required_exit_distance_pct is not None
                else 0.35
            ),
            "required_exit_distance_weight": max(args.target_required_exit_distance_weight, 1.0),
            "min_score": args.target_min_score if args.target_min_score is not None else -1.0,
            "min_momentum_observations": 1,
            "min_bid_improvement_pct": args.target_min_bid_improvement_pct,
            "min_mid_improvement_pct": args.target_min_mid_improvement_pct,
            "cooldown_cycles_after_sell": max(args.target_cooldown_cycles_after_sell, 2),
            "max_hold_cycles": args.target_max_hold_cycles if args.target_max_hold_cycles > 0 else 8,
            "max_hold_min_progress_pct": args.target_max_hold_min_progress_pct,
            "max_hold_cooldown_cycles": (
                args.target_max_hold_cooldown_cycles
                if args.target_max_hold_cooldown_cycles > 0
                else 8
            ),
            "max_positions": max(args.target_max_positions, 4),
            "max_entries_per_cycle": max(getattr(args, "target_max_entries_per_cycle", 1), 4),
            "diversify_by": (
                args.target_diversify_by
                if args.target_diversify_by != "none"
                else "condition"
            ),
            "max_positions_per_group": max(args.target_max_positions_per_group, 1),
            "watchlist_size": max(getattr(args, "target_watchlist_size", 0), 24),
            "history_change_weight": 3.0,
        },
        "maker_convex_basket_goal": {
            "entry_notional": (
                args.target_entry_notional
                if args.target_entry_notional > 0
                else args.initial_cash / 4.0
            ),
            "capital_fraction": 1.0,
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
                else 0.02
            ),
            "max_bid_price": (
                args.target_max_bid_price
                if args.target_max_bid_price is not None
                else 0.25
            ),
            "max_entry_mark_to_bid_loss_pct": (
                args.target_max_entry_mark_to_bid_loss_pct
                if args.target_max_entry_mark_to_bid_loss_pct is not None
                else 0.01
            ),
            "max_required_exit_distance_pct": (
                args.target_max_required_exit_distance_pct
                if args.target_max_required_exit_distance_pct is not None
                else 0.35
            ),
            "required_exit_distance_weight": max(args.target_required_exit_distance_weight, 1.0),
            "min_score": args.target_min_score if args.target_min_score is not None else -1.0,
            "min_momentum_observations": 1,
            "min_bid_improvement_pct": args.target_min_bid_improvement_pct,
            "min_mid_improvement_pct": args.target_min_mid_improvement_pct,
            "cooldown_cycles_after_sell": max(args.target_cooldown_cycles_after_sell, 2),
            "max_hold_cycles": args.target_max_hold_cycles if args.target_max_hold_cycles > 0 else 8,
            "max_hold_min_progress_pct": args.target_max_hold_min_progress_pct,
            "max_hold_cooldown_cycles": (
                args.target_max_hold_cooldown_cycles
                if args.target_max_hold_cooldown_cycles > 0
                else 8
            ),
            "max_positions": max(args.target_max_positions, 4),
            "max_entries_per_cycle": max(getattr(args, "target_max_entries_per_cycle", 1), 4),
            "diversify_by": (
                args.target_diversify_by
                if args.target_diversify_by != "none"
                else "condition"
            ),
            "max_positions_per_group": max(args.target_max_positions_per_group, 1),
            "watchlist_size": max(getattr(args, "target_watchlist_size", 0), 24),
            "history_change_weight": 3.0,
            "entry_execution_style": "maker",
        },
        "rolling_momentum_maker_goal": {
            "entry_notional": (
                args.target_entry_notional
                if args.target_entry_notional > 0
                else args.initial_cash
            ),
            "capital_fraction": 1.0,
            "take_profit_pct": max(args.take_profit_pct, 0.10),
            "allow_take_profit_before_target": True,
            "stop_loss_pct": max(args.stop_loss_pct, 0.25),
            "adaptive_entry_sizing": True,
            "min_entry_notional": max(args.target_min_entry_notional, 50.0),
            "max_spread_pct": max(args.target_max_spread_pct, 0.25),
            "max_entry_impact_pct": max(args.target_max_entry_impact_pct, 0.25),
            "min_book_imbalance": min(args.target_min_book_imbalance, -1.0),
            "min_bid_price": (
                args.target_min_bid_price
                if args.target_min_bid_price is not None
                else 0.02
            ),
            "max_bid_price": (
                args.target_max_bid_price
                if args.target_max_bid_price is not None
                else 0.60
            ),
            "max_entry_mark_to_bid_loss_pct": (
                args.target_max_entry_mark_to_bid_loss_pct
                if args.target_max_entry_mark_to_bid_loss_pct is not None
                else 0.01
            ),
            "max_required_exit_distance_pct": (
                args.target_max_required_exit_distance_pct
                if args.target_max_required_exit_distance_pct is not None
                else 0.18
            ),
            "required_exit_distance_weight": max(args.target_required_exit_distance_weight, 1.0),
            "min_score": args.target_min_score if args.target_min_score is not None else -1.0,
            "min_momentum_observations": 1,
            "min_bid_improvement_pct": min(args.target_min_bid_improvement_pct, 0.0),
            "min_mid_improvement_pct": min(args.target_min_mid_improvement_pct, 0.0),
            "cooldown_cycles_after_sell": 0,
            "max_hold_cycles": args.target_max_hold_cycles if args.target_max_hold_cycles > 0 else 4,
            "max_hold_min_progress_pct": max(args.target_max_hold_min_progress_pct, 0.10),
            "max_hold_cooldown_cycles": (
                args.target_max_hold_cooldown_cycles
                if args.target_max_hold_cooldown_cycles > 0
                else 6
            ),
            "max_positions": 1,
            "max_entries_per_cycle": 1,
            "diversify_by": "none",
            "max_positions_per_group": 0,
            "watchlist_size": max(getattr(args, "target_watchlist_size", 0), 16),
            "history_change_weight": max(getattr(args, "target_history_change_weight", 0.0), 10.0),
            "entry_execution_style": "maker",
        },
        "breakout_goal": {
            "capital_fraction": 1.0,
            "take_profit_pct": max(args.take_profit_pct, 0.10),
            "allow_take_profit_before_target": False,
            "stop_loss_pct": max(args.stop_loss_pct, 0.30),
            "adaptive_entry_sizing": True,
            "min_entry_notional": max(args.target_min_entry_notional, 5.0),
            "max_spread_pct": min(args.target_max_spread_pct, 0.05),
            "max_entry_impact_pct": min(args.target_max_entry_impact_pct, 0.05),
            "min_book_imbalance": min(args.target_min_book_imbalance, -1.0),
            "min_bid_price": (
                args.target_min_bid_price
                if args.target_min_bid_price is not None
                else 0.50
            ),
            "max_bid_price": (
                args.target_max_bid_price
                if args.target_max_bid_price is not None
                else 0.85
            ),
            "max_entry_mark_to_bid_loss_pct": (
                args.target_max_entry_mark_to_bid_loss_pct
                if args.target_max_entry_mark_to_bid_loss_pct is not None
                else 0.03
            ),
            "max_required_exit_distance_pct": (
                args.target_max_required_exit_distance_pct
                if args.target_max_required_exit_distance_pct is not None
                else 0.15
            ),
            "required_exit_distance_weight": max(args.target_required_exit_distance_weight, 10.0),
            "min_score": args.target_min_score if args.target_min_score is not None else -1.0,
            "min_momentum_observations": max(args.target_min_momentum_observations, 2),
            "min_bid_improvement_pct": max(args.target_min_bid_improvement_pct, 0.001),
            "min_mid_improvement_pct": max(args.target_min_mid_improvement_pct, 0.001),
            "cooldown_cycles_after_sell": max(args.target_cooldown_cycles_after_sell, 2),
            "max_hold_cycles": args.target_max_hold_cycles,
            "max_hold_min_progress_pct": args.target_max_hold_min_progress_pct,
            "max_hold_cooldown_cycles": args.target_max_hold_cooldown_cycles,
            "max_positions": args.target_max_positions,
            "diversify_by": args.target_diversify_by,
            "max_positions_per_group": args.target_max_positions_per_group,
            "watchlist_size": max(getattr(args, "target_watchlist_size", 0), 12),
        },
        "breakout_relaxed_goal": {
            "capital_fraction": 1.0,
            "take_profit_pct": max(args.take_profit_pct, 0.10),
            "allow_take_profit_before_target": False,
            "stop_loss_pct": max(args.stop_loss_pct, 0.30),
            "adaptive_entry_sizing": True,
            "min_entry_notional": max(args.target_min_entry_notional, 5.0),
            "max_spread_pct": min(args.target_max_spread_pct, 0.05),
            "max_entry_impact_pct": min(args.target_max_entry_impact_pct, 0.05),
            "min_book_imbalance": min(args.target_min_book_imbalance, -1.0),
            "min_bid_price": (
                args.target_min_bid_price
                if args.target_min_bid_price is not None
                else 0.50
            ),
            "max_bid_price": (
                args.target_max_bid_price
                if args.target_max_bid_price is not None
                else 0.85
            ),
            "max_entry_mark_to_bid_loss_pct": (
                args.target_max_entry_mark_to_bid_loss_pct
                if args.target_max_entry_mark_to_bid_loss_pct is not None
                else 0.03
            ),
            "max_required_exit_distance_pct": (
                args.target_max_required_exit_distance_pct
                if args.target_max_required_exit_distance_pct is not None
                else 0.15
            ),
            "required_exit_distance_weight": max(args.target_required_exit_distance_weight, 10.0),
            "min_score": args.target_min_score if args.target_min_score is not None else -1.0,
            "min_momentum_observations": max(args.target_min_momentum_observations, 2),
            "min_bid_improvement_pct": args.target_min_bid_improvement_pct,
            "min_mid_improvement_pct": args.target_min_mid_improvement_pct,
            "cooldown_cycles_after_sell": max(args.target_cooldown_cycles_after_sell, 2),
            "max_hold_cycles": args.target_max_hold_cycles,
            "max_hold_min_progress_pct": args.target_max_hold_min_progress_pct,
            "max_hold_cooldown_cycles": args.target_max_hold_cooldown_cycles,
            "max_positions": args.target_max_positions,
            "diversify_by": args.target_diversify_by,
            "max_positions_per_group": args.target_max_positions_per_group,
            "watchlist_size": max(getattr(args, "target_watchlist_size", 0), 12),
        },
        "basket_goal": {
            "entry_notional": (
                args.target_entry_notional
                if args.target_entry_notional > 0
                else args.initial_cash / 3.0
            ),
            "capital_fraction": 1.0,
            "take_profit_pct": max(args.take_profit_pct, 0.12),
            "allow_take_profit_before_target": True,
            "stop_loss_pct": max(args.stop_loss_pct, 0.30),
            "adaptive_entry_sizing": True,
            "min_entry_notional": max(args.target_min_entry_notional, 5.0),
            "max_spread_pct": min(args.target_max_spread_pct, 0.05),
            "max_entry_impact_pct": min(max(args.target_max_entry_impact_pct, 0.05), 0.08),
            "min_book_imbalance": min(args.target_min_book_imbalance, -1.0),
            "min_bid_price": (
                args.target_min_bid_price
                if args.target_min_bid_price is not None
                else 0.20
            ),
            "max_bid_price": (
                args.target_max_bid_price
                if args.target_max_bid_price is not None
                else 0.85
            ),
            "max_entry_mark_to_bid_loss_pct": (
                args.target_max_entry_mark_to_bid_loss_pct
                if args.target_max_entry_mark_to_bid_loss_pct is not None
                else 0.03
            ),
            "max_required_exit_distance_pct": (
                args.target_max_required_exit_distance_pct
                if args.target_max_required_exit_distance_pct is not None
                else 0.18
            ),
            "required_exit_distance_weight": max(args.target_required_exit_distance_weight, 3.0),
            "min_score": args.target_min_score if args.target_min_score is not None else -1.0,
            "min_momentum_observations": max(args.target_min_momentum_observations, 2),
            "min_bid_improvement_pct": args.target_min_bid_improvement_pct,
            "min_mid_improvement_pct": args.target_min_mid_improvement_pct,
            "cooldown_cycles_after_sell": max(args.target_cooldown_cycles_after_sell, 1),
            "max_hold_cycles": args.target_max_hold_cycles if args.target_max_hold_cycles > 0 else 12,
            "max_hold_min_progress_pct": args.target_max_hold_min_progress_pct,
            "max_hold_cooldown_cycles": (
                args.target_max_hold_cooldown_cycles
                if args.target_max_hold_cooldown_cycles > 0
                else 6
            ),
            "max_positions": max(args.target_max_positions, 3),
            "max_entries_per_cycle": max(getattr(args, "target_max_entries_per_cycle", 1), 3),
            "diversify_by": (
                args.target_diversify_by
                if args.target_diversify_by != "none"
                else "condition"
            ),
            "max_positions_per_group": max(args.target_max_positions_per_group, 1),
            "watchlist_size": max(getattr(args, "target_watchlist_size", 0), 18),
            "history_change_weight": 2.0,
        },
        "low_distance_goal": {
            "capital_fraction": 1.0,
            "take_profit_pct": max(args.take_profit_pct, 0.10),
            "allow_take_profit_before_target": False,
            "stop_loss_pct": max(args.stop_loss_pct, 0.30),
            "adaptive_entry_sizing": True,
            "min_entry_notional": max(args.target_min_entry_notional, 5.0),
            "max_spread_pct": min(args.target_max_spread_pct, 0.05),
            "max_entry_impact_pct": min(args.target_max_entry_impact_pct, 0.05),
            "min_book_imbalance": min(args.target_min_book_imbalance, -1.0),
            "min_bid_price": (
                args.target_min_bid_price
                if args.target_min_bid_price is not None
                else 0.50
            ),
            "max_bid_price": (
                args.target_max_bid_price
                if args.target_max_bid_price is not None
                else 0.85
            ),
            "max_entry_mark_to_bid_loss_pct": (
                args.target_max_entry_mark_to_bid_loss_pct
                if args.target_max_entry_mark_to_bid_loss_pct is not None
                else 0.03
            ),
            "max_required_exit_distance_pct": (
                args.target_max_required_exit_distance_pct
                if args.target_max_required_exit_distance_pct is not None
                else 0.15
            ),
            "required_exit_distance_weight": max(args.target_required_exit_distance_weight, 10.0),
            "min_score": args.target_min_score if args.target_min_score is not None else -1.0,
            "min_momentum_observations": 1,
            "min_bid_improvement_pct": min(args.target_min_bid_improvement_pct, 0.0),
            "min_mid_improvement_pct": min(args.target_min_mid_improvement_pct, 0.0),
            "cooldown_cycles_after_sell": max(args.target_cooldown_cycles_after_sell, 2),
            "max_hold_cycles": args.target_max_hold_cycles,
            "max_hold_min_progress_pct": args.target_max_hold_min_progress_pct,
            "max_hold_cooldown_cycles": args.target_max_hold_cooldown_cycles,
            "max_positions": args.target_max_positions,
            "diversify_by": args.target_diversify_by,
            "max_positions_per_group": args.target_max_positions_per_group,
        },
        "momentum_scalper_goal": {
            "strategy_type": "momentum_scalper",
            "entry_notional": (
                args.target_entry_notional
                if args.target_entry_notional > 0
                else args.initial_cash / 2.0
            ),
            "capital_fraction": min(max(args.target_capital_fraction, 0.50), 0.80),
            "take_profit_pct": min(args.take_profit_pct, 0.04),
            "stop_loss_pct": max(args.stop_loss_pct, 0.04),
            "min_entry_notional": max(args.target_min_entry_notional, 5.0),
            "max_spread_pct": min(max(args.target_max_spread_pct, 0.04), 0.08),
            "min_spread_pct": 0.0,
            "max_entry_impact_pct": min(max(args.target_max_entry_impact_pct, 0.05), 0.08),
            "min_book_imbalance": min(args.target_min_book_imbalance, -0.25),
            "min_bid_price": (
                args.target_min_bid_price
                if args.target_min_bid_price is not None
                else 0.10
            ),
            "max_bid_price": (
                args.target_max_bid_price
                if args.target_max_bid_price is not None
                else 0.90
            ),
            "min_momentum_observations": max(args.target_min_momentum_observations, 2),
            "min_bid_improvement_pct": max(args.target_min_bid_improvement_pct, 0.001),
            "min_mid_improvement_pct": max(args.target_min_mid_improvement_pct, 0.001),
            "max_spread_widen_pct": max(args.target_max_spread_widen_pct, 0.02),
            "cooldown_cycles_after_sell": max(args.target_cooldown_cycles_after_sell, 2),
            "max_hold_cycles": args.target_max_hold_cycles if args.target_max_hold_cycles > 0 else 18,
            "max_hold_min_progress_pct": args.target_max_hold_min_progress_pct,
            "max_hold_cooldown_cycles": (
                args.target_max_hold_cooldown_cycles
                if args.target_max_hold_cooldown_cycles > 0
                else 4
            ),
            "max_positions": max(args.target_max_positions, 2),
            "max_entries_per_cycle": max(getattr(args, "target_max_entries_per_cycle", 1), 1),
            "entry_execution_style": "taker",
            "maker_exit": False,
        },
        "crypto_directional_goal": {
            "strategy_type": "crypto_directional",
            "entry_notional": (
                args.target_entry_notional
                if args.target_entry_notional > 0
                else args.initial_cash * 0.35
            ),
            "capital_fraction": min(max(args.target_capital_fraction, 0.35), 0.70),
            "take_profit_pct": min(args.take_profit_pct, 0.03),
            "stop_loss_pct": max(args.stop_loss_pct, 0.02),
            "min_entry_notional": max(args.target_min_entry_notional, 5.0),
            "max_spread_pct": min(max(args.target_max_spread_pct, 0.03), 0.06),
            "max_entry_impact_pct": min(max(args.target_max_entry_impact_pct, 0.02), 0.04),
            "min_bid_price": (
                args.target_min_bid_price
                if args.target_min_bid_price is not None
                else 0.05
            ),
            "max_ask_price": (
                args.target_max_bid_price
                if args.target_max_bid_price is not None
                else 0.90
            ),
            "min_spot_move_pct": 0.0006,
            "lookback_observations": 2,
            "min_spot_observations": 2,
            "exit_reversal_pct": 0.0004,
            "cooldown_cycles_after_sell": max(args.target_cooldown_cycles_after_sell, 2),
            "max_hold_cycles": args.target_max_hold_cycles if args.target_max_hold_cycles > 0 else 36,
            "max_positions": max(args.target_max_positions, 2),
            "max_entries_per_cycle": max(getattr(args, "target_max_entries_per_cycle", 1), 1),
        },
        "crypto_interval_anchor_goal": {
            "strategy_type": "crypto_interval_anchor",
            "entry_notional": (
                args.target_entry_notional
                if args.target_entry_notional > 0
                else args.initial_cash * 0.45
            ),
            "capital_fraction": min(max(args.target_capital_fraction, 0.45), 0.80),
            "take_profit_pct": min(args.take_profit_pct, 0.04),
            "stop_loss_pct": max(args.stop_loss_pct, 0.10),
            "min_entry_notional": max(args.target_min_entry_notional, 5.0),
            "max_spread_pct": min(max(args.target_max_spread_pct, 0.04), 0.08),
            "max_entry_impact_pct": min(max(args.target_max_entry_impact_pct, 0.02), 0.04),
            "min_bid_price": (
                args.target_min_bid_price
                if args.target_min_bid_price is not None
                else 0.03
            ),
            "max_ask_price": (
                args.target_max_bid_price
                if args.target_max_bid_price is not None
                else 0.95
            ),
            "min_anchor_move_pct": 0.0010,
            "exit_reversal_pct": 0.0004,
            "min_net_settlement_roi": 0.02,
            "max_anchor_lag_seconds": 45,
            "min_market_age_seconds": 20,
            "min_seconds_to_close": 15,
            "hold_to_settlement_after_seconds": 210,
            "cooldown_cycles_after_sell": max(args.target_cooldown_cycles_after_sell, 1),
            "max_hold_cycles": args.target_max_hold_cycles if args.target_max_hold_cycles > 0 else 96,
            "max_positions": max(args.target_max_positions, 2),
            "max_entries_per_cycle": max(getattr(args, "target_max_entries_per_cycle", 1), 1),
        },
        "crypto_interval_close_edge_goal": {
            "strategy_type": "crypto_interval_close_edge",
            "entry_notional": (
                args.target_entry_notional
                if args.target_entry_notional > 0
                else args.initial_cash * 0.40
            ),
            "capital_fraction": min(max(args.target_capital_fraction, 0.40), 0.75),
            "take_profit_pct": min(args.take_profit_pct, 0.02),
            "stop_loss_pct": max(args.stop_loss_pct, 0.20),
            "min_entry_notional": max(args.target_min_entry_notional, 5.0),
            "max_spread_pct": min(max(args.target_max_spread_pct, 0.04), 0.08),
            "max_entry_impact_pct": min(max(args.target_max_entry_impact_pct, 0.02), 0.04),
            "min_bid_price": (
                args.target_min_bid_price
                if args.target_min_bid_price is not None
                else 0.03
            ),
            "max_ask_price": (
                args.target_max_bid_price
                if args.target_max_bid_price is not None
                else 0.95
            ),
            "min_anchor_move_pct": 0.0005,
            "exit_reversal_pct": 0.0003,
            "min_net_settlement_roi": 0.04,
            "max_anchor_lag_seconds": 90,
            "min_market_age_seconds": 210,
            "min_seconds_to_close": 5,
            "max_seconds_to_close": 75,
            "hold_to_settlement_after_seconds": 0,
            "cooldown_cycles_after_sell": max(args.target_cooldown_cycles_after_sell, 1),
            "max_hold_cycles": args.target_max_hold_cycles if args.target_max_hold_cycles > 0 else 96,
            "max_positions": max(args.target_max_positions, 2),
            "max_entries_per_cycle": max(getattr(args, "target_max_entries_per_cycle", 1), 1),
        },
        "crypto_interval_book_skew_goal": {
            "strategy_type": "crypto_interval_book_skew",
            "entry_notional": (
                args.target_entry_notional
                if args.target_entry_notional > 0
                else args.initial_cash * 0.50
            ),
            "capital_fraction": min(max(args.target_capital_fraction, 0.50), 0.80),
            "take_profit_pct": min(args.take_profit_pct, 0.03),
            "stop_loss_pct": max(args.stop_loss_pct, 0.35),
            "min_entry_notional": max(args.target_min_entry_notional, 5.0),
            "max_spread_pct": min(max(args.target_max_spread_pct, 0.04), 0.08),
            "max_entry_impact_pct": min(max(args.target_max_entry_impact_pct, 0.02), 0.04),
            "min_bid_price": (
                args.target_min_bid_price
                if args.target_min_bid_price is not None
                else 0.58
            ),
            "max_ask_price": (
                args.target_max_bid_price
                if args.target_max_bid_price is not None
                else 0.88
            ),
            "min_net_settlement_roi": 0.08,
            "min_market_age_seconds": 20,
            "min_seconds_to_close": 20,
            "max_seconds_to_close": 240,
            "cooldown_cycles_after_sell": max(args.target_cooldown_cycles_after_sell, 1),
            "max_hold_cycles": args.target_max_hold_cycles if args.target_max_hold_cycles > 0 else 96,
            "max_positions": max(args.target_max_positions, 2),
            "max_entries_per_cycle": max(getattr(args, "target_max_entries_per_cycle", 1), 1),
        },
        "spread_capture_maker_goal": {
            "strategy_type": "spread_capture_maker",
            "entry_notional": (
                args.target_entry_notional
                if args.target_entry_notional > 0
                else args.initial_cash * 0.25
            ),
            "capital_fraction": min(max(args.target_capital_fraction, 0.25), 0.50),
            "take_profit_pct": min(args.take_profit_pct, 0.02),
            "stop_loss_pct": max(args.stop_loss_pct, 0.04),
            "min_entry_notional": max(args.target_min_entry_notional, 5.0),
            "max_spread_pct": max(args.target_max_spread_pct, 0.30),
            "min_spread_pct": 0.02,
            "max_entry_impact_pct": 0.0,
            "min_book_imbalance": min(args.target_min_book_imbalance, -0.50),
            "min_bid_price": (
                args.target_min_bid_price
                if args.target_min_bid_price is not None
                else 0.05
            ),
            "max_bid_price": (
                args.target_max_bid_price
                if args.target_max_bid_price is not None
                else 0.90
            ),
            "min_momentum_observations": max(args.target_min_momentum_observations, 2),
            "min_bid_improvement_pct": min(args.target_min_bid_improvement_pct, 0.0),
            "min_mid_improvement_pct": min(args.target_min_mid_improvement_pct, 0.0),
            "max_spread_widen_pct": max(args.target_max_spread_widen_pct, 0.10),
            "cooldown_cycles_after_sell": max(args.target_cooldown_cycles_after_sell, 2),
            "max_hold_cycles": args.target_max_hold_cycles if args.target_max_hold_cycles > 0 else 12,
            "max_hold_min_progress_pct": args.target_max_hold_min_progress_pct,
            "max_hold_cooldown_cycles": (
                args.target_max_hold_cooldown_cycles
                if args.target_max_hold_cooldown_cycles > 0
                else 4
            ),
            "max_positions": 1,
            "max_entries_per_cycle": 1,
            "entry_execution_style": "maker",
            "maker_exit": True,
        },
        "maker_rebate_rotation_goal": {
            "strategy_type": "maker_rebate_rotation",
            "entry_notional": (
                args.target_entry_notional
                if args.target_entry_notional > 0
                else args.initial_cash * 0.20
            ),
            "capital_fraction": min(max(args.target_capital_fraction, 0.20), 0.45),
            "take_profit_pct": min(args.take_profit_pct, 0.006),
            "stop_loss_pct": max(args.stop_loss_pct, 0.06),
            "min_entry_notional": max(args.target_min_entry_notional, 5.0),
            "max_spread_pct": max(args.target_max_spread_pct, 0.25),
            "min_spread_pct": 0.0,
            "max_entry_impact_pct": 0.0,
            "min_book_imbalance": min(args.target_min_book_imbalance, -1.0),
            "min_bid_price": (
                args.target_min_bid_price
                if args.target_min_bid_price is not None
                else 0.05
            ),
            "max_bid_price": (
                args.target_max_bid_price
                if args.target_max_bid_price is not None
                else 0.90
            ),
            "min_momentum_observations": 1,
            "min_bid_improvement_pct": min(args.target_min_bid_improvement_pct, 0.0),
            "min_mid_improvement_pct": min(args.target_min_mid_improvement_pct, 0.0),
            "max_spread_widen_pct": max(args.target_max_spread_widen_pct, 0.10),
            "cooldown_cycles_after_sell": max(args.target_cooldown_cycles_after_sell, 1),
            "max_hold_cycles": args.target_max_hold_cycles if args.target_max_hold_cycles > 0 else 10,
            "max_hold_min_progress_pct": 0.0,
            "max_hold_cooldown_cycles": (
                args.target_max_hold_cooldown_cycles
                if args.target_max_hold_cooldown_cycles > 0
                else 2
            ),
            "max_positions": 2,
            "max_entries_per_cycle": 1,
            "min_round_trip_edge_pct": 0.004,
            "min_maker_rebate_pct": 0.0,
            "min_touch_depth_notional": 25.0,
        },
        "outcome_basket_arb_goal": {
            "strategy_type": "outcome_basket_arb",
            "entry_notional": (
                args.target_entry_notional
                if args.target_entry_notional > 0
                else args.initial_cash * 0.25
            ),
            "capital_fraction": min(max(args.target_capital_fraction, 0.25), 0.50),
            "take_profit_pct": min(args.take_profit_pct, 0.04),
            "stop_loss_pct": max(args.stop_loss_pct, 0.08),
            "min_entry_notional": max(args.target_min_entry_notional, 5.0),
            "min_settlement_roi": 0.02,
            "min_mark_roi": -0.08,
            "max_outcomes": 2,
            "cooldown_cycles_after_sell": max(args.target_cooldown_cycles_after_sell, 12),
            "max_hold_cycles": args.target_max_hold_cycles if args.target_max_hold_cycles > 0 else 72,
            "max_positions": max(args.target_max_positions, 2),
            "max_entries_per_cycle": max(getattr(args, "target_max_entries_per_cycle", 1), 1),
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
    selected = []
    unknown = []
    for name in requested:
        if name in configs:
            selected.append((name, configs[name]))
            continue
        expanded = _expanded_target_variant_group(args, name, configs)
        if expanded is None:
            unknown.append(name)
        else:
            selected.extend(expanded)
    if unknown:
        raise ValueError(f"unknown target variants: {', '.join(unknown)}")
    if not selected:
        raise ValueError("at least one target variant is required")
    return selected


def _expanded_target_variant_group(args, name: str, base_configs: dict):
    if name == "strategy_v1_selected":
        return _strategy_v1_selected_grid(args, base_configs)
    if name == "momentum_scalper_grid":
        return _momentum_scalper_grid(args, base_configs["momentum_scalper_goal"])
    if name == "crypto_directional_grid":
        return _crypto_directional_grid(args, base_configs["crypto_directional_goal"])
    if name == "crypto_interval_anchor_grid":
        return _crypto_interval_anchor_grid(args, base_configs["crypto_interval_anchor_goal"])
    if name == "crypto_interval_close_edge_grid":
        return _crypto_interval_close_edge_grid(args, base_configs["crypto_interval_close_edge_goal"])
    if name == "crypto_interval_book_skew_grid":
        return _crypto_interval_book_skew_grid(args, base_configs["crypto_interval_book_skew_goal"])
    if name == "spread_capture_maker_grid":
        return _spread_capture_maker_grid(args, base_configs["spread_capture_maker_goal"])
    if name == "maker_rebate_rotation_grid":
        return _maker_rebate_rotation_grid(args, base_configs["maker_rebate_rotation_goal"])
    if name == "outcome_basket_arb_grid":
        return _outcome_basket_arb_grid(args, base_configs["outcome_basket_arb_goal"])
    if name == "online_goal_grid":
        return (
            _momentum_scalper_grid(args, base_configs["momentum_scalper_goal"])
            + _crypto_directional_grid(args, base_configs["crypto_directional_goal"])
            + _crypto_interval_anchor_grid(args, base_configs["crypto_interval_anchor_goal"])
            + _crypto_interval_close_edge_grid(args, base_configs["crypto_interval_close_edge_goal"])
            + _crypto_interval_book_skew_grid(args, base_configs["crypto_interval_book_skew_goal"])
            + _spread_capture_maker_grid(args, base_configs["spread_capture_maker_goal"])
            + _maker_rebate_rotation_grid(args, base_configs["maker_rebate_rotation_goal"])
            + _outcome_basket_arb_grid(args, base_configs["outcome_basket_arb_goal"])
        )
    return None


def _strategy_v1_selected_grid(args, base_configs: dict) -> list:
    anchor = _select_numbered_grid(
        _crypto_interval_anchor_grid(args, base_configs["crypto_interval_anchor_goal"]),
        "crypto_interval_anchor_grid",
        STRATEGY_V1_ANCHOR_GRID_INDEXES,
    )
    book_skew = _select_numbered_grid(
        _crypto_interval_book_skew_grid(args, base_configs["crypto_interval_book_skew_goal"]),
        "crypto_interval_book_skew_grid",
        STRATEGY_V1_BOOK_SKEW_GRID_INDEXES,
    )
    return anchor + book_skew


def _select_numbered_grid(variants: list, prefix: str, indexes: tuple) -> list:
    wanted = {f"{prefix}_{index:02d}" for index in indexes}
    selected = [(name, config) for name, config in variants if name in wanted]
    if len(selected) != len(wanted):
        raise ValueError(f"strategy-v1 selection is out of sync for {prefix}")
    return selected


def _momentum_scalper_grid(args, base_config: dict) -> list:
    variants = []
    index = 1
    for capital_fraction in (0.30, 0.50, 0.70):
        for take_profit_pct in (0.015, 0.03):
            for min_improvement in (0.001, 0.003):
                config = dict(base_config)
                config.update(
                    {
                        "capital_fraction": capital_fraction,
                        "take_profit_pct": take_profit_pct,
                        "stop_loss_pct": max(0.025, take_profit_pct * 1.5),
                        "min_bid_improvement_pct": min_improvement,
                        "min_mid_improvement_pct": min_improvement,
                        "max_spread_pct": 0.03,
                        "max_positions": max(2, getattr(args, "target_max_positions", 1)),
                        "max_entries_per_cycle": max(1, min(2, getattr(args, "target_max_entries_per_cycle", 1))),
                        "max_hold_cycles": 12 if take_profit_pct <= 0.015 else 18,
                        "diagnostic_limit": 5,
                    }
                )
                variants.append((f"momentum_scalper_grid_{index:02d}", config))
                index += 1
    return variants


def _spread_capture_maker_grid(args, base_config: dict) -> list:
    variants = []
    index = 1
    for min_spread_pct in (0.01, 0.02, 0.04):
        for capital_fraction in (0.20, 0.35, 0.65):
            for max_hold_cycles in (12, 24):
                for max_positions in (1, 3):
                    config = dict(base_config)
                    config.update(
                        {
                            "capital_fraction": capital_fraction,
                            "take_profit_pct": 0.003
                            if min_spread_pct <= 0.01
                            else 0.005
                            if min_spread_pct <= 0.02
                            else 0.01,
                            "stop_loss_pct": 0.06,
                            "min_spread_pct": min_spread_pct,
                            "max_spread_pct": max(0.20, min_spread_pct * 8.0),
                            "max_hold_cycles": max_hold_cycles,
                            "max_hold_min_progress_pct": 0.05,
                            "max_positions": max_positions,
                            "max_entries_per_cycle": 1 if max_positions == 1 else 2,
                            "min_momentum_observations": 1,
                            "diagnostic_limit": 5,
                        }
                    )
                    variants.append((f"spread_capture_maker_grid_{index:02d}", config))
                    index += 1
    return variants


def _maker_rebate_rotation_grid(args, base_config: dict) -> list:
    variants = []
    index = 1
    for min_bid_price in (0.25, 0.40):
        for min_round_trip_edge_pct in (0.006, 0.012, 0.020):
            for max_positions in (2, 4):
                config = dict(base_config)
                config.update(
                    {
                        "capital_fraction": 0.25,
                        "take_profit_pct": 0.004 if min_round_trip_edge_pct <= 0.012 else 0.006,
                        "stop_loss_pct": 0.06,
                        "min_bid_price": min_bid_price,
                        "max_spread_pct": 0.12,
                        "min_spread_pct": 0.0,
                        "max_hold_cycles": 10,
                        "max_hold_min_progress_pct": 0.0,
                        "max_positions": max_positions,
                        "max_entries_per_cycle": 1 if max_positions == 2 else 2,
                        "min_round_trip_edge_pct": min_round_trip_edge_pct,
                        "min_maker_rebate_pct": 0.0,
                        "min_touch_depth_notional": 50.0,
                        "diagnostic_limit": 5,
                    }
                )
                variants.append((f"maker_rebate_rotation_grid_{index:02d}", config))
                index += 1
    return variants


def _crypto_directional_grid(args, base_config: dict) -> list:
    variants = []
    index = 1
    for min_spot_move_pct in (0.0002, 0.0004, 0.0007, 0.0010):
        for take_profit_pct in (0.015, 0.03):
            for lookback_observations in (1, 2, 4):
                config = dict(base_config)
                config.update(
                    {
                        "min_spot_move_pct": min_spot_move_pct,
                        "take_profit_pct": take_profit_pct,
                        "stop_loss_pct": max(0.015, take_profit_pct * 0.8),
                        "lookback_observations": lookback_observations,
                        "min_spot_observations": max(2, lookback_observations + 1),
                        "exit_reversal_pct": min_spot_move_pct * 0.75,
                        "capital_fraction": 0.25 if min_spot_move_pct <= 0.0004 else 0.35,
                        "max_spread_pct": 0.04,
                        "max_entry_impact_pct": 0.03,
                        "max_hold_cycles": 24 if take_profit_pct <= 0.015 else 36,
                        "diagnostic_limit": 5,
                    }
                )
                variants.append((f"crypto_directional_grid_{index:02d}", config))
                index += 1
    return variants


def _crypto_interval_anchor_grid(args, base_config: dict) -> list:
    variants = []
    index = 1
    for min_anchor_move_pct in (0.0002, 0.0005, 0.0010, 0.0015, 0.0020):
        for capital_fraction in (0.35, 0.60):
            for min_net_settlement_roi in (0.02, 0.08):
                for max_anchor_lag_seconds in (45, 150, 180):
                    config = dict(base_config)
                    config.update(
                        {
                            "min_anchor_move_pct": min_anchor_move_pct,
                            "capital_fraction": capital_fraction,
                            "min_net_settlement_roi": min_net_settlement_roi,
                            "take_profit_pct": 0.025 if min_net_settlement_roi <= 0.02 else 0.04,
                            "stop_loss_pct": 0.12,
                            "max_spread_pct": 0.08,
                            "max_entry_impact_pct": 0.04,
                            "max_anchor_lag_seconds": max_anchor_lag_seconds,
                            "min_market_age_seconds": 20,
                            "min_seconds_to_close": 15,
                            "hold_to_settlement_after_seconds": 210,
                            "max_hold_cycles": 96,
                            "diagnostic_limit": 5,
                        }
                    )
                    variants.append((f"crypto_interval_anchor_grid_{index:02d}", config))
                    index += 1
    return variants


def _crypto_interval_close_edge_grid(args, base_config: dict) -> list:
    variants = []
    index = 1
    for min_anchor_move_pct in (0.0002, 0.0005, 0.0010):
        for capital_fraction in (0.40, 0.70):
            for min_net_settlement_roi in (0.03, 0.08):
                for max_seconds_to_close in (45, 75):
                    for max_anchor_lag_seconds in (60, 180):
                        config = dict(base_config)
                        config.update(
                            {
                                "min_anchor_move_pct": min_anchor_move_pct,
                                "capital_fraction": capital_fraction,
                                "min_net_settlement_roi": min_net_settlement_roi,
                                "max_seconds_to_close": max_seconds_to_close,
                                "max_anchor_lag_seconds": max_anchor_lag_seconds,
                                "take_profit_pct": 0.015 if min_net_settlement_roi <= 0.03 else 0.02,
                                "stop_loss_pct": 0.20,
                                "max_spread_pct": 0.08,
                                "max_entry_impact_pct": 0.04,
                                "min_market_age_seconds": 210,
                                "min_seconds_to_close": 5,
                                "hold_to_settlement_after_seconds": 0,
                                "max_hold_cycles": 96,
                                "diagnostic_limit": 5,
                            }
                        )
                        variants.append((f"crypto_interval_close_edge_grid_{index:02d}", config))
                        index += 1
    return variants


def _crypto_interval_book_skew_grid(args, base_config: dict) -> list:
    variants = []
    index = 1
    for min_bid_price in (0.50, 0.58, 0.65, 0.72):
        for max_ask_price in (0.84, 0.90):
            for min_net_settlement_roi in (0.02, 0.06, 0.12):
                for max_seconds_to_close in (180, 240, 300):
                    config = dict(base_config)
                    config.update(
                        {
                            "min_bid_price": min_bid_price,
                            "max_ask_price": max_ask_price,
                            "min_net_settlement_roi": min_net_settlement_roi,
                            "max_seconds_to_close": max_seconds_to_close,
                            "capital_fraction": 0.70 if min_bid_price >= 0.65 else 0.55,
                            "take_profit_pct": 0.015
                            if min_net_settlement_roi <= 0.02
                            else 0.02
                            if min_net_settlement_roi <= 0.06
                            else 0.03,
                            "stop_loss_pct": 0.35,
                            "max_spread_pct": 0.08,
                            "max_entry_impact_pct": 0.04,
                            "min_market_age_seconds": 20,
                            "min_seconds_to_close": 20,
                            "max_hold_cycles": 96,
                            "diagnostic_limit": 5,
                        }
                    )
                    variants.append((f"crypto_interval_book_skew_grid_{index:02d}", config))
                    index += 1
    return variants


def _outcome_basket_arb_grid(args, base_config: dict) -> list:
    variants = []
    index = 1
    for min_settlement_roi in (0.0, 0.01, 0.02, 0.04):
        for min_mark_roi in (-0.15, -0.08):
            config = dict(base_config)
            config.update(
                {
                    "min_settlement_roi": min_settlement_roi,
                    "min_mark_roi": min_mark_roi,
                    "take_profit_pct": 0.02 if min_settlement_roi <= 0.01 else 0.04,
                    "stop_loss_pct": 0.10,
                    "max_hold_cycles": 72,
                    "diagnostic_limit": 5,
                }
            )
            variants.append((f"outcome_basket_arb_grid_{index:02d}", config))
            index += 1
    return variants
