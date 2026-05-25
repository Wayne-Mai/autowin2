# Acceptance Gates

The system is accepted only when the evidence below holds for the current
worktree.

## 1. No Real Trading Capability

- The Polymarket client exposes only public `GET` requests.
- Allowed hosts are limited to `data-api.polymarket.com`,
  `gamma-api.polymarket.com`, and `clob.polymarket.com`.
- Order-like, cancel-like, auth-like, and API-key-like paths are rejected before
  network I/O.
- There is no private-key, signature, credential, or order-submit module.

Evidence:

```bash
python3 -m unittest tests.test_no_live_trading
```

## 2. Time Causality

- A strategy receives one public trader event at the current replay timestamp.
- A virtual order is not eligible to fill until `signal_time + delay_seconds`.
- Latency can be decomposed into detection, polling, decision, and execution
  components.
- The fill model uses the first quote tick at or after the eligible execution
  time, never the trader's original execution price.
- End-of-run marking uses quotes at or before the replay end.

Evidence:

```bash
python3 -m unittest tests.test_causality
```

## 3. Reproducibility

- Fixture replay with the same strategy config and seed produces identical
  orders, fills, and metrics.
- Random baselines derive decisions from deterministic hashes, not ambient
  process state.

Evidence:

```bash
python3 -m unittest tests.test_reproducibility
```

## 4. Virtual Execution Credibility

- Buys execute against asks plus slippage, walking L2 depth when available.
- Sells execute against bids minus slippage, walking L2 depth when available.
- Partial fills are recorded when available depth cannot satisfy requested size.
- Taker fees use the Polymarket-style curve
  `shares * fee_rate * (price * (1 - price)) ** exponent`.
- Tick size and minimum order size are enforced before a fill is accepted.
- Sells cannot create short positions.
- Missing quotes or insufficient inventory are recorded as missed fills.

Evidence:

```bash
python3 -m unittest tests.test_fill_model
```

## 5. Comparable Baselines

The simulator can run these baselines through the same event clock, fill model,
portfolio rules, and metrics:

- `no_trade`
- `random_same_turnover`
- `single_trader_mirror`
- `maker_single_trader_mirror`
- `consensus_mirror`
- `specialist_mirror`

Evidence:

```bash
python3 -m unittest tests.test_baselines
```

## 6. Benchmark Suite

- Fill realism scenarios are configured outside code in
  `configs/fill_scenarios.yml`.
- `benchmark-suite` replays the same fixture across multiple scenarios while
  holding market data, strategy suite, seed, and starting cash constant.
- The summary reports ROI/rank deltas against a baseline scenario plus fill,
  partial, and miss rates.
- JSON, CSV, and Markdown outputs are generated for downstream analysis.

Evidence:

```bash
python3 -m unittest tests.test_benchmark
python3 -m polypaper.cli benchmark-suite --fixture tests/fixtures/small_replay.json --scenarios optimistic,realistic --strategy-suite default_with_maker --out-dir reports/benchmark_acceptance
```

## 7. Online Paper Runner Smoke

- `paper-run` does not depend on top traders.
- It snapshots public active markets and public CLOB order books.
- It runs `paper_no_trade` and `paper_random_market_taker`.
- It persists order books, signals, paper fills, and portfolio snapshots.
- With positive execution latency, orders remain pending until a later eligible
  snapshot.
- Hundreds of agents share one collector snapshot; API calls scale with watched
  assets, not with agent count.

Evidence:

```bash
python3 -m unittest tests.test_paper_runner
python3 -m polypaper.cli paper-run --cycles 1 --market-limit 1 --max-assets 1 --trade-probability 1 --execution-delay-seconds 0
```

## 8. Market Recording Replay

- `record-snapshots` must save public `MarketSnapshot` batches and market rules
  into a reusable JSON or JSON.GZ recording.
- `target-replay-recording` must replay target paper agents offline against the
  saved stream without making new market-data API calls.
- A synthetic recording must be able to verify a profitable target strategy
  through the same SQLite verifier used by online paper runs.
- Recordings are for internal ablation only. The final 6-hour profitability
  claim must use online virtual-paper execution against live public books.

Evidence:

```bash
python3 -m unittest tests.test_recording
python3 -m polypaper.cli record-snapshots --out data/recordings/acceptance_smoke.json.gz --cycles 1 --market-limit 1 --max-assets 1
python3 -m polypaper.cli target-replay-recording --recording data/recordings/acceptance_smoke.json.gz --db data/recording_acceptance.sqlite --run-id recording-acceptance --target-variants balanced --max-cycles 1
```

## 9. Dashboard

- The dashboard reads the local SQLite database only.
- It exposes JSON endpoints for runs, summary metrics, actions, and equity
  curves.
- It renders agent PnL, fills, fees, and action stream in a browser.

Evidence:

```bash
python3 -m polypaper.cli dashboard --db data/polypaper.sqlite
```

## 10. 10% Profit Target Agent

- The target-profit agent opens a virtual position, tracks fill-derived average
  cost, exits on configured take-profit, and stops opening new positions after
  portfolio target ROI is reached.
- When entry notional is set to `0`, the agent auto-sizes capital from
  `portfolio_target_roi / take_profit_pct`, capped by the configured capital
  fraction, so the default 10% target is internally consistent while preserving
  a cash buffer for fees.
- The agent must support adaptive entry sizing, where the configured entry
  notional is a maximum and the actual order size is reduced to the largest
  notional that passes the same L2 impact, mark-to-bid, exit-distance, price
  band, and cash constraints used by the scanner.
- The agent must reject entries whose estimated L2 average ask would create
  excessive immediate market impact versus the current bid.
- The agent must reject entries whose estimated fill cost plus fees would
  already mark below the configured stop-loss threshold at the current bid.
- The agent must expose required-exit distance, and target variants must be
  able to reject entries that need too large a bid move before the portfolio
  target can be verified.
- Target variants must be able to restrict entries to a bid-price band, so
  high-movement probes can focus on contracts with enough price elasticity for
  a 10% benchmark while conservative probes can leave the band unset.
- The agent must reject entries when near-touch L2 bid-side depth is too weak
  relative to ask-side depth.
- When multiple candidate markets are available in one collection cycle, the
  target agent must rank viable opportunities and choose the strongest one
  instead of buying the first eligible snapshot.
- The target agent must require positive short-horizon bid and mid momentum
  before opening a new position, while still allowing exits whenever the
  portfolio target is reached.
- The target agent must support stop-loss exits so long-window target runs can
  release capital after adverse moves.
- The target agent must support building multiple bounded positions when
  `max_positions` is greater than one, while still avoiding duplicate entries
  for an already held or pending asset.
- Multi-position target variants must be able to cap positions per related
  market group, so repeated event families do not consume the whole position
  budget.
- The target agent must support progress-aware max-hold exits so stagnant or
  deteriorating positions can release capital for later candidates instead of
  blocking the runner indefinitely, while positions moving toward their target
  can keep running.
- Max-hold exits must be able to cool down the stale asset so the strategy does
  not immediately rebuy the same stagnant token and churn fees.
- The target agent must support a compound mode that can realize smaller
  take-profit exits and re-enter until the final flat portfolio reaches the
  configured ROI target.
- Target runs must include a stricter compound-quality variant that rejects
  high mark-to-bid loss entries and candidates whose fee-aware take-profit exit
  is too far from the current bid.
- Target runs must include a volatile compound variant that uses a mid-price
  band, wider risk controls, and a larger realized-profit step for short-window
  high-movement markets.
- Compound take-profit exits must be fee-aware: the required exit bid must
  produce the configured net profit after estimated exit fees, not merely trade
  at a gross price above average cost.
- The target agent must enforce a cooldown after sells to avoid immediate
  churn back into the same token.
- A scan command must expose the same opportunity scoring without placing
  virtual orders.
- Online market discovery must support explicit Gamma ordering such as
  `volume_24hr` or `liquidity`, so candidate selection is reproducible and not
  dependent on the API default order.
- A `verify-target` command must evaluate final ROI from SQLite and return a
  failing exit code when the target was not reached.
- A `target-run-until` command must keep running target agents until
  enough strategies pass `verify-target` or a maximum cycle count is reached,
  returning a success exit code only for verified target achievement.
- `target-run-until` must support multiple target variants sharing the same
  market-data collection, and report the verified winning strategy when one
  reaches the target.
- Maker-order paper runs must support an optimistic legacy fill proxy and
  stricter queue-based modes that can model queue position, partial fills,
  order expiry, cancellation after price movement, and adverse-selection fills.
- Market fee rules must parse both taker fee rates and maker rebate rates from
  public market metadata, with maker rebates recorded as negative fees on
  virtual maker fills.
- Maker partial fills must leave an above-minimum residual order pending, and
  target-agent cost basis must remain valid across partial buy and sell fills.
- Final six-hour virtual-paper validation must use online `target-run-until`
  against live public books, with `--min-cycles-before-pass` and
  `--min-runtime-seconds-before-pass` preventing early success before the full
  online window has elapsed. It must require at least two passing strategies at
  the run loop, matching the final verifier. The cycle gate should be
  configurable and must not replace the wall-clock six-hour gate. Repeated
  final runs must use unique run ids, or an explicitly selected run id, so
  SQLite evidence from separate attempts is not mixed during verification.
  Resume mode must count already-recorded cycles/runtime toward the same gates.
- Online virtual-paper validation must remain read-only: public market data is
  allowed, virtual orders/fills are recorded locally, and no real order/cancel
  endpoints are exposed. All agents in a cycle must share the same market-data
  collection rather than fetching per agent. Strategies that need wall-clock
  market age must also receive one shared cycle timestamp so later agents in a
  large batch do not see an artificially older market than earlier agents.
- Online virtual-paper positions must support local settlement from public
  Gamma metadata. The runner may settle only when the market is `closed=true`
  and public `outcomePrices` are effectively binary, and the settlement fill
  must be recorded locally as virtual paper activity.
- Final online virtual-paper validation must use non-zero execution realism
  parameters unless an ablation explicitly overrides them: market-specific
  public fee metadata, configurable detection/polling/decision/execution
  latency, queue-aware maker fills, maker cancellation/adverse-selection
  behavior, and local partial fills from visible book depth.
- Online market selection must support `--market-prefer-keywords` for stable
  prioritization of target market families such as crypto up/down, and
  `--market-filter-keywords` for ablations that intentionally exclude
  non-matching markets. For timestamped 5m/15m crypto Up/Down markets, preferred
  selection should rank currently active intervals before upcoming intervals so
  online paper agents can anchor and evaluate the same live window. The online
  run may scan multiple paginated Gamma pages with `--market-pages`, but each
  cycle must still share one selected book collection across all agents.
- At least two target strategies must be available for final validation. The
  current dedicated candidates are `momentum_scalper_goal`,
  `crypto_directional_goal`, `crypto_interval_anchor_goal`,
  `crypto_interval_close_edge_goal`, `crypto_interval_book_skew_goal`,
  `spread_capture_maker_goal`, and `outcome_basket_arb_goal`. The
  `online_goal_grid` group expands those
  families into independently named candidate agents for online scaling
  experiments. Its interval-anchor grid may include late-anchor ablation
  variants, but final reporting must distinguish those from strict early-window
  interval-anchor evidence. Close-edge variants must be reported separately from
  early interval-anchor variants. Book-skew variants must be reported as
  book-implied direction strategies because they do not require a spot anchor.
- A long online run should have a read-only status command that reports current
  runtime, cycles, two-strategy pass progress, top strategy ROIs, fill counts,
  and common diagnostics from the same SQLite evidence used by the final
  verifier.
- A synthetic favorable path must verify that the agent can reach at least 10%
  ROI under the simulator rules.
- Live paper-run output must not be interpreted as guaranteed real-market
  profitability.

Evidence:

```bash
make target-profit-test
python3 -m unittest tests.test_fill_model
python3 -m unittest tests.test_goal_scalpers
python3 -m unittest tests.test_no_live_trading tests.test_paper_runner
python3 -m polypaper.cli scan-target-opportunities --market-limit 20 --max-assets 40 --top 10
python3 -m polypaper.cli target-run-until --max-cycles 120 --interval-seconds 5 --market-limit 20 --max-assets 40 --target-variants balanced,compound,near_target,aggressive,conservative --require-flat
python3 -m polypaper.cli target-run-until --max-cycles 120 --interval-seconds 5 --market-limit 20 --max-assets 40 --target-variants rolling_momentum_maker_goal,maker_convex_basket_goal --maker-fill-mode queue_proxy --maker-queue-ahead-fraction 1 --maker-queue-decay 0.25 --maker-max-order-age-attempts 24 --maker-cancel-on-price-move --maker-adverse-fill-on-price-move --maker-adverse-fill-fraction 0.5 --require-flat
scripts/online_goal_6h.sh
scripts/launch_online_goal_6h.sh
scripts/stop_online_goal_6h.sh
scripts/online_goal_status.sh
scripts/verify_online_goal.sh
python3 -m polypaper.cli verify-target --db data/polypaper.sqlite --run-id <paper_run_id> --strategy paper_target_profit_10pct --target-roi 0.10 --require-flat
```
