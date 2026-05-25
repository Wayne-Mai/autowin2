# Polymarket Strategy V1 Final Report

This report summarizes the strategy set selected from the online virtual-paper benchmark. It is paper-only research output: live public Polymarket data was used as input, while all orders, fills, queue behavior, latency, fees, and PnL were simulated locally.

## Verification Result

Final verifier line:

```text
PASS run_id=polymarket-online-6h-20260524T160400Z mode=online_target runtime=21652s required_runtime=21600s passed_strategies=72/272 required_strategies=2 passed_families=2/2 target_roi=10.0000% flat_required=True reason=online_goal_reached
```

Acceptance interpretation:

- Online runtime: 21652 seconds, above the 21600 second requirement.
- Target ROI: at least 10 percent final ROI.
- Flat requirement: all selected passing agents ended flat.
- Strategy count: 72 passing agents out of 272 tested agents.
- Family count: 2 passing strategy families, satisfying the diversity requirement.

## Final Selected Strategy Families

Only the following two families are selected for strategy-v1:

| Family | Passing agents | Final ROI range | Aggregate simulated PnL | Orders | Filled/partial fills |
| --- | ---: | ---: | ---: | ---: | ---: |
| `crypto_interval_anchor` | 24 | 12.8264% to 17.3576% | 36147.10 | 284 | 320 |
| `crypto_interval_book_skew` | 48 | 11.7653% to 14.5596% | 67135.99 | 561 | 822 |

The dashboard may show negative PnL for other agents because it displays the whole 272-agent sweep. Those losing agents are not part of the selected final strategy set.

## Strategy Logic

### 1. `crypto_interval_anchor`

The anchor family trades Polymarket crypto interval markets by comparing current spot movement against the interval anchor/open reference.

Core idea:

```text
if current_spot is meaningfully above the interval anchor:
    consider UP/YES
if current_spot is meaningfully below the interval anchor:
    consider DOWN/NO
otherwise:
    skip
```

The selected passing band was concentrated in lower anchor-move thresholds:

```text
min_anchor_move_pct: 0.0002 or 0.0005
capital_fraction: 0.35 or 0.60
min_net_settlement_roi: 0.02 or 0.08
max_anchor_lag_seconds: 45, 150, or 180
take_profit_pct: 0.025 to 0.04
stop_loss_pct: 0.12
```

Interpretation: the profitable anchor variants were not waiting for very large spot moves. They entered when the direction was already visible but the market had not fully repriced the aligned side.

### 2. `crypto_interval_book_skew`

The book-skew family trades the same crypto interval market class, but uses orderbook pressure as the confirmation signal.

Core idea:

```text
score candidate side by bid support, touch depth, price quality, and settlement edge
enter only when depth/skew and price filters agree
skip thin, expensive, stale, or low-edge books
```

The selected passing set covered 48 variants across these parameter ranges:

```text
min_bid_price: 0.50, 0.58, 0.65, or 0.72
max_ask_price: 0.84 or 0.90
min_net_settlement_roi: 0.02, 0.06, or 0.12
max_seconds_to_close: 180, 240, or 300
capital_fraction: 0.55 for lower min_bid bands, 0.70 for higher min_bid bands
take_profit_pct: 0.015, 0.02, or 0.03
stop_loss_pct: 0.35
```

Interpretation: book-skew was more robust than maker/spread variants in the 6 hour online paper run. It produced fewer extreme losses because it filtered on book pressure plus settlement edge, and it flattened after reaching target.

## Top Passing Agents

| Strategy | Family | Final ROI | Simulated PnL | Orders | Filled/partial | Flat |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `paper_target_crypto_interval_anchor_grid_01` | anchor | 17.3576% | 1735.76 | 12 | 13 | yes |
| `paper_target_crypto_interval_anchor_grid_04` | anchor | 17.3576% | 1735.76 | 12 | 13 | yes |
| `paper_target_crypto_interval_anchor_grid_13` | anchor | 17.3305% | 1733.05 | 9 | 11 | yes |
| `paper_target_crypto_interval_anchor_grid_16` | anchor | 17.3305% | 1733.05 | 9 | 11 | yes |
| `paper_target_crypto_interval_anchor_grid_02` | anchor | 17.1923% | 1719.23 | 14 | 15 | yes |
| `paper_target_crypto_interval_anchor_grid_03` | anchor | 17.1923% | 1719.23 | 14 | 15 | yes |
| `paper_target_crypto_interval_anchor_grid_05` | anchor | 17.1923% | 1719.23 | 14 | 15 | yes |
| `paper_target_crypto_interval_anchor_grid_06` | anchor | 17.1923% | 1719.23 | 14 | 15 | yes |
| `paper_target_crypto_interval_anchor_grid_14` | anchor | 17.1651% | 1716.51 | 11 | 13 | yes |
| `paper_target_crypto_interval_anchor_grid_15` | anchor | 17.1651% | 1716.51 | 11 | 13 | yes |
| `paper_target_crypto_interval_book_skew_grid_10` | book skew | 14.5596% | 1455.96 | 10 | 16 | yes |
| `paper_target_crypto_interval_book_skew_grid_13` | book skew | 14.5596% | 1455.96 | 10 | 16 | yes |
| `paper_target_crypto_interval_book_skew_grid_28` | book skew | 14.5522% | 1455.22 | 9 | 14 | yes |
| `paper_target_crypto_interval_book_skew_grid_31` | book skew | 14.5522% | 1455.22 | 9 | 14 | yes |
| `paper_target_crypto_interval_book_skew_grid_46` | book skew | 14.5522% | 1455.22 | 9 | 14 | yes |
| `paper_target_crypto_interval_book_skew_grid_49` | book skew | 14.5522% | 1455.22 | 9 | 14 | yes |

## Full Selected Set

### Anchor Family

Selected anchor variants:

```text
paper_target_crypto_interval_anchor_grid_01
paper_target_crypto_interval_anchor_grid_02
paper_target_crypto_interval_anchor_grid_03
paper_target_crypto_interval_anchor_grid_04
paper_target_crypto_interval_anchor_grid_05
paper_target_crypto_interval_anchor_grid_06
paper_target_crypto_interval_anchor_grid_07
paper_target_crypto_interval_anchor_grid_08
paper_target_crypto_interval_anchor_grid_09
paper_target_crypto_interval_anchor_grid_10
paper_target_crypto_interval_anchor_grid_11
paper_target_crypto_interval_anchor_grid_12
paper_target_crypto_interval_anchor_grid_13
paper_target_crypto_interval_anchor_grid_14
paper_target_crypto_interval_anchor_grid_15
paper_target_crypto_interval_anchor_grid_16
paper_target_crypto_interval_anchor_grid_17
paper_target_crypto_interval_anchor_grid_18
paper_target_crypto_interval_anchor_grid_19
paper_target_crypto_interval_anchor_grid_20
paper_target_crypto_interval_anchor_grid_21
paper_target_crypto_interval_anchor_grid_22
paper_target_crypto_interval_anchor_grid_23
paper_target_crypto_interval_anchor_grid_24
```

### Book-Skew Family

Selected book-skew variants:

```text
paper_target_crypto_interval_book_skew_grid_01
paper_target_crypto_interval_book_skew_grid_02
paper_target_crypto_interval_book_skew_grid_04
paper_target_crypto_interval_book_skew_grid_05
paper_target_crypto_interval_book_skew_grid_07
paper_target_crypto_interval_book_skew_grid_08
paper_target_crypto_interval_book_skew_grid_10
paper_target_crypto_interval_book_skew_grid_11
paper_target_crypto_interval_book_skew_grid_13
paper_target_crypto_interval_book_skew_grid_14
paper_target_crypto_interval_book_skew_grid_16
paper_target_crypto_interval_book_skew_grid_17
paper_target_crypto_interval_book_skew_grid_19
paper_target_crypto_interval_book_skew_grid_21
paper_target_crypto_interval_book_skew_grid_22
paper_target_crypto_interval_book_skew_grid_24
paper_target_crypto_interval_book_skew_grid_25
paper_target_crypto_interval_book_skew_grid_27
paper_target_crypto_interval_book_skew_grid_28
paper_target_crypto_interval_book_skew_grid_30
paper_target_crypto_interval_book_skew_grid_31
paper_target_crypto_interval_book_skew_grid_33
paper_target_crypto_interval_book_skew_grid_34
paper_target_crypto_interval_book_skew_grid_36
paper_target_crypto_interval_book_skew_grid_37
paper_target_crypto_interval_book_skew_grid_40
paper_target_crypto_interval_book_skew_grid_43
paper_target_crypto_interval_book_skew_grid_46
paper_target_crypto_interval_book_skew_grid_49
paper_target_crypto_interval_book_skew_grid_52
paper_target_crypto_interval_book_skew_grid_55
paper_target_crypto_interval_book_skew_grid_56
paper_target_crypto_interval_book_skew_grid_57
paper_target_crypto_interval_book_skew_grid_58
paper_target_crypto_interval_book_skew_grid_59
paper_target_crypto_interval_book_skew_grid_60
paper_target_crypto_interval_book_skew_grid_61
paper_target_crypto_interval_book_skew_grid_62
paper_target_crypto_interval_book_skew_grid_63
paper_target_crypto_interval_book_skew_grid_64
paper_target_crypto_interval_book_skew_grid_65
paper_target_crypto_interval_book_skew_grid_66
paper_target_crypto_interval_book_skew_grid_67
paper_target_crypto_interval_book_skew_grid_68
paper_target_crypto_interval_book_skew_grid_69
paper_target_crypto_interval_book_skew_grid_70
paper_target_crypto_interval_book_skew_grid_71
paper_target_crypto_interval_book_skew_grid_72
```

## Rejected Families

The final selected strategy-v1 excludes these families even if some individual variants had positive PnL:

- `spread_capture_maker`
- `maker_rebate_rotation`
- `outcome_basket_arb`
- `crypto_directional`
- `crypto_interval_close_edge`
- `momentum_scalper`

Reason: they either did not reach 10 percent final ROI, did not finish flat, were less robust, or introduced large negative-PnL tails in the full sweep. The selected set keeps only the families that met the final verifier requirements.

## Operational Rule

For future benchmark runs, treat strategy-v1 as:

```text
crypto_interval_anchor + crypto_interval_book_skew
paper-only
online data input
realistic virtual execution
target-hit flattening required
```

Do not evaluate the strategy using optimistic instant fills. Do not include real wallet or live order placement logic.
