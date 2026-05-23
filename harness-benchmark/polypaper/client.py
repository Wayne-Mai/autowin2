from __future__ import annotations

import json
from typing import Dict, Iterable, List, Mapping, Optional, Tuple
from urllib.parse import urlencode, urlunparse
from urllib.request import Request, urlopen


class ReadOnlyViolation(ValueError):
    """Raised when code attempts to use a non-public or trading-like endpoint."""


class PublicPolymarketClient:
    """Small public-data client with hard read-only guards.

    The class intentionally exposes no POST/PUT/DELETE methods and accepts only
    allowlisted public GET endpoints. It is meant for academic data collection
    and benchmark fixtures, not execution.
    """

    USER_AGENT = "harness-benchmark/0.1 academic paper trading"

    ALLOWED_ENDPOINTS = {
        ("data-api.polymarket.com", "/v1/leaderboard"),
        ("data-api.polymarket.com", "/trades"),
        ("data-api.polymarket.com", "/activity"),
        ("data-api.polymarket.com", "/positions"),
        ("gamma-api.polymarket.com", "/markets"),
        ("gamma-api.polymarket.com", "/markets/keyset"),
        ("clob.polymarket.com", "/prices-history"),
        ("clob.polymarket.com", "/book"),
    }
    ALLOWED_PATH_PREFIXES = {
        ("clob.polymarket.com", "/clob-markets/"),
    }

    FORBIDDEN_PATH_PARTS = (
        "order",
        "orders",
        "cancel",
        "auth",
        "api-key",
        "apikey",
        "signature",
        "login",
        "allowance",
    )

    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    def leaderboard(
        self,
        category: str = "OVERALL",
        time_period: str = "ALL",
        order_by: str = "PNL",
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, object]]:
        return self._get_json(
            "data-api.polymarket.com",
            "/v1/leaderboard",
            {
                "category": category,
                "timePeriod": time_period,
                "orderBy": order_by,
                "limit": limit,
                "offset": offset,
            },
        )

    def user_trades(
        self,
        wallet: str,
        limit: int = 500,
        offset: int = 0,
    ) -> List[Dict[str, object]]:
        return self._get_json(
            "data-api.polymarket.com",
            "/trades",
            {"user": wallet, "limit": limit, "offset": offset},
        )

    def user_activity(
        self,
        wallet: str,
        limit: int = 500,
        offset: int = 0,
        activity_type: Optional[str] = None,
    ) -> List[Dict[str, object]]:
        params: Dict[str, object] = {"user": wallet, "limit": limit, "offset": offset}
        if activity_type:
            params["type"] = activity_type
        return self._get_json("data-api.polymarket.com", "/activity", params)

    def user_positions(
        self,
        wallet: str,
        limit: int = 500,
        offset: int = 0,
    ) -> List[Dict[str, object]]:
        return self._get_json(
            "data-api.polymarket.com",
            "/positions",
            {"user": wallet, "limit": limit, "offset": offset},
        )

    def markets(
        self,
        limit: int = 100,
        closed: bool = False,
        active: bool = True,
        order: Optional[str] = "volume_24hr",
        ascending: bool = False,
    ) -> List[Dict[str, object]]:
        params: Dict[str, object] = {
            "limit": limit,
            "closed": str(closed).lower(),
            "active": str(active).lower(),
            "ascending": str(ascending).lower(),
        }
        if order:
            params["order"] = order
        return self._get_json("gamma-api.polymarket.com", "/markets", params)

    def price_history(
        self,
        token_id: str,
        start_ts: int,
        end_ts: int,
        interval: str = "1h",
        fidelity: Optional[int] = None,
    ) -> Dict[str, object]:
        params: Dict[str, object] = {
            "market": token_id,
            "startTs": start_ts,
            "endTs": end_ts,
            "interval": interval,
        }
        if fidelity is not None:
            params["fidelity"] = fidelity
        return self._get_json("clob.polymarket.com", "/prices-history", params)

    def book(self, token_id: str) -> Dict[str, object]:
        return self._get_json("clob.polymarket.com", "/book", {"token_id": token_id})

    def clob_market_info(self, condition_id: str) -> Dict[str, object]:
        return self._get_json("clob.polymarket.com", f"/clob-markets/{condition_id}", {})

    def paged(
        self,
        method_name: str,
        page_size: int = 500,
        max_items: Optional[int] = None,
        **kwargs: object,
    ) -> Iterable[Dict[str, object]]:
        method = getattr(self, method_name)
        offset = 0
        yielded = 0
        while True:
            limit = page_size
            if max_items is not None:
                limit = min(limit, max_items - yielded)
                if limit <= 0:
                    return
            batch = method(limit=limit, offset=offset, **kwargs)
            if not batch:
                return
            for row in batch:
                yield row
                yielded += 1
                if max_items is not None and yielded >= max_items:
                    return
            if len(batch) < limit:
                return
            offset += limit

    def _get_json(
        self,
        host: str,
        path: str,
        params: Optional[Mapping[str, object]] = None,
    ):
        self._validate_get(host, path)
        query = urlencode(params or {})
        url = urlunparse(("https", host, path, "", query, ""))
        req = Request(url, method="GET", headers={"User-Agent": self.USER_AGENT})
        with urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read())

    @classmethod
    def _validate_get(cls, host: str, path: str) -> None:
        key = (host, path)
        prefix_allowed = any(
            host == allowed_host and path.startswith(prefix)
            for allowed_host, prefix in cls.ALLOWED_PATH_PREFIXES
        )
        if key not in cls.ALLOWED_ENDPOINTS and not prefix_allowed:
            raise ReadOnlyViolation(f"endpoint is not allowlisted for public GET: {host}{path}")
        lower_path = path.lower().strip("/")
        parts = tuple(part for part in lower_path.replace("_", "-").split("/") if part)
        for forbidden in cls.FORBIDDEN_PATH_PARTS:
            if forbidden in parts:
                raise ReadOnlyViolation(f"trading/auth endpoint is forbidden: {host}{path}")


def leaderboard_pages(
    client: PublicPolymarketClient,
    limit: int,
    category: str = "OVERALL",
    time_period: str = "ALL",
    order_by: str = "PNL",
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    page_size = 50
    offset = 0
    while len(rows) < limit:
        batch = client.leaderboard(
            category=category,
            time_period=time_period,
            order_by=order_by,
            limit=min(page_size, limit - len(rows)),
            offset=offset,
        )
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return rows
