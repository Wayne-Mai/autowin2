from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
from typing import List
from uuid import uuid4

from .benchmark import (
    benchmark_markdown_report,
    load_fill_scenarios,
    parse_csv_names,
    run_replay_benchmark,
    write_benchmark_outputs,
)
from .client import PublicPolymarketClient, leaderboard_pages
from .dashboard import serve_dashboard
from .engines import paper_engine, replay_backtest_engine
from .marketdata import order_book_from_clob, token_ids_from_market
from .models import Quote, TraderTrade
from .online_status import format_online_goal_status, online_goal_status_from_path
from .opportunity import (
    scan_paired_outcome_opportunities,
    score_adaptive_target_opportunity,
    score_target_opportunity,
    target_entry_notional,
)
from .paper import PaperRunner
from .recording import (
    RecordedMarketDataCollector,
    load_recording,
    record_market_snapshots,
    save_recording,
)
from .report import markdown_report
from .simulator import ConservativeFillModel, LatencyModel, MarketRules, PolymarketFeeModel, ReplaySimulator
from .storage import (
    connect,
    init_db,
    insert_leaderboard,
    insert_order_books,
    insert_quotes,
    insert_trades,
    upsert_paper_run,
)
from .strategies.paper import (
    DEFAULT_TARGET_VARIANTS_ARG,
    TARGET_VARIANT_HELP,
    default_paper_strategies,
    sweep_target_opportunities,
    target_strategy_from_config,
    target_strategy_from_sweep_result,
    target_sweep_configs,
    target_variant_configs,
)
from .strategies.replay import default_replay_strategies
from .target_runner import run_until_target
from .verification import verify_online_goal_from_path, verify_target_run_from_path


SWEEP_UNIQUE_RAW_MULTIPLIER = 200


def _add_history_args(parser) -> None:
    parser.add_argument("--history-window-seconds", type=int, default=0)
    parser.add_argument("--history-interval", default="1h")
    parser.add_argument("--history-min-change-pct", type=float, default=None)
    parser.add_argument("--history-candidate-assets", type=int, default=0)
    parser.add_argument("--history-cache-seconds", type=int, default=60)
    parser.add_argument("--history-min-bid-price", type=float, default=None)
    parser.add_argument("--history-max-bid-price", type=float, default=None)
    parser.add_argument("--history-max-spread-pct", type=float, default=None)
    parser.add_argument(
        "--history-max-queries",
        type=int,
        default=0,
        help="Maximum prices-history requests per collection cycle; 0 means unbounded",
    )


def _add_market_selection_args(parser) -> None:
    parser.add_argument(
        "--market-pages",
        type=int,
        default=1,
        help="Number of paginated Gamma market pages to scan before keyword selection",
    )
    parser.add_argument(
        "--market-filter-keywords",
        default="",
        help="Comma-separated keywords; only matching market title/slug/outcome/category are kept",
    )
    parser.add_argument(
        "--market-prefer-keywords",
        default="",
        help="Comma-separated keywords; matching markets are ranked before other markets",
    )


def _add_asset_scope_args(parser) -> None:
    parser.add_argument("--pin-assets", default="", help="Comma-separated token ids to always refresh")
    parser.add_argument("--target-allowed-assets", default="", help="Comma-separated token ids target agents may trade")
    parser.add_argument(
        "--pinned-only-after-entry",
        action="store_true",
        help="After any target agent has a position or pending order, only refresh pinned assets",
    )
    parser.add_argument(
        "--pinned-only-after-watchlist",
        action="store_true",
        help="After any target agent has watched candidates, only refresh pinned/watchlist assets",
    )
    parser.add_argument(
        "--pinned-watchlist-rescan-cycles",
        type=int,
        default=0,
        help="When pinned-only-after-watchlist is active, do a full scan every N collection cycles; 0 disables rescans",
    )


def _add_settlement_args(parser) -> None:
    parser.add_argument(
        "--settlement-check-seconds",
        type=int,
        default=60,
        help="Seconds between public Gamma resolution checks per condition; 0 checks every cycle, negative disables",
    )


def _add_maker_fill_args(parser) -> None:
    parser.add_argument(
        "--maker-fill-mode",
        choices=("optimistic", "queue_proxy", "probabilistic_queue"),
        default="optimistic",
        help="Maker fill proxy: optimistic preserves the legacy behavior; queue modes require queue decay first",
    )
    parser.add_argument(
        "--maker-queue-ahead-fraction",
        type=float,
        default=1.0,
        help="Visible top-of-book queue assumed ahead of our maker order in queue modes",
    )
    parser.add_argument(
        "--maker-queue-decay",
        type=float,
        default=0.5,
        help="Per-attempt queue-ahead decay in queue modes",
    )
    parser.add_argument(
        "--maker-fill-probability",
        type=float,
        default=1.0,
        help="Extra deterministic fill probability multiplier for probabilistic_queue mode",
    )
    parser.add_argument("--maker-seed", type=int, default=0)
    parser.add_argument(
        "--maker-max-order-age-attempts",
        type=int,
        default=0,
        help="Expire unfilled maker orders after this many book attempts; 0 disables expiry",
    )
    parser.add_argument(
        "--maker-cancel-on-price-move",
        action="store_true",
        help="Mark maker orders missed when the touch moves away from the limit before filling",
    )
    parser.add_argument(
        "--maker-adverse-fill-on-price-move",
        action="store_true",
        help="Fill maker orders at the limit when the next book has moved through the limit",
    )
    parser.add_argument(
        "--maker-adverse-fill-fraction",
        type=float,
        default=1.0,
        help="Fraction of target notional/shares filled by the adverse-selection price-move proxy",
    )


def _maker_fill_kwargs(args) -> dict:
    return {
        "maker_fill_mode": getattr(args, "maker_fill_mode", "optimistic"),
        "maker_queue_ahead_fraction": getattr(args, "maker_queue_ahead_fraction", 1.0),
        "maker_queue_decay": getattr(args, "maker_queue_decay", 0.5),
        "maker_fill_probability": getattr(args, "maker_fill_probability", 1.0),
        "maker_seed": getattr(args, "maker_seed", 0),
        "maker_max_order_age_attempts": getattr(args, "maker_max_order_age_attempts", 0),
        "maker_cancel_on_price_move": getattr(args, "maker_cancel_on_price_move", False),
        "maker_adverse_fill_on_price_move": getattr(args, "maker_adverse_fill_on_price_move", False),
        "maker_adverse_fill_fraction": getattr(args, "maker_adverse_fill_fraction", 1.0),
    }


TARGET_REPLAY_DEFAULTS = {
    "portfolio_target_roi": 0.10,
    "take_profit_pct": 0.10,
    "target_allow_take_profit_before_target": False,
    "stop_loss_pct": 0.03,
    "target_entry_notional": 0.0,
    "target_entry_execution_style": "taker",
    "target_capital_fraction": 0.95,
    "target_adaptive_entry_sizing": False,
    "target_min_entry_notional": 1.0,
    "target_max_spread_pct": 0.05,
    "target_max_entry_impact_pct": 0.05,
    "target_max_exit_price": 0.99,
    "target_min_book_imbalance": 0.05,
    "target_depth_window_pct": 0.03,
    "target_imbalance_weight": 0.10,
    "target_min_bid_price": None,
    "target_max_bid_price": None,
    "target_max_entry_mark_to_bid_loss_pct": None,
    "target_max_required_exit_distance_pct": None,
    "target_required_exit_distance_weight": 0.0,
    "target_min_score": None,
    "target_history_change_weight": 0.0,
    "target_min_momentum_observations": 2,
    "target_min_bid_improvement_pct": 0.001,
    "target_min_mid_improvement_pct": 0.001,
    "target_max_spread_widen_pct": 0.01,
    "target_cooldown_cycles_after_sell": 3,
    "target_max_hold_cycles": 0,
    "target_max_hold_min_progress_pct": 0.0,
    "target_max_hold_cooldown_cycles": 0,
    "target_max_positions": 1,
    "target_max_entries_per_cycle": 1,
    "target_diversify_by": "none",
    "target_max_positions_per_group": 0,
    "target_watchlist_size": 0,
    "target_variants": DEFAULT_TARGET_VARIANTS_ARG,
    "target_allowed_assets": "",
}


def _add_recording_target_args(parser) -> None:
    parser.add_argument("--portfolio-target-roi", type=float, default=0.10)
    parser.add_argument("--take-profit-pct", type=float, default=0.10)
    parser.add_argument("--target-allow-take-profit-before-target", action="store_true")
    parser.add_argument("--stop-loss-pct", type=float, default=0.03)
    parser.add_argument("--target-entry-notional", type=float, default=0.0)
    parser.add_argument("--target-entry-execution-style", choices=("taker", "maker"), default="taker")
    parser.add_argument("--target-capital-fraction", type=float, default=0.95)
    parser.add_argument("--target-adaptive-entry-sizing", action="store_true")
    parser.add_argument("--target-min-entry-notional", type=float, default=1.0)
    parser.add_argument("--target-max-spread-pct", type=float, default=0.05)
    parser.add_argument("--target-max-entry-impact-pct", type=float, default=0.05)
    parser.add_argument("--target-max-exit-price", type=float, default=0.99)
    parser.add_argument("--target-min-book-imbalance", type=float, default=0.05)
    parser.add_argument("--target-depth-window-pct", type=float, default=0.03)
    parser.add_argument("--target-imbalance-weight", type=float, default=0.10)
    parser.add_argument("--target-min-bid-price", type=float, default=None)
    parser.add_argument("--target-max-bid-price", type=float, default=None)
    parser.add_argument("--target-max-entry-mark-to-bid-loss-pct", type=float, default=None)
    parser.add_argument("--target-max-required-exit-distance-pct", type=float, default=None)
    parser.add_argument("--target-required-exit-distance-weight", type=float, default=0.0)
    parser.add_argument("--target-min-score", type=float, default=None)
    parser.add_argument("--target-history-change-weight", type=float, default=0.0)
    parser.add_argument("--target-min-momentum-observations", type=int, default=2)
    parser.add_argument("--target-min-bid-improvement-pct", type=float, default=0.001)
    parser.add_argument("--target-min-mid-improvement-pct", type=float, default=0.001)
    parser.add_argument("--target-max-spread-widen-pct", type=float, default=0.01)
    parser.add_argument("--target-cooldown-cycles-after-sell", type=int, default=3)
    parser.add_argument("--target-max-hold-cycles", type=int, default=0)
    parser.add_argument("--target-max-hold-min-progress-pct", type=float, default=0.0)
    parser.add_argument("--target-max-hold-cooldown-cycles", type=int, default=0)
    parser.add_argument("--target-max-positions", type=int, default=1)
    parser.add_argument("--target-max-entries-per-cycle", type=int, default=1)
    parser.add_argument("--target-diversify-by", default="none")
    parser.add_argument("--target-max-positions-per-group", type=int, default=0)
    parser.add_argument("--target-watchlist-size", type=int, default=0)
    parser.add_argument(
        "--target-variants",
        default=DEFAULT_TARGET_VARIANTS_ARG,
        help=TARGET_VARIANT_HELP,
    )
    parser.add_argument("--target-allowed-assets", default="")


def _ensure_target_replay_defaults(args) -> None:
    for name, value in TARGET_REPLAY_DEFAULTS.items():
        if not hasattr(args, name):
            setattr(args, name, value)


def main(argv: List[str] = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only Polymarket paper harness")
    sub = parser.add_subparsers(dest="cmd", required=True)

    init = sub.add_parser("init-db", help="Create SQLite schema")
    init.add_argument("--db", default="data/polypaper.sqlite")

    lb = sub.add_parser("collect-leaderboard", help="Collect public leaderboard snapshot")
    lb.add_argument("--db", default="data/polypaper.sqlite")
    lb.add_argument("--limit", type=int, default=100)
    lb.add_argument("--category", default="OVERALL")
    lb.add_argument("--time-period", default="ALL")
    lb.add_argument("--order-by", default="PNL")

    trades = sub.add_parser("collect-trades", help="Collect public trades for one wallet")
    trades.add_argument("--db", default="data/polypaper.sqlite")
    trades.add_argument("--wallet", required=True)
    trades.add_argument("--max-items", type=int, default=1000)

    book = sub.add_parser("collect-book", help="Collect current public CLOB book as a quote")
    book.add_argument("--db", default="data/polypaper.sqlite")
    book.add_argument("--asset", required=True, help="CLOB token id")

    books = sub.add_parser("collect-current-books", help="Collect current quotes for active markets")
    books.add_argument("--db", default="data/polypaper.sqlite")
    books.add_argument("--market-limit", type=int, default=10)
    books.add_argument("--market-order", default="volume_24hr")
    books.add_argument("--market-ascending", action="store_true")

    replay = sub.add_parser("replay-fixture", help="Replay a deterministic JSON fixture")
    replay.add_argument("fixture")
    replay.add_argument("--out", default="")
    replay.add_argument("--delay-seconds", type=int, default=60)
    replay.add_argument("--detection-delay-seconds", type=int, default=0)
    replay.add_argument("--polling-delay-seconds", type=int, default=0)
    replay.add_argument("--decision-delay-seconds", type=int, default=0)
    replay.add_argument("--execution-delay-seconds", type=int, default=None)
    replay.add_argument("--slippage-bps", type=float, default=0.0)
    replay.add_argument("--fee-rate", type=float, default=0.0)
    replay.add_argument("--fee-exponent", type=float, default=1.0)
    replay.add_argument("--tick-size", type=float, default=0.01)
    replay.add_argument("--min-order-size", type=float, default=1.0)
    _add_maker_fill_args(replay)
    replay.add_argument("--initial-cash", type=float, default=10000.0)
    replay.add_argument("--seed", type=int, default=42)

    benchmark = sub.add_parser(
        "benchmark-suite",
        help="Run a replay fixture across fill realism scenarios and summarize strategy robustness",
    )
    benchmark.add_argument("--fixture", required=True)
    benchmark.add_argument("--fill-scenarios", default="configs/fill_scenarios.yml")
    benchmark.add_argument("--scenarios", default="", help="Comma-separated fill scenarios; empty means all")
    benchmark.add_argument(
        "--strategy-suite",
        choices=("default", "default_with_maker", "maker_only"),
        default="default_with_maker",
    )
    benchmark.add_argument("--baseline-scenario", default="")
    benchmark.add_argument("--initial-cash", type=float, default=10000.0)
    benchmark.add_argument("--seed", type=int, default=42)
    benchmark.add_argument("--delay-seconds", type=int, default=60)
    benchmark.add_argument("--detection-delay-seconds", type=int, default=0)
    benchmark.add_argument("--polling-delay-seconds", type=int, default=0)
    benchmark.add_argument("--decision-delay-seconds", type=int, default=0)
    benchmark.add_argument("--execution-delay-seconds", type=int, default=None)
    benchmark.add_argument("--slippage-bps", type=float, default=0.0)
    benchmark.add_argument("--fee-rate", type=float, default=0.0)
    benchmark.add_argument("--fee-exponent", type=float, default=1.0)
    benchmark.add_argument("--tick-size", type=float, default=0.01)
    benchmark.add_argument("--min-order-size", type=float, default=1.0)
    benchmark.add_argument("--min-notional", type=float, default=1.0)
    benchmark.add_argument("--out-dir", default="")
    benchmark.add_argument("--json-out", default="")
    benchmark.add_argument("--csv-out", default="")
    benchmark.add_argument("--md-out", default="")

    record = sub.add_parser("record-snapshots", help="Record public market snapshots for offline paper replay")
    record.add_argument("--out", required=True)
    record.add_argument("--recording-id", default="")
    record.add_argument("--cycles", type=int, default=1)
    record.add_argument("--interval-seconds", type=float, default=0.0)
    record.add_argument("--market-limit", type=int, default=10)
    record.add_argument("--max-assets", type=int, default=20)
    record.add_argument("--market-order", default="volume_24hr")
    record.add_argument("--market-ascending", action="store_true")
    _add_history_args(record)
    _add_market_selection_args(record)
    record.add_argument("--pin-assets", default="", help="Comma-separated token ids to always refresh")

    target_recording = sub.add_parser(
        "target-replay-recording",
        help="Replay target paper agents offline against a recorded market snapshot stream",
    )
    target_recording.add_argument("--recording", required=True)
    target_recording.add_argument("--db", default="data/recording_replay.sqlite")
    target_recording.add_argument("--run-id", default="")
    target_recording.add_argument("--max-cycles", type=int, default=0, help="0 means all recorded collections")
    target_recording.add_argument("--min-cycles-before-pass", type=int, default=0)
    target_recording.add_argument("--initial-cash", type=float, default=10000.0)
    target_recording.add_argument("--require-flat", action="store_true")
    _add_recording_target_args(target_recording)
    target_recording.add_argument("--detection-delay-seconds", type=int, default=0)
    target_recording.add_argument("--polling-delay-seconds", type=int, default=0)
    target_recording.add_argument("--decision-delay-seconds", type=int, default=0)
    target_recording.add_argument("--execution-delay-seconds", type=int, default=0)
    target_recording.add_argument("--slippage-bps", type=float, default=0.0)
    target_recording.add_argument("--fee-rate", type=float, default=0.0)
    target_recording.add_argument("--fee-exponent", type=float, default=1.0)
    target_recording.add_argument("--tick-size", type=float, default=0.01)
    target_recording.add_argument("--min-order-size", type=float, default=1.0)
    _add_maker_fill_args(target_recording)
    target_recording.add_argument("--out", default="")

    paper = sub.add_parser("paper-run", help="Run an online public-data paper simulation")
    paper.add_argument("--db", default="data/polypaper.sqlite")
    paper.add_argument("--run-id", default="")
    paper.add_argument("--cycles", type=int, default=1)
    paper.add_argument("--interval-seconds", type=float, default=0.0)
    paper.add_argument("--market-limit", type=int, default=5)
    paper.add_argument("--max-assets", type=int, default=10)
    paper.add_argument("--market-order", default="volume_24hr")
    paper.add_argument("--market-ascending", action="store_true")
    _add_history_args(paper)
    _add_market_selection_args(paper)
    _add_asset_scope_args(paper)
    _add_settlement_args(paper)
    paper.add_argument("--initial-cash", type=float, default=10000.0)
    paper.add_argument("--seed", type=int, default=42)
    paper.add_argument("--random-agents", type=int, default=1)
    paper.add_argument("--target-profit-agents", type=int, default=0)
    paper.add_argument("--portfolio-target-roi", type=float, default=0.10)
    paper.add_argument("--take-profit-pct", type=float, default=0.10)
    paper.add_argument("--target-allow-take-profit-before-target", action="store_true")
    paper.add_argument("--stop-loss-pct", type=float, default=0.03)
    paper.add_argument("--target-entry-notional", type=float, default=0.0)
    paper.add_argument("--target-entry-execution-style", choices=("taker", "maker"), default="taker")
    paper.add_argument("--target-capital-fraction", type=float, default=0.95)
    paper.add_argument("--target-adaptive-entry-sizing", action="store_true")
    paper.add_argument("--target-min-entry-notional", type=float, default=1.0)
    paper.add_argument("--target-max-spread-pct", type=float, default=0.05)
    paper.add_argument("--target-max-entry-impact-pct", type=float, default=0.05)
    paper.add_argument("--target-max-exit-price", type=float, default=0.99)
    paper.add_argument("--target-min-book-imbalance", type=float, default=0.05)
    paper.add_argument("--target-depth-window-pct", type=float, default=0.03)
    paper.add_argument("--target-imbalance-weight", type=float, default=0.10)
    paper.add_argument("--target-min-bid-price", type=float, default=None)
    paper.add_argument("--target-max-bid-price", type=float, default=None)
    paper.add_argument("--target-max-entry-mark-to-bid-loss-pct", type=float, default=None)
    paper.add_argument("--target-max-required-exit-distance-pct", type=float, default=None)
    paper.add_argument("--target-required-exit-distance-weight", type=float, default=0.0)
    paper.add_argument("--target-min-score", type=float, default=None)
    paper.add_argument("--target-history-change-weight", type=float, default=0.0)
    paper.add_argument("--target-min-momentum-observations", type=int, default=2)
    paper.add_argument("--target-min-bid-improvement-pct", type=float, default=0.001)
    paper.add_argument("--target-min-mid-improvement-pct", type=float, default=0.001)
    paper.add_argument("--target-max-spread-widen-pct", type=float, default=0.01)
    paper.add_argument("--target-cooldown-cycles-after-sell", type=int, default=3)
    paper.add_argument("--target-max-hold-cycles", type=int, default=0)
    paper.add_argument("--target-max-hold-min-progress-pct", type=float, default=0.0)
    paper.add_argument("--target-max-hold-cooldown-cycles", type=int, default=0)
    paper.add_argument("--target-max-positions", type=int, default=1)
    paper.add_argument("--target-max-entries-per-cycle", type=int, default=1)
    paper.add_argument("--target-diversify-by", default="none")
    paper.add_argument("--target-max-positions-per-group", type=int, default=0)
    paper.add_argument("--target-watchlist-size", type=int, default=0)
    paper.add_argument("--trade-probability", type=float, default=0.25)
    paper.add_argument("--max-notional", type=float, default=25.0)
    paper.add_argument("--detection-delay-seconds", type=int, default=0)
    paper.add_argument("--polling-delay-seconds", type=int, default=0)
    paper.add_argument("--decision-delay-seconds", type=int, default=0)
    paper.add_argument("--execution-delay-seconds", type=int, default=0)
    paper.add_argument("--slippage-bps", type=float, default=0.0)
    paper.add_argument("--fee-rate", type=float, default=0.0)
    paper.add_argument("--fee-exponent", type=float, default=1.0)
    paper.add_argument("--tick-size", type=float, default=0.01)
    paper.add_argument("--min-order-size", type=float, default=1.0)
    _add_maker_fill_args(paper)
    paper.add_argument("--out", default="")

    dash = sub.add_parser("dashboard", help="Serve the local paper-run dashboard")
    dash.add_argument("--db", default="data/polypaper.sqlite")
    dash.add_argument("--host", default="127.0.0.1")
    dash.add_argument("--port", type=int, default=8765)

    verify = sub.add_parser("verify-target", help="Verify a paper run reached the target ROI")
    verify.add_argument("--db", default="data/polypaper.sqlite")
    verify.add_argument("--run-id", default="")
    verify.add_argument("--strategy", default="paper_target_profit_10pct")
    verify.add_argument("--target-roi", type=float, default=0.10)
    verify.add_argument("--require-flat", action="store_true")
    verify.add_argument("--json", action="store_true")

    verify_goal = sub.add_parser("verify-online-goal", help="Verify final online virtual-paper goal evidence")
    verify_goal.add_argument("--db", default="data/polypaper.sqlite")
    verify_goal.add_argument("--run-id", default="")
    verify_goal.add_argument("--strategies", default="", help="Comma-separated strategy names; empty means all")
    verify_goal.add_argument("--target-roi", type=float, default=0.10)
    verify_goal.add_argument("--require-flat", action="store_true")
    verify_goal.add_argument("--min-runtime-seconds", type=int, default=21600)
    verify_goal.add_argument("--min-strategies", type=int, default=2)
    verify_goal.add_argument("--min-strategy-families", type=int, default=1)
    verify_goal.add_argument("--allow-non-online-mode", action="store_true")
    verify_goal.add_argument("--json", action="store_true")

    status_goal = sub.add_parser("online-goal-status", help="Print online virtual-paper goal progress")
    status_goal.add_argument("--db", default="data/polypaper.sqlite")
    status_goal.add_argument("--run-id", default="")
    status_goal.add_argument("--strategies", default="", help="Comma-separated strategy names; empty means all")
    status_goal.add_argument("--target-roi", type=float, default=0.10)
    status_goal.add_argument("--require-flat", action="store_true")
    status_goal.add_argument("--min-runtime-seconds", type=int, default=21600)
    status_goal.add_argument("--min-strategies", type=int, default=2)
    status_goal.add_argument("--min-strategy-families", type=int, default=1)
    status_goal.add_argument("--allow-non-online-mode", action="store_true")
    status_goal.add_argument("--top", type=int, default=10)
    status_goal.add_argument("--json", action="store_true")

    scan = sub.add_parser("scan-target-opportunities", help="Score active markets for the target-profit agent")
    scan.add_argument("--market-limit", type=int, default=10)
    scan.add_argument("--max-assets", type=int, default=20)
    scan.add_argument("--market-order", default="volume_24hr")
    scan.add_argument("--market-ascending", action="store_true")
    _add_history_args(scan)
    _add_market_selection_args(scan)
    _add_asset_scope_args(scan)
    scan.add_argument("--initial-cash", type=float, default=10000.0)
    scan.add_argument("--portfolio-target-roi", type=float, default=0.10)
    scan.add_argument("--take-profit-pct", type=float, default=0.10)
    scan.add_argument("--target-allow-take-profit-before-target", action="store_true")
    scan.add_argument("--target-entry-notional", type=float, default=0.0)
    scan.add_argument("--target-entry-execution-style", choices=("taker", "maker"), default="taker")
    scan.add_argument("--target-capital-fraction", type=float, default=0.95)
    scan.add_argument("--target-adaptive-entry-sizing", action="store_true")
    scan.add_argument("--target-min-entry-notional", type=float, default=1.0)
    scan.add_argument("--target-max-spread-pct", type=float, default=0.05)
    scan.add_argument("--target-max-entry-impact-pct", type=float, default=0.05)
    scan.add_argument("--target-max-exit-price", type=float, default=0.99)
    scan.add_argument("--target-min-book-imbalance", type=float, default=0.05)
    scan.add_argument("--target-depth-window-pct", type=float, default=0.03)
    scan.add_argument("--target-imbalance-weight", type=float, default=0.10)
    scan.add_argument("--target-min-bid-price", type=float, default=None)
    scan.add_argument("--target-max-bid-price", type=float, default=None)
    scan.add_argument("--target-max-entry-mark-to-bid-loss-pct", type=float, default=None)
    scan.add_argument("--target-max-required-exit-distance-pct", type=float, default=None)
    scan.add_argument("--target-required-exit-distance-weight", type=float, default=0.0)
    scan.add_argument("--target-min-score", type=float, default=None)
    scan.add_argument("--target-history-change-weight", type=float, default=0.0)
    scan.add_argument("--top", type=int, default=10)
    scan.add_argument("--json", action="store_true")

    pair_scan = sub.add_parser("scan-pair-opportunities", help="Scan paired YES/NO markets for settlement edge")
    pair_scan.add_argument("--market-limit", type=int, default=80)
    pair_scan.add_argument("--max-assets", type=int, default=160)
    pair_scan.add_argument("--market-order", default="volume_24hr")
    pair_scan.add_argument("--market-ascending", action="store_true")
    _add_history_args(pair_scan)
    _add_market_selection_args(pair_scan)
    _add_asset_scope_args(pair_scan)
    pair_scan.add_argument("--min-settlement-roi", type=float, default=0.0)
    pair_scan.add_argument("--top", type=int, default=10)
    pair_scan.add_argument("--json", action="store_true")

    sweep = sub.add_parser("sweep-target-opportunities", help="Search target-agent parameter grids on current books")
    sweep.add_argument("--market-limit", type=int, default=20)
    sweep.add_argument("--max-assets", type=int, default=40)
    sweep.add_argument("--market-order", default="liquidity")
    sweep.add_argument("--market-ascending", action="store_true")
    _add_history_args(sweep)
    _add_market_selection_args(sweep)
    _add_asset_scope_args(sweep)
    sweep.add_argument("--initial-cash", type=float, default=10000.0)
    sweep.add_argument("--portfolio-target-roi", type=float, default=0.10)
    sweep.add_argument("--take-profit-pcts", default="0.01,0.02,0.03,0.05,0.10")
    sweep.add_argument("--capital-fractions", default="0.05,0.10,0.20,0.50,0.95")
    sweep.add_argument("--target-min-entry-notional", type=float, default=25.0)
    sweep.add_argument("--target-max-spread-pct", type=float, default=0.03)
    sweep.add_argument("--target-max-entry-impact-pct", type=float, default=0.12)
    sweep.add_argument("--target-max-exit-price", type=float, default=0.99)
    sweep.add_argument("--target-min-book-imbalance", type=float, default=-0.60)
    sweep.add_argument("--target-depth-window-pct", type=float, default=0.03)
    sweep.add_argument("--target-imbalance-weight", type=float, default=0.10)
    sweep.add_argument("--target-min-bid-price", type=float, default=0.20)
    sweep.add_argument("--target-max-bid-price", type=float, default=0.80)
    sweep.add_argument("--target-max-entry-mark-to-bid-loss-pcts", default="0.02,0.03,0.05,0.08,0.12")
    sweep.add_argument("--target-max-required-exit-distance-pcts", default="0.03,0.05,0.10,0.20,0.30")
    sweep.add_argument("--target-required-exit-distance-weights", default="0,1,2,4")
    sweep.add_argument("--target-min-scores", default="0,0.01,0.02,0.05")
    sweep.add_argument("--top", type=int, default=20)
    sweep.add_argument("--json", action="store_true")

    sweep_until = sub.add_parser(
        "sweep-target-run-until",
        help="Build target agents from a current-book sweep and run them until verification target or max cycles",
    )
    sweep_until.add_argument("--db", default="data/polypaper.sqlite")
    sweep_until.add_argument("--run-id", default="")
    sweep_until.add_argument("--max-cycles", type=int, default=60)
    sweep_until.add_argument("--interval-seconds", type=float, default=5.0)
    sweep_until.add_argument("--market-limit", type=int, default=80)
    sweep_until.add_argument("--max-assets", type=int, default=120)
    sweep_until.add_argument("--market-order", default="volume_24hr")
    sweep_until.add_argument("--market-ascending", action="store_true")
    _add_history_args(sweep_until)
    _add_market_selection_args(sweep_until)
    _add_asset_scope_args(sweep_until)
    _add_settlement_args(sweep_until)
    sweep_until.add_argument("--initial-cash", type=float, default=10000.0)
    sweep_until.add_argument("--portfolio-target-roi", type=float, default=0.10)
    sweep_until.add_argument("--take-profit-pcts", default="0.01,0.02,0.03,0.05,0.10")
    sweep_until.add_argument("--capital-fractions", default="0.05,0.10,0.20,0.50,0.95")
    sweep_until.add_argument("--target-min-entry-notional", type=float, default=25.0)
    sweep_until.add_argument("--target-max-spread-pct", type=float, default=0.03)
    sweep_until.add_argument("--target-max-entry-impact-pct", type=float, default=0.12)
    sweep_until.add_argument("--target-max-exit-price", type=float, default=0.99)
    sweep_until.add_argument("--target-min-book-imbalance", type=float, default=-0.60)
    sweep_until.add_argument("--target-depth-window-pct", type=float, default=0.03)
    sweep_until.add_argument("--target-imbalance-weight", type=float, default=0.10)
    sweep_until.add_argument("--target-min-bid-price", type=float, default=0.20)
    sweep_until.add_argument("--target-max-bid-price", type=float, default=0.80)
    sweep_until.add_argument("--target-max-entry-mark-to-bid-loss-pcts", default="0.02,0.03,0.05,0.08")
    sweep_until.add_argument("--target-max-required-exit-distance-pcts", default="0.03,0.05,0.10,0.20,0.30")
    sweep_until.add_argument("--target-required-exit-distance-weights", default="1,2,4")
    sweep_until.add_argument("--target-min-scores", default="0,0.01,0.02")
    sweep_until.add_argument("--sweep-strategies", type=int, default=5)
    sweep_until.add_argument("--min-cycles-before-pass", type=int, default=0)
    sweep_until.add_argument("--min-runtime-seconds-before-pass", type=float, default=0.0)
    sweep_until.add_argument("--progress-every-cycles", type=int, default=0)
    sweep_until.add_argument("--require-flat", action="store_true")
    sweep_until.add_argument("--stop-loss-pct", type=float, default=0.15)
    sweep_until.add_argument("--target-min-momentum-observations", type=int, default=2)
    sweep_until.add_argument("--target-min-bid-improvement-pct", type=float, default=0.001)
    sweep_until.add_argument("--target-min-mid-improvement-pct", type=float, default=0.001)
    sweep_until.add_argument("--target-max-spread-widen-pct", type=float, default=0.01)
    sweep_until.add_argument("--target-cooldown-cycles-after-sell", type=int, default=1)
    sweep_until.add_argument("--target-max-hold-cycles", type=int, default=0)
    sweep_until.add_argument("--target-max-hold-min-progress-pct", type=float, default=0.0)
    sweep_until.add_argument("--target-max-hold-cooldown-cycles", type=int, default=0)
    sweep_until.add_argument("--target-watchlist-size", type=int, default=0)
    sweep_until.add_argument("--detection-delay-seconds", type=int, default=0)
    sweep_until.add_argument("--polling-delay-seconds", type=int, default=0)
    sweep_until.add_argument("--decision-delay-seconds", type=int, default=0)
    sweep_until.add_argument("--execution-delay-seconds", type=int, default=0)
    sweep_until.add_argument("--slippage-bps", type=float, default=0.0)
    sweep_until.add_argument("--fee-rate", type=float, default=0.0)
    sweep_until.add_argument("--fee-exponent", type=float, default=1.0)
    sweep_until.add_argument("--tick-size", type=float, default=0.01)
    sweep_until.add_argument("--min-order-size", type=float, default=1.0)
    _add_maker_fill_args(sweep_until)
    sweep_until.add_argument("--out", default="")

    target_until = sub.add_parser("target-run-until", help="Run target paper agents until verified ROI target or max cycles")
    target_until.add_argument("--db", default="data/polypaper.sqlite")
    target_until.add_argument("--run-id", default="")
    target_until.add_argument("--resume", action="store_true")
    target_until.add_argument("--max-cycles", type=int, default=60)
    target_until.add_argument("--min-cycles-before-pass", type=int, default=0)
    target_until.add_argument("--min-runtime-seconds-before-pass", type=float, default=0.0)
    target_until.add_argument("--min-passing-strategies", type=int, default=1)
    target_until.add_argument("--min-passing-families", type=int, default=1)
    target_until.add_argument("--progress-every-cycles", type=int, default=0)
    target_until.add_argument("--interval-seconds", type=float, default=5.0)
    target_until.add_argument("--market-limit", type=int, default=10)
    target_until.add_argument("--max-assets", type=int, default=20)
    target_until.add_argument("--market-order", default="volume_24hr")
    target_until.add_argument("--market-ascending", action="store_true")
    _add_history_args(target_until)
    _add_market_selection_args(target_until)
    _add_asset_scope_args(target_until)
    _add_settlement_args(target_until)
    target_until.add_argument("--initial-cash", type=float, default=10000.0)
    target_until.add_argument("--portfolio-target-roi", type=float, default=0.10)
    target_until.add_argument("--take-profit-pct", type=float, default=0.10)
    target_until.add_argument("--target-allow-take-profit-before-target", action="store_true")
    target_until.add_argument("--stop-loss-pct", type=float, default=0.03)
    target_until.add_argument("--target-entry-notional", type=float, default=0.0)
    target_until.add_argument("--target-entry-execution-style", choices=("taker", "maker"), default="taker")
    target_until.add_argument("--target-capital-fraction", type=float, default=0.95)
    target_until.add_argument("--target-adaptive-entry-sizing", action="store_true")
    target_until.add_argument("--target-min-entry-notional", type=float, default=1.0)
    target_until.add_argument("--target-max-spread-pct", type=float, default=0.05)
    target_until.add_argument("--target-max-entry-impact-pct", type=float, default=0.05)
    target_until.add_argument("--target-max-exit-price", type=float, default=0.99)
    target_until.add_argument("--target-min-book-imbalance", type=float, default=0.05)
    target_until.add_argument("--target-depth-window-pct", type=float, default=0.03)
    target_until.add_argument("--target-imbalance-weight", type=float, default=0.10)
    target_until.add_argument("--target-min-bid-price", type=float, default=None)
    target_until.add_argument("--target-max-bid-price", type=float, default=None)
    target_until.add_argument("--target-max-entry-mark-to-bid-loss-pct", type=float, default=None)
    target_until.add_argument("--target-max-required-exit-distance-pct", type=float, default=None)
    target_until.add_argument("--target-required-exit-distance-weight", type=float, default=0.0)
    target_until.add_argument("--target-min-score", type=float, default=None)
    target_until.add_argument("--target-history-change-weight", type=float, default=0.0)
    target_until.add_argument("--target-min-momentum-observations", type=int, default=2)
    target_until.add_argument("--target-min-bid-improvement-pct", type=float, default=0.001)
    target_until.add_argument("--target-min-mid-improvement-pct", type=float, default=0.001)
    target_until.add_argument("--target-max-spread-widen-pct", type=float, default=0.01)
    target_until.add_argument("--target-cooldown-cycles-after-sell", type=int, default=3)
    target_until.add_argument("--target-max-hold-cycles", type=int, default=0)
    target_until.add_argument("--target-max-hold-min-progress-pct", type=float, default=0.0)
    target_until.add_argument("--target-max-hold-cooldown-cycles", type=int, default=0)
    target_until.add_argument("--target-max-positions", type=int, default=1)
    target_until.add_argument("--target-max-entries-per-cycle", type=int, default=1)
    target_until.add_argument("--target-diversify-by", default="none")
    target_until.add_argument("--target-max-positions-per-group", type=int, default=0)
    target_until.add_argument("--target-watchlist-size", type=int, default=0)
    target_until.add_argument(
        "--target-variants",
        default=DEFAULT_TARGET_VARIANTS_ARG,
        help=TARGET_VARIANT_HELP,
    )
    target_until.add_argument("--require-flat", action="store_true")
    target_until.add_argument("--detection-delay-seconds", type=int, default=0)
    target_until.add_argument("--polling-delay-seconds", type=int, default=0)
    target_until.add_argument("--decision-delay-seconds", type=int, default=0)
    target_until.add_argument("--execution-delay-seconds", type=int, default=0)
    target_until.add_argument("--slippage-bps", type=float, default=0.0)
    target_until.add_argument("--fee-rate", type=float, default=0.0)
    target_until.add_argument("--fee-exponent", type=float, default=1.0)
    target_until.add_argument("--tick-size", type=float, default=0.01)
    target_until.add_argument("--min-order-size", type=float, default=1.0)
    _add_maker_fill_args(target_until)
    target_until.add_argument("--out", default="")

    args = parser.parse_args(argv)
    if args.cmd == "init-db":
        conn = connect(args.db)
        init_db(conn)
        print(f"initialized {args.db}")
        return 0
    if args.cmd == "collect-leaderboard":
        conn = connect(args.db)
        init_db(conn)
        client = PublicPolymarketClient()
        rows = leaderboard_pages(
            client,
            limit=args.limit,
            category=args.category,
            time_period=args.time_period,
            order_by=args.order_by,
        )
        inserted = insert_leaderboard(conn, rows, args.category, args.time_period, args.order_by)
        print(f"inserted {inserted} leaderboard rows into {args.db}")
        return 0
    if args.cmd == "collect-trades":
        conn = connect(args.db)
        init_db(conn)
        client = PublicPolymarketClient()
        rows = list(client.paged("user_trades", wallet=args.wallet, max_items=args.max_items))
        inserted = insert_trades(conn, rows)
        print(f"inserted {inserted} public trade rows into {args.db}")
        return 0
    if args.cmd == "collect-book":
        conn = connect(args.db)
        init_db(conn)
        client = PublicPolymarketClient()
        book = order_book_from_clob(client.book(args.asset))
        if book is None:
            print(f"no quote available for {args.asset}")
            return 1
        quote = book.to_quote()
        insert_order_books(conn, [book])
        inserted = insert_quotes(conn, [quote])
        print(f"inserted {inserted} quote row and 1 order book row for {quote.asset} into {args.db}")
        return 0
    if args.cmd == "collect-current-books":
        conn = connect(args.db)
        init_db(conn)
        client = PublicPolymarketClient()
        books = []
        for market in client.markets(
            limit=args.market_limit,
            closed=False,
            active=True,
            order=args.market_order,
            ascending=args.market_ascending,
        ):
            for token_id in token_ids_from_market(market):
                book = order_book_from_clob(client.book(token_id))
                if book:
                    books.append(book)
        quotes = [book.to_quote() for book in books]
        insert_order_books(conn, books)
        inserted = insert_quotes(conn, quotes)
        print(f"inserted {inserted} current quote rows and {len(books)} order book rows into {args.db}")
        return 0
    if args.cmd == "replay-fixture":
        results = _run_fixture(args)
        report = markdown_report(results)
        if args.out:
            path = Path(args.out)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(report, encoding="utf-8")
        print(report)
        return 0
    if args.cmd == "benchmark-suite":
        result = _run_benchmark_suite(args)
        write_benchmark_outputs(
            result,
            json_out=args.json_out,
            csv_out=args.csv_out,
            md_out=args.md_out,
            out_dir=args.out_dir,
        )
        print(benchmark_markdown_report(result))
        return 0
    if args.cmd == "record-snapshots":
        recording = _run_record_snapshots(args)
        save_recording(recording, args.out)
        snapshot_count = sum(len(collection.snapshots) for collection in recording.collections)
        print(
            f"recorded {len(recording.collections)} collections and {snapshot_count} snapshots "
            f"to {args.out}"
        )
        return 0
    if args.cmd == "target-replay-recording":
        result = _run_target_replay_recording(args)
        report = markdown_report(result.results)
        if args.out:
            path = Path(args.out)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(report, encoding="utf-8")
        verification = result.best_verification
        status = "PASS" if result.passed else "FAIL"
        if verification is None:
            detail = "no_verification"
        else:
            detail = (
                f"strategy={verification.strategy} final_roi={verification.final_roi:.4%} "
                f"max_roi={verification.max_roi:.4%} roi_gap={verification.roi_gap:.4%} "
                f"equity_gap={verification.equity_gap:.4f} "
                f"required_position_gain={verification.required_position_gain_pct:.4%} "
                f"flat={verification.flat} reason={verification.reason}"
            )
        print(f"{status} run_id={result.run_id} cycles={result.cycles_completed} {detail}")
        _print_verification_table(result.latest_verifications)
        print(report)
        return 0 if result.passed else 1
    if args.cmd == "paper-run":
        results, run_id = _run_paper(args)
        report = markdown_report(results)
        if args.out:
            path = Path(args.out)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(report, encoding="utf-8")
        print(f"paper_run_id={run_id}")
        print(report)
        return 0
    if args.cmd == "dashboard":
        serve_dashboard(args.db, host=args.host, port=args.port)
        return 0
    if args.cmd == "verify-target":
        verification = verify_target_run_from_path(
            args.db,
            run_id=args.run_id,
            strategy=args.strategy,
            target_roi=args.target_roi,
            require_flat=args.require_flat,
        )
        if args.json:
            print(json.dumps(verification.to_dict(), sort_keys=True, indent=2))
        else:
            status = "PASS" if verification.passed else "FAIL"
            print(
                f"{status} run_id={verification.run_id} strategy={verification.strategy} "
                f"final_roi={verification.final_roi:.4%} max_roi={verification.max_roi:.4%} "
                f"roi_gap={verification.roi_gap:.4%} equity_gap={verification.equity_gap:.4f} "
                f"target_roi={verification.target_roi:.4%} flat={verification.flat} "
                f"required_position_gain={verification.required_position_gain_pct:.4%} "
                f"reason={verification.reason}"
            )
        return 0 if verification.passed else 1
    if args.cmd == "verify-online-goal":
        verification = verify_online_goal_from_path(
            args.db,
            run_id=args.run_id,
            strategies=_parse_csv(args.strategies),
            target_roi=args.target_roi,
            require_flat=args.require_flat,
            min_runtime_seconds=args.min_runtime_seconds,
            min_strategies=args.min_strategies,
            min_strategy_families=args.min_strategy_families,
            require_online_mode=not args.allow_non_online_mode,
        )
        if args.json:
            print(json.dumps(verification.to_dict(), sort_keys=True, indent=2))
        else:
            status = "PASS" if verification.passed else "FAIL"
            print(
                f"{status} run_id={verification.run_id} mode={verification.run_mode or 'unknown'} "
                f"runtime={verification.runtime_seconds}s required_runtime={verification.min_runtime_seconds}s "
                f"passed_strategies={verification.passed_strategies}/{verification.total_strategies} "
                f"required_strategies={verification.required_strategies} "
                f"passed_families={verification.passed_strategy_families}/{verification.required_strategy_families} "
                f"target_roi={verification.target_roi:.4%} flat_required={verification.flat_required} "
                f"reason={verification.reason}"
            )
            _print_verification_table(verification.strategy_results)
        return 0 if verification.passed else 1
    if args.cmd == "online-goal-status":
        status = online_goal_status_from_path(
            args.db,
            run_id=args.run_id,
            strategies=_parse_csv(args.strategies),
            target_roi=args.target_roi,
            require_flat=args.require_flat,
            min_runtime_seconds=args.min_runtime_seconds,
            min_strategies=args.min_strategies,
            min_strategy_families=args.min_strategy_families,
            require_online_mode=not args.allow_non_online_mode,
            top=args.top,
        )
        if args.json:
            print(json.dumps(status.to_dict(), sort_keys=True, indent=2))
        else:
            print(format_online_goal_status(status))
        return 0
    if args.cmd == "scan-target-opportunities":
        opportunities = _scan_target_opportunities(args)
        if args.json:
            print(json.dumps([item.to_dict() for item in opportunities], sort_keys=True, indent=2))
        else:
            _print_opportunity_table(opportunities)
        return 0
    if args.cmd == "scan-pair-opportunities":
        opportunities = _scan_pair_opportunities(args)
        if args.json:
            print(json.dumps([item.to_dict() for item in opportunities], sort_keys=True, indent=2))
        else:
            _print_pair_opportunity_table(opportunities)
        return 0
    if args.cmd == "sweep-target-opportunities":
        results = _sweep_target_opportunities(args)
        if args.json:
            print(json.dumps([item.to_dict() for item in results], sort_keys=True, indent=2))
        else:
            _print_sweep_table(results)
        return 0
    if args.cmd == "sweep-target-run-until":
        result, sweep_results = _run_sweep_target_until(args)
        report = markdown_report(result.results)
        if args.out:
            path = Path(args.out)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(report, encoding="utf-8")
        if sweep_results:
            print("sweep_selected:")
            _print_sweep_table(sweep_results)
        verification = result.best_verification
        status = "PASS" if result.passed else "FAIL"
        if verification is None:
            detail = "no_verification"
        else:
            detail = (
                f"strategy={verification.strategy} final_roi={verification.final_roi:.4%} "
                f"max_roi={verification.max_roi:.4%} roi_gap={verification.roi_gap:.4%} "
                f"equity_gap={verification.equity_gap:.4f} "
                f"required_position_gain={verification.required_position_gain_pct:.4%} "
                f"flat={verification.flat} reason={verification.reason}"
            )
        print(f"{status} run_id={result.run_id} cycles={result.cycles_completed} {detail}")
        _print_verification_table(result.latest_verifications)
        print(report)
        return 0 if result.passed else 1
    if args.cmd == "target-run-until":
        result = _run_target_until(args)
        report = markdown_report(result.results)
        if args.out:
            path = Path(args.out)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(report, encoding="utf-8")
        verification = result.best_verification
        status = "PASS" if result.passed else "FAIL"
        if verification is None:
            detail = "no_verification"
        else:
            detail = (
                f"strategy={verification.strategy} final_roi={verification.final_roi:.4%} "
                f"max_roi={verification.max_roi:.4%} roi_gap={verification.roi_gap:.4%} "
                f"equity_gap={verification.equity_gap:.4f} "
                f"required_position_gain={verification.required_position_gain_pct:.4%} "
                f"flat={verification.flat} reason={verification.reason}"
            )
        print(f"{status} run_id={result.run_id} cycles={result.cycles_completed} {detail}")
        _print_verification_table(result.latest_verifications)
        print(report)
        return 0 if result.passed else 1
    raise ValueError(args.cmd)


def _run_fixture(args) -> list:
    data = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    trades = [TraderTrade.from_api(row) for row in data["trades"]]
    books = [Quote.from_dict(row) for row in data.get("quotes", [])]
    if data.get("order_books"):
        from .models import OrderBook

        books = [OrderBook.from_dict(row) for row in data["order_books"]]
    strategies = default_replay_strategies(trades, seed=args.seed)
    simulator = ReplaySimulator(
        strategies=strategies,
        fill_model=ConservativeFillModel(
            delay_seconds=args.delay_seconds,
            slippage_bps=args.slippage_bps,
            latency_model=LatencyModel(
                detection_delay_seconds=args.detection_delay_seconds,
                polling_delay_seconds=args.polling_delay_seconds,
                decision_delay_seconds=args.decision_delay_seconds,
                execution_delay_seconds=(
                    args.execution_delay_seconds
                    if args.execution_delay_seconds is not None
                    else args.delay_seconds
                ),
            ),
            default_rules=MarketRules(
                tick_size=args.tick_size,
                min_order_size=args.min_order_size,
                fee_model=PolymarketFeeModel(
                    fee_rate=args.fee_rate,
                    exponent=args.fee_exponent,
                    taker_only=True,
                ),
            ),
            **_maker_fill_kwargs(args),
        ),
        initial_cash=args.initial_cash,
    )
    engine = replay_backtest_engine(
        simulator=simulator,
        trades=trades,
        quotes=books,
        name="replay-fixture",
    )
    return engine.run_once()


def _run_benchmark_suite(args):
    scenarios = load_fill_scenarios(
        args.fill_scenarios,
        selected_names=parse_csv_names(args.scenarios),
    )
    return run_replay_benchmark(
        fixture_path=args.fixture,
        scenarios=scenarios,
        strategy_suite=args.strategy_suite,
        seed=args.seed,
        initial_cash=args.initial_cash,
        base_fill_params=_benchmark_base_fill_params(args),
        baseline_scenario=args.baseline_scenario,
    )


def _benchmark_base_fill_params(args) -> dict:
    return {
        "delay_seconds": args.delay_seconds,
        "detection_delay_seconds": args.detection_delay_seconds,
        "polling_delay_seconds": args.polling_delay_seconds,
        "decision_delay_seconds": args.decision_delay_seconds,
        "execution_delay_seconds": (
            args.execution_delay_seconds
            if args.execution_delay_seconds is not None
            else args.delay_seconds
        ),
        "slippage_bps": args.slippage_bps,
        "fee_rate": args.fee_rate,
        "fee_exponent": args.fee_exponent,
        "tick_size": args.tick_size,
        "min_order_size": args.min_order_size,
        "min_notional": args.min_notional,
    }


def _run_record_snapshots(args):
    client = PublicPolymarketClient()
    from .paper import MarketDataCollector

    collector = MarketDataCollector(
        client,
        market_limit=args.market_limit,
        max_assets=args.max_assets,
        market_order=args.market_order,
        market_ascending=args.market_ascending,
        pinned_assets=_parse_csv(getattr(args, "pin_assets", "") or ""),
        **_collector_market_selection_kwargs(args),
        **_collector_history_kwargs(args),
    )
    metadata = {
        "market_limit": args.market_limit,
        "max_assets": args.max_assets,
        "market_order": args.market_order,
        "market_ascending": args.market_ascending,
        "interval_seconds": args.interval_seconds,
        "cycles": args.cycles,
        "history": _collector_history_kwargs(args),
        "market_selection": _collector_market_selection_kwargs(args),
        "pin_assets": _parse_csv(getattr(args, "pin_assets", "") or ""),
    }
    return record_market_snapshots(
        collector,
        cycles=args.cycles,
        interval_seconds=args.interval_seconds,
        recording_id=args.recording_id or f"recording-{int(time.time())}-{uuid4().hex[:8]}",
        metadata=metadata,
    )


def _run_target_replay_recording(args):
    _ensure_target_replay_defaults(args)
    conn = connect(args.db)
    init_db(conn)
    recording = load_recording(args.recording)
    run_id = args.run_id or f"recording-target-{int(time.time())}-{uuid4().hex[:8]}"
    collector = RecordedMarketDataCollector(recording)
    fill_model = ConservativeFillModel(
        slippage_bps=args.slippage_bps,
        latency_model=LatencyModel(
            detection_delay_seconds=args.detection_delay_seconds,
            polling_delay_seconds=args.polling_delay_seconds,
            decision_delay_seconds=args.decision_delay_seconds,
            execution_delay_seconds=args.execution_delay_seconds,
        ),
        default_rules=MarketRules(
            tick_size=args.tick_size,
            min_order_size=args.min_order_size,
            fee_model=PolymarketFeeModel(
                fee_rate=args.fee_rate,
                exponent=args.fee_exponent,
                taker_only=True,
            ),
        ),
        **_maker_fill_kwargs(args),
    )
    variants = target_variant_configs(args)
    runner = PaperRunner(
        client=None,
        conn=conn,
        run_id=run_id,
        strategies=[target_strategy_from_config(args, name, config) for name, config in variants],
        fill_model=fill_model,
        initial_cash=args.initial_cash,
        collector=collector,
    )
    engine = paper_engine(
        runner,
        name="recording-replay",
        uses_live_market_data=False,
        description="Recorded market snapshot replay through the paper execution engine.",
    )
    strategy_names = [state.strategy.name for state in runner.agent_batch]
    max_cycles = args.max_cycles if args.max_cycles > 0 else len(recording.collections)
    upsert_paper_run(conn, run_id, "recording_replay", _run_metadata_config(args, strategy_names))
    result = run_until_target(
        runner=engine,
        conn=conn,
        run_id=run_id,
        strategy_names=strategy_names,
        target_roi=args.portfolio_target_roi,
        max_cycles=max_cycles,
        interval_seconds=0,
        min_cycles_before_pass=getattr(args, "min_cycles_before_pass", 0),
        require_flat=args.require_flat,
    )
    upsert_paper_run(
        conn,
        run_id,
        "recording_replay",
        {"cycles_completed": result.cycles_completed, "passed": result.passed},
    )
    return result


def _run_paper(args) -> tuple:
    conn = connect(args.db)
    init_db(conn)
    run_id = args.run_id or f"paper-{int(time.time())}-{uuid4().hex[:8]}"
    client = PublicPolymarketClient()
    runner = _build_paper_runner(args, conn, run_id, client)
    engine = paper_engine(runner, name="online-paper")
    strategy_names = [state.strategy.name for state in runner.agent_batch]
    upsert_paper_run(conn, run_id, "online_paper", _run_metadata_config(args, strategy_names))
    results = engine.run(cycles=args.cycles, interval_seconds=args.interval_seconds)
    upsert_paper_run(conn, run_id, "online_paper", {"cycles_completed": args.cycles})
    return results, run_id


def _build_paper_runner(args, conn, run_id: str, client):
    fill_model = ConservativeFillModel(
        slippage_bps=args.slippage_bps,
        latency_model=LatencyModel(
            detection_delay_seconds=args.detection_delay_seconds,
            polling_delay_seconds=args.polling_delay_seconds,
            decision_delay_seconds=args.decision_delay_seconds,
            execution_delay_seconds=args.execution_delay_seconds,
        ),
        default_rules=MarketRules(
            tick_size=args.tick_size,
            min_order_size=args.min_order_size,
            fee_model=PolymarketFeeModel(
                fee_rate=args.fee_rate,
                exponent=args.fee_exponent,
                taker_only=True,
            ),
        ),
        **_maker_fill_kwargs(args),
    )
    return PaperRunner(
        client=client,
        conn=conn,
        run_id=run_id,
        strategies=default_paper_strategies(args),
        fill_model=fill_model,
        initial_cash=args.initial_cash,
        market_limit=args.market_limit,
        max_assets=args.max_assets,
        market_order=args.market_order,
        market_ascending=args.market_ascending,
        **_collector_market_selection_kwargs(args),
        pinned_assets=_collector_pinned_assets(args),
        pinned_only_after_entry=getattr(args, "pinned_only_after_entry", False),
        pinned_only_after_watchlist=getattr(args, "pinned_only_after_watchlist", False),
        pinned_watchlist_rescan_cycles=getattr(args, "pinned_watchlist_rescan_cycles", 0),
        settlement_check_seconds=getattr(args, "settlement_check_seconds", 60),
        use_wall_time_timestamps=True,
        **_collector_history_kwargs(args),
    )


def _run_target_until(args):
    conn = connect(args.db)
    init_db(conn)
    run_id = args.run_id or f"target-{int(time.time())}-{uuid4().hex[:8]}"
    client = PublicPolymarketClient()
    runner = _build_target_runner(args, conn, run_id, client)
    if args.resume:
        runner.resume_from_db()
    engine = paper_engine(runner, name="online-target")
    strategy_names = [state.strategy.name for state in runner.agent_batch]
    upsert_paper_run(conn, run_id, "online_target", _run_metadata_config(args, strategy_names))
    resume_cycles, resume_elapsed = _resume_gate_offsets(conn, run_id) if args.resume else (0, 0.0)
    result = run_until_target(
        runner=engine,
        conn=conn,
        run_id=run_id,
        strategy_names=strategy_names,
        target_roi=args.portfolio_target_roi,
        max_cycles=args.max_cycles,
        interval_seconds=args.interval_seconds,
        min_cycles_before_pass=getattr(args, "min_cycles_before_pass", 0),
        min_elapsed_seconds_before_pass=getattr(args, "min_runtime_seconds_before_pass", 0.0),
        min_passing_strategies=getattr(args, "min_passing_strategies", 1),
        min_passing_families=getattr(args, "min_passing_families", 1),
        initial_cycles_completed=resume_cycles,
        initial_elapsed_seconds=resume_elapsed,
        require_flat=args.require_flat,
        on_cycle=_paper_run_cycle_callback(
            conn,
            run_id,
            "online_target",
            getattr(args, "progress_every_cycles", 0),
        ),
    )
    upsert_paper_run(
        conn,
        run_id,
        "online_target",
        {"cycles_completed": result.cycles_completed, "passed": result.passed},
    )
    return result


def _resume_gate_offsets(conn, run_id: str) -> tuple:
    cycles = 0
    row = conn.execute(
        "SELECT config_json FROM paper_runs WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    if row is not None:
        try:
            config = json.loads(row[0] or "{}")
        except (TypeError, ValueError):
            config = {}
        if isinstance(config, dict):
            try:
                cycles = max(0, int(config.get("cycles_completed", 0) or 0))
            except (TypeError, ValueError):
                cycles = 0
    if cycles <= 0:
        row = conn.execute(
            """
            SELECT COUNT(DISTINCT timestamp)
            FROM portfolio_snapshots
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()
        distinct_timestamps = int(row[0] if row else 0)
        cycles = max(0, distinct_timestamps - 1)
    row = conn.execute(
        "SELECT started_at, updated_at FROM paper_runs WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    if row is not None and row[0] is not None and row[1] is not None and int(row[1]) > int(row[0]):
        elapsed = float(max(0, int(row[1]) - int(row[0])))
    else:
        row = conn.execute(
            """
            SELECT MIN(timestamp), MAX(timestamp)
            FROM portfolio_snapshots
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()
        if row is None or row[0] is None or row[1] is None:
            elapsed = 0.0
        else:
            elapsed = float(max(0, int(row[1]) - int(row[0])))
    return cycles, elapsed


def _build_target_runner(args, conn, run_id: str, client):
    fill_model = ConservativeFillModel(
        slippage_bps=args.slippage_bps,
        latency_model=LatencyModel(
            detection_delay_seconds=args.detection_delay_seconds,
            polling_delay_seconds=args.polling_delay_seconds,
            decision_delay_seconds=args.decision_delay_seconds,
            execution_delay_seconds=args.execution_delay_seconds,
        ),
        default_rules=MarketRules(
            tick_size=args.tick_size,
            min_order_size=args.min_order_size,
            fee_model=PolymarketFeeModel(
                fee_rate=args.fee_rate,
                exponent=args.fee_exponent,
                taker_only=True,
            ),
        ),
        **_maker_fill_kwargs(args),
    )
    variants = target_variant_configs(args)
    return PaperRunner(
        client=client,
        conn=conn,
        run_id=run_id,
        strategies=[target_strategy_from_config(args, name, config) for name, config in variants],
        fill_model=fill_model,
        initial_cash=args.initial_cash,
        market_limit=args.market_limit,
        max_assets=args.max_assets,
        market_order=args.market_order,
        market_ascending=args.market_ascending,
        **_collector_market_selection_kwargs(args),
        pinned_assets=_collector_pinned_assets(args),
        pinned_only_after_entry=getattr(args, "pinned_only_after_entry", False),
        pinned_only_after_watchlist=getattr(args, "pinned_only_after_watchlist", False),
        pinned_watchlist_rescan_cycles=getattr(args, "pinned_watchlist_rescan_cycles", 0),
        settlement_check_seconds=getattr(args, "settlement_check_seconds", 60),
        use_wall_time_timestamps=True,
        **_collector_history_kwargs(args),
    )


def _run_sweep_target_until(args):
    conn = connect(args.db)
    init_db(conn)
    run_id = args.run_id or f"sweep-target-{int(time.time())}-{uuid4().hex[:8]}"
    client = PublicPolymarketClient()
    raw_sweep_results = _collect_target_sweep(args, client, top=_sweep_raw_top(args))
    sweep_results = _unique_sweep_assets(raw_sweep_results, args.sweep_strategies)
    if not sweep_results:
        runner = _build_sweep_target_runner(args, conn, run_id, client, [])
        engine = paper_engine(runner, name="online-sweep-target")
        upsert_paper_run(conn, run_id, "online_sweep_target", _run_metadata_config(args, []))
        result = run_until_target(
            runner=engine,
            conn=conn,
            run_id=run_id,
            strategy_names=[],
            target_roi=args.portfolio_target_roi,
            max_cycles=0,
            interval_seconds=0,
            require_flat=args.require_flat,
        )
        upsert_paper_run(
            conn,
            run_id,
            "online_sweep_target",
            {"cycles_completed": result.cycles_completed, "passed": result.passed},
        )
        return result, sweep_results
    runner = _build_sweep_target_runner(args, conn, run_id, client, sweep_results)
    engine = paper_engine(runner, name="online-sweep-target")
    strategy_names = [state.strategy.name for state in runner.agent_batch]
    upsert_paper_run(conn, run_id, "online_sweep_target", _run_metadata_config(args, strategy_names))
    result = run_until_target(
        runner=engine,
        conn=conn,
        run_id=run_id,
        strategy_names=strategy_names,
        target_roi=args.portfolio_target_roi,
        max_cycles=args.max_cycles,
        interval_seconds=args.interval_seconds,
        min_cycles_before_pass=getattr(args, "min_cycles_before_pass", 0),
        min_elapsed_seconds_before_pass=getattr(args, "min_runtime_seconds_before_pass", 0.0),
        require_flat=args.require_flat,
        on_cycle=_paper_run_cycle_callback(
            conn,
            run_id,
            "online_sweep_target",
            getattr(args, "progress_every_cycles", 0),
        ),
    )
    upsert_paper_run(
        conn,
        run_id,
        "online_sweep_target",
        {"cycles_completed": result.cycles_completed, "passed": result.passed},
    )
    return result, sweep_results


def _build_sweep_target_runner(args, conn, run_id: str, client, sweep_results: list):
    fill_model = ConservativeFillModel(
        slippage_bps=args.slippage_bps,
        latency_model=LatencyModel(
            detection_delay_seconds=args.detection_delay_seconds,
            polling_delay_seconds=args.polling_delay_seconds,
            decision_delay_seconds=args.decision_delay_seconds,
            execution_delay_seconds=args.execution_delay_seconds,
        ),
        default_rules=MarketRules(
            tick_size=args.tick_size,
            min_order_size=args.min_order_size,
            fee_model=PolymarketFeeModel(
                fee_rate=args.fee_rate,
                exponent=args.fee_exponent,
                taker_only=True,
            ),
        ),
        **_maker_fill_kwargs(args),
    )
    return PaperRunner(
        client=client,
        conn=conn,
        run_id=run_id,
        strategies=[
            target_strategy_from_sweep_result(args, result, index + 1)
            for index, result in enumerate(sweep_results)
        ],
        fill_model=fill_model,
        initial_cash=args.initial_cash,
        market_limit=args.market_limit,
        max_assets=args.max_assets,
        market_order=args.market_order,
        market_ascending=args.market_ascending,
        **_collector_market_selection_kwargs(args),
        pinned_assets=_collector_pinned_assets(args) + [result.opportunity.asset for result in sweep_results],
        pinned_only_after_entry=getattr(args, "pinned_only_after_entry", False),
        pinned_only_after_watchlist=getattr(args, "pinned_only_after_watchlist", False),
        pinned_watchlist_rescan_cycles=getattr(args, "pinned_watchlist_rescan_cycles", 0),
        settlement_check_seconds=getattr(args, "settlement_check_seconds", 60),
        use_wall_time_timestamps=True,
        **_collector_history_kwargs(args),
    )

def _unique_sweep_assets(results: list, limit: int) -> list:
    selected = []
    seen_assets = set()
    for result in results:
        asset = result.opportunity.asset
        if asset in seen_assets:
            continue
        seen_assets.add(asset)
        selected.append(result)
        if len(selected) >= limit:
            break
    return selected


def _sweep_raw_top(args) -> int:
    return max(args.sweep_strategies * SWEEP_UNIQUE_RAW_MULTIPLIER, args.sweep_strategies)


def _scan_target_opportunities(args) -> list:
    from .paper import MarketDataCollector

    client = PublicPolymarketClient()
    collector = MarketDataCollector(
        client,
        market_limit=args.market_limit,
        max_assets=args.max_assets,
        market_order=args.market_order,
        market_ascending=args.market_ascending,
        **_collector_market_selection_kwargs(args),
        pinned_assets=_collector_pinned_assets(args),
        **_collector_history_kwargs(args),
    )
    collection = collector.collect()
    notional = target_entry_notional(
        initial_cash=args.initial_cash,
        current_cash=args.initial_cash,
        portfolio_target_roi=args.portfolio_target_roi,
        take_profit_pct=args.take_profit_pct,
        entry_notional=args.target_entry_notional,
        capital_fraction=args.target_capital_fraction,
    )
    opportunities = []
    for snapshot in collection.snapshots:
        score_kwargs = {
            "snapshot": snapshot,
            "initial_cash": args.initial_cash,
            "current_cash": args.initial_cash,
            "portfolio_target_roi": args.portfolio_target_roi,
            "take_profit_pct": args.take_profit_pct,
            "allow_take_profit_before_target": args.target_allow_take_profit_before_target,
            "max_spread_pct": args.target_max_spread_pct,
            "max_entry_impact_pct": args.target_max_entry_impact_pct,
            "max_exit_price": args.target_max_exit_price,
            "min_book_imbalance": args.target_min_book_imbalance,
            "depth_window_pct": args.target_depth_window_pct,
            "imbalance_weight": args.target_imbalance_weight,
            "min_bid_price": args.target_min_bid_price,
            "max_bid_price": args.target_max_bid_price,
            "max_entry_mark_to_bid_loss_pct": args.target_max_entry_mark_to_bid_loss_pct,
            "max_required_exit_distance_pct": args.target_max_required_exit_distance_pct,
            "required_exit_distance_weight": args.target_required_exit_distance_weight,
            "min_score": args.target_min_score,
            "fee_model": getattr(collection.rules_by_asset.get(snapshot.asset), "fee_model", None),
            "entry_price_mode": "maker_bid"
            if args.target_entry_execution_style == "maker"
            else "taker",
        }
        if args.target_adaptive_entry_sizing:
            opportunities.append(
                score_adaptive_target_opportunity(
                    max_target_notional=notional,
                    min_target_notional=args.target_min_entry_notional,
                    **score_kwargs,
                )
            )
        else:
            opportunities.append(score_target_opportunity(target_notional=notional, **score_kwargs))
    history_weight = getattr(args, "target_history_change_weight", 0.0)
    if history_weight:
        from dataclasses import replace

        opportunities = [
            replace(
                opportunity,
                score=opportunity.score
                + history_weight * (opportunity.history_change_pct or 0.0),
            )
            for opportunity in opportunities
        ]
    opportunities.sort(key=lambda item: (item.viable, item.score), reverse=True)
    return opportunities[: args.top]


def _sweep_target_opportunities(args) -> list:
    client = PublicPolymarketClient()
    return _collect_target_sweep(args, client, top=args.top)


def _scan_pair_opportunities(args) -> list:
    from .paper import MarketDataCollector

    client = PublicPolymarketClient()
    collector = MarketDataCollector(
        client,
        market_limit=args.market_limit,
        max_assets=args.max_assets,
        market_order=args.market_order,
        market_ascending=args.market_ascending,
        **_collector_market_selection_kwargs(args),
        pinned_assets=_collector_pinned_assets(args),
        **_collector_history_kwargs(args),
    )
    collection = collector.collect()
    opportunities = scan_paired_outcome_opportunities(
        collection.snapshots,
        rules_by_asset=collection.rules_by_asset,
        min_settlement_roi=args.min_settlement_roi,
    )
    return list(opportunities[: args.top])


def _collect_target_sweep(args, client, top: int) -> list:
    from .paper import MarketDataCollector

    collector = MarketDataCollector(
        client,
        market_limit=args.market_limit,
        max_assets=args.max_assets,
        market_order=args.market_order,
        market_ascending=args.market_ascending,
        **_collector_market_selection_kwargs(args),
        pinned_assets=_collector_pinned_assets(args),
        **_collector_history_kwargs(args),
    )
    collection = collector.collect()
    configs = target_sweep_configs(
        take_profit_pcts=_parse_float_list(args.take_profit_pcts),
        capital_fractions=_parse_float_list(args.capital_fractions),
        max_entry_mark_to_bid_loss_pcts=_parse_float_list(args.target_max_entry_mark_to_bid_loss_pcts),
        max_required_exit_distance_pcts=_parse_float_list(args.target_max_required_exit_distance_pcts),
        required_exit_distance_weights=_parse_float_list(args.target_required_exit_distance_weights),
        min_scores=_parse_float_list(args.target_min_scores),
    )
    return sweep_target_opportunities(
        snapshots=collection.snapshots,
        rules_by_asset=collection.rules_by_asset,
        configs=configs,
        initial_cash=args.initial_cash,
        portfolio_target_roi=args.portfolio_target_roi,
        min_entry_notional=args.target_min_entry_notional,
        max_spread_pct=args.target_max_spread_pct,
        max_entry_impact_pct=args.target_max_entry_impact_pct,
        max_exit_price=args.target_max_exit_price,
        min_book_imbalance=args.target_min_book_imbalance,
        depth_window_pct=args.target_depth_window_pct,
        imbalance_weight=args.target_imbalance_weight,
        min_bid_price=args.target_min_bid_price,
        max_bid_price=args.target_max_bid_price,
        top=top,
    )


def _parse_float_list(raw: str) -> list:
    values = []
    for item in str(raw).split(","):
        item = item.strip()
        if item:
            values.append(float(item))
    if not values:
        raise ValueError("expected at least one numeric value")
    return values


def _collector_history_kwargs(args) -> dict:
    return {
        "history_window_seconds": getattr(args, "history_window_seconds", 0),
        "history_interval": getattr(args, "history_interval", "1h"),
        "history_min_change_pct": getattr(args, "history_min_change_pct", None),
        "history_candidate_assets": getattr(args, "history_candidate_assets", 0),
        "history_cache_seconds": getattr(args, "history_cache_seconds", 60),
        "history_min_bid_price": getattr(args, "history_min_bid_price", None),
        "history_max_bid_price": getattr(args, "history_max_bid_price", None),
        "history_max_spread_pct": getattr(args, "history_max_spread_pct", None),
        "history_max_queries": getattr(args, "history_max_queries", 0),
    }


def _collector_market_selection_kwargs(args) -> dict:
    return {
        "market_pages": max(1, getattr(args, "market_pages", 1)),
        "market_filter_keywords": _parse_csv(getattr(args, "market_filter_keywords", "") or ""),
        "market_prefer_keywords": _parse_csv(getattr(args, "market_prefer_keywords", "") or ""),
    }


def _collector_pinned_assets(args) -> list:
    assets = []
    assets.extend(_parse_csv(getattr(args, "pin_assets", "") or ""))
    assets.extend(_parse_csv(getattr(args, "target_allowed_assets", "") or ""))
    deduped = []
    seen = set()
    for asset in assets:
        if asset in seen:
            continue
        seen.add(asset)
        deduped.append(asset)
    return deduped


def _parse_csv(raw: str) -> list:
    return [item.strip() for item in str(raw).split(",") if item.strip()]


def _run_metadata_config(args, strategy_names: list) -> dict:
    fields = (
        "max_cycles",
        "min_cycles_before_pass",
        "min_runtime_seconds_before_pass",
        "min_passing_strategies",
        "min_passing_families",
        "interval_seconds",
        "market_limit",
        "market_pages",
        "max_assets",
        "market_order",
        "market_filter_keywords",
        "market_prefer_keywords",
        "portfolio_target_roi",
        "target_variants",
        "require_flat",
        "maker_fill_mode",
        "maker_queue_ahead_fraction",
        "maker_queue_decay",
        "maker_max_order_age_attempts",
        "maker_cancel_on_price_move",
        "maker_adverse_fill_on_price_move",
        "maker_adverse_fill_fraction",
        "settlement_check_seconds",
        "detection_delay_seconds",
        "polling_delay_seconds",
        "decision_delay_seconds",
        "execution_delay_seconds",
        "slippage_bps",
        "fee_rate",
        "fee_exponent",
        "tick_size",
        "min_order_size",
    )
    config = {field: getattr(args, field) for field in fields if hasattr(args, field)}
    config["strategies"] = list(strategy_names)
    return config


def _paper_run_cycle_callback(conn, run_id: str, mode: str, progress_every_cycles: int = 0):
    progress_every_cycles = max(0, int(progress_every_cycles or 0))

    def on_cycle(cycles_completed, latest_verifications, best_verification, passed):
        config = {
            "cycles_completed": cycles_completed,
            "passed": bool(passed),
        }
        if best_verification is not None:
            config.update(
                {
                    "best_strategy": best_verification.strategy,
                    "best_final_roi": best_verification.final_roi,
                    "best_max_roi": best_verification.max_roi,
                    "best_reason": best_verification.reason,
                }
            )
        upsert_paper_run(conn, run_id, mode, config)
        if progress_every_cycles and cycles_completed % progress_every_cycles == 0:
            passed_count = sum(1 for item in latest_verifications if item.passed)
            if best_verification is None:
                detail = "no_verification"
            else:
                detail = (
                    f"best_strategy={best_verification.strategy} "
                    f"final_roi={best_verification.final_roi:.4%} "
                    f"max_roi={best_verification.max_roi:.4%} "
                    f"reason={best_verification.reason}"
                )
            top = sorted(
                latest_verifications,
                key=lambda item: (item.passed, -item.roi_gap, item.final_roi),
                reverse=True,
            )[:2]
            top_detail = ",".join(
                f"{item.strategy}:{item.final_roi:.2%}/{item.max_roi:.2%}" for item in top
            )
            print(
                f"PROGRESS run_id={run_id} cycles={cycles_completed} "
                f"strategies={len(latest_verifications)} passed_count={passed_count} "
                f"cycle_passed={passed} {detail} top={top_detail or 'n/a'}",
                flush=True,
            )

    return on_cycle


def _print_opportunity_table(opportunities: list) -> None:
    print("| Viable | Score | History | Target Notional | Required Exit | Exit Distance | Bid | Ask | Avg Entry | Entry Fee | Mark Loss | Spread | Impact | Imbalance | Reason | Outcome | Title |")
    print("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |")
    for item in opportunities:
        title = item.title.replace("|", "/")[:80]
        outcome = item.outcome.replace("|", "/")[:32]
        history = item.history_change_pct
        history_text = f"{history:.2%}" if history is not None else "n/a"
        print(
            f"| {'yes' if item.viable else 'no'} "
            f"| {item.score:.4f} "
            f"| {history_text} "
            f"| {item.target_notional:.4f} "
            f"| {item.required_exit_bid:.4f} "
            f"| {item.required_exit_distance_pct:.2%} "
            f"| {item.bid:.4f} "
            f"| {item.ask:.4f} "
            f"| {item.average_entry_price:.4f} "
            f"| {item.estimated_entry_fee:.4f} "
            f"| {item.entry_mark_to_bid_loss_pct:.2%} "
            f"| {item.spread_pct:.2%} "
            f"| {item.entry_impact_pct:.2%} "
            f"| {item.book_imbalance:.2f} "
            f"| {item.reason} "
            f"| {outcome} "
            f"| {title} |"
        )


def _print_pair_opportunity_table(opportunities: list) -> None:
    print("| Viable | Settlement ROI | Mark ROI | Cost/Set | Bid Value | Entry Fee | Outcomes | Bids | Asks | Reason | Title |")
    print("| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- | --- |")
    for item in opportunities:
        title = item.title.replace("|", "/")[:80]
        outcomes = "/".join(str(outcome).replace("|", "/")[:24] for outcome in item.outcomes)
        bids = "/".join(f"{bid:.4f}" for bid in item.bids)
        asks = "/".join(f"{ask:.4f}" for ask in item.asks)
        print(
            f"| {'yes' if item.viable else 'no'} "
            f"| {item.settlement_roi:.2%} "
            f"| {item.mark_roi:.2%} "
            f"| {item.cost_per_set:.4f} "
            f"| {item.bid_value_per_set:.4f} "
            f"| {item.entry_fee_per_set:.4f} "
            f"| {outcomes} "
            f"| {bids} "
            f"| {asks} "
            f"| {item.reason} "
            f"| {title} |"
        )


def _print_sweep_table(results: list) -> None:
    print("| Score | Fee | TP | Capital | Mark Cap | Exit Cap | Weight | Min Score | Target Notional | Required Exit | Exit Distance | Mark Loss | Bid | Ask | Outcome | Title |")
    print("| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |")
    for result in results:
        config = result.config
        item = result.opportunity
        title = item.title.replace("|", "/")[:80]
        outcome = item.outcome.replace("|", "/")[:32]
        print(
            f"| {item.score:.4f} "
            f"| {result.fee_rate:.4f} "
            f"| {config.take_profit_pct:.2%} "
            f"| {config.capital_fraction:.2f} "
            f"| {config.max_entry_mark_to_bid_loss_pct:.2%} "
            f"| {config.max_required_exit_distance_pct:.2%} "
            f"| {config.required_exit_distance_weight:.1f} "
            f"| {config.min_score:.4f} "
            f"| {item.target_notional:.4f} "
            f"| {item.required_exit_bid:.4f} "
            f"| {item.required_exit_distance_pct:.2%} "
            f"| {item.entry_mark_to_bid_loss_pct:.2%} "
            f"| {item.bid:.4f} "
            f"| {item.ask:.4f} "
            f"| {outcome} "
            f"| {title} |"
        )


def _print_verification_table(verifications: list) -> None:
    if not verifications:
        return
    print("verification_by_strategy:")
    print("| Passed | Strategy | Final ROI | Max ROI | ROI Gap | Required Gain | Orders | Filled | Flat | Reason |")
    print("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |")
    ranked = sorted(verifications, key=lambda item: (item.passed, item.final_roi), reverse=True)
    for item in ranked:
        print(
            f"| {'yes' if item.passed else 'no'} "
            f"| {item.strategy} "
            f"| {item.final_roi:.4%} "
            f"| {item.max_roi:.4%} "
            f"| {item.roi_gap:.4%} "
            f"| {item.required_position_gain_pct:.4%} "
            f"| {item.orders} "
            f"| {item.filled_orders} "
            f"| {'yes' if item.flat else 'no'} "
            f"| {item.reason} |"
        )


if __name__ == "__main__":
    raise SystemExit(main())
