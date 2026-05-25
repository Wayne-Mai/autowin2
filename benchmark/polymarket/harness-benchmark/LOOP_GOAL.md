# Loop Goal: Find Compounding-Pattern Polymarket Traders

## Target
Identify ≥50 unique wallets that pass Layer 1 thresholds from the Polymarket
orderbook-subgraph (Goldsky-hosted, prod), as the seed candidate pool for
deeper Layer 2-5 analysis.

## Layer 1 thresholds
- `n_trades_maker + n_trades_taker >= 100`
- `last_ts - first_ts >= 180 * 86400` (span ≥ 180 days)
- `n_distinct_markets >= 20`

## Per-iteration recipe
```
python3 /Users/gaga/harness-benchmark/subgraph_scan.py
```
This script:
1. Reads cursor_ts from `data/polypaper.sqlite::subgraph_pull_state`
2. Pulls 30 pages × 1000 events of OrderFilledEvents (backwards from cursor)
3. Aggregates per-wallet trade counts + first_ts/last_ts + distinct markets
4. Jumps cursor back additional 7 days (`JUMP_BACK_DAYS`)
5. Prints current Layer 1 candidate count
6. Saves state for next iter

## Stop conditions (any one)
1. `subgraph_pull_state.scan_complete == '1'` — subgraph fully scanned
2. `>=50` wallets passing Layer 1
3. 30 consecutive iterations with no new Layer 1 candidates
4. Explicit user stop

## State location
- DB: `/Users/gaga/harness-benchmark/data/polypaper.sqlite`
- Tables: `subgraph_wallets`, `subgraph_wallet_markets`, `subgraph_pull_state`

## What to do on each wake
1. Run the script (~60s wall time)
2. Check stop conditions from sqlite
3. If stopped: report final candidates, terminate loop
4. If continuing: pick a short delay (60-300s) since work is bursty and
   doesn't depend on external state changes; use ScheduleWakeup with prompt
   = same /loop task

## After loop completes
Hand off to Layer 2-5 deep analysis on the candidate pool (separate task,
not part of this loop).
