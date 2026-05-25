from __future__ import annotations

from typing import List

from .base import PaperStrategy
from .baseline import NoTradePaperStrategy, RandomMarketTakerStrategy
from .target import target_strategy_from_args


def default_paper_strategies(args) -> List[PaperStrategy]:
    strategies: List[PaperStrategy] = [NoTradePaperStrategy()]
    strategies.extend(
        target_strategy_from_args(
            args,
            name=(
                "paper_target_profit_10pct"
                if args.target_profit_agents == 1
                else f"paper_target_profit_{index + 1:04d}"
            ),
        )
        for index in range(args.target_profit_agents)
    )
    strategies.extend(
        RandomMarketTakerStrategy(
            seed=args.seed + index,
            trade_probability=args.trade_probability,
            max_notional=args.max_notional,
            name=(
                "paper_random_market_taker"
                if args.random_agents == 1
                else f"paper_random_market_taker_{index + 1:04d}"
            ),
        )
        for index in range(args.random_agents)
    )
    return strategies
