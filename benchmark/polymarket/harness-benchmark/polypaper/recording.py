from __future__ import annotations

from dataclasses import dataclass
import gzip
import json
import time
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence

from .models import MarketSnapshot, OrderBook
from .paper import CollectionResult, MarketDataCollector
from .simulator import MarketRules, PolymarketFeeModel


@dataclass(frozen=True)
class RecordedCollection:
    cycle: int
    collected_at: int
    snapshots: List[MarketSnapshot]
    rules_by_asset: Dict[str, MarketRules]

    def to_dict(self) -> Dict[str, object]:
        return {
            "cycle": self.cycle,
            "collected_at": self.collected_at,
            "snapshots": [snapshot.to_dict() for snapshot in self.snapshots],
            "rules_by_asset": {
                asset: market_rules_to_dict(rules)
                for asset, rules in self.rules_by_asset.items()
            },
        }

    @classmethod
    def from_dict(cls, row: Mapping[str, object]) -> "RecordedCollection":
        raw_rules = row.get("rules_by_asset") or {}
        if not isinstance(raw_rules, dict):
            raw_rules = {}
        return cls(
            cycle=int(row.get("cycle", 0) or 0),
            collected_at=int(row.get("collected_at", 0) or 0),
            snapshots=[
                market_snapshot_from_dict(item)
                for item in row.get("snapshots", [])
                if isinstance(item, dict)
            ],
            rules_by_asset={
                str(asset): market_rules_from_dict(rules)
                for asset, rules in raw_rules.items()
                if isinstance(rules, dict)
            },
        )


@dataclass(frozen=True)
class MarketRecording:
    recording_id: str
    created_at: int
    metadata: Dict[str, object]
    collections: List[RecordedCollection]

    def to_dict(self) -> Dict[str, object]:
        return {
            "recording_id": self.recording_id,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
            "collections": [collection.to_dict() for collection in self.collections],
        }

    @classmethod
    def from_dict(cls, row: Mapping[str, object]) -> "MarketRecording":
        return cls(
            recording_id=str(row.get("recording_id", "")),
            created_at=int(row.get("created_at", 0) or 0),
            metadata=dict(row.get("metadata", {}) or {}),
            collections=[
                RecordedCollection.from_dict(item)
                for item in row.get("collections", [])
                if isinstance(item, dict)
            ],
        )


class RecordedMarketDataCollector:
    def __init__(
        self,
        recording: MarketRecording,
        repeat_last: bool = False,
    ):
        self.recording = recording
        self.repeat_last = repeat_last
        self.collection_count = 0
        self.pinned_assets = set()
        self.market_limit = 0
        self.max_assets = 0

    def collect(self) -> CollectionResult:
        if not self.recording.collections:
            self.collection_count += 1
            return CollectionResult(snapshots=[], rules_by_asset={})
        index = self.collection_count
        self.collection_count += 1
        if index >= len(self.recording.collections):
            if not self.repeat_last:
                return CollectionResult(snapshots=[], rules_by_asset={})
            index = len(self.recording.collections) - 1
        collection = self.recording.collections[index]
        return CollectionResult(
            snapshots=collection.snapshots,
            rules_by_asset=collection.rules_by_asset,
        )


def record_market_snapshots(
    collector: MarketDataCollector,
    cycles: int,
    interval_seconds: float = 0.0,
    recording_id: str = "",
    metadata: Optional[Mapping[str, object]] = None,
    sleeper=time.sleep,
    clock=time.time,
) -> MarketRecording:
    collections: List[RecordedCollection] = []
    for index in range(cycles):
        collected_at = int(clock())
        result = collector.collect()
        collections.append(
            RecordedCollection(
                cycle=index + 1,
                collected_at=collected_at,
                snapshots=result.snapshots,
                rules_by_asset=result.rules_by_asset,
            )
        )
        if interval_seconds > 0 and index < cycles - 1:
            sleeper(interval_seconds)
    return MarketRecording(
        recording_id=recording_id or f"recording-{int(clock())}",
        created_at=int(clock()),
        metadata=dict(metadata or {}),
        collections=collections,
    )


def save_recording(recording: MarketRecording, path: str) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(recording.to_dict(), indent=2, sort_keys=True)
    if output.suffix == ".gz":
        with gzip.open(output, "wt", encoding="utf-8") as handle:
            handle.write(payload)
        return
    output.write_text(payload, encoding="utf-8")


def load_recording(path: str) -> MarketRecording:
    input_path = Path(path)
    if input_path.suffix == ".gz":
        with gzip.open(input_path, "rt", encoding="utf-8") as handle:
            data = json.load(handle)
    else:
        data = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("recording file must contain a JSON object")
    return MarketRecording.from_dict(data)


def market_snapshot_from_dict(row: Mapping[str, object]) -> MarketSnapshot:
    return MarketSnapshot(
        asset=str(row["asset"]),
        condition_id=str(row.get("condition_id", "")),
        timestamp=int(row["timestamp"]),
        book=OrderBook.from_dict(row["book"]),
        title=str(row.get("title", "")),
        slug=str(row.get("slug", "")),
        outcome=str(row.get("outcome", "")),
        outcome_index=int(row.get("outcome_index", 0) or 0),
        category=str(row.get("category", "")),
        history_change_pct=(
            None
            if row.get("history_change_pct") is None
            else float(row.get("history_change_pct"))
        ),
    )


def market_rules_to_dict(rules: MarketRules) -> Dict[str, object]:
    return {
        "tick_size": rules.tick_size,
        "min_order_size": rules.min_order_size,
        "minimum_order_age_seconds": rules.minimum_order_age_seconds,
        "fee_model": {
            "fee_rate": rules.fee_model.fee_rate,
            "exponent": rules.fee_model.exponent,
            "taker_only": rules.fee_model.taker_only,
            "maker_rebate_rate": rules.fee_model.maker_rebate_rate,
            "min_fee": rules.fee_model.min_fee,
            "precision": rules.fee_model.precision,
        },
    }


def market_rules_from_dict(row: Mapping[str, object]) -> MarketRules:
    fee = row.get("fee_model") or {}
    if not isinstance(fee, dict):
        fee = {}
    return MarketRules(
        tick_size=float(row.get("tick_size", 0.01) or 0.01),
        min_order_size=float(row.get("min_order_size", 1.0) or 1.0),
        minimum_order_age_seconds=int(row.get("minimum_order_age_seconds", 0) or 0),
        fee_model=PolymarketFeeModel(
            fee_rate=float(fee.get("fee_rate", 0.0) or 0.0),
            exponent=float(fee.get("exponent", 1.0) or 1.0),
            taker_only=bool(fee.get("taker_only", True)),
            maker_rebate_rate=float(fee.get("maker_rebate_rate", 0.0) or 0.0),
            min_fee=float(fee.get("min_fee", 0.00001) or 0.00001),
            precision=int(fee.get("precision", 5) or 5),
        ),
    )
