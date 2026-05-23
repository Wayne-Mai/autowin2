# Polymarket Paper Replay Report

| Strategy | PnL | ROI | Orders | Filled | Partial | Missed | Turnover | Fees | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| paper_sweep_001_tp0100_cap10_545953 | -45.9270 | -0.4593% | 1 | 1 | 0 | 0 | 1000.0000 | 18.9000 | -0.4593% |
| paper_sweep_002_tp0100_cap20_526200 | -53.0293 | -0.5303% | 1 | 1 | 0 | 0 | 2000.0000 | 49.1000 | -0.5303% |

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
        "order_id": "goal-sweep-unique-probe-paper_sweep_001_tp0100_cap10_545953-1",
        "price": 0.37,
        "quote_timestamp": 1779550067,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 1000.0,
        "shares": 2702.702702702703,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_sweep_001_tp0100_cap10_545953",
        "taker": true,
        "timestamp": 1779550067
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
        "created_at": 1779550067,
        "eligible_at": 1779550067,
        "order_id": "goal-sweep-unique-probe-paper_sweep_001_tp0100_cap10_545953-1",
        "signal": {
          "asset": "44914465637297319816681463234953032477919413063019359633128421605039733545953",
          "condition_id": "0x22e7b5e35423e76842dd3a5e1a21d13793811080d5e7b2896d0c001bd5e97d54",
          "reason": "target_opportunity_momentum score=0.4775 exit_bid=0.3879 exit_distance=7.75% imbalance=0.52 mark_loss=4.51%",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_sweep_001_tp0100_cap10_545953",
          "target_notional": 1000.0,
          "timestamp": 1779550067
        }
      }
    ],
    "strategy": "paper_sweep_001_tp0100_cap10_545953"
  },
  {
    "fills": [
      {
        "asset": "91863162118308663069733924043159186005106558783397508844234610341221325526200",
        "average_price": 0.509,
        "fee": 49.1,
        "filled_notional": 2000.0,
        "liquidity_source": "paper_run",
        "notional": 2000.0,
        "order_id": "goal-sweep-unique-probe-paper_sweep_002_tp0100_cap20_526200-2",
        "price": 0.509,
        "quote_timestamp": 1779550060,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 2000.0,
        "shares": 3929.2730844793714,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_sweep_002_tp0100_cap20_526200",
        "taker": true,
        "timestamp": 1779550060
      }
    ],
    "metrics": {
      "cash": 7950.9,
      "ending_equity": 9946.97072691552,
      "fees": 49.1,
      "filled_orders": 1.0,
      "initial_cash": 10000.0,
      "max_drawdown": -0.005302927308447942,
      "missed_orders": 0.0,
      "orders": 1.0,
      "partial_orders": 0.0,
      "pending_orders": 0.0,
      "pnl": -53.02927308447943,
      "roi": -0.005302927308447942,
      "turnover": 2000.0
    },
    "orders": [
      {
        "created_at": 1779550060,
        "eligible_at": 1779550060,
        "order_id": "goal-sweep-unique-probe-paper_sweep_002_tp0100_cap20_526200-2",
        "signal": {
          "asset": "91863162118308663069733924043159186005106558783397508844234610341221325526200",
          "condition_id": "0xbb57ccf5853a85487bc3d83d04d669310d28c6c810758953b9d9b91d1aee89d2",
          "reason": "target_opportunity_momentum score=0.4343 exit_bid=0.5391 exit_distance=6.13% imbalance=0.75 mark_loss=2.59%",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_sweep_002_tp0100_cap20_526200",
          "target_notional": 2000.0,
          "timestamp": 1779550060
        }
      }
    ],
    "strategy": "paper_sweep_002_tp0100_cap20_526200"
  }
]
```
