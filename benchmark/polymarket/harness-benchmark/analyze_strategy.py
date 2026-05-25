"""
Strategy fingerprint for the two confirmed exemplars.

For each wallet:
  1. Pull full /activity, persist to data/wallet_<addr>.json
  2. From TRADE events compute per-market net position + avg cost basis
  3. Sample 20-30 markets, query CLOB /markets/{cid} for question/category/winner
  4. Print:
     - BUY price distribution (cost-basis histogram)
     - Total USDC per market distribution
     - Activity volume per week (recent vs older)
     - Specific market examples (winners and losers)
     - Hedging fingerprint (markets with both YES+NO BUYs)
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ACT_URL = "https://data-api.polymarket.com/activity"
CLOB_URL = "https://clob.polymarket.com/markets/{cid}"
DATA_DIR = "/Users/gaga/harness-benchmark/data"

WALLETS = [
    ("0x63d43bbb87f85af03b8f2f9e2fad7b54334fa2f1", "FAVORITE PICKER (88% on 4396)"),
    ("0xe3726a1b9c6ba2f06585d1c9e01d00afaedaeb38", "LONG-SHOT BETTOR (11% on 4136)"),
]
PAGE_SIZE = 500
SLEEP_ACT = 0.25
SLEEP_CLOB = 0.15


def http_get(url, params=None, retries=3, timeout=25):
    full = url + ("?" + urlencode(params) if params else "")
    for attempt in range(retries):
        try:
            req = Request(full, headers={"User-Agent": "Mozilla/5.0"})
            return json.loads(urlopen(req, timeout=timeout).read())
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(1.0 + attempt)


def pull_activity_cached(wallet):
    path = f"{DATA_DIR}/wallet_{wallet}.json"
    if os.path.exists(path):
        return json.load(open(path))
    print(f"  pulling /activity for {wallet}...")
    out = []
    cursor = None
    seen = set()
    for _ in range(200):
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
            seen.add(k); out.append(a); new_count += 1
            ts = a.get("timestamp")
            if ts is not None and (emin is None or ts < emin):
                emin = ts
        if new_count == 0 or emin is None:
            break
        cursor = emin
        if len(batch) < PAGE_SIZE:
            break
        time.sleep(SLEEP_ACT)
    with open(path, "w") as f:
        json.dump(out, f)
    return out


def per_market_summary(acts):
    """Returns {cid: {primary_outcome, shares, usdc_spent, avg_price, n_trades, ...}}"""
    state = defaultdict(lambda: defaultdict(lambda: {"shares": 0.0, "usdc": 0.0, "n_trades": 0, "title": None, "slug": None}))
    redeemed = set()
    for ev in acts:
        if ev.get("type") == "REDEEM":
            cid = ev.get("conditionId")
            if cid:
                redeemed.add(cid)
            continue
        if ev.get("type") != "TRADE":
            continue
        cid = ev.get("conditionId")
        outcome = ev.get("outcome")
        if not cid or not outcome:
            continue
        size = float(ev.get("size") or 0)
        price = float(ev.get("price") or 0)
        side = ev.get("side")
        d = state[cid][outcome]
        if side == "BUY":
            d["shares"] += size
            d["usdc"] += size * price
            d["n_trades"] += 1
        elif side == "SELL":
            d["shares"] -= size
            d["usdc"] -= size * price
        d["title"] = ev.get("title")
        d["slug"] = ev.get("slug")
    result = {}
    for cid, outs in state.items():
        # Find primary outcome (largest net long position)
        primary = max(outs.items(), key=lambda kv: kv[1]["shares"])
        primary_outcome = primary[0]
        primary_d = primary[1]
        n_outcomes_bought = sum(1 for o, d in outs.items() if d["n_trades"] > 0)
        title = primary_d["title"] or next((d["title"] for d in outs.values() if d["title"]), "?")
        slug = primary_d["slug"] or next((d["slug"] for d in outs.values() if d["slug"]), "?")
        result[cid] = {
            "primary_outcome": primary_outcome,
            "shares": primary_d["shares"],
            "usdc_spent": primary_d["usdc"],
            "avg_price": primary_d["usdc"] / primary_d["shares"] if primary_d["shares"] > 0 else 0,
            "n_trades_primary": primary_d["n_trades"],
            "all_outcomes_total_usdc": sum(d["usdc"] for d in outs.values() if d["usdc"] > 0),
            "n_outcomes_bought": n_outcomes_bought,  # 2 = hedged both sides
            "title": title,
            "slug": slug,
            "redeemed": cid in redeemed,
        }
    return result


def fetch_winner(cid):
    try:
        d = http_get(CLOB_URL.format(cid=cid), timeout=10)
    except Exception:
        return None, None, None
    tokens = d.get("tokens") or []
    closed = d.get("closed", False)
    winner = None
    for t in tokens:
        if t.get("winner"):
            winner = t.get("outcome")
    question = d.get("question")
    return closed, winner, question


def hist_text(values, bins, labels=None):
    """Simple text histogram."""
    counts = [0] * len(bins)
    for v in values:
        for i in range(len(bins) - 1):
            if bins[i] <= v < bins[i + 1]:
                counts[i] += 1
                break
        else:
            if v >= bins[-1]:
                counts[-1] += 1
    total = sum(counts)
    out = []
    for i, c in enumerate(counts[:-1]):
        bar = "█" * int(40 * c / max(total, 1))
        lab = labels[i] if labels else f"[{bins[i]:.2f}, {bins[i+1]:.2f})"
        out.append(f"  {lab:>16s} {bar} {c} ({100*c/max(total,1):.1f}%)")
    return "\n".join(out)


def analyze_wallet(wallet, label):
    print(f"\n{'='*72}\n{label}\n{wallet}\n{'='*72}")
    acts = pull_activity_cached(wallet)
    trades = [e for e in acts if e.get("type") == "TRADE"]
    n_buys = sum(1 for e in trades if e.get("side") == "BUY")
    n_sells = sum(1 for e in trades if e.get("side") == "SELL")
    n_redeems = sum(1 for e in acts if e.get("type") == "REDEEM")
    print(f"\nActivity totals: {len(acts)} events  ({n_buys} BUY  {n_sells} SELL  {n_redeems} REDEEM)")
    ts_min = min((e["timestamp"] for e in acts), default=0)
    ts_max = max((e["timestamp"] for e in acts), default=0)
    span_d = (ts_max - ts_min) / 86400
    print(f"True span: {span_d:.0f} days "
          f"({datetime.fromtimestamp(ts_min, tz=timezone.utc).strftime('%Y-%m-%d')} → "
          f"{datetime.fromtimestamp(ts_max, tz=timezone.utc).strftime('%Y-%m-%d')})")

    markets = per_market_summary(acts)
    print(f"Distinct markets BUY'd: {len(markets)}")
    n_hedged = sum(1 for m in markets.values() if m["n_outcomes_bought"] == 2)
    print(f"Markets where BOTH outcomes bought (hedged): {n_hedged} ({100*n_hedged/max(len(markets),1):.1f}%)")
    n_redeemed = sum(1 for m in markets.values() if m["redeemed"])
    print(f"Markets where they REDEEMed: {n_redeemed} ({100*n_redeemed/max(len(markets),1):.1f}%)")

    # Price-at-entry distribution
    print(f"\nCost-basis (avg entry price) distribution:")
    prices = [m["avg_price"] for m in markets.values() if 0 < m["avg_price"] <= 1]
    print(hist_text(prices, [0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 0.95, 1.0]))

    # Bet size distribution
    print(f"\nUSDC spent per market distribution:")
    sizes = [m["usdc_spent"] for m in markets.values() if m["usdc_spent"] > 0]
    print(hist_text(sizes, [0, 10, 50, 200, 1000, 5000, 20000, 100000, 1e9]))

    # Weekly activity (last 26 weeks)
    print(f"\nActivity by week (last 12 weeks, # BUY trades):")
    week_counts = Counter()
    for e in trades:
        if e.get("side") == "BUY":
            wk = datetime.fromtimestamp(e["timestamp"], tz=timezone.utc).strftime("%Y-W%V")
            week_counts[wk] += 1
    recent = sorted(week_counts.items())[-12:]
    for w, c in recent:
        print(f"  {w:>10s}  {'█'*min(int(c/5), 60)} {c}")

    # Sample 20 random resolved markets, fetch CLOB winner, show examples
    print(f"\nSample 20 specific markets (with CLOB resolution lookup):")
    sample = list(markets.items())[:20]  # first 20 by dict order (we'll show variety later)
    # Actually pick: top-USDC 10 + bottom-cost-basis 5 + redeemed 5
    by_usdc = sorted(markets.items(), key=lambda kv: -kv[1]["usdc_spent"])[:10]
    by_low_price = [kv for kv in sorted(markets.items(), key=lambda kv: kv[1]["avg_price"])
                    if kv[1]["avg_price"] > 0 and kv[1]["usdc_spent"] > 50][:5]
    by_high_price = [kv for kv in sorted(markets.items(), key=lambda kv: -kv[1]["avg_price"])
                     if kv[1]["avg_price"] < 1 and kv[1]["usdc_spent"] > 50][:5]
    seen_cids = set()
    sample = []
    for batch in [by_usdc, by_low_price, by_high_price]:
        for cid, m in batch:
            if cid not in seen_cids:
                sample.append((cid, m))
                seen_cids.add(cid)
    print(f"  (10 biggest by USDC + 5 lowest entry-price + 5 highest entry-price; deduped → {len(sample)})\n")
    print(f"  {'price':>5s} {'usdc':>8s} {'shares':>9s} {'bet':>5s} {'result':>7s} title")
    for cid, m in sample:
        closed, winner, question = fetch_winner(cid)
        if winner is None:
            result = "open" if not closed else "uncl?"
        elif winner == m["primary_outcome"]:
            result = "✓WIN"
        else:
            result = "✗LOSS"
        time.sleep(SLEEP_CLOB)
        q = (question or m["title"] or "?")[:60]
        print(f"  ${m['avg_price']:.3f} ${m['usdc_spent']:>6.0f} {m['shares']:>9.0f} "
              f"{m['primary_outcome']:>5s} {result:>7s} {q}")


def main():
    for w, label in WALLETS:
        analyze_wallet(w, label)


if __name__ == "__main__":
    main()
