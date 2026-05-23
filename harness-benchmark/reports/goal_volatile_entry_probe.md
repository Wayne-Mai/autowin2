# Polymarket Paper Replay Report

| Strategy | PnL | ROI | Orders | Filled | Partial | Missed | Turnover | Fees | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| paper_target_volatile_compound | -46.9205 | -0.4692% | 1 | 1 | 0 | 0 | 500.0000 | 16.3305 | -0.4692% |

## Raw Metrics

```json
[
  {
    "fills": [
      {
        "asset": "112825064232503621364261629075963117883995323115924183833913665403613322420644",
        "average_price": 0.5325834558275283,
        "fee": 16.3305,
        "filled_notional": 500.0,
        "liquidity_source": "paper_run",
        "notional": 500.0,
        "order_id": "goal-volatile-entry-probe-paper_target_volatile_compound-1",
        "price": 0.5325834558275283,
        "quote_timestamp": 1779546224,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 500.0,
        "shares": 938.8199999999998,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_target_volatile_compound",
        "taker": true,
        "timestamp": 1779546224
      }
    ],
    "metrics": {
      "cash": 9483.6695,
      "ending_equity": 9953.0795,
      "fees": 16.3305,
      "filled_orders": 1.0,
      "initial_cash": 10000.0,
      "max_drawdown": -0.004692050000000017,
      "missed_orders": 0.0,
      "orders": 1.0,
      "partial_orders": 0.0,
      "pending_orders": 0.0,
      "pnl": -46.920500000000175,
      "roi": -0.004692050000000017,
      "turnover": 500.0
    },
    "orders": [
      {
        "created_at": 1779546224,
        "eligible_at": 1779546224,
        "order_id": "goal-volatile-entry-probe-paper_target_volatile_compound-1",
        "signal": {
          "asset": "112825064232503621364261629075963117883995323115924183833913665403613322420644",
          "condition_id": "0x8a5a1abcd287065d83b0f1e09b885112e600574fa05c780d82e4b8d20f147370",
          "reason": "target_opportunity_momentum score=0.0346 exit_bid=0.6215 exit_distance=24.30% imbalance=-0.10 mark_loss=9.09%",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_volatile_compound",
          "target_notional": 500.0,
          "timestamp": 1779546224
        }
      }
    ],
    "strategy": "paper_target_volatile_compound"
  }
]
```
