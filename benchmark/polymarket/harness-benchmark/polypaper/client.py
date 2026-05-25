from __future__ import annotations

import json
import socket
import ssl
import time
from typing import Dict, Iterable, List, Mapping, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlunparse
from urllib.request import Request, urlopen


class ReadOnlyViolation(ValueError):
    """Raised when code attempts to use a non-public or trading-like endpoint."""


class PublicPolymarketClient:
    """Small public-data client with hard read-only guards.

    The class intentionally accepts only allowlisted public data endpoints. It
    is meant for academic data collection and benchmark fixtures, not execution.
    """

    USER_AGENT = "harness-benchmark/0.1 academic paper trading"
    MAX_BOOKS_PER_REQUEST = 500

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
    ALLOWED_POST_ENDPOINTS = {
        ("clob.polymarket.com", "/books"),
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

    RETRYABLE_HTTP_CODES = {408, 409, 425, 429}

    def __init__(self, timeout: int = 20, retries: int = 3, retry_backoff: float = 0.5):
        self.timeout = timeout
        self.retries = max(0, int(retries))
        self.retry_backoff = max(0.0, float(retry_backoff))

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
        offset: int = 0,
    ) -> List[Dict[str, object]]:
        params: Dict[str, object] = {
            "limit": limit,
            "closed": str(closed).lower(),
            "active": str(active).lower(),
            "ascending": str(ascending).lower(),
        }
        if order:
            params["order"] = order
        if offset:
            params["offset"] = offset
        return self._get_json("gamma-api.polymarket.com", "/markets", params)

    def markets_by_condition_id(
        self,
        condition_id: str,
        closed: Optional[bool] = None,
        active: Optional[bool] = None,
        limit: int = 10,
    ) -> List[Dict[str, object]]:
        params: Dict[str, object] = {
            "condition_ids": str(condition_id),
            "limit": limit,
        }
        if closed is not None:
            params["closed"] = str(closed).lower()
        if active is not None:
            params["active"] = str(active).lower()
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

    def books(self, token_ids: Iterable[str]) -> List[Dict[str, object]]:
        ids = [str(token_id) for token_id in token_ids if str(token_id)]
        books: List[Dict[str, object]] = []
        for offset in range(0, len(ids), self.MAX_BOOKS_PER_REQUEST):
            chunk = ids[offset : offset + self.MAX_BOOKS_PER_REQUEST]
            if not chunk:
                continue
            payload = [{"token_id": token_id} for token_id in chunk]
            batch = self._post_json("clob.polymarket.com", "/books", payload)
            if isinstance(batch, list):
                books.extend(item for item in batch if isinstance(item, dict))
        return books

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
        return self._urlopen_json(req)

    def _post_json(
        self,
        host: str,
        path: str,
        payload: object,
    ):
        self._validate_post(host, path)
        url = urlunparse(("https", host, path, "", "", ""))
        body = json.dumps(payload).encode("utf-8")
        req = Request(
            url,
            data=body,
            method="POST",
            headers={
                "User-Agent": self.USER_AGENT,
                "Content-Type": "application/json",
            },
        )
        return self._urlopen_json(req)

    def _urlopen_json(self, req: Request):
        last_error = None
        for attempt in range(self.retries + 1):
            try:
                with urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read())
            except HTTPError as exc:
                if not self._retryable_http_error(exc):
                    raise
                last_error = exc
            except (URLError, TimeoutError, socket.timeout, ssl.SSLError) as exc:
                last_error = exc
            if attempt < self.retries and self.retry_backoff > 0:
                time.sleep(self.retry_backoff * (2**attempt))
        if last_error is not None:
            raise last_error
        raise RuntimeError("request failed without an exception")

    @classmethod
    def _retryable_http_error(cls, exc: HTTPError) -> bool:
        return exc.code in cls.RETRYABLE_HTTP_CODES or 500 <= exc.code <= 599

    @classmethod
    def _validate_get(cls, host: str, path: str) -> None:
        key = (host, path)
        prefix_allowed = any(
            host == allowed_host and path.startswith(prefix)
            for allowed_host, prefix in cls.ALLOWED_PATH_PREFIXES
        )
        if key not in cls.ALLOWED_ENDPOINTS and not prefix_allowed:
            raise ReadOnlyViolation(f"endpoint is not allowlisted for public GET: {host}{path}")
        cls._reject_forbidden_path(host, path)

    @classmethod
    def _validate_post(cls, host: str, path: str) -> None:
        key = (host, path)
        if key not in cls.ALLOWED_POST_ENDPOINTS:
            raise ReadOnlyViolation(f"endpoint is not allowlisted for public POST: {host}{path}")
        cls._reject_forbidden_path(host, path)

    @classmethod
    def _reject_forbidden_path(cls, host: str, path: str) -> None:
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
