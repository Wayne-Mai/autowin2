from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable, List, Optional, Sequence

from .models import StrategyResult
from .verification import TargetVerification, verify_target_run


@dataclass(frozen=True)
class TargetRunUntilResult:
    run_id: str
    cycles_completed: int
    passed: bool
    best_verification: Optional[TargetVerification]
    results: List[StrategyResult]


def run_until_target(
    runner,
    conn,
    run_id: str,
    strategy_names: Sequence[str],
    target_roi: float = 0.10,
    max_cycles: int = 1,
    interval_seconds: float = 0.0,
    require_flat: bool = False,
    sleeper: Callable[[float], None] = time.sleep,
) -> TargetRunUntilResult:
    best: Optional[TargetVerification] = None
    completed = 0
    for index in range(max_cycles):
        runner.run_once()
        completed = index + 1
        best = _best_verification(conn, run_id, strategy_names, target_roi, require_flat, best)
        if best is not None and best.passed:
            return TargetRunUntilResult(
                run_id=run_id,
                cycles_completed=completed,
                passed=True,
                best_verification=best,
                results=runner.results(),
            )
        if interval_seconds > 0 and index < max_cycles - 1:
            sleeper(interval_seconds)
    return TargetRunUntilResult(
        run_id=run_id,
        cycles_completed=completed,
        passed=False,
        best_verification=best,
        results=runner.results(),
    )


def _best_verification(
    conn,
    run_id: str,
    strategy_names: Sequence[str],
    target_roi: float,
    require_flat: bool,
    current_best: Optional[TargetVerification],
) -> Optional[TargetVerification]:
    best = current_best
    for strategy in strategy_names:
        verification = verify_target_run(
            conn,
            run_id=run_id,
            strategy=strategy,
            target_roi=target_roi,
            require_flat=require_flat,
        )
        if best is None or verification.final_roi > best.final_roi:
            best = verification
        if verification.passed:
            return verification
    return best
