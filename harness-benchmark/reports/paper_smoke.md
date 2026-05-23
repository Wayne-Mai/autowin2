# Polymarket Paper Replay Report

| Strategy | PnL | ROI | Orders | Filled | Partial | Missed | Turnover | Fees | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| paper_no_trade | 0.0000 | 0.0000% | 0 | 0 | 0 | 0 | 0.0000 | 0.0000 | 0.0000% |
| paper_random_market_taker | -1.8088 | -0.0181% | 1 | 1 | 0 | 0 | 25.0000 | 0.5795 | -0.0181% |

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
        "asset": "98022490269692409998126496127597032490334070080325855126491859374983463996227",
        "average_price": 0.5363762421083162,
        "fee": 0.5794699999999999,
        "filled_notional": 25.0,
        "liquidity_source": "paper_run",
        "notional": 25.0,
        "order_id": "paper-1779537950-dc4923d1-paper_random_market_taker-1",
        "price": 0.5363762421083162,
        "quote_timestamp": 1779537950,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 25.0,
        "shares": 46.60907407407407,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_random_market_taker",
        "taker": true,
        "timestamp": 1779537950
      }
    ],
    "metrics": {
      "cash": 9974.42053,
      "ending_equity": 9998.191157777777,
      "fees": 0.5794699999999999,
      "filled_orders": 1.0,
      "initial_cash": 10000.0,
      "max_drawdown": -0.00018088422222226655,
      "missed_orders": 0.0,
      "orders": 1.0,
      "partial_orders": 0.0,
      "pending_orders": 0.0,
      "pnl": -1.8088422222226654,
      "roi": -0.00018088422222226655,
      "turnover": 25.0
    },
    "orders": [
      {
        "created_at": 1779537950,
        "eligible_at": 1779537950,
        "order_id": "paper-1779537950-dc4923d1-paper_random_market_taker-1",
        "signal": {
          "asset": "98022490269692409998126496127597032490334070080325855126491859374983463996227",
          "condition_id": "0x1fad72fae204143ff1c3035e99e7c0f65ea8d5cd9bd1070987bd1a3316f772be",
          "reason": "deterministic random market taker baseline",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_random_market_taker",
          "target_notional": 25.0,
          "timestamp": 1779537950
        }
      }
    ],
    "strategy": "paper_random_market_taker"
  }
]
```
