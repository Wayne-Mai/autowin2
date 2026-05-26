---
strategy: Camarilla 膨胀与收缩概念突破策略（Camarilla + LRS）
trader: 频道编辑
source_video: https://www.youtube.com/watch?v=4oZojXfUias
source_transcript: 特朗普Taco交易术的克星！！最强的_5_种价格行为策略曝光：Camarilla_突破策略，孕线策略，谐波策略，2618双顶底结构，一次全掌握！！#价格行为策略_#美股__#mitrade.md
asset_class: mixed
timeframe: intraday
claimed_returns: <未明确>
claimed_win_rate: <未明确>
claimed_payoff_ratio: <未明确，分批止盈>
backtest_period: <未明确>
indicators: [Expanded Camarilla Levels, Linear Regression Slope (LRS)]
tags: [价格行为, 突破, 收缩膨胀, 包含区间, 15分钟, 1小时, 4小时]
extracted: 2026-05-26
---

# Camarilla 膨胀与收缩突破策略 — 频道编辑

## TL;DR
基于"波动性收缩-膨胀"概念：当前一小时(或一天/一周)的价格波动范围完全包含在前一个时段的波动范围内时，说明波动性下降、多空力量达到短暂平衡——价格随后选择方向突破并在区间外收盘，突破方向就是多空选择。用 Camarilla 上下轨 (H3/L3) 标记区间，用 LRS (Linear Regression Slope, 长度200) 判断市场多空方向。15分钟、1小时、4小时级别均好用。

## Setup / 形态

### 指标设置
- **指标1: Expanded Camarilla Levels** (00:19)
  - HTF mode 设置为 "用户自定义"
  - timeframe 设置为 1小时
  - 菜单栏只留 **H3** 和 **L3** 线
  - 图形设置成圆点图
  - 其他用不到的功能勾掉
  - 含义：timeframe=1小时表示当前1小时的价格波动范围已完全包含在前一小时的波动范围之内 (00:32)；也可设为1天/1周，原理相同——都表示波动性相较前一时段下降，多空达到短暂平衡 (00:42)。
- **指标2: Linear Regression Slope (LRS)** (01:00)
  - 长度参数 = **200**
  - 用于判断市场多空方向

### 核心原理 (00:42)
波动性相较前一时段下降 → 市场多空力量短暂平衡 → 价格选择突破 → 在区间外收盘 → 突破方向即多空选择。

### 时间框架
- 15分钟、1小时、4小时级别都非常好用 (00:57)。

## Entry Rules / 入场

### 多头规则 (01:09)
1. 先找到一组 Camarilla 包含区间 (H3/L3之间)。
2. 阳K线上穿 Camarilla 上轨 (H3) 时，**收盘价也要落在上方** (01:14)。
3. Camarilla 包含区间要处在 LRS 指标上方 (01:17)。
4. 三条件全部满足后，这根阳K线即关键K线；收盘价即入场位置 (01:23)。

### 空头规则 (01:25)
与多头规则正相反：
1. Camarilla 包含区间。
2. 阴K线下穿 Camarilla 下轨 (L3) 时收盘价也落在下方。
3. Camarilla 包含区间处在 LRS 指标下方。

### 特殊情况：Camarilla 包含区间与 LRS 重合 (01:28)
- **做多规则简化**：只需阳K线上穿 Camarilla 上轨 + 收盘价也落在上方 (01:35)。
- **做空规则简化**：阴K线下穿 Camarilla 下轨 + 收盘价落在下方 (01:41)。

## Exit & Stop Loss / 出场止损
- **止损** (01:51)：可以设置到 Camarilla 上轨/下轨线；如距离近期波段高点很近，也可放宽止损幅度。
- **止盈**：分批止盈方式。

## Risk Management / 仓位
- 多周期/多品种通用，建议在自己经常做的品种和时间周期进行回测验证后再使用 (片头作者建议)。

## Examples / 实例
- 视频未给具体K线图实例，主要展示概念图。

## Caveats / 注意
- "运线"分型(隐含inside bar概念)是这种结构的另一种形式；策略本质是震荡突破。
- LRS 长度200用以判断大方向——逆 LRS 方向的突破不入场。
- Camarilla包含区间 = 当前周期波动完全被前一周期包住的 inside bar/inside range。

## My Notes
