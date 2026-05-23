# Polymarket Paper Replay Report

| Strategy | PnL | ROI | Orders | Filled | Partial | Missed | Turnover | Fees | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| paper_target_volatile_compound | -78.0838 | -0.7808% | 1 | 1 | 0 | 0 | 630.8928 | 20.2759 | -0.7808% |

## Raw Metrics

```json
[
  {
    "fills": [
      {
        "asset": "46532026588259081338975869184183765613400177851893354159085997873374092525848",
        "average_price": 0.5394269971874427,
        "fee": 20.27594,
        "filled_notional": 630.8927550911903,
        "liquidity_source": "paper_run",
        "notional": 630.8927550911903,
        "order_id": "goal-volatile-adaptive-hold-probe-paper_target_volatile_compound-1",
        "price": 0.5394269971874427,
        "quote_timestamp": 1779546228,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 630.8927550911903,
        "shares": 1169.5609570537765,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_target_volatile_compound",
        "taker": true,
        "timestamp": 1779546228
      }
    ],
    "metrics": {
      "cash": 9348.83130490881,
      "ending_equity": 9921.91617386516,
      "fees": 20.27594,
      "filled_orders": 1.0,
      "initial_cash": 10000.0,
      "max_drawdown": -0.007808382613483991,
      "missed_orders": 0.0,
      "orders": 1.0,
      "partial_orders": 0.0,
      "pending_orders": 0.0,
      "pnl": -78.08382613483991,
      "roi": -0.007808382613483991,
      "turnover": 630.8927550911903
    },
    "orders": [
      {
        "created_at": 1779546228,
        "eligible_at": 1779546228,
        "order_id": "goal-volatile-adaptive-hold-probe-paper_target_volatile_compound-1",
        "signal": {
          "asset": "46532026588259081338975869184183765613400177851893354159085997873374092525848",
          "condition_id": "0x58b8de7f21c91c7a655bc1411680fba62cad5655552336da2cbb9cfb3d1aa75a",
          "reason": "target_opportunity_momentum score=-0.0256 exit_bid=0.6288 exit_distance=28.33% imbalance=0.08 mark_loss=12.00%",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_volatile_compound",
          "target_notional": 630.8927550911903,
          "timestamp": 1779546228
        }
      }
    ],
    "strategy": "paper_target_volatile_compound"
  }
]
```
