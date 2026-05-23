# Polymarket Paper Replay Report

| Strategy | PnL | ROI | Orders | Filled | Partial | Missed | Turnover | Fees | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| paper_no_trade | 0.0000 | 0.0000% | 0 | 0 | 0 | 0 | 0.0000 | 0.0000 | 0.0000% |
| paper_target_profit_10pct | -2964.1176 | -29.6412% | 1 | 0 | 1 | 0 | 9904.9022 | 95.0978 | -29.6412% |

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
        "average_price": 0.8024287357842812,
        "fee": 95.09779999999999,
        "filled_notional": 9904.902199999982,
        "liquidity_source": "paper_run",
        "notional": 9904.902199999982,
        "order_id": "paper-1779541554-54683256-paper_target_profit_10pct-1",
        "price": 0.8024287357842812,
        "quote_timestamp": 1779541554,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 10000.0,
        "shares": 12343.65340907076,
        "side": "BUY",
        "status": "PARTIAL",
        "strategy": "paper_target_profit_10pct",
        "taker": true,
        "timestamp": 1779541554
      }
    ],
    "metrics": {
      "cash": 1.8189894035458565e-11,
      "ending_equity": 7035.882443170351,
      "fees": 95.09779999999999,
      "filled_orders": 0.0,
      "initial_cash": 10000.0,
      "max_drawdown": -0.29641175568296496,
      "missed_orders": 0.0,
      "orders": 1.0,
      "partial_orders": 1.0,
      "pending_orders": 0.0,
      "pnl": -2964.1175568296494,
      "roi": -0.29641175568296496,
      "turnover": 9904.902199999982
    },
    "orders": [
      {
        "created_at": 1779541554,
        "eligible_at": 1779541554,
        "order_id": "paper-1779541554-54683256-paper_target_profit_10pct-1",
        "signal": {
          "asset": "98022490269692409998126496127597032490334070080325855126491859374983463996227",
          "condition_id": "0x1fad72fae204143ff1c3035e99e7c0f65ea8d5cd9bd1070987bd1a3316f772be",
          "reason": "enter_until_10.00%_portfolio_target",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_profit_10pct",
          "target_notional": 10000.0,
          "timestamp": 1779541554
        }
      }
    ],
    "strategy": "paper_target_profit_10pct"
  }
]
```
