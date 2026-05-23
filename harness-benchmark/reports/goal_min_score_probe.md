# Polymarket Paper Replay Report

| Strategy | PnL | ROI | Orders | Filled | Partial | Missed | Turnover | Fees | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| paper_target_volatile_compound | -84.8255 | -0.8483% | 2 | 2 | 0 | 0 | 786.9339 | 25.8647 | -0.8483% |
| paper_target_compound_quality | 0.0000 | 0.0000% | 0 | 0 | 0 | 0 | 0.0000 | 0.0000 | 0.0000% |

## Raw Metrics

```json
[
  {
    "fills": [
      {
        "asset": "42417411459178368443600583298935691581346313752999656519238534786985010533220",
        "average_price": 0.5300501822844514,
        "fee": 16.453210000000002,
        "filled_notional": 501.29177421331406,
        "liquidity_source": "paper_run",
        "notional": 501.29177421331406,
        "order_id": "goal-min-score-probe-paper_target_volatile_compound-1",
        "price": 0.5300501822844514,
        "quote_timestamp": 1779546224,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 501.29177421331406,
        "shares": 945.7439898479195,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_target_volatile_compound",
        "taker": true,
        "timestamp": 1779546224
      },
      {
        "asset": "19982334401337488874735470001892824349216263984710413542991338788708306324126",
        "average_price": 0.5290497680491772,
        "fee": 9.411529999999999,
        "filled_notional": 285.64217202954313,
        "liquidity_source": "paper_run",
        "notional": 285.64217202954313,
        "order_id": "goal-min-score-probe-paper_target_volatile_compound-2",
        "price": 0.5290497680491772,
        "quote_timestamp": 1779548166,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 285.64217202954313,
        "shares": 539.9155037584131,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_target_volatile_compound",
        "taker": true,
        "timestamp": 1779548166
      }
    ],
    "metrics": {
      "cash": 9187.201313757143,
      "ending_equity": 9915.174465624244,
      "fees": 25.86474,
      "filled_orders": 2.0,
      "initial_cash": 10000.0,
      "max_drawdown": -0.008482553437575552,
      "missed_orders": 0.0,
      "orders": 2.0,
      "partial_orders": 0.0,
      "pending_orders": 0.0,
      "pnl": -84.82553437575552,
      "roi": -0.008482553437575552,
      "turnover": 786.9339462428572
    },
    "orders": [
      {
        "created_at": 1779546224,
        "eligible_at": 1779546224,
        "order_id": "goal-min-score-probe-paper_target_volatile_compound-1",
        "signal": {
          "asset": "42417411459178368443600583298935691581346313752999656519238534786985010533220",
          "condition_id": "0x8a5a1abcd287065d83b0f1e09b885112e600574fa05c780d82e4b8d20f147370",
          "reason": "target_opportunity_momentum score=0.0200 exit_bid=0.6187 exit_distance=26.28% imbalance=0.07 mark_loss=10.50%",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_volatile_compound",
          "target_notional": 501.29177421331406,
          "timestamp": 1779546224
        }
      },
      {
        "created_at": 1779548166,
        "eligible_at": 1779548166,
        "order_id": "goal-min-score-probe-paper_target_volatile_compound-2",
        "signal": {
          "asset": "19982334401337488874735470001892824349216263984710413542991338788708306324126",
          "condition_id": "0x92ba8546851d2747687a4005fe6792a2d8bc955a04e6890295199e4cb2e7beba",
          "reason": "target_opportunity_momentum score=0.0200 exit_bid=0.6177 exit_distance=26.06% imbalance=0.02 mark_loss=10.34%",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_volatile_compound",
          "target_notional": 285.64217202954313,
          "timestamp": 1779548166
        }
      }
    ],
    "strategy": "paper_target_volatile_compound"
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
    "strategy": "paper_target_compound_quality"
  }
]
```
