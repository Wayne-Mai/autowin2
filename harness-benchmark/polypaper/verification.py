from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import sqlite3
from pathlib import Path
from typing import Dict, Optional


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


def _loads_positions(raw: str) -> Dict[str, float]:
    data = json.loads(raw or "{}")
    if not isinstance(data, dict):
        return {}
    return {str(key): float(value) for key, value in data.items()}


def _count(conn: sqlite3.Connection, query: str, run_id: str, strategy: str) -> int:
    row = conn.execute(query, (run_id, strategy)).fetchone()
    return int(row[0]) if row else 0
