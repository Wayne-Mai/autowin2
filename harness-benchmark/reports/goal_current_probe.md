# Polymarket Paper Replay Report

| Strategy | PnL | ROI | Orders | Filled | Partial | Missed | Turnover | Fees | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| paper_target_balanced | 0.0000 | 0.0000% | 0 | 0 | 0 | 0 | 0.0000 | 0.0000 | 0.0000% |
| paper_target_aggressive | -979.1494 | -9.7915% | 2 | 2 | 0 | 0 | 18473.5252 | 452.6746 | -9.7915% |
| paper_target_conservative | 0.0000 | 0.0000% | 0 | 0 | 0 | 0 | 0.0000 | 0.0000 | 0.0000% |

## Raw Metrics

```json
[
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
    "strategy": "paper_target_balanced"
  },
  {
    "fills": [
      {
        "asset": "101738487887518832481587379955535423775326921556438741919099866785354159699479",
        "average_price": 0.1881573709055145,
        "fee": 231.37079000000003,
        "filled_notional": 9500.0,
        "liquidity_source": "paper_run",
        "notional": 9500.0,
        "order_id": "goal-current-probe-paper_target_aggressive-1",
        "price": 0.1881573709055145,
        "quote_timestamp": 1779543134,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 9500.0,
        "shares": 50489.651052631576,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_target_aggressive",
        "taker": true,
        "timestamp": 1779543134
      },
      {
        "asset": "101738487887518832481587379955535423775326921556438741919099866785354159699479",
        "average_price": 0.1777299908474209,
        "fee": 221.30382999999998,
        "filled_notional": 8973.525219473684,
        "liquidity_source": "paper_run",
        "notional": 8973.525219473684,
        "order_id": "goal-current-probe-paper_target_aggressive-2",
        "price": 0.1777299908474209,
        "quote_timestamp": 1779543174,
        "reason": "depth_fill_at_bids_minus_slippage",
        "requested_notional": 9189.116491578947,
        "shares": 50489.651052631576,
        "side": "SELL",
        "status": "FILLED",
        "strategy": "paper_target_aggressive",
        "taker": true,
        "timestamp": 1779543174
      }
    ],
    "metrics": {
      "cash": 9020.850599473682,
      "ending_equity": 9020.850599473682,
      "fees": 452.67462,
      "filled_orders": 2.0,
      "initial_cash": 10000.0,
      "max_drawdown": -0.09791494005263175,
      "missed_orders": 0.0,
      "orders": 2.0,
      "partial_orders": 0.0,
      "pending_orders": 0.0,
      "pnl": -979.1494005263175,
      "roi": -0.09791494005263175,
      "turnover": 18473.525219473682
    },
    "orders": [
      {
        "created_at": 1779543134,
        "eligible_at": 1779543134,
        "order_id": "goal-current-probe-paper_target_aggressive-1",
        "signal": {
          "asset": "101738487887518832481587379955535423775326921556438741919099866785354159699479",
          "condition_id": "0xf8f63bb47b2a7c2e0c1be3cedf4075079b11c07476d76a9469065b0c4791961a",
          "reason": "target_opportunity_momentum score=0.7438 exit_bid=0.2177 imbalance=0.10",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_aggressive",
          "target_notional": 9500.0,
          "timestamp": 1779543134
        }
      },
      {
        "created_at": 1779543174,
        "eligible_at": 1779543174,
        "order_id": "goal-current-probe-paper_target_aggressive-2",
        "signal": {
          "asset": "101738487887518832481587379955535423775326921556438741919099866785354159699479",
          "condition_id": "0xf8f63bb47b2a7c2e0c1be3cedf4075079b11c07476d76a9469065b0c4791961a",
          "reason": "stop_loss",
          "side": "SELL",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_aggressive",
          "target_notional": 9189.116491578947,
          "timestamp": 1779543174
        }
      }
    ],
    "strategy": "paper_target_aggressive"
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
    "strategy": "paper_target_conservative"
  }
]
```
