# Polymarket Paper Harness Benchmark

Academic, read-only paper-trading harness for benchmarking strategy evaluation on
Polymarket public data.

This project is intentionally unable to place real orders. It has no private-key
support, no credential loading, and its Polymarket client only exposes allowlisted
public `GET` endpoints.

## What It Tests

- Time causality: signals are generated from replay events at or before the
  current replay clock.
- Reproducibility: fixture replays are deterministic with the same seed.
- Credible virtual execution: orders execute only after configured latency,
  walk orderbook depth when L2 snapshots are available, enforce tick/min-size
  rules, and charge configurable taker fees.
- Comparable baselines: no-trade, random same-turnover, single-trader mirror,
  consensus mirror, and specialist mirror share one simulator.
- No live trading capability: tests and client guards reject non-public or
  order-related endpoints.

## Code Layout

Strategy implementations live under `polypaper/strategies/` so new benchmark
agents can be added without mixing them into the runner or simulator:

- `polypaper/strategies/replay/`: historical replay baselines driven by
  public trader events.
- `polypaper/strategies/paper/`: online paper-run agents driven by live
  market snapshots.
- `polypaper/strategies/paper/target/`: target-profit family containing the
  implementation, named variants, and sweep helpers.

`polypaper/paper.py` owns collection, multi-agent dispatch, virtual execution,
and persistence. `polypaper/simulator.py` owns fixture replay and shared fill
rules. The legacy `polypaper.baselines` module remains as a compatibility import
shim for older scripts.

## Realism Boundaries

The harness is for strategy and infrastructure benchmarking, not an absolute
live-PnL promise.

- Fixture replay is only as realistic as the quote/orderbook snapshots supplied.
- REST polling misses intra-poll book changes; read-only WebSocket capture should
  be a later milestone for high-frequency studies.
- Mirror strategies are modeled as taker flow. Limit-order strategies need a
  queue-position model before they should be evaluated.
- Public data visibility lag is strategy-critical. Use separate detection,
  polling, decision, and execution latency parameters instead of treating a
  single delay as ground truth.

## Quick Start

```bash
python3 -m unittest discover -s tests
python3 -m polypaper.cli replay-fixture tests/fixtures/small_replay.json --out reports/small_replay.md
```

More realistic replay parameters:

```bash
python3 -m polypaper.cli replay-fixture tests/fixtures/small_replay.json \
  --out reports/small_replay.md \
  --detection-delay-seconds 30 \
  --polling-delay-seconds 15 \
  --execution-delay-seconds 60 \
  --fee-rate 0.05 \
  --tick-size 0.01 \
  --min-order-size 5
```

The replay command writes a Markdown report and prints the same summary to
stdout.

## Optional Public Data Collection

These commands only call public `GET` endpoints.

```bash
python3 -m polypaper.cli init-db --db data/polypaper.sqlite
python3 -m polypaper.cli collect-leaderboard --db data/polypaper.sqlite --limit 100
python3 -m polypaper.cli collect-trades --db data/polypaper.sqlite --wallet 0x...
python3 -m polypaper.cli collect-current-books --db data/polypaper.sqlite --market-limit 10
```

`collect-book` and `collect-current-books` persist both best bid/ask quote rows
and full L2 orderbook snapshots. Use collected data as raw evidence. For
benchmark acceptance, prefer fixture or snapshot-driven replays so results can
be reproduced exactly.

## Online Paper Smoke

`paper-run` is the continuous public-data paper simulator. It does not use top
traders. It polls active Polymarket markets, snapshots public CLOB books, runs
basic market-snapshot baselines, simulates taker fills, updates virtual
portfolios, and writes signals/fills/portfolio snapshots to SQLite.

Minimal one-cycle smoke test:

```bash
python3 -m polypaper.cli paper-run \
  --db data/polypaper.sqlite \
  --cycles 1 \
  --market-limit 1 \
  --max-assets 1 \
  --trade-probability 1 \
  --execution-delay-seconds 0 \
  --out reports/paper_smoke.md
```

Available first-pass baselines:

- `paper_no_trade`: control baseline; should produce zero orders.
- `paper_random_market_taker`: deterministic random taker baseline over market
  snapshots; useful for proving fill, fee, portfolio, and report plumbing.
- `paper_target_profit_10pct`: target-profit agent that buys a watched market,
  exits when the position or portfolio reaches the configured profit target, and
  stops opening new positions after the portfolio target is reached.

Run only the 10% target-profit agent:

```bash
python3 -m polypaper.cli paper-run \
  --db data/polypaper.sqlite \
  --cycles 3 \
  --market-limit 1 \
  --max-assets 1 \
  --random-agents 0 \
  --target-profit-agents 1 \
  --portfolio-target-roi 0.10 \
  --take-profit-pct 0.10 \
  --stop-loss-pct 0.03 \
  --target-entry-notional 0 \
  --target-capital-fraction 0.95 \
  --target-max-spread-pct 0.05 \
  --target-max-entry-impact-pct 0.05 \
  --target-max-entry-mark-to-bid-loss-pct 0.03 \
  --target-max-required-exit-distance-pct 0.12 \
  --target-max-exit-price 0.99 \
  --target-min-book-imbalance 0.05 \
  --target-depth-window-pct 0.03 \
  --target-min-momentum-observations 2 \
  --target-min-bid-improvement-pct 0.001 \
  --target-min-mid-improvement-pct 0.001 \
  --execution-delay-seconds 0 \
  --out reports/paper_target_profit.md
```

`--target-entry-notional 0` means auto-size the entry from the portfolio target
and take-profit percentage. For example, a 10% portfolio target with a 10%
take-profit needs roughly 100% of starting capital before fees and spread. The
default `--target-capital-fraction 0.95` leaves cash for fees and execution
friction. Set a positive `--target-entry-notional` to override that sizing.
`--target-adaptive-entry-sizing` lets the agent treat that amount as a maximum
instead of a fixed size. It binary-searches the largest notional that still
passes the configured L2 impact, mark-to-bid loss, exit-distance, price-band,
and cash checks. `--target-min-entry-notional` controls the smallest size it
will consider.
The target agent also checks L2 depth before entry; if the estimated average
ask for the target notional is more than `--target-max-entry-impact-pct` above
the current bid, it skips the trade.
It also rejects entries whose estimated average fill cost plus fees would
already be down more than `--target-max-entry-mark-to-bid-loss-pct` when marked
to the current bid. When omitted, the target strategy uses `--stop-loss-pct` for
that entry gate, preventing trades that would immediately violate the same
stop-loss rule after fill.
`--target-max-required-exit-distance-pct` can further reject entries whose
required exit bid is too far above the current bid. This matters for the 10%
portfolio target because fees and spread often mean a candidate still needs an
11% or larger bid move before `verify-target` can pass.
`--target-min-score` adds a final edge gate on the same score used for ranking:
exit headroom minus spread, L2 entry impact, mark-to-bid loss after estimated
fees, and weighted required-exit distance, plus weighted book imbalance. The
stricter default target variants require a non-negative score so they wait
instead of buying candidates whose fee-aware path to the target is already
unattractive by this ranking.
`--target-min-bid-price` and `--target-max-bid-price` define an optional price
band. This is useful when testing high-volatility variants that need enough
price movement to compound toward 10%, while avoiding very low-probability or
already-near-resolution contracts.
It also compares near-touch bid-side depth with ask-side depth; by default
`--target-min-book-imbalance 0.05` requires modest buy-side support in the L2
book before opening a position.
By default it also waits for at least two observations of the same token and
requires bid and mid improvement before entering. This makes a one-cycle
paper-run an observation pass; use multiple cycles when testing the target
agent online.
Open positions also have a stop-loss exit, controlled by `--stop-loss-pct`, so
long-window target runs can free capital instead of waiting indefinitely for a
target exit. After a sell, the strategy applies
`--target-cooldown-cycles-after-sell` before it can re-enter the same token.
`--target-max-hold-cycles` can force a stale position to exit after a fixed
number of post-entry observations without a target or stop-loss event. It is
progress-aware: `--target-max-hold-min-progress-pct` controls how much of the
distance from entry bid to target exit bid must be covered before the strategy
keeps holding. The default compound variant enables max-hold with a zero
progress threshold, so deteriorating positions can rotate out while flat or
improving positions avoid unnecessary fee churn. `--target-max-hold-cooldown-cycles`
prevents an asset exited by max-hold from being immediately rebought; the
compound variant applies this by default to avoid repeated fee churn in the
same stagnant token.
`--target-max-positions` lets a target agent build more than one bounded
position over multiple cycles. Each cycle still emits at most one new order,
but the strategy no longer blocks new entries solely because one position is
open when the max-position budget has room.
`--target-diversify-by` and `--target-max-positions-per-group` cap repeated
exposure to related markets. Supported grouping modes include `condition`,
`slug`, `title`, and `title_prefix`. The volatile variant defaults to
`title_prefix` with one position per group, so repeated
`Bitcoin Up or Down - ...` windows do not consume the whole position budget.
For accumulation experiments, `--target-allow-take-profit-before-target` allows
the agent to close a smaller profitable trade before the whole portfolio has
reached 10%, then re-enter and compound realized gains until the flat verifier
passes. The compound target variant uses a smaller default take-profit step and
computes the exit bid after estimated exit fees, so a sell only triggers when
net proceeds satisfy the configured step.
`target-run-until` also includes a `compound_quality` variant by default. It is
the stricter compound agent: it uses the same fee-aware 1% realized-profit step
but only enters when estimated mark-to-bid loss is small and the required exit
bid is close to the current bid. This keeps the benchmark from selecting
long-shot markets simply because they have large theoretical headroom.
The default target batch also includes `volatile_compound`, which is a separate
high-movement probe. It uses a mid-price band, a 50% maximum capital slice,
adaptive entry sizing, wider stop loss, and a larger fee-aware take-profit step
to test short-horizon markets without weakening the stricter `compound_quality`
baseline. Unlike the cautious variants, it does not wait for a second momentum
observation before entry; adaptive sizing and max-hold exit are the main risk
controls. It also caps estimated entry mark-to-bid loss at 5% by default; if
even the minimum adaptive size cannot pass that gate, the agent waits instead
of buying into fee and spread drag.
`micro_compound` is the more aggressive sweep-informed variant. It uses a 1%
fee-aware realized-profit step, adaptive sizing, an 8% mark-to-bid entry cap,
and a 20% maximum required-exit-distance cap. It exists to test whether many
small realized wins can compound toward the 10% verifier when current books do
not offer low-friction entries.
`convex_tick` is a separate low-price/high-movement probe. It targets contracts
below 20c with a 20% fee-aware take-profit step, wider spread and mark-loss
limits, and a two-observation momentum gate. It is meant for small-account
paper experiments where one or two favorable ticks can plausibly reach the 10%
ROI verifier, while keeping that high-risk behavior out of the stricter quality
variants.
The high-movement variants default to a three-position budget so several small
adaptive entries can contribute to the portfolio target, while the title-prefix
group cap prevents those entries from all being the same repeated event family.

Scan current public markets for target-compatible candidates before running:

```bash
python3 -m polypaper.cli scan-target-opportunities \
  --market-limit 20 \
  --max-assets 40 \
  --market-order volume_24hr \
  --portfolio-target-roi 0.10 \
  --take-profit-pct 0.10 \
  --target-entry-notional 0 \
  --target-max-exit-price 0.99 \
  --target-min-book-imbalance 0.05 \
  --target-max-entry-mark-to-bid-loss-pct 0.03 \
  --target-required-exit-distance-weight 2.0 \
  --target-min-score 0 \
  --top 10
```

The scanner ranks candidates by required exit bid, spread, estimated L2 entry
impact, mark-to-bid loss after estimated fees, and near-touch book imbalance.
Market discovery defaults to `--market-order volume_24hr` with descending
ordering and `active=true`, following the public Gamma market API ordering
parameters. You can switch to `--market-order liquidity` when you want the
candidate set to emphasize depth over recent volume.
It is still only an opportunity filter, not a prediction model.

Search current books across a parameter grid before promoting a new target
variant:

```bash
python3 -m polypaper.cli sweep-target-opportunities \
  --market-limit 20 \
  --max-assets 40 \
  --market-order liquidity \
  --take-profit-pcts 0.01,0.02,0.03,0.05 \
  --capital-fractions 0.05,0.10,0.20,0.50 \
  --target-max-entry-mark-to-bid-loss-pcts 0.02,0.03,0.05 \
  --target-max-required-exit-distance-pcts 0.03,0.05,0.10,0.20 \
  --target-min-scores 0,0.01,0.02 \
  --top 20
```

This command uses one public-data snapshot and ranks viable strategy configs
without placing paper orders. It is intended for research iteration: use it to
identify candidates, then run `target-run-until` with the matching named or
explicit target parameters and verify the resulting run.

To turn the current sweep into runnable agents immediately:

```bash
python3 -m polypaper.cli sweep-target-run-until \
  --db data/polypaper.sqlite \
  --run-id sweep-target-research \
  --max-cycles 60 \
  --interval-seconds 5 \
  --market-limit 80 \
  --max-assets 120 \
  --market-order volume_24hr \
  --sweep-strategies 5 \
  --require-flat \
  --out reports/sweep_target_research.md
```

The command first selects the top sweep configurations from the current public
books, then creates one independent paper agent per selected config and runs
the same SQLite verifier used by `target-run-until`. Each generated agent is
scoped to the asset it was selected for and, by default, waits for a second
observation with positive bid and mid movement before entry. This keeps the
research run from buying solely because a single static book looked feasible.

Verify a completed run from SQLite:

```bash
python3 -m polypaper.cli verify-target \
  --db data/polypaper.sqlite \
  --run-id <paper_run_id> \
  --strategy paper_target_profit_10pct \
  --target-roi 0.10 \
  --require-flat
```

Run a long-window target experiment that stops as soon as SQLite verification
passes:

```bash
python3 -m polypaper.cli target-run-until \
  --db data/polypaper.sqlite \
  --max-cycles 120 \
  --interval-seconds 5 \
  --market-limit 20 \
  --max-assets 40 \
  --portfolio-target-roi 0.10 \
  --target-variants balanced,compound,near_target,aggressive,conservative \
  --require-flat \
  --out reports/target_run_until.md
```

The command exits `0` only if a target agent reaches the requested ROI under
the verifier; otherwise it exits `1` after `--max-cycles`. Variants share the
same market-data collection and differ in capital fraction, momentum strictness,
spread/impact tolerance, book-imbalance threshold, required-exit distance
preference, and exit mode. The `near_target` variant specializes in candidates
whose verified exit threshold is closest to the current bid. The `compound`
variant specializes in smaller take-profit exits that can be reinvested toward
the 10% flat portfolio target.

The unit verification uses a favorable synthetic path and proves the target
logic can reach at least 10% ROI:

```bash
make target-profit-test
```

## Dashboard

Start the local dashboard after at least one `paper-run`:

```bash
python3 -m polypaper.cli dashboard --db data/polypaper.sqlite --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765`. The page refreshes every 3 seconds and shows:

- agent-level PnL, ROI, orders, fills, turnover, and fees
- equity curve by agent
- signal and fill action stream
- latest portfolio state from SQLite

## Scaling Agents

For scaling studies, agents should share one market-data layer. Do not let each
agent call Polymarket independently.

Recommended architecture:

```text
one collector:
  polls /markets and /book or consumes a read-only market WebSocket

many agents:
  receive the same in-memory MarketSnapshot objects
  produce signals locally

one simulator:
  applies common fee, latency, tick-size, min-size, and depth-fill rules
```

This keeps API usage proportional to watched markets, not agent count. For
example, 500 agents watching the same 50 tokens should still require roughly 50
book snapshots per polling cycle, not 25,000 requests.

Run a scaling smoke test with 25 agents sharing one market snapshot:

```bash
python3 -m polypaper.cli paper-run \
  --db data/polypaper.sqlite \
  --cycles 1 \
  --market-limit 1 \
  --max-assets 1 \
  --random-agents 25 \
  --trade-probability 1 \
  --execution-delay-seconds 0 \
  --out reports/paper_25_agents.md
```

For hundreds of agents, increase `--random-agents`; API usage still follows
`market_limit` and `max_assets`, while CPU/SQLite writes scale with agent count.
