from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Dict, Iterable

from .models import OrderBook, Quote, StrategyDiagnostic, TraderTrade


SCHEMA = """
CREATE TABLE IF NOT EXISTS leaderboard_snapshots (
  snapshot_ts INTEGER NOT NULL,
  category TEXT NOT NULL,
  time_period TEXT NOT NULL,
  order_by TEXT NOT NULL,
  rank INTEGER NOT NULL,
  wallet TEXT NOT NULL,
  username TEXT,
  volume REAL,
  pnl REAL,
  raw_json TEXT NOT NULL,
  PRIMARY KEY (snapshot_ts, category, time_period, order_by, rank, wallet)
);

CREATE TABLE IF NOT EXISTS trader_trades (
  wallet TEXT NOT NULL,
  timestamp INTEGER NOT NULL,
  side TEXT NOT NULL,
  asset TEXT NOT NULL,
  condition_id TEXT NOT NULL,
  size REAL NOT NULL,
  price REAL NOT NULL,
  title TEXT,
  slug TEXT,
  event_slug TEXT,
  outcome TEXT,
  category TEXT,
  tx_hash TEXT NOT NULL,
  raw_json TEXT NOT NULL,
  PRIMARY KEY (wallet, timestamp, tx_hash, asset, side)
);

CREATE TABLE IF NOT EXISTS price_snapshots (
  asset TEXT NOT NULL,
  timestamp INTEGER NOT NULL,
  bid REAL NOT NULL,
  ask REAL NOT NULL,
  source TEXT NOT NULL,
  raw_json TEXT NOT NULL,
  PRIMARY KEY (asset, timestamp, source)
);

CREATE TABLE IF NOT EXISTS order_book_snapshots (
  asset TEXT NOT NULL,
  timestamp INTEGER NOT NULL,
  source TEXT NOT NULL,
  bids_json TEXT NOT NULL,
  asks_json TEXT NOT NULL,
  raw_json TEXT NOT NULL,
  PRIMARY KEY (asset, timestamp, source)
);

CREATE TABLE IF NOT EXISTS signals (
  run_id TEXT NOT NULL,
  strategy TEXT NOT NULL,
  timestamp INTEGER NOT NULL,
  side TEXT NOT NULL,
  asset TEXT NOT NULL,
  condition_id TEXT NOT NULL,
  target_notional REAL NOT NULL,
  reason TEXT NOT NULL,
  raw_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS strategy_diagnostics (
  run_id TEXT NOT NULL,
  strategy TEXT NOT NULL,
  timestamp INTEGER NOT NULL,
  asset TEXT NOT NULL,
  condition_id TEXT NOT NULL,
  reason TEXT NOT NULL,
  score REAL,
  raw_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS paper_fills (
  run_id TEXT NOT NULL,
  strategy TEXT NOT NULL,
  order_id TEXT NOT NULL,
  timestamp INTEGER NOT NULL,
  side TEXT NOT NULL,
  asset TEXT NOT NULL,
  status TEXT NOT NULL,
  price REAL NOT NULL,
  shares REAL NOT NULL,
  notional REAL NOT NULL,
  reason TEXT NOT NULL,
  raw_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
  run_id TEXT NOT NULL,
  strategy TEXT NOT NULL,
  timestamp INTEGER NOT NULL,
  cash REAL NOT NULL,
  equity REAL NOT NULL,
  positions_json TEXT NOT NULL,
  raw_json TEXT NOT NULL,
  PRIMARY KEY (run_id, strategy, timestamp)
);

CREATE TABLE IF NOT EXISTS paper_runs (
  run_id TEXT PRIMARY KEY,
  mode TEXT NOT NULL,
  started_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  config_json TEXT NOT NULL,
  raw_json TEXT NOT NULL
);
"""


def connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def upsert_paper_run(
    conn: sqlite3.Connection,
    run_id: str,
    mode: str,
    config: Dict[str, object] = None,
    timestamp: int = None,
) -> None:
    now = int(time.time()) if timestamp is None else int(timestamp)
    config = dict(config or {})
    existing = conn.execute(
        "SELECT started_at, config_json FROM paper_runs WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    started_at = int(existing[0]) if existing else now
    if existing:
        try:
            merged_config = json.loads(existing[1] or "{}")
        except (TypeError, ValueError):
            merged_config = {}
        if not isinstance(merged_config, dict):
            merged_config = {}
        merged_config.update(config)
        config = merged_config
    raw = {
        "run_id": run_id,
        "mode": mode,
        "started_at": started_at,
        "updated_at": now,
        "config": config,
    }
    conn.execute(
        """
        INSERT OR REPLACE INTO paper_runs
        (run_id, mode, started_at, updated_at, config_json, raw_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            mode,
            started_at,
            now,
            json.dumps(config, sort_keys=True),
            json.dumps(raw, sort_keys=True),
        ),
    )
    conn.commit()


def insert_leaderboard(
    conn: sqlite3.Connection,
    rows: Iterable[Dict[str, object]],
    category: str,
    time_period: str,
    order_by: str,
    snapshot_ts: int = None,
) -> int:
    snapshot = int(time.time()) if snapshot_ts is None else snapshot_ts
    count = 0
    for row in rows:
        conn.execute(
            """
            INSERT OR REPLACE INTO leaderboard_snapshots
            (snapshot_ts, category, time_period, order_by, rank, wallet, username, volume, pnl, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot,
                category,
                time_period,
                order_by,
                int(row.get("rank", 0) or 0),
                str(row.get("proxyWallet", "")),
                str(row.get("userName", "") or row.get("name", "") or ""),
                float(row.get("vol", 0.0) or 0.0),
                float(row.get("pnl", 0.0) or row.get("amount", 0.0) or 0.0),
                json.dumps(row, sort_keys=True),
            ),
        )
        count += 1
    conn.commit()
    return count


def insert_trades(conn: sqlite3.Connection, rows: Iterable[Dict[str, object]]) -> int:
    count = 0
    for row in rows:
        trade = TraderTrade.from_api(row)
        conn.execute(
            """
            INSERT OR REPLACE INTO trader_trades
            (wallet, timestamp, side, asset, condition_id, size, price, title, slug, event_slug,
             outcome, category, tx_hash, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trade.wallet,
                trade.timestamp,
                trade.side,
                trade.asset,
                trade.condition_id,
                trade.size,
                trade.price,
                trade.title,
                trade.slug,
                trade.event_slug,
                trade.outcome,
                trade.category,
                trade.tx_hash,
                json.dumps(row, sort_keys=True),
            ),
        )
        count += 1
    conn.commit()
    return count


def insert_quotes(conn: sqlite3.Connection, quotes: Iterable[Quote]) -> int:
    count = 0
    for quote in quotes:
        conn.execute(
            """
            INSERT OR REPLACE INTO price_snapshots
            (asset, timestamp, bid, ask, source, raw_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                quote.asset,
                quote.timestamp,
                quote.bid,
                quote.ask,
                quote.source,
                json.dumps(quote.to_dict(), sort_keys=True),
            ),
        )
        count += 1
    conn.commit()
    return count


def insert_order_books(conn: sqlite3.Connection, books: Iterable[OrderBook]) -> int:
    count = 0
    for book in books:
        raw = book.to_dict()
        conn.execute(
            """
            INSERT OR REPLACE INTO order_book_snapshots
            (asset, timestamp, source, bids_json, asks_json, raw_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                book.asset,
                book.timestamp,
                book.source,
                json.dumps(raw["bids"], sort_keys=True),
                json.dumps(raw["asks"], sort_keys=True),
                json.dumps(raw, sort_keys=True),
            ),
        )
        count += 1
    conn.commit()
    return count


def insert_signal_rows(conn: sqlite3.Connection, run_id: str, signals: Iterable[object]) -> int:
    count = 0
    for signal in signals:
        raw = signal.to_dict()
        conn.execute(
            """
            INSERT INTO signals
            (run_id, strategy, timestamp, side, asset, condition_id, target_notional, reason, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                signal.strategy,
                signal.timestamp,
                signal.side,
                signal.asset,
                signal.condition_id,
                signal.target_notional,
                signal.reason,
                json.dumps(raw, sort_keys=True),
            ),
        )
        count += 1
    conn.commit()
    return count


def insert_strategy_diagnostics(
    conn: sqlite3.Connection,
    run_id: str,
    diagnostics: Iterable[StrategyDiagnostic],
) -> int:
    count = 0
    for diagnostic in diagnostics:
        raw = diagnostic.to_dict()
        conn.execute(
            """
            INSERT INTO strategy_diagnostics
            (run_id, strategy, timestamp, asset, condition_id, reason, score, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                diagnostic.strategy,
                diagnostic.timestamp,
                diagnostic.asset,
                diagnostic.condition_id,
                diagnostic.reason,
                diagnostic.score,
                json.dumps(raw, sort_keys=True),
            ),
        )
        count += 1
    conn.commit()
    return count


def insert_paper_fills(conn: sqlite3.Connection, run_id: str, fills: Iterable[object]) -> int:
    count = 0
    for fill in fills:
        raw = fill.to_dict()
        conn.execute(
            """
            INSERT INTO paper_fills
            (run_id, strategy, order_id, timestamp, side, asset, status, price, shares, notional, reason, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                fill.strategy,
                fill.order_id,
                fill.timestamp,
                fill.side,
                fill.asset,
                fill.status,
                fill.price,
                fill.shares,
                fill.notional,
                fill.reason,
                json.dumps(raw, sort_keys=True),
            ),
        )
        count += 1
    conn.commit()
    return count


def insert_portfolio_snapshot(
    conn: sqlite3.Connection,
    run_id: str,
    strategy: str,
    timestamp: int,
    cash: float,
    equity: float,
    positions: Dict[str, float],
) -> None:
    raw = {
        "run_id": run_id,
        "strategy": strategy,
        "timestamp": timestamp,
        "cash": cash,
        "equity": equity,
        "positions": positions,
    }
    conn.execute(
        """
        INSERT OR REPLACE INTO portfolio_snapshots
        (run_id, strategy, timestamp, cash, equity, positions_json, raw_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            strategy,
            timestamp,
            cash,
            equity,
            json.dumps(positions, sort_keys=True),
            json.dumps(raw, sort_keys=True),
        ),
    )
    conn.commit()
