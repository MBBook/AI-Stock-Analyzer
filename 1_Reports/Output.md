============================= test session starts =============================
platform win32 -- Python 3.14.6, pytest-9.1.1, pluggy-1.6.0 -- D:\AI_Project\Dashboard_Share\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\AI_Project\Dashboard_Share
plugins: anyio-3.7.1, timeout-2.4.0
collecting ... collected 210 items

test_main.py::TestHealth::test_health_is_fast PASSED                     [  0%]
test_main.py::TestHealth::test_health_returns_200 PASSED                 [  0%]
test_main.py::TestHealth::test_health_returns_ok_status PASSED           [  1%]
test_main.py::TestWorkflowEndpoint::test_workflow_already_running_returns_already_running PASSED [  1%]
test_main.py::TestWorkflowEndpoint::test_workflow_monday_mode_flag_true PASSED [  2%]
test_main.py::TestWorkflowEndpoint::test_workflow_no_stocks_returns_no_stocks PASSED [  2%]
test_main.py::TestWorkflowEndpoint::test_workflow_normal_mode_flag_false PASSED [  3%]
test_main.py::TestWorkflowEndpoint::test_workflow_response_has_job_id PASSED [  3%]
test_main.py::TestWorkflowEndpoint::test_workflow_sets_status_to_running PASSED [  4%]
test_main.py::TestWorkflowEndpoint::test_workflow_starts_immediately_no_blocking PASSED [  4%]
test_main.py::TestWorkflowResume::test_resume_all_done_today_returns_complete PASSED [  5%]
test_main.py::TestWorkflowResume::test_resume_already_running_skips PASSED [  5%]
test_main.py::TestWorkflowResume::test_resume_pending_stocks_starts_workflow PASSED [  6%]
test_main.py::TestLineNotification::test_api_400_no_crash PASSED         [  6%]
test_main.py::TestLineNotification::test_api_500_no_crash PASSED         [  7%]
test_main.py::TestLineNotification::test_empty_message_no_crash PASSED   [  7%]
test_main.py::TestLineNotification::test_network_error_no_crash PASSED   [  8%]
test_main.py::TestLineNotification::test_no_token_no_crash PASSED        [  8%]
test_main.py::TestLineNotification::test_timeout_no_crash PASSED         [  9%]
test_main.py::TestWorkflowBackground::test_bg_exception_sends_line_notification PASSED [  9%]
test_main.py::TestWorkflowBackground::test_bg_exception_sets_error_status PASSED [ 10%]
test_main.py::TestNikSuggestionsEndpoint::test_empty_db_returns_zero_count PASSED [ 10%]
test_main.py::TestNikSuggestionsEndpoint::test_limit_10_records PASSED   [ 10%]
test_main.py::TestNikSuggestionsEndpoint::test_pending_count_correct PASSED [ 11%]
test_main.py::TestNikSuggestionsEndpoint::test_response_has_required_fields PASSED [ 11%]
test_main.py::TestNikSuggestionsEndpoint::test_suggestion_item_has_required_fields PASSED [ 12%]
test_main.py::TestNikExportEndpoint::test_bypasses_dashboard_auth_when_both_set PASSED [ 12%]
test_main.py::TestNikExportEndpoint::test_correct_token_returns_200_with_suggestions PASSED [ 13%]
test_main.py::TestNikExportEndpoint::test_limit_capped_at_20 PASSED      [ 13%]
test_main.py::TestNikExportEndpoint::test_missing_token_param_returns_401 PASSED [ 14%]
test_main.py::TestNikExportEndpoint::test_no_token_env_set_returns_403 PASSED [ 14%]
test_main.py::TestNikExportEndpoint::test_wrong_token_returns_401 PASSED [ 15%]
test_main.py::TestNikRejectEndpoint::test_reject_already_complete_returns_400 PASSED [ 15%]
test_main.py::TestNikRejectEndpoint::test_reject_already_rejected_returns_400 PASSED [ 16%]
test_main.py::TestNikRejectEndpoint::test_reject_not_found_returns_404 PASSED [ 16%]
test_main.py::TestNikRejectEndpoint::test_reject_pending_returns_200_and_sets_rejected PASSED [ 17%]
test_main.py::TestNikRejectEndpoint::test_reject_requires_dashboard_auth_when_enabled PASSED [ 17%]
test_main.py::TestNikCheckStatusEndpoint::test_find_block_gone_marks_complete PASSED [ 18%]
test_main.py::TestNikCheckStatusEndpoint::test_find_block_still_present_stays_pending PASSED [ 18%]
test_main.py::TestNikCheckStatusEndpoint::test_github_fetch_fails_returns_503 PASSED [ 19%]
test_main.py::TestNikCheckStatusEndpoint::test_no_github_token_returns_503 PASSED [ 19%]
test_main.py::TestNikCheckStatusEndpoint::test_no_parseable_find_blocks_returns_422 PASSED [ 20%]
test_main.py::TestNikCheckStatusEndpoint::test_not_found_returns_404 PASSED [ 20%]
test_main.py::TestNikCheckStatusEndpoint::test_not_pending_returns_400 PASSED [ 20%]
test_main.py::TestNikCheckStatusEndpoint::test_requires_dashboard_auth_when_enabled PASSED [ 21%]
test_main.py::TestDashboardAuth::test_401_response_has_cors_header PASSED [ 21%]
test_main.py::TestDashboardAuth::test_health_stays_public_when_auth_on PASSED [ 22%]
test_main.py::TestDashboardAuth::test_login_correct_password_returns_token PASSED [ 22%]
test_main.py::TestDashboardAuth::test_login_wrong_password_401 PASSED    [ 23%]
test_main.py::TestDashboardAuth::test_no_env_auth_disabled_protected_route_open PASSED [ 23%]
test_main.py::TestDashboardAuth::test_no_env_login_returns_auth_disabled_flag PASSED [ 24%]
test_main.py::TestDashboardAuth::test_options_preflight_not_blocked PASSED [ 24%]
test_main.py::TestDashboardAuth::test_protected_route_with_token_200 PASSED [ 25%]
test_main.py::TestDashboardAuth::test_protected_route_without_token_401 PASSED [ 25%]
test_main.py::TestDashboardAuth::test_protected_route_wrong_token_401 PASSED [ 26%]
test_main.py::TestLoginRateLimit::test_lock_expires_after_window PASSED  [ 26%]
test_main.py::TestLoginRateLimit::test_locked_even_with_correct_password PASSED [ 27%]
test_main.py::TestLoginRateLimit::test_lockout_after_max_fails PASSED    [ 27%]
test_main.py::TestLoginRateLimit::test_success_resets_fail_count PASSED  [ 28%]
test_main.py::TestNewsEndpoint::test_news_broken_json_row_skipped_not_500 PASSED [ 28%]
test_main.py::TestNewsEndpoint::test_news_dedup_across_tickers_and_sort PASSED [ 29%]
test_main.py::TestNewsEndpoint::test_news_empty_cache_returns_empty_list PASSED [ 29%]
test_main.py::TestNewsEndpoint::test_news_translation_applied PASSED     [ 30%]
test_main.py::TestNewsEndpoint::test_news_untranslated_falls_back_to_english PASSED [ 30%]
test_agents.py::TestSafeFloat::test_actual_float PASSED                  [ 30%]
test_agents.py::TestSafeFloat::test_empty_string_returns_none PASSED     [ 31%]
test_agents.py::TestSafeFloat::test_garbage_string_returns_none PASSED   [ 31%]
test_agents.py::TestSafeFloat::test_integer_string PASSED                [ 32%]
test_agents.py::TestSafeFloat::test_mixed_garbage PASSED                 [ 32%]
test_agents.py::TestSafeFloat::test_negative_float_string PASSED         [ 33%]
test_agents.py::TestSafeFloat::test_negative_price_returns_none PASSED   [ 33%]
test_agents.py::TestSafeFloat::test_none_returns_none PASSED             [ 34%]
test_agents.py::TestSafeFloat::test_placeholder_NaN PASSED               [ 34%]
test_agents.py::TestSafeFloat::test_placeholder_dash PASSED              [ 35%]
test_agents.py::TestSafeFloat::test_placeholder_na PASSED                [ 35%]
test_agents.py::TestSafeFloat::test_placeholder_nan PASSED               [ 36%]
test_agents.py::TestSafeFloat::test_placeholder_none_string PASSED       [ 36%]
test_agents.py::TestSafeFloat::test_placeholder_zero_float_string PASSED [ 37%]
test_agents.py::TestSafeFloat::test_placeholder_zero_string PASSED       [ 37%]
test_agents.py::TestSafeFloat::test_positive_float_string PASSED         [ 38%]
test_agents.py::TestSafeFloat::test_positive_price_ok PASSED             [ 38%]
test_agents.py::TestSafeFloat::test_price_dash_returns_none PASSED       [ 39%]
test_agents.py::TestSafeFloat::test_price_na_returns_none PASSED         [ 39%]
test_agents.py::TestSafeFloat::test_price_none_returns_none PASSED       [ 40%]
test_agents.py::TestSafeFloat::test_whitespace_only PASSED               [ 40%]
test_agents.py::TestSafeFloat::test_zero_price_returns_none PASSED       [ 40%]
test_agents.py::TestNattyFallback::test_all_tiers_fail_skips_ticker PASSED [ 41%]
test_agents.py::TestNattyFallback::test_pe_negative_is_preserved PASSED  [ 41%]
test_agents.py::TestNattyFallback::test_tier1_yfinance_success PASSED    [ 42%]
test_agents.py::TestNattyFallback::test_tier2_finnhub_fallback_on_yfinance_429 PASSED [ 42%]
test_agents.py::TestNattyFallback::test_tier3_alpha_vantage_fallback PASSED [ 43%]
test_agents.py::TestMarketAuxNews::test_format_news_avg_sentiment PASSED [ 43%]
test_agents.py::TestMarketAuxNews::test_format_news_empty_returns_no_news PASSED [ 44%]
test_agents.py::TestMarketAuxNews::test_format_news_negative_sentiment PASSED [ 44%]
test_agents.py::TestMarketAuxNews::test_group_similar_in_url PASSED      [ 45%]
test_agents.py::TestMarketAuxNews::test_limit_6_in_url PASSED            [ 45%]
test_agents.py::TestMarketAuxNews::test_monday_mode_published_after_friday PASSED [ 46%]
test_agents.py::TestMarketAuxNews::test_regular_mode_published_after_yesterday PASSED [ 46%]
test_agents.py::TestNumAnalyzeStocks::test_invalid_signal_defaults_to_hold PASSED [ 47%]
test_agents.py::TestNumAnalyzeStocks::test_json_parse_fail_uses_fallback PASSED [ 47%]
test_agents.py::TestNumAnalyzeStocks::test_negative_pe_included_in_prompt PASSED [ 48%]
test_agents.py::TestNumAnalyzeStocks::test_no_price_data_sets_zero_confidence PASSED [ 48%]
test_agents.py::TestNumAnalyzeStocks::test_valid_buy_signal PASSED       [ 49%]
test_agents.py::TestMudValidation::test_exception_flags_needs_review PASSED [ 49%]
test_agents.py::TestMudValidation::test_json_parse_fail_flags_needs_review PASSED [ 50%]
test_agents.py::TestMudValidation::test_needs_review_ticker_skipped_in_db PASSED [ 50%]
test_agents.py::TestMudValidation::test_valid_pass_result PASSED         [ 50%]
test_agents.py::TestNanQACheck::test_exception_returns_reject PASSED     [ 51%]
test_agents.py::TestNanQACheck::test_html_stripped_from_approval_reason PASSED [ 51%]
test_agents.py::TestNanQACheck::test_html_stripped_from_issues PASSED    [ 52%]
test_agents.py::TestNanQACheck::test_json_parse_fail_returns_reject PASSED [ 52%]
test_agents.py::TestNanQACheck::test_pass_result PASSED                  [ 53%]
test_agents.py::TestNanQACheck::test_report_html_stripped_before_qa PASSED [ 53%]
test_agents.py::TestWorkflow::test_complete_workflow_pass PASSED         [ 54%]
test_agents.py::TestWorkflow::test_empty_analysis_aborts_workflow PASSED [ 54%]
test_agents.py::TestWorkflow::test_empty_news_data_aborts_workflow PASSED [ 55%]
test_agents.py::TestWorkflow::test_no_shared_state_between_claude_calls PASSED [ 55%]
test_agents.py::TestWorkflow::test_qa_reject_retries_up_to_max PASSED    [ 56%]
test_agents.py::TestWorkflow::test_workflow_log_resets_each_run PASSED   [ 56%]
test_agents.py::TestColsonTrade::test_garbage_response_returns_none PASSED [ 57%]
test_agents.py::TestColsonTrade::test_parse_error_returns_none PASSED    [ 57%]
test_agents.py::TestColsonTrade::test_ticker_uppercased PASSED           [ 58%]
test_agents.py::TestColsonTrade::test_valid_buy_trade PASSED             [ 58%]
test_agents.py::TestUpdateDatabase::test_batch_commit_once PASSED        [ 59%]
test_agents.py::TestUpdateDatabase::test_current_price_updated PASSED    [ 59%]
test_agents.py::TestUpdateDatabase::test_needs_review_skipped PASSED     [ 60%]
test_agents.py::TestUpdateDatabase::test_zero_confidence_skipped PASSED  [ 60%]
test_agents.py::TestMarketCapUnit::test_mcap_has_M_USD_suffix PASSED     [ 60%]
test_agents.py::TestMarketCapUnit::test_mcap_none_shows_na PASSED        [ 61%]
test_agents.py::TestMarketCapUnit::test_mcap_small_value PASSED          [ 61%]
test_agents.py::TestNewHighFlag::test_ath_and_atl_mutually_exclusive PASSED [ 62%]
test_agents.py::TestNewHighFlag::test_big_gap_above_clears_range PASSED  [ 62%]
test_agents.py::TestNewHighFlag::test_new_high_flag_set PASSED           [ 63%]
test_agents.py::TestNewHighFlag::test_new_low_below_threshold_clears_range PASSED [ 63%]
test_agents.py::TestNewHighFlag::test_new_low_exact_boundary PASSED      [ 64%]
test_agents.py::TestNewHighFlag::test_new_low_flag_set PASSED            [ 64%]
test_agents.py::TestNewHighFlag::test_new_low_low_updated PASSED         [ 65%]
test_agents.py::TestNewHighFlag::test_price_far_below_low_clears_range PASSED [ 65%]
test_agents.py::TestNewHighFlag::test_within_range_no_flag PASSED        [ 66%]
test_agents.py::TestMudRecommendationFormat::test_pass_fail_only_constraint_in_source PASSED [ 66%]
test_agents.py::TestMudRecommendationFormat::test_pass_with_warning_not_allowed PASSED [ 67%]
test_agents.py::TestCrossCurrencyTickers::test_aapl_not_affected PASSED  [ 67%]
test_agents.py::TestCrossCurrencyTickers::test_asml_cleared PASSED       [ 68%]
test_agents.py::TestCrossCurrencyTickers::test_brkb_cleared PASSED       [ 68%]
test_agents.py::TestCrossCurrencyTickers::test_tsm_cleared PASSED        [ 69%]
test_agents.py::TestCrossCurrencyTickers::test_usd_ticker_not_affected PASSED [ 69%]
test_agents.py::TestHarryPortfolio::test_buy_signal_with_shares_is_aligned PASSED [ 70%]
test_agents.py::TestHarryPortfolio::test_buy_signal_with_zero_shares_is_misaligned PASSED [ 70%]
test_agents.py::TestHarryPortfolio::test_check_alignment_all_cases PASSED [ 70%]
test_agents.py::TestHarryPortfolio::test_db_exception_propagates PASSED  [ 71%]
test_agents.py::TestHarryPortfolio::test_empty_portfolio_returns_zero_holdings PASSED [ 71%]
test_agents.py::TestHarryPortfolio::test_get_action_all_cases PASSED     [ 72%]
test_agents.py::TestHarryPortfolio::test_sell_signal_with_shares_is_misaligned PASSED [ 72%]
test_agents.py::TestHarryPortfolio::test_sell_with_zero_shares_is_aligned PASSED [ 73%]
test_agents.py::TestHarryPortfolio::test_ticker_not_in_analysis_skipped PASSED [ 73%]
test_agents.py::TestARecordImprovements::test_db_error_no_crash PASSED   [ 74%]
test_agents.py::TestARecordImprovements::test_empty_results_no_crash PASSED [ 74%]
test_agents.py::TestARecordImprovements::test_haiku_model_used PASSED    [ 75%]
test_agents.py::TestARecordImprovements::test_signal_counts_passed_to_claude PASSED [ 75%]
test_agents.py::TestNikOptimizeCode::test_agents_py_too_large_returns_none PASSED [ 76%]
test_agents.py::TestNikOptimizeCode::test_db_save_fails_no_crash PASSED  [ 76%]
test_agents.py::TestNikOptimizeCode::test_no_diff_blocks_returns_none PASSED [ 77%]
test_agents.py::TestNikOptimizeCode::test_no_github_token_returns_none PASSED [ 77%]
test_agents.py::TestNikOptimizeCode::test_no_rejected_suggestions_shows_none_placeholder PASSED [ 78%]
test_agents.py::TestNikOptimizeCode::test_rejected_suggestions_included_in_prompt PASSED [ 78%]
test_agents.py::TestNikOptimizeCode::test_summary_extracted_from_first_summary_line PASSED [ 79%]
test_agents.py::TestNikOptimizeCode::test_valid_diff_saves_to_db_and_returns PASSED [ 79%]
test_agents.py::TestNikOptimizeCode::test_workflow_log_query_filtered_by_5_days PASSED [ 80%]
test_agents.py::TestNikParseDiffBlocks::test_empty_string_returns_empty PASSED [ 80%]
test_agents.py::TestNikParseDiffBlocks::test_malformed_no_find_replace_returns_empty PASSED [ 80%]
test_agents.py::TestNikParseDiffBlocks::test_multiple_blocks PASSED      [ 81%]
test_agents.py::TestNikParseDiffBlocks::test_none_input_returns_empty PASSED [ 81%]
test_agents.py::TestNikParseDiffBlocks::test_noop_diff_find_equals_replace_still_extracted PASSED [ 82%]
test_agents.py::TestNikParseDiffBlocks::test_single_block_extracts_find PASSED [ 82%]
test_agents.py::TestCheckpointDatabase::test_commit_called_once_for_batch PASSED [ 83%]
test_agents.py::TestCheckpointDatabase::test_db_error_no_crash PASSED    [ 83%]
test_agents.py::TestCheckpointDatabase::test_saves_valid_ticker_and_commits PASSED [ 84%]
test_agents.py::TestCheckpointDatabase::test_skips_needs_review PASSED   [ 84%]
test_agents.py::TestCheckpointDatabase::test_skips_none_s1 PASSED        [ 85%]
test_agents.py::TestCheckpointDatabase::test_skips_zero_confidence PASSED [ 85%]
test_agents.py::TestCalculateROI::test_buy_signal_price_up_is_win PASSED [ 86%]
test_agents.py::TestCalculateROI::test_exception_returns_error_dict_no_crash PASSED [ 86%]
test_agents.py::TestCalculateROI::test_meets_win_target_flag_true_when_above_threshold PASSED [ 87%]
test_agents.py::TestCalculateROI::test_no_data_returns_none_values PASSED [ 87%]
test_agents.py::TestCalculateROI::test_no_future_snapshot_skipped PASSED [ 88%]
test_agents.py::TestCalculateROI::test_portfolio_return_below_target PASSED [ 88%]
test_agents.py::TestCalculateROI::test_portfolio_return_computed_from_latest_snapshot PASSED [ 89%]
test_agents.py::TestCalculateROI::test_portfolio_return_no_snapshot_yet PASSED [ 89%]
test_agents.py::TestCalculateROI::test_sell_signal_price_down_is_win PASSED [ 90%]
test_agents.py::TestCalculateROI::test_signal_too_new_not_evaluated PASSED [ 90%]
test_agents.py::TestSnapshotPortfolio::test_computes_total_value_and_cost_correctly PASSED [ 90%]
test_agents.py::TestSnapshotPortfolio::test_db_error_logs_warning_no_crash PASSED [ 91%]
test_agents.py::TestSnapshotPortfolio::test_empty_portfolio_does_not_add_snapshot PASSED [ 91%]
test_agents.py::TestPortfolioReturnHistory::test_daily_excludes_weekends PASSED [ 92%]
test_agents.py::TestPortfolioReturnHistory::test_monthly_uses_last_snapshot_of_month PASSED [ 92%]
test_agents.py::TestPortfolioReturnHistory::test_no_data_returns_empty_lists PASSED [ 93%]
test_agents.py::TestPegAlphaVantage::test_av_failure_does_not_break_prefetch PASSED [ 93%]
test_agents.py::TestPegAlphaVantage::test_daily_cap_20_of_30_stale PASSED [ 94%]
test_agents.py::TestPegAlphaVantage::test_fetch_success_returns_float PASSED [ 94%]
test_agents.py::TestPegAlphaVantage::test_in_refresh_hour_fresh_value_wins PASSED [ 95%]
test_agents.py::TestPegAlphaVantage::test_outside_refresh_hour_no_av_call_and_carry_forward PASSED [ 95%]
test_agents.py::TestPegAlphaVantage::test_peg_none_dash_missing_are_safe PASSED [ 96%]
test_agents.py::TestPegAlphaVantage::test_per_ticker_exception_skips_and_continues PASSED [ 96%]
test_agents.py::TestPegAlphaVantage::test_rate_limit_information_breaks_batch PASSED [ 97%]
test_agents.py::TestPegAlphaVantage::test_rate_limit_note_breaks_batch PASSED [ 97%]
test_agents.py::TestNewsTranslate::test_news_key_deterministic_and_matches_formula PASSED [ 98%]
test_agents.py::TestNewsTranslate::test_translate_bad_llm_response_does_not_crash PASSED [ 98%]
test_agents.py::TestNewsTranslate::test_translate_new_items_saved PASSED [ 99%]
test_agents.py::TestNewsTranslate::test_translate_respects_max_per_run_cap PASSED [ 99%]
test_agents.py::TestNewsTranslate::test_translate_skips_already_translated PASSED [100%]

============================== warnings summary ===============================
models.py:5: 1 warning
test_main.py: 24 warnings
  D:\AI_Project\Dashboard_Share\models.py:5: MovedIn20Warning: The ``declarative_base()`` function is now available as sqlalchemy.orm.declarative_base(). (deprecated since: 2.0) (Background on SQLAlchemy 2.0 at: https://sqlalche.me/e/b8d9)
    Base = declarative_base()

.venv\Lib\site-packages\starlette\_utils.py:17: 31 warnings
test_main.py: 68 warnings
  D:\AI_Project\Dashboard_Share\.venv\Lib\site-packages\starlette\_utils.py:17: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    return asyncio.iscoroutinefunction(obj) or (

.venv\Lib\site-packages\fastapi\routing.py:211: 27 warnings
  D:\AI_Project\Dashboard_Share\.venv\Lib\site-packages\fastapi\routing.py:211: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    is_coroutine = asyncio.iscoroutinefunction(dependant.call)

main.py:315
  D:\AI_Project\Dashboard_Share\main.py:315: DeprecationWarning: 
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

main.py:496
  D:\AI_Project\Dashboard_Share\main.py:496: DeprecationWarning: 
          on_event is deprecated, use lifespan event handlers instead.
  
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    @app.on_event("shutdown")

test_main.py: 56 warnings
  D:\AI_Project\Dashboard_Share\.venv\Lib\site-packages\starlette\_utils.py:18: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    callable(obj) and asyncio.iscoroutinefunction(obj.__call__)

test_main.py: 56 warnings
  D:\AI_Project\Dashboard_Share\.venv\Lib\site-packages\httpx\_client.py:690: DeprecationWarning: The 'app' shortcut is now deprecated. Use the explicit style 'transport=WSGITransport(app=...)' instead.
    warnings.warn(message, DeprecationWarning)

test_main.py::TestWorkflowEndpoint::test_workflow_monday_mode_flag_true
test_main.py::TestWorkflowEndpoint::test_workflow_normal_mode_flag_false
test_main.py::TestWorkflowEndpoint::test_workflow_response_has_job_id
test_main.py::TestWorkflowEndpoint::test_workflow_sets_status_to_running
test_main.py::TestWorkflowEndpoint::test_workflow_starts_immediately_no_blocking
  D:\AI_Project\Dashboard_Share\main.py:950: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    _job["started_at"] = datetime.utcnow().isoformat()

test_main.py::TestWorkflowEndpoint::test_workflow_no_stocks_returns_no_stocks
  D:\AI_Project\Dashboard_Share\main.py:942: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    "timestamp": datetime.utcnow().isoformat()

test_main.py::TestWorkflowResume::test_resume_pending_stocks_starts_workflow
  D:\AI_Project\Dashboard_Share\main.py:1038: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    _job["started_at"]  = datetime.utcnow().isoformat()

test_main.py::TestWorkflowBackground::test_bg_exception_sends_line_notification
test_main.py::TestWorkflowBackground::test_bg_exception_sets_error_status
  D:\AI_Project\Dashboard_Share\main.py:303: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    _job["finished_at"] = datetime.utcnow().isoformat()

test_main.py::TestNikCheckStatusEndpoint::test_find_block_gone_marks_complete
  D:\AI_Project\Dashboard_Share\main.py:1190: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    item.applied_at = datetime.utcnow()

test_main.py: 26 warnings
  D:\AI_Project\Dashboard_Share\main.py:168: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    now = datetime.utcnow()

test_main.py::TestLoginRateLimit::test_lock_expires_after_window
  D:\AI_Project\Dashboard_Share\test_main.py:949: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    rec["lock_until"] = _dt.utcnow() - _td(seconds=1)

test_agents.py::TestPegAlphaVantage::test_av_failure_does_not_break_prefetch
  D:\AI_Project\Dashboard_Share\test_agents.py:1892: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    self.orc.PEG_REFRESH_UTC_HOUR = datetime.utcnow().hour

test_agents.py::TestPegAlphaVantage::test_av_failure_does_not_break_prefetch
test_agents.py::TestPegAlphaVantage::test_daily_cap_20_of_30_stale
test_agents.py::TestPegAlphaVantage::test_in_refresh_hour_fresh_value_wins
test_agents.py::TestPegAlphaVantage::test_outside_refresh_hour_no_av_call_and_carry_forward
  D:\AI_Project\Dashboard_Share\agents.py:609: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    if AV_KEY and datetime.utcnow().hour == self.PEG_REFRESH_UTC_HOUR:

test_agents.py::TestPegAlphaVantage::test_daily_cap_20_of_30_stale
  D:\AI_Project\Dashboard_Share\test_agents.py:1875: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    self.orc.PEG_REFRESH_UTC_HOUR = datetime.utcnow().hour

test_agents.py::TestPegAlphaVantage::test_in_refresh_hour_fresh_value_wins
  D:\AI_Project\Dashboard_Share\test_agents.py:1859: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    self.orc.PEG_REFRESH_UTC_HOUR = datetime.utcnow().hour  # บังคับให้ "ในรอบ"

test_agents.py::TestPegAlphaVantage::test_outside_refresh_hour_no_av_call_and_carry_forward
  D:\AI_Project\Dashboard_Share\test_agents.py:1842: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    self.orc.PEG_REFRESH_UTC_HOUR = (datetime.utcnow().hour + 3) % 24  # บังคับให้ "นอกรอบ" เสมอ

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
===================== 210 passed, 312 warnings in 11.67s ======================
