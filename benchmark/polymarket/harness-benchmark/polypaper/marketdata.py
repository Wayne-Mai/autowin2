from __future__ import annotations

import json
from typing import Dict, List, Optional

from .models import BookLevel, OrderBook, Quote


def quote_from_book(book: Dict[str, object], source: str = "clob_book") -> Optional[Quote]:
    order_book = order_book_from_clob(book, source=source)
    if order_book is None:
        return None
    return order_book.to_quote()


def order_book_from_clob(book: Dict[str, object], source: str = "clob_book") -> Optional[OrderBook]:
    bids = [BookLevel.from_dict(level) for level in book.get("bids", [])]
    asks = [BookLevel.from_dict(level) for level in book.get("asks", [])]
    if not bids or not asks:
        return None
    timestamp = int(book.get("timestamp", 0) or 0)
    if timestamp > 10_000_000_000:
        timestamp = timestamp // 1000
    return OrderBook(
        asset=str(book.get("asset_id") or book.get("asset") or ""),
        timestamp=timestamp,
        bids=tuple(sorted(bids, key=lambda level: level.price, reverse=True)),
        asks=tuple(sorted(asks, key=lambda level: level.price)),
        source=source,
    )


def token_ids_from_market(market: Dict[str, object]) -> List[str]:
    raw = market.get("clobTokenIds", [])
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return []
    else:
        parsed = raw
    return [str(token) for token in parsed if str(token)]
