---
strategy: ADX+EMA200+Stoch RSI+ATR 趋势策略
trader: 频道编辑
source_video: https://www.youtube.com/watch?v=gfEqy4uGe8c
source_transcript: 【强烈推荐】指标之王ADX的最强战法#交易系统_#交易策略测试_#指标.md
asset_class: crypto
timeframe: intraday
claimed_returns: "胜率赔率和收益率三率表现最好"（频道主自述）
claimed_win_rate: 未具体公布
claimed_payoff_ratio: 分批止盈 1:1出部分 + 拉余仓
backtest_period: "闭关十天，数百次交易回测"
indicators: [EMA200, ADX, Stoch RSI, ATR Stop Loss Finder]
tags: [ADX, 趋势, EMA, RSI, ATR, BTC, 1小时]
extracted: 2026-05-26
---

# ADX+EMA200+Stoch RSI+ATR 趋势策略 — 频道编辑

## TL;DR
频道主"闭关十天数百次回测"打造的趋势策略，结合EMA200趋势过滤、ADX强度过滤、Stoch RSI超买超卖择时和ATR止损。声称胜率、赔率、收益率三率表现最佳。

## Setup / 形态
**指标设置**（共4个，免费TV指标）：

1. **EMA 移动平均线**（00:00:37-00:53）
   - 名称：Moving Average Exponential
   - **参数长度 = 200**
   - **时间周期 = 4小时**
   - 颜色：浅蓝色
   - 用途：判断大周期趋势

2. **ADX and DI**（00:00:54-01:15）
   - 取消勾选 DI+ 和 DI-，只保留 ADX 线
   - **参数等级 = 50**
   - 含义：ADX 处在 50 上方时趋势动能足够强劲，趋势大概率延续

3. **Stoch RSI（随机相对强弱）**（00:01:15-01:34）
   - 参数保持默认
   - K线（蓝）/D线（黄）
   - KD 在 80 上方 = 超买；在 20 下方 = 超卖

4. **ATR Stop Loss Finder**（00:01:34-01:42）
   - **参数长度 = 8**
   - 用于止损放置

**主交易周期**：1小时图表（00:01:47示例为BTCUSDT 1H）

## Entry Rules / 入场
**多头规则**（00:01:50-02:15）：
1. 价格处在 EMA200（4小时）的**上方**
2. ADX 处在 **50 上方**
3. Stoch RSI 的蓝色K线**上穿**黄色D线，在**超卖区（<20）形成金叉**
4. 三个条件全部满足时，金叉对应的K线 = 关键K线
5. **关键K线的收盘价**入场多单

**空头规则**（00:02:26-02:51）：
1. 价格处在 EMA200（4小时）的**下方**
2. ADX 处在 **50 上方**
3. Stoch RSI 蓝色K线**下穿**黄色D线，在**超买区（>80）形成死叉**
4. 三个条件全部满足时，死叉对应的K线 = 关键K线
5. **关键K线的收盘价**入场空单

## Exit & Stop Loss / 出场止损
- **多单止损**：关键K线对应的 ATR 蓝线**下方**（00:02:15）
- **空单止损**：关键K线对应的 ATR 红线**上方**（00:02:51）
- **止盈方式**（分批）：
  - 风险回报比 1:1 出一部分仓位
  - 剩余部分拿住博取更高利润

## Risk Management / 仓位
- 视频未明确具体仓位百分比
- 采用分批止盈以兼顾风险与盈利

## Examples / 实例
- 多头实例：价格在EMA200上方 + ADX>50 + Stoch RSI超卖金叉 → 入场 → 小风险博大收益（00:03:08-03:39）
- 空头实例：价格在EMA200下方 + ADX>50 + Stoch RSI超买死叉 → 入场 → 非常丰厚回报（00:03:39-04:09）

## Caveats / 注意
- ADX 50 是较严格的趋势强度过滤，会减少信号频次
- 三指标共振才入场 — 入场机会不会很多
- 该频道允许只能添加3指标的用户使用合并指标（描述中链接）
- 频道主未公布具体数字胜率/收益

## My Notes
