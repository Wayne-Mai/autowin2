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
- `consensus_mirror`
- `specialist_mirror`

Evidence:

```bash
python3 -m unittest tests.test_baselines
```

## 6. Online Paper Runner Smoke

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

## 7. Dashboard

- The dashboard reads the local SQLite database only.
- It exposes JSON endpoints for runs, summary metrics, actions, and equity
  curves.
- It renders agent PnL, fills, fees, and action stream in a browser.

Evidence:

```bash
python3 -m polypaper.cli dashboard --db data/polypaper.sqlite
```

## 8. 10% Profit Target Agent

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
  `verify-target` passes or a maximum cycle count is reached, returning a
  success exit code only for verified target achievement.
- `target-run-until` must support multiple target variants sharing the same
  market-data collection, and report the verified winning strategy when one
  reaches the target.
- A synthetic favorable path must verify that the agent can reach at least 10%
  ROI under the simulator rules.
- Live paper-run output must not be interpreted as guaranteed real-market
  profitability.

Evidence:

```bash
make target-profit-test
python3 -m polypaper.cli scan-target-opportunities --market-limit 20 --max-assets 40 --top 10
python3 -m polypaper.cli target-run-until --max-cycles 120 --interval-seconds 5 --market-limit 20 --max-assets 40 --target-variants balanced,compound,near_target,aggressive,conservative --require-flat
python3 -m polypaper.cli verify-target --db data/polypaper.sqlite --run-id <paper_run_id> --strategy paper_target_profit_10pct --target-roi 0.10 --require-flat
```
