from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Sequence

from .models import BookLevel, MarketSnapshot, OrderBook


@dataclass(frozen=True)
class TargetOpportunity:
    asset: str
    condition_id: str
    title: str
    outcome: str
    timestamp: int
    target_notional: float
    bid: float
    ask: float
    average_entry_price: float
    estimated_entry_fee: float
    shares: float
    entry_mark_to_bid_loss_pct: float
    spread_pct: float
    entry_impact_pct: float
    bid_depth_notional: float
    ask_depth_notional: float
    book_imbalance: float
    required_exit_bid: float
    required_exit_distance_pct: float
    exit_headroom: float
    score: float
    viable: bool
    reason: str
    slug: str = ""

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def target_entry_notional(
    initial_cash: float,
    current_cash: float,
    portfolio_target_roi: float,
    take_profit_pct: float,
    entry_notional: float = 0.0,
    capital_fraction: float = 1.0,
) -> float:
    if current_cash <= 0:
        return 0.0
    max_capital = current_cash * min(max(capital_fraction, 0.0), 1.0)
    if entry_notional > 0:
        return min(entry_notional, max_capital)
    if take_profit_pct <= 0:
        return max_capital
    required = initial_cash * portfolio_target_roi / take_profit_pct
    return min(required, max_capital)


def score_target_opportunity(
    snapshot: MarketSnapshot,
    initial_cash: float,
    current_cash: float,
    target_notional: float,
    portfolio_target_roi: float = 0.10,
    take_profit_pct: float = 0.10,
    allow_take_profit_before_target: bool = False,
    max_spread_pct: float = 0.05,
    max_entry_impact_pct: float = 0.05,
    max_exit_price: float = 0.99,
    min_book_imbalance: float = 0.05,
    depth_window_pct: float = 0.03,
    imbalance_weight: float = 0.10,
    min_bid_price: Optional[float] = None,
    max_bid_price: Optional[float] = None,
    max_entry_mark_to_bid_loss_pct: Optional[float] = None,
    max_required_exit_distance_pct: Optional[float] = None,
    required_exit_distance_weight: float = 0.0,
    min_score: Optional[float] = None,
    fee_model: Any = None,
) -> TargetOpportunity:
    bid = snapshot.book.bid
    ask = snapshot.book.ask
    empty = _empty_opportunity(snapshot, target_notional, bid, ask)
    if target_notional <= 0:
        return _replace(empty, viable=False, reason="no_target_notional")
    if bid <= 0 or ask <= 0:
        return _replace(empty, viable=False, reason="missing_bid_or_ask")
    if min_bid_price is not None and bid < min_bid_price:
        return _replace(empty, viable=False, reason="bid_below_min_price")
    if max_bid_price is not None and bid > max_bid_price:
        return _replace(empty, viable=False, reason="bid_above_max_price")
    if target_notional > current_cash + 1e-9:
        return _replace(empty, viable=False, reason="target_notional_exceeds_cash")

    spread_pct = (ask - bid) / ask
    if spread_pct > max_spread_pct:
        return _replace(empty, spread_pct=spread_pct, viable=False, reason="spread_too_wide")

    average_entry_price = average_buy_price(snapshot.book, target_notional)
    if average_entry_price is None:
        return _replace(empty, spread_pct=spread_pct, viable=False, reason="insufficient_ask_depth")
    shares = target_notional / average_entry_price
    if shares <= 0:
        return _replace(empty, spread_pct=spread_pct, viable=False, reason="zero_estimated_shares")
    entry_fee = _fee_for(fee_model, shares, average_entry_price)
    average_cost = (target_notional + entry_fee) / shares
    entry_mark_to_bid_loss_pct = max(0.0, (average_cost - bid) / average_cost) if average_cost > 0 else 0.0
    if target_notional + entry_fee > current_cash + 1e-9:
        return _replace(
            empty,
            average_entry_price=average_entry_price,
            estimated_entry_fee=entry_fee,
            shares=shares,
            entry_mark_to_bid_loss_pct=entry_mark_to_bid_loss_pct,
            spread_pct=spread_pct,
            viable=False,
            reason="insufficient_cash_after_estimated_fee",
        )
    if (
        max_entry_mark_to_bid_loss_pct is not None
        and entry_mark_to_bid_loss_pct > max_entry_mark_to_bid_loss_pct
    ):
        return _replace(
            empty,
            average_entry_price=average_entry_price,
            estimated_entry_fee=entry_fee,
            shares=shares,
            entry_mark_to_bid_loss_pct=entry_mark_to_bid_loss_pct,
            spread_pct=spread_pct,
            viable=False,
            reason="entry_mark_to_bid_loss_too_high",
        )

    entry_impact_pct = (average_entry_price - bid) / average_entry_price
    if entry_impact_pct > max_entry_impact_pct:
        return _replace(
            empty,
            average_entry_price=average_entry_price,
            estimated_entry_fee=entry_fee,
            shares=shares,
            entry_mark_to_bid_loss_pct=entry_mark_to_bid_loss_pct,
            spread_pct=spread_pct,
            entry_impact_pct=entry_impact_pct,
            viable=False,
            reason="entry_impact_too_high",
        )
    bid_depth, ask_depth, book_imbalance = book_depth_imbalance(snapshot.book, depth_window_pct)
    if book_imbalance < min_book_imbalance:
        return _replace(
            empty,
            average_entry_price=average_entry_price,
            estimated_entry_fee=entry_fee,
            shares=shares,
            entry_mark_to_bid_loss_pct=entry_mark_to_bid_loss_pct,
            spread_pct=spread_pct,
            entry_impact_pct=entry_impact_pct,
            bid_depth_notional=bid_depth,
            ask_depth_notional=ask_depth,
            book_imbalance=book_imbalance,
            viable=False,
            reason="book_imbalance_too_weak",
        )

    post_entry_cash = current_cash - target_notional - entry_fee
    target_equity = initial_cash * (1.0 + portfolio_target_roi)
    portfolio_exit_bid = _required_exit_price(
        shares=shares,
        post_entry_cash=post_entry_cash,
        target_equity=target_equity,
        max_exit_price=max_exit_price,
        fee_model=fee_model,
    )
    take_profit_exit_bid = required_exit_price_for_net_proceeds(
        shares=shares,
        required_net_proceeds=shares * average_cost * (1.0 + take_profit_pct),
        max_exit_price=max_exit_price,
        fee_model=fee_model,
    )
    required_exit_bid = (
        min(portfolio_exit_bid, take_profit_exit_bid)
        if allow_take_profit_before_target
        else max(portfolio_exit_bid, take_profit_exit_bid)
    )
    required_exit_distance_pct = (
        max(0.0, (required_exit_bid - bid) / bid)
        if bid > 0 and required_exit_bid != float("inf")
        else float("inf")
    )
    exit_headroom = max_exit_price - required_exit_bid
    viable = required_exit_bid <= max_exit_price
    reason = "viable" if viable else "required_exit_above_max"
    if (
        viable
        and max_required_exit_distance_pct is not None
        and required_exit_distance_pct > max_required_exit_distance_pct
    ):
        viable = False
        reason = "required_exit_distance_too_far"
    score = (
        exit_headroom
        - spread_pct
        - entry_impact_pct
        - entry_mark_to_bid_loss_pct
        - required_exit_distance_weight * required_exit_distance_pct
        + imbalance_weight * book_imbalance
    )
    if viable and min_score is not None and score < min_score:
        viable = False
        reason = "score_below_min"
    return TargetOpportunity(
        asset=snapshot.asset,
        condition_id=snapshot.condition_id,
        title=snapshot.title,
        outcome=snapshot.outcome,
        timestamp=snapshot.timestamp,
        target_notional=target_notional,
        bid=bid,
        ask=ask,
        average_entry_price=average_entry_price,
        estimated_entry_fee=entry_fee,
        shares=shares,
        entry_mark_to_bid_loss_pct=entry_mark_to_bid_loss_pct,
        spread_pct=spread_pct,
        entry_impact_pct=entry_impact_pct,
        bid_depth_notional=bid_depth,
        ask_depth_notional=ask_depth,
        book_imbalance=book_imbalance,
        required_exit_bid=required_exit_bid,
        required_exit_distance_pct=required_exit_distance_pct,
        exit_headroom=exit_headroom,
        score=score,
        viable=viable,
        reason=reason,
        slug=snapshot.slug,
    )


def score_adaptive_target_opportunity(
    snapshot: MarketSnapshot,
    initial_cash: float,
    current_cash: float,
    max_target_notional: float,
    min_target_notional: float = 1.0,
    portfolio_target_roi: float = 0.10,
    take_profit_pct: float = 0.10,
    allow_take_profit_before_target: bool = False,
    max_spread_pct: float = 0.05,
    max_entry_impact_pct: float = 0.05,
    max_exit_price: float = 0.99,
    min_book_imbalance: float = 0.05,
    depth_window_pct: float = 0.03,
    imbalance_weight: float = 0.10,
    min_bid_price: Optional[float] = None,
    max_bid_price: Optional[float] = None,
    max_entry_mark_to_bid_loss_pct: Optional[float] = None,
    max_required_exit_distance_pct: Optional[float] = None,
    required_exit_distance_weight: float = 0.0,
    min_score: Optional[float] = None,
    fee_model: Any = None,
) -> TargetOpportunity:
    if max_target_notional <= 0:
        return score_target_opportunity(
            snapshot,
            initial_cash=initial_cash,
            current_cash=current_cash,
            target_notional=max_target_notional,
            portfolio_target_roi=portfolio_target_roi,
            take_profit_pct=take_profit_pct,
            allow_take_profit_before_target=allow_take_profit_before_target,
            max_spread_pct=max_spread_pct,
            max_entry_impact_pct=max_entry_impact_pct,
            max_exit_price=max_exit_price,
            min_book_imbalance=min_book_imbalance,
            depth_window_pct=depth_window_pct,
            imbalance_weight=imbalance_weight,
            min_bid_price=min_bid_price,
            max_bid_price=max_bid_price,
            max_entry_mark_to_bid_loss_pct=max_entry_mark_to_bid_loss_pct,
            max_required_exit_distance_pct=max_required_exit_distance_pct,
            required_exit_distance_weight=required_exit_distance_weight,
            min_score=min_score,
            fee_model=fee_model,
        )
    min_notional = min(max(min_target_notional, 0.0), max_target_notional)
    max_opportunity = score_target_opportunity(
        snapshot,
        initial_cash=initial_cash,
        current_cash=current_cash,
        target_notional=max_target_notional,
        portfolio_target_roi=portfolio_target_roi,
        take_profit_pct=take_profit_pct,
        allow_take_profit_before_target=allow_take_profit_before_target,
        max_spread_pct=max_spread_pct,
        max_entry_impact_pct=max_entry_impact_pct,
        max_exit_price=max_exit_price,
        min_book_imbalance=min_book_imbalance,
        depth_window_pct=depth_window_pct,
        imbalance_weight=imbalance_weight,
        min_bid_price=min_bid_price,
        max_bid_price=max_bid_price,
        max_entry_mark_to_bid_loss_pct=max_entry_mark_to_bid_loss_pct,
        max_required_exit_distance_pct=max_required_exit_distance_pct,
        required_exit_distance_weight=required_exit_distance_weight,
        min_score=min_score,
        fee_model=fee_model,
    )
    if max_opportunity.viable:
        return max_opportunity

    min_opportunity = score_target_opportunity(
        snapshot,
        initial_cash=initial_cash,
        current_cash=current_cash,
        target_notional=min_notional,
        portfolio_target_roi=portfolio_target_roi,
        take_profit_pct=take_profit_pct,
        allow_take_profit_before_target=allow_take_profit_before_target,
        max_spread_pct=max_spread_pct,
        max_entry_impact_pct=max_entry_impact_pct,
        max_exit_price=max_exit_price,
        min_book_imbalance=min_book_imbalance,
        depth_window_pct=depth_window_pct,
        imbalance_weight=imbalance_weight,
        min_bid_price=min_bid_price,
        max_bid_price=max_bid_price,
        max_entry_mark_to_bid_loss_pct=max_entry_mark_to_bid_loss_pct,
        max_required_exit_distance_pct=max_required_exit_distance_pct,
        required_exit_distance_weight=required_exit_distance_weight,
        min_score=min_score,
        fee_model=fee_model,
    )
    if not min_opportunity.viable:
        return min_opportunity

    best = min_opportunity
    low = min_notional
    high = max_target_notional
    for _ in range(24):
        mid = (low + high) / 2.0
        opportunity = score_target_opportunity(
            snapshot,
            initial_cash=initial_cash,
            current_cash=current_cash,
            target_notional=mid,
            portfolio_target_roi=portfolio_target_roi,
            take_profit_pct=take_profit_pct,
            allow_take_profit_before_target=allow_take_profit_before_target,
            max_spread_pct=max_spread_pct,
            max_entry_impact_pct=max_entry_impact_pct,
            max_exit_price=max_exit_price,
            min_book_imbalance=min_book_imbalance,
            depth_window_pct=depth_window_pct,
            imbalance_weight=imbalance_weight,
            min_bid_price=min_bid_price,
            max_bid_price=max_bid_price,
            max_entry_mark_to_bid_loss_pct=max_entry_mark_to_bid_loss_pct,
            max_required_exit_distance_pct=max_required_exit_distance_pct,
            required_exit_distance_weight=required_exit_distance_weight,
            min_score=min_score,
            fee_model=fee_model,
        )
        if opportunity.viable:
            best = opportunity
            low = mid
        else:
            high = mid
    return best


def average_buy_price(book: OrderBook, target_notional: float) -> Optional[float]:
    remaining = target_notional
    gross = 0.0
    shares = 0.0
    for level in _sorted_asks(book.asks):
        if remaining <= 1e-9:
            break
        level_gross = min(remaining, level.price * level.size)
        if level_gross <= 0:
            continue
        gross += level_gross
        shares += level_gross / level.price
        remaining -= level_gross
    if remaining > 1e-9 or shares <= 0:
        return None
    return gross / shares


def book_depth_imbalance(book: OrderBook, depth_window_pct: float = 0.03) -> tuple:
    bid = book.bid
    ask = book.ask
    if bid <= 0 or ask <= 0:
        return 0.0, 0.0, 0.0
    bid_floor = bid * (1.0 - max(depth_window_pct, 0.0))
    ask_ceiling = ask * (1.0 + max(depth_window_pct, 0.0))
    bid_depth = sum(level.price * level.size for level in book.bids if level.price >= bid_floor)
    ask_depth = sum(level.price * level.size for level in book.asks if level.price <= ask_ceiling)
    total = bid_depth + ask_depth
    imbalance = (bid_depth - ask_depth) / total if total > 0 else 0.0
    return bid_depth, ask_depth, imbalance


def _sorted_asks(levels: Sequence[BookLevel]) -> Sequence[BookLevel]:
    return sorted(levels, key=lambda item: item.price)


def _empty_opportunity(
    snapshot: MarketSnapshot,
    target_notional: float,
    bid: float,
    ask: float,
) -> TargetOpportunity:
    return TargetOpportunity(
        asset=snapshot.asset,
        condition_id=snapshot.condition_id,
        title=snapshot.title,
        outcome=snapshot.outcome,
        timestamp=snapshot.timestamp,
        target_notional=target_notional,
        bid=bid,
        ask=ask,
        average_entry_price=0.0,
        estimated_entry_fee=0.0,
        shares=0.0,
        entry_mark_to_bid_loss_pct=0.0,
        spread_pct=0.0,
        entry_impact_pct=0.0,
        bid_depth_notional=0.0,
        ask_depth_notional=0.0,
        book_imbalance=0.0,
        required_exit_bid=0.0,
        required_exit_distance_pct=0.0,
        exit_headroom=0.0,
        score=float("-inf"),
        viable=False,
        reason="not_scored",
        slug=snapshot.slug,
    )


def _replace(opportunity: TargetOpportunity, **changes) -> TargetOpportunity:
    data = opportunity.to_dict()
    data.update(changes)
    return TargetOpportunity(**data)


def _required_exit_price(
    shares: float,
    post_entry_cash: float,
    target_equity: float,
    max_exit_price: float,
    fee_model: Any,
) -> float:
    required_after_fee = target_equity - post_entry_cash
    return required_exit_price_for_net_proceeds(
        shares=shares,
        required_net_proceeds=required_after_fee,
        max_exit_price=max_exit_price,
        fee_model=fee_model,
    )


def required_exit_price_for_net_proceeds(
    shares: float,
    required_net_proceeds: float,
    max_exit_price: float,
    fee_model: Any,
) -> float:
    if shares <= 0:
        return float("inf")
    no_fee_price = max(0.0, required_net_proceeds / shares)
    if fee_model is None:
        return no_fee_price
    low = 0.0
    high = max_exit_price
    for _ in range(40):
        mid = (low + high) / 2.0
        proceeds = shares * mid - _fee_for(fee_model, shares, mid)
        if proceeds >= required_net_proceeds:
            high = mid
        else:
            low = mid
    proceeds = shares * high - _fee_for(fee_model, shares, high)
    if proceeds + 1e-9 < required_net_proceeds:
        return float("inf")
    return high


def _fee_for(fee_model: Any, shares: float, price: float) -> float:
    if fee_model is None:
        return 0.0
    fee_for = getattr(fee_model, "fee_for", None)
    if fee_for is None:
        return 0.0
    return float(fee_for(shares, price, taker=True))
