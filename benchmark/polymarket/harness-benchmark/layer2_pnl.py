"""
Layer 2: PnL reconstruction for L3 survivors via Polymarket data-api /activity.

For each L3-pass wallet:
  - pull full activity via timestamp-cursor pagination
  - reconstruct cash-flow PnL: BUY -size*price, SELL +size*price,
    REDEEM/REWARD/MERGE +usdcSize
  - compute win_rate over resolved markets (REDEEM markers)
  - max drawdown % of capital deployed (cumulative outflow)
  - monthly positive %
  - layer2_pass = positive PnL AND win_rate >= 0.45 AND mDD < 60% AND mo_pos >= 45%

Writes columns to candidate_metrics.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ACT_URL = "https://data-api.polymarket.com/activity"
DB_PATH = "/Users/gaga/harness-benchmark/data/polypaper.sqlite"
PAGE_SIZE = 500


def http_get(url, params, retries=3):
    for attempt in range(retries):
        try:
            req = Request(f"{url}?{urlencode(params)}", headers={"User-Agent": "Mozilla/5.0"})
            return json.loads(urlopen(req, timeout=25).read())
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(1.0 + attempt)


def get_activity(wallet):
    out = []
    cursor = None
    seen = set()
    for _ in range(200):  # cap pages
        params = {"user": wallet, "limit": PAGE_SIZE}
        if cursor is not None:
            params["end"] = cursor
        batch = http_get(ACT_URL, params)
        if not batch:
            break
        new_count = 0
        emin = None
        for a in batch:
            k = (a.get("timestamp"), a.get("transactionHash"), a.get("asset"), a.get("type"))
            if k in seen:
                continue
            seen.add(k)
            out.append(a)
            new_count += 1
            ts = a.get("timestamp")
            if ts is not None and (emin is None or ts < emin):
                emin = ts
        if new_count == 0 or emin is None:
            break
        cursor = emin
        if len(batch) < PAGE_SIZE:
            break
        time.sleep(0.3)
    return out


def cash_flow(ev):
    t = ev.get("type")
    if t == "TRADE":
        size = float(ev.get("size") or 0)
        price = float(ev.get("price") or 0)
        return -size * price if ev.get("side") == "BUY" else +size * price
    if t in ("REDEEM", "REWARD", "MERGE"):
        return +float(ev.get("usdcSize") or 0)
    return 0.0


def analyze(acts):
    if not acts:
        return None
    acts = sorted(acts, key=lambda x: x.get("timestamp") or 0)

    market_pnl = defaultdict(float)
    monthly = defaultdict(float)
    cum = 0.0
    equity = []
    out_total = 0.0
    in_total = 0.0
    for ev in acts:
        cf = cash_flow(ev)
        cum += cf
        equity.append(cum)
        ts = ev.get("timestamp")
        if ts:
            month = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m")
            monthly[month] += cf
        if ev.get("conditionId"):
            market_pnl[ev["conditionId"]] += cf
        if cf < 0:
            out_total += -cf
        else:
            in_total += cf

    resolved = {e["conditionId"] for e in acts if e.get("type") == "REDEEM"}
    n_resolved = len(resolved)
    wins = sum(1 for cid in resolved if market_pnl[cid] > 0)
    win_rate = wins / max(n_resolved, 1)

    peak = float("-inf")
    max_dd_abs = 0.0
    for v in equity:
        if v > peak:
            peak = v
        if peak - v > max_dd_abs:
            max_dd_abs = peak - v
    max_dd_pct = (max_dd_abs / out_total * 100) if out_total > 0 else 0

    n_months = len(monthly)
    n_pos_months = sum(1 for m in monthly if monthly[m] > 0)
    mo_pos_pct = (n_pos_months / n_months * 100) if n_months else 0

    return {
        "n_events": len(acts),
        "n_resolved": n_resolved,
        "win_rate": win_rate,
        "final_pnl": cum,
        "max_dd_pct": max_dd_pct,
        "n_months": n_months,
        "mo_pos_pct": mo_pos_pct,
        "out_total": out_total,
    }


def main():
    conn = sqlite3.connect(DB_PATH)
    # Ensure columns exist
    for col in ("recon_pnl_usdc REAL", "n_resolved_markets INTEGER", "win_rate REAL",
                "max_drawdown_pct REAL", "n_months_active INTEGER",
                "monthly_positive_pct REAL", "layer2_pass INTEGER",
                "capital_deployed_usdc REAL"):
        try:
            conn.execute(f"ALTER TABLE candidate_metrics ADD COLUMN {col}")
        except sqlite3.OperationalError:
            pass

    survivors = [r[0] for r in conn.execute(
        "SELECT wallet FROM candidate_metrics WHERE layer3_pass=1"
    ).fetchall()]
    print(f"Layer 2: PnL reconstruction on {len(survivors)} L3 survivors\n")
    print(f"{'wallet':45s} {'events':>7s} {'PnL$k':>9s} {'wins%':>6s} {'mDD%':>6s} {'mo+%':>6s} {'n_res':>6s} pass")
    print("-" * 110)

    passed = []
    for w in survivors:
        try:
            acts = get_activity(w)
        except Exception as e:
            print(f"  {w}  ERR {e}")
            continue
        m = analyze(acts)
        if not m:
            print(f"  {w}  no events")
            continue
        l2_pass = int(
            m["final_pnl"] > 0
            and m["win_rate"] >= 0.45
            and m["max_dd_pct"] < 60
            and m["mo_pos_pct"] >= 45
        )
        conn.execute("""UPDATE candidate_metrics SET
            recon_pnl_usdc=?, n_resolved_markets=?, win_rate=?, max_drawdown_pct=?,
            n_months_active=?, monthly_positive_pct=?, layer2_pass=?, capital_deployed_usdc=?
            WHERE wallet=?""",
            (m["final_pnl"], m["n_resolved"], m["win_rate"], m["max_dd_pct"],
             m["n_months"], m["mo_pos_pct"], l2_pass, m["out_total"], w))
        print(f"{w} {m['n_events']:>7d} {m['final_pnl']/1e3:>8.1f} "
              f"{m['win_rate']*100:>5.1f} {m['max_dd_pct']:>5.1f} {m['mo_pos_pct']:>5.1f} "
              f"{m['n_resolved']:>6d}  {'PASS' if l2_pass else 'fail'}")
        if l2_pass:
            passed.append(w)
        time.sleep(0.2)

    conn.commit()
    print(f"\nLayer 2 survivors: {len(passed)}/{len(survivors)}")


if __name__ == "__main__":
    main()
