"""
Subgraph full-network scan for Polymarket compounding-pattern traders.

State machine designed for /loop iteration:
- Reads cursor from sqlite (subgraph_pull_state.cursor_ts)
- Pulls one batch of OrderFilledEvents (page_size * max_pages_per_iter)
- Updates per-wallet aggregates in subgraph_wallets table
- Reports candidates passing Layer 1 thresholds
- Decides whether more work remains

Idempotent: re-running with the same cursor produces the same state.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from collections import defaultdict
from typing import Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SUBGRAPH_URL = (
    "https://api.goldsky.com/api/public/"
    "project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/prod/gn"
)
DB_PATH = "/Users/gaga/harness-benchmark/data/polypaper.sqlite"

# Pagination & batch sizing
PAGE_SIZE = 1000               # subgraph max first=1000
MAX_PAGES_PER_ITER = 30        # ~30k events per /loop wake (≈ 30-60s wall time)
SLEEP_BETWEEN_PAGES = 0.25
SUBGRAPH_SKIP_CAP = 5000       # skip past 5000 returns errors

# After pulling a 30k-event sample, jump cursor backwards by this many extra
# days. This produces a sparse multi-window sample across history (instead of
# walking 7 min of event-time per iter). Long-span wallets appear in multiple
# windows, allowing Layer 1 (span>=180d) candidates to surface in O(26) iters.
JUMP_BACK_DAYS = 7

# Layer 1 (sample/breadth) thresholds for "candidate" reporting
LAYER1 = {
    "n_trades_min": 100,
    "active_span_days_min": 180,
    "n_distinct_markets_min": 20,
}

DDL = """
CREATE TABLE IF NOT EXISTS subgraph_wallets (
  wallet TEXT PRIMARY KEY,
  n_trades_maker INTEGER NOT NULL DEFAULT 0,
  n_trades_taker INTEGER NOT NULL DEFAULT 0,
  first_ts INTEGER,
  last_ts INTEGER,
  n_distinct_markets INTEGER NOT NULL DEFAULT 0,
  vol_collateral_raw REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS subgraph_wallet_markets (
  wallet TEXT NOT NULL,
  asset_id TEXT NOT NULL,
  trade_count INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (wallet, asset_id)
);
CREATE TABLE IF NOT EXISTS subgraph_pull_state (
  key TEXT PRIMARY KEY,
  value TEXT
);
CREATE INDEX IF NOT EXISTS idx_subgraph_wallets_trades
  ON subgraph_wallets(n_trades_maker, n_trades_taker);
"""


def gql(query: str, variables: Optional[dict] = None, timeout: int = 30):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = Request(
        SUBGRAPH_URL,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
    )
    with urlopen(req, timeout=timeout) as resp:
        d = json.loads(resp.read())
    if "errors" in d:
        raise RuntimeError(f"GraphQL errors: {d['errors']}")
    return d["data"]


def ensure_db(conn):
    conn.executescript(DDL)
    conn.commit()


def get_state(conn, key, default=None):
    row = conn.execute("SELECT value FROM subgraph_pull_state WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def set_state(conn, key, value):
    conn.execute(
        "INSERT INTO subgraph_pull_state(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, str(value)),
    )


def pull_page(cursor_ts: Optional[int], skip: int = 0):
    """Pull one page of OrderFilledEvents ordered by timestamp DESC, with
    optional `timestamp_lt: cursor_ts` cursor. Returns list of events."""
    where = f"where: {{ timestamp_lt: \"{cursor_ts}\" }}" if cursor_ts is not None else ""
    q = f"""{{
      orderFilledEvents(
        first: {PAGE_SIZE}
        skip: {skip}
        orderBy: timestamp
        orderDirection: desc
        {where}
      ) {{
        timestamp
        maker
        taker
        makerAssetId
        takerAssetId
        makerAmountFilled
        takerAmountFilled
      }}
    }}"""
    return gql(q)["orderFilledEvents"]


def apply_batch(conn, batch):
    """Update per-wallet aggregates from a batch of events.

    For each fill:
      - count +1 for both maker and taker
      - update first_ts / last_ts
      - track per-wallet distinct markets via subgraph_wallet_markets
      - accumulate USDC volume (the side where assetId == "0" is collateral)

    'Market' here = the non-zero assetId in the pair (the conditional token).
    """
    # Accumulate in-memory first to minimize sqlite churn
    per_wallet_trades = defaultdict(lambda: {"maker": 0, "taker": 0, "min_ts": None, "max_ts": None, "vol": 0.0})
    per_wallet_markets = defaultdict(int)  # (wallet, asset) -> count

    for ev in batch:
        ts = int(ev["timestamp"])
        maker = ev["maker"].lower()
        taker = ev["taker"].lower()
        m_asset = ev["makerAssetId"]
        t_asset = ev["takerAssetId"]
        # Identify the non-collateral asset = the conditional token ("market")
        token_asset = t_asset if m_asset == "0" else m_asset
        # USDC side amount in raw units (6 decimals)
        usdc_raw = int(ev["makerAmountFilled"] if m_asset == "0" else ev["takerAmountFilled"])

        for side, wallet in [("maker", maker), ("taker", taker)]:
            w = per_wallet_trades[wallet]
            w[side] += 1
            if w["min_ts"] is None or ts < w["min_ts"]:
                w["min_ts"] = ts
            if w["max_ts"] is None or ts > w["max_ts"]:
                w["max_ts"] = ts
            w["vol"] += usdc_raw
            per_wallet_markets[(wallet, token_asset)] += 1

    # Flush to sqlite
    cur = conn.cursor()
    for wallet, w in per_wallet_trades.items():
        cur.execute(
            """INSERT INTO subgraph_wallets(wallet, n_trades_maker, n_trades_taker,
                  first_ts, last_ts, vol_collateral_raw)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(wallet) DO UPDATE SET
                  n_trades_maker = n_trades_maker + excluded.n_trades_maker,
                  n_trades_taker = n_trades_taker + excluded.n_trades_taker,
                  first_ts = MIN(first_ts, excluded.first_ts),
                  last_ts  = MAX(last_ts, excluded.last_ts),
                  vol_collateral_raw = vol_collateral_raw + excluded.vol_collateral_raw""",
            (wallet, w["maker"], w["taker"], w["min_ts"], w["max_ts"], w["vol"]),
        )
    for (wallet, asset), n in per_wallet_markets.items():
        cur.execute(
            """INSERT INTO subgraph_wallet_markets(wallet, asset_id, trade_count)
               VALUES (?, ?, ?)
               ON CONFLICT(wallet, asset_id) DO UPDATE SET
                  trade_count = trade_count + excluded.trade_count""",
            (wallet, asset, n),
        )

    # Recompute n_distinct_markets cheaply per touched wallet
    touched = {w for w, _ in per_wallet_markets.keys()}
    for w in touched:
        cnt = cur.execute(
            "SELECT COUNT(*) FROM subgraph_wallet_markets WHERE wallet=?", (w,)
        ).fetchone()[0]
        cur.execute("UPDATE subgraph_wallets SET n_distinct_markets=? WHERE wallet=?", (cnt, w))


def report_layer1(conn):
    """Wallets currently passing Layer 1 (sample/breadth) thresholds."""
    rows = conn.execute(
        """SELECT wallet, n_trades_maker + n_trades_taker AS n_trades,
                  first_ts, last_ts, n_distinct_markets, vol_collateral_raw
           FROM subgraph_wallets
           WHERE (n_trades_maker + n_trades_taker) >= ?
             AND (last_ts - first_ts) >= ?
             AND n_distinct_markets >= ?
           ORDER BY n_trades DESC
           LIMIT 50""",
        (LAYER1["n_trades_min"], LAYER1["active_span_days_min"] * 86400, LAYER1["n_distinct_markets_min"]),
    ).fetchall()
    return rows


def progress_stats(conn):
    return conn.execute(
        """SELECT COUNT(*) AS n_wallets,
                  SUM(n_trades_maker + n_trades_taker) AS total_events_credited
           FROM subgraph_wallets"""
    ).fetchone()


def main():
    conn = sqlite3.connect(DB_PATH)
    ensure_db(conn)

    cursor_ts = get_state(conn, "cursor_ts")
    cursor_ts = int(cursor_ts) if cursor_ts and cursor_ts != "None" else None
    total_events_pulled = int(get_state(conn, "total_events_pulled", 0))
    iter_n = int(get_state(conn, "iter_n", 0)) + 1

    print(f"[iter {iter_n}] starting; cursor_ts={cursor_ts}; total_events_pulled_so_far={total_events_pulled}")

    pulled_this_iter = 0
    new_cursor = cursor_ts
    pages = 0
    while pages < MAX_PAGES_PER_ITER:
        try:
            batch = pull_page(new_cursor, skip=0)
        except Exception as e:
            print(f"  ERR pull at cursor={new_cursor}: {e}")
            break
        if not batch:
            print("  (empty batch — reached oldest events)")
            new_cursor = None  # marks completion
            break
        apply_batch(conn, batch)
        conn.commit()
        oldest_ts = min(int(e["timestamp"]) for e in batch)
        new_cursor = oldest_ts  # next page: timestamp_lt this
        pulled_this_iter += len(batch)
        pages += 1
        if pages % 5 == 0 or pages == 1:
            print(f"  page {pages}/{MAX_PAGES_PER_ITER}: oldest_ts={oldest_ts} ({pulled_this_iter} events this iter)")
        time.sleep(SLEEP_BETWEEN_PAGES)

    total_events_pulled += pulled_this_iter
    # After pulling a window, jump cursor backwards by JUMP_BACK_DAYS to sample
    # a different historical region next iter. Skip when scan is complete.
    jumped_cursor = new_cursor
    if new_cursor is not None and pulled_this_iter > 0:
        jumped_cursor = new_cursor - JUMP_BACK_DAYS * 86400
        print(f"  jump cursor: {new_cursor} -> {jumped_cursor} (back {JUMP_BACK_DAYS}d)")
    set_state(conn, "cursor_ts", jumped_cursor)
    set_state(conn, "total_events_pulled", total_events_pulled)
    set_state(conn, "iter_n", iter_n)
    set_state(conn, "last_iter_unix", int(time.time()))
    set_state(conn, "last_window_oldest_ts", new_cursor)
    conn.commit()

    n_wallets, total_credited = progress_stats(conn)
    print(f"\n[iter {iter_n}] done. pulled={pulled_this_iter} events; cursor->{new_cursor}")
    print(f"  cumulative wallets seen: {n_wallets} | total event-credits: {total_credited}")

    layer1 = report_layer1(conn)
    n_candidates = len(layer1)
    prev_n = int(get_state(conn, "last_layer1_count", 0))
    consec_no_new = int(get_state(conn, "consec_iters_no_new", 0))
    # Only count "no new candidates" iters after we've found at least one.
    # Otherwise the counter races to 30 before candidates can possibly emerge
    # (need ~26 iters to reach 180d span coverage).
    if n_candidates > 0 and n_candidates <= prev_n:
        consec_no_new += 1
    elif n_candidates > prev_n:
        consec_no_new = 0
    # else: still at 0 candidates, leave counter at 0 (waiting for first hit)
    set_state(conn, "last_layer1_count", n_candidates)
    set_state(conn, "consec_iters_no_new", consec_no_new)
    conn.commit()

    print(f"  Layer 1 candidates so far: {n_candidates}  (consec_no_new={consec_no_new})")
    for w, n_trades, first_ts, last_ts, n_markets, vol in layer1[:10]:
        span_d = (last_ts - first_ts) / 86400
        print(f"    {w}  trades={n_trades}  span={span_d:.0f}d  markets={n_markets}  vol_usdc={vol/1e6:.0f}")

    # Decide: more work to do?
    if new_cursor is None:
        print("\nSTOP: subgraph fully scanned, no more events to pull")
        set_state(conn, "scan_complete", "1")
        conn.commit()
        return 0
    if n_candidates >= 50:
        print(f"\nSTOP: reached >=50 Layer 1 candidates")
        return 0
    if consec_no_new >= 30:
        print(f"\nSTOP: 30 consecutive iters with no new Layer 1 candidates")
        return 0
    print(f"\nCONTINUE: schedule next /loop wake")
    return 2  # signal "continue"


if __name__ == "__main__":
    sys.exit(main())
