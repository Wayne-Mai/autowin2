# Polymarket Paper Replay Report

| Strategy | PnL | ROI | Orders | Filled | Partial | Missed | Turnover | Fees | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| paper_no_trade | 0.0000 | 0.0000% | 0 | 0 | 0 | 0 | 0.0000 | 0.0000 | 0.0000% |
| paper_target_profit_10pct | 0.0000 | 0.0000% | 1 | 0 | 0 | 1 | 0.0000 | 0.0000 | 0.0000% |

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
        "average_price": 0.0,
        "fee": 0.0,
        "filled_notional": 0.0,
        "liquidity_source": "paper_run",
        "notional": 0.0,
        "order_id": "paper-1779541837-669c97d4-paper_target_profit_10pct-1",
        "price": 0.0,
        "quote_timestamp": 1779541839,
        "reason": "insufficient_cash_after_fee",
        "requested_notional": 10000.0,
        "shares": 0.0,
        "side": "BUY",
        "status": "MISSED",
        "strategy": "paper_target_profit_10pct",
        "taker": true,
        "timestamp": 1779541839
      }
    ],
    "metrics": {
      "cash": 10000.0,
      "ending_equity": 10000.0,
      "fees": 0,
      "filled_orders": 0.0,
      "initial_cash": 10000.0,
      "max_drawdown": 0.0,
      "missed_orders": 1.0,
      "orders": 1.0,
      "partial_orders": 0.0,
      "pending_orders": 0.0,
      "pnl": 0.0,
      "roi": 0.0,
      "turnover": 0
    },
    "orders": [
      {
        "created_at": 1779541839,
        "eligible_at": 1779541839,
        "order_id": "paper-1779541837-669c97d4-paper_target_profit_10pct-1",
        "signal": {
          "asset": "105267568073659068217311993901927962476298440625043565106676088842803600775810",
          "condition_id": "0xbb57ccf5853a85487bc3d83d04d669310d28c6c810758953b9d9b91d1aee89d2",
          "reason": "target_opportunity score=0.4368 exit_bid=0.5440",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_profit_10pct",
          "target_notional": 10000.0,
          "timestamp": 1779541839
        }
      }
    ],
    "strategy": "paper_target_profit_10pct"
  }
]
```
