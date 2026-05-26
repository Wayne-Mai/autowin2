---
strategy: SuperTrend + TRAMA 平均K线剥头皮策略
trader: 频道编辑（测评自 Quantum Trading Strategy 频道）
source_video: https://www.youtube.com/watch?v=6jX7iIDrebk
source_transcript: 测评：新型超级趋势策略，300次连续交易数据大公开#交易系统_#交易策略测试_#supertrend#测评.md
asset_class: mixed
timeframe: scalping
claimed_returns: "ETH/USD 15min 200日测试 354.94% 收益；AAPL 15min 100次回测有 11 笔达到 1:10 盈亏比"
claimed_win_rate: "ETH 1:1=61% / 1:2=37% / 1:3=27%；AAPL 1:1=59% / 1:2=39% / 1:3=31%"
claimed_payoff_ratio: 1:1/1:2/1:3 分级
backtest_period: ETH 2022/2/17–2022/9/2 共197交易日；AAPL 2021/1/28–2022/9/2，各100次连续交易
indicators: [SuperTrend, TRAMA (Trend Regularity Adaptive Moving Average LUX), Heikin Ashi, ATR Stop Loss Finder]
tags: [supertrend, TRAMA, Heikin-Ashi, scalping, ETH, AAPL, 剥头皮]
extracted: 2026-05-26
---

# SuperTrend + TRAMA 平均K线剥头皮策略 — 频道编辑

## TL;DR
源自 Quantum Trading Strategy 频道的 1 分钟剥头皮策略（原称单笔 120% 利润）。把 Heikin Ashi 平均 K 线图当作信号指标，添加 SuperTrend 与 TRAMA(100)，在普通 K 线图上的对应位置入场。频道编辑给评分 6/10——有利可图但要 10 倍杠杆才能达到原作者声称的收益 (00:00-06:05)。

## Setup / 形态
- **图表样式**：图表样式栏 → 选中 Heikin Ashi（平均 K 线图），并收藏便于切换普通 K 线 (00:38-00:50)
- **指标 1 SuperTrend**：在 Heikin Ashi 图上添加，将 ATR Multiplier 改成 **4.5**，买入信号位置改在 "bar 下方"，卖出信号在 "列上"，其它无用功能勾掉 (01:16-01:29)
- **指标 2 TRAMA**：Trend Regularity Adaptive Moving Average [LUX]，参数改成 **100** (01:31-01:43)
- **可选**：ATR Stop Loss Finder（止损指标）(03:04-03:11)

## Entry Rules / 入场

### 多头规则
1. Heikin Ashi 图中 SuperTrend 发出买入信号 (01:55-01:58)
2. 买入信号所对应 K 线的收盘价处在 TRAMA 线上方 (01:58-02:02)
3. 两个条件同时满足 → 平均 K 线对应的下方普通 K 线 = 关键 K 线
4. **入场价 = 关键 K 线收盘价** (检查两个图表时间线对账一致) (02:13-02:18)

### 空头规则
1. Heikin Ashi 图中 SuperTrend 发出卖出信号 (02:42-02:47)
2. 卖出信号 K 线的收盘价处在 TRAMA 线下方 (02:47-02:52)
3. 关键 K 线收盘价 = 入场位置

## Exit & Stop Loss / 出场止损
- **止损**：
  - 如果关键 K 线涨跌幅度很大 → 关键 K 线最低价（多）/ 最高价（空）附近
  - 如果幅度不大 → 近期低点/高点
  - 也可结合 ATR Stop Loss Finder 红线 (02:18-03:11)
- **止盈**：分批止盈，风险回报比 1:1 或 1:2 先出一部分，剩余博取更高收益 (02:29-02:43)

## Risk Management / 仓位
- 原作者建议 10 倍杠杆才能达到单笔 120%+ 收益
- 频道编辑评分 6/10：账户风险和损失也会成 10 倍数增加 (05:42-05:56)

## Examples / 实例
- ETH/USD 15min 多头示例 (03:17-03:46)
- ETH/USD 15min 空头示例 (03:47-04:18)

## Backtest Results / 测评数据 (04:18-05:42)
- ETH/USD 1min (100 次)：数据不理想，改用 15min
- ETH/USD 15min (2022/2/17–2022/9/2 共197个交易日)：
  - 1:1 胜率 61%、1:2 胜率 37%、1:3 胜率 27%
  - 总收益 354.94%
  - 单笔收益 >12% 订单 9 笔
- AAPL 15min (2021/1/28–2022/9/2, 100 次)：
  - 1:1 胜率 59%、1:2 胜率 39%、1:3 胜率 31%
  - 1:10 盈亏比的交易 11 次（但单笔 12% 收益只有 1 笔）

## Caveats / 注意
- "用平均 K 线图作为指标使用，普通 K 线图作为下单图" — 平均 K 线收盘价≠实际收盘价
- 10 倍杠杆账户风险极大
- 频道编辑评分 6/10

## My Notes
