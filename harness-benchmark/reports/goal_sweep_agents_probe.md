# Polymarket Paper Replay Report

| Strategy | PnL | ROI | Orders | Filled | Partial | Missed | Turnover | Fees | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| paper_sweep_001_tp0100_cap10_545953 | -45.9270 | -0.4593% | 1 | 1 | 0 | 0 | 1000.0000 | 18.9000 | -0.4593% |
| paper_sweep_002_tp0100_cap20_545953 | -91.8541 | -0.9185% | 1 | 1 | 0 | 0 | 2000.0000 | 37.8000 | -0.9185% |
| paper_sweep_003_tp0100_cap05_545953 | -22.9635 | -0.2296% | 1 | 1 | 0 | 0 | 500.0000 | 9.4500 | -0.2296% |

## Raw Metrics

```json
[
  {
    "fills": [
      {
        "asset": "44914465637297319816681463234953032477919413063019359633128421605039733545953",
        "average_price": 0.37,
        "fee": 18.9,
        "filled_notional": 1000.0000000000001,
        "liquidity_source": "paper_run",
        "notional": 1000.0000000000001,
        "order_id": "goal-sweep-agents-probe-paper_sweep_001_tp0100_cap10_545953-1",
        "price": 0.37,
        "quote_timestamp": 1779549880,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 1000.0,
        "shares": 2702.702702702703,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_sweep_001_tp0100_cap10_545953",
        "taker": true,
        "timestamp": 1779549880
      }
    ],
    "metrics": {
      "cash": 8981.1,
      "ending_equity": 9954.072972972974,
      "fees": 18.9,
      "filled_orders": 1.0,
      "initial_cash": 10000.0,
      "max_drawdown": -0.004592702702702627,
      "missed_orders": 0.0,
      "orders": 1.0,
      "partial_orders": 0.0,
      "pending_orders": 0.0,
      "pnl": -45.92702702702627,
      "roi": -0.004592702702702627,
      "turnover": 1000.0000000000001
    },
    "orders": [
      {
        "created_at": 1779549880,
        "eligible_at": 1779549880,
        "order_id": "goal-sweep-agents-probe-paper_sweep_001_tp0100_cap10_545953-1",
        "signal": {
          "asset": "44914465637297319816681463234953032477919413063019359633128421605039733545953",
          "condition_id": "0x22e7b5e35423e76842dd3a5e1a21d13793811080d5e7b2896d0c001bd5e97d54",
          "reason": "target_opportunity_momentum score=0.4775 exit_bid=0.3879 exit_distance=7.75% imbalance=0.52 mark_loss=4.51%",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_sweep_001_tp0100_cap10_545953",
          "target_notional": 1000.0,
          "timestamp": 1779549880
        }
      }
    ],
    "strategy": "paper_sweep_001_tp0100_cap10_545953"
  },
  {
    "fills": [
      {
        "asset": "44914465637297319816681463234953032477919413063019359633128421605039733545953",
        "average_price": 0.37,
        "fee": 37.8,
        "filled_notional": 2000.0000000000002,
        "liquidity_source": "paper_run",
        "notional": 2000.0000000000002,
        "order_id": "goal-sweep-agents-probe-paper_sweep_002_tp0100_cap20_545953-2",
        "price": 0.37,
        "quote_timestamp": 1779549880,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 2000.0,
        "shares": 5405.405405405406,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_sweep_002_tp0100_cap20_545953",
        "taker": true,
        "timestamp": 1779549880
      }
    ],
    "metrics": {
      "cash": 7962.2,
      "ending_equity": 9908.145945945946,
      "fees": 37.8,
      "filled_orders": 1.0,
      "initial_cash": 10000.0,
      "max_drawdown": -0.009185405405405436,
      "missed_orders": 0.0,
      "orders": 1.0,
      "partial_orders": 0.0,
      "pending_orders": 0.0,
      "pnl": -91.85405405405436,
      "roi": -0.009185405405405436,
      "turnover": 2000.0000000000002
    },
    "orders": [
      {
        "created_at": 1779549880,
        "eligible_at": 1779549880,
        "order_id": "goal-sweep-agents-probe-paper_sweep_002_tp0100_cap20_545953-2",
        "signal": {
          "asset": "44914465637297319816681463234953032477919413063019359633128421605039733545953",
          "condition_id": "0x22e7b5e35423e76842dd3a5e1a21d13793811080d5e7b2896d0c001bd5e97d54",
          "reason": "target_opportunity_momentum score=0.4775 exit_bid=0.3879 exit_distance=7.75% imbalance=0.52 mark_loss=4.51%",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_sweep_002_tp0100_cap20_545953",
          "target_notional": 2000.0,
          "timestamp": 1779549880
        }
      }
    ],
    "strategy": "paper_sweep_002_tp0100_cap20_545953"
  },
  {
    "fills": [
      {
        "asset": "44914465637297319816681463234953032477919413063019359633128421605039733545953",
        "average_price": 0.37,
        "fee": 9.45,
        "filled_notional": 500.00000000000006,
        "liquidity_source": "paper_run",
        "notional": 500.00000000000006,
        "order_id": "goal-sweep-agents-probe-paper_sweep_003_tp0100_cap05_545953-3",
        "price": 0.37,
        "quote_timestamp": 1779549880,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 500.0,
        "shares": 1351.3513513513515,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_sweep_003_tp0100_cap05_545953",
        "taker": true,
        "timestamp": 1779549880
      }
    ],
    "metrics": {
      "cash": 9490.55,
      "ending_equity": 9977.036486486486,
      "fees": 9.45,
      "filled_orders": 1.0,
      "initial_cash": 10000.0,
      "max_drawdown": -0.0022963513513514044,
      "missed_orders": 0.0,
      "orders": 1.0,
      "partial_orders": 0.0,
      "pending_orders": 0.0,
      "pnl": -22.963513513514044,
      "roi": -0.0022963513513514044,
      "turnover": 500.00000000000006
    },
    "orders": [
      {
        "created_at": 1779549880,
        "eligible_at": 1779549880,
        "order_id": "goal-sweep-agents-probe-paper_sweep_003_tp0100_cap05_545953-3",
        "signal": {
          "asset": "44914465637297319816681463234953032477919413063019359633128421605039733545953",
          "condition_id": "0x22e7b5e35423e76842dd3a5e1a21d13793811080d5e7b2896d0c001bd5e97d54",
          "reason": "target_opportunity_momentum score=0.4775 exit_bid=0.3879 exit_distance=7.75% imbalance=0.52 mark_loss=4.51%",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_sweep_003_tp0100_cap05_545953",
          "target_notional": 500.0,
          "timestamp": 1779549880
        }
      }
    ],
    "strategy": "paper_sweep_003_tp0100_cap05_545953"
  }
]
```
