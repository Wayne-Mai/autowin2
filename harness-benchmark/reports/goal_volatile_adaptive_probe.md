# Polymarket Paper Replay Report

| Strategy | PnL | ROI | Orders | Filled | Partial | Missed | Turnover | Fees | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| paper_target_volatile_compound | -135.4039 | -1.3540% | 2 | 2 | 0 | 0 | 1166.9280 | 40.5463 | -1.3540% |

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
        "order_id": "goal-volatile-adaptive-probe-paper_target_volatile_compound-1",
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
      },
      {
        "asset": "46532026588259081338975869184183765613400177851893354159085997873374092525848",
        "average_price": 0.4583217306714003,
        "fee": 20.27036,
        "filled_notional": 536.0352019625861,
        "liquidity_source": "paper_run",
        "notional": 536.0352019625861,
        "order_id": "goal-volatile-adaptive-probe-paper_target_volatile_compound-2",
        "price": 0.4583217306714003,
        "quote_timestamp": 1779546228,
        "reason": "depth_fill_at_bids_minus_slippage",
        "requested_notional": 573.0848689563505,
        "shares": 1169.5609570537765,
        "side": "SELL",
        "status": "FILLED",
        "strategy": "paper_target_volatile_compound",
        "taker": true,
        "timestamp": 1779546228
      }
    ],
    "metrics": {
      "cash": 9864.596146871396,
      "ending_equity": 9864.596146871396,
      "fees": 40.5463,
      "filled_orders": 2.0,
      "initial_cash": 10000.0,
      "max_drawdown": -0.013540385312860417,
      "missed_orders": 0.0,
      "orders": 2.0,
      "partial_orders": 0.0,
      "pending_orders": 0.0,
      "pnl": -135.40385312860417,
      "roi": -0.013540385312860417,
      "turnover": 1166.9279570537765
    },
    "orders": [
      {
        "created_at": 1779546228,
        "eligible_at": 1779546228,
        "order_id": "goal-volatile-adaptive-probe-paper_target_volatile_compound-1",
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
      },
      {
        "created_at": 1779546228,
        "eligible_at": 1779546228,
        "order_id": "goal-volatile-adaptive-probe-paper_target_volatile_compound-2",
        "signal": {
          "asset": "46532026588259081338975869184183765613400177851893354159085997873374092525848",
          "condition_id": "0x58b8de7f21c91c7a655bc1411680fba62cad5655552336da2cbb9cfb3d1aa75a",
          "reason": "max_hold_exit",
          "side": "SELL",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_volatile_compound",
          "target_notional": 573.0848689563505,
          "timestamp": 1779546228
        }
      }
    ],
    "strategy": "paper_target_volatile_compound"
  }
]
```
