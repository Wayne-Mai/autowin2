# Polymarket Paper Replay Report

| Strategy | PnL | ROI | Orders | Filled | Partial | Missed | Turnover | Fees | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| paper_target_compound | -61.9881 | -0.6199% | 1 | 1 | 0 | 0 | 9500.0000 | 50.4450 | -0.6199% |
| paper_target_near_target | -61.9881 | -0.6199% | 1 | 1 | 0 | 0 | 9500.0000 | 50.4450 | -0.6199% |

## Raw Metrics

```json
[
  {
    "fills": [
      {
        "asset": "32270411694523539495262303868629477861017829722282576458031815333486368239544",
        "average_price": 0.8230000000000001,
        "fee": 50.445,
        "filled_notional": 9500.0,
        "liquidity_source": "paper_run",
        "notional": 9500.0,
        "order_id": "goal-compound-feeaware-probe-paper_target_compound-1",
        "price": 0.8230000000000001,
        "quote_timestamp": 1779544444,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 9500.0,
        "shares": 11543.134872417982,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_target_compound",
        "taker": true,
        "timestamp": 1779544444
      }
    ],
    "metrics": {
      "cash": 449.5550000000003,
      "ending_equity": 9938.01186512758,
      "fees": 50.445,
      "filled_orders": 1.0,
      "initial_cash": 10000.0,
      "max_drawdown": -0.006198813487241933,
      "missed_orders": 0.0,
      "orders": 1.0,
      "partial_orders": 0.0,
      "pending_orders": 0.0,
      "pnl": -61.98813487241932,
      "roi": -0.006198813487241933,
      "turnover": 9500.0
    },
    "orders": [
      {
        "created_at": 1779544444,
        "eligible_at": 1779544444,
        "order_id": "goal-compound-feeaware-probe-paper_target_compound-1",
        "signal": {
          "asset": "32270411694523539495262303868629477861017829722282576458031815333486368239544",
          "condition_id": "0x9b6fef249040fd17e9c107955b37ac2c3e923509b6b0ff01cc463a331ddeb894",
          "reason": "target_opportunity_momentum score=0.1203 exit_bid=0.8397 exit_distance=2.15% imbalance=0.15 mark_loss=0.65%",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_compound",
          "target_notional": 9500.0,
          "timestamp": 1779544444
        }
      }
    ],
    "strategy": "paper_target_compound"
  },
  {
    "fills": [
      {
        "asset": "32270411694523539495262303868629477861017829722282576458031815333486368239544",
        "average_price": 0.8230000000000001,
        "fee": 50.445,
        "filled_notional": 9500.0,
        "liquidity_source": "paper_run",
        "notional": 9500.0,
        "order_id": "goal-compound-feeaware-probe-paper_target_near_target-2",
        "price": 0.8230000000000001,
        "quote_timestamp": 1779544444,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 9500.0,
        "shares": 11543.134872417982,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_target_near_target",
        "taker": true,
        "timestamp": 1779544444
      }
    ],
    "metrics": {
      "cash": 449.5550000000003,
      "ending_equity": 9938.01186512758,
      "fees": 50.445,
      "filled_orders": 1.0,
      "initial_cash": 10000.0,
      "max_drawdown": -0.006198813487241933,
      "missed_orders": 0.0,
      "orders": 1.0,
      "partial_orders": 0.0,
      "pending_orders": 0.0,
      "pnl": -61.98813487241932,
      "roi": -0.006198813487241933,
      "turnover": 9500.0
    },
    "orders": [
      {
        "created_at": 1779544444,
        "eligible_at": 1779544444,
        "order_id": "goal-compound-feeaware-probe-paper_target_near_target-2",
        "signal": {
          "asset": "32270411694523539495262303868629477861017829722282576458031815333486368239544",
          "condition_id": "0x9b6fef249040fd17e9c107955b37ac2c3e923509b6b0ff01cc463a331ddeb894",
          "reason": "target_opportunity_momentum score=-0.1427 exit_bid=0.9163 exit_distance=11.47% imbalance=0.15 mark_loss=0.65%",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_near_target",
          "target_notional": 9500.0,
          "timestamp": 1779544444
        }
      }
    ],
    "strategy": "paper_target_near_target"
  }
]
```
