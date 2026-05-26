---
strategy: 平均K线+双ATR波动率策略 (Heikin Ashi + Dual ATR)
trader: 频道编辑 (投机实验室)
source_video: https://www.youtube.com/watch?v=eYWma3ZXF1g
source_transcript: 【推荐必看！】平均k线和双波动率催生的交易利器！！#交易系统_#交易策略测试_#指标.md
asset_class: mixed
timeframe: intraday
claimed_returns: "外汇和加密货币两个市场连续200次交易回测"
claimed_win_rate: "把胜率和收益拿捏得死死的" (具体数值未给出)
claimed_payoff_ratio: 分批止盈在1:1出一半，剩余博取更高利润
backtest_period: 外汇 + 加密货币两个市场连续200次回测
indicators: [Smoothed Heiken Ashi - SamX, ATR(1), ATR(14 或 8 for BTC)]
tags: [forex, crypto, trend-following, Heikin-Ashi, ATR, volatility-breakout, scalping]
extracted: 2026-05-26
---

# 平均K线+双ATR波动率策略 — 频道编辑

## TL;DR
用 Smoothed Heiken Ashi 趋势判断 + 双 ATR (周期1 vs 周期14) 比对单根K线动能与14根均值动能，当单K动能超过均值动能且方向与平滑HA对侧不接触 → 关键K线收盘价入场 (00:36-04:00)。

## Setup / 形态

**三个免费 TradingView 指标设置**：

1. **Smoothed Heiken Ashi - SamX** (00:35-00:49)
   - 在指标搜索栏输入 "Smoothed Heiken Ashi - SamX"
   - 参数保持不变
   - 颜色自定义 (参考视频作者设置)

2. **ATR 1 (甲ATR)** (00:55-01:05)
   - 搜索 "Average True Range" 添加两次
   - 第一个 ATR 参数长度 = **1**
   - 代表"一根K线的波动幅度"
   - 后面统称甲 ATR

3. **ATR 2 (乙ATR)** (01:05-01:16)
   - 第二个 ATR 参数 = **14** (默认)
   - 如果交易**比特币这种短期波动幅度过大的品种**，可以将参数长度改成 **8**
   - 后面统称乙 ATR

## Entry Rules / 入场

### 多头规则 (01:21-01:48)
1. **阳K线**要处在平滑 Heikin Ashi **上方**，**不能有任何接触**
2. 这根阳K线所对应的**甲ATR数值要大于乙ATR数值** (当前K线波动幅度超过14根K线平均波动幅度 → 有资金入场动向)
3. 满足两个条件 → 这根阳K线 = **关键K线**
4. **入场位置 = 关键K线的收盘价**
5. **止损 = 关键K线的下方**

### 空头规则 (02:18-02:45)
1. **阴K线**要处在平滑 Heikin Ashi **下方**，不能有接触
2. 这根阴K线对应的**甲ATR数值要大于乙ATR数值**
3. 满足两个条件 → 这根阴K线 = 关键K线
4. **入场位置 = 关键K线的收盘价**
5. **止损 = 关键K线的上方**

### 同趋势重复入场规则 (02:04-02:18)
- 在一段趋势中，**只可以进行一次盈利的交易**
- 如果第一笔交易被止损，才可以在这段趋势中寻找**第二次入场机会**
- 直到两次交易结束为止，无论盈利与否都不在这段趋势进行**第三次交易**

## Exit & Stop Loss / 出场止损

**止盈方式** (01:50-01:58)：
- **分批止盈**
- 在风险回报比 **1:1 出一部分**
- 剩余部分拿住博取更高利润

**趋势结束信号** (01:58-02:04 / 02:45-02:52)：
- 多头：关键K线后有K线跌破平滑 Heikin Ashi → 趋势结束
- 空头：关键K线后有K线突破平滑 Heikin Ashi → 趋势结束

**止损位置**：
- 多 = 关键K线下方
- 空 = 关键K线上方

## Risk Management / 仓位
视频未给出具体仓位/资金管理百分比。

## Examples / 实例

**英镑美元 15分钟图表多头例子** (01:21-02:04)：
- 阳K位于平滑HA上方且无接触
- 甲ATR > 乙ATR
- 关键阳K收盘价入场 + 关键K线下方止损
- 1:1 出一半 + 剩余博取更高利润

**比特币美元 1小时图表多头例子** (02:52-03:30)：
- 把乙ATR参数长度改成 **8** (适应BTC波动)
- 阳K位于平滑HA上方且无接触
- 甲ATR > 乙ATR
- 关键阳K收盘价入场 + 关键K线下方止损 + 分批止盈

**比特币空头例子** (03:30-04:00)：
- 阴K线位于平滑HA下方且无接触
- 甲ATR > 乙ATR
- 关键阴K收盘价入场 + 关键K线上方止损
- 入场位置正处在趋势启动初期，下方足足有40%跌幅

## Caveats / 注意
- K线必须与平滑Heikin Ashi"不接触"，接触不算入场信号
- BTC 等高波动品种需调整乙ATR周期为 8
- 严格限制每段趋势内交易次数 (最多2次，第二次仅在第一次被止损后)

## My Notes
