# Polymarket Paper Replay Report

| Strategy | PnL | ROI | Orders | Filled | Partial | Missed | Turnover | Fees | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| paper_target_volatile_compound | -235.4901 | -2.3549% | 3 | 3 | 0 | 0 | 1902.6706 | 61.1508 | -2.3549% |

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
        "order_id": "goal-volatile-multi-probe-paper_target_volatile_compound-1",
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
        "asset": "44968738055270247318529370107374681251853502250167714352070267579707432153273",
        "average_price": 0.5394269893871757,
        "fee": 20.51562,
        "filled_notional": 638.3086968431197,
        "liquidity_source": "paper_run",
        "notional": 638.3086968431197,
        "order_id": "goal-volatile-multi-probe-paper_target_volatile_compound-2",
        "price": 0.5394269893871757,
        "quote_timestamp": 1779546234,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 638.3086968431197,
        "shares": 1183.308787660551,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_target_volatile_compound",
        "taker": true,
        "timestamp": 1779546234
      },
      {
        "asset": "83772953121098312130154813833007134739769427797493023957359314028162792240646",
        "average_price": 0.5394269857837083,
        "fee": 20.35927,
        "filled_notional": 633.4691772819915,
        "liquidity_source": "paper_run",
        "notional": 633.4691772819915,
        "order_id": "goal-volatile-multi-probe-paper_target_volatile_compound-3",
        "price": 0.5394269857837083,
        "quote_timestamp": 1779546228,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 633.4691772819915,
        "shares": 1174.3372022103301,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_target_volatile_compound",
        "taker": true,
        "timestamp": 1779546228
      }
    ],
    "metrics": {
      "cash": 8036.178540783699,
      "ending_equity": 9764.50994477678,
      "fees": 61.15083,
      "filled_orders": 3.0,
      "initial_cash": 10000.0,
      "max_drawdown": -0.02354900552232193,
      "missed_orders": 0.0,
      "orders": 3.0,
      "partial_orders": 0.0,
      "pending_orders": 0.0,
      "pnl": -235.49005522321931,
      "roi": -0.02354900552232193,
      "turnover": 1902.6706292163017
    },
    "orders": [
      {
        "created_at": 1779546228,
        "eligible_at": 1779546228,
        "order_id": "goal-volatile-multi-probe-paper_target_volatile_compound-1",
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
        "created_at": 1779546234,
        "eligible_at": 1779546234,
        "order_id": "goal-volatile-multi-probe-paper_target_volatile_compound-2",
        "signal": {
          "asset": "44968738055270247318529370107374681251853502250167714352070267579707432153273",
          "condition_id": "0x7f6ea00dc7a1b5dc7d33734b047bc6c3b1b9cc0072ba4d4dc8d7217feb1dbac2",
          "reason": "target_opportunity_momentum score=-0.0257 exit_bid=0.6288 exit_distance=28.33% imbalance=0.08 mark_loss=12.00%",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_volatile_compound",
          "target_notional": 638.3086968431197,
          "timestamp": 1779546234
        }
      },
      {
        "created_at": 1779546228,
        "eligible_at": 1779546228,
        "order_id": "goal-volatile-multi-probe-paper_target_volatile_compound-3",
        "signal": {
          "asset": "83772953121098312130154813833007134739769427797493023957359314028162792240646",
          "condition_id": "0xf0cdc544de0b5797108e92e366f3ec1a5bc2d7f6aaf14d1f59a71352fd2f4b7b",
          "reason": "target_opportunity_momentum score=-0.0258 exit_bid=0.6288 exit_distance=28.33% imbalance=0.08 mark_loss=12.00%",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_volatile_compound",
          "target_notional": 633.4691772819915,
          "timestamp": 1779546228
        }
      }
    ],
    "strategy": "paper_target_volatile_compound"
  }
]
```
