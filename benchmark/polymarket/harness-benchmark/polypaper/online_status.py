from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from .verification import OnlineGoalVerification, TargetVerification, verify_online_goal


@dataclass(frozen=True)
class OnlineGoalStatus:
    verification: OnlineGoalVerification
    cycles_completed: int
    min_cycles_before_pass: int
    started_at: int
    updated_at: int
    snapshot_count: int
    signal_count: int
    fill_status_counts: Dict[str, int]
    top_diagnostics: List[Tuple[str, int]]
    top_strategies: List[TargetVerification]

    def to_dict(self) -> Dict[str, object]:
        data = asdict(self)
        data["verification"] = self.verification.to_dict()
        data["top_strategies"] = [item.to_dict() for item in self.top_strategies]
        data["top_diagnostics"] = [
            {"reason": reason, "count": count} for reason, count in self.top_diagnostics
        ]
        return data


def online_goal_status_from_path(
    db_path: str,
    run_id: str = "",
    strategies: Sequence[str] = (),
    target_roi: float = 0.10,
    require_flat: bool = True,
    min_runtime_seconds: int = 21600,
    min_strategies: int = 2,
    min_strategy_families: int = 1,
    require_online_mode: bool = True,
    top: int = 10,
) -> OnlineGoalStatus:
    path = Path(db_path)
    if not path.exists():
        raise ValueError(f"database does not exist: {db_path}")
    conn = sqlite3.connect(str(path))
    try:
        verification = verify_online_goal(
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
        return online_goal_status(conn, verification=verification, top=top)
    finally:
        conn.close()


def online_goal_status(
    conn: sqlite3.Connection,
    verification: OnlineGoalVerification,
    top: int = 10,
) -> OnlineGoalStatus:
    run_id = verification.run_id
    config, started_at, updated_at = _run_config(conn, run_id)
    cycles_completed = _cycles_completed(conn, run_id, config)
    min_cycles = int(config.get("min_cycles_before_pass", 0) or 0)
    fill_status_counts = {
        status: count
        for status, count in conn.execute(
            """
            SELECT status, COUNT(*)
            FROM paper_fills
            WHERE run_id = ?
            GROUP BY status
            ORDER BY status
            """,
            (run_id,),
        ).fetchall()
    }
    top_strategies = sorted(
        verification.strategy_results,
        key=lambda item: (item.passed, item.final_roi, item.max_roi),
        reverse=True,
    )[: max(1, int(top))]
    return OnlineGoalStatus(
        verification=verification,
        cycles_completed=cycles_completed,
        min_cycles_before_pass=min_cycles,
        started_at=started_at,
        updated_at=updated_at,
        snapshot_count=_count(conn, "portfolio_snapshots", run_id),
        signal_count=_count(conn, "signals", run_id),
        fill_status_counts=fill_status_counts,
        top_diagnostics=_top_diagnostics(conn, run_id, limit=max(1, int(top))),
        top_strategies=top_strategies,
    )


def format_online_goal_status(status: OnlineGoalStatus) -> str:
    verification = status.verification
    goal_status = "PASS" if verification.passed else "ACTIVE"
    fills_total = sum(status.fill_status_counts.values())
    filled = status.fill_status_counts.get("FILLED", 0)
    partial = status.fill_status_counts.get("PARTIAL", 0)
    missed = status.fill_status_counts.get("MISSED", 0)
    lines = [
        (
            f"{goal_status} run_id={verification.run_id} mode={verification.run_mode or 'unknown'} "
            f"runtime={verification.runtime_seconds}s/{verification.min_runtime_seconds}s "
            f"cycles={status.cycles_completed}/{status.min_cycles_before_pass} "
            f"passed_strategies={verification.passed_strategies}/{verification.total_strategies} "
            f"required_strategies={verification.required_strategies} "
            f"passed_families={verification.passed_strategy_families}/{verification.required_strategy_families} "
            f"target_roi={verification.target_roi:.4%} reason={verification.reason}"
        ),
        (
            f"counts snapshots={status.snapshot_count} signals={status.signal_count} "
            f"fills={fills_total} filled={filled} partial={partial} missed={missed}"
        ),
    ]
    if status.top_strategies:
        lines.append("top_strategies:")
        for item in status.top_strategies:
            lines.append(
                f"- {item.strategy}: final_roi={item.final_roi:.4%} max_roi={item.max_roi:.4%} "
                f"orders={item.orders} filled={item.filled_orders} flat={item.flat} reason={item.reason}"
            )
    if status.top_diagnostics:
        lines.append("top_diagnostics:")
        for reason, count in status.top_diagnostics:
            lines.append(f"- {reason}: {count}")
    return "\n".join(lines)


def _run_config(conn: sqlite3.Connection, run_id: str) -> tuple:
    row = conn.execute(
        "SELECT started_at, updated_at, config_json FROM paper_runs WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    if row is None:
        return {}, 0, 0
    try:
        config = json.loads(row[2] or "{}")
    except (TypeError, ValueError):
        config = {}
    if not isinstance(config, dict):
        config = {}
    return config, int(row[0] or 0), int(row[1] or 0)


def _cycles_completed(conn: sqlite3.Connection, run_id: str, config: Dict[str, object]) -> int:
    try:
        cycles = int(config.get("cycles_completed", 0) or 0)
    except (TypeError, ValueError):
        cycles = 0
    if cycles > 0:
        return cycles
    row = conn.execute(
        """
        SELECT COUNT(DISTINCT timestamp)
        FROM portfolio_snapshots
        WHERE run_id = ?
        """,
        (run_id,),
    ).fetchone()
    return max(0, int(row[0] if row else 0) - 1)


def _count(conn: sqlite3.Connection, table: str, run_id: str) -> int:
    row = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE run_id = ?", (run_id,)).fetchone()
    return int(row[0]) if row else 0


def _top_diagnostics(conn: sqlite3.Connection, run_id: str, limit: int) -> List[Tuple[str, int]]:
    rows = conn.execute(
        """
        SELECT reason, COUNT(*) AS count
        FROM strategy_diagnostics
        WHERE run_id = ?
        GROUP BY reason
        ORDER BY count DESC, reason
        LIMIT ?
        """,
        (run_id, limit),
    ).fetchall()
    return [(str(reason), int(count)) for reason, count in rows]
