# Polymarket Paper Replay Report

| Strategy | PnL | ROI | Orders | Filled | Partial | Missed | Turnover | Fees | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| paper_target_balanced | 0.0000 | 0.0000% | 0 | 0 | 0 | 0 | 0.0000 | 0.0000 | 0.0000% |
| paper_target_aggressive | -85.4432 | -0.8544% | 1 | 1 | 0 | 0 | 9500.0000 | 51.3155 | -0.8544% |
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
        "asset": "87978082071653935678874296685430503892266481242311708420787197372467948088235",
        "average_price": 0.8199455642455401,
        "fee": 51.31548,
        "filled_notional": 9500.0,
        "liquidity_source": "paper_run",
        "notional": 9500.0,
        "order_id": "goal-fee-safe-longer-paper_target_aggressive-1",
        "price": 0.8199455642455401,
        "quote_timestamp": 1779543516,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 9500.0,
        "shares": 11586.134999999998,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_target_aggressive",
        "taker": true,
        "timestamp": 1779543516
      }
    ],
    "metrics": {
      "cash": 448.6845200000007,
      "ending_equity": 9914.556814999998,
      "fees": 51.31548,
      "filled_orders": 1.0,
      "initial_cash": 10000.0,
      "max_drawdown": -0.008544318500000191,
      "missed_orders": 0.0,
      "orders": 1.0,
      "partial_orders": 0.0,
      "pending_orders": 0.0,
      "pnl": -85.4431850000019,
      "roi": -0.008544318500000191,
      "turnover": 9500.0
    },
    "orders": [
      {
        "created_at": 1779543516,
        "eligible_at": 1779543516,
        "order_id": "goal-fee-safe-longer-paper_target_aggressive-1",
        "signal": {
          "asset": "87978082071653935678874296685430503892266481242311708420787197372467948088235",
          "condition_id": "0xf8f63bb47b2a7c2e0c1be3cedf4075079b11c07476d76a9469065b0c4791961a",
          "reason": "target_opportunity_momentum score=0.0854 exit_bid=0.9131 imbalance=0.13 mark_loss=0.89%",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_aggressive",
          "target_notional": 9500.0,
          "timestamp": 1779543516
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
