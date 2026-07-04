============================= test session starts =============================
platform win32 -- Python 3.14.6, pytest-9.1.1, pluggy-1.6.0 -- D:\AI_Project\Dashboard_Share\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\AI_Project\Dashboard_Share
plugins: anyio-3.7.1, timeout-2.4.0
collecting ... collected 149 items

test_agents.py::TestSafeFloat::test_actual_float PASSED                  [  0%]
test_agents.py::TestSafeFloat::test_empty_string_returns_none PASSED     [  1%]
test_agents.py::TestSafeFloat::test_garbage_string_returns_none PASSED   [  2%]
test_agents.py::TestSafeFloat::test_integer_string PASSED                [  2%]
test_agents.py::TestSafeFloat::test_mixed_garbage PASSED                 [  3%]
test_agents.py::TestSafeFloat::test_negative_float_string PASSED         [  4%]
test_agents.py::TestSafeFloat::test_negative_price_returns_none PASSED   [  4%]
test_agents.py::TestSafeFloat::test_none_returns_none PASSED             [  5%]
test_agents.py::TestSafeFloat::test_placeholder_NaN PASSED               [  6%]
test_agents.py::TestSafeFloat::test_placeholder_dash PASSED              [  6%]
test_agents.py::TestSafeFloat::test_placeholder_na PASSED                [  7%]
test_agents.py::TestSafeFloat::test_placeholder_nan PASSED               [  8%]
test_agents.py::TestSafeFloat::test_placeholder_none_string PASSED       [  8%]
test_agents.py::TestSafeFloat::test_placeholder_zero_float_string PASSED [  9%]
test_agents.py::TestSafeFloat::test_placeholder_zero_string PASSED       [ 10%]
test_agents.py::TestSafeFloat::test_positive_float_string PASSED         [ 10%]
test_agents.py::TestSafeFloat::test_positive_price_ok PASSED             [ 11%]
test_agents.py::TestSafeFloat::test_price_dash_returns_none PASSED       [ 12%]
test_agents.py::TestSafeFloat::test_price_na_returns_none PASSED         [ 12%]
test_agents.py::TestSafeFloat::test_price_none_returns_none PASSED       [ 13%]
test_agents.py::TestSafeFloat::test_whitespace_only PASSED               [ 14%]
test_agents.py::TestSafeFloat::test_zero_price_returns_none PASSED       [ 14%]
test_agents.py::TestNattyFallback::test_all_tiers_fail_skips_ticker PASSED [ 15%]
test_agents.py::TestNattyFallback::test_pe_negative_is_preserved PASSED  [ 16%]
test_agents.py::TestNattyFallback::test_tier1_yfinance_success PASSED    [ 16%]
test_agents.py::TestNattyFallback::test_tier2_finnhub_fallback_on_yfinance_429 PASSED [ 17%]
test_agents.py::TestNattyFallback::test_tier3_alpha_vantage_fallback PASSED [ 18%]
test_agents.py::TestMarketAuxNews::test_format_news_avg_sentiment PASSED [ 18%]
test_agents.py::TestMarketAuxNews::test_format_news_empty_returns_no_news PASSED [ 19%]
test_agents.py::TestMarketAuxNews::test_format_news_negative_sentiment PASSED [ 20%]
test_agents.py::TestMarketAuxNews::test_group_similar_in_url PASSED      [ 20%]
test_agents.py::TestMarketAuxNews::test_limit_6_in_url PASSED            [ 21%]
test_agents.py::TestMarketAuxNews::test_monday_mode_published_after_friday PASSED [ 22%]
test_agents.py::TestMarketAuxNews::test_regular_mode_published_after_yesterday PASSED [ 22%]
test_agents.py::TestNumAnalyzeStocks::test_invalid_signal_defaults_to_hold PASSED [ 23%]
test_agents.py::TestNumAnalyzeStocks::test_json_parse_fail_uses_fallback PASSED [ 24%]
test_agents.py::TestNumAnalyzeStocks::test_negative_pe_included_in_prompt PASSED [ 24%]
test_agents.py::TestNumAnalyzeStocks::test_no_price_data_sets_zero_confidence PASSED [ 25%]
test_agents.py::TestNumAnalyzeStocks::test_valid_buy_signal PASSED       [ 26%]
test_agents.py::TestMudValidation::test_exception_flags_needs_review PASSED [ 26%]
test_agents.py::TestMudValidation::test_json_parse_fail_flags_needs_review PASSED [ 27%]
test_agents.py::TestMudValidation::test_needs_review_ticker_skipped_in_db PASSED [ 28%]
test_agents.py::TestMudValidation::test_valid_pass_result PASSED         [ 28%]
test_agents.py::TestNanQACheck::test_exception_returns_reject PASSED     [ 29%]
test_agents.py::TestNanQACheck::test_html_stripped_from_approval_reason PASSED [ 30%]
test_agents.py::TestNanQACheck::test_html_stripped_from_issues PASSED    [ 30%]
test_agents.py::TestNanQACheck::test_json_parse_fail_returns_reject PASSED [ 31%]
test_agents.py::TestNanQACheck::test_pass_result PASSED                  [ 32%]
test_agents.py::TestNanQACheck::test_report_html_stripped_before_qa PASSED [ 32%]
test_agents.py::TestWorkflow::test_complete_workflow_pass PASSED         [ 33%]
test_agents.py::TestWorkflow::test_empty_analysis_aborts_workflow PASSED [ 34%]
test_agents.py::TestWorkflow::test_empty_news_data_aborts_workflow PASSED [ 34%]
test_agents.py::TestWorkflow::test_no_shared_state_between_claude_calls PASSED [ 35%]
test_agents.py::TestWorkflow::test_qa_reject_retries_up_to_max PASSED    [ 36%]
test_agents.py::TestWorkflow::test_workflow_log_resets_each_run PASSED   [ 36%]
test_agents.py::TestColsonTrade::test_garbage_response_returns_none PASSED [ 37%]
test_agents.py::TestColsonTrade::test_parse_error_returns_none PASSED    [ 38%]
test_agents.py::TestColsonTrade::test_ticker_uppercased PASSED           [ 38%]
test_agents.py::TestColsonTrade::test_valid_buy_trade PASSED             [ 39%]
test_agents.py::TestUpdateDatabase::test_batch_commit_once PASSED        [ 40%]
test_agents.py::TestUpdateDatabase::test_current_price_updated PASSED    [ 40%]
test_agents.py::TestUpdateDatabase::test_needs_review_skipped PASSED     [ 41%]
test_agents.py::TestUpdateDatabase::test_zero_confidence_skipped PASSED  [ 42%]
test_agents.py::TestMarketCapUnit::test_mcap_has_M_USD_suffix PASSED     [ 42%]
test_agents.py::TestMarketCapUnit::test_mcap_none_shows_na PASSED        [ 43%]
test_agents.py::TestMarketCapUnit::test_mcap_small_value PASSED          [ 44%]
test_agents.py::TestNewHighFlag::test_ath_and_atl_mutually_exclusive PASSED [ 44%]
test_agents.py::TestNewHighFlag::test_big_gap_above_clears_range PASSED  [ 45%]
test_agents.py::TestNewHighFlag::test_new_high_flag_set PASSED           [ 46%]
test_agents.py::TestNewHighFlag::test_new_low_below_threshold_clears_range PASSED [ 46%]
test_agents.py::TestNewHighFlag::test_new_low_exact_boundary PASSED      [ 47%]
test_agents.py::TestNewHighFlag::test_new_low_flag_set PASSED            [ 48%]
test_agents.py::TestNewHighFlag::test_new_low_low_updated PASSED         [ 48%]
test_agents.py::TestNewHighFlag::test_price_far_below_low_clears_range PASSED [ 49%]
test_agents.py::TestNewHighFlag::test_within_range_no_flag PASSED        [ 50%]
test_agents.py::TestMudRecommendationFormat::test_pass_fail_only_constraint_in_source PASSED [ 51%]
test_agents.py::TestMudRecommendationFormat::test_pass_with_warning_not_allowed PASSED [ 51%]
test_agents.py::TestCrossCurrencyTickers::test_aapl_not_affected PASSED  [ 52%]
test_agents.py::TestCrossCurrencyTickers::test_asml_cleared PASSED       [ 53%]
test_agents.py::TestCrossCurrencyTickers::test_brkb_cleared PASSED       [ 53%]
test_agents.py::TestCrossCurrencyTickers::test_tsm_cleared PASSED        [ 54%]
test_agents.py::TestCrossCurrencyTickers::test_usd_ticker_not_affected PASSED [ 55%]
test_agents.py::TestHarryPortfolio::test_buy_signal_with_shares_is_aligned PASSED [ 55%]
test_agents.py::TestHarryPortfolio::test_buy_signal_with_zero_shares_is_misaligned PASSED [ 56%]
test_agents.py::TestHarryPortfolio::test_check_alignment_all_cases PASSED [ 57%]
test_agents.py::TestHarryPortfolio::test_db_exception_propagates PASSED  [ 57%]
test_agents.py::TestHarryPortfolio::test_empty_portfolio_returns_zero_holdings PASSED [ 58%]
test_agents.py::TestHarryPortfolio::test_get_action_all_cases PASSED     [ 59%]
test_agents.py::TestHarryPortfolio::test_sell_signal_with_shares_is_misaligned PASSED [ 59%]
test_agents.py::TestHarryPortfolio::test_sell_with_zero_shares_is_aligned PASSED [ 60%]
test_agents.py::TestHarryPortfolio::test_ticker_not_in_analysis_skipped PASSED [ 61%]
test_agents.py::TestARecordImprovements::test_db_error_no_crash PASSED   [ 61%]
test_agents.py::TestARecordImprovements::test_empty_results_no_crash PASSED [ 62%]
test_agents.py::TestARecordImprovements::test_haiku_model_used PASSED    [ 63%]
test_agents.py::TestARecordImprovements::test_signal_counts_passed_to_claude PASSED [ 63%]
test_agents.py::TestNikOptimizeCode::test_agents_py_too_large_returns_none PASSED [ 64%]
test_agents.py::TestNikOptimizeCode::test_db_save_fails_no_crash PASSED  [ 65%]
test_agents.py::TestNikOptimizeCode::test_no_diff_blocks_returns_none PASSED [ 65%]
test_agents.py::TestNikOptimizeCode::test_no_github_token_returns_none PASSED [ 66%]
test_agents.py::TestNikOptimizeCode::test_summary_extracted_from_first_summary_line PASSED [ 67%]
test_agents.py::TestNikOptimizeCode::test_valid_diff_saves_to_db_and_returns PASSED [ 67%]
test_agents.py::TestCheckpointDatabase::test_commit_called_once_for_batch PASSED [ 68%]
test_agents.py::TestCheckpointDatabase::test_db_error_no_crash PASSED    [ 69%]
test_agents.py::TestCheckpointDatabase::test_saves_valid_ticker_and_commits PASSED [ 69%]
test_agents.py::TestCheckpointDatabase::test_skips_needs_review PASSED   [ 70%]
test_agents.py::TestCheckpointDatabase::test_skips_none_s1 PASSED        [ 71%]
test_agents.py::TestCheckpointDatabase::test_skips_zero_confidence PASSED [ 71%]
test_agents.py::TestCalculateROI::test_buy_signal_price_up_is_win PASSED [ 72%]
test_agents.py::TestCalculateROI::test_exception_returns_error_dict_no_crash PASSED [ 73%]
test_agents.py::TestCalculateROI::test_meets_win_target_flag_true_when_above_threshold PASSED [ 73%]
test_agents.py::TestCalculateROI::test_no_data_returns_none_values PASSED [ 74%]
test_agents.py::TestCalculateROI::test_no_future_snapshot_skipped PASSED [ 75%]
test_agents.py::TestCalculateROI::test_portfolio_return_below_target PASSED [ 75%]
test_agents.py::TestCalculateROI::test_portfolio_return_computed_from_latest_snapshot PASSED [ 76%]
test_agents.py::TestCalculateROI::test_portfolio_return_no_snapshot_yet PASSED [ 77%]
test_agents.py::TestCalculateROI::test_sell_signal_price_down_is_win PASSED [ 77%]
test_agents.py::TestCalculateROI::test_signal_too_new_not_evaluated PASSED [ 78%]
test_agents.py::TestSnapshotPortfolio::test_computes_total_value_and_cost_correctly PASSED [ 79%]
test_agents.py::TestSnapshotPortfolio::test_db_error_logs_warning_no_crash PASSED [ 79%]
test_agents.py::TestSnapshotPortfolio::test_empty_portfolio_does_not_add_snapshot PASSED [ 80%]
test_agents.py::TestPortfolioReturnHistory::test_daily_excludes_weekends PASSED [ 81%]
test_agents.py::TestPortfolioReturnHistory::test_monthly_uses_last_snapshot_of_month PASSED [ 81%]
test_agents.py::TestPortfolioReturnHistory::test_no_data_returns_empty_lists PASSED [ 82%]
test_main.py::TestHealth::test_health_is_fast PASSED                     [ 83%]
test_main.py::TestHealth::test_health_returns_200 PASSED                 [ 83%]
test_main.py::TestHealth::test_health_returns_ok_status PASSED           [ 84%]
test_main.py::TestWorkflowEndpoint::test_workflow_already_running_returns_already_running PASSED [ 85%]
test_main.py::TestWorkflowEndpoint::test_workflow_monday_mode_flag_true PASSED [ 85%]
test_main.py::TestWorkflowEndpoint::test_workflow_no_stocks_returns_no_stocks PASSED [ 86%]
test_main.py::TestWorkflowEndpoint::test_workflow_normal_mode_flag_false PASSED [ 87%]
test_main.py::TestWorkflowEndpoint::test_workflow_response_has_job_id PASSED [ 87%]
test_main.py::TestWorkflowEndpoint::test_workflow_sets_status_to_running PASSED [ 88%]
test_main.py::TestWorkflowEndpoint::test_workflow_starts_immediately_no_blocking PASSED [ 89%]
test_main.py::TestWorkflowResume::test_resume_all_done_today_returns_complete PASSED [ 89%]
test_main.py::TestWorkflowResume::test_resume_already_running_skips PASSED [ 90%]
test_main.py::TestWorkflowResume::test_resume_pending_stocks_starts_workflow PASSED [ 91%]
test_main.py::TestLineNotification::test_api_400_no_crash PASSED         [ 91%]
test_main.py::TestLineNotification::test_api_500_no_crash PASSED         [ 92%]
test_main.py::TestLineNotification::test_empty_message_no_crash PASSED   [ 93%]
test_main.py::TestLineNotification::test_network_error_no_crash PASSED   [ 93%]
test_main.py::TestLineNotification::test_no_token_no_crash PASSED        [ 94%]
test_main.py::TestLineNotification::test_timeout_no_crash PASSED         [ 95%]
test_main.py::TestWorkflowBackground::test_bg_exception_sends_line_notification PASSED [ 95%]
test_main.py::TestWorkflowBackground::test_bg_exception_sets_error_status PASSED [ 96%]
test_main.py::TestNikSuggestionsEndpoint::test_empty_db_returns_zero_count PASSED [ 97%]
test_main.py::TestNikSuggestionsEndpoint::test_limit_10_records PASSED   [ 97%]
test_main.py::TestNikSuggestionsEndpoint::test_pending_count_correct PASSED [ 98%]
test_main.py::TestNikSuggestionsEndpoint::test_response_has_required_fields PASSED [ 99%]
test_main.py::TestNikSuggestionsEndpoint::test_suggestion_item_has_required_fields PASSED [100%]

============================== warnings summary ===============================
.venv\Lib\site-packages\starlette\_utils.py:17: 26 warnings
test_main.py: 18 warnings
  D:\AI_Project\Dashboard_Share\.venv\Lib\site-packages\starlette\_utils.py:17: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    return asyncio.iscoroutinefunction(obj) or (

main.py:182
  D:\AI_Project\Dashboard_Share\main.py:182: DeprecationWarning: 
          on_event is deprecated, use lifespan event handlers instead.
  
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    @app.on_event("startup")

.venv\Lib\site-packages\fastapi\applications.py:4547
.venv\Lib\site-packages\fastapi\applications.py:4547
  D:\AI_Project\Dashboard_Share\.venv\Lib\site-packages\fastapi\applications.py:4547: DeprecationWarning: 
          on_event is deprecated, use lifespan event handlers instead.
  
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    return self.router.on_event(event_type)

main.py:336
  D:\AI_Project\Dashboard_Share\main.py:336: DeprecationWarning: 
          on_event is deprecated, use lifespan event handlers instead.
  
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    @app.on_event("shutdown")

.venv\Lib\site-packages\fastapi\routing.py:211: 22 warnings
  D:\AI_Project\Dashboard_Share\.venv\Lib\site-packages\fastapi\routing.py:211: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    is_coroutine = asyncio.iscoroutinefunction(dependant.call)

test_main.py: 18 warnings
  D:\AI_Project\Dashboard_Share\.venv\Lib\site-packages\starlette\_utils.py:18: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    callable(obj) and asyncio.iscoroutinefunction(obj.__call__)

test_main.py: 18 warnings
  D:\AI_Project\Dashboard_Share\.venv\Lib\site-packages\httpx\_client.py:690: DeprecationWarning: The 'app' shortcut is now deprecated. Use the explicit style 'transport=WSGITransport(app=...)' instead.
    warnings.warn(message, DeprecationWarning)

test_main.py::TestWorkflowEndpoint::test_workflow_monday_mode_flag_true
test_main.py::TestWorkflowEndpoint::test_workflow_normal_mode_flag_false
test_main.py::TestWorkflowEndpoint::test_workflow_response_has_job_id
test_main.py::TestWorkflowEndpoint::test_workflow_sets_status_to_running
test_main.py::TestWorkflowEndpoint::test_workflow_starts_immediately_no_blocking
  D:\AI_Project\Dashboard_Share\main.py:590: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    _job["started_at"] = datetime.utcnow().isoformat()

test_main.py::TestWorkflowEndpoint::test_workflow_no_stocks_returns_no_stocks
  D:\AI_Project\Dashboard_Share\main.py:582: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    "timestamp": datetime.utcnow().isoformat()

test_main.py::TestWorkflowResume::test_resume_pending_stocks_starts_workflow
  D:\AI_Project\Dashboard_Share\main.py:678: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    _job["started_at"]  = datetime.utcnow().isoformat()

test_main.py::TestWorkflowBackground::test_bg_exception_sends_line_notification
test_main.py::TestWorkflowBackground::test_bg_exception_sets_error_status
  D:\AI_Project\Dashboard_Share\main.py:170: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    _job["finished_at"] = datetime.utcnow().isoformat()

test_main.py::TestNikSuggestionsEndpoint::test_empty_db_returns_zero_count
test_main.py::TestNikSuggestionsEndpoint::test_limit_10_records
test_main.py::TestNikSuggestionsEndpoint::test_pending_count_correct
test_main.py::TestNikSuggestionsEndpoint::test_response_has_required_fields
test_main.py::TestNikSuggestionsEndpoint::test_suggestion_item_has_required_fields
  D:\AI_Project\Dashboard_Share\models.py:5: MovedIn20Warning: The ``declarative_base()`` function is now available as sqlalchemy.orm.declarative_base(). (deprecated since: 2.0) (Background on SQLAlchemy 2.0 at: https://sqlalche.me/e/b8d9)
    Base = declarative_base()

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
====================== 149 passed, 120 warnings in 9.89s ======================
