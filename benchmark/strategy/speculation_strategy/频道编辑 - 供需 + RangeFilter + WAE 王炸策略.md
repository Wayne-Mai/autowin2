---
strategy: 供需 + RangeFilter + WAE 王炸策略（3.0/3.1 双版本）
trader: 频道编辑
source_video: https://www.youtube.com/watch?v=KgN97lPYFy8
source_transcript: 【王炸策略！！】胜率90%的超级供需策略，颤抖着手进行了连续100次交易回测！！TradingView上最好用订单块指标一定要看！！#交易策略_#forextrading_#嘉盛.md
asset_class: forex
timeframe: intraday
claimed_returns: "EUR/USD 15min 100次回测按 10x 杠杆收益率 315%；若只按 1:2 操作 104.1%"
claimed_win_rate: "1:1 = 69%; 1:2 = 41%; 1:3 = 35%; 1:5 = 19%"
claimed_payoff_ratio: 1:1/1:2/1:3/1:5 分级
backtest_period: "2024/3/15 – 2024/6/21 (<100 天)"
indicators: [fluid trades (自动供需区+市场结构), Range Filter (range_multiplier=2.5), Waddah Attar Explosion (WAE)]
tags: [供需策略, 订单块, range-filter, WAE, EURUSD, forex]
extracted: 2026-05-26
---

# 供需 + RangeFilter + WAE 王炸策略 — 频道编辑

## TL;DR
组合三个 TradingView 指标：fluid trades 自动识别供需区/市场结构、Range Filter 提供买卖信号、Waddah Attar Explosion (WAE) 跟踪趋势强度。提供 3.0 简化版与 3.1 含 BOS 突破版。EUR/USD 15min 100 次回测 1:1 胜率 69% (00:00-04:33)。

## Setup / 形态
- **指标 1**：fluid trades — 自动识别供给需求区和市场结构。**Supply/Demand Box Width = 10**，其他不变 (00:47-01:08)
- **指标 2**：Range Filter（范围过滤器买卖指标）。**range_multiplier = 2.5**，其他用不到的勾掉 (01:08-01:29)
- **指标 3**：Waddah Attar Explosion (WAE) — 把 MACD 和布林带合并跟踪趋势强度和方向 (01:29-01:42)

## Entry Rules / 入场

### 策略 3.0 多头规则 (01:48-02:18)
1. 价格回落到**需求区**后
2. Range Filter 出现**买入信号**
3. K 线对应的 **WAE 绿柱必须收于黄线上方**
4. 两个条件满足 → 这根 K 线 = 关键 K 线，**关键 K 线收盘价 = 入场位置**
5. 止损：需求区附近 或 近期低点
6. 止盈：分批止盈，1:1 出一部分，剩余拿住博取更高利润

### 策略 3.0 空头规则 (02:18-02:42)
1. 价格在**供给区遇阻**后
2. Range Filter 出现**卖出信号**
3. K 线对应的 **WAE 红柱必须收于黄线上方**
4. 两个条件满足 → 关键 K 线收盘价入场空单
5. 止损：供给区附近 或 近期高点

### 策略 3.1 多头规则（含 BOS 突破确认）(02:42-03:25)
1. 价格回落到需求区附近 + Range Filter 买入信号
2. **不要急于入场**，耐心等待看涨形态的出现
3. 主要看价格是否突破 **BOS**（Break of Structure）
4. 实际使用中也可用头肩底、双底等看涨模型辅助
5. **突破 BOS 的这根 K 线对应的 WAE 绿柱必须收于黄线上方**
6. 三个条件全部满足 → 关键 K 线收盘价入场多单
7. 止损：需求区附近 或 近期低点

### 策略 3.1 空头规则（与多头对称）(03:25-04:00)
1. 供给区遇阻回落 + Range Filter 卖出信号
2. 耐心等待看跌形态出现（突破 BOS）
3. 跌破 BOS 的这根 K 线对应的 **WAE 红柱必须收于黄线上方**
4. 三个条件满足 → 关键 K 线收盘价入场空单
5. 止盈：1:2 风险回报比

## Exit & Stop Loss / 出场止损
- 止损固定在供需区附近或近期高低点
- 止盈分批，1:1 出一部分

## Backtest Results / 测评数据
- **EUR/USD 15min, 2024/3/15 – 2024/6/21 (100 笔连续)** (04:00-04:35)：
  - 盈亏比 1:1 胜率 69%
  - 1:2 胜率 41%
  - 1:3 胜率 35%
  - 1:5+ 胜率 19%
  - 10 倍杠杆下收益率 315%
  - 只按 1:2 操作收益率 104.1%
- 频道编辑评分 **7/10**：非常有利可图的交易策略，"供需策略也确实是最适用外汇交易的策略之一" (04:35-04:45)

## Caveats / 注意
- 三个指标都是免费 TradingView 指标，但有些用户图表只能添加 2 个 → 前两个有合并版本（见说明栏）
- 适用于外汇市场

## My Notes
