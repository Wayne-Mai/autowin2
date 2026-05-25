from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import re
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Sequence


@dataclass(frozen=True)
class TargetVerification:
    run_id: str
    strategy: str
    target_roi: float
    target_equity: float
    initial_equity: float
    final_equity: float
    max_equity: float
    equity_gap: float
    final_roi: float
    max_roi: float
    roi_gap: float
    open_position_value: float
    required_position_gain_pct: float
    orders: int
    filled_orders: int
    final_positions: Dict[str, float]
    flat: bool
    passed: bool
    reason: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class OnlineGoalVerification:
    run_id: str
    target_roi: float
    min_runtime_seconds: int
    runtime_seconds: int
    required_strategies: int
    passed_strategies: int
    required_strategy_families: int
    passed_strategy_families: int
    total_strategies: int
    run_mode: str
    online_mode: bool
    flat_required: bool
    passed: bool
    reason: str
    strategy_results: List[TargetVerification]

    def to_dict(self) -> Dict[str, object]:
        data = asdict(self)
        data["strategy_results"] = [item.to_dict() for item in self.strategy_results]
        return data


def verify_target_run_from_path(
    db_path: str,
    run_id: str = "",
    strategy: str = "paper_target_profit_10pct",
    target_roi: float = 0.10,
    require_flat: bool = False,
) -> TargetVerification:
    path = Path(db_path)
    if not path.exists():
        raise ValueError(f"database does not exist: {db_path}")
    conn = sqlite3.connect(str(path))
    try:
        return verify_target_run(
            conn,
            run_id=run_id,
            strategy=strategy,
            target_roi=target_roi,
            require_flat=require_flat,
        )
    finally:
        conn.close()


def verify_online_goal_from_path(
    db_path: str,
    run_id: str = "",
    strategies: Sequence[str] = (),
    target_roi: float = 0.10,
    require_flat: bool = True,
    min_runtime_seconds: int = 21600,
    min_strategies: int = 2,
    min_strategy_families: int = 1,
    require_online_mode: bool = True,
) -> OnlineGoalVerification:
    path = Path(db_path)
    if not path.exists():
        raise ValueError(f"database does not exist: {db_path}")
    conn = sqlite3.connect(str(path))
    try:
        return verify_online_goal(
            conn,
            run_id=run_id,
            strategies=strategies,
            target_roi=target_roi,
            require_flat=require_flat,
            min_runtime_seconds=min_runtime_seconds,
            min_strategies=min_strategies,
            min_strategy_families=min_strategy_families,
            require_online_mode=require_online_mode,
        )
    finally:
        conn.close()


def verify_target_run(
    conn: sqlite3.Connection,
    run_id: str = "",
    strategy: str = "paper_target_profit_10pct",
    target_roi: float = 0.10,
    require_flat: bool = False,
) -> TargetVerification:
    selected_run_id = run_id or _latest_run_id(conn)
    if not selected_run_id:
        raise ValueError("no paper runs found in portfolio_snapshots")

    rows = conn.execute(
        """
        SELECT timestamp, equity, cash, positions_json
        FROM portfolio_snapshots
        WHERE run_id = ? AND strategy = ?
        ORDER BY timestamp
        """,
        (selected_run_id, strategy),
    ).fetchall()
    if not rows:
        raise ValueError(f"no portfolio snapshots for run_id={selected_run_id!r} strategy={strategy!r}")

    initial_equity = float(rows[0][1])
    final_equity = float(rows[-1][1])
    final_cash = float(rows[-1][2])
    max_equity = max(float(row[1]) for row in rows)
    final_positions = _loads_positions(rows[-1][3])
    flat = all(abs(value) <= 1e-9 for value in final_positions.values())
    final_roi = (final_equity - initial_equity) / initial_equity if initial_equity else 0.0
    max_roi = (max_equity - initial_equity) / initial_equity if initial_equity else 0.0
    target_equity = initial_equity * (1.0 + target_roi)
    equity_gap = max(0.0, target_equity - final_equity)
    roi_gap = max(0.0, target_roi - final_roi)
    open_position_value = max(0.0, final_equity - final_cash)
    required_position_value = max(0.0, target_equity - final_cash)
    required_position_gain_pct = (
        max(0.0, (required_position_value - open_position_value) / open_position_value)
        if open_position_value > 0
        else 0.0
    )
    orders = _count(
        conn,
        "SELECT COUNT(*) FROM signals WHERE run_id = ? AND strategy = ?",
        selected_run_id,
        strategy,
    )
    filled_orders = _count(
        conn,
        """
        SELECT COUNT(*)
        FROM paper_fills
        WHERE run_id = ? AND strategy = ? AND status IN ('FILLED', 'PARTIAL')
        """,
        selected_run_id,
        strategy,
    )
    passed = final_roi >= target_roi and (flat or not require_flat)
    if passed:
        reason = "target_roi_reached"
    elif final_roi < target_roi:
        reason = "final_roi_below_target"
    else:
        reason = "final_position_not_flat"

    return TargetVerification(
        run_id=selected_run_id,
        strategy=strategy,
        target_roi=target_roi,
        target_equity=target_equity,
        initial_equity=initial_equity,
        final_equity=final_equity,
        max_equity=max_equity,
        equity_gap=equity_gap,
        final_roi=final_roi,
        max_roi=max_roi,
        roi_gap=roi_gap,
        open_position_value=open_position_value,
        required_position_gain_pct=required_position_gain_pct,
        orders=orders,
        filled_orders=filled_orders,
        final_positions=final_positions,
        flat=flat,
        passed=passed,
        reason=reason,
    )


def verify_online_goal(
    conn: sqlite3.Connection,
    run_id: str = "",
    strategies: Sequence[str] = (),
    target_roi: float = 0.10,
    require_flat: bool = True,
    min_runtime_seconds: int = 21600,
    min_strategies: int = 2,
    min_strategy_families: int = 1,
    require_online_mode: bool = True,
) -> OnlineGoalVerification:
    selected_run_id = run_id or _latest_run_id(conn)
    if not selected_run_id:
        raise ValueError("no paper runs found in portfolio_snapshots")
    strategy_names = list(strategies) or _strategies_for_run(conn, selected_run_id)
    if not strategy_names:
        raise ValueError(f"no strategies for run_id={selected_run_id!r}")
    strategy_results: List[TargetVerification] = []
    for strategy in strategy_names:
        try:
            strategy_results.append(
                verify_target_run(
                    conn,
                    run_id=selected_run_id,
                    strategy=strategy,
                    target_roi=target_roi,
                    require_flat=require_flat,
                )
            )
        except ValueError:
            continue
    if not strategy_results:
        raise ValueError(f"no verifiable strategy snapshots for run_id={selected_run_id!r}")
    run_mode = _run_mode(conn, selected_run_id)
    runtime_seconds = _online_runtime_seconds(conn, selected_run_id, run_mode)
    online_mode = run_mode in {"online_target", "online_sweep_target", "online_paper"}
    passed_results = [item for item in strategy_results if item.passed]
    passed_count = len(passed_results)
    passed_family_count = len({_strategy_family(item.strategy) for item in passed_results})
    required_runtime = max(0, int(min_runtime_seconds))
    required_strategies = max(1, int(min_strategies))
    required_families = max(1, int(min_strategy_families))
    if require_online_mode and not online_mode:
        passed = False
        reason = "run_mode_not_online"
    elif runtime_seconds < required_runtime:
        passed = False
        reason = "runtime_below_minimum"
    elif passed_count < required_strategies:
        passed = False
        reason = "too_few_strategies_passed"
    elif passed_family_count < required_families:
        passed = False
        reason = "too_few_strategy_families_passed"
    else:
        passed = True
        reason = "online_goal_reached"
    return OnlineGoalVerification(
        run_id=selected_run_id,
        target_roi=target_roi,
        min_runtime_seconds=required_runtime,
        runtime_seconds=runtime_seconds,
        required_strategies=required_strategies,
        passed_strategies=passed_count,
        required_strategy_families=required_families,
        passed_strategy_families=passed_family_count,
        total_strategies=len(strategy_results),
        run_mode=run_mode,
        online_mode=online_mode,
        flat_required=require_flat,
        passed=passed,
        reason=reason,
        strategy_results=strategy_results,
    )


def _latest_run_id(conn: sqlite3.Connection) -> Optional[str]:
    row = conn.execute(
        """
        SELECT run_id
        FROM portfolio_snapshots
        GROUP BY run_id
        ORDER BY MAX(timestamp) DESC
        LIMIT 1
        """
    ).fetchone()
    return str(row[0]) if row else None


def _strategies_for_run(conn: sqlite3.Connection, run_id: str) -> List[str]:
    rows = conn.execute(
        """
        SELECT DISTINCT strategy
        FROM portfolio_snapshots
        WHERE run_id = ?
        ORDER BY strategy
        """,
        (run_id,),
    ).fetchall()
    return [str(row[0]) for row in rows]


def _run_timestamp_span(conn: sqlite3.Connection, run_id: str) -> int:
    row = conn.execute(
        """
        SELECT MIN(timestamp), MAX(timestamp)
        FROM portfolio_snapshots
        WHERE run_id = ?
        """,
        (run_id,),
    ).fetchone()
    if row is None or row[0] is None or row[1] is None:
        return 0
    return max(0, int(row[1]) - int(row[0]))


def _online_runtime_seconds(conn: sqlite3.Connection, run_id: str, run_mode: str) -> int:
    if run_mode in {"online_target", "online_sweep_target", "online_paper"}:
        row = conn.execute(
            """
            SELECT started_at, updated_at
            FROM paper_runs
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()
        if row is not None and row[0] is not None and row[1] is not None:
            elapsed = max(0, int(row[1]) - int(row[0]))
            if elapsed > 0:
                return elapsed
    return _run_timestamp_span(conn, run_id)


def _run_mode(conn: sqlite3.Connection, run_id: str) -> str:
    try:
        row = conn.execute(
            "SELECT mode FROM paper_runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
    except sqlite3.OperationalError:
        return ""
    return str(row[0]) if row else ""


def _strategy_family(strategy: str) -> str:
    name = str(strategy)
    if name.startswith("paper_target_"):
        name = name[len("paper_target_") :]
    match = re.match(r"(.+?)_grid_\d+$", name)
    if match:
        return match.group(1)
    match = re.match(r"(.+?)_goal$", name)
    if match:
        return match.group(1)
    return name


def _loads_positions(raw: str) -> Dict[str, float]:
    data = json.loads(raw or "{}")
    if not isinstance(data, dict):
        return {}
    return {str(key): float(value) for key, value in data.items()}


def _count(conn: sqlite3.Connection, query: str, run_id: str, strategy: str) -> int:
    row = conn.execute(query, (run_id, strategy)).fetchone()
    return int(row[0]) if row else 0
