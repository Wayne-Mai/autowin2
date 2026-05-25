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
- Mirror strategies are modeled as taker flow by default. Maker benchmark
  suites should use the queue-position scenarios in `configs/fill_scenarios.yml`
  and compare against the optimistic legacy proxy. Public market fee metadata is
  also used for platform taker fees and maker rebates when present.
- Public data visibility lag is strategy-critical. Use separate detection,
  polling, decision, and execution latency parameters instead of treating a
  single delay as ground truth.

## Quick Start

```bash
python3 -m unittest discover -s tests
python3 -m polypaper.cli replay-fixture tests/fixtures/small_replay.json --out reports/small_replay.md
python3 -m polypaper.cli benchmark-suite \
  --fixture tests/fixtures/small_replay.json \
  --scenarios optimistic,realistic,pessimistic \
  --strategy-suite default_with_maker \
  --out-dir reports/benchmark_small
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

## Benchmark Suite

`benchmark-suite` replays the same fixture across named fill-realism scenarios
and emits strategy-level robustness metrics. It is the preferred first check
when changing fill assumptions because the market stream, seed, and strategy
suite are held constant while only the execution model changes.

Default scenarios live in `configs/fill_scenarios.yml`:

- `optimistic`: legacy maker proxy, useful as the old baseline.
- `realistic`: queue proxy with expiry, cancellation, and partial adverse fills.
- `pessimistic`: slower probabilistic queue and stronger adverse-selection
  assumptions.

Example:

```bash
python3 -m polypaper.cli benchmark-suite \
  --fixture tests/fixtures/small_replay.json \
  --fill-scenarios configs/fill_scenarios.yml \
  --scenarios optimistic,realistic,pessimistic \
  --strategy-suite default_with_maker \
  --out-dir reports/benchmark_small
```

The command writes:

- `benchmark_summary.json`: full scenarios, summary rows, and raw strategy
  results.
- `benchmark_summary.csv`: flat rows for spreadsheet analysis.
- `benchmark_summary.md`: readable comparison report.

Key columns are `roi_delta_vs_baseline`, `rank_delta_vs_baseline`, `fill_rate`,
`partial_rate`, and `miss_rate`. A maker strategy that only works under
`optimistic` and collapses under `realistic` should be treated as execution
assumption-sensitive rather than robust.

## Market Recordings

Use `record-snapshots` to turn live public order books into a reusable research
dataset. This is for internal ablation and parameter searches: record the
market stream once, then replay target agents offline many times under
different strategy and fill assumptions. The final claim should still be an
online paper run, not an offline replay.

Short ablation recording:

```bash
python3 -m polypaper.cli record-snapshots \
  --out data/recordings/polymarket_ablation_1h.json.gz \
  --recording-id polymarket-ablation-1h \
  --cycles 720 \
  --interval-seconds 5 \
  --market-limit 25 \
  --max-assets 50 \
  --market-order volume_24hr
```

Six-hour validation recording:

```bash
python3 -m polypaper.cli record-snapshots \
  --out data/recordings/polymarket_6h.json.gz \
  --recording-id polymarket-6h \
  --cycles 4320 \
  --interval-seconds 5 \
  --market-limit 50 \
  --max-assets 100 \
  --market-order volume_24hr
```

Replay target strategies against a recording with realistic maker execution:

```bash
python3 -m polypaper.cli target-replay-recording \
  --recording data/recordings/polymarket_6h.json.gz \
  --db data/polymarket_6h_replay.sqlite \
  --run-id polymarket-6h-realistic \
  --portfolio-target-roi 0.10 \
  --take-profit-pct 0.01 \
  --target-allow-take-profit-before-target \
  --target-adaptive-entry-sizing \
  --target-min-entry-notional 5 \
  --target-max-spread-pct 0.05 \
  --target-max-entry-impact-pct 0.12 \
  --target-max-entry-mark-to-bid-loss-pct 0.08 \
  --target-max-required-exit-distance-pct 0.20 \
  --target-min-book-imbalance -0.60 \
  --target-min-momentum-observations 1 \
  --target-variants compound_quality,low_friction_compound,volatile_compound,micro_compound,rolling_momentum_maker_goal,maker_convex_basket_goal,momentum_scalper_goal,spread_capture_maker_goal,outcome_basket_arb_goal \
  --require-flat \
  --maker-fill-mode queue_proxy \
  --maker-queue-ahead-fraction 1.0 \
  --maker-queue-decay 0.25 \
  --maker-max-order-age-attempts 24 \
  --maker-cancel-on-price-move \
  --maker-adverse-fill-on-price-move \
  --maker-adverse-fill-fraction 0.50 \
  --out reports/polymarket_6h_realistic.md
```

Passing a 6-hour replay is useful evidence, but it is not the final acceptance
gate. The final gate is an online virtual-paper run against live public books.

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

For online virtual-paper runs, open positions are also checked against public
Gamma market metadata for final resolution. A position is settled locally only
when the market is marked `closed=true` and `outcomePrices` are binary
approximately `1/0`; no order, cancel, wallet, or private endpoint is used.

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
below 20c with a 95% maximum capital slice, 10% fee-aware take-profit step,
wider spread and mark-loss limits, and a two-observation momentum gate. It is
meant for small-account paper experiments where one or two favorable ticks can
plausibly reach the 10% ROI verifier, while keeping that high-risk behavior out
of the stricter quality variants.
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

Run a long-window online virtual-paper target experiment. For final 6-hour
validation, set both `--min-cycles-before-pass` and
`--min-runtime-seconds-before-pass` so the run cannot pass early:

```bash
scripts/online_goal_6h.sh
```

For a detached long run that writes a log and PID file:

```bash
scripts/launch_online_goal_6h.sh
```

Stop the detached run if needed:

```bash
scripts/stop_online_goal_6h.sh
```

The command exits `0` only if enough target agents reach the requested ROI
under the verifier after the minimum online duration/cycles; otherwise it exits
`1` after `--max-cycles`. The wrapper defaults to `MIN_CYCLES_BEFORE_PASS=720`
and `MIN_RUNTIME_SECONDS_BEFORE_PASS=21600`, so wall-clock duration is the
authoritative six-hour gate while still requiring a meaningful number of online
cycles. `MAX_CYCLES` defaults to `4321` as a backstop.
By default the script uses a UTC timestamp in the SQLite DB, run id, and
markdown report path, then writes the selected values to
`reports/polymarket_online_6h_last.env` for follow-up verification. This is an
online virtual-paper run: the runner reads current public Polymarket books and
records virtual orders/fills only; it never submits real orders. Variants share
one market-data collection per cycle, and the collector uses Polymarket's
public batch book endpoint when available so
hundreds of agents can evaluate the same snapshot without each agent making its
own market-data request. The runner also gives every strategy in a cycle the
same wall-clock timestamp, so large agent batches do not make later agents see
the same market as artificially older than earlier agents. The final script
also passes `--market-prefer-keywords "up or down,updown"` so short-window
crypto markets are ranked ahead of other liquid markets while the rest of the
online universe remains available. When those preferred markets include timestamped 5m/15m
crypto Up/Down slugs, the collector ranks currently active intervals first,
then upcoming intervals, before applying the asset cap. The final script also
uses `--market-pages 3` so discovery scans multiple paginated Gamma market pages
before choosing shared CLOB books for the agent batch. Use
`--market-filter-keywords` only for ablations where non-matching markets should
be excluded entirely. The final wrapper uses a configurable latency profile
(`DETECTION_DELAY_SECONDS=1`, `POLLING_DELAY_SECONDS=5`,
`DECISION_DELAY_SECONDS=1`, `EXECUTION_DELAY_SECONDS=2` by default), queue-aware
maker fills, public Gamma market fees, and optional fallback fee/slippage env
vars for markets without fee metadata. The
`momentum_scalper_goal` variant uses taker entries/exits after short-horizon
bid/mid improvement. The `spread_capture_maker_goal` variant uses passive
entries/exits and should be tested with queue-aware maker fills. The
`outcome_basket_arb_goal` variant buys complete outcome baskets only when the
combined ask has a settlement edge, then exits when the basket bid value recovers.
`crypto_interval_anchor_goal` records an online spot anchor early in a 5m/15m
crypto Up/Down interval, then trades the matching outcome only when current spot
has moved far enough from that anchor and the net settlement payout clears the
configured edge. The interval-anchor grid also includes explicitly late-anchor
ablation variants, capped at 180 seconds after interval start, to measure how
much signal is lost when online polling misses the opening window.
`crypto_interval_close_edge_goal` uses the same observed early anchor, but waits
until the interval is near settlement before entering; this separates
early-momentum interval trades from near-close settlement-edge trades while
still using only public online observations.
`crypto_interval_book_skew_goal` trades active short-window crypto Up/Down
markets from the book-implied dominant side, which keeps the online test active
when the runner joins an interval too late to form a clean spot anchor.
`online_goal_grid` expands those families plus the public-spot crypto
directional family into candidate agents with different momentum, maker-spread,
basket-edge, interval-anchor, close-edge, book-skew, and crypto spot thresholds. Each candidate is
still an independently named strategy in SQLite, so `verify-online-goal` can
require that at least two of them pass the final ROI and flat-position gate.
The final wrapper passes `--min-passing-strategies 2`, so `target-run-until`
uses the same two-strategy success gate as the post-run verifier instead of
stopping after the first passing agent.

After the run, independently verify the final online goal evidence from SQLite:

```bash
scripts/verify_online_goal.sh
```

Without explicit `DB_PATH` and `RUN_ID`, the verifier reads
`reports/polymarket_online_6h_last.env`, so repeated online runs do not mix
evidence under the same SQLite run id.

If a long run is interrupted, resume the most recent run id and SQLite DB:

```bash
scripts/resume_online_goal_6h.sh
```

Resume mode restores open paper positions and counts already-recorded
cycles/runtime toward the same 6-hour gates.

During a long online run, print a monitor-friendly status snapshot:

```bash
scripts/online_goal_status.sh
```

The status command reads the same `reports/polymarket_online_6h_last.env` file
by default and reports runtime, cycles, passed strategy count, top strategy
ROIs, fill counts, and the most common diagnostics.

Maker-entry experiments can make the paper fill model more conservative than
the legacy optimistic proxy:

```bash
python3 -m polypaper.cli target-run-until \
  --db data/polypaper.sqlite \
  --max-cycles 120 \
  --interval-seconds 5 \
  --market-limit 20 \
  --max-assets 40 \
  --target-variants rolling_momentum_maker_goal,maker_convex_basket_goal \
  --maker-fill-mode queue_proxy \
  --maker-queue-ahead-fraction 1.0 \
  --maker-queue-decay 0.25 \
  --maker-max-order-age-attempts 24 \
  --maker-cancel-on-price-move \
  --maker-adverse-fill-on-price-move \
  --maker-adverse-fill-fraction 0.50 \
  --require-flat
```

`--maker-fill-mode optimistic` preserves the old behavior: a passive bid or ask
can fill on a later matching book without queue friction. `queue_proxy` assumes
some visible queue is ahead of the paper order and only releases fillable size
after repeated book observations. `probabilistic_queue` adds a deterministic
seeded fill-probability multiplier, useful when comparing many agents under the
same randomization. The price-move flags model cancellation and adverse
selection: a moved touch can either miss the resting order or fill it at the
limit before the book moves through that price. Maker partial fills remain
pending as residual limit orders when the remaining notional is above the
minimum, so later books can complete the same paper order instead of treating
the partial as terminal.

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
  polls /markets and batched /books or consumes a read-only market WebSocket

many agents:
  receive the same in-memory MarketSnapshot objects
  produce signals locally

one simulator:
  applies common fee, latency, tick-size, min-size, and depth-fill rules
```

This keeps API usage proportional to watched markets, not agent count. For
example, 500 agents watching the same 50 tokens should still require one batch
book request per polling cycle, not 25,000 per-agent requests.

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
