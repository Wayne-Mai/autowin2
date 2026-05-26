---
strategy: 永续合约 + 交割合约 吃费率套利
trader: 频道编辑
source_video: https://www.youtube.com/watch?v=B0x1pJlECdQ
source_transcript: 套利策略，半神半木夏的吃费率大法，年收益居然远超膏利贷_#交易策略_#套利_#okx_#策略广场.md
asset_class: crypto
timeframe: position
claimed_returns: 未提及
claimed_win_rate: 无风险套利
claimed_payoff_ratio: 未提及
backtest_period: 未提及
indicators: [资金费率, 永续合约, 交割合约, OKX组合套利]
tags: [套利, 费率套利, 交割合约, OKX]
extracted: 2026-05-26
---

# 永续合约 + 交割合约 吃费率套利 — Speculation Lab

## TL;DR
把币币杠杆换成交割合约，省掉杠杆利息费用。在永续做空 + 交割合约做多形成对冲，吃永续的费率。

## Setup / 形态
- 仅在永续费率为正时使用，方向相反时镜像
- 适合所有大市值币种
- 与"永续 + 币币杠杆"相比，省掉了杠杆的有息贷款利息

## Entry Rules / 入场
1. 在 OKX 策略广场 → 组合套利 → 套利下单
2. 视频示例：LTC/USDT
3. 左腿选择 3 倍永续合约**做空**
4. 右腿选择 3 倍当周交割合约**做多**
5. 入场方式：市价
6. 两腿数量都输入相同（如 1000）

## Exit & Stop Loss / 出场止损
- 当周交割合约交割时间较短，必须在交割前移仓（05:53–05:56）
- 不移仓 → 交割合约自动平仓 → 套利结构被打破，剩余永续裸单
- 资金费率每天 3 次结算，长期持有可长期收取

## Risk Management / 仓位
- 双腿仓位相等 → 多空盈亏相互抵消
- 必须时刻关注交割合约的剩余天数，临近交割前进行移仓
- 杠杆 3 倍是兼顾仓位放大与保证金安全的常用选择

## Examples / 实例
- LTC/USDT：永续 3 倍空 + 当周 3 倍多，行情上涨/下跌都不影响套利收益

## Caveats / 注意
- 必须移仓，否则交割后变裸单
- 同样要选费率稳定的大市值币种
- 比起永续 + 现货，多了一个移仓成本和操作复杂度
- 该方法是"网格策略 + 马丁格尔策略 + 定投策略 + 套利"系列策略广场上成熟工具之一

## My Notes

