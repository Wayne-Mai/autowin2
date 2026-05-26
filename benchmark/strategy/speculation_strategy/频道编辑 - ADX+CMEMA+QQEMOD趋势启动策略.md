---
strategy: ADX + CM EMA Trend Bars + QQE MOD 趋势启动策略
trader: 频道编辑
source_video: https://www.youtube.com/watch?v=fWMr2itcp80
source_transcript: 【牛犇，早看早赚！】TradingView上看趋势最准的ADX策略，最强量价策略策略抓住牛市的起点，提供精确的买入卖出信号！！#adxindicator_#obv_#tradingview.md
asset_class: mixed
timeframe: intraday
claimed_returns: "BTC 1小时图159天回测：1:2操作收益69%；100次连续交易总收益率315%"
claimed_win_rate: "1:1胜率65%，1:2胜率36%，1:3胜率32%，1:5以上21%"
claimed_payoff_ratio: "分批止盈，第一目标1:1"
backtest_period: "BTC 1小时图，约159天"
indicators: [ADX and DI(等级20), CM EMA Trend Bars(21), QQE MOD]
tags: [ADX, EMA, QQE, 趋势启动, 趋势起点, 1小时]
extracted: 2026-05-26
---

# ADX + CM EMA Trend Bars + QQE MOD 趋势启动策略 — 频道编辑

## TL;DR
"能让人在24年发财致富的交易策略"——通过 ADX > 20 + CM EMA Trend Bars 21 上穿/下穿 + QQE MOD 蓝/红能量柱 三共振，对趋势起点的识别非常敏感，经常能以较小风险博取很大收益。BTC 1小时图100次连续交易 1:1胜率65%、按1:2总收益69%，整体收益率315%。

## Setup / 形态

### 指标设置
- **ADX and DI** (03:32)
  - 数值改为 **20**（比第一套策略的30更低，捕捉更多交易机会 03:34）
  - 只留 ADX 线
- **CM EMA Trend Bars** (03:37)
  - 参数 = **21**
  - **bar color 选项勾掉**
- **QQE MOD** (03:48)
  - 该指标结合 RSI 和 ATR 数据，对识别盘整 vs 趋势行情非常有效 (03:50)
  - 参数保持不变
  - **QQE line 选项勾掉** (03:57)

### 时间框架
- 示例：BTC/USD **1小时**图 (04:05)

## Entry Rules / 入场

### 多头规则 (04:09) — 三个条件全部满足
1. **阳K线上穿 CM EMA 绿线的起始位置** (04:11)。
2. **ADX 线处在 20 上方** (04:15)。
3. **QQE MOD 必须是蓝色能量柱** (04:18)。
4. 三条件满足 → 这根阳K线即关键K线，收盘价即入场位置 (04:26)。

### 空头规则 (04:46) — 三个条件全部满足
1. **阴K线下穿 CM EMA 红线的起始位置** (04:48)。
2. **ADX 红线处在 20 上方** (04:53)。
3. **QQE MOD 必须是红色能量柱** (04:56)。
4. 三条件满足 → 关键阴K线收盘价入场。

## Exit & Stop Loss / 出场止损

### 止损
- **多头** (04:30)：近期波段低点附近。
- **空头** (05:07)：近期波段高点附近。

### 止盈
- 分批止盈方式 (04:34)：1:1 出一部分，剩余拿住博取更高利润。

## Risk Management / 仓位
- 视频未单独提仓位规则。

## Examples / 实例
- 视频未给具体K线实例。

## Caveats / 注意
- ADX 阈值从30降到20——更多交易机会但也更多假信号 (03:34)。
- CM EMA Trend Bars 的"绿线起始位置"和"红线起始位置"是关键——必须是 K 线穿过该 EMA 的那根 K 线作为关键 K 线。
- QQE MOD 能量柱颜色必须明确——蓝色对应做多、红色对应做空。
- 对趋势起点敏感意味着会承接小回撤但博取大延续。
- 主播评分：7分；值得花时间优化 (06:09)。

## Backtest Stats / 回测统计
- BTC 1小时图 100次连续交易：
  - 1:1 胜率 = **65%**
  - 1:2 胜率 = **36%**
  - 1:3 胜率 = **32%**
  - 1:5以上 = **21%**
- 100次连续交易收益率 = **315%**
- 159天只按1:2操作 = **69% 收益**

## My Notes
