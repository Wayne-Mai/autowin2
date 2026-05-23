# Polymarket Paper Replay Report

| Strategy | PnL | ROI | Orders | Filled | Partial | Missed | Turnover | Fees | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| paper_target_balanced | 0.0000 | 0.0000% | 0 | 0 | 0 | 0 | 0.0000 | 0.0000 | 0.0000% |
| paper_target_aggressive | -986.6201 | -9.8662% | 3 | 3 | 0 | 0 | 27841.7573 | 692.4755 | -9.8662% |
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
        "asset": "91863162118308663069733924043159186005106558783397508844234610341221325526200",
        "average_price": 0.5114865327925561,
        "fee": 232.03133,
        "filled_notional": 9500.0,
        "liquidity_source": "paper_run",
        "notional": 9500.0,
        "order_id": "target-1779542805-f77d929a-paper_target_aggressive-1",
        "price": 0.5114865327925561,
        "quote_timestamp": 1779542808,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 9500.0,
        "shares": 18573.31403846154,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_target_aggressive",
        "taker": true,
        "timestamp": 1779542808
      },
      {
        "asset": "91863162118308663069733924043159186005106558783397508844234610341221325526200",
        "average_price": 0.5054872490704275,
        "fee": 232.13797,
        "filled_notional": 9388.573419423077,
        "liquidity_source": "paper_run",
        "notional": 9388.573419423077,
        "order_id": "target-1779542805-f77d929a-paper_target_aggressive-2",
        "price": 0.5054872490704275,
        "quote_timestamp": 1779542812,
        "reason": "depth_fill_at_bids_minus_slippage",
        "requested_notional": 9435.243531538463,
        "shares": 18573.31403846154,
        "side": "SELL",
        "status": "FILLED",
        "strategy": "paper_target_aggressive",
        "taker": true,
        "timestamp": 1779542812
      },
      {
        "asset": "90435811253665578014957380826505992530054077692143838383981805324273750424057",
        "average_price": 0.49,
        "fee": 228.30619,
        "filled_notional": 8953.183913451923,
        "liquidity_source": "paper_run",
        "notional": 8953.183913451923,
        "order_id": "target-1779542805-f77d929a-paper_target_aggressive-3",
        "price": 0.49,
        "quote_timestamp": 1779542810,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 8953.183913451923,
        "shares": 18271.803905003926,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "paper_target_aggressive",
        "taker": true,
        "timestamp": 1779542810
      }
    ],
    "metrics": {
      "cash": 242.9140159711551,
      "ending_equity": 9013.379890373039,
      "fees": 692.47549,
      "filled_orders": 3.0,
      "initial_cash": 10000.0,
      "max_drawdown": -0.09866201096269615,
      "missed_orders": 0.0,
      "orders": 3.0,
      "partial_orders": 0.0,
      "pending_orders": 0.0,
      "pnl": -986.6201096269615,
      "roi": -0.09866201096269615,
      "turnover": 27841.757332875
    },
    "orders": [
      {
        "created_at": 1779542808,
        "eligible_at": 1779542808,
        "order_id": "target-1779542805-f77d929a-paper_target_aggressive-1",
        "signal": {
          "asset": "91863162118308663069733924043159186005106558783397508844234610341221325526200",
          "condition_id": "0xbb57ccf5853a85487bc3d83d04d669310d28c6c810758953b9d9b91d1aee89d2",
          "reason": "target_opportunity_momentum score=0.4658 exit_bid=0.5899 imbalance=0.74",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_aggressive",
          "target_notional": 9500.0,
          "timestamp": 1779542808
        }
      },
      {
        "created_at": 1779542812,
        "eligible_at": 1779542812,
        "order_id": "target-1779542805-f77d929a-paper_target_aggressive-2",
        "signal": {
          "asset": "91863162118308663069733924043159186005106558783397508844234610341221325526200",
          "condition_id": "0xbb57ccf5853a85487bc3d83d04d669310d28c6c810758953b9d9b91d1aee89d2",
          "reason": "stop_loss",
          "side": "SELL",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_aggressive",
          "target_notional": 9435.243531538463,
          "timestamp": 1779542812
        }
      },
      {
        "created_at": 1779542810,
        "eligible_at": 1779542810,
        "order_id": "target-1779542805-f77d929a-paper_target_aggressive-3",
        "signal": {
          "asset": "90435811253665578014957380826505992530054077692143838383981805324273750424057",
          "condition_id": "0x32b09f6390252b37d674501527e709016d55581b2c1e544bd4b8167f5f732f4c",
          "reason": "target_opportunity_momentum score=0.3605 exit_bid=0.6007 imbalance=0.12",
          "side": "BUY",
          "source_tx_hashes": [],
          "source_wallets": [],
          "strategy": "paper_target_aggressive",
          "target_notional": 8953.183913451923,
          "timestamp": 1779542810
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
