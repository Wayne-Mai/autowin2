"""
Layer 3: Market-maker detection on Layer 1 candidates.

For each candidate, pulls the most recent 1000 OrderFilledEvents on each side
(maker, taker) from the orderbook-subgraph. Computes per-wallet:

  - n_buys, n_sells  (BUY = collateral->token, SELL = token->collateral)
  - sell_buy_ratio   (≈1 = scalping/MM, low = directional)
  - median_holding_period_d  (per-asset BUY→matched-SELL latency, median)
  - frac_short_holds_under_1d (fraction of matched holds under 1 day)
  - n_assets_with_round_trip (markets where they both bought AND sold)

MM heuristic (any one is sufficient to flag as MM):
  - median_holding_period_d < 1.0 AND sell_buy_ratio > 0.6
  - frac_short_holds_under_1d > 0.7
  - n_assets_with_round_trip / n_distinct_assets > 0.5  (most positions closed pre-resolution)

Writes results to candidate_metrics table; layer3_pass=1 means survived as
"non-MM, holding-style trader".
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time
from collections import defaultdict
from urllib.request import Request, urlopen

SUBGRAPH_URL = (
    "https://api.goldsky.com/api/public/"
    "project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/prod/gn"
)
DB_PATH = "/Users/gaga/harness-benchmark/data/polypaper.sqlite"
EVENTS_PER_SIDE = 1000
SLEEP = 0.15

DDL = """
CREATE TABLE IF NOT EXISTS candidate_metrics (
  wallet TEXT PRIMARY KEY,
  n_events_sampled INTEGER,
  n_buys INTEGER,
  n_sells INTEGER,
  sell_buy_ratio REAL,
  median_holding_period_d REAL,
  avg_holding_period_d REAL,
  frac_short_holds_under_1d REAL,
  n_distinct_assets INTEGER,
  n_assets_with_round_trip INTEGER,
  round_trip_ratio REAL,
  is_mm INTEGER,
  layer3_pass INTEGER
);
"""


def gql(query: str, timeout: int = 30):
    req = Request(
        SUBGRAPH_URL,
        data=json.dumps({"query": query}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
    )
    with urlopen(req, timeout=timeout) as resp:
        d = json.loads(resp.read())
    if "errors" in d:
        raise RuntimeError(d["errors"])
    return d["data"]


def pull_events(wallet: str):
    """Pull up to 2000 most recent events involving wallet (1000 as maker + 1000 as taker)."""
    events = []
    for role in ("maker", "taker"):
        q = f'''{{
          orderFilledEvents(first: {EVENTS_PER_SIDE}, orderBy: timestamp, orderDirection: desc,
                            where: {{ {role}: "{wallet}" }}) {{
            timestamp makerAssetId takerAssetId makerAmountFilled takerAmountFilled
          }}
        }}'''
        for e in gql(q)["orderFilledEvents"]:
            ts = int(e["timestamp"])
            m_asset = e["makerAssetId"]
            t_asset = e["takerAssetId"]
            # Maker's makerAssetId is what they're GIVING UP.
            # If makerAssetId == "0" (USDC collateral), maker is buying token = BUY.
            # Conversely the taker is selling the token they have for USDC = SELL.
            if m_asset == "0":
                asset = t_asset
                side = "BUY" if role == "maker" else "SELL"
            else:
                asset = m_asset
                side = "SELL" if role == "maker" else "BUY"
            events.append((ts, asset, side))
        time.sleep(SLEEP)
    return events


def compute_metrics(events):
    """Compute Layer 3 signals from a list of (ts, asset, side) events."""
    events.sort()
    per_asset_acts = defaultdict(list)
    n_buys = n_sells = 0
    for ts, asset, side in events:
        per_asset_acts[asset].append((ts, side))
        if side == "BUY":
            n_buys += 1
        elif side == "SELL":
            n_sells += 1

    # Match each SELL with the most recent prior BUY on the same asset
    holding_periods = []
    n_assets_with_round_trip = 0
    for asset, acts in per_asset_acts.items():
        buys = [ts for ts, s in acts if s == "BUY"]
        sells = [ts for ts, s in acts if s == "SELL"]
        round_trip = False
        for s_ts in sells:
            priors = [b for b in buys if b < s_ts]
            if priors:
                holding_periods.append(s_ts - max(priors))
                round_trip = True
        if round_trip:
            n_assets_with_round_trip += 1

    n_assets = len(per_asset_acts)
    if holding_periods:
        sorted_hp = sorted(holding_periods)
        avg_hp = sum(holding_periods) / len(holding_periods)
        med_hp = sorted_hp[len(sorted_hp) // 2]
        frac_short = sum(1 for h in holding_periods if h < 86400) / len(holding_periods)
    else:
        avg_hp = med_hp = None
        frac_short = 0.0

    sell_buy_ratio = n_sells / max(n_buys, 1)
    round_trip_ratio = n_assets_with_round_trip / max(n_assets, 1)

    # MM heuristic
    is_mm = False
    if med_hp is not None:
        if med_hp / 86400 < 1.0 and sell_buy_ratio > 0.6:
            is_mm = True
        if frac_short > 0.7:
            is_mm = True
        if round_trip_ratio > 0.5:
            is_mm = True

    return {
        "n_events_sampled": len(events),
        "n_buys": n_buys,
        "n_sells": n_sells,
        "sell_buy_ratio": round(sell_buy_ratio, 3),
        "median_holding_period_d": round(med_hp / 86400, 2) if med_hp else None,
        "avg_holding_period_d": round(avg_hp / 86400, 2) if avg_hp else None,
        "frac_short_holds_under_1d": round(frac_short, 3),
        "n_distinct_assets": n_assets,
        "n_assets_with_round_trip": n_assets_with_round_trip,
        "round_trip_ratio": round(round_trip_ratio, 3),
        "is_mm": int(is_mm),
    }


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(DDL)

    candidates = [r[0] for r in conn.execute("""
        SELECT wallet FROM subgraph_wallets
        WHERE (n_trades_maker + n_trades_taker) >= 100
          AND (last_ts - first_ts) >= 180*86400
          AND n_distinct_markets >= 20
        ORDER BY (n_trades_maker + n_trades_taker) DESC
    """).fetchall()]
    print(f"Analyzing {len(candidates)} Layer 1 candidates for MM patterns\n")

    survivors = []
    for i, w in enumerate(candidates, 1):
        try:
            events = pull_events(w)
        except Exception as e:
            print(f"  [{i}/{len(candidates)}] {w} ERR {e}")
            continue
        m = compute_metrics(events)
        m["wallet"] = w
        m["layer3_pass"] = int(not m["is_mm"])
        conn.execute("""INSERT OR REPLACE INTO candidate_metrics
            (wallet, n_events_sampled, n_buys, n_sells, sell_buy_ratio,
             median_holding_period_d, avg_holding_period_d, frac_short_holds_under_1d,
             n_distinct_assets, n_assets_with_round_trip, round_trip_ratio,
             is_mm, layer3_pass)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (w, m["n_events_sampled"], m["n_buys"], m["n_sells"], m["sell_buy_ratio"],
             m["median_holding_period_d"], m["avg_holding_period_d"], m["frac_short_holds_under_1d"],
             m["n_distinct_assets"], m["n_assets_with_round_trip"], m["round_trip_ratio"],
             m["is_mm"], m["layer3_pass"]))
        if not m["is_mm"]:
            survivors.append(w)
        if i % 20 == 0 or i == len(candidates):
            print(f"  [{i:>3d}/{len(candidates)}] {w}  med_hp={m['median_holding_period_d']}d  "
                  f"s/b={m['sell_buy_ratio']:.2f}  short_frac={m['frac_short_holds_under_1d']:.2f}  "
                  f"rt_ratio={m['round_trip_ratio']:.2f}  {'MM' if m['is_mm'] else 'OK'}")
    conn.commit()

    print(f"\n{'='*60}")
    print(f"Layer 3 result: {len(survivors)}/{len(candidates)} survived MM filter")
    print(f"{'='*60}\n")
    print("Top L3 survivors (ordered by n_trades from L1):")
    print(f"{'wallet':45s} {'trades':>7s} {'span':>5s} {'mkts':>5s} {'med_hp_d':>9s} {'rt_ratio':>9s}")
    rows = conn.execute("""
        SELECT sw.wallet, sw.n_trades_maker + sw.n_trades_taker AS trades,
               CAST((sw.last_ts - sw.first_ts)/86400.0 AS INT) AS span_d,
               sw.n_distinct_markets,
               cm.median_holding_period_d, cm.round_trip_ratio
        FROM subgraph_wallets sw JOIN candidate_metrics cm USING (wallet)
        WHERE cm.layer3_pass=1
          AND (sw.n_trades_maker + sw.n_trades_taker) >= 100
          AND (sw.last_ts - sw.first_ts) >= 180*86400
          AND sw.n_distinct_markets >= 20
        ORDER BY trades DESC LIMIT 30
    """).fetchall()
    for r in rows:
        hp = f"{r[4]:.2f}" if r[4] is not None else "  n/a"
        print(f"{r[0]} {r[1]:>7d} {r[2]:>5d} {r[3]:>5d} {hp:>9s} {r[5]:>9.2f}")


if __name__ == "__main__":
    main()
