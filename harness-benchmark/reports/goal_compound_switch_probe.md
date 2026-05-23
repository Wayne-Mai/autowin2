# Polymarket Paper Replay Report

| Strategy | PnL | ROI | Orders | Filled | Partial | Missed | Turnover | Fees | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| paper_target_compound | -291.9383 | -2.9194% | 4 | 4 | 0 | 0 | 37698.0275 | 204.0131 | -2.9194% |

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
        "order_id": "goal-compound-switch-probe-paper_target_compound-1",
        "price": 0.8230000000000001,
        "quote_timestamp": 1779544988,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 9500.0,
        "shares": 11543.134872417982,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_target_compound",
        "taker": true,
        "timestamp": 1779544988
      },
      {
        "asset": "32270411694523539495262303868629477861017829722282576458031815333486368239544",
        "average_price": 0.8220000000000001,
        "fee": 50.66836,
        "filled_notional": 9488.45686512758,
        "liquidity_source": "paper_run",
        "notional": 9488.45686512758,
        "order_id": "goal-compound-switch-probe-paper_target_compound-2",
        "price": 0.8220000000000001,
        "quote_timestamp": 1779545079,
        "reason": "depth_fill_at_bids_minus_slippage",
        "requested_notional": 9488.45686512758,
        "shares": 11543.13487241798,
        "side": "SELL",
        "status": "FILLED",
        "strategy": "paper_target_compound",
        "taker": true,
        "timestamp": 1779545079
      },
      {
        "asset": "87978082071653935678874296685430503892266481242311708420787197372467948088235",
        "average_price": 0.8199895608858953,
        "fee": 50.72501,
        "filled_notional": 9392.976329871202,
        "liquidity_source": "paper_run",
        "notional": 9392.976329871202,
        "order_id": "goal-compound-switch-probe-paper_target_compound-3",
        "price": 0.8199895608858953,
        "quote_timestamp": 1779545090,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 9392.976329871202,
        "shares": 11454.99501203805,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_target_compound",
        "taker": true,
        "timestamp": 1779545090
      },
      {
        "asset": "87978082071653935678874296685430503892266481242311708420787197372467948088235",
        "average_price": 0.8133215492441587,
        "fee": 52.17474,
        "filled_notional": 9316.594289774897,
        "liquidity_source": "paper_run",
        "notional": 9316.594289774897,
        "order_id": "goal-compound-switch-probe-paper_target_compound-4",
        "price": 0.8133215492441587,
        "quote_timestamp": 1779545130,
        "reason": "depth_fill_at_bids_minus_slippage",
        "requested_notional": 9370.185919847125,
        "shares": 11454.99501203805,
        "side": "SELL",
        "status": "FILLED",
        "strategy": "paper_target_compound",
        "taker": true,
        "timestamp": 1779545130
      }
    ],
    "metrics": {
      "cash": 9708.061715031276,
      "ending_equity": 9708.061715031276,
      "fees": 204.01310999999998,
      "filled_orders": 4.0,
      "initial_cash": 10000.0,
      "max_drawdown": -0.029193828496872447,
      "missed_orders": 0.0,
      "orders": 4.0,
      "partial_orders": 0.0,
      "pending_orders": 0.0,
      "pnl": -291.9382849687245,
      "roi": -0.029193828496872447,
      "turnover": 37698.02748477368
    },
    "orders": [
      {
        "created_at": 1779544988,
        "eligible_at": 1779544988,
        "order_id": "goal-compound-switch-probe-paper_target_compound-1",
        "signal": {
          "asset": "32270411694523539495262303868629477861017829722282576458031815333486368239544",
          "condition_id": "0x9b6fef249040fd17e9c107955b37ac2c3e923509b6b0ff01cc463a331ddeb894",
          "reason": "target_opportunity_momentum score=0.1203 exit_bid=0.8397 exit_distance=2.15% imbalance=0.15 mark_loss=0.65%",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_compound",
          "target_notional": 9500.0,
          "timestamp": 1779544988
        }
      },
      {
        "created_at": 1779545079,
        "eligible_at": 1779545079,
        "order_id": "goal-compound-switch-probe-paper_target_compound-2",
        "signal": {
          "asset": "32270411694523539495262303868629477861017829722282576458031815333486368239544",
          "condition_id": "0x9b6fef249040fd17e9c107955b37ac2c3e923509b6b0ff01cc463a331ddeb894",
          "reason": "max_hold_exit",
          "side": "SELL",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_compound",
          "target_notional": 9488.45686512758,
          "timestamp": 1779545079
        }
      },
      {
        "created_at": 1779545090,
        "eligible_at": 1779545090,
        "order_id": "goal-compound-switch-probe-paper_target_compound-3",
        "signal": {
          "asset": "87978082071653935678874296685430503892266481242311708420787197372467948088235",
          "condition_id": "0xf8f63bb47b2a7c2e0c1be3cedf4075079b11c07476d76a9469065b0c4791961a",
          "reason": "target_opportunity_momentum score=0.1167 exit_bid=0.8368 exit_distance=2.29% imbalance=0.13 mark_loss=0.78%",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_compound",
          "target_notional": 9392.976329871202,
          "timestamp": 1779545090
        }
      },
      {
        "created_at": 1779545130,
        "eligible_at": 1779545130,
        "order_id": "goal-compound-switch-probe-paper_target_compound-4",
        "signal": {
          "asset": "87978082071653935678874296685430503892266481242311708420787197372467948088235",
          "condition_id": "0xf8f63bb47b2a7c2e0c1be3cedf4075079b11c07476d76a9469065b0c4791961a",
          "reason": "max_hold_exit",
          "side": "SELL",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_compound",
          "target_notional": 9370.185919847125,
          "timestamp": 1779545130
        }
      }
    ],
    "strategy": "paper_target_compound"
  }
]
```
