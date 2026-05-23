# Polymarket Paper Replay Report

| Strategy | PnL | ROI | Orders | Filled | Partial | Missed | Turnover | Fees | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| paper_target_volatile_compound | -154.1455 | -1.5415% | 2 | 2 | 0 | 0 | 1245.0573 | 40.0625 | -1.5415% |

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
        "order_id": "goal-volatile-diversified-probe-paper_target_volatile_compound-1",
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
        "asset": "19982334401337488874735470001892824349216263984710413542991338788708306324126",
        "average_price": 0.5394269898702266,
        "fee": 19.78656,
        "filled_notional": 614.1645814017506,
        "liquidity_source": "paper_run",
        "notional": 614.1645814017506,
        "order_id": "goal-volatile-diversified-probe-paper_target_volatile_compound-2",
        "price": 0.5394269898702266,
        "quote_timestamp": 1779546228,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 614.1645814017506,
        "shares": 1138.5499667888403,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_target_volatile_compound",
        "taker": true,
        "timestamp": 1779546228
      }
    ],
    "metrics": {
      "cash": 8714.88016350706,
      "ending_equity": 9845.854516189942,
      "fees": 40.0625,
      "filled_orders": 2.0,
      "initial_cash": 10000.0,
      "max_drawdown": -0.015414548381005807,
      "missed_orders": 0.0,
      "orders": 2.0,
      "partial_orders": 0.0,
      "pending_orders": 0.0,
      "pnl": -154.14548381005807,
      "roi": -0.015414548381005807,
      "turnover": 1245.057336492941
    },
    "orders": [
      {
        "created_at": 1779546228,
        "eligible_at": 1779546228,
        "order_id": "goal-volatile-diversified-probe-paper_target_volatile_compound-1",
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
        "order_id": "goal-volatile-diversified-probe-paper_target_volatile_compound-2",
        "signal": {
          "asset": "19982334401337488874735470001892824349216263984710413542991338788708306324126",
          "condition_id": "0x92ba8546851d2747687a4005fe6792a2d8bc955a04e6890295199e4cb2e7beba",
          "reason": "target_opportunity_momentum score=-0.0318 exit_bid=0.6288 exit_distance=28.33% imbalance=0.02 mark_loss=12.00%",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_volatile_compound",
          "target_notional": 614.1645814017506,
          "timestamp": 1779546228
        }
      }
    ],
    "strategy": "paper_target_volatile_compound"
  }
]
```
