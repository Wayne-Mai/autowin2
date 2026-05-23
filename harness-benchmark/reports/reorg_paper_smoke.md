# Polymarket Paper Replay Report

| Strategy | PnL | ROI | Orders | Filled | Partial | Missed | Turnover | Fees | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| paper_no_trade | 0.0000 | 0.0000% | 0 | 0 | 0 | 0 | 0.0000 | 0.0000 | 0.0000% |
| paper_target_profit_10pct | -6.9393 | -0.0694% | 1 | 1 | 0 | 0 | 100.0000 | 2.0006 | -0.0694% |
| paper_random_market_taker | -1.0132 | -0.0101% | 1 | 1 | 0 | 0 | 25.0000 | 0.5232 | -0.0101% |

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
        "average_price": 0.5996134950389356,
        "fee": 2.0005699999999997,
        "filled_notional": 100.0,
        "liquidity_source": "paper_run",
        "notional": 100.0,
        "order_id": "paper-1779541306-7df35a28-paper_target_profit_10pct-1",
        "price": 0.5996134950389356,
        "quote_timestamp": 1779541307,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 100.0,
        "shares": 166.77409836065573,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_target_profit_10pct",
        "taker": true,
        "timestamp": 1779541307
      }
    ],
    "metrics": {
      "cash": 9897.99943,
      "ending_equity": 9993.060666065574,
      "fees": 2.0005699999999997,
      "filled_orders": 1.0,
      "initial_cash": 10000.0,
      "max_drawdown": -0.0006939333934426031,
      "missed_orders": 0.0,
      "orders": 1.0,
      "partial_orders": 0.0,
      "pending_orders": 0.0,
      "pnl": -6.939333934426031,
      "roi": -0.0006939333934426031,
      "turnover": 100.0
    },
    "orders": [
      {
        "created_at": 1779541307,
        "eligible_at": 1779541307,
        "order_id": "paper-1779541306-7df35a28-paper_target_profit_10pct-1",
        "signal": {
          "asset": "98022490269692409998126496127597032490334070080325855126491859374983463996227",
          "condition_id": "0x1fad72fae204143ff1c3035e99e7c0f65ea8d5cd9bd1070987bd1a3316f772be",
          "reason": "enter_until_10.00%_portfolio_target",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_profit_10pct",
          "target_notional": 100.0,
          "timestamp": 1779541307
        }
      }
    ],
    "strategy": "paper_target_profit_10pct"
  },
  {
    "fills": [
      {
        "asset": "98022490269692409998126496127597032490334070080325855126491859374983463996227",
        "average_price": 0.5813953488372092,
        "fee": 0.52323,
        "filled_notional": 25.0,
        "liquidity_source": "paper_run",
        "notional": 25.0,
        "order_id": "paper-1779541306-7df35a28-paper_random_market_taker-2",
        "price": 0.5813953488372092,
        "quote_timestamp": 1779541307,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 25.0,
        "shares": 43.00000000000001,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_random_market_taker",
        "taker": true,
        "timestamp": 1779541307
      }
    ],
    "metrics": {
      "cash": 9974.47677,
      "ending_equity": 9998.98677,
      "fees": 0.52323,
      "filled_orders": 1.0,
      "initial_cash": 10000.0,
      "max_drawdown": -0.00010132300000004762,
      "missed_orders": 0.0,
      "orders": 1.0,
      "partial_orders": 0.0,
      "pending_orders": 0.0,
      "pnl": -1.0132300000004761,
      "roi": -0.00010132300000004762,
      "turnover": 25.0
    },
    "orders": [
      {
        "created_at": 1779541307,
        "eligible_at": 1779541307,
        "order_id": "paper-1779541306-7df35a28-paper_random_market_taker-2",
        "signal": {
          "asset": "98022490269692409998126496127597032490334070080325855126491859374983463996227",
          "condition_id": "0x1fad72fae204143ff1c3035e99e7c0f65ea8d5cd9bd1070987bd1a3316f772be",
          "reason": "deterministic random market taker baseline",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_random_market_taker",
          "target_notional": 25.0,
          "timestamp": 1779541307
        }
      }
    ],
    "strategy": "paper_random_market_taker"
  }
]
```
