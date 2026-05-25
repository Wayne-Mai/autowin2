from __future__ import annotations

import csv
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .engines import replay_backtest_engine
from .models import OrderBook, Quote, StrategyResult, TraderTrade
from .simulator import ConservativeFillModel, LatencyModel, MarketRules, PolymarketFeeModel, ReplaySimulator
from .strategies.replay import replay_strategies_for_suite


SCENARIO_FILL_KEYS = {
    "delay_seconds",
    "slippage_bps",
    "min_notional",
    "detection_delay_seconds",
    "polling_delay_seconds",
    "decision_delay_seconds",
    "execution_delay_seconds",
    "fee_rate",
    "fee_exponent",
    "tick_size",
    "min_order_size",
    "maker_fill_mode",
    "maker_queue_ahead_fraction",
    "maker_queue_decay",
    "maker_fill_probability",
    "maker_seed",
    "maker_max_order_age_attempts",
    "maker_cancel_on_price_move",
    "maker_adverse_fill_on_price_move",
    "maker_adverse_fill_fraction",
}


CONSERVATIVE_FILL_MODEL_KEYS = {
    "delay_seconds",
    "slippage_bps",
    "min_notional",
    "maker_fill_mode",
    "maker_queue_ahead_fraction",
    "maker_queue_decay",
    "maker_fill_probability",
    "maker_seed",
    "maker_max_order_age_attempts",
    "maker_cancel_on_price_move",
    "maker_adverse_fill_on_price_move",
    "maker_adverse_fill_fraction",
}


@dataclass(frozen=True)
class FillScenario:
    name: str
    description: str
    params: Dict[str, object]

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "params": dict(self.params),
        }


@dataclass(frozen=True)
class BenchmarkSuiteResult:
    fixture: str
    strategy_suite: str
    baseline_scenario: str
    scenarios: List[FillScenario]
    results_by_scenario: Dict[str, List[StrategyResult]]
    summary_rows: List[Dict[str, object]]

    def to_dict(self) -> Dict[str, object]:
        return {
            "fixture": self.fixture,
            "strategy_suite": self.strategy_suite,
            "baseline_scenario": self.baseline_scenario,
            "scenarios": [scenario.to_dict() for scenario in self.scenarios],
            "summary": self.summary_rows,
            "results_by_scenario": {
                scenario: [result.to_dict() for result in results]
                for scenario, results in self.results_by_scenario.items()
            },
        }


def load_fill_scenarios(path: str, selected_names: Sequence[str] = ()) -> List[FillScenario]:
    text = Path(path).read_text(encoding="utf-8")
    raw = _parse_scenario_text(text)
    names = [name for name in selected_names if name]
    if not names:
        names = list(raw)
    scenarios: List[FillScenario] = []
    for name in names:
        if name not in raw:
            raise ValueError(f"fill scenario not found: {name}")
        config = dict(raw[name])
        description = str(config.pop("description", ""))
        unknown = sorted(set(config) - SCENARIO_FILL_KEYS)
        if unknown:
            raise ValueError(f"unsupported keys in fill scenario {name}: {unknown}")
        scenarios.append(FillScenario(name=name, description=description, params=config))
    return scenarios


def run_replay_benchmark(
    fixture_path: str,
    scenarios: Sequence[FillScenario],
    strategy_suite: str = "default_with_maker",
    seed: int = 42,
    initial_cash: float = 10000.0,
    base_fill_params: Optional[Mapping[str, object]] = None,
    baseline_scenario: str = "",
) -> BenchmarkSuiteResult:
    trades, books = load_replay_fixture(fixture_path)
    results_by_scenario: Dict[str, List[StrategyResult]] = {}
    for scenario in scenarios:
        fill_model = fill_model_for_scenario(scenario, base_fill_params or {})
        strategies = replay_strategies_for_suite(trades, seed=seed, suite=strategy_suite)
        simulator = ReplaySimulator(
            strategies=strategies,
            fill_model=fill_model,
            initial_cash=initial_cash,
        )
        engine = replay_backtest_engine(
            simulator=simulator,
            trades=trades,
            quotes=books,
            name=f"replay:{scenario.name}",
        )
        results_by_scenario[scenario.name] = engine.run_once()
    baseline = baseline_scenario or (scenarios[0].name if scenarios else "")
    rows = benchmark_summary_rows(results_by_scenario, baseline_scenario=baseline)
    return BenchmarkSuiteResult(
        fixture=fixture_path,
        strategy_suite=strategy_suite,
        baseline_scenario=baseline,
        scenarios=list(scenarios),
        results_by_scenario=results_by_scenario,
        summary_rows=rows,
    )


def load_replay_fixture(fixture_path: str) -> Tuple[List[TraderTrade], List[object]]:
    data = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
    trades = [TraderTrade.from_api(row) for row in data["trades"]]
    books: List[object] = [Quote.from_dict(row) for row in data.get("quotes", [])]
    if data.get("order_books"):
        books = [OrderBook.from_dict(row) for row in data["order_books"]]
    return trades, books


def fill_model_for_scenario(
    scenario: FillScenario,
    base_fill_params: Mapping[str, object],
) -> ConservativeFillModel:
    params = dict(base_fill_params)
    params.update(scenario.params)
    delay_seconds = int(params.get("delay_seconds", 60))
    execution_delay = params.get("execution_delay_seconds", delay_seconds)
    latency = LatencyModel(
        detection_delay_seconds=int(params.get("detection_delay_seconds", 0)),
        polling_delay_seconds=int(params.get("polling_delay_seconds", 0)),
        decision_delay_seconds=int(params.get("decision_delay_seconds", 0)),
        execution_delay_seconds=int(execution_delay),
    )
    default_rules = MarketRules(
        tick_size=float(params.get("tick_size", 0.01)),
        min_order_size=float(params.get("min_order_size", 1.0)),
        fee_model=PolymarketFeeModel(
            fee_rate=float(params.get("fee_rate", 0.0)),
            exponent=float(params.get("fee_exponent", 1.0)),
            taker_only=True,
        ),
    )
    model_kwargs = {
        key: params[key]
        for key in CONSERVATIVE_FILL_MODEL_KEYS
        if key in params
    }
    return ConservativeFillModel(
        latency_model=latency,
        default_rules=default_rules,
        **model_kwargs,
    )


def benchmark_summary_rows(
    results_by_scenario: Mapping[str, Sequence[StrategyResult]],
    baseline_scenario: str,
) -> List[Dict[str, object]]:
    ranks_by_scenario: Dict[str, Dict[str, int]] = {}
    roi_by_scenario: Dict[str, Dict[str, float]] = {}
    for scenario, results in results_by_scenario.items():
        ranked = sorted(results, key=lambda result: result.metrics.get("roi", 0.0), reverse=True)
        ranks_by_scenario[scenario] = {
            result.strategy: index + 1
            for index, result in enumerate(ranked)
        }
        roi_by_scenario[scenario] = {
            result.strategy: float(result.metrics.get("roi", 0.0))
            for result in results
        }
    baseline_ranks = ranks_by_scenario.get(baseline_scenario, {})
    baseline_roi = roi_by_scenario.get(baseline_scenario, {})

    rows: List[Dict[str, object]] = []
    for scenario, results in results_by_scenario.items():
        for result in results:
            metrics = result.metrics
            orders = float(metrics.get("orders", 0.0))
            filled = float(metrics.get("filled_orders", 0.0))
            partial = float(metrics.get("partial_orders", 0.0))
            missed = float(metrics.get("missed_orders", 0.0))
            strategy = result.strategy
            rank = ranks_by_scenario.get(scenario, {}).get(strategy)
            base_rank = baseline_ranks.get(strategy)
            roi = float(metrics.get("roi", 0.0))
            base_roi = baseline_roi.get(strategy)
            rows.append(
                {
                    "scenario": scenario,
                    "strategy": strategy,
                    "rank": rank,
                    "baseline_rank": base_rank,
                    "rank_delta_vs_baseline": (
                        rank - base_rank
                        if rank is not None and base_rank is not None
                        else None
                    ),
                    "roi": roi,
                    "baseline_roi": base_roi,
                    "roi_delta_vs_baseline": (
                        roi - base_roi
                        if base_roi is not None
                        else None
                    ),
                    "pnl": float(metrics.get("pnl", 0.0)),
                    "orders": orders,
                    "filled_orders": filled,
                    "partial_orders": partial,
                    "missed_orders": missed,
                    "fill_rate": (filled + partial) / orders if orders else 0.0,
                    "partial_rate": partial / orders if orders else 0.0,
                    "miss_rate": missed / orders if orders else 0.0,
                    "turnover": float(metrics.get("turnover", 0.0)),
                    "fees": float(metrics.get("fees", 0.0)),
                    "max_drawdown": float(metrics.get("max_drawdown", 0.0)),
                }
            )
    return rows


def benchmark_markdown_report(result: BenchmarkSuiteResult) -> str:
    rows = [
        "# Polymarket Benchmark Suite Report",
        "",
        f"- Fixture: `{result.fixture}`",
        f"- Strategy suite: `{result.strategy_suite}`",
        f"- Baseline scenario: `{result.baseline_scenario}`",
        "",
        "| Scenario | Strategy | Rank | ROI | ROI Δ | Orders | Fill Rate | Partial | Miss | Turnover | Max DD |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in result.summary_rows:
        roi_delta = row["roi_delta_vs_baseline"]
        rows.append(
            "| {scenario} | {strategy} | {rank} | {roi:.4%} | {delta} | {orders:.0f} | "
            "{fill_rate:.2%} | {partial_rate:.2%} | {miss_rate:.2%} | {turnover:.4f} | {max_dd:.4%} |".format(
                scenario=row["scenario"],
                strategy=row["strategy"],
                rank=row["rank"],
                roi=row["roi"],
                delta="" if roi_delta is None else f"{roi_delta:.4%}",
                orders=row["orders"],
                fill_rate=row["fill_rate"],
                partial_rate=row["partial_rate"],
                miss_rate=row["miss_rate"],
                turnover=row["turnover"],
                max_dd=row["max_drawdown"],
            )
        )
    rows.extend(["", "## Fill Scenarios", ""])
    for scenario in result.scenarios:
        rows.append(f"### {scenario.name}")
        if scenario.description:
            rows.append(scenario.description)
        rows.append("")
        rows.append("```json")
        rows.append(json.dumps(scenario.params, indent=2, sort_keys=True))
        rows.append("```")
        rows.append("")
    return "\n".join(rows)


def write_benchmark_outputs(
    result: BenchmarkSuiteResult,
    json_out: str = "",
    csv_out: str = "",
    md_out: str = "",
    out_dir: str = "",
) -> None:
    if out_dir:
        base = Path(out_dir)
        base.mkdir(parents=True, exist_ok=True)
        json_out = json_out or str(base / "benchmark_summary.json")
        csv_out = csv_out or str(base / "benchmark_summary.csv")
        md_out = md_out or str(base / "benchmark_summary.md")
    if json_out:
        path = Path(json_out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    if csv_out:
        _write_summary_csv(result.summary_rows, csv_out)
    if md_out:
        path = Path(md_out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(benchmark_markdown_report(result), encoding="utf-8")


def _write_summary_csv(rows: Sequence[Mapping[str, object]], path: str) -> None:
    if not rows:
        return
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _parse_scenario_text(text: str) -> Dict[str, Dict[str, object]]:
    stripped = text.strip()
    if not stripped:
        return {}
    if stripped.startswith("{"):
        raw = json.loads(stripped)
        if "scenarios" in raw and isinstance(raw["scenarios"], dict):
            raw = raw["scenarios"]
        return {str(name): dict(config) for name, config in raw.items()}
    return _parse_simple_yaml_mapping(text)


def _parse_simple_yaml_mapping(text: str) -> Dict[str, Dict[str, object]]:
    scenarios: Dict[str, Dict[str, object]] = {}
    current: Optional[str] = None
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        content = line.strip()
        if indent == 0 and content.endswith(":"):
            current = content[:-1].strip()
            if not current:
                raise ValueError("empty scenario name")
            scenarios[current] = {}
            continue
        if current is None or indent < 2 or ":" not in content:
            raise ValueError(f"unsupported scenario config line: {raw_line!r}")
        key, value = content.split(":", 1)
        scenarios[current][key.strip()] = _parse_scalar(value.strip())
    return scenarios


def _parse_scalar(value: str) -> object:
    if value == "":
        return ""
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none"}:
        return None
    try:
        if any(char in value for char in (".", "e", "E")):
            return float(value)
        return int(value)
    except ValueError:
        return value


def parse_csv_names(raw: str) -> List[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]
