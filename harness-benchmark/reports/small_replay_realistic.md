# Polymarket Paper Replay Report

| Strategy | PnL | ROI | Orders | Filled | Partial | Missed | Turnover | Fees | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| no_trade | 0.0000 | 0.0000% | 0 | 0 | 0 | 0 | 0.0000 | 0.0000 | 0.0000% |
| random_same_turnover | 0.0000 | 0.0000% | 2 | 0 | 0 | 2 | 0.0000 | 0.0000 | 0.0000% |
| single_trader_mirror | 8.6725 | 0.0867% | 2 | 2 | 0 | 0 | 61.0000 | 1.3275 | -0.0250% |
| consensus_mirror | 11.3000 | 0.1130% | 1 | 1 | 0 | 0 | 50.0000 | 1.2000 | -0.0312% |
| specialist_mirror | 12.4018 | 0.1240% | 4 | 4 | 0 | 0 | 92.0000 | 2.1815 | -0.0381% |

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
      "pnl": 0.0,
      "roi": 0.0,
      "turnover": 0
    },
    "orders": [],
    "strategy": "no_trade"
  },
  {
    "fills": [
      {
        "asset": "YES-C1",
        "average_price": 0.0,
        "fee": 0.0,
        "filled_notional": 0.0,
        "liquidity_source": "fixture",
        "notional": 0.0,
        "order_id": "random_same_turnover-1",
        "price": 0.0,
        "quote_timestamp": 180,
        "reason": "no_inventory_no_shorting",
        "requested_notional": 40.0,
        "shares": 0.0,
        "side": "SELL",
        "status": "MISSED",
        "strategy": "random_same_turnover",
        "taker": true,
        "timestamp": 180
      },
      {
        "asset": "NO-C2",
        "average_price": 0.0,
        "fee": 0.0,
        "filled_notional": 0.0,
        "liquidity_source": "fixture",
        "notional": 0.0,
        "order_id": "random_same_turnover-8",
        "price": 0.0,
        "quote_timestamp": 310,
        "reason": "no_inventory_no_shorting",
        "requested_notional": 10.0,
        "shares": 0.0,
        "side": "SELL",
        "status": "MISSED",
        "strategy": "random_same_turnover",
        "taker": true,
        "timestamp": 310
      }
    ],
    "metrics": {
      "cash": 10000.0,
      "ending_equity": 10000.0,
      "fees": 0,
      "filled_orders": 0.0,
      "initial_cash": 10000.0,
      "max_drawdown": 0.0,
      "missed_orders": 2.0,
      "orders": 2.0,
      "partial_orders": 0.0,
      "pnl": 0.0,
      "roi": 0.0,
      "turnover": 0
    },
    "orders": [
      {
        "created_at": 100,
        "eligible_at": 160,
        "order_id": "random_same_turnover-1",
        "signal": {
          "asset": "YES-C1",
          "condition_id": "C1",
          "reason": "deterministic random same-turnover control",
          "side": "SELL",
          "source_tx_hashes": [
            "tx-aaa-100"
          ],
          "source_wallets": [
            "0xaaa"
          ],
          "strategy": "random_same_turnover",
          "target_notional": 40.0,
          "timestamp": 100
        }
      },
      {
        "created_at": 240,
        "eligible_at": 300,
        "order_id": "random_same_turnover-8",
        "signal": {
          "asset": "NO-C2",
          "condition_id": "C2",
          "reason": "deterministic random same-turnover control",
          "side": "SELL",
          "source_tx_hashes": [
            "tx-ccc-240"
          ],
          "source_wallets": [
            "0xccc"
          ],
          "strategy": "random_same_turnover",
          "target_notional": 10.0,
          "timestamp": 240
        }
      }
    ],
    "strategy": "random_same_turnover"
  },
  {
    "fills": [
      {
        "asset": "YES-C1",
        "average_price": 0.52,
        "fee": 0.96,
        "filled_notional": 40.0,
        "liquidity_source": "fixture",
        "notional": 40.0,
        "order_id": "single_trader_mirror-2",
        "price": 0.52,
        "quote_timestamp": 180,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 40.0,
        "shares": 76.92307692307692,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "single_trader_mirror",
        "taker": true,
        "timestamp": 180
      },
      {
        "asset": "YES-C1",
        "average_price": 0.65,
        "fee": 0.3675,
        "filled_notional": 21.0,
        "liquidity_source": "fixture",
        "notional": 21.0,
        "order_id": "single_trader_mirror-6",
        "price": 0.65,
        "quote_timestamp": 300,
        "reason": "depth_fill_at_bids_minus_slippage",
        "requested_notional": 21.0,
        "shares": 32.30769230769231,
        "side": "SELL",
        "status": "FILLED",
        "strategy": "single_trader_mirror",
        "taker": true,
        "timestamp": 300
      }
    ],
    "metrics": {
      "cash": 9979.6725,
      "ending_equity": 10008.6725,
      "fees": 1.3275,
      "filled_orders": 2.0,
      "initial_cash": 10000.0,
      "max_drawdown": -0.00024984615384601055,
      "missed_orders": 0.0,
      "orders": 2.0,
      "partial_orders": 0.0,
      "pnl": 8.672500000000582,
      "roi": 0.0008672500000000582,
      "turnover": 61.0
    },
    "orders": [
      {
        "created_at": 100,
        "eligible_at": 160,
        "order_id": "single_trader_mirror-2",
        "signal": {
          "asset": "YES-C1",
          "condition_id": "C1",
          "reason": "mirror selected public trader trade",
          "side": "BUY",
          "source_tx_hashes": [
            "tx-aaa-100"
          ],
          "source_wallets": [
            "0xaaa"
          ],
          "strategy": "single_trader_mirror",
          "target_notional": 40.0,
          "timestamp": 100
        }
      },
      {
        "created_at": 230,
        "eligible_at": 290,
        "order_id": "single_trader_mirror-6",
        "signal": {
          "asset": "YES-C1",
          "condition_id": "C1",
          "reason": "mirror selected public trader trade",
          "side": "SELL",
          "source_tx_hashes": [
            "tx-aaa-230"
          ],
          "source_wallets": [
            "0xaaa"
          ],
          "strategy": "single_trader_mirror",
          "target_notional": 21.0,
          "timestamp": 230
        }
      }
    ],
    "strategy": "single_trader_mirror"
  },
  {
    "fills": [
      {
        "asset": "YES-C1",
        "average_price": 0.52,
        "fee": 1.2,
        "filled_notional": 50.0,
        "liquidity_source": "fixture",
        "notional": 50.0,
        "order_id": "consensus_mirror-4",
        "price": 0.52,
        "quote_timestamp": 180,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 50.0,
        "shares": 96.15384615384615,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "consensus_mirror",
        "taker": true,
        "timestamp": 180
      }
    ],
    "metrics": {
      "cash": 9948.8,
      "ending_equity": 10011.3,
      "fees": 1.2,
      "filled_orders": 1.0,
      "initial_cash": 10000.0,
      "max_drawdown": -0.0003123076923076951,
      "missed_orders": 0.0,
      "orders": 1.0,
      "partial_orders": 0.0,
      "pnl": 11.299999999999272,
      "roi": 0.0011299999999999273,
      "turnover": 50.0
    },
    "orders": [
      {
        "created_at": 120,
        "eligible_at": 180,
        "order_id": "consensus_mirror-4",
        "signal": {
          "asset": "YES-C1",
          "condition_id": "C1",
          "reason": "2 selected traders same-direction within 3600s",
          "side": "BUY",
          "source_tx_hashes": [
            "tx-aaa-100",
            "tx-bbb-120"
          ],
          "source_wallets": [
            "0xaaa",
            "0xbbb"
          ],
          "strategy": "consensus_mirror",
          "target_notional": 50.0,
          "timestamp": 120
        }
      }
    ],
    "strategy": "consensus_mirror"
  },
  {
    "fills": [
      {
        "asset": "YES-C1",
        "average_price": 0.52,
        "fee": 0.96,
        "filled_notional": 40.0,
        "liquidity_source": "fixture",
        "notional": 40.0,
        "order_id": "specialist_mirror-3",
        "price": 0.52,
        "quote_timestamp": 180,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 40.0,
        "shares": 76.92307692307692,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "specialist_mirror",
        "taker": true,
        "timestamp": 180
      },
      {
        "asset": "YES-C1",
        "average_price": 0.52,
        "fee": 0.504,
        "filled_notional": 20.999999999999996,
        "liquidity_source": "fixture",
        "notional": 20.999999999999996,
        "order_id": "specialist_mirror-5",
        "price": 0.52,
        "quote_timestamp": 180,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 21.0,
        "shares": 40.38461538461538,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "specialist_mirror",
        "taker": true,
        "timestamp": 180
      },
      {
        "asset": "YES-C1",
        "average_price": 0.65,
        "fee": 0.3675,
        "filled_notional": 21.0,
        "liquidity_source": "fixture",
        "notional": 21.0,
        "order_id": "specialist_mirror-7",
        "price": 0.65,
        "quote_timestamp": 300,
        "reason": "depth_fill_at_bids_minus_slippage",
        "requested_notional": 21.0,
        "shares": 32.30769230769231,
        "side": "SELL",
        "status": "FILLED",
        "strategy": "specialist_mirror",
        "taker": true,
        "timestamp": 300
      },
      {
        "asset": "NO-C2",
        "average_price": 0.3,
        "fee": 0.35,
        "filled_notional": 10.0,
        "liquidity_source": "fixture",
        "notional": 10.0,
        "order_id": "specialist_mirror-9",
        "price": 0.3,
        "quote_timestamp": 310,
        "reason": "depth_fill_at_asks_plus_slippage",
        "requested_notional": 10.0,
        "shares": 33.333333333333336,
        "side": "BUY",
        "status": "FILLED",
        "strategy": "specialist_mirror",
        "taker": true,
        "timestamp": 310
      }
    ],
    "metrics": {
      "cash": 9947.8185,
      "ending_equity": 10012.401833333333,
      "fees": 2.1814999999999998,
      "filled_orders": 4.0,
      "initial_cash": 10000.0,
      "max_drawdown": -0.0003810153846154208,
      "missed_orders": 0.0,
      "orders": 4.0,
      "partial_orders": 0.0,
      "pnl": 12.401833333333343,
      "roi": 0.0012401833333333342,
      "turnover": 92.0
    },
    "orders": [
      {
        "created_at": 100,
        "eligible_at": 160,
        "order_id": "specialist_mirror-3",
        "signal": {
          "asset": "YES-C1",
          "condition_id": "C1",
          "reason": "mirror selected trader inside specialist category politics",
          "side": "BUY",
          "source_tx_hashes": [
            "tx-aaa-100"
          ],
          "source_wallets": [
            "0xaaa"
          ],
          "strategy": "specialist_mirror",
          "target_notional": 40.0,
          "timestamp": 100
        }
      },
      {
        "created_at": 120,
        "eligible_at": 180,
        "order_id": "specialist_mirror-5",
        "signal": {
          "asset": "YES-C1",
          "condition_id": "C1",
          "reason": "mirror selected trader inside specialist category politics",
          "side": "BUY",
          "source_tx_hashes": [
            "tx-bbb-120"
          ],
          "source_wallets": [
            "0xbbb"
          ],
          "strategy": "specialist_mirror",
          "target_notional": 21.0,
          "timestamp": 120
        }
      },
      {
        "created_at": 230,
        "eligible_at": 290,
        "order_id": "specialist_mirror-7",
        "signal": {
          "asset": "YES-C1",
          "condition_id": "C1",
          "reason": "mirror selected trader inside specialist category politics",
          "side": "SELL",
          "source_tx_hashes": [
            "tx-aaa-230"
          ],
          "source_wallets": [
            "0xaaa"
          ],
          "strategy": "specialist_mirror",
          "target_notional": 21.0,
          "timestamp": 230
        }
      },
      {
        "created_at": 240,
        "eligible_at": 300,
        "order_id": "specialist_mirror-9",
        "signal": {
          "asset": "NO-C2",
          "condition_id": "C2",
          "reason": "mirror selected trader inside specialist category sports",
          "side": "BUY",
          "source_tx_hashes": [
            "tx-ccc-240"
          ],
          "source_wallets": [
            "0xccc"
          ],
          "strategy": "specialist_mirror",
          "target_notional": 10.0,
          "timestamp": 240
        }
      }
    ],
    "strategy": "specialist_mirror"
  }
]
```
