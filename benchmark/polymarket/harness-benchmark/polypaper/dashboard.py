from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import sqlite3
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse


INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Polypaper Dashboard</title>
  <style>
    :root {
      --bg: #f6f7f2;
      --panel: #ffffff;
      --ink: #17201a;
      --muted: #617064;
      --line: #d8ded4;
      --green: #1f8a5b;
      --red: #b23b3b;
      --blue: #2f5f9e;
      --amber: #b7791f;
      --shadow: 0 1px 2px rgba(20, 31, 24, 0.08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--ink);
      letter-spacing: 0;
    }
    header {
      border-bottom: 1px solid var(--line);
      background: #fbfcf8;
      position: sticky;
      top: 0;
      z-index: 5;
    }
    .topbar {
      max-width: 1480px;
      margin: 0 auto;
      padding: 14px 18px;
      display: grid;
      grid-template-columns: 1fr auto auto;
      gap: 12px;
      align-items: center;
    }
    h1 {
      margin: 0;
      font-size: 18px;
      line-height: 1.2;
      font-weight: 750;
    }
    .sub {
      color: var(--muted);
      font-size: 12px;
      margin-top: 3px;
    }
    select, button {
      height: 34px;
      border: 1px solid var(--line);
      background: white;
      color: var(--ink);
      border-radius: 6px;
      padding: 0 10px;
      font-size: 13px;
    }
    button { cursor: pointer; }
    button:hover { border-color: #aab6ad; }
    main {
      max-width: 1480px;
      margin: 0 auto;
      padding: 18px;
      display: grid;
      gap: 16px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      min-width: 0;
    }
    .panel-head {
      padding: 12px 14px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 10px;
    }
    .panel-title {
      font-size: 13px;
      font-weight: 700;
      text-transform: uppercase;
      color: #344238;
    }
    .panel-note {
      font-size: 12px;
      color: var(--muted);
      white-space: nowrap;
    }
    .metric {
      padding: 14px;
    }
    .metric-label {
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 8px;
    }
    .metric-value {
      font-size: 24px;
      font-weight: 760;
      line-height: 1;
      font-variant-numeric: tabular-nums;
    }
    .metric-delta {
      margin-top: 8px;
      font-size: 12px;
      color: var(--muted);
    }
    .two-col {
      display: grid;
      grid-template-columns: minmax(0, 1.4fr) minmax(360px, 0.9fr);
      gap: 16px;
    }
    .chart-wrap {
      padding: 12px 14px 14px;
      height: 320px;
    }
    canvas {
      width: 100%;
      height: 100%;
      display: block;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }
    th, td {
      padding: 9px 10px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: middle;
      white-space: nowrap;
      font-variant-numeric: tabular-nums;
    }
    th {
      color: var(--muted);
      font-weight: 650;
      background: #fbfcf8;
    }
    td.wrap {
      white-space: normal;
      word-break: break-word;
      min-width: 180px;
    }
    .table-scroll {
      max-height: 420px;
      overflow: auto;
    }
    .pos { color: var(--green); }
    .neg { color: var(--red); }
    .badge {
      display: inline-flex;
      align-items: center;
      height: 22px;
      padding: 0 7px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: #f9faf7;
      color: #39453d;
      font-size: 11px;
      font-weight: 650;
    }
    .badge.buy { color: var(--green); border-color: #afd8c2; background: #f1fbf5; }
    .badge.sell { color: var(--red); border-color: #e2b9b9; background: #fff6f6; }
    .badge.fill { color: var(--blue); border-color: #b9c8e6; background: #f5f8ff; }
    .badge.pending { color: var(--amber); border-color: #e4c98b; background: #fff9e8; }
    .agent-row {
      display: grid;
      grid-template-columns: minmax(0, 1fr) repeat(5, minmax(86px, auto));
      gap: 8px;
      padding: 10px 14px;
      align-items: center;
      border-bottom: 1px solid var(--line);
      font-size: 12px;
    }
    .agent-name {
      font-weight: 700;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .agent-stat {
      text-align: right;
      font-variant-numeric: tabular-nums;
    }
    .status-line {
      display: flex;
      gap: 8px;
      align-items: center;
      color: var(--muted);
      font-size: 12px;
      flex-wrap: wrap;
    }
    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--green);
      display: inline-block;
    }
    @media (max-width: 980px) {
      .topbar { grid-template-columns: 1fr; }
      .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .two-col { grid-template-columns: 1fr; }
      .agent-row { grid-template-columns: minmax(0, 1fr) repeat(2, minmax(70px, auto)); }
      .hide-mobile { display: none; }
    }
  </style>
</head>
<body>
  <header>
    <div class="topbar">
      <div>
        <h1>Polypaper Agent Benchmark</h1>
        <div class="sub">Read-only Polymarket paper-run monitor</div>
      </div>
      <select id="runSelect" aria-label="Run"></select>
      <button id="refreshBtn">Refresh</button>
    </div>
  </header>
  <main>
    <section class="grid" id="metrics"></section>
    <section class="two-col">
      <div class="panel">
        <div class="panel-head">
                <div class="panel-title">Equity Curve</div>
          <div class="status-line"><span class="dot"></span><span id="lastUpdated">waiting</span></div>
        </div>
        <div class="chart-wrap"><canvas id="equityCanvas"></canvas></div>
      </div>
      <div class="panel">
        <div class="panel-head">
          <div class="panel-title">Agents</div>
          <div class="panel-note">PnL / orders / fills</div>
        </div>
        <div id="agents"></div>
      </div>
    </section>
    <section class="panel">
      <div class="panel-head">
        <div class="panel-title">Actions</div>
        <div class="panel-note">signals and fills</div>
      </div>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Time</th><th>Agent</th><th>Action</th><th>Side</th><th>Status</th>
              <th>Notional</th><th>Price</th><th>Fee</th><th class="wrap">Asset / Reason</th>
            </tr>
          </thead>
          <tbody id="actions"></tbody>
        </table>
      </div>
    </section>
  </main>
  <script>
    const state = { runId: null, colors: new Map() };
    const palette = ['#2f5f9e', '#1f8a5b', '#b7791f', '#8a4f9e', '#b23b3b', '#52796f'];

    function fmtMoney(v) {
      const value = Number(v || 0);
      return `${value < 0 ? '-' : ''}$${Math.abs(value).toFixed(4)}`;
    }
    function fmtPct(v) { return `${(Number(v || 0) * 100).toFixed(4)}%`; }
    function fmtNum(v, n = 2) { return Number(v || 0).toFixed(n); }
    function cls(v) { return Number(v || 0) < 0 ? 'neg' : Number(v || 0) > 0 ? 'pos' : ''; }
    function t(ts) { return ts ? new Date(Number(ts) * 1000).toLocaleTimeString() : ''; }
    function agentColor(name) {
      if (!state.colors.has(name)) state.colors.set(name, palette[state.colors.size % palette.length]);
      return state.colors.get(name);
    }
    async function getJson(url) {
      const res = await fetch(url, { cache: 'no-store' });
      if (!res.ok) throw new Error(`${res.status} ${url}`);
      return res.json();
    }
    async function loadRuns() {
      const data = await getJson('/api/runs');
      const select = document.getElementById('runSelect');
      const current = state.runId || select.value;
      select.innerHTML = '';
      data.runs.forEach(run => {
        const opt = document.createElement('option');
        opt.value = run.run_id;
        opt.textContent = `${run.run_id} · ${run.strategies} agents · ${run.last_ts || ''}`;
        select.appendChild(opt);
      });
      state.runId = current && data.runs.some(r => r.run_id === current) ? current : (data.runs[0]?.run_id || '');
      select.value = state.runId;
    }
    function renderMetrics(summary) {
      const totalPnL = summary.agents.reduce((s, a) => s + a.pnl, 0);
      const totalFees = summary.agents.reduce((s, a) => s + a.fees, 0);
      const orders = summary.agents.reduce((s, a) => s + a.orders, 0);
      const fills = summary.agents.reduce((s, a) => s + a.filled_orders + a.partial_orders, 0);
      const rows = [
        ['Total PnL', fmtMoney(totalPnL), `${summary.agents.length} agents`, cls(totalPnL)],
        ['Orders', fmtNum(orders, 0), `${fmtNum(fills, 0)} fills`, ''],
        ['Fees', fmtMoney(totalFees), 'taker fee model', totalFees > 0 ? 'neg' : ''],
        ['Snapshots', fmtNum(summary.snapshots || 0, 0), `Run ${summary.run_id || ''}`, '']
      ];
      document.getElementById('metrics').innerHTML = rows.map(([label, value, delta, klass]) => `
        <div class="panel metric">
          <div class="metric-label">${label}</div>
          <div class="metric-value ${klass}">${value}</div>
          <div class="metric-delta">${delta}</div>
        </div>`).join('');
    }
    function renderAgents(summary) {
      const rows = summary.agents.slice(0, 200).map(a => `
        <div class="agent-row">
          <div class="agent-name"><span style="color:${agentColor(a.strategy)}">●</span> ${a.strategy}</div>
          <div class="agent-stat ${cls(a.pnl)}">${fmtMoney(a.pnl)}</div>
          <div class="agent-stat hide-mobile">${fmtPct(a.roi)}</div>
          <div class="agent-stat">${fmtNum(a.orders, 0)} ord</div>
          <div class="agent-stat">${fmtNum(a.filled_orders + a.partial_orders, 0)} fill</div>
          <div class="agent-stat hide-mobile">${fmtMoney(a.equity)}</div>
        </div>`).join('');
      const overflow = summary.agents.length > 200
        ? `<div class="agent-row"><div class="agent-name">${summary.agents.length - 200} more agents hidden</div></div>`
        : '';
      document.getElementById('agents').innerHTML = rows + overflow || '<div class="agent-row"><div>No agents yet</div></div>';
    }
    function renderActions(actions) {
      document.getElementById('actions').innerHTML = actions.map(a => {
        const actionBadge = a.kind === 'fill' ? 'fill' : 'pending';
        const sideBadge = String(a.side || '').toLowerCase();
        return `<tr>
          <td>${t(a.timestamp)}</td>
          <td>${a.strategy}</td>
          <td><span class="badge ${actionBadge}">${a.kind}</span></td>
          <td><span class="badge ${sideBadge}">${a.side || ''}</span></td>
          <td>${a.status || ''}</td>
          <td>${fmtMoney(a.notional || a.target_notional)}</td>
          <td>${a.price ? fmtNum(a.price, 4) : ''}</td>
          <td>${a.fee ? fmtMoney(a.fee) : ''}</td>
          <td class="wrap">${short(a.asset)} · ${a.reason || ''}</td>
        </tr>`;
      }).join('');
    }
    function short(s) {
      s = String(s || '');
      return s.length > 18 ? `${s.slice(0, 8)}…${s.slice(-6)}` : s;
    }
    function drawChart(series) {
      const canvas = document.getElementById('equityCanvas');
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.max(1, Math.floor(rect.width * dpr));
      canvas.height = Math.max(1, Math.floor(rect.height * dpr));
      const ctx = canvas.getContext('2d');
      ctx.scale(dpr, dpr);
      ctx.clearRect(0, 0, rect.width, rect.height);
      const pad = { l: 46, r: 16, t: 14, b: 28 };
      const all = series.flatMap(s => s.points.map(p => p.equity));
      if (!all.length) {
        ctx.fillStyle = '#617064';
        ctx.fillText('No portfolio snapshots yet', 18, 28);
        return;
      }
      const min = Math.min(...all);
      const max = Math.max(...all);
      const span = Math.max(0.0001, max - min);
      const timestamps = series.flatMap(s => s.points.map(p => p.timestamp));
      const minT = Math.min(...timestamps), maxT = Math.max(...timestamps);
      const x = ts => pad.l + ((ts - minT) / Math.max(1, maxT - minT)) * (rect.width - pad.l - pad.r);
      const y = v => pad.t + (1 - ((v - min) / span)) * (rect.height - pad.t - pad.b);
      ctx.strokeStyle = '#d8ded4';
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (let i = 0; i < 4; i++) {
        const yy = pad.t + i * (rect.height - pad.t - pad.b) / 3;
        ctx.moveTo(pad.l, yy); ctx.lineTo(rect.width - pad.r, yy);
      }
      ctx.stroke();
      ctx.fillStyle = '#617064';
      ctx.font = '11px ui-sans-serif, system-ui';
      ctx.fillText(fmtMoney(max), 4, pad.t + 4);
      ctx.fillText(fmtMoney(min), 4, rect.height - pad.b + 4);
      series.forEach(s => {
        const pts = s.points;
        if (!pts.length) return;
        ctx.strokeStyle = agentColor(s.strategy);
        ctx.lineWidth = 2;
        ctx.beginPath();
        pts.forEach((p, i) => {
          const xx = x(p.timestamp), yy = y(p.equity);
          if (i === 0) ctx.moveTo(xx, yy); else ctx.lineTo(xx, yy);
        });
        ctx.stroke();
      });
    }
    async function refresh() {
      await loadRuns();
      if (!state.runId) return;
      const [summary, actions, equity] = await Promise.all([
        getJson(`/api/summary?run_id=${encodeURIComponent(state.runId)}`),
        getJson(`/api/actions?run_id=${encodeURIComponent(state.runId)}&limit=80`),
        getJson(`/api/equity?run_id=${encodeURIComponent(state.runId)}`)
      ]);
      renderMetrics(summary);
      renderAgents(summary);
      renderActions(actions.actions);
      drawChart(equity.series);
      document.getElementById('lastUpdated').textContent = `updated ${new Date().toLocaleTimeString()}`;
    }
    document.getElementById('refreshBtn').addEventListener('click', refresh);
    document.getElementById('runSelect').addEventListener('change', e => { state.runId = e.target.value; refresh(); });
    window.addEventListener('resize', () => state.runId && refresh());
    refresh().catch(err => {
      document.getElementById('lastUpdated').textContent = err.message;
      console.error(err);
    });
    setInterval(() => refresh().catch(console.error), 3000);
  </script>
</body>
</html>
"""


def serve_dashboard(db_path: str, host: str = "127.0.0.1", port: int = 8765) -> None:
    handler = _make_handler(db_path)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Dashboard running at http://{host}:{port}")
    server.serve_forever()


def _make_handler(db_path: str):
    class DashboardHandler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            parsed = urlparse(self.path)
            try:
                if parsed.path == "/":
                    self._send_html(INDEX_HTML)
                    return
                if parsed.path == "/api/runs":
                    self._send_json(_runs(db_path))
                    return
                if parsed.path == "/api/summary":
                    params = parse_qs(parsed.query)
                    run_id = _one(params, "run_id") or _latest_run_id(db_path)
                    self._send_json(_summary(db_path, run_id))
                    return
                if parsed.path == "/api/actions":
                    params = parse_qs(parsed.query)
                    run_id = _one(params, "run_id") or _latest_run_id(db_path)
                    limit = int(_one(params, "limit") or 80)
                    self._send_json({"run_id": run_id, "actions": _actions(db_path, run_id, limit)})
                    return
                if parsed.path == "/api/equity":
                    params = parse_qs(parsed.query)
                    run_id = _one(params, "run_id") or _latest_run_id(db_path)
                    self._send_json({"run_id": run_id, "series": _equity(db_path, run_id)})
                    return
                self.send_error(404)
            except Exception as exc:  # pragma: no cover - keeps dashboard debuggable.
                self._send_json({"error": str(exc)}, status=500)

        def log_message(self, fmt, *args):
            return

        def _send_html(self, body: str) -> None:
            data = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_json(self, obj, status: int = 200) -> None:
            data = json.dumps(obj, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return DashboardHandler


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _runs(db_path: str) -> Dict[str, List[Dict[str, object]]]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT run_id, MAX(timestamp) AS last_ts, COUNT(DISTINCT strategy) AS strategies
            FROM portfolio_snapshots
            GROUP BY run_id
            ORDER BY last_ts DESC
            LIMIT 100
            """
        ).fetchall()
    return {"runs": [dict(row) for row in rows]}


def _latest_run_id(db_path: str) -> str:
    runs = _runs(db_path)["runs"]
    return str(runs[0]["run_id"]) if runs else ""


def _summary(db_path: str, run_id: str) -> Dict[str, object]:
    if not run_id:
        return {"run_id": "", "agents": [], "snapshots": 0}
    with _connect(db_path) as conn:
        strategies = [
            row["strategy"]
            for row in conn.execute(
                "SELECT DISTINCT strategy FROM portfolio_snapshots WHERE run_id = ? ORDER BY strategy",
                (run_id,),
            )
        ]
        agents = []
        for strategy in strategies:
            first = conn.execute(
                """
                SELECT * FROM portfolio_snapshots
                WHERE run_id = ? AND strategy = ?
                ORDER BY timestamp ASC
                LIMIT 1
                """,
                (run_id, strategy),
            ).fetchone()
            latest = conn.execute(
                """
                SELECT * FROM portfolio_snapshots
                WHERE run_id = ? AND strategy = ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (run_id, strategy),
            ).fetchone()
            fill_rows = conn.execute(
                "SELECT raw_json FROM paper_fills WHERE run_id = ? AND strategy = ?",
                (run_id, strategy),
            ).fetchall()
            fills = [_loads(row["raw_json"]) for row in fill_rows]
            signal_count = conn.execute(
                "SELECT COUNT(*) FROM signals WHERE run_id = ? AND strategy = ?",
                (run_id, strategy),
            ).fetchone()[0]
            initial = float(first["equity"]) if first else 0.0
            equity = float(latest["equity"]) if latest else initial
            fill_like = [f for f in fills if f.get("status") in {"FILLED", "PARTIAL"}]
            agents.append(
                {
                    "strategy": strategy,
                    "initial_equity": initial,
                    "equity": equity,
                    "cash": float(latest["cash"]) if latest else 0.0,
                    "pnl": equity - initial,
                    "roi": (equity - initial) / initial if initial else 0.0,
                    "orders": float(signal_count),
                    "filled_orders": float(sum(1 for f in fills if f.get("status") == "FILLED")),
                    "partial_orders": float(sum(1 for f in fills if f.get("status") == "PARTIAL")),
                    "missed_orders": float(sum(1 for f in fills if f.get("status") == "MISSED")),
                    "turnover": sum(float(f.get("notional", 0.0) or 0.0) for f in fill_like),
                    "fees": sum(float(f.get("fee", 0.0) or 0.0) for f in fill_like),
                    "positions": _loads(latest["positions_json"]) if latest else {},
                }
            )
        agents = sorted(agents, key=lambda row: row["pnl"])
        snapshots = conn.execute(
            "SELECT COUNT(*) FROM portfolio_snapshots WHERE run_id = ?",
            (run_id,),
        ).fetchone()[0]
    return {"run_id": run_id, "agents": agents, "snapshots": snapshots}


def _actions(db_path: str, run_id: str, limit: int) -> List[Dict[str, object]]:
    if not run_id:
        return []
    with _connect(db_path) as conn:
        signals = [
            {
                "kind": "signal",
                "run_id": row["run_id"],
                "strategy": row["strategy"],
                "timestamp": row["timestamp"],
                "side": row["side"],
                "asset": row["asset"],
                "target_notional": row["target_notional"],
                "reason": row["reason"],
                "status": "PENDING",
                "price": 0.0,
                "fee": 0.0,
            }
            for row in conn.execute(
                """
                SELECT * FROM signals
                WHERE run_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (run_id, limit),
            )
        ]
        fills = []
        for row in conn.execute(
            """
            SELECT * FROM paper_fills
            WHERE run_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (run_id, limit),
        ):
            raw = _loads(row["raw_json"])
            fills.append(
                {
                    "kind": "fill",
                    "run_id": row["run_id"],
                    "strategy": row["strategy"],
                    "timestamp": row["timestamp"],
                    "side": row["side"],
                    "asset": row["asset"],
                    "notional": row["notional"],
                    "price": row["price"],
                    "fee": raw.get("fee", 0.0),
                    "reason": row["reason"],
                    "status": row["status"],
                }
            )
    return sorted(signals + fills, key=lambda row: row["timestamp"], reverse=True)[:limit]


def _equity(db_path: str, run_id: str) -> List[Dict[str, object]]:
    if not run_id:
        return []
    with _connect(db_path) as conn:
        strategies = [
            row["strategy"]
            for row in conn.execute(
                "SELECT DISTINCT strategy FROM portfolio_snapshots WHERE run_id = ? ORDER BY strategy",
                (run_id,),
            )
        ]
        if len(strategies) > 80:
            summary = _summary(db_path, run_id)
            strategies = [agent["strategy"] for agent in summary["agents"][:80]]
        series = []
        for strategy in strategies:
            points = [
                {"timestamp": row["timestamp"], "equity": row["equity"], "cash": row["cash"]}
                for row in conn.execute(
                    """
                    SELECT timestamp, equity, cash
                    FROM portfolio_snapshots
                    WHERE run_id = ? AND strategy = ?
                    ORDER BY timestamp ASC
                    """,
                    (run_id, strategy),
                )
            ]
            series.append({"strategy": strategy, "points": points})
    return series


def _one(params: Dict[str, List[str]], key: str) -> Optional[str]:
    values = params.get(key) or []
    return values[0] if values else None


def _loads(raw: str):
    try:
        return json.loads(raw)
    except Exception:
        return {}
