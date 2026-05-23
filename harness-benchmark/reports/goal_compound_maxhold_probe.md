# Polymarket Paper Replay Report

| Strategy | PnL | ROI | Orders | Filled | Partial | Missed | Turnover | Fees | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| paper_target_compound | -224.0438 | -2.2404% | 4 | 4 | 0 | 0 | 37762.9964 | 201.0876 | -2.2404% |
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
        "order_id": "goal-compound-maxhold-probe-paper_target_compound-1",
        "price": 0.8230000000000001,
        "quote_timestamp": 1779544746,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 9500.0,
        "shares": 11543.134872417982,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_target_compound",
        "taker": true,
        "timestamp": 1779544746
      },
      {
        "asset": "32270411694523539495262303868629477861017829722282576458031815333486368239544",
        "average_price": 0.8220000000000001,
        "fee": 50.66836,
        "filled_notional": 9488.45686512758,
        "liquidity_source": "paper_run",
        "notional": 9488.45686512758,
        "order_id": "goal-compound-maxhold-probe-paper_target_compound-3",
        "price": 0.8220000000000001,
        "quote_timestamp": 1779544807,
        "reason": "depth_fill_at_bids_minus_slippage",
        "requested_notional": 9488.45686512758,
        "shares": 11543.13487241798,
        "side": "SELL",
        "status": "FILLED",
        "strategy": "paper_target_compound",
        "taker": true,
        "timestamp": 1779544807
      },
      {
        "asset": "32270411694523539495262303868629477861017829722282576458031815333486368239544",
        "average_price": 0.8230000000000001,
        "fee": 49.8767,
        "filled_notional": 9392.976329871202,
        "liquidity_source": "paper_run",
        "notional": 9392.976329871202,
        "order_id": "goal-compound-maxhold-probe-paper_target_compound-4",
        "price": 0.8230000000000001,
        "quote_timestamp": 1779544837,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 9392.976329871202,
        "shares": 11413.093960961363,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_target_compound",
        "taker": true,
        "timestamp": 1779544837
      },
      {
        "asset": "32270411694523539495262303868629477861017829722282576458031815333486368239544",
        "average_price": 0.8220000000000001,
        "fee": 50.09755,
        "filled_notional": 9381.56323591024,
        "liquidity_source": "paper_run",
        "notional": 9381.56323591024,
        "order_id": "goal-compound-maxhold-probe-paper_target_compound-5",
        "price": 0.8220000000000001,
        "quote_timestamp": 1779544897,
        "reason": "depth_fill_at_bids_minus_slippage",
        "requested_notional": 9381.56323591024,
        "shares": 11413.093960961362,
        "side": "SELL",
        "status": "FILLED",
        "strategy": "paper_target_compound",
        "taker": true,
        "timestamp": 1779544897
      }
    ],
    "metrics": {
      "cash": 9775.956161166618,
      "ending_equity": 9775.956161166618,
      "fees": 201.08760999999998,
      "filled_orders": 4.0,
      "initial_cash": 10000.0,
      "max_drawdown": -0.022404383883338232,
      "missed_orders": 0.0,
      "orders": 4.0,
      "partial_orders": 0.0,
      "pending_orders": 0.0,
      "pnl": -224.04383883338232,
      "roi": -0.022404383883338232,
      "turnover": 37762.99643090902
    },
    "orders": [
      {
        "created_at": 1779544746,
        "eligible_at": 1779544746,
        "order_id": "goal-compound-maxhold-probe-paper_target_compound-1",
        "signal": {
          "asset": "32270411694523539495262303868629477861017829722282576458031815333486368239544",
          "condition_id": "0x9b6fef249040fd17e9c107955b37ac2c3e923509b6b0ff01cc463a331ddeb894",
          "reason": "target_opportunity_momentum score=0.1203 exit_bid=0.8397 exit_distance=2.15% imbalance=0.15 mark_loss=0.65%",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_compound",
          "target_notional": 9500.0,
          "timestamp": 1779544746
        }
      },
      {
        "created_at": 1779544807,
        "eligible_at": 1779544807,
        "order_id": "goal-compound-maxhold-probe-paper_target_compound-3",
        "signal": {
          "asset": "32270411694523539495262303868629477861017829722282576458031815333486368239544",
          "condition_id": "0x9b6fef249040fd17e9c107955b37ac2c3e923509b6b0ff01cc463a331ddeb894",
          "reason": "max_hold_exit",
          "side": "SELL",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_compound",
          "target_notional": 9488.45686512758,
          "timestamp": 1779544807
        }
      },
      {
        "created_at": 1779544837,
        "eligible_at": 1779544837,
        "order_id": "goal-compound-maxhold-probe-paper_target_compound-4",
        "signal": {
          "asset": "32270411694523539495262303868629477861017829722282576458031815333486368239544",
          "condition_id": "0x9b6fef249040fd17e9c107955b37ac2c3e923509b6b0ff01cc463a331ddeb894",
          "reason": "target_opportunity_momentum score=0.1203 exit_bid=0.8397 exit_distance=2.15% imbalance=0.15 mark_loss=0.65%",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_compound",
          "target_notional": 9392.976329871202,
          "timestamp": 1779544837
        }
      },
      {
        "created_at": 1779544897,
        "eligible_at": 1779544897,
        "order_id": "goal-compound-maxhold-probe-paper_target_compound-5",
        "signal": {
          "asset": "32270411694523539495262303868629477861017829722282576458031815333486368239544",
          "condition_id": "0x9b6fef249040fd17e9c107955b37ac2c3e923509b6b0ff01cc463a331ddeb894",
          "reason": "max_hold_exit",
          "side": "SELL",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_compound",
          "target_notional": 9381.56323591024,
          "timestamp": 1779544897
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
        "order_id": "goal-compound-maxhold-probe-paper_target_near_target-2",
        "price": 0.8230000000000001,
        "quote_timestamp": 1779544746,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 9500.0,
        "shares": 11543.134872417982,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_target_near_target",
        "taker": true,
        "timestamp": 1779544746
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
        "created_at": 1779544746,
        "eligible_at": 1779544746,
        "order_id": "goal-compound-maxhold-probe-paper_target_near_target-2",
        "signal": {
          "asset": "32270411694523539495262303868629477861017829722282576458031815333486368239544",
          "condition_id": "0x9b6fef249040fd17e9c107955b37ac2c3e923509b6b0ff01cc463a331ddeb894",
          "reason": "target_opportunity_momentum score=-0.1428 exit_bid=0.9163 exit_distance=11.47% imbalance=0.15 mark_loss=0.65%",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_near_target",
          "target_notional": 9500.0,
          "timestamp": 1779544746
        }
      }
    ],
    "strategy": "paper_target_near_target"
  }
]
```
