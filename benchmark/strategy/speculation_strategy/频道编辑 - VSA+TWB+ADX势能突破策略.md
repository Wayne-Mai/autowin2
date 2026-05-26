---
strategy: VSA + TWB + ADX 势能突破策略
trader: 频道编辑
source_video: https://www.youtube.com/watch?v=Yd2Kndbi3Ec
source_transcript: 【吐血推荐！】Tradingview上胜率最开门指标，单指标胜率超66%，三大策略组合全部泄漏，必看！！#crypto_#交易策略_#tradingviewbestindicators.md
asset_class: mixed
timeframe: intraday
claimed_returns: <未明确>
claimed_win_rate: "VSA单指标胜率超过66%（基础参考）"
claimed_payoff_ratio: "分批止盈"
backtest_period: <未明确>
indicators: [Volume Spread for VSA, Trendlines with Breaks (TWB), ADX and DI]
tags: [价格行为, 突破, 趋势线, VSA, ADX, 反转/反弹]
extracted: 2026-05-26
---

# VSA + TWB + ADX 势能突破策略 — 频道编辑

## TL;DR
"结合势能指标的突破策略"——用 Trendlines with Breaks (TWB) 自动标记短期顶部/底部的上下轨；当 K 线触轨后未能突破收盘 + 对应量能柱呈现红色 (VSA超高量) + ADX 处于30下方(趋势较弱不易延续) → 三共振反向入场。

## Setup / 形态

### 指标设置
- **Volume Spread for VSA** (与VSA单指标策略相同设置)
- **Trendlines with Breaks (TWB)** (04:20)
  - 长度参数 = **24**
  - 斜率 = **0**
  - 上轨和下轨颜色 = **黄色**
  - 其他用不到的功能勾掉
- **ADX and DI** (04:39)
  - 勾掉 DI+ 和 DI-，只留 ADX线
  - 参数等级设置成 **30**
  - 无论上升还是下降趋势，ADX 处在 30 下方即表明当前趋势较弱、大概率不会延续 (04:51)

## Entry Rules / 入场

### 空头规则 (05:00) — 三个条件全部满足
1. K线接触 **TWB 上轨线后，收盘价处在上轨线下方** (05:02)。
2. 阳K线对应的 **量能柱呈现红色** (VSA超高量) (05:08)。
3. **ADX 线处在 30 下方** (05:11)。
4. 三条件满足 → 这根K线即关键K线，收盘价入场。

### 多头规则 (05:30) — 三个条件全部满足
1. K线接触 **TWB 下轨线后，收盘价处在下轨线上方** (05:30)。
2. 阴K线对应的 **量能柱呈现红色** (VSA超高量) (05:37)。
3. **ADX 线处在 30 下方** (05:40)。
4. 三条件满足 → 关键K线收盘价入场。

## Exit & Stop Loss / 出场止损

### 止损
- **空头** (05:23)：近期波段高点附近。
- **多头** (05:51)：近期波段低点附近。

### 止盈
- 分批止盈方式。

## Risk Management / 仓位
- 视频未明确给定仓位规则。

## Examples / 实例
- 视频未给具体K线实例。

## Caveats / 注意
- 这是"假突破回归"逻辑——K线触轨后未能突破收盘 + 高量出货 + ADX弱趋势→大概率回归区间。
- ADX>30 时不入场（趋势强劲、突破有效概率高，不适合反转交易）。
- 量能柱必须为红色（VSA超高量），普通量能柱不算共振。
- 与单纯 VSA 左侧交易相比，加入 TWB+ADX 过滤更稳健。

## My Notes
