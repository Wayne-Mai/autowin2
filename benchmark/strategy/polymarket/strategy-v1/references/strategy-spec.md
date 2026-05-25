# Strategy Spec: Polymarket Crypto Interval Paper Strategy

## Purpose

This spec describes the paper-only strategy families that produced the useful online result in the harness benchmark: `crypto_interval_anchor` and `crypto_interval_book_skew`. It is written so another agent can implement, review, or tune the strategy without relying on prior chat context.

## Data Inputs

Required live public inputs:

- Polymarket market metadata: condition, outcomes, token IDs, start/end timestamps, active/closed flags.
- CLOB/orderbook snapshots: best bid, best ask, touch depth, deeper book depth when available.
- Crypto spot stream or sampled price: current spot and interval anchor/open reference.
- Local portfolio state: cash, positions, average cost, pending simulated orders, previous diagnostics.

All execution is simulated locally.

## Family 1: Crypto Interval Anchor

### Intuition

In a short crypto interval market, the market resolves based on whether the asset is above or below its interval anchor. If current spot has moved enough from the anchor, but the corresponding outcome token remains underpriced, enter the aligned side and exit when the edge is realized or the portfolio target is reached.

### Pseudocode

```python
def anchor_signal(snapshot, portfolio, config):
    if not is_crypto_interval(snapshot.market):
        return skip("not_crypto_interval")
    if not interval_started(snapshot):
        return skip("market_not_started")
    if too_close_or_too_far_from_close(snapshot, config):
        return skip("not_close_enough_to_settlement")
    if portfolio.target_reached:
        return exit_to_flat_if_needed()

    anchor = snapshot.interval.anchor_spot
    spot = snapshot.current_spot
    if anchor <= 0 or spot <= 0:
        return skip("spot_unavailable")

    move = spot / anchor - 1.0
    if abs(move) < config.min_spot_move:
        return skip("spot_move_too_small")

    side = "UP" if move > 0 else "DOWN"
    token = token_for_side(snapshot.market, side)
    book = snapshot.book_for(token)

    if book.ask > config.max_entry_price:
        return skip("ask_above_max_price")
    if book.bid < config.min_bid_price:
        return skip("bid_below_min_price")
    if spread(book) > config.max_spread:
        return skip("spread_too_wide")
    if touch_depth(book) < config.min_touch_depth:
        return skip("bid_touch_depth_too_thin")
    if expected_impact(book, config.order_size) > config.max_entry_impact:
        return skip("entry_impact_too_high")

    edge = estimated_settlement_value(side, move) - book.ask
    if edge < config.min_net_settlement_roi:
        return skip("settlement_edge_too_small")

    size = budgeted_size(portfolio, config.capital_fraction, book.ask)
    if size <= 0:
        return skip("position_budget_full")

    return buy(token, size=size, limit_price=book.ask, style=config.entry_style)
```

### Exit

```python
def anchor_exit(position, snapshot, portfolio, config):
    if position.size <= 0:
        return None

    if portfolio.equity >= portfolio.initial_equity * (1 + config.target_roi):
        return sell_all(position, style="taker", reason="portfolio_target_reached")

    if snapshot.book.bid >= position.avg_cost * (1 + config.take_profit_pct):
        return sell_all(position, style="taker", reason="take_profit")

    if snapshot.book.bid <= position.avg_cost * (1 - config.stop_loss_pct):
        return sell_all(position, style="taker", reason="stop_loss")

    if position.age_cycles >= config.max_hold_cycles:
        return sell_all(position, style="taker", reason="stale_position_exit")
```

## Family 2: Crypto Interval Book Skew

### Intuition

The orderbook sometimes reveals pressure before the price fully reflects it. If one side has materially stronger bid/depth support and still offers enough settlement edge, enter the supported side.

### Pseudocode

```python
def book_skew_signal(snapshot, portfolio, config):
    if not is_crypto_interval(snapshot.market):
        return skip("not_crypto_interval")
    if portfolio.target_reached:
        return exit_to_flat_if_needed()

    up = book_for_side(snapshot, "UP")
    down = book_for_side(snapshot, "DOWN")

    up_score = score_book(up, down, config)
    down_score = score_book(down, up, config)
    if max(up_score, down_score) < config.min_skew_score:
        return skip("book_skew_too_small")

    side = "UP" if up_score > down_score else "DOWN"
    book = up if side == "UP" else down

    if book.bid < config.min_bid_price:
        return skip("bid_below_min_price")
    if book.ask > config.max_entry_price:
        return skip("ask_above_max_price")
    if touch_depth(book) < config.min_touch_depth:
        return skip("bid_touch_depth_too_thin")
    if spread(book) > config.max_spread:
        return skip("spread_too_wide")

    edge = estimated_settlement_edge(snapshot, side, book.ask)
    if edge < config.min_net_settlement_roi:
        return skip("settlement_edge_too_small")

    size = budgeted_size(portfolio, config.capital_fraction, book.ask)
    if size <= 0:
        return skip("position_budget_full")

    return buy(token_for_side(snapshot.market, side), size=size, limit_price=book.ask)
```

Book score:

```python
def score_book(candidate, opposite, config):
    bid_strength = candidate.bid_depth / max(opposite.bid_depth, 1e-9)
    touch_strength = candidate.touch_depth / max(opposite.touch_depth, 1e-9)
    price_quality = clamp((candidate.bid - config.min_bid_price) / config.price_band, 0, 1)
    return (
        config.bid_depth_weight * bid_strength
        + config.touch_depth_weight * touch_strength
        + config.price_weight * price_quality
    )
```

## Suggested Parameter Ranges

Use a grid rather than one hand-picked config:

```text
target_roi: 0.10
capital_fraction: 0.20, 0.35, 0.55, 0.65, 0.70
min_spot_move: 0.0002, 0.0004, 0.0008
max_seconds_to_close: 180, 240, 300
min_bid_price: 0.50, 0.58, 0.65, 0.72
max_entry_price: 0.90, 0.95
min_net_settlement_roi: 0.02, 0.06, 0.12
take_profit_pct: 0.015, 0.02, 0.03
stop_loss_pct: 0.02, 0.04, 0.06
max_hold_cycles: 4, 8, 12
min_touch_depth: tune to observed CLOB scale
max_entry_impact: conservative; reject thin books
```

For final online tests, require at least one anchor grid and one book-skew grid.

## Diagnostics to Emit

Emit diagnostics instead of silently skipping:

```text
market_not_started
market_too_young
market_too_close_to_end
not_close_enough_to_settlement
spot_insufficient_observations
spot_move_too_small
wrong_outcome_for_spot_direction
bid_below_min_price
ask_above_max_price
spread_too_wide
spread_too_tight
bid_touch_depth_too_thin
entry_impact_too_high
settlement_edge_too_small
position_budget_full
condition_budget_full
cooldown_active
target_reached_waiting_flat
```

These diagnostics make ablations and failure analysis possible.

## Execution Model Requirements

Final paper acceptance should use realistic virtual execution:

- decision and execution latency,
- queue proxy maker fills,
- partial fills,
- queue-ahead fraction and queue decay,
- cancel-on-price-move,
- adverse fill on price move,
- fees/slippage as configured by the harness.

Do not evaluate final strategy quality using optimistic instant fills.

## Implementation Notes for `/Users/gaga/harness-benchmark`

Relevant modules:

```text
polypaper/strategies/paper/target/crypto.py
polypaper/strategies/paper/target/scalpers.py
polypaper/strategies/paper/target/variants.py
polypaper/target_runner.py
polypaper/verification.py
```

Keep strategy changes narrowly scoped. Update tests when changing:

- target-hit flattening,
- variant counts,
- family parsing,
- verifier pass criteria,
- no-live-trading guarantees.

Run:

```bash
python3 -m unittest discover -s tests
```

## Common Pitfalls

### Mistaking max ROI for final ROI

The verifier uses final ROI. A strategy that touched 10% but ended below 10% does not pass.

### Failing flat requirement

The strategy must have no final position. After target is reached, no new entries should be created and exits should prioritize flattening.

### One-family overfitting

Passing variants from one family are not enough for the benchmark. Keep anchor and book-skew families distinct.

### Hidden optimistic fills

Do not remove queue, partial-fill, latency, or adverse-fill realism to make the strategy look better. Use optimistic fills only for explicit ablations.

### Real trading leakage

Any wallet, private key, private API credential, or live order placement violates this strategy's intended use.
