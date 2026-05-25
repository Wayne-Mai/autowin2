# Engine Architecture

Backtest, paper trading, and live trading are separate engines with the same
small interface:

```python
engine.run_once()
engine.results()
engine.metadata
```

`engine.metadata` declares the engine kind, whether it reads live market data,
whether it can place real orders, and whether it persists results.

## Backtest Engine

`ReplayBacktestEngine` is offline and deterministic. It wraps
`ReplaySimulator.run(...)` with fixed public trades and quote/order-book
snapshots. It does not poll Polymarket, persist state, or place orders.

Use it for fixture replay, fill-model ablation, and strategy regression tests.

## Paper Engine

`PaperTradingEngine` wraps `PaperRunner`. It can read live public data or a
recorded market stream, but execution remains local and simulated:

- no private keys
- no signed orders
- no order placement endpoints
- fills produced by the configured conservative fill model
- optional persistence to the local SQLite benchmark database

Use it for online virtual-paper benchmark runs.

## Live Engine

`DisabledLiveTradingEngine` is a safety placeholder. It has the same interface,
but `run_once()` raises `LiveTradingDisabledError`.

This benchmark currently has no real-money execution path. A future live engine
would need separate credentials, order-routing code, risk controls, and tests,
and should not share the paper engine's simulated-fill implementation.
