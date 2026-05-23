# Polymarket Paper Replay Report

| Strategy | PnL | ROI | Orders | Filled | Partial | Missed | Turnover | Fees | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| paper_target_balanced | 0.0000 | 0.0000% | 0 | 0 | 0 | 0 | 0.0000 | 0.0000 | 0.0000% |
| paper_target_aggressive | -296.7878 | -2.9679% | 1 | 1 | 0 | 0 | 9500.0000 | 232.0313 | -2.9679% |
| paper_target_conservative | 0.0000 | 0.0000% | 0 | 0 | 0 | 0 | 0.0000 | 0.0000 | 0.0000% |

## Raw Metrics

```json
[
  {
    "fills": [],
    "metrics": {
      "cash": 10000.0,
      "ending_equity": 10000.0,
      "fees": 0,
      "filled_orders": 0.0,
      "initial_cash": 10000.0,
      "max_drawdown": 0.0,
      "missed_orders": 0.0,
      "orders": 0.0,
      "partial_orders": 0.0,
      "pending_orders": 0.0,
      "pnl": 0.0,
      "roi": 0.0,
      "turnover": 0
    },
    "orders": [],
    "strategy": "paper_target_balanced"
  },
  {
    "fills": [
      {
        "asset": "91863162118308663069733924043159186005106558783397508844234610341221325526200",
        "average_price": 0.5114865327925561,
        "fee": 232.03133,
        "filled_notional": 9500.0,
        "liquidity_source": "paper_run",
        "notional": 9500.0,
        "order_id": "target-1779542617-f4af27e3-paper_target_aggressive-1",
        "price": 0.5114865327925561,
        "quote_timestamp": 1779542617,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 9500.0,
        "shares": 18573.31403846154,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_target_aggressive",
        "taker": true,
        "timestamp": 1779542617
      }
    ],
    "metrics": {
      "cash": 267.9686700000002,
      "ending_equity": 9703.212201538463,
      "fees": 232.03133,
      "filled_orders": 1.0,
      "initial_cash": 10000.0,
      "max_drawdown": -0.0296787798461537,
      "missed_orders": 0.0,
      "orders": 1.0,
      "partial_orders": 0.0,
      "pending_orders": 0.0,
      "pnl": -296.787798461537,
      "roi": -0.0296787798461537,
      "turnover": 9500.0
    },
    "orders": [
      {
        "created_at": 1779542617,
        "eligible_at": 1779542617,
        "order_id": "target-1779542617-f4af27e3-paper_target_aggressive-1",
        "signal": {
          "asset": "91863162118308663069733924043159186005106558783397508844234610341221325526200",
          "condition_id": "0xbb57ccf5853a85487bc3d83d04d669310d28c6c810758953b9d9b91d1aee89d2",
          "reason": "target_opportunity_momentum score=0.4658 exit_bid=0.5899 imbalance=0.74",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_aggressive",
          "target_notional": 9500.0,
          "timestamp": 1779542617
        }
      }
    ],
    "strategy": "paper_target_aggressive"
  },
  {
    "fills": [],
    "metrics": {
      "cash": 10000.0,
      "ending_equity": 10000.0,
      "fees": 0,
      "filled_orders": 0.0,
      "initial_cash": 10000.0,
      "max_drawdown": 0.0,
      "missed_orders": 0.0,
      "orders": 0.0,
      "partial_orders": 0.0,
      "pending_orders": 0.0,
      "pnl": 0.0,
      "roi": 0.0,
      "turnover": 0
    },
    "orders": [],
    "strategy": "paper_target_conservative"
  }
]
```
