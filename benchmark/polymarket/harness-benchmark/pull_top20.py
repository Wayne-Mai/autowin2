"""
Compatibility helper: pull top 20 leaderboard wallets and recent public trades.

Read-only: uses polypaper.client, which only permits allowlisted public GET
endpoints. This script is for quick data snapshots; deterministic benchmark
acceptance should use fixture replay or archived snapshots.
"""

from __future__ import annotations

import json
import os
import time

from polypaper.client import PublicPolymarketClient, leaderboard_pages


DATA_DIR = "/Users/gaga/harness-benchmark/data"
MAX_TRADES_PER_WALLET = 1000


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    client = PublicPolymarketClient()
    leaderboard = leaderboard_pages(client, limit=20)
    print(f"Leaderboard returned {len(leaderboard)} entries")

    summary = []
    for index, entry in enumerate(leaderboard, start=1):
        wallet = str(entry["proxyWallet"])
        name = entry.get("userName") or entry.get("name") or wallet[:10]
        trades = list(
            client.paged(
                "user_trades",
                wallet=wallet,
                page_size=500,
                max_items=MAX_TRADES_PER_WALLET,
            )
        )
        type_counts = {}
        for trade in trades:
            side = trade.get("side", "")
            type_counts[side] = type_counts.get(side, 0) + 1
        ts_min = min((int(trade["timestamp"]) for trade in trades), default=0)
        ts_max = max((int(trade["timestamp"]) for trade in trades), default=0)
        span_days = (ts_max - ts_min) / 86400 if trades else 0
        pnl = float(entry.get("pnl", 0.0) or 0.0)

        print(
            f"[{index:2d}/20] {name:20s} {wallet}  "
            f"pnl=${pnl:>14,.0f}  trades={len(trades):>6d}  "
            f"span={span_days:>5.0f}d  sides={type_counts}"
        )

        with open(f"{DATA_DIR}/{wallet}.json", "w", encoding="utf-8") as f:
            json.dump({"meta": entry, "trades": trades}, f, sort_keys=True)

        summary.append(
            {
                "rank": index,
                "wallet": wallet,
                "name": name,
                "pnl_usd": pnl,
                "n_trades": len(trades),
                "side_counts": type_counts,
                "ts_min": ts_min,
                "ts_max": ts_max,
                "span_days": span_days,
            }
        )
        time.sleep(0.3)

    with open(f"{DATA_DIR}/_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
    print(f"\nDone. Saved {len(summary)} wallets + summary to {DATA_DIR}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

