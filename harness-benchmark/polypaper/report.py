from __future__ import annotations

import json
from typing import Iterable, List

from .models import StrategyResult


def markdown_report(results: Iterable[StrategyResult]) -> str:
    rows: List[str] = [
        "# Polymarket Paper Replay Report",
        "",
        "| Strategy | PnL | ROI | Orders | Filled | Partial | Missed | Turnover | Fees | Max DD |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for result in results:
        m = result.metrics
        rows.append(
            "| {strategy} | {pnl:.4f} | {roi:.4%} | {orders:.0f} | {filled:.0f} | "
            "{partial:.0f} | {missed:.0f} | {turnover:.4f} | {fees:.4f} | {dd:.4%} |".format(
                strategy=result.strategy,
                pnl=m["pnl"],
                roi=m["roi"],
                orders=m["orders"],
                filled=m["filled_orders"],
                partial=m.get("partial_orders", 0.0),
                missed=m["missed_orders"],
                turnover=m["turnover"],
                fees=m.get("fees", 0.0),
                dd=m["max_drawdown"],
            )
        )
    rows.extend(
        [
            "",
            "## Raw Metrics",
            "",
            "```json",
            json.dumps([result.to_dict() for result in results], indent=2, sort_keys=True),
            "```",
            "",
        ]
    )
    return "\n".join(rows)
