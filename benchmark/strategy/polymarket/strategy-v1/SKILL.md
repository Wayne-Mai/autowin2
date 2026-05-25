---
name: polymarket-crypto-interval-paper-strategy
description: Implement, review, tune, or explain the paper-only Polymarket crypto interval trading strategy based on interval anchor direction and orderbook skew. Use when Codex needs to create strategy code, strategy docs, parameter grids, ablation variants, or verification notes for online virtual-paper agents that trade Polymarket crypto up/down interval markets. Do not use for real-money trading, wallet-connected automation, or live order placement.
---

# Polymarket Crypto Interval Paper Strategy

## Non-Negotiables

Use this strategy only for academic paper trading. Never connect a wallet, never place real Polymarket orders, and never optimize around live execution claims that the virtual fill model cannot simulate.

When implementing in `/Users/gaga/harness-benchmark`, keep strategies under:

```text
polypaper/strategies/paper/target/
```

Register grid variants in:

```text
polypaper/strategies/paper/target/variants.py
```

## Strategy Objective

Trade short-duration Polymarket crypto up/down interval markets using live public data, while all orders/fills/PnL remain local simulation. Prefer repeatable, verifier-friendly agents that can:

- identify directional edge near settlement,
- enter only when price and book quality pass filters,
- exit quickly after target or invalidation,
- finish flat for verifier acceptance.

## Two Core Families

### Anchor Direction

Use the market interval anchor/open reference as the baseline. Buy the side that matches current crypto movement when the market price is still cheap enough.

Decision rule:

```text
spot_delta = current_spot / anchor_spot - 1
if spot_delta >= min_spot_move:
    candidate_side = UP/YES
elif spot_delta <= -min_spot_move:
    candidate_side = DOWN/NO
else:
    skip
```

Enter only if `candidate_side` token has acceptable ask/bid, enough depth, enough settlement edge, and the interval is close enough to resolution.

### Book Skew

Use orderbook pressure as confirmation. Prefer markets where one side's bid/depth is strong relative to the other side, while entry price still leaves target room.

Decision rule:

```text
bid_skew = candidate_bid_depth / max(opposite_bid_depth, epsilon)
touch_ok = candidate_bid_depth >= min_touch_depth
price_ok = min_bid_price <= candidate_bid <= max_bid_price
edge_ok = estimated_settlement_value - entry_cost >= min_net_settlement_roi
```

Enter only if skew, depth, price, and settlement-edge filters all pass.

## Entry Filters

Require all relevant filters before entering:

- market is a crypto interval up/down market,
- market has started and is not stale,
- enough spot observations exist,
- time to close is within configured bounds,
- selected side matches observed direction or book skew,
- best ask does not exceed `max_entry_price`,
- best bid is above `min_bid_price`,
- spread is neither too tight for edge nor too wide for execution quality,
- top-of-book depth passes `min_touch_depth`,
- expected impact is below `max_entry_impact`,
- position, condition, and portfolio budgets are not full.

Skip and record diagnostics rather than forcing a trade.

## Exit Rules

Exit in this order:

1. Portfolio target reached.
2. Take-profit price reached.
3. Stop-loss or direction invalidation.
4. Stale position or max-hold timeout.
5. Market too close to settlement for safe virtual execution.

After portfolio target is reached, prioritize becoming flat over earning more. Use taker-style exits in the paper model if a pending maker exit could leave the agent stuck.

## Risk Controls

Use explicit controls:

- `capital_fraction` per strategy variant,
- max concurrent positions per strategy,
- per-condition budget,
- cooldown after stale/stop exits,
- max hold cycles,
- minimum depth and maximum impact,
- no new entries once portfolio target is reached,
- require final flat state for benchmark acceptance.

Do not average down blindly. Do not increase risk to rescue a losing virtual position.

## Parameter Grid Guidance

Build variants across:

- `min_spot_move`
- `max_seconds_to_close`
- `min_bid_price`
- `max_entry_price`
- `min_net_settlement_roi`
- `capital_fraction`
- `take_profit_pct`
- `stop_loss_pct`
- depth/skew thresholds

Keep at least two distinct families in final grids: anchor direction and book skew. Spread-capture maker variants are useful baselines, but do not let them be the only source of passing strategies.

## Verification

For final online paper acceptance, require:

```text
runtime >= 21600s
target_roi >= 10%
flat_required=True
passed_strategies >= 2
passed_families >= 2
mode=online_target
```

Use the harness verifier, not visual inspection, as the source of truth:

```bash
cd /Users/gaga/harness-benchmark
scripts/verify_online_goal.sh | sed -n '1p'
```

Read [references/strategy-spec.md](references/strategy-spec.md) for implementation-level pseudocode, default parameters, diagnostics, and common failure modes.
