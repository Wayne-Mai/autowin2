# Polymarket Paper Replay Report

| Strategy | PnL | ROI | Orders | Filled | Partial | Missed | Turnover | Fees | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| paper_target_micro_compound | -33.2837 | -0.3328% | 2 | 2 | 0 | 0 | 402.4932 | 13.6525 | -0.3328% |

## Raw Metrics

```json
[
  {
    "fills": [
      {
        "asset": "46532026588259081338975869184183765613400177851893354159085997873374092525848",
        "average_price": 0.515124701410278,
        "fee": 10.5956,
        "filled_notional": 312.40100264549255,
        "liquidity_source": "paper_run",
        "notional": 312.40100264549255,
        "order_id": "goal-micro-compound-probe-paper_target_micro_compound-1",
        "price": 0.515124701410278,
        "quote_timestamp": 1779549091,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 312.40100264549255,
        "shares": 606.4570419360973,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_target_micro_compound",
        "taker": true,
        "timestamp": 1779549091
      },
      {
        "asset": "19982334401337488874735470001892824349216263984710413542991338788708306324126",
        "average_price": 0.5151246948316105,
        "fee": 3.05688,
        "filled_notional": 90.09216220462947,
        "liquidity_source": "paper_run",
        "notional": 90.09216220462947,
        "order_id": "goal-micro-compound-probe-paper_target_micro_compound-2",
        "price": 0.5151246948316105,
        "quote_timestamp": 1779548166,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 90.09216220462947,
        "shares": 174.89389095213107,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_target_micro_compound",
        "taker": true,
        "timestamp": 1779548166
      }
    ],
    "metrics": {
      "cash": 9583.854355149877,
      "ending_equity": 9966.716312265109,
      "fees": 13.652479999999999,
      "filled_orders": 2.0,
      "initial_cash": 10000.0,
      "max_drawdown": -0.0033283687734890917,
      "missed_orders": 0.0,
      "orders": 2.0,
      "partial_orders": 0.0,
      "pending_orders": 0.0,
      "pnl": -33.28368773489092,
      "roi": -0.0033283687734890917,
      "turnover": 402.493164850122
    },
    "orders": [
      {
        "created_at": 1779549091,
        "eligible_at": 1779549091,
        "order_id": "goal-micro-compound-probe-paper_target_micro_compound-1",
        "signal": {
          "asset": "46532026588259081338975869184183765613400177851893354159085997873374092525848",
          "condition_id": "0x58b8de7f21c91c7a655bc1411680fba62cad5655552336da2cbb9cfb3d1aa75a",
          "reason": "target_opportunity_momentum score=0.0280 exit_bid=0.5552 exit_distance=13.31% imbalance=0.08 mark_loss=8.00%",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_micro_compound",
          "target_notional": 312.40100264549255,
          "timestamp": 1779549091
        }
      },
      {
        "created_at": 1779548166,
        "eligible_at": 1779548166,
        "order_id": "goal-micro-compound-probe-paper_target_micro_compound-2",
        "signal": {
          "asset": "19982334401337488874735470001892824349216263984710413542991338788708306324126",
          "condition_id": "0x92ba8546851d2747687a4005fe6792a2d8bc955a04e6890295199e4cb2e7beba",
          "reason": "target_opportunity_momentum score=0.0218 exit_bid=0.5552 exit_distance=13.31% imbalance=0.02 mark_loss=8.00%",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_micro_compound",
          "target_notional": 90.09216220462947,
          "timestamp": 1779548166
        }
      }
    ],
    "strategy": "paper_target_micro_compound"
  }
]
```
