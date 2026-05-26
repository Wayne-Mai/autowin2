---
strategy: ADX + HalfTrend + OBV 趋势三共振策略
trader: 频道编辑
source_video: https://www.youtube.com/watch?v=fWMr2itcp80
source_transcript: 【牛犇，早看早赚！】TradingView上看趋势最准的ADX策略，最强量价策略策略抓住牛市的起点，提供精确的买入卖出信号！！#adxindicator_#obv_#tradingview.md
asset_class: mixed
timeframe: intraday
claimed_returns: "BTC 15分钟图192天回测：1:2操作收益76%；100次连续交易总收益率231%"
claimed_win_rate: "1:1胜率67%，1:2胜率38%，1:3胜率27%，1:5以上18%"
claimed_payoff_ratio: "分批止盈，第一目标1:1"
backtest_period: "BTC 15分钟图，约192天"
indicators: [ADX and DI(等级30), HalfTrend, OBV oscillator(长度83)]
tags: [ADX, OBV, HalfTrend, 趋势, 量价共振]
extracted: 2026-05-26
---

# ADX + HalfTrend + OBV 趋势三共振策略 — 频道编辑

## TL;DR
ADX 是 TradingView 上最精准的趋势强度指标——可以量化趋势强度、明确界定趋势强弱的分界线。本策略用 ADX(>30判定强趋势) + HalfTrend(基于波动率的趋势指标，买卖箭头信号) + OBV(能量潮量价确认) 的三共振组合捕捉强趋势的延续。BTC 15分钟 100次连续交易 1:1胜率67%，按1:2操作总收益76%。

## Setup / 形态

### 指标设置
- **ADX and DI** (00:55)
  - 参数保持不变
  - 勾掉 DI+ 和 DI-，只留 ADX 线
  - **等级 = 30**（超过30=强趋势，走势大概率延续）
  - 颜色参考主播设置
- **HalfTrend** (01:21) (基于波动率的趋势指标，与 supertrend 类似但识别逻辑不同)
  - 只留 HalfTrend 趋势线 + 买卖指示信号
  - HalfTrend 信号大部分都很有效，但遇到震荡行情难免出现错乱指示——所以要加上 OBV 过滤 (01:42)
- **OBV oscillator** (01:50)
  - **长度参数 = 83**
  - 颜色参考主播设置
  - 通过成交量增减 + 价格变动关系判断走势 (02:00)

### 时间框架
- 示例：BTC/USD 15分钟图 (02:22)

## Entry Rules / 入场

### 多头规则 (02:25) — 三个条件全部满足
1. **HalfTrend 指标出现绿色买入信号** (02:27)。
2. **OBV 指标处在蓝色区域** (02:31)。
3. **ADX 黄线在蓝线上方**（数值 > 30）(02:34)。
4. 条件全部满足 → 所对应K线的收盘价即入场位置 (02:42)。

### 空头规则 (02:59) — 三个条件全部满足
1. **HalfTrend 指标出现红色卖出信号** (03:02)。
2. **OBV 指标处在红色区域** (03:06)。
3. **ADX 黄线在蓝线上方** (03:10)（数值 > 30）。
4. 条件全部满足 → 所对应K线收盘价入场。

## Exit & Stop Loss / 出场止损

### 止损
- **多头** (02:46)：近期的小波段低点附近。
- **空头** (03:19)：近期的小波段高点附近。

### 止盈
- 分批止盈方式 (02:49)：1:1 出一部分，剩余拿住博取更高利润。

## Risk Management / 仓位
- 视频未单独提仓位规则。

## Examples / 实例
- 视频未给具体K线实例，主要以概念说明。

## Caveats / 注意
- ADX > 30 才有效；ADX 上升中 + HalfTrend 信号是关键。
- OBV 处于对应颜色区是量价确认，过滤 HalfTrend 在震荡中的假信号。
- 主播评分：7分；策略还有不小提升空间，值得花时间优化 (06:09)。

## Backtest Stats / 回测统计
- BTC 15分钟图 100次连续交易：
  - 1:1 胜率 = **67%**
  - 1:2 胜率 = **38%**
  - 1:3 胜率 = **27%**
  - 1:5以上 = **18%**
- 100次连续交易收益率 = **231%**
- 192天只按1:2操作 = **76% 收益**

## My Notes
