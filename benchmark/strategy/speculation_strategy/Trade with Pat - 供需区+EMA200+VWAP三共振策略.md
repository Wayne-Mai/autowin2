---
strategy: 供需区 + EMA200 + VWAP 三方资金合力策略
trader: Trade with Pat
source_video: https://www.youtube.com/watch?v=xLAn99ghOxs
source_transcript: Trade_with_Pat说这是94%的策略，测他一测！！#priceaction_#聪明钱策略_#daytrading.md
asset_class: mixed
timeframe: intraday
claimed_returns: "为Trade with Pat带来不少收益（视频未单独披露此子策略的具体金额，整套系统总收益>1万美金，第一组3000+，第三组7500）"
claimed_win_rate: <未明确单独披露；总系统94.44%>
claimed_payoff_ratio: "固定比例（视频未规定）"
backtest_period: <未明确>
indicators: [供给需求区, EMA200, VWAP(周)]
tags: [供需, 聪明钱, VWAP, EMA200, 共振]
extracted: 2026-05-26
---

# 供需区 + EMA200 + VWAP 三方资金合力策略 — Trade with Pat

## TL;DR
Trade with Pat 系统的第二组策略：当价格回到供需区时，需求区/EMA200/VWAP 三个关键位置 **尽量重合**——这种"三方资金合力" 大概率会阻止价格继续运行的方向。逻辑是每个指标后面都会有一些资金把它当做入场信号，三方资金的合力大概率能产生停止行为。

## Setup / 形态

### 指标设置
- **EMA200** (前面策略设置过)
  - 长度 200，颜色白色
- **VWAP (Volume Weighted Average Price)** (01:21)
  - 时间周期 = **每周**
  - 颜色 = 紫色
  - 其他选项参考主播设置

### 供需区识别 (与第一组策略相同)
- 跌平涨 / 涨平涨 → 需求区
- 涨平跌 / 跌平跌 → 供给区
- 主观判定为大资金布置订单的位置

## Entry Rules / 入场

### 多头规则 (04:43)
1. 价格回落到 **需求区** 区域时，**EMA200 均线 / VWAP 线 / 需求区** 这三个位置尽量 **重合** (04:48)。
2. 三方资金合力大概率阻止价格继续下行 (04:59)。
3. 可以在K线收盘价入场 (05:03)。

### 空头规则 (05:13)
1. 价格反弹到 **供给区** 区域时，**EMA200 均线 / VWAP 线 / 供给区** 三个位置需要 **重合** (05:18)。
2. 在K线收盘价入场空单 (05:23)。

## Exit & Stop Loss / 出场止损

### 止损
- **多头** (05:05)：设置在 **三个指标的最下沿**；如果没有重合就以 **需求区为主**。
- **空头** (05:25)：设置在 **三个指标的最上沿**；如果没有重合就以 **供给区为主**。

### 止盈
- 固定比例方式（如1:1 / 1:2 等），具体未规定，参考第一组策略的1:2最优结果。

## Risk Management / 仓位
- 视频未单独详述本子策略的仓位规则。

## Examples / 实例
- 视频未给出独立K线实例，主要以概念图说明。

## Caveats / 注意
- "三个位置尽量重合"是关键——三方资金合力才有意义，散开的指标信号说服力低。
- VWAP 设为每周——这意味着重合点在一周内动态变化，需实时观察。
- 与RSI策略可共存——同一价格区如果同时满足RSI+EMA+供需区(策略一) 与 EMA+VWAP+供需区(策略二)，信号更强。

## My Notes
