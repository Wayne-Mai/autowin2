import unittest

from polypaper.models import BookLevel, MarketSnapshot, OrderBook
from polypaper.opportunity import (
    book_depth_imbalance,
    score_adaptive_target_opportunity,
    score_target_opportunity,
    target_entry_notional,
)
from polypaper.simulator import PolymarketFeeModel


def snapshot_with_book(bid, asks):
    return MarketSnapshot(
        asset="TOKEN-YES",
        condition_id="0xcondition",
        timestamp=1000,
        book=OrderBook(
            asset="TOKEN-YES",
            timestamp=1000,
            bids=(BookLevel(price=bid, size=1000),),
            asks=tuple(BookLevel(price=price, size=size) for price, size in asks),
        ),
        title="Opportunity fixture",
        outcome="Yes",
    )


class OpportunityTests(unittest.TestCase):
    def test_target_entry_notional_auto_sizes_from_portfolio_goal(self):
        self.assertEqual(
            target_entry_notional(
                initial_cash=100,
                current_cash=100,
                portfolio_target_roi=0.10,
                take_profit_pct=0.10,
                entry_notional=0,
                capital_fraction=1.0,
            ),
            100,
        )
        self.assertEqual(
            target_entry_notional(
                initial_cash=100,
                current_cash=100,
                portfolio_target_roi=0.10,
                take_profit_pct=0.10,
                entry_notional=0,
                capital_fraction=0.5,
            ),
            50,
        )

    def test_target_opportunity_scores_viable_l2_depth(self):
        opportunity = score_target_opportunity(
            snapshot_with_book(0.49, [(0.50, 1000)]),
            initial_cash=100,
            current_cash=100,
            target_notional=100,
            portfolio_target_roi=0.10,
            take_profit_pct=0.10,
            max_spread_pct=0.05,
            max_entry_impact_pct=0.05,
            max_exit_price=0.99,
            min_book_imbalance=-1.0,
        )
        self.assertTrue(opportunity.viable)
        self.assertEqual(opportunity.reason, "viable")
        self.assertAlmostEqual(opportunity.average_entry_price, 0.50)
        self.assertAlmostEqual(opportunity.required_exit_bid, 0.55)

    def test_target_opportunity_rejects_impossible_exit_price(self):
        opportunity = score_target_opportunity(
            snapshot_with_book(0.89, [(0.90, 1000)]),
            initial_cash=100,
            current_cash=100,
            target_notional=100,
            portfolio_target_roi=0.10,
            take_profit_pct=0.20,
            max_spread_pct=0.05,
            max_entry_impact_pct=0.05,
            max_exit_price=0.99,
            min_book_imbalance=-1.0,
        )
        self.assertFalse(opportunity.viable)
        self.assertEqual(opportunity.reason, "required_exit_above_max")

    def test_target_opportunity_accounts_for_entry_and_exit_fees(self):
        without_fee = score_target_opportunity(
            snapshot_with_book(0.49, [(0.50, 1000)]),
            initial_cash=100,
            current_cash=100,
            target_notional=95,
            portfolio_target_roi=0.10,
            take_profit_pct=0.10,
            max_spread_pct=0.05,
            max_entry_impact_pct=0.05,
            max_exit_price=0.99,
            min_book_imbalance=-1.0,
        )
        with_fee = score_target_opportunity(
            snapshot_with_book(0.49, [(0.50, 1000)]),
            initial_cash=100,
            current_cash=100,
            target_notional=95,
            portfolio_target_roi=0.10,
            take_profit_pct=0.10,
            max_spread_pct=0.05,
            max_entry_impact_pct=0.05,
            max_exit_price=0.99,
            min_book_imbalance=-1.0,
            fee_model=PolymarketFeeModel(fee_rate=0.05, exponent=1.0),
        )
        self.assertGreater(with_fee.estimated_entry_fee, 0)
        self.assertGreater(with_fee.required_exit_bid, without_fee.required_exit_bid)
        self.assertLess(with_fee.score, without_fee.score)

    def test_target_opportunity_rejects_entries_already_beyond_stop_loss(self):
        opportunity = score_target_opportunity(
            snapshot_with_book(0.49, [(0.50, 1000)]),
            initial_cash=100,
            current_cash=100,
            target_notional=95,
            portfolio_target_roi=0.10,
            take_profit_pct=0.10,
            max_spread_pct=0.05,
            max_entry_impact_pct=0.05,
            max_exit_price=0.99,
            min_book_imbalance=-1.0,
            max_entry_mark_to_bid_loss_pct=0.03,
            fee_model=PolymarketFeeModel(fee_rate=0.05, exponent=1.0),
        )
        self.assertFalse(opportunity.viable)
        self.assertEqual(opportunity.reason, "entry_mark_to_bid_loss_too_high")
        self.assertGreater(opportunity.entry_mark_to_bid_loss_pct, 0.03)

    def test_target_opportunity_rejects_required_exit_distance_too_far(self):
        opportunity = score_target_opportunity(
            snapshot_with_book(0.49, [(0.50, 1000)]),
            initial_cash=100,
            current_cash=100,
            target_notional=100,
            portfolio_target_roi=0.10,
            take_profit_pct=0.10,
            max_spread_pct=0.05,
            max_entry_impact_pct=0.05,
            max_exit_price=0.99,
            min_book_imbalance=-1.0,
            max_required_exit_distance_pct=0.10,
        )
        self.assertFalse(opportunity.viable)
        self.assertEqual(opportunity.reason, "required_exit_distance_too_far")
        self.assertGreater(opportunity.required_exit_distance_pct, 0.10)

    def test_target_opportunity_rejects_score_below_minimum(self):
        opportunity = score_target_opportunity(
            snapshot_with_book(0.49, [(0.50, 1000)]),
            initial_cash=100,
            current_cash=100,
            target_notional=100,
            portfolio_target_roi=0.10,
            take_profit_pct=0.10,
            max_spread_pct=0.05,
            max_entry_impact_pct=0.05,
            max_exit_price=0.99,
            min_book_imbalance=-1.0,
            required_exit_distance_weight=10.0,
            min_score=0.0,
        )
        self.assertFalse(opportunity.viable)
        self.assertEqual(opportunity.reason, "score_below_min")
        self.assertLess(opportunity.score, 0.0)

    def test_adaptive_target_opportunity_reduces_notional_to_fit_depth_constraints(self):
        opportunity = score_adaptive_target_opportunity(
            snapshot_with_book(0.50, [(0.51, 500), (0.80, 1000)]),
            initial_cash=1000,
            current_cash=1000,
            max_target_notional=500,
            min_target_notional=25,
            portfolio_target_roi=0.10,
            take_profit_pct=0.10,
            allow_take_profit_before_target=True,
            max_spread_pct=0.05,
            max_entry_impact_pct=0.05,
            max_exit_price=0.99,
            min_book_imbalance=-1.0,
            max_entry_mark_to_bid_loss_pct=0.05,
            max_required_exit_distance_pct=0.30,
        )

        self.assertTrue(opportunity.viable)
        self.assertGreater(opportunity.target_notional, 250)
        self.assertLess(opportunity.target_notional, 500)
        self.assertLessEqual(opportunity.entry_impact_pct, 0.05 + 1e-6)
        self.assertLessEqual(opportunity.entry_mark_to_bid_loss_pct, 0.05 + 1e-6)

    def test_adaptive_target_opportunity_returns_min_failure_when_no_size_is_viable(self):
        opportunity = score_adaptive_target_opportunity(
            snapshot_with_book(0.50, [(0.90, 1000)]),
            initial_cash=1000,
            current_cash=1000,
            max_target_notional=500,
            min_target_notional=25,
            portfolio_target_roi=0.10,
            take_profit_pct=0.10,
            allow_take_profit_before_target=True,
            max_spread_pct=0.05,
            max_entry_impact_pct=0.05,
            max_exit_price=0.99,
            min_book_imbalance=-1.0,
            max_entry_mark_to_bid_loss_pct=0.05,
            max_required_exit_distance_pct=0.30,
        )

        self.assertFalse(opportunity.viable)
        self.assertEqual(opportunity.target_notional, 25)

    def test_adaptive_target_opportunity_applies_minimum_score(self):
        opportunity = score_adaptive_target_opportunity(
            snapshot_with_book(0.49, [(0.50, 1000)]),
            initial_cash=100,
            current_cash=100,
            max_target_notional=100,
            min_target_notional=25,
            portfolio_target_roi=0.10,
            take_profit_pct=0.10,
            max_spread_pct=0.05,
            max_entry_impact_pct=0.05,
            max_exit_price=0.99,
            min_book_imbalance=-1.0,
            required_exit_distance_weight=10.0,
            min_score=0.0,
        )

        self.assertFalse(opportunity.viable)
        self.assertEqual(opportunity.reason, "score_below_min")

    def test_target_opportunity_rejects_bid_below_price_band(self):
        opportunity = score_target_opportunity(
            snapshot_with_book(0.19, [(0.20, 1000)]),
            initial_cash=100,
            current_cash=100,
            target_notional=50,
            portfolio_target_roi=0.10,
            take_profit_pct=0.04,
            min_bid_price=0.20,
            max_spread_pct=0.10,
            max_entry_impact_pct=0.10,
            max_exit_price=0.99,
            min_book_imbalance=-1.0,
        )
        self.assertFalse(opportunity.viable)
        self.assertEqual(opportunity.reason, "bid_below_min_price")

    def test_target_opportunity_rejects_bid_above_price_band(self):
        opportunity = score_target_opportunity(
            snapshot_with_book(0.81, [(0.82, 1000)]),
            initial_cash=100,
            current_cash=100,
            target_notional=50,
            portfolio_target_roi=0.10,
            take_profit_pct=0.04,
            max_bid_price=0.80,
            max_spread_pct=0.10,
            max_entry_impact_pct=0.10,
            max_exit_price=0.99,
            min_book_imbalance=-1.0,
        )
        self.assertFalse(opportunity.viable)
        self.assertEqual(opportunity.reason, "bid_above_max_price")

    def test_target_opportunity_can_score_reinvestable_take_profit_exit(self):
        buy_and_hold_target = score_target_opportunity(
            snapshot_with_book(0.49, [(0.50, 1000)]),
            initial_cash=100,
            current_cash=100,
            target_notional=50,
            portfolio_target_roi=0.10,
            take_profit_pct=0.03,
            max_spread_pct=0.05,
            max_entry_impact_pct=0.05,
            max_exit_price=0.99,
            min_book_imbalance=-1.0,
        )
        compound_target = score_target_opportunity(
            snapshot_with_book(0.49, [(0.50, 1000)]),
            initial_cash=100,
            current_cash=100,
            target_notional=50,
            portfolio_target_roi=0.10,
            take_profit_pct=0.03,
            allow_take_profit_before_target=True,
            max_spread_pct=0.05,
            max_entry_impact_pct=0.05,
            max_exit_price=0.99,
            min_book_imbalance=-1.0,
        )

        self.assertAlmostEqual(buy_and_hold_target.required_exit_bid, 0.60)
        self.assertAlmostEqual(compound_target.required_exit_bid, 0.515)
        self.assertLess(compound_target.required_exit_distance_pct, buy_and_hold_target.required_exit_distance_pct)

    def test_target_opportunity_reinvestable_take_profit_is_exit_fee_aware(self):
        fee_model = PolymarketFeeModel(fee_rate=0.05, exponent=1.0)
        opportunity = score_target_opportunity(
            snapshot_with_book(0.49, [(0.50, 1000)]),
            initial_cash=100,
            current_cash=100,
            target_notional=95,
            portfolio_target_roi=0.10,
            take_profit_pct=0.03,
            allow_take_profit_before_target=True,
            max_spread_pct=0.05,
            max_entry_impact_pct=0.05,
            max_exit_price=0.99,
            min_book_imbalance=-1.0,
            fee_model=fee_model,
        )
        naive_exit = opportunity.average_entry_price * (1.0 + 0.03)
        required_net = (95 + opportunity.estimated_entry_fee) * 1.03
        exit_fee = fee_model.fee_for(opportunity.shares, opportunity.required_exit_bid, taker=True)
        net_proceeds = opportunity.shares * opportunity.required_exit_bid - exit_fee

        self.assertTrue(opportunity.viable)
        self.assertGreater(opportunity.required_exit_bid, naive_exit)
        self.assertGreaterEqual(net_proceeds + 1e-9, required_net)

    def test_book_depth_imbalance_measures_near_touch_pressure(self):
        book = OrderBook(
            asset="TOKEN-YES",
            timestamp=1000,
            bids=(BookLevel(price=0.49, size=200), BookLevel(price=0.40, size=1000)),
            asks=(BookLevel(price=0.50, size=50), BookLevel(price=0.80, size=1000)),
        )
        bid_depth, ask_depth, imbalance = book_depth_imbalance(book, depth_window_pct=0.03)
        self.assertAlmostEqual(bid_depth, 98.0)
        self.assertAlmostEqual(ask_depth, 25.0)
        self.assertGreater(imbalance, 0.5)

    def test_target_opportunity_rejects_weak_book_imbalance(self):
        opportunity = score_target_opportunity(
            snapshot_with_book(0.49, [(0.50, 1000)]),
            initial_cash=100,
            current_cash=100,
            target_notional=50,
            portfolio_target_roi=0.10,
            take_profit_pct=0.10,
            max_spread_pct=0.05,
            max_entry_impact_pct=0.05,
            max_exit_price=0.99,
            min_book_imbalance=0.05,
        )
        self.assertFalse(opportunity.viable)
        self.assertEqual(opportunity.reason, "book_imbalance_too_weak")

    def test_target_opportunity_accepts_strong_book_imbalance(self):
        snapshot = MarketSnapshot(
            asset="TOKEN-YES",
            condition_id="0xcondition",
            timestamp=1000,
            book=OrderBook(
                asset="TOKEN-YES",
                timestamp=1000,
                bids=(BookLevel(price=0.49, size=1000),),
                asks=(BookLevel(price=0.50, size=100),),
            ),
            title="Opportunity fixture",
            outcome="Yes",
        )
        opportunity = score_target_opportunity(
            snapshot,
            initial_cash=100,
            current_cash=100,
            target_notional=50,
            portfolio_target_roi=0.10,
            take_profit_pct=0.10,
            max_spread_pct=0.05,
            max_entry_impact_pct=0.05,
            max_exit_price=0.99,
            min_book_imbalance=0.05,
        )
        self.assertTrue(opportunity.viable)
        self.assertGreater(opportunity.book_imbalance, 0.05)


if __name__ == "__main__":
    unittest.main()
