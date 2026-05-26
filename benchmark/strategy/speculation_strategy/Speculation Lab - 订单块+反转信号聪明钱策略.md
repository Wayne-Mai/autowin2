---
strategy: 订单块 + Reversal Signals 聪明钱策略
trader: 频道编辑
source_video: https://www.youtube.com/watch?v=lIB7GiaEhXU
source_transcript: 【推荐必看】订单块策略真是苍蓝猛兽，两套顶级聪明钱策略，不好用你给我一个大笔豆_#smartmoney_#daytrading_#reversal_signals.md
asset_class: crypto
timeframe: intraday
claimed_returns: 未提及
claimed_win_rate: 未提及
claimed_payoff_ratio: 未提及
backtest_period: 建议至少回测 500 次以上
indicators: [Smart Money Concepts (LUX), Internal Order Blocks, Reversal Signals, EMA200]
tags: [聪明钱, 订单块, 反转信号, 日内交易, SMC]
extracted: 2026-05-26
---

# 订单块 + Reversal Signals 聪明钱策略 — Speculation Lab

## TL;DR
两个 TradingView 免费指标组合的日内交易策略：用 Smart Money Concepts 自动标注的 Internal Order Blocks 作为关键位置，Reversal Signals 出现的看涨/看跌信号作为入场触发。订单块视作广义供需区，是大资金集团参与的价格区域。

## Setup / 形态
- 交易品种示例：BTC/USD
- 时间周期：15 分钟图（日内）
- 指标 1：Smart Money Concepts (LUX) — 仅启用 Internal Order Blocks 功能
- 指标 2：Reversal Signals — 只留下看涨信号和看跌信号两个功能（其他可关闭）

## Entry Rules / 入场
**多头规则（02:06–02:30）**
1. 价格回落到订单块区域
2. Reversal Signals 指标出现**绿色买入信号**
3. 两个条件全部满足 → 买入信号对应的 K 线即为关键 K 线
4. 在关键 K 线的**收盘价**入场多单

**空头规则（02:30–02:55）**
1. 价格反弹到订单块区域
2. Reversal Signals 指标出现**红色卖出信号**
3. 两个条件全部满足 → 卖出信号对应的 K 线即为关键 K 线
4. 在关键 K 线的**收盘价**入场空单

## Exit & Stop Loss / 出场止损
**多头**：
- 止损：订单块下方 或 前期波段低点附近
- 止盈：固定比例 或 分批止盈

**空头**：
- 止损：订单块上方 或 前期波段高点附近
- 止盈：固定比例 或 分批止盈

## Risk Management / 仓位
- 视频未提供具体仓位公式
- 强烈建议至少在所做品种和周期上**连续回测 500 次以上**（05:24–05:31）

## Examples / 实例
- 示例品种：BTC/USD
- 视频提到的指标作者：LuxAlgo（Lux）近期发布的非重绘反转指标

## Caveats / 注意
- 必须等关键 K 线收盘后再入场，不能盘中预判
- 订单块 = 广义供需区，可作为支撑阻力，也能找潜在止盈止损位
- 至少回测 500 次以上才能对策略长期运行有把握
- 节目仅供娱乐，无投资建议

## My Notes

