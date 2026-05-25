from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable, List, Optional, Sequence

from .engines import TradingEngine
from .models import StrategyResult
from .verification import TargetVerification, _strategy_family, verify_target_run


@dataclass(frozen=True)
class TargetRunUntilResult:
    run_id: str
    cycles_completed: int
    passed: bool
    best_verification: Optional[TargetVerification]
    latest_verifications: List[TargetVerification]
    results: List[StrategyResult]


def run_until_target(
    runner: TradingEngine,
    conn,
    run_id: str,
    strategy_names: Sequence[str],
    target_roi: float = 0.10,
    max_cycles: int = 1,
    interval_seconds: float = 0.0,
    min_cycles_before_pass: int = 0,
    min_elapsed_seconds_before_pass: float = 0.0,
    min_passing_strategies: int = 1,
    min_passing_families: int = 1,
    initial_cycles_completed: int = 0,
    initial_elapsed_seconds: float = 0.0,
    require_flat: bool = False,
    sleeper: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
    on_cycle: Optional[Callable[[int, List[TargetVerification], Optional[TargetVerification], bool], None]] = None,
) -> TargetRunUntilResult:
    best: Optional[TargetVerification] = None
    latest_verifications: List[TargetVerification] = []
    completed = max(0, int(initial_cycles_completed))
    started_at = clock() - max(0.0, float(initial_elapsed_seconds))
    for index in range(max_cycles):
        runner.run_once()
        completed = max(0, int(initial_cycles_completed)) + index + 1
        latest_verifications = _cycle_verifications(conn, run_id, strategy_names, target_roi, require_flat)
        best = _best_verification(latest_verifications, best)
        passed_verifications = [verification for verification in latest_verifications if verification.passed]
        passed = passed_verifications[0] if passed_verifications else None
        min_cycles_met = completed >= max(0, int(min_cycles_before_pass))
        min_elapsed_met = (clock() - started_at) >= max(0.0, float(min_elapsed_seconds_before_pass))
        min_strategies_met = len(passed_verifications) >= max(1, int(min_passing_strategies))
        min_families_met = len({_strategy_family(item.strategy) for item in passed_verifications}) >= max(
            1,
            int(min_passing_families),
        )
        cycle_passed = (
            passed is not None
            and min_strategies_met
            and min_families_met
            and min_cycles_met
            and min_elapsed_met
        )
        if on_cycle is not None:
            on_cycle(completed, latest_verifications, best, cycle_passed)
        if cycle_passed:
            return TargetRunUntilResult(
                run_id=run_id,
                cycles_completed=completed,
                passed=True,
                best_verification=best,
                latest_verifications=latest_verifications,
                results=runner.results(),
            )
        if interval_seconds > 0 and index < max_cycles - 1:
            sleeper(interval_seconds)
    return TargetRunUntilResult(
        run_id=run_id,
        cycles_completed=completed,
        passed=False,
        best_verification=best,
        latest_verifications=latest_verifications,
        results=runner.results(),
    )


def _cycle_verifications(
    conn,
    run_id: str,
    strategy_names: Sequence[str],
    target_roi: float,
    require_flat: bool,
) -> List[TargetVerification]:
    verifications: List[TargetVerification] = []
    for strategy in strategy_names:
        try:
            verifications.append(
                verify_target_run(
                    conn,
                    run_id=run_id,
                    strategy=strategy,
                    target_roi=target_roi,
                    require_flat=require_flat,
                )
            )
        except ValueError:
            continue
    return verifications


def _best_verification(
    latest_verifications: Sequence[TargetVerification],
    current_best: Optional[TargetVerification],
) -> Optional[TargetVerification]:
    best = current_best
    for verification in latest_verifications:
        if best is None or _verification_rank(verification) > _verification_rank(best):
            best = verification
    return best


def _verification_rank(verification: TargetVerification) -> tuple:
    invested = verification.open_position_value > 0 or verification.filled_orders > 0
    return (
        verification.passed,
        invested,
        -verification.roi_gap,
        verification.final_roi,
        -verification.required_position_gain_pct,
    )
