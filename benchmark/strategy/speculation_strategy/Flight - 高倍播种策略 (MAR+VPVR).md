---
strategy: 高倍播种策略 (MAR均线带 + VPVR成交量分布)
trader: Flight (韩国论坛交易员)
source_video: https://www.youtube.com/watch?v=IC-ysmoTeYM
source_transcript: 炒币圣经！！韩国论坛上最火的交易员Flight，用370赚到750万美金的三套超绝策略曝光，逆势刀锋策略，高倍播种策略，成交量和RSI背离策略，完完整整全公开！#专业炒币策略_#crypto.md
asset_class: crypto
timeframe: swing
claimed_returns: "用370美元本金赚到750万美元（账户级别）"
claimed_win_rate: 未具名
claimed_payoff_ratio: 未具名
backtest_period: 未具名
indicators: [Moving Average Ribbon (MAR), VPVR (Visible Range Volume Profile), Volume]
tags: [crypto, trend-confirmation, volume-profile, moving-average-ribbon, breakout, support-resistance]
extracted: 2026-05-26
---

# 高倍播种策略 (MAR+VPVR) — Flight

## TL;DR
使用 Moving Average Ribbon (MAR，移动平均带状指标) 配合 VPVR (可见范围成交量分布) 去判断价格在均线带和POC处会突破还是遇阻。颜色由紫转绿且放量突破均线带 = 趋势由空转多；反向规则同 (04:01-04:46)。

## Setup / 形态
- **MAR 移动平均带状指标 (Moving Average Ribbon)**：
  - 由几十根不同长度的移动平均线组成的密集线网 (04:14-04:20)
  - 紫色代表空头趋势，绿色代表多头趋势
  - 发散程度反映趋势强弱
  - 颜色表示多空趋势 (04:26-04:28)
- **VPVR (Visible Range Volume Profile)** (04:46-05:24)：
  - 全称 Visible Range Volume Profile
  - TradingView 上唯一被单独列组的指标 (技术列表 → Profiles → Visible Range Volume Profile)
  - 普通版TradingView可使用侧边栏第五个工具栏的"固定范围成交量分布图"，手动标注范围
  - 右侧横向量能柱：显示图表当前可见范围内所有K线的成交量在各价格上的分布
- POC (Point of Control) 红线 = 整个可见范围成交量最密集的价位 (05:54-06:06)

## Entry Rules / 入场
**多头规则** (04:28-04:34)：
1. MAR 指标由紫线转成绿线
2. 价格放量突破或完全脱离均线带 → 趋势已由空转多
3. 在 VPVR 成交量密集区域 / POC 红线附近寻找支撑确认 (经常被当成支撑使用，05:54-06:06)

**空头规则** (04:37-04:46)：
1. MAR 指标由绿线转成紫线
2. 价格放量跌破或完全脱离均线带 → 趋势已由多转空
3. 在 VPVR 成交量密集区域 / POC 红线附近寻找阻力确认

## Exit & Stop Loss / 出场止损
- 成交量密集区域常成为支撑阻力，难以一次突破，可作为利润目标 (05:54-06:01)
- 成交量低的区域 (跳空/暴涨暴跌区) 为供需失衡区，价格通常不停留太久，不作为止盈位 (06:06-06:20)
- 视频未给出具体止损公式 (沿用Flight风控框架：单笔2%、20倍杠杆、1%本金/笔)

## Risk Management / 仓位
沿用Flight统一框架：1% 本金/笔、最大杠杆20倍、单笔止损2%、日内最大亏损4%、同时持仓不超过3个、单日开仓不超过10次。

## Examples / 实例
- 视频中描述：MAR紫转绿+放量突破=趋势反转入场点。具体K线案例未单独展示。

## Caveats / 注意
- Volume指标与VPVR本质不同：Volume表示一个时间周期内的成交量；VPVR表示一个价格范围内的成交量 (05:24-05:50)
- 图表范围变动时 VPVR 量能柱也随之变化 (05:08-05:15)
- 跳空/暴涨暴跌区域订单积累少，价格不会久留，不可作为目标位

## My Notes
