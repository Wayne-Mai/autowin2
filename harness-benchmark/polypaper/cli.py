from __future__ import annotations

import argparse
import json
from pathlib import Path
import time
from typing import List
from uuid import uuid4

from .client import PublicPolymarketClient, leaderboard_pages
from .dashboard import serve_dashboard
from .marketdata import order_book_from_clob, token_ids_from_market
from .models import Quote, TraderTrade
from .opportunity import score_adaptive_target_opportunity, score_target_opportunity, target_entry_notional
from .paper import PaperRunner
from .report import markdown_report
from .simulator import ConservativeFillModel, LatencyModel, MarketRules, PolymarketFeeModel, ReplaySimulator
from .storage import connect, init_db, insert_leaderboard, insert_order_books, insert_quotes, insert_trades
from .strategies.paper import (
    DEFAULT_TARGET_VARIANTS_ARG,
    NoTradePaperStrategy,
    RandomMarketTakerStrategy,
    TARGET_VARIANT_HELP,
    TargetProfitPaperStrategy,
    sweep_target_opportunities,
    target_strategy_from_args,
    target_strategy_from_config,
    target_sweep_configs,
    target_variant_configs,
)
from .strategies.replay import (
    ConsensusMirrorBaseline,
    NoTradeBaseline,
    RandomSameTurnoverBaseline,
    SingleTraderMirrorBaseline,
    SpecialistMirrorBaseline,
)
from .target_runner import run_until_target
from .verification import verify_target_run_from_path


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
    replay.add_argument("--initial-cash", type=float, default=10000.0)
    replay.add_argument("--seed", type=int, default=42)

    paper = sub.add_parser("paper-run", help="Run an online public-data paper simulation")
    paper.add_argument("--db", default="data/polypaper.sqlite")
    paper.add_argument("--run-id", default="")
    paper.add_argument("--cycles", type=int, default=1)
    paper.add_argument("--interval-seconds", type=float, default=0.0)
    paper.add_argument("--market-limit", type=int, default=5)
    paper.add_argument("--max-assets", type=int, default=10)
    paper.add_argument("--market-order", default="volume_24hr")
    paper.add_argument("--market-ascending", action="store_true")
    paper.add_argument("--initial-cash", type=float, default=10000.0)
    paper.add_argument("--seed", type=int, default=42)
    paper.add_argument("--random-agents", type=int, default=1)
    paper.add_argument("--target-profit-agents", type=int, default=0)
    paper.add_argument("--portfolio-target-roi", type=float, default=0.10)
    paper.add_argument("--take-profit-pct", type=float, default=0.10)
    paper.add_argument("--target-allow-take-profit-before-target", action="store_true")
    paper.add_argument("--stop-loss-pct", type=float, default=0.03)
    paper.add_argument("--target-entry-notional", type=float, default=0.0)
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
    paper.add_argument("--target-min-momentum-observations", type=int, default=2)
    paper.add_argument("--target-min-bid-improvement-pct", type=float, default=0.001)
    paper.add_argument("--target-min-mid-improvement-pct", type=float, default=0.001)
    paper.add_argument("--target-max-spread-widen-pct", type=float, default=0.01)
    paper.add_argument("--target-cooldown-cycles-after-sell", type=int, default=3)
    paper.add_argument("--target-max-hold-cycles", type=int, default=0)
    paper.add_argument("--target-max-hold-min-progress-pct", type=float, default=0.0)
    paper.add_argument("--target-max-hold-cooldown-cycles", type=int, default=0)
    paper.add_argument("--target-max-positions", type=int, default=1)
    paper.add_argument("--target-diversify-by", default="none")
    paper.add_argument("--target-max-positions-per-group", type=int, default=0)
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

    scan = sub.add_parser("scan-target-opportunities", help="Score active markets for the target-profit agent")
    scan.add_argument("--market-limit", type=int, default=10)
    scan.add_argument("--max-assets", type=int, default=20)
    scan.add_argument("--market-order", default="volume_24hr")
    scan.add_argument("--market-ascending", action="store_true")
    scan.add_argument("--initial-cash", type=float, default=10000.0)
    scan.add_argument("--portfolio-target-roi", type=float, default=0.10)
    scan.add_argument("--take-profit-pct", type=float, default=0.10)
    scan.add_argument("--target-allow-take-profit-before-target", action="store_true")
    scan.add_argument("--target-entry-notional", type=float, default=0.0)
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
    scan.add_argument("--top", type=int, default=10)
    scan.add_argument("--json", action="store_true")

    sweep = sub.add_parser("sweep-target-opportunities", help="Search target-agent parameter grids on current books")
    sweep.add_argument("--market-limit", type=int, default=20)
    sweep.add_argument("--max-assets", type=int, default=40)
    sweep.add_argument("--market-order", default="liquidity")
    sweep.add_argument("--market-ascending", action="store_true")
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
    sweep_until.add_argument("--detection-delay-seconds", type=int, default=0)
    sweep_until.add_argument("--polling-delay-seconds", type=int, default=0)
    sweep_until.add_argument("--decision-delay-seconds", type=int, default=0)
    sweep_until.add_argument("--execution-delay-seconds", type=int, default=0)
    sweep_until.add_argument("--slippage-bps", type=float, default=0.0)
    sweep_until.add_argument("--fee-rate", type=float, default=0.0)
    sweep_until.add_argument("--fee-exponent", type=float, default=1.0)
    sweep_until.add_argument("--tick-size", type=float, default=0.01)
    sweep_until.add_argument("--min-order-size", type=float, default=1.0)
    sweep_until.add_argument("--out", default="")

    target_until = sub.add_parser("target-run-until", help="Run target paper agents until verified ROI target or max cycles")
    target_until.add_argument("--db", default="data/polypaper.sqlite")
    target_until.add_argument("--run-id", default="")
    target_until.add_argument("--max-cycles", type=int, default=60)
    target_until.add_argument("--interval-seconds", type=float, default=5.0)
    target_until.add_argument("--market-limit", type=int, default=10)
    target_until.add_argument("--max-assets", type=int, default=20)
    target_until.add_argument("--market-order", default="volume_24hr")
    target_until.add_argument("--market-ascending", action="store_true")
    target_until.add_argument("--initial-cash", type=float, default=10000.0)
    target_until.add_argument("--portfolio-target-roi", type=float, default=0.10)
    target_until.add_argument("--take-profit-pct", type=float, default=0.10)
    target_until.add_argument("--target-allow-take-profit-before-target", action="store_true")
    target_until.add_argument("--stop-loss-pct", type=float, default=0.03)
    target_until.add_argument("--target-entry-notional", type=float, default=0.0)
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
    target_until.add_argument("--target-min-momentum-observations", type=int, default=2)
    target_until.add_argument("--target-min-bid-improvement-pct", type=float, default=0.001)
    target_until.add_argument("--target-min-mid-improvement-pct", type=float, default=0.001)
    target_until.add_argument("--target-max-spread-widen-pct", type=float, default=0.01)
    target_until.add_argument("--target-cooldown-cycles-after-sell", type=int, default=3)
    target_until.add_argument("--target-max-hold-cycles", type=int, default=0)
    target_until.add_argument("--target-max-hold-min-progress-pct", type=float, default=0.0)
    target_until.add_argument("--target-max-hold-cooldown-cycles", type=int, default=0)
    target_until.add_argument("--target-max-positions", type=int, default=1)
    target_until.add_argument("--target-diversify-by", default="none")
    target_until.add_argument("--target-max-positions-per-group", type=int, default=0)
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
    if args.cmd == "scan-target-opportunities":
        opportunities = _scan_target_opportunities(args)
        if args.json:
            print(json.dumps([item.to_dict() for item in opportunities], sort_keys=True, indent=2))
        else:
            _print_opportunity_table(opportunities)
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
    wallets = sorted({trade.wallet for trade in trades})
    first_wallet = wallets[:1] or ["none"]
    specialist_map = {}
    for trade in trades:
        if trade.category:
            specialist_map.setdefault(trade.wallet, set()).add(trade.category)
    strategies = [
        NoTradeBaseline(),
        RandomSameTurnoverBaseline(seed=args.seed, trade_probability=0.5, max_notional=50.0),
        SingleTraderMirrorBaseline(wallets=first_wallet, max_notional=50.0),
        ConsensusMirrorBaseline(wallets=wallets, threshold=min(2, len(wallets) or 2), max_notional=50.0),
        SpecialistMirrorBaseline(wallet_categories=specialist_map, max_notional=50.0),
    ]
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
        ),
        initial_cash=args.initial_cash,
    )
    return simulator.run(trades, books)


def _run_paper(args) -> tuple:
    conn = connect(args.db)
    init_db(conn)
    run_id = args.run_id or f"paper-{int(time.time())}-{uuid4().hex[:8]}"
    client = PublicPolymarketClient()
    runner = _build_paper_runner(args, conn, run_id, client)
    return runner.run(cycles=args.cycles, interval_seconds=args.interval_seconds), run_id


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
    )
    return PaperRunner(
        client=client,
        conn=conn,
        run_id=run_id,
        strategies=[
            NoTradePaperStrategy(),
        ]
        + [
            target_strategy_from_args(
                args,
                name=(
                    "paper_target_profit_10pct"
                    if args.target_profit_agents == 1
                    else f"paper_target_profit_{index + 1:04d}"
                ),
            )
            for index in range(args.target_profit_agents)
        ]
        + [
            RandomMarketTakerStrategy(
                seed=args.seed + index,
                trade_probability=args.trade_probability,
                max_notional=args.max_notional,
                name=(
                    "paper_random_market_taker"
                    if args.random_agents == 1
                    else f"paper_random_market_taker_{index + 1:04d}"
                ),
            )
            for index in range(args.random_agents)
        ],
        fill_model=fill_model,
        initial_cash=args.initial_cash,
        market_limit=args.market_limit,
        max_assets=args.max_assets,
        market_order=args.market_order,
        market_ascending=args.market_ascending,
    )


def _run_target_until(args):
    conn = connect(args.db)
    init_db(conn)
    run_id = args.run_id or f"target-{int(time.time())}-{uuid4().hex[:8]}"
    client = PublicPolymarketClient()
    runner = _build_target_runner(args, conn, run_id, client)
    strategy_names = [state.strategy.name for state in runner.agent_batch]
    return run_until_target(
        runner=runner,
        conn=conn,
        run_id=run_id,
        strategy_names=strategy_names,
        target_roi=args.portfolio_target_roi,
        max_cycles=args.max_cycles,
        interval_seconds=args.interval_seconds,
        require_flat=args.require_flat,
    )


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
    )


def _run_sweep_target_until(args):
    conn = connect(args.db)
    init_db(conn)
    run_id = args.run_id or f"sweep-target-{int(time.time())}-{uuid4().hex[:8]}"
    client = PublicPolymarketClient()
    raw_sweep_results = _collect_target_sweep(args, client, top=max(args.sweep_strategies * 20, args.sweep_strategies))
    sweep_results = _unique_sweep_assets(raw_sweep_results, args.sweep_strategies)
    if not sweep_results:
        runner = _build_sweep_target_runner(args, conn, run_id, client, [])
        return run_until_target(
            runner=runner,
            conn=conn,
            run_id=run_id,
            strategy_names=[],
            target_roi=args.portfolio_target_roi,
            max_cycles=0,
            interval_seconds=0,
            require_flat=args.require_flat,
        ), sweep_results
    runner = _build_sweep_target_runner(args, conn, run_id, client, sweep_results)
    strategy_names = [state.strategy.name for state in runner.agent_batch]
    return run_until_target(
        runner=runner,
        conn=conn,
        run_id=run_id,
        strategy_names=strategy_names,
        target_roi=args.portfolio_target_roi,
        max_cycles=args.max_cycles,
        interval_seconds=args.interval_seconds,
        require_flat=args.require_flat,
    ), sweep_results


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
    )
    return PaperRunner(
        client=client,
        conn=conn,
        run_id=run_id,
        strategies=[
            _target_strategy_from_sweep_result(args, result, index + 1)
            for index, result in enumerate(sweep_results)
        ],
        fill_model=fill_model,
        initial_cash=args.initial_cash,
        market_limit=args.market_limit,
        max_assets=args.max_assets,
        market_order=args.market_order,
        market_ascending=args.market_ascending,
    )


def _target_strategy_from_sweep_result(args, result, index: int) -> TargetProfitPaperStrategy:
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
        allowed_assets=[result.opportunity.asset],
        name=name,
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


def _scan_target_opportunities(args) -> list:
    from .paper import MarketDataCollector

    client = PublicPolymarketClient()
    collector = MarketDataCollector(
        client,
        market_limit=args.market_limit,
        max_assets=args.max_assets,
        market_order=args.market_order,
        market_ascending=args.market_ascending,
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
    opportunities.sort(key=lambda item: (item.viable, item.score), reverse=True)
    return opportunities[: args.top]


def _sweep_target_opportunities(args) -> list:
    client = PublicPolymarketClient()
    return _collect_target_sweep(args, client, top=args.top)


def _collect_target_sweep(args, client, top: int) -> list:
    from .paper import MarketDataCollector

    collector = MarketDataCollector(
        client,
        market_limit=args.market_limit,
        max_assets=args.max_assets,
        market_order=args.market_order,
        market_ascending=args.market_ascending,
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


def _print_opportunity_table(opportunities: list) -> None:
    print("| Viable | Score | Target Notional | Required Exit | Exit Distance | Bid | Ask | Avg Entry | Entry Fee | Mark Loss | Spread | Impact | Imbalance | Reason | Outcome | Title |")
    print("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |")
    for item in opportunities:
        title = item.title.replace("|", "/")[:80]
        outcome = item.outcome.replace("|", "/")[:32]
        print(
            f"| {'yes' if item.viable else 'no'} "
            f"| {item.score:.4f} "
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


if __name__ == "__main__":
    raise SystemExit(main())
