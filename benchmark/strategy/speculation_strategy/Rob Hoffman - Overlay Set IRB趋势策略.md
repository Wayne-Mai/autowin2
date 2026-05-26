---
strategy: Overlay Set + Inventory Retracement Bar (IRB) 趋势策略
trader: Rob Hoffman
source_video: https://www.youtube.com/watch?v=HGOEzcRO29k
source_transcript: 传奇交易员Rob_Hoffman的交易策略，实盘交易冠军这样做趋势单！_#交易系统_#交易策略_#交易策略测试.md
asset_class: mixed
timeframe: intraday
claimed_returns: "国际顶级交易赛事7次实盘账户冠军"
claimed_win_rate: <未明确>
claimed_payoff_ratio: <分批止盈，第一目标 1:1>
backtest_period: <未明确>
indicators: [Rob Hoffman Overlay Set, Rob Hoffman Inventory Retracement Bar, EMA]
tags: [趋势, 冠军策略, 比特币, 趋势过滤]
extracted: 2026-05-26
---

# Overlay Set + IRB 趋势策略 — Rob Hoffman

## TL;DR
Rob Hoffman是国际顶级交易赛事7次实盘账户冠军。策略用两个免费TradingView指标——Rob Hoffman Overlay Set (多条均线带) + Rob Hoffman Inventory Retracement Bar (IRB) ——通过Overlay Set过滤掉震荡行情中频繁出现的假信号、识别最佳趋势入场点，IRB标记关键回撤K线。规则简单，规定一段趋势中只可进行一次盈利交易（被止损可再试一次，最多两次）。

## Setup / 形态

### 指标设置
- **指标1: Rob Hoffman - Overlay Set** (00:39)
  - 颜色参考主播设置
  - 为简洁可勾掉用不到的功能
- **指标2: Rob Hoffman's Inventory Retracement Bar (IRB)** (00:55)
  - 参数保持默认
  - 样式 Long Bar 颜色设置成浅蓝色，指示箭头换成向上标签，位置在Bar下方
  - 样式 Short Bar 颜色设置成红色，指示箭头换成向下标签，位置在列上

### 时间框架
- 示例使用：BTC/USD 15分钟图 (01:15)

## Entry Rules / 入场

### 多头规则 (01:18)
1. **Overlay Set 趋势条件**：红色慢线要 **高于** 蓝色快线，且红蓝线之间没有白线 (01:20)。
2. **IRB 关键K线**：蓝色箭头所指向的阳K线要处在红线上方 (01:27)；这根阳K线就是关键K线。
3. **入场位置**：关键K线的收盘价 (01:35)。

### 空头规则 (02:12)
1. **Overlay Set 趋势条件**：红色慢线要 **低于** 蓝色快线，且红蓝线之间没有白线 (02:14)。
2. **IRB 关键K线**：红色箭头所指向的阴K线要处在红线下方 (02:21)。
3. **入场位置**：关键K线的收盘价。

## Exit & Stop Loss / 出场止损

### 止损
- **多头**：设置在蓝线下方 (01:38)；如果白线密集缠绕，可选择在最下方的白线处止损 (01:40)。
- **空头**：设置在蓝线上方 (02:33)；白线密集缠绕时选择最上方的白线处。

### 止盈
- 分批止盈方式 (01:45)：1:1风险回报比出一部分，剩余部分拿住博取更高利润。

### 趋势结束信号
- **多头趋势结束** (01:53)：关键K线后有K线跌破最下方的白线。
- **空头趋势结束** (02:42)：关键K线后有K线突破最上方的白线。

## Risk Management / 仓位

### 同一段趋势内的交易次数限制 (01:59)
- 一段趋势中只可以进行 **一次盈利的交易**。
- 如果第一笔交易被止损，才可以在这段趋势中寻找第二次入场机会。
- 直到两次交易结束为止——盈利与否，都不在这段趋势进行第三次交易。
- 空单规则相同 (02:46)。

## Examples / 实例
- **多头实例 (03:01)**：BTC 15分钟图，Overlay Set 红线高于蓝线、红蓝间无白线 → IRB 绿色箭头指向阳K线在红线上方 → 关键K线收盘价入场 → 止损蓝线下方 → 分批止盈；抓到趋势起点获利可观。
- **空头实例 (03:28)**：Overlay Set 红线低于蓝线、红蓝间无白线 → IRB 红色箭头指向阴K线在红线下方 → 关键K线收盘价入场 → 因线条密集缠绕选最上方白线处止损 → 分批止盈；利润空间惊人。

## Caveats / 注意
- 红蓝线之间必须没有白线，否则不入场。
- 关键K线必须满足箭头方向 + 处于红线对应侧两个条件。
- 同一段趋势最多两次交易上限是硬规定，约束过度交易。
- Rob Hoffman 七次冠军即"方法有效的证据"——但仍只是一种趋势跟随策略，需要清晰趋势配合。

## My Notes
