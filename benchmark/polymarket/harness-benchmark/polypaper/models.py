from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class TraderTrade:
    wallet: str
    timestamp: int
    side: str
    asset: str
    condition_id: str
    price: float
    size: float
    title: str = ""
    slug: str = ""
    event_slug: str = ""
    outcome: str = ""
    category: str = ""
    tx_hash: str = ""

    @property
    def notional(self) -> float:
        return abs(self.price * self.size)

    @classmethod
    def from_api(cls, row: Dict[str, object]) -> "TraderTrade":
        return cls(
            wallet=str(row.get("proxyWallet") or row.get("wallet") or ""),
            timestamp=int(row["timestamp"]),
            side=str(row.get("side", "")).upper(),
            asset=str(row.get("asset", "")),
            condition_id=str(row.get("conditionId") or row.get("condition_id") or ""),
            price=float(row.get("price", 0.0) or 0.0),
            size=float(row.get("size", 0.0) or 0.0),
            title=str(row.get("title", "") or ""),
            slug=str(row.get("slug", "") or ""),
            event_slug=str(row.get("eventSlug") or row.get("event_slug") or ""),
            outcome=str(row.get("outcome", "") or ""),
            category=str(row.get("category", "") or ""),
            tx_hash=str(row.get("transactionHash") or row.get("tx_hash") or ""),
        )

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class Quote:
    asset: str
    timestamp: int
    bid: float
    ask: float
    source: str = "fixture"

    def __post_init__(self) -> None:
        if self.bid < 0 or self.ask < 0:
            raise ValueError("bid/ask must be non-negative")
        if self.bid > self.ask:
            raise ValueError("bid cannot exceed ask")

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2

    @classmethod
    def from_dict(cls, row: Dict[str, object]) -> "Quote":
        return cls(
            asset=str(row["asset"]),
            timestamp=int(row["timestamp"]),
            bid=float(row["bid"]),
            ask=float(row["ask"]),
            source=str(row.get("source", "fixture")),
        )

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class BookLevel:
    price: float
    size: float

    def __post_init__(self) -> None:
        if self.price <= 0 or self.price > 1:
            raise ValueError("book level price must be in (0, 1]")
        if self.size < 0:
            raise ValueError("book level size must be non-negative")

    @classmethod
    def from_dict(cls, row: Dict[str, object]) -> "BookLevel":
        return cls(price=float(row["price"]), size=float(row.get("size", 0.0) or 0.0))

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class OrderBook:
    asset: str
    timestamp: int
    bids: Tuple[BookLevel, ...]
    asks: Tuple[BookLevel, ...]
    source: str = "fixture"

    def __post_init__(self) -> None:
        if not self.asset:
            raise ValueError("order book asset is required")
        for level in self.bids + self.asks:
            if not isinstance(level, BookLevel):
                raise TypeError("bids and asks must contain BookLevel instances")

    @property
    def bid(self) -> float:
        return max((level.price for level in self.bids), default=0.0)

    @property
    def ask(self) -> float:
        return min((level.price for level in self.asks), default=0.0)

    def to_quote(self) -> Quote:
        return Quote(asset=self.asset, timestamp=self.timestamp, bid=self.bid, ask=self.ask, source=self.source)

    @classmethod
    def from_quote(cls, quote: Quote, depth_size: float = 1_000_000_000.0) -> "OrderBook":
        bids: Tuple[BookLevel, ...] = ()
        asks: Tuple[BookLevel, ...] = ()
        if quote.bid > 0:
            bids = (BookLevel(price=quote.bid, size=depth_size),)
        if quote.ask > 0:
            asks = (BookLevel(price=quote.ask, size=depth_size),)
        return cls(asset=quote.asset, timestamp=quote.timestamp, bids=bids, asks=asks, source=quote.source)

    @classmethod
    def from_dict(cls, row: Dict[str, object]) -> "OrderBook":
        return cls(
            asset=str(row["asset"]),
            timestamp=int(row["timestamp"]),
            bids=tuple(BookLevel.from_dict(level) for level in row.get("bids", [])),
            asks=tuple(BookLevel.from_dict(level) for level in row.get("asks", [])),
            source=str(row.get("source", "fixture")),
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "asset": self.asset,
            "timestamp": self.timestamp,
            "bids": [level.to_dict() for level in self.bids],
            "asks": [level.to_dict() for level in self.asks],
            "source": self.source,
        }


@dataclass(frozen=True)
class Signal:
    strategy: str
    timestamp: int
    side: str
    asset: str
    condition_id: str
    target_notional: float
    reason: str
    source_wallets: Tuple[str, ...] = ()
    source_tx_hashes: Tuple[str, ...] = ()
    execution_style: str = "taker"
    limit_price: Optional[float] = None

    def to_dict(self) -> Dict[str, object]:
        out = asdict(self)
        out["source_wallets"] = list(self.source_wallets)
        out["source_tx_hashes"] = list(self.source_tx_hashes)
        return out


@dataclass(frozen=True)
class StrategyDiagnostic:
    strategy: str
    timestamp: int
    asset: str
    condition_id: str
    reason: str
    score: Optional[float] = None
    title: str = ""
    outcome: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PaperOrder:
    order_id: str
    signal: Signal
    created_at: int
    eligible_at: int
    attempts: int = 0

    def to_dict(self) -> Dict[str, object]:
        return {
            "order_id": self.order_id,
            "created_at": self.created_at,
            "eligible_at": self.eligible_at,
            "attempts": self.attempts,
            "signal": self.signal.to_dict(),
        }


@dataclass(frozen=True)
class PaperFill:
    order_id: str
    strategy: str
    asset: str
    side: str
    status: str
    timestamp: int
    price: float
    shares: float
    notional: float
    reason: str = ""
    quote_timestamp: Optional[int] = None
    fee: float = 0.0
    taker: bool = True
    requested_notional: float = 0.0
    filled_notional: float = 0.0
    average_price: float = 0.0
    liquidity_source: str = ""

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class Portfolio:
    initial_cash: float
    cash: float = field(init=False)
    positions: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.cash = float(self.initial_cash)

    def buy(self, asset: str, shares: float, price: float, fee: float = 0.0) -> None:
        cost = shares * price + fee
        if cost > self.cash + 1e-9:
            raise ValueError("insufficient cash")
        self.cash -= cost
        self.positions[asset] = self.positions.get(asset, 0.0) + shares

    def sell(self, asset: str, shares: float, price: float, fee: float = 0.0) -> None:
        current = self.positions.get(asset, 0.0)
        if shares > current + 1e-9:
            raise ValueError("insufficient shares")
        self.cash += shares * price - fee
        remaining = current - shares
        if remaining <= 1e-9:
            self.positions.pop(asset, None)
        else:
            self.positions[asset] = remaining

    def equity(self, latest_quotes: Dict[str, Quote]) -> float:
        value = self.cash
        for asset, shares in self.positions.items():
            quote = latest_quotes.get(asset)
            if quote:
                value += shares * quote.bid
        return value


@dataclass
class StrategyResult:
    strategy: str
    orders: List[PaperOrder]
    fills: List[PaperFill]
    metrics: Dict[str, float]

    def to_dict(self) -> Dict[str, object]:
        return {
            "strategy": self.strategy,
            "orders": [o.to_dict() for o in self.orders],
            "fills": [f.to_dict() for f in self.fills],
            "metrics": self.metrics,
        }


@dataclass(frozen=True)
class MarketSnapshot:
    asset: str
    condition_id: str
    timestamp: int
    book: OrderBook
    title: str = ""
    slug: str = ""
    outcome: str = ""
    outcome_index: int = 0
    category: str = ""
    history_change_pct: Optional[float] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "asset": self.asset,
            "condition_id": self.condition_id,
            "timestamp": self.timestamp,
            "book": self.book.to_dict(),
            "title": self.title,
            "slug": self.slug,
            "outcome": self.outcome,
            "outcome_index": self.outcome_index,
            "category": self.category,
            "history_change_pct": self.history_change_pct,
        }
