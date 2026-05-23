# Polymarket Paper Replay Report

| Strategy | PnL | ROI | Orders | Filled | Partial | Missed | Turnover | Fees | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| paper_no_trade | 0.0000 | 0.0000% | 0 | 0 | 0 | 0 | 0.0000 | 0.0000 | 0.0000% |
| paper_target_profit_10pct | -307.8892 | -3.0789% | 1 | 1 | 0 | 0 | 9500.0000 | 240.0983 | -3.0789% |

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
    "strategy": "paper_no_trade"
  },
  {
    "fills": [
      {
        "asset": "105267568073659068217311993901927962476298440625043565106676088842803600775810",
        "average_price": 0.4945289049978614,
        "fee": 240.09826999999999,
        "filled_notional": 9500.0,
        "liquidity_source": "paper_run",
        "notional": 9500.0,
        "order_id": "paper-1779541999-22bfbfc9-paper_target_profit_10pct-1",
        "price": 0.4945289049978614,
        "quote_timestamp": 1779541999,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 9500.0,
        "shares": 19210.201676767676,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_target_profit_10pct",
        "taker": true,
        "timestamp": 1779541999
      }
    ],
    "metrics": {
      "cash": 259.9017299999996,
      "ending_equity": 9692.110753292929,
      "fees": 240.09826999999999,
      "filled_orders": 1.0,
      "initial_cash": 10000.0,
      "max_drawdown": -0.030788924670707093,
      "missed_orders": 0.0,
      "orders": 1.0,
      "partial_orders": 0.0,
      "pending_orders": 0.0,
      "pnl": -307.8892467070709,
      "roi": -0.030788924670707093,
      "turnover": 9500.0
    },
    "orders": [
      {
        "created_at": 1779541999,
        "eligible_at": 1779541999,
        "order_id": "paper-1779541999-22bfbfc9-paper_target_profit_10pct-1",
        "signal": {
          "asset": "105267568073659068217311993901927962476298440625043565106676088842803600775810",
          "condition_id": "0xbb57ccf5853a85487bc3d83d04d669310d28c6c810758953b9d9b91d1aee89d2",
          "reason": "target_opportunity score=0.4095 exit_bid=0.5713",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_profit_10pct",
          "target_notional": 9500.0,
          "timestamp": 1779541999
        }
      }
    ],
    "strategy": "paper_target_profit_10pct"
  }
]
```
