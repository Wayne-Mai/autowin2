---
strategy: 订单块 + Inevitrade Pro 双背离策略（可叠加 EMA200 趋势过滤）
trader: 频道编辑
source_video: https://www.youtube.com/watch?v=lIB7GiaEhXU
source_transcript: 【推荐必看】订单块策略真是苍蓝猛兽，两套顶级聪明钱策略，不好用你给我一个大笔豆_#smartmoney_#daytrading_#reversal_signals.md
asset_class: crypto
timeframe: intraday
claimed_returns: 未提及
claimed_win_rate: 未提及
claimed_payoff_ratio: 未提及
backtest_period: 建议至少回测 500 次以上
indicators: [Smart Money Concepts (LUX), Internal Order Blocks, Inevitrade Pro, EMA200]
tags: [聪明钱, 订单块, 背离, EMA, 日内交易]
extracted: 2026-05-26
---

# 订单块 + Inevitrade Pro 双背离策略 — Speculation Lab

## TL;DR
第二种聪明钱策略：用 Smart Money Concepts 的 Order Blocks 标注关键区域，再用 Inevitrade Pro 的超买超卖 + 价格-指标背离作为反转信号。可叠加 4 倍周期的 EMA200 作为大趋势过滤器，以及与 BTC 的强弱比较来选择山寨币方向。

## Setup / 形态
- 时间周期：示例 1 小时图，可灵活变更
- 指标 1：Smart Money Concepts (LUX) — Internal Order Blocks
- 指标 2：Inevitrade Pro — 只看下面的灰色区域（超买区 >70，超卖区 <30）
  - 当 Inevitrade 线 >70 或 <30 时，会显示红/绿色竖条
- 指标 3（可选）：EMA200，时间周期最好是当前周期的 4 倍（如当前 1H，则 EMA200 用 4H）

## Entry Rules / 入场
**多头规则（03:11–03:50）**
1. 价格回落到订单块区域
2. Inevitrade 指标的**两个波谷与价格走势形成底背离**
3. 条件满足后，这根 K 线的收盘价 = 入场位置

**空头规则（03:52–04:10）**
1. 价格反弹到订单块区域
2. Inevitrade 指标的**两个波峰与价格走势形成顶背离**
3. 在这根 K 线的收盘价入场空单

**叠加 EMA200 过滤（04:10–04:43）**
- EMA200 时间周期 = 当前周期 × 4（如 1H 图叠加 4H EMA200）
- 价格在 EMA200 上方 → 只参考多头规则
- 价格在 EMA200 下方 → 只参考空头规则
- 减少交易频率但过滤掉大量逆势亏损信号

**与 BTC 强弱比较（04:44–05:16）**
- 在 Inevitrade 的 Compare To 输入框，选择常用交易所的 BTC 数据
- 这条线表示当前山寨币的走势比 BTC 强还是弱
- 做多山寨币：等比 BTC 强势的信号
- 做空山寨币：等比 BTC 弱势的信号

## Exit & Stop Loss / 出场止损
**多头**：
- 止损：订单块下方 或 前期波段低点附近
- 止盈：固定比例 或 分批止盈

**空头**：
- 止损：订单块上方 或 前期波段高点附近
- 止盈：固定比例 或 分批止盈

## Risk Management / 仓位
- 视频未提供具体仓位公式
- 强烈建议在所做品种和周期上**连续回测 500 次以上**

## Examples / 实例
- 视频以 1H 图 + 4H EMA200 为例
- 山寨币时强烈建议看 BTC 强弱对比

## Caveats / 注意
- 必须等关键 K 线收盘
- 两个波峰/波谷的背离 = 必须 2 个明确的极值点
- 加 EMA200 减少交易频率，但显著提高质量
- 节目仅供娱乐，无投资建议

## My Notes

