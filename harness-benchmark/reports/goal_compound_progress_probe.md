# Polymarket Paper Replay Report

| Strategy | PnL | ROI | Orders | Filled | Partial | Missed | Turnover | Fees | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| paper_target_compound | -74.3544 | -0.7435% | 1 | 1 | 0 | 0 | 9500.0000 | 51.3029 | -0.7435% |

## Raw Metrics

```json
[
  {
    "fills": [
      {
        "asset": "87978082071653935678874296685430503892266481242311708420787197372467948088235",
        "average_price": 0.8199896784878153,
        "fee": 51.30294,
        "filled_notional": 9500.0,
        "liquidity_source": "paper_run",
        "notional": 9500.0,
        "order_id": "goal-compound-progress-probe-paper_target_compound-1",
        "price": 0.8199896784878153,
        "quote_timestamp": 1779545323,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 9500.0,
        "shares": 11585.51168292683,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_target_compound",
        "taker": true,
        "timestamp": 1779545323
      }
    ],
    "metrics": {
      "cash": 448.6970600000004,
      "ending_equity": 9925.645616634147,
      "fees": 51.30294,
      "filled_orders": 1.0,
      "initial_cash": 10000.0,
      "max_drawdown": -0.007435438336585321,
      "missed_orders": 0.0,
      "orders": 1.0,
      "partial_orders": 0.0,
      "pending_orders": 0.0,
      "pnl": -74.35438336585321,
      "roi": -0.007435438336585321,
      "turnover": 9500.0
    },
    "orders": [
      {
        "created_at": 1779545323,
        "eligible_at": 1779545323,
        "order_id": "goal-compound-progress-probe-paper_target_compound-1",
        "signal": {
          "asset": "87978082071653935678874296685430503892266481242311708420787197372467948088235",
          "condition_id": "0xf8f63bb47b2a7c2e0c1be3cedf4075079b11c07476d76a9469065b0c4791961a",
          "reason": "target_opportunity_momentum score=0.1169 exit_bid=0.8368 exit_distance=2.29% imbalance=0.13 mark_loss=0.78%",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_compound",
          "target_notional": 9500.0,
          "timestamp": 1779545323
        }
      }
    ],
    "strategy": "paper_target_compound"
  }
]
```
