.PHONY: test demo init-db collect-top100 collect-current-books paper-smoke scale-smoke target-profit-test dashboard

test:
	python3 -m unittest discover -s tests

demo:
	python3 -m polypaper.cli replay-fixture tests/fixtures/small_replay.json --out reports/small_replay.md

init-db:
	python3 -m polypaper.cli init-db --db data/polypaper.sqlite

collect-top100:
	python3 -m polypaper.cli collect-leaderboard --db data/polypaper.sqlite --limit 100

collect-current-books:
	python3 -m polypaper.cli collect-current-books --db data/polypaper.sqlite --market-limit 10

paper-smoke:
	python3 -m polypaper.cli paper-run --db data/polypaper.sqlite --cycles 1 --market-limit 1 --max-assets 1 --trade-probability 1 --execution-delay-seconds 0 --out reports/paper_smoke.md

scale-smoke:
	python3 -m polypaper.cli paper-run --db data/polypaper.sqlite --cycles 1 --market-limit 1 --max-assets 1 --random-agents 25 --trade-probability 1 --execution-delay-seconds 0 --out reports/paper_25_agents.md

target-profit-test:
	python3 -m unittest \
		tests.test_paper_runner.PaperRunnerTests.test_target_profit_strategy_reaches_10pct_roi_on_favorable_path \
		tests.test_paper_runner.PaperRunnerTests.test_target_profit_strategy_auto_sizes_entry_for_portfolio_goal \
		tests.test_paper_runner.PaperRunnerTests.test_target_profit_strategy_can_compound_take_profit_exits_to_10pct \
		tests.test_paper_runner.PaperRunnerTests.test_target_profit_strategy_compound_exit_is_fee_aware \
		tests.test_paper_runner.PaperRunnerTests.test_target_profit_strategy_exits_stale_position_after_max_hold \
		tests.test_paper_runner.PaperRunnerTests.test_target_profit_strategy_does_not_max_hold_exit_when_progressing \
		tests.test_paper_runner.PaperRunnerTests.test_target_profit_strategy_can_switch_after_max_hold_exit \
		tests.test_paper_runner.PaperRunnerTests.test_target_profit_strategy_skips_wide_spreads \
		tests.test_paper_runner.PaperRunnerTests.test_target_profit_strategy_skips_high_market_impact_entries \
		tests.test_paper_runner.PaperRunnerTests.test_target_profit_strategy_selects_best_viable_candidate_per_cycle \
		tests.test_paper_runner.PaperRunnerTests.test_target_profit_strategy_waits_for_positive_momentum_before_entry \
		tests.test_paper_runner.PaperRunnerTests.test_target_profit_strategy_rejects_negative_momentum \
		tests.test_paper_runner.PaperRunnerTests.test_target_profit_strategy_skips_entries_already_inside_stop_loss \
		tests.test_paper_runner.PaperRunnerTests.test_target_profit_strategy_exits_on_stop_loss \
		tests.test_paper_runner.PaperRunnerTests.test_target_profit_strategy_cools_down_after_sell \
		tests.test_paper_runner.PaperRunnerTests.test_target_profit_strategy_global_cooldown_blocks_new_asset_after_sell \
		tests.test_paper_runner.PaperRunnerTests.test_target_profit_strategy_requires_positive_book_imbalance \
		tests.test_paper_runner.PaperRunnerTests.test_target_profit_strategy_accepts_positive_book_imbalance \
		tests.test_opportunity \
		tests.test_target_runner \
		tests.test_verification

dashboard:
	python3 -m polypaper.cli dashboard --db data/polypaper.sqlite --host 127.0.0.1 --port 8765
