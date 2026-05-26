---
strategy: NMACD + 5 IN 1 + MA13 三率全优交易系统
trader: 频道编辑
source_video: https://www.youtube.com/watch?v=fT4jb-I5zYc
source_transcript: 【强烈推荐】顶级的交易策略，胜率收益率频率三率全优的神级交易系统#交易系统#交易策略回测#MACD.md
asset_class: crypto
timeframe: intraday
claimed_returns: "示例 1H BTC 空单 39000 → 35200 ≈ 10% 下跌空间；10 倍杠杆 → 钱包翻倍"
claimed_win_rate: "频率/胜率/收益率三率全优（视频原话，无具体数字）"
claimed_payoff_ratio: 至少 1:1，分批止盈剩余博取更高
backtest_period: 未明确
indicators: [NORMALIZED MACD (Fast MA=13), 5 IN 1 (RSI=21, SMA=55), MA13]
tags: [MACD, RSI, 均线, 共振, 1H, 加密货币]
extracted: 2026-05-26
---

# NMACD + 5 IN 1 + MA13 三率全优交易系统 — Speculation Lab

## TL;DR
3 个 TradingView 免费指标共振的入场系统：NORMALIZED MACD 给方向，5 IN 1（RSI+SMA）给金叉/死叉触发，MA13 均线作大趋势过滤。1H BTC 示例显示 10 倍杠杆睡一觉钱包翻倍。视频自称"频率胜率收益率三率全优的神级交易系统"。

## Setup / 形态
- 时间周期：1H 级别（视频主用）
- 品种：BTC/USD
- 指标 1：NORMALIZED MACD (N/MACD)
  - Fast MA 改成 13
  - N/MACD 比常规 MACD 入场提示更及时，常规 MACD 经常行情走完信号才出现（滞后）
- 指标 2：5 IN 1（指标搜索栏搜 "5 IN 1"，选带黄色五角星按钮）
  - RSI 参数 21
  - SMA 参数 55
  - RSI 颜色白色
  - 背景选项取消
- 指标 3：移动平均线 MA
  - 参数 13
  - 颜色蓝色

## Entry Rules / 入场

**多头规则（01:21–01:43）**
1. N/MACD 的**红线由下往上穿过白线**（多头信号）
2. RSI 的**白线由下往上穿过红线**（金叉）
3. 金叉对应的 K 线 = 关键 K 线
4. **关键 K 线的收盘价必须收在 MA13 均线上方**
5. 三个条件全部满足 → 在关键 K 线的**收盘价**入场多单

**空头规则（02:01–02:23）**
1. N/MACD 的**红线由上往下穿过白线**（危险信号）
2. RSI 的**白线由上往下穿过红线**（死叉）
3. 死叉对应的 K 线 = 关键 K 线
4. **关键 K 线的收盘价必须收在 MA13 均线下方**
5. 三个条件全部满足 → 在关键 K 线的**收盘价**入场空单

## Exit & Stop Loss / 出场止损

**多头止损**
- 近期低点位置
- 如果关键 K 线涨跌幅度过大，止损放在**关键 K 线下方**

**空头止损**
- 近期高点位置
- 关键 K 线涨跌幅度大 → 止损放在**关键 K 线上方**

**止盈（多/空通用）**
- 分批止盈
- 在风险回报比 1:1 出一部分
- 剩余留场博取更高利润

## Risk Management / 仓位
- 视频未提供具体仓位公式
- 视频示例 10 倍杠杆 → 10% 下跌空间 = 钱包翻倍（说明高杠杆使用时空间幅度的重要性）

## Examples / 实例
- 5 月 4 日 7 点 BTC/USD 1H 图：多头信号入场
- 5 月 5 日 7 点 N/MACD 危险信号 → 21 点 RSI 死叉 → 关键 K 线收盘在 MA13 下方 → 入场空单
- 空单从 39000 美金入场，下跌到 35200 美金附近 ≈ 10% 下跌空间
- 睡前开 10 倍杠杆空单，醒来钱包翻倍

## Caveats / 注意
- 三个条件必须同时满足，缺一不可
- 关键 K 线必须等收盘才能入场
- 关键 K 线幅度过大时止损要设在 K 线之外（防被反向插针打损）
- 视频明确"高阶交易策略往往就是这样朴实无华"

## My Notes

