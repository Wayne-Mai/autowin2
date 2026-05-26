---
strategy: ATR (Average True Range) 止损策略
trader: 频道编辑
source_video: https://www.youtube.com/watch?v=--zG77QC4K0
source_transcript: ATR指标就是交易金矿，地球上最有用的指标#交易系统_#指标_#atr.md
asset_class: mixed
timeframe: mixed
claimed_returns: 案例盈亏比超过3:1
claimed_win_rate: 未给出
claimed_payoff_ratio: 案例展示3:1+
backtest_period: 未给出
indicators: [ATR, Vegas Tunnel, MACD]
tags: [ATR, 止损, indicator-review, 波动率, BTC]
extracted: 2026-05-26
---

# ATR 指标止损策略 — 频道编辑

## TL;DR
真实波动幅度均值（Average True Range, ATR）是衡量市场波动性的工具。频道主介绍其计算原理，并给出基于"入场K线涨跌幅相对于ATR倍数"的分级止损公式，配合Vegas隧道+MACD背离作为入场信号。

## What It Measures / 它衡量什么
- ATR 衡量市场近期的**真实波动幅度均值**，不衡量价格方向
- 数值无负数
- ATR 大 = 近期波动剧烈 → 接下来可能继续大K线 → 止损应放远
- ATR 小 = 近期小幅波动 → 接下来大K线概率小 → 止损可放近
- 适合任何品种、任何周期

## Parameters & Settings / 参数设置
（00:00:21-00:48）
- 在TV指标搜索 `Average True Range` → 添加到图表
- **默认长度天数 = 14**（最常用）：返回最后14根K线波动幅度的平均值
- 如果只想看单根K线波动幅度 → 长度天数 = 1
- 不同周期 ATR 数值差异极大（00:02:24-02:36）：
  - BTCUSD 日线 ATR ≈ 1494
  - BTCUSD 15分钟 ATR ≈ 95
  - 15分钟 ATR < 日线 ATR 的 1/10

## How To Read / 怎么解读
**ATR 算法**（00:00:48-01:17）：
取以下三者的**绝对值的最大值**：
1. 当前K线的最高价 − 最低价
2. 当前K线的最高价 − 前一根K线收盘价（取绝对值）
3. 当前K线的最低价 − 前一根K线收盘价（取绝对值）

这个最大值就叫"波动幅度"。
14日参数 ATR = 最近14根K线波动幅度的平均。

**常见误区**：
- 用几十美金的小风险博日线/4小时大行情 → 价格在朝你方向运行之前没有足够生存空间应对日常波动 → 连续止损
- 必须根据周期级别的ATR给出合理止损空间

## Trade Setups Using It / 配套的入场出场
**完整止损公式**（基于入场K线涨跌幅 vs 入场K线对应的 ATR）：

| 入场K线涨跌幅 | 多单止损 | 空单止损 |
|---|---|---|
| < 1× ATR | 入场K线最低价 − 1×ATR | 入场K线最高价 + 1×ATR |
| 1× ~ 2× ATR | 入场K线最低价 − 2×ATR | 入场K线最高价 + 2×ATR |
| > 2× ATR（自信很强时） | 入场K线最低价 − 3×ATR | 入场K线最高价 + 3×ATR |

**如果止损点距离其他关键位置（前低/前高/密集成交区）较近，且在可承受风险内，可以拉到共振重合位置**。

**入场信号示例**（00:03:01）：BTCUSD 1小时图
- 多头：价格回落到Vegas隧道附近 + MACD出现底背离 → 这根K线收盘价买入
- 空头：价格反弹到Vegas隧道附近 + MACD出现连续顶背离 → MACD的实柱转虚柱K线收盘价空单

## Caveats / 注意
- 是 indicator-review，专门讲止损放置
- ATR 数据来源于近期，不能保证未来波动相似
- 设置止损时务必考虑当前周期的ATR量级（日线和15分钟差几十倍）
- "据传说，即使是家里的猫使用ATR也能成为百万富猫"（00:00:15）

## My Notes
