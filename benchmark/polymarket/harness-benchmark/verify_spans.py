"""
For top-N wallets in subgraph_wallets table, query the subgraph directly for
the TRUE earliest and latest OrderFilledEvent timestamp (as maker OR taker).
Updates first_ts/last_ts in-place. This bypasses the sparse-sampling problem
where span is underestimated because we only see 7-minute slices of history.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time
from urllib.request import Request, urlopen

SUBGRAPH_URL = (
    "https://api.goldsky.com/api/public/"
    "project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/prod/gn"
)
DB_PATH = "/Users/gaga/harness-benchmark/data/polypaper.sqlite"
TOP_N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
SLEEP_BETWEEN_CALLS = 0.15


def gql(query, variables=None, timeout=20):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = Request(SUBGRAPH_URL, data=body,
                  headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=timeout) as resp:
        d = json.loads(resp.read())
    if "errors" in d:
        raise RuntimeError(f"GQL errors: {d['errors']}")
    return d["data"]


def extreme_ts(wallet, direction):
    """Get earliest (asc) or latest (desc) event timestamp for a wallet
    (as either maker or taker). Returns int or None."""
    # Subgraph doesn't always support `or` in where, so run 2 queries and take min/max
    parts = []
    for role in ("maker", "taker"):
        q = f'''{{
          orderFilledEvents(first: 1, orderBy: timestamp, orderDirection: {direction},
                            where: {{ {role}: "{wallet}" }}) {{ timestamp }}
        }}'''
        d = gql(q)["orderFilledEvents"]
        if d:
            parts.append(int(d[0]["timestamp"]))
        time.sleep(SLEEP_BETWEEN_CALLS)
    if not parts:
        return None
    return min(parts) if direction == "asc" else max(parts)


def main():
    conn = sqlite3.connect(DB_PATH)
    # Ensure verification timestamp column
    try:
        conn.execute("ALTER TABLE subgraph_wallets ADD COLUMN span_verified_at INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    rows = conn.execute(
        """SELECT wallet, n_trades_maker + n_trades_taker AS n_trades, first_ts, last_ts
           FROM subgraph_wallets
           WHERE COALESCE(span_verified_at, 0) = 0
           ORDER BY n_trades DESC
           LIMIT ?""",
        (TOP_N,),
    ).fetchall()
    print(f"Verifying spans for next {len(rows)} UNVERIFIED top wallets by n_trades")

    updated = 0
    for i, (w, n_trades, sampled_first, sampled_last) in enumerate(rows, 1):
        try:
            true_first = extreme_ts(w, "asc")
            true_last = extreme_ts(w, "desc")
        except Exception as e:
            print(f"  [{i}/{len(rows)}] {w} ERR {e}")
            continue
        if true_first is None or true_last is None:
            continue
        new_first = min(sampled_first or true_first, true_first)
        new_last = max(sampled_last or true_last, true_last)
        if new_first != sampled_first or new_last != sampled_last:
            conn.execute(
                "UPDATE subgraph_wallets SET first_ts=?, last_ts=? WHERE wallet=?",
                (new_first, new_last, w),
            )
            updated += 1
        conn.execute(
            "UPDATE subgraph_wallets SET span_verified_at=? WHERE wallet=?",
            (int(time.time()), w),
        )
        span_d = (new_last - new_first) / 86400
        if i % 25 == 0 or span_d >= 180:
            print(f"  [{i}/{len(rows)}] {w}  trades={n_trades}  TRUE span={span_d:.0f}d")
    conn.commit()
    print(f"\nUpdated {updated} wallet rows with verified spans")

    # Recompute layer1
    layer1 = conn.execute(
        """SELECT wallet, n_trades_maker + n_trades_taker AS n_trades,
                  first_ts, last_ts, n_distinct_markets, vol_collateral_raw
           FROM subgraph_wallets
           WHERE (n_trades_maker + n_trades_taker) >= 100
             AND (last_ts - first_ts) >= 180 * 86400
             AND n_distinct_markets >= 20
           ORDER BY n_trades DESC
           LIMIT 100""",
    ).fetchall()
    print(f"\nLayer 1 candidates after span verification: {len(layer1)}")
    for w, n_trades, ft, lt, nm, vol in layer1[:20]:
        span_d = (lt - ft) / 86400
        print(f"  {w}  trades={n_trades:>7d}  span={span_d:>5.0f}d  markets={nm:>4d}  vol_usdc={vol/1e6:>9.0f}")
    conn.execute(
        "INSERT INTO subgraph_pull_state(key,value) VALUES('last_layer1_count',?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(len(layer1)),))
    conn.commit()


if __name__ == "__main__":
    main()
