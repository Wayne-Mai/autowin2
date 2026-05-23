# Polymarket Paper Replay Report

| Strategy | PnL | ROI | Orders | Filled | Partial | Missed | Turnover | Fees | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| paper_target_compound_quality | -42.6182 | -0.4262% | 1 | 1 | 0 | 0 | 9500.0000 | 31.9200 | -0.4262% |

## Raw Metrics

```json
[
  {
    "fills": [
      {
        "asset": "77121637225348873006259930776623502125079210522997384841464684944292365296940",
        "average_price": 0.8879999999999999,
        "fee": 31.92,
        "filled_notional": 9500.0,
        "liquidity_source": "paper_run",
        "notional": 9500.0,
        "order_id": "goal-ordered-quality-entry-probe-paper_target_compound_quality-1",
        "price": 0.8879999999999999,
        "quote_timestamp": 1779546218,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 9500.0,
        "shares": 10698.198198198199,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_target_compound_quality",
        "taker": true,
        "timestamp": 1779546218
      }
    ],
    "metrics": {
      "cash": 468.0799999999999,
      "ending_equity": 9957.381801801803,
      "fees": 31.92,
      "filled_orders": 1.0,
      "initial_cash": 10000.0,
      "max_drawdown": -0.004261819819819721,
      "missed_orders": 0.0,
      "orders": 1.0,
      "partial_orders": 0.0,
      "pending_orders": 0.0,
      "pnl": -42.618198198197206,
      "roi": -0.004261819819819721,
      "turnover": 9500.0
    },
    "orders": [
      {
        "created_at": 1779546218,
        "eligible_at": 1779546218,
        "order_id": "goal-ordered-quality-entry-probe-paper_target_compound_quality-1",
        "signal": {
          "asset": "77121637225348873006259930776623502125079210522997384841464684944292365296940",
          "condition_id": "0x375409bc5eeeff961e82b479caeccc20f33d15738e5bce1186d628aa3d9dfb1f",
          "reason": "target_opportunity_momentum score=0.0393 exit_bid=0.9025 exit_distance=1.75% imbalance=0.24 mark_loss=0.45%",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_compound_quality",
          "target_notional": 9500.0,
          "timestamp": 1779546218
        }
      }
    ],
    "strategy": "paper_target_compound_quality"
  }
]
```
