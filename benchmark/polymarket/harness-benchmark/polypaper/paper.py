from __future__ import annotations

from dataclasses import dataclass, field, replace
import json
import re
import time
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .marketdata import order_book_from_clob, token_ids_from_market
from .models import (
    MarketSnapshot,
    OrderBook,
    PaperFill,
    PaperOrder,
    Portfolio,
    Quote,
    Signal,
    StrategyDiagnostic,
    StrategyResult,
)
from .simulator import ConservativeFillModel, MarketRules, residual_maker_order_after_partial
from .storage import (
    insert_order_books,
    insert_paper_fills,
    insert_portfolio_snapshot,
    insert_quotes,
    insert_signal_rows,
    insert_strategy_diagnostics,
)
from .strategies.paper import PaperStrategy


@dataclass
class _PaperState:
    strategy: PaperStrategy
    portfolio: Portfolio
    orders: List[PaperOrder] = field(default_factory=list)
    pending: List[PaperOrder] = field(default_factory=list)
    fills: List[PaperFill] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)


@dataclass(frozen=True)
class CollectionResult:
    snapshots: List[MarketSnapshot]
    rules_by_asset: Dict[str, MarketRules]


@dataclass(frozen=True)
class _CandidateToken:
    market: Dict[str, object]
    rules: MarketRules
    token_id: str
    condition_id: str
    outcome: str
    outcome_index: int


@dataclass(frozen=True)
class _AssetMetadata:
    asset: str
    condition_id: str
    outcome: str = ""
    outcome_index: int = 0
    title: str = ""
    slug: str = ""


@dataclass(frozen=True)
class _Settlement:
    condition_id: str
    prices_by_asset: Dict[str, float]


class MarketDataCollector:
    def __init__(
        self,
        client,
        market_limit: int = 5,
        max_assets: int = 10,
        market_order: str = "volume_24hr",
        market_ascending: bool = False,
        market_pages: int = 1,
        market_active: bool = True,
        history_window_seconds: int = 0,
        history_interval: str = "1h",
        history_min_change_pct: Optional[float] = None,
        history_candidate_assets: int = 0,
        history_cache_seconds: int = 60,
        history_min_bid_price: Optional[float] = None,
        history_max_bid_price: Optional[float] = None,
        history_max_spread_pct: Optional[float] = None,
        history_max_queries: int = 0,
        market_filter_keywords: Optional[Sequence[str]] = None,
        market_prefer_keywords: Optional[Sequence[str]] = None,
        pinned_assets: Optional[Sequence[str]] = None,
        clock=None,
    ):
        self.client = client
        self.market_limit = market_limit
        self.max_assets = max_assets
        self.market_order = market_order
        self.market_ascending = market_ascending
        self.market_pages = max(1, int(market_pages))
        self.market_active = market_active
        self.history_window_seconds = history_window_seconds
        self.history_interval = history_interval
        self.history_min_change_pct = history_min_change_pct
        self.history_candidate_assets = history_candidate_assets
        self.history_cache_seconds = history_cache_seconds
        self.history_min_bid_price = history_min_bid_price
        self.history_max_bid_price = history_max_bid_price
        self.history_max_spread_pct = history_max_spread_pct
        self.history_max_queries = history_max_queries
        self.market_filter_keywords = _normalize_keywords(market_filter_keywords)
        self.market_prefer_keywords = _normalize_keywords(market_prefer_keywords)
        self.pinned_assets = {asset for asset in (pinned_assets or []) if asset}
        self.clock = clock or time.time
        self._history_change_cache: Dict[Tuple[str, str, int], Tuple[int, Optional[float]]] = {}
        self._snapshot_by_asset: Dict[str, MarketSnapshot] = {}
        self._rules_by_asset_cache: Dict[str, MarketRules] = {}
        self.collection_count = 0

    def collect(self) -> CollectionResult:
        self.collection_count += 1
        snapshots: List[MarketSnapshot] = []
        rules_by_asset: Dict[str, MarketRules] = {}
        candidate_limit = self._candidate_asset_limit()
        if candidate_limit <= 0:
            snapshots = self._with_pinned_snapshots([], [])
            rules_by_asset = self._rules_for_snapshots(snapshots, rules_by_asset)
            return CollectionResult(snapshots=snapshots, rules_by_asset=rules_by_asset)
        markets = self._markets()
        markets = self._select_markets(markets)
        candidates = self._candidate_tokens(markets)
        cursor = 0
        while cursor < len(candidates) and len(snapshots) < candidate_limit:
            remaining = candidate_limit - len(snapshots)
            chunk = candidates[cursor : cursor + min(500, remaining)]
            cursor += len(chunk)
            books_by_token = self._books_for_tokens(candidate.token_id for candidate in chunk)
            for candidate in chunk:
                if len(snapshots) >= candidate_limit:
                    break
                raw_book = books_by_token.get(candidate.token_id)
                if raw_book is None:
                    continue
                book = order_book_from_clob(raw_book, source="paper_run")
                if book is None:
                    continue
                snapshot = self._snapshot_from_candidate(candidate, book)
                rules_by_asset[book.asset] = candidate.rules
                self._snapshot_by_asset[book.asset] = snapshot
                self._rules_by_asset_cache[book.asset] = candidate.rules
                snapshots.append(snapshot)
        candidate_snapshots = snapshots
        snapshots = self._apply_history_filter(candidate_snapshots)
        snapshots = self._with_pinned_snapshots(snapshots, candidate_snapshots)
        rules_by_asset = self._rules_for_snapshots(snapshots, rules_by_asset)
        return CollectionResult(snapshots=snapshots, rules_by_asset=rules_by_asset)

    def _markets(self) -> List[Dict[str, object]]:
        page_size = max(1, min(int(self.market_limit), 100))
        markets: List[Dict[str, object]] = []
        seen = set()
        for page in range(self.market_pages):
            offset = page * page_size
            kwargs = {
                "limit": page_size,
                "closed": False,
                "active": self.market_active,
                "order": self.market_order,
                "ascending": self.market_ascending,
            }
            if offset:
                kwargs["offset"] = offset
            page_markets = self.client.markets(**kwargs)
            for market in page_markets:
                key = _market_identity(market)
                if key in seen:
                    continue
                seen.add(key)
                markets.append(market)
            if len(page_markets) < page_size:
                break
        return markets

    def _candidate_tokens(self, markets: Sequence[Dict[str, object]]) -> List[_CandidateToken]:
        candidates: List[_CandidateToken] = []
        for market in markets:
            rules = MarketRules.from_gamma_market(market)
            token_ids = token_ids_from_market(market)
            outcomes = _parse_json_list(market.get("outcomes"))
            condition_id = str(market.get("conditionId", ""))
            for outcome_index, token_id in enumerate(token_ids):
                candidates.append(
                    _CandidateToken(
                        market=market,
                        rules=rules,
                        token_id=token_id,
                        condition_id=condition_id,
                        outcome=str(outcomes[outcome_index]) if outcome_index < len(outcomes) else "",
                        outcome_index=outcome_index,
                    )
                )
        return candidates

    def _select_markets(self, markets: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
        selected = list(markets)
        if self.market_filter_keywords:
            selected = [
                market
                for market in selected
                if _market_matches_keywords(market, self.market_filter_keywords)
            ]
        if self.market_prefer_keywords:
            selected = [
                market
                for _, market in sorted(
                    enumerate(selected),
                    key=lambda item: (
                        not _market_matches_keywords(item[1], self.market_prefer_keywords),
                        _short_crypto_interval_priority(item[1], now=int(self.clock())),
                        item[0],
                    ),
                )
            ]
        return selected

    def _books_for_tokens(self, token_ids: Iterable[str]) -> Dict[str, Dict[str, object]]:
        ids = [str(token_id) for token_id in token_ids if str(token_id)]
        if not ids:
            return {}
        batch_books = getattr(self.client, "books", None)
        if callable(batch_books):
            try:
                return _books_by_requested_token(ids, batch_books(ids))
            except Exception:
                pass
        return self._books_for_tokens_individually(ids)

    def _books_for_tokens_individually(self, token_ids: Sequence[str]) -> Dict[str, Dict[str, object]]:
        books_by_token: Dict[str, Dict[str, object]] = {}
        for token_id in token_ids:
            try:
                raw_book = self.client.book(token_id)
            except Exception:
                continue
            if isinstance(raw_book, dict):
                books_by_token[token_id] = raw_book
        return books_by_token

    def _snapshot_from_candidate(self, candidate: _CandidateToken, book: OrderBook) -> MarketSnapshot:
        market = candidate.market
        return MarketSnapshot(
            asset=book.asset,
            condition_id=candidate.condition_id,
            timestamp=book.timestamp,
            book=book,
            title=str(market.get("question", "") or ""),
            slug=str(market.get("slug", "") or ""),
            outcome=candidate.outcome,
            outcome_index=candidate.outcome_index,
            category=str(market.get("category", "") or market.get("categorySlug", "") or ""),
        )

    def _candidate_asset_limit(self) -> int:
        if self.max_assets <= 0:
            return 0
        if self.history_window_seconds > 0 and self.history_candidate_assets > self.max_assets:
            return self.history_candidate_assets
        return self.max_assets

    def _rules_for_snapshots(
        self,
        snapshots: Sequence[MarketSnapshot],
        current_rules: Dict[str, MarketRules],
    ) -> Dict[str, MarketRules]:
        rules_by_asset: Dict[str, MarketRules] = {}
        for snapshot in snapshots:
            if snapshot.asset in current_rules:
                rules_by_asset[snapshot.asset] = current_rules[snapshot.asset]
            elif snapshot.asset in self._rules_by_asset_cache:
                rules_by_asset[snapshot.asset] = self._rules_by_asset_cache[snapshot.asset]
        return rules_by_asset

    def _apply_history_filter(self, snapshots: Sequence[MarketSnapshot]) -> List[MarketSnapshot]:
        if self.history_window_seconds <= 0:
            return list(snapshots[: self.max_assets])
        end_ts = int(self.clock())
        start_ts = max(0, end_ts - self.history_window_seconds)
        scored = []
        history_queries = 0
        for snapshot in snapshots:
            if not self._history_prefilter_allows(snapshot):
                continue
            if self.history_max_queries > 0 and history_queries >= self.history_max_queries:
                break
            history_queries += 1
            change = self._history_change_pct(snapshot.asset, start_ts=start_ts, end_ts=end_ts)
            if change is None:
                continue
            if self.history_min_change_pct is not None and change < self.history_min_change_pct:
                continue
            scored.append((change, replace(snapshot, history_change_pct=change)))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [snapshot for _, snapshot in scored[: self.max_assets]]

    def _history_prefilter_allows(self, snapshot: MarketSnapshot) -> bool:
        bid = snapshot.book.bid
        ask = snapshot.book.ask
        if self.history_min_bid_price is not None and bid < self.history_min_bid_price:
            return False
        if self.history_max_bid_price is not None and bid > self.history_max_bid_price:
            return False
        if self.history_max_spread_pct is not None:
            if ask <= 0:
                return False
            spread_pct = (ask - bid) / ask
            if spread_pct > self.history_max_spread_pct:
                return False
        return True

    def _with_pinned_snapshots(
        self,
        snapshots: Sequence[MarketSnapshot],
        candidate_snapshots: Sequence[MarketSnapshot],
    ) -> List[MarketSnapshot]:
        selected = list(snapshots)
        if not self.pinned_assets:
            return selected
        selected_assets = {snapshot.asset for snapshot in selected}
        for snapshot in candidate_snapshots:
            if snapshot.asset in self.pinned_assets and snapshot.asset not in selected_assets:
                selected.append(snapshot)
                selected_assets.add(snapshot.asset)
        for asset in sorted(self.pinned_assets - selected_assets):
            snapshot = self._refresh_pinned_snapshot(asset)
            if snapshot is None:
                continue
            selected.append(snapshot)
            selected_assets.add(snapshot.asset)
        return selected

    def _refresh_pinned_snapshot(self, asset: str) -> Optional[MarketSnapshot]:
        template = self._snapshot_by_asset.get(asset)
        try:
            book = order_book_from_clob(self.client.book(asset), source="paper_run")
        except Exception:
            return None
        if book is None:
            return None
        snapshot = MarketSnapshot(
            asset=book.asset,
            condition_id=template.condition_id if template is not None else "",
            timestamp=book.timestamp,
            book=book,
            title=template.title if template is not None else f"pinned asset {book.asset}",
            slug=template.slug if template is not None else "",
            outcome=template.outcome if template is not None else "",
            outcome_index=template.outcome_index if template is not None else 0,
            category=template.category if template is not None else "",
            history_change_pct=template.history_change_pct if template is not None else None,
        )
        self._snapshot_by_asset[snapshot.asset] = snapshot
        return snapshot

    def _history_change_pct(self, asset: str, start_ts: int, end_ts: int) -> Optional[float]:
        cache_key = (asset, self.history_interval, self.history_window_seconds)
        if self.history_cache_seconds > 0:
            cached = self._history_change_cache.get(cache_key)
            if cached is not None and end_ts - cached[0] <= self.history_cache_seconds:
                return cached[1]
        price_history = getattr(self.client, "price_history", None)
        if price_history is None:
            return None
        try:
            data = price_history(asset, start_ts=start_ts, end_ts=end_ts, interval=self.history_interval)
        except Exception:
            if self.history_cache_seconds > 0:
                self._history_change_cache[cache_key] = (end_ts, None)
            return None
        prices = _prices_from_history(data)
        if len(prices) < 2 or prices[0] <= 0:
            if self.history_cache_seconds > 0:
                self._history_change_cache[cache_key] = (end_ts, None)
            return None
        change = (prices[-1] - prices[0]) / prices[0]
        if self.history_cache_seconds > 0:
            self._history_change_cache[cache_key] = (end_ts, change)
        return change


class PublicMarketSettlementResolver:
    """Resolve closed markets from public Gamma metadata."""

    def __init__(self, client, check_interval_seconds: int = 60, clock=None):
        self.client = client
        self.check_interval_seconds = max(0, int(check_interval_seconds))
        self.clock = clock or time.time
        self._last_checked_by_condition: Dict[str, int] = {}
        self._settlement_by_condition: Dict[str, Optional[_Settlement]] = {}

    def settlement_for(self, condition_id: str, now: Optional[int] = None) -> Optional[_Settlement]:
        condition_id = str(condition_id or "")
        if not condition_id:
            return None
        now = int(self.clock() if now is None else now)
        last_checked = self._last_checked_by_condition.get(condition_id)
        if last_checked is not None and now - last_checked < self.check_interval_seconds:
            return self._settlement_by_condition.get(condition_id)
        self._last_checked_by_condition[condition_id] = now
        settlement = self._fetch_settlement(condition_id)
        if settlement is not None:
            self._settlement_by_condition[condition_id] = settlement
        else:
            self._settlement_by_condition.setdefault(condition_id, None)
        return settlement

    def _fetch_settlement(self, condition_id: str) -> Optional[_Settlement]:
        markets_by_condition = getattr(self.client, "markets_by_condition_id", None)
        if not callable(markets_by_condition):
            return None
        rows = []
        for closed in (True, None):
            try:
                batch = markets_by_condition(condition_id, closed=closed, active=None)
            except Exception:
                continue
            if isinstance(batch, list):
                rows.extend(row for row in batch if isinstance(row, dict))
        for market in rows:
            if str(market.get("conditionId", "")) != condition_id:
                continue
            settlement = self._settlement_from_market(condition_id, market)
            if settlement is not None:
                return settlement
        return None

    def _settlement_from_market(self, condition_id: str, market: Dict[str, object]) -> Optional[_Settlement]:
        if not bool(market.get("closed", False)):
            return None
        token_ids = _parse_json_list(market.get("clobTokenIds"))
        outcome_prices = _parse_json_list(market.get("outcomePrices"))
        if not token_ids or len(token_ids) != len(outcome_prices):
            return None
        prices_by_asset: Dict[str, float] = {}
        for token_id, raw_price in zip(token_ids, outcome_prices):
            try:
                price = float(raw_price)
            except (TypeError, ValueError):
                return None
            if price >= 0.999:
                settlement_price = 1.0
            elif price <= 0.001:
                settlement_price = 0.0
            else:
                return None
            prices_by_asset[str(token_id)] = settlement_price
        return _Settlement(condition_id=condition_id, prices_by_asset=prices_by_asset)


class AgentBatch:
    def __init__(self, strategies: Sequence[PaperStrategy], initial_cash: float):
        self.states = [
            _PaperState(strategy=strategy, portfolio=Portfolio(initial_cash), equity_curve=[initial_cash])
            for strategy in strategies
        ]

    def __iter__(self):
        return iter(self.states)

    def __len__(self) -> int:
        return len(self.states)


class PaperExecutionEngine:
    def __init__(
        self,
        run_id: str,
        fill_model: ConservativeFillModel,
        latest_quotes: Dict[str, Quote],
    ):
        self.run_id = run_id
        self.fill_model = fill_model
        self.latest_quotes = latest_quotes
        self.order_counter = 0

    def try_pending_for_book(
        self,
        state: _PaperState,
        book: OrderBook,
        order_ids: Optional[set] = None,
        attempt_timestamp: Optional[int] = None,
    ) -> List[PaperFill]:
        fill_book = (
            replace(book, timestamp=int(attempt_timestamp))
            if attempt_timestamp is not None
            else book
        )
        fills: List[PaperFill] = []
        still_pending: List[PaperOrder] = []
        for order in state.pending:
            if order.signal.asset != fill_book.asset:
                still_pending.append(order)
                continue
            if order_ids is not None and order.order_id not in order_ids:
                still_pending.append(order)
                continue
            fill = self.fill_model.try_fill(order, fill_book, state.portfolio)
            if fill is None:
                attempts = order.attempts + 1 if fill_book.timestamp >= order.eligible_at else order.attempts
                still_pending.append(replace(order, attempts=attempts))
                continue
            fills.append(fill)
            state.fills.append(fill)
            residual_order = residual_maker_order_after_partial(order, fill, self.fill_model.min_notional)
            state.strategy.on_fill(fill)
            if residual_order is not None:
                still_pending.append(residual_order)
                _mark_strategy_pending(state.strategy, residual_order.signal.asset, residual_order.signal.side)
        state.pending = still_pending
        return fills

    def create_orders(self, state: _PaperState, signals: Sequence[Signal]) -> List[PaperOrder]:
        orders: List[PaperOrder] = []
        for signal in signals:
            self.order_counter += 1
            order = PaperOrder(
                order_id=f"{self.run_id}-{signal.strategy}-{self.order_counter}",
                signal=signal,
                created_at=signal.timestamp,
                eligible_at=self.fill_model.eligible_at(signal),
            )
            state.orders.append(order)
            state.pending.append(order)
            orders.append(order)
        return orders


def _mark_strategy_pending(strategy: PaperStrategy, asset: str, side: str) -> None:
    pending_assets = getattr(strategy, "pending_assets", None)
    if isinstance(pending_assets, dict):
        pending_assets[asset] = side.upper()


class PaperRunner:
    def __init__(
        self,
        client,
        conn,
        run_id: str,
        strategies: Sequence[PaperStrategy],
        fill_model: ConservativeFillModel,
        initial_cash: float = 10000.0,
        market_limit: int = 5,
        max_assets: int = 10,
        market_order: str = "volume_24hr",
        market_ascending: bool = False,
        market_pages: int = 1,
        market_active: bool = True,
        history_window_seconds: int = 0,
        history_interval: str = "1h",
        history_min_change_pct: Optional[float] = None,
        history_candidate_assets: int = 0,
        history_cache_seconds: int = 60,
        history_min_bid_price: Optional[float] = None,
        history_max_bid_price: Optional[float] = None,
        history_max_spread_pct: Optional[float] = None,
        history_max_queries: int = 0,
        market_filter_keywords: Optional[Sequence[str]] = None,
        market_prefer_keywords: Optional[Sequence[str]] = None,
        pinned_assets: Optional[Sequence[str]] = None,
        pinned_only_after_entry: bool = False,
        pinned_only_after_watchlist: bool = False,
        pinned_watchlist_rescan_cycles: int = 0,
        collector: Optional[MarketDataCollector] = None,
        settlement_resolver: Optional[PublicMarketSettlementResolver] = None,
        settlement_check_seconds: int = 60,
        use_wall_time_timestamps: bool = False,
        clock=None,
    ):
        self.client = client
        self.conn = conn
        self.run_id = run_id
        self.fill_model = fill_model
        self.initial_cash = initial_cash
        self.pinned_only_after_entry = pinned_only_after_entry
        self.pinned_only_after_watchlist = pinned_only_after_watchlist
        self.pinned_watchlist_rescan_cycles = max(0, pinned_watchlist_rescan_cycles)
        self.use_wall_time_timestamps = bool(use_wall_time_timestamps)
        self.collector = collector or MarketDataCollector(
            client,
            market_limit=market_limit,
            max_assets=max_assets,
            market_order=market_order,
            market_ascending=market_ascending,
            market_pages=market_pages,
            market_active=market_active,
            history_window_seconds=history_window_seconds,
            history_interval=history_interval,
            history_min_change_pct=history_min_change_pct,
            history_candidate_assets=history_candidate_assets,
            history_cache_seconds=history_cache_seconds,
            history_min_bid_price=history_min_bid_price,
            history_max_bid_price=history_max_bid_price,
            history_max_spread_pct=history_max_spread_pct,
            history_max_queries=history_max_queries,
            market_filter_keywords=market_filter_keywords,
            market_prefer_keywords=market_prefer_keywords,
            pinned_assets=pinned_assets,
            clock=clock,
        )
        self.clock = clock or time.time
        self.agent_batch = AgentBatch(list(strategies), initial_cash=initial_cash)
        self.latest_quotes: Dict[str, Quote] = {}
        self._asset_metadata: Dict[str, _AssetMetadata] = {}
        self.settlement_resolver = settlement_resolver
        if self.settlement_resolver is None and client is not None and settlement_check_seconds >= 0:
            self.settlement_resolver = PublicMarketSettlementResolver(
                client,
                check_interval_seconds=settlement_check_seconds,
                clock=self.clock,
            )
        self.execution = PaperExecutionEngine(run_id, fill_model, self.latest_quotes)
        self._initial_snapshots_persisted = False
        self._collector_base_limits = (
            getattr(self.collector, "market_limit", None),
            getattr(self.collector, "max_assets", None),
        )

    def resume_from_db(self) -> None:
        for state in self.agent_batch:
            row = self.conn.execute(
                """
                SELECT cash, equity, positions_json
                FROM portfolio_snapshots
                WHERE run_id = ? AND strategy = ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (self.run_id, state.strategy.name),
            ).fetchone()
            if row is None:
                continue
            state.portfolio.cash = float(row[0])
            state.portfolio.positions = _loads_positions(row[2])
            state.equity_curve = [
                float(item[0])
                for item in self.conn.execute(
                    """
                    SELECT equity
                    FROM portfolio_snapshots
                    WHERE run_id = ? AND strategy = ?
                    ORDER BY timestamp
                    """,
                    (self.run_id, state.strategy.name),
                ).fetchall()
            ] or [float(row[1])]
            self._restore_strategy_cost_basis(state)
        self._restore_latest_quotes()
        self._restore_asset_metadata()
        self._restore_order_counter()
        self._initial_snapshots_persisted = True

    def run(self, cycles: int = 1, interval_seconds: float = 0.0) -> List[StrategyResult]:
        for index in range(cycles):
            self.run_once()
            if interval_seconds > 0 and index < cycles - 1:
                time.sleep(interval_seconds)
        return self.results()

    def run_once(self) -> List[MarketSnapshot]:
        self._sync_collector_pinned_assets()
        self._apply_pinned_only_mode()
        collection = self.collector.collect()
        snapshots, rules_by_asset = collection.snapshots, collection.rules_by_asset
        self._remember_snapshot_metadata(snapshots)
        cycle_wall_time = int(self.clock())
        timestamp = (
            cycle_wall_time
            if self.use_wall_time_timestamps
            else max((snapshot.timestamp for snapshot in snapshots), default=cycle_wall_time)
        )
        strategy_rules_by_asset = self._strategy_rules_by_asset(snapshots, rules_by_asset)
        self._persist_initial_snapshots(snapshots)
        self.fill_model.rules_by_asset.update(rules_by_asset)
        books = [snapshot.book for snapshot in snapshots]
        quotes = [book.to_quote() for book in books]
        insert_order_books(self.conn, books)
        insert_quotes(self.conn, quotes)
        for quote in quotes:
            self.latest_quotes[quote.asset] = quote

        new_fills: List[PaperFill] = []
        for snapshot in snapshots:
            for state in self.agent_batch:
                new_fills.extend(
                    self.execution.try_pending_for_book(
                        state,
                        snapshot.book,
                        attempt_timestamp=timestamp if self.use_wall_time_timestamps else None,
                    )
                )
        new_fills.extend(self._settle_resolved_positions(timestamp))

        new_signals: List[Signal] = []
        new_order_ids = set()
        new_diagnostics: List[StrategyDiagnostic] = []
        for state in self.agent_batch:
            state.strategy.set_cycle_wall_time(cycle_wall_time)
            signals = state.strategy.on_snapshots(
                snapshots,
                state.portfolio,
                rules_by_asset=strategy_rules_by_asset,
            )
            if self.use_wall_time_timestamps:
                signals = [replace(signal, timestamp=timestamp) for signal in signals]
            for signal in signals:
                new_signals.append(signal)
            orders = self.execution.create_orders(state, signals)
            new_order_ids.update(order.order_id for order in orders)
            diagnostics = state.strategy.pop_diagnostics()
            if self.use_wall_time_timestamps:
                diagnostics = [replace(diagnostic, timestamp=timestamp) for diagnostic in diagnostics]
            new_diagnostics.extend(diagnostics)

        for snapshot in snapshots:
            for state in self.agent_batch:
                new_fills.extend(
                    self.execution.try_pending_for_book(
                        state,
                        snapshot.book,
                        order_ids=new_order_ids,
                        attempt_timestamp=timestamp if self.use_wall_time_timestamps else None,
                    )
                )

        if new_signals:
            insert_signal_rows(self.conn, self.run_id, new_signals)
        if new_diagnostics:
            insert_strategy_diagnostics(self.conn, self.run_id, new_diagnostics)
        if new_fills:
            insert_paper_fills(self.conn, self.run_id, new_fills)

        for state in self.agent_batch:
            equity = state.portfolio.equity(self.latest_quotes)
            state.equity_curve.append(equity)
            insert_portfolio_snapshot(
                self.conn,
                self.run_id,
                state.strategy.name,
                timestamp,
                state.portfolio.cash,
                equity,
                dict(state.portfolio.positions),
            )
        return snapshots

    def _remember_snapshot_metadata(self, snapshots: Sequence[MarketSnapshot]) -> None:
        for snapshot in snapshots:
            self._asset_metadata[snapshot.asset] = _AssetMetadata(
                asset=snapshot.asset,
                condition_id=snapshot.condition_id,
                outcome=snapshot.outcome,
                outcome_index=snapshot.outcome_index,
                title=snapshot.title,
                slug=snapshot.slug,
            )

    def _settle_resolved_positions(self, timestamp: int) -> List[PaperFill]:
        if self.settlement_resolver is None:
            return []
        fills: List[PaperFill] = []
        settlement_by_condition: Dict[str, Optional[_Settlement]] = {}
        for state in self.agent_batch:
            for asset, shares in list(state.portfolio.positions.items()):
                if shares <= 1e-9:
                    continue
                metadata = self._asset_metadata.get(asset)
                if metadata is None or not metadata.condition_id:
                    continue
                if metadata.condition_id not in settlement_by_condition:
                    settlement_by_condition[metadata.condition_id] = self.settlement_resolver.settlement_for(
                        metadata.condition_id,
                        now=timestamp,
                    )
                settlement = settlement_by_condition.get(metadata.condition_id)
                if settlement is None or asset not in settlement.prices_by_asset:
                    continue
                fill = self._settlement_fill(
                    state=state,
                    asset=asset,
                    shares=shares,
                    price=settlement.prices_by_asset[asset],
                    timestamp=timestamp,
                    condition_id=metadata.condition_id,
                )
                fills.append(fill)
        return fills

    def _settlement_fill(
        self,
        state: _PaperState,
        asset: str,
        shares: float,
        price: float,
        timestamp: int,
        condition_id: str,
    ) -> PaperFill:
        self.execution.order_counter += 1
        state.portfolio.sell(asset, shares, price, fee=0.0)
        self.latest_quotes[asset] = Quote(asset=asset, timestamp=timestamp, bid=price, ask=price, source="settlement")
        state.pending = [order for order in state.pending if order.signal.asset != asset]
        reason = "settled_winning_outcome" if price >= 1.0 else "settled_losing_outcome"
        fill = PaperFill(
            order_id=f"{self.run_id}-{state.strategy.name}-settlement-{self.execution.order_counter}",
            strategy=state.strategy.name,
            asset=asset,
            side="SELL",
            status="FILLED",
            timestamp=timestamp,
            price=price,
            shares=shares,
            notional=shares * price,
            reason=reason,
            quote_timestamp=timestamp,
            fee=0.0,
            taker=False,
            requested_notional=shares * price,
            filled_notional=shares * price,
            average_price=price,
            liquidity_source="gamma_settlement",
        )
        state.fills.append(fill)
        state.strategy.on_fill(fill)
        return fill

    def _sync_collector_pinned_assets(self) -> None:
        pinned_assets = getattr(self.collector, "pinned_assets", None)
        if pinned_assets is None:
            return
        for state in self.agent_batch:
            pinned_assets.update(asset for asset, shares in state.portfolio.positions.items() if shares > 1e-9)
            pinned_assets.update(order.signal.asset for order in state.pending)
            watched_assets = getattr(state.strategy, "watched_assets", None)
            if callable(watched_assets):
                pinned_assets.update(asset for asset in watched_assets() if asset)

    def _apply_pinned_only_mode(self) -> None:
        if not self.pinned_only_after_entry and not self.pinned_only_after_watchlist:
            return
        if not hasattr(self.collector, "market_limit") or not hasattr(self.collector, "max_assets"):
            return
        has_active_asset = any(
            any(shares > 1e-9 for shares in state.portfolio.positions.values()) or bool(state.pending)
            for state in self.agent_batch
        )
        has_watchlist_asset = any(
            bool(watched_assets())
            for state in self.agent_batch
            for watched_assets in [getattr(state.strategy, "watched_assets", None)]
            if callable(watched_assets)
        )
        watchlist_pinned_only = self.pinned_only_after_watchlist and has_watchlist_asset
        if watchlist_pinned_only and self.pinned_watchlist_rescan_cycles > 0:
            collection_count = getattr(self.collector, "collection_count", 0)
            if collection_count > 0 and collection_count % self.pinned_watchlist_rescan_cycles == 0:
                watchlist_pinned_only = False
        entry_pinned_only = self.pinned_only_after_entry and has_active_asset
        if entry_pinned_only or watchlist_pinned_only:
            self.collector.market_limit = 0
            self.collector.max_assets = 0
        else:
            market_limit, max_assets = self._collector_base_limits
            if market_limit is not None:
                self.collector.market_limit = market_limit
            if max_assets is not None:
                self.collector.max_assets = max_assets

    def _strategy_rules_by_asset(
        self,
        snapshots: Sequence[MarketSnapshot],
        collected_rules_by_asset: Dict[str, MarketRules],
    ) -> Dict[str, MarketRules]:
        return {
            snapshot.asset: collected_rules_by_asset.get(
                snapshot.asset,
                self.fill_model.rules_by_asset.get(snapshot.asset, self.fill_model.default_rules),
            )
            for snapshot in snapshots
        }

    def _restore_strategy_cost_basis(self, state: _PaperState) -> None:
        avg_cost_by_asset = getattr(state.strategy, "avg_cost_by_asset", None)
        position_shares_by_asset = getattr(state.strategy, "position_shares_by_asset", None)
        entry_bid_by_asset = getattr(state.strategy, "entry_bid_by_asset", None)
        hold_cycles_by_asset = getattr(state.strategy, "hold_cycles_by_asset", None)
        if not isinstance(avg_cost_by_asset, dict):
            return
        rows = self.conn.execute(
            """
            SELECT side, asset, shares, notional, raw_json
            FROM paper_fills
            WHERE run_id = ? AND strategy = ? AND status IN ('FILLED', 'PARTIAL')
            ORDER BY timestamp
            """,
            (self.run_id, state.strategy.name),
        ).fetchall()
        cost_basis: Dict[str, Tuple[float, float, float]] = {}
        for side, asset, shares, notional, raw_json in rows:
            side = str(side).upper()
            asset = str(asset)
            fill_shares = float(shares)
            if side == "BUY":
                raw = _loads_dict(raw_json)
                fee = float(raw.get("fee", 0.0) or 0.0)
                total_cost, total_shares, first_price = cost_basis.get(asset, (0.0, 0.0, float(raw.get("price", 0.0) or 0.0)))
                cost_basis[asset] = (
                    total_cost + float(notional) + fee,
                    total_shares + fill_shares,
                    first_price or float(raw.get("price", 0.0) or 0.0),
                )
            elif side == "SELL":
                total_cost, total_shares, first_price = cost_basis.get(asset, (0.0, 0.0, 0.0))
                if total_shares <= fill_shares + 1e-9:
                    cost_basis.pop(asset, None)
                    continue
                average_cost = total_cost / total_shares
                cost_basis[asset] = (
                    total_cost - average_cost * fill_shares,
                    total_shares - fill_shares,
                    first_price,
                )
        avg_cost_by_asset.clear()
        if isinstance(position_shares_by_asset, dict):
            position_shares_by_asset.clear()
        if isinstance(entry_bid_by_asset, dict):
            entry_bid_by_asset.clear()
        if isinstance(hold_cycles_by_asset, dict):
            hold_cycles_by_asset.clear()
        for asset, position_shares in state.portfolio.positions.items():
            if position_shares <= 1e-9:
                continue
            total_cost, total_shares, first_price = cost_basis.get(asset, (0.0, 0.0, 0.0))
            if total_shares <= 1e-9:
                continue
            avg_cost_by_asset[asset] = total_cost / total_shares
            if isinstance(position_shares_by_asset, dict):
                position_shares_by_asset[asset] = position_shares
            if isinstance(entry_bid_by_asset, dict):
                entry_bid_by_asset[asset] = first_price or avg_cost_by_asset[asset]
            if isinstance(hold_cycles_by_asset, dict):
                hold_cycles_by_asset[asset] = 0

    def _restore_latest_quotes(self) -> None:
        assets = {
            asset
            for state in self.agent_batch
            for asset, shares in state.portfolio.positions.items()
            if shares > 1e-9
        }
        for asset in assets:
            row = self.conn.execute(
                """
                SELECT timestamp, bid, ask, source
                FROM price_snapshots
                WHERE asset = ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (asset,),
            ).fetchone()
            if row is None:
                continue
            self.latest_quotes[asset] = Quote(
                asset=asset,
                timestamp=int(row[0]),
                bid=float(row[1]),
                ask=float(row[2]),
                source=str(row[3]),
            )

    def _restore_asset_metadata(self) -> None:
        assets = {
            asset
            for state in self.agent_batch
            for asset, shares in state.portfolio.positions.items()
            if shares > 1e-9
        }
        for asset in assets:
            row = self.conn.execute(
                """
                SELECT condition_id, raw_json
                FROM signals
                WHERE run_id = ? AND asset = ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (self.run_id, asset),
            ).fetchone()
            if row is None:
                continue
            raw = _loads_dict(row[1])
            self._asset_metadata[asset] = _AssetMetadata(
                asset=asset,
                condition_id=str(row[0] or raw.get("condition_id", "") or raw.get("conditionId", "") or ""),
                outcome=str(raw.get("outcome", "") or ""),
                outcome_index=int(raw.get("outcome_index", 0) or 0),
                title=str(raw.get("title", "") or ""),
                slug=str(raw.get("slug", "") or ""),
            )

    def _restore_order_counter(self) -> None:
        row = self.conn.execute(
            "SELECT COUNT(*) FROM signals WHERE run_id = ?",
            (self.run_id,),
        ).fetchone()
        self.execution.order_counter = int(row[0] if row else 0)

    def _persist_initial_snapshots(self, snapshots: Sequence[MarketSnapshot]) -> None:
        if self._initial_snapshots_persisted:
            return
        timestamp = min((snapshot.timestamp for snapshot in snapshots), default=int(self.clock())) - 1
        for state in self.agent_batch:
            insert_portfolio_snapshot(
                self.conn,
                self.run_id,
                state.strategy.name,
                timestamp,
                state.portfolio.cash,
                state.portfolio.equity(self.latest_quotes),
                dict(state.portfolio.positions),
            )
        self._initial_snapshots_persisted = True

    def fetch_snapshots(self) -> Tuple[List[MarketSnapshot], Dict[str, MarketRules]]:
        collection = self.collector.collect()
        return collection.snapshots, collection.rules_by_asset

    def results(self) -> List[StrategyResult]:
        return [self._result(state) for state in self.agent_batch]

    def _result(self, state: _PaperState) -> StrategyResult:
        equity = state.portfolio.equity(self.latest_quotes)
        fill_like = [fill for fill in state.fills if fill.status in {"FILLED", "PARTIAL"}]
        filled = [fill for fill in state.fills if fill.status == "FILLED"]
        partial = [fill for fill in state.fills if fill.status == "PARTIAL"]
        missed = [fill for fill in state.fills if fill.status == "MISSED"]
        return StrategyResult(
            strategy=state.strategy.name,
            orders=state.orders,
            fills=state.fills,
            metrics={
                "initial_cash": self.initial_cash,
                "ending_equity": equity,
                "cash": state.portfolio.cash,
                "pnl": equity - self.initial_cash,
                "roi": (equity - self.initial_cash) / self.initial_cash if self.initial_cash else 0.0,
                "orders": float(len(state.orders)),
                "filled_orders": float(len(filled)),
                "partial_orders": float(len(partial)),
                "missed_orders": float(len(missed)),
                "turnover": sum(fill.notional for fill in fill_like),
                "fees": sum(fill.fee for fill in fill_like),
                "pending_orders": float(len(state.pending)),
                "max_drawdown": _max_drawdown(state.equity_curve),
            },
        )


def _parse_json_list(raw) -> List[object]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            parsed = __import__("json").loads(raw)
        except ValueError:
            return []
        return parsed if isinstance(parsed, list) else []
    return []


def _normalize_keywords(keywords: Optional[Sequence[str]]) -> Tuple[str, ...]:
    if not keywords:
        return ()
    if isinstance(keywords, str):
        keywords = keywords.split(",")
    return tuple(
        keyword.strip().lower()
        for keyword in keywords
        if str(keyword).strip()
    )


def _market_matches_keywords(market: Dict[str, object], keywords: Sequence[str]) -> bool:
    if not keywords:
        return True
    text = _market_search_text(market)
    return any(keyword in text for keyword in keywords)


def _market_identity(market: Dict[str, object]) -> Tuple[str, str, str]:
    return (
        str(market.get("id", "") or ""),
        str(market.get("conditionId", "") or ""),
        str(market.get("slug", "") or ""),
    )


def _market_search_text(market: Dict[str, object]) -> str:
    parts = [
        market.get("question"),
        market.get("slug"),
        market.get("category"),
        market.get("categorySlug"),
        market.get("description"),
    ]
    parts.extend(_parse_json_list(market.get("outcomes")))
    return " ".join(str(part) for part in parts if part is not None).lower()


def _short_crypto_interval_priority(market: Dict[str, object], now: int) -> Tuple[int, int]:
    window = _short_crypto_interval_window(market)
    if window is None:
        return (3, 0)
    start_ts, end_ts = window
    if start_ts <= now < end_ts:
        return (0, now - start_ts)
    if now < start_ts:
        return (1, start_ts - now)
    return (2, now - end_ts)


def _short_crypto_interval_window(market: Dict[str, object]) -> Optional[Tuple[int, int]]:
    text = _market_search_text(market)
    match = re.search(r"\b(?:btc|eth|sol|xrp|bnb)-updown-(5|15)m-(\d{9,12})\b", text)
    if not match:
        return None
    minutes = int(match.group(1))
    start_ts = int(match.group(2))
    return start_ts, start_ts + minutes * 60


def _books_by_requested_token(
    token_ids: Sequence[str],
    raw_books: object,
) -> Dict[str, Dict[str, object]]:
    if not isinstance(raw_books, list):
        return {}
    books_by_token: Dict[str, Dict[str, object]] = {}
    requested = set(token_ids)
    for index, raw_book in enumerate(raw_books):
        if not isinstance(raw_book, dict):
            continue
        asset = str(raw_book.get("asset_id") or raw_book.get("asset") or "")
        if asset:
            if asset in requested:
                books_by_token[asset] = raw_book
            continue
        if index < len(token_ids):
            books_by_token[token_ids[index]] = raw_book
    return books_by_token


def _loads_positions(raw: str) -> Dict[str, float]:
    data = _loads_dict(raw)
    return {str(key): float(value) for key, value in data.items()}


def _loads_dict(raw: str) -> Dict[str, object]:
    try:
        data = json.loads(raw or "{}")
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _prices_from_history(data) -> List[float]:
    if not isinstance(data, dict):
        return []
    history = data.get("history") or data.get("prices") or []
    prices: List[float] = []
    for point in history:
        value = None
        if isinstance(point, dict):
            value = point.get("p", point.get("price", point.get("value")))
        elif isinstance(point, (list, tuple)) and len(point) >= 2:
            value = point[1]
        if value is None:
            continue
        try:
            prices.append(float(value))
        except (TypeError, ValueError):
            continue
    return prices


def _max_drawdown(equity_curve: Sequence[float]) -> float:
    peak = None
    worst = 0.0
    for value in equity_curve:
        peak = value if peak is None else max(peak, value)
        if peak and peak > 0:
            worst = min(worst, (value - peak) / peak)
    return worst
