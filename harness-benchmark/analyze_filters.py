"""
Compute Layer 1-2 'compounding pattern' filter stats from per-wallet activity
JSON snapshots, then apply pass/fail thresholds.

Reads:  data/0x*.json  (produced by pull_top20.py)
Writes: data/_filter_report.json  +  prints a table to stdout

Filter thresholds (Layer 1-2, see project_polymarket_benchmark memory):
  Layer 1 (sample / breadth):
    n_trades              >= 100
    active_span_days      >= 180
    n_distinct_markets    >= 20
  Layer 2 (compounding curve shape):
    monthly_positive_pct  >= 60%
    max_drawdown_pct      <= 30%
    bankroll_growth_x     >= 2.0   (cash from $0; we use net cash inflow)
    single_market_share   <= 25%   (no single-event dominance)
"""
import json
import os
import sys
import glob
from collections import defaultdict
from datetime import datetime, timezone

DATA_DIR = "/Users/gaga/harness-benchmark/data"

THRESHOLDS = {
    "n_trades_min": 100,
    "active_span_days_min": 180,
    "n_distinct_markets_min": 20,
    "monthly_positive_pct_min": 60.0,
    "max_drawdown_pct_max": 30.0,
    "bankroll_growth_x_min": 2.0,
    "single_market_share_max": 25.0,
}


def event_cash_flow(ev):
    """Return signed USDC delta to the trader's cash account.
    BUY  TRADE:  -size * price (paid)
    SELL TRADE:  +size * price (received)
    REDEEM:      +usdcSize    (winnings paid out at resolution)
    REWARD:      +usdcSize    (LP rebate)
    MERGE:       +usdcSize    (YES+NO consolidated back to $1 USDC; net cash IN)
    """
    t = ev.get("type")
    if t == "TRADE":
        size = float(ev.get("size") or 0)
        price = float(ev.get("price") or 0)
        side = ev.get("side")
        if side == "BUY":
            return -size * price
        elif side == "SELL":
            return +size * price
        else:
            return 0.0
    elif t in ("REDEEM", "REWARD", "MERGE"):
        return +float(ev.get("usdcSize") or 0)
    return 0.0


def per_market_pnl(events):
    """Net cash flow per conditionId. Markets with no REDEEM are still 'open'."""
    pnl = defaultdict(float)
    resolved = set()
    for ev in events:
        cid = ev.get("conditionId")
        if not cid:
            continue
        pnl[cid] += event_cash_flow(ev)
        if ev.get("type") == "REDEEM":
            resolved.add(cid)
    return pnl, resolved


def month_key(ts):
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return f"{dt.year:04d}-{dt.month:02d}"


def analyze_wallet(meta, events):
    if not events:
        return {"wallet": meta["proxyWallet"], "name": meta.get("pseudonym"), "error": "no_events"}

    events = sorted(events, key=lambda e: e.get("timestamp") or 0)
    n_total = len(events)
    trades = [e for e in events if e.get("type") == "TRADE"]
    n_trades = len(trades)
    n_markets = len({e.get("conditionId") for e in trades if e.get("conditionId")})

    ts_min = events[0]["timestamp"]
    ts_max = events[-1]["timestamp"]
    span_days = (ts_max - ts_min) / 86400

    # Equity curve = cumulative cash flow
    equity = []
    cum = 0.0
    monthly = defaultdict(float)
    for ev in events:
        cf = event_cash_flow(ev)
        cum += cf
        equity.append((ev["timestamp"], cum))
        monthly[month_key(ev["timestamp"])] += cf

    months_sorted = sorted(monthly.keys())
    n_months = len(months_sorted)
    n_pos_months = sum(1 for m in months_sorted if monthly[m] > 0)
    monthly_pos_pct = (n_pos_months / n_months * 100) if n_months else 0

    # Drawdown reformulated for traders who run deep capital deficit before payouts:
    # Track running peak AND running trough. max_dd_abs = peak - subsequent_trough.
    # Normalize by 'capital at risk' = max(cumulative_gross_outflow). This is
    # the USDC the trader pushed in to fund positions — analog of bankroll deployed.
    peak = float("-inf")
    max_dd_abs = 0.0
    cum_outflow = 0.0
    max_outflow = 0.0  # gross USDC sent out (BUYs); proxy for capital deployed
    for ts, val in equity:
        if val > peak:
            peak = val
        if peak - val > max_dd_abs:
            max_dd_abs = peak - val
    for ev in events:
        cf = event_cash_flow(ev)
        if cf < 0:
            cum_outflow += -cf
            if cum_outflow > max_outflow:
                max_outflow = cum_outflow
        else:
            cum_outflow = max(0.0, cum_outflow - cf)
    # Use max_outflow (or max_deficit) as the capital base — robust to deficit periods
    min_equity = min(v for _, v in equity)
    capital_base = max(max_outflow, -min_equity, 1.0)
    max_dd_pct = (max_dd_abs / capital_base * 100) if capital_base > 0 else 0

    final_pnl = equity[-1][1]
    max_equity = max(v for _, v in equity)
    # Compounding growth = final realized PnL / capital deployed.
    # >= 2.0 means doubled the capital they put at risk.
    bankroll_growth_x = (final_pnl / capital_base) if capital_base > 0 else 0

    # Per-market concentration
    market_pnl, resolved_set = per_market_pnl(events)
    sorted_markets = sorted(market_pnl.items(), key=lambda kv: kv[1], reverse=True)
    total_pos_pnl = sum(v for v in market_pnl.values() if v > 0)
    top_market_share_pct = (sorted_markets[0][1] / total_pos_pnl * 100) if total_pos_pnl > 0 else 0

    # Drop-top-N test: PnL excluding top 5 winning markets
    pnl_ex_top5 = final_pnl - sum(v for _, v in sorted_markets[:5])

    # Side distribution
    sides = defaultdict(int)
    for e in trades:
        sides[e.get("side")] = sides.get(e.get("side"), 0) + 1

    # MM-pattern check: ratio of (BUY-SELL pairs hours apart) — proxy: avg holding period
    # Skipping for sanity-check pass; this is Layer 4 territory.

    return {
        "wallet": meta["proxyWallet"],
        "name": meta.get("pseudonym") or meta.get("name"),
        "leaderboard_profit": meta.get("amount"),
        "n_events_total": n_total,
        "n_trades": n_trades,
        "n_markets": n_markets,
        "n_markets_resolved": len(resolved_set),
        "ts_min": ts_min,
        "ts_max": ts_max,
        "span_days": round(span_days, 1),
        "buy_count": sides.get("BUY", 0),
        "sell_count": sides.get("SELL", 0),
        "buy_only": sides.get("SELL", 0) == 0,
        "final_pnl": round(final_pnl, 0),
        "max_equity": round(max_equity, 0),
        "min_equity": round(min_equity, 0),
        "max_drawdown_pct": round(max_dd_pct, 1),
        "bankroll_growth_x": round(bankroll_growth_x, 2),
        "n_months_active": n_months,
        "monthly_positive_pct": round(monthly_pos_pct, 1),
        "top_market_share_pct": round(top_market_share_pct, 1),
        "pnl_ex_top5_markets": round(pnl_ex_top5, 0),
    }


def apply_filters(stats):
    """Return (passes, list_of_failed_reasons)."""
    fails = []
    if stats.get("error"):
        return False, [stats["error"]]
    if stats["n_trades"] < THRESHOLDS["n_trades_min"]:
        fails.append(f"n_trades={stats['n_trades']}<{THRESHOLDS['n_trades_min']}")
    if stats["span_days"] < THRESHOLDS["active_span_days_min"]:
        fails.append(f"span={stats['span_days']}d<{THRESHOLDS['active_span_days_min']}d")
    if stats["n_markets"] < THRESHOLDS["n_distinct_markets_min"]:
        fails.append(f"markets={stats['n_markets']}<{THRESHOLDS['n_distinct_markets_min']}")
    # Only enforce monthly_positive_pct when we have enough months to be meaningful
    if stats["n_months_active"] >= 6:
        if stats["monthly_positive_pct"] < THRESHOLDS["monthly_positive_pct_min"]:
            fails.append(f"pos_mo={stats['monthly_positive_pct']}%<{THRESHOLDS['monthly_positive_pct_min']}%")
    else:
        fails.append(f"n_months={stats['n_months_active']}<6 (insufficient)")
    if stats["max_drawdown_pct"] > THRESHOLDS["max_drawdown_pct_max"]:
        fails.append(f"dd={stats['max_drawdown_pct']}%>{THRESHOLDS['max_drawdown_pct_max']}%")
    if stats["bankroll_growth_x"] < THRESHOLDS["bankroll_growth_x_min"]:
        fails.append(f"growth={stats['bankroll_growth_x']}x<{THRESHOLDS['bankroll_growth_x_min']}x")
    if stats["top_market_share_pct"] > THRESHOLDS["single_market_share_max"]:
        fails.append(f"concentration={stats['top_market_share_pct']}%>{THRESHOLDS['single_market_share_max']}%")
    return len(fails) == 0, fails


def main():
    paths = sorted(glob.glob(f"{DATA_DIR}/0x*.json"))
    print(f"Found {len(paths)} wallet files\n")
    results = []
    for p in paths:
        d = json.load(open(p))
        meta = d["meta"]
        acts = d.get("activity") or d.get("trades") or []
        stats = analyze_wallet(meta, acts)
        passes, fails = apply_filters(stats)
        stats["passes"] = passes
        stats["fail_reasons"] = fails
        results.append(stats)

    # Sort by leaderboard rank (profit desc)
    results.sort(key=lambda r: -(r.get("leaderboard_profit") or 0))

    # Print table
    print(f"{'name':18s} {'profit$M':>9s} {'trades':>7s} {'mkts':>5s} {'span':>6s} {'dd%':>6s} {'+mo%':>6s} {'topMkt%':>8s} {'growth':>7s} {'pass':>5s}  fail_reasons")
    print("-" * 130)
    for r in results:
        if r.get("error"):
            print(f"{r['name'][:18]:18s} ERROR: {r['error']}")
            continue
        print(f"{(r['name'] or '?')[:18]:18s} "
              f"{(r['leaderboard_profit'] or 0)/1e6:>9.2f} "
              f"{r['n_trades']:>7d} "
              f"{r['n_markets']:>5d} "
              f"{r['span_days']:>6.0f} "
              f"{r['max_drawdown_pct']:>6.1f} "
              f"{r['monthly_positive_pct']:>6.1f} "
              f"{r['top_market_share_pct']:>8.1f} "
              f"{r['bankroll_growth_x']:>7.2f} "
              f"{'PASS' if r['passes'] else 'fail':>5s}  "
              f"{','.join(r['fail_reasons'])[:60]}")

    n_pass = sum(1 for r in results if r.get("passes"))
    print(f"\n{n_pass}/{len(results)} wallets pass all Layer 1-2 filters")

    with open(f"{DATA_DIR}/_filter_report.json", "w") as f:
        json.dump({"thresholds": THRESHOLDS, "results": results}, f, indent=2)
    print(f"Report → {DATA_DIR}/_filter_report.json")


if __name__ == "__main__":
    main()
