============================= test session starts =============================
platform win32 -- Python 3.14.6, pytest-9.1.1, pluggy-1.6.0 -- D:\AI_Project\Dashboard_Share\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\AI_Project\Dashboard_Share
plugins: anyio-3.7.1, timeout-2.4.0
collecting ... collected 182 items

test_main.py::TestHealth::test_health_is_fast PASSED                     [  0%]
test_main.py::TestHealth::test_health_returns_200 PASSED                 [  1%]
test_main.py::TestHealth::test_health_returns_ok_status PASSED           [  1%]
test_main.py::TestWorkflowEndpoint::test_workflow_already_running_returns_already_running PASSED [  2%]
test_main.py::TestWorkflowEndpoint::test_workflow_monday_mode_flag_true PASSED [  2%]
test_main.py::TestWorkflowEndpoint::test_workflow_no_stocks_returns_no_stocks PASSED [  3%]
test_main.py::TestWorkflowEndpoint::test_workflow_normal_mode_flag_false PASSED [  3%]
test_main.py::TestWorkflowEndpoint::test_workflow_response_has_job_id PASSED [  4%]
test_main.py::TestWorkflowEndpoint::test_workflow_sets_status_to_running PASSED [  4%]
test_main.py::TestWorkflowEndpoint::test_workflow_starts_immediately_no_blocking PASSED [  5%]
test_main.py::TestWorkflowResume::test_resume_all_done_today_returns_complete PASSED [  6%]
test_main.py::TestWorkflowResume::test_resume_already_running_skips PASSED [  6%]
test_main.py::TestWorkflowResume::test_resume_pending_stocks_starts_workflow PASSED [  7%]
test_main.py::TestLineNotification::test_api_400_no_crash PASSED         [  7%]
test_main.py::TestLineNotification::test_api_500_no_crash PASSED         [  8%]
test_main.py::TestLineNotification::test_empty_message_no_crash PASSED   [  8%]
test_main.py::TestLineNotification::test_network_error_no_crash PASSED   [  9%]
test_main.py::TestLineNotification::test_no_token_no_crash PASSED        [  9%]
test_main.py::TestLineNotification::test_timeout_no_crash PASSED         [ 10%]
test_main.py::TestWorkflowBackground::test_bg_exception_sends_line_notification PASSED [ 10%]
test_main.py::TestWorkflowBackground::test_bg_exception_sets_error_status PASSED [ 11%]
test_main.py::TestNikSuggestionsEndpoint::test_empty_db_returns_zero_count PASSED [ 12%]
test_main.py::TestNikSuggestionsEndpoint::test_limit_10_records PASSED   [ 12%]
test_main.py::TestNikSuggestionsEndpoint::test_pending_count_correct PASSED [ 13%]
test_main.py::TestNikSuggestionsEndpoint::test_response_has_required_fields PASSED [ 13%]
test_main.py::TestNikSuggestionsEndpoint::test_suggestion_item_has_required_fields PASSED [ 14%]
test_main.py::TestDashboardAuth::test_401_response_has_cors_header PASSED [ 14%]
test_main.py::TestDashboardAuth::test_health_stays_public_when_auth_on PASSED [ 15%]
test_main.py::TestDashboardAuth::test_login_correct_password_returns_token PASSED [ 15%]
test_main.py::TestDashboardAuth::test_login_wrong_password_401 PASSED    [ 16%]
test_main.py::TestDashboardAuth::test_no_env_auth_disabled_protected_route_open PASSED [ 17%]
test_main.py::TestDashboardAuth::test_no_env_login_returns_auth_disabled_flag PASSED [ 17%]
test_main.py::TestDashboardAuth::test_options_preflight_not_blocked PASSED [ 18%]
test_main.py::TestDashboardAuth::test_protected_route_with_token_200 PASSED [ 18%]
test_main.py::TestDashboardAuth::test_protected_route_without_token_401 PASSED [ 19%]
test_main.py::TestDashboardAuth::test_protected_route_wrong_token_401 PASSED [ 19%]
test_main.py::TestLoginRateLimit::test_lock_expires_after_window PASSED  [ 20%]
test_main.py::TestLoginRateLimit::test_locked_even_with_correct_password PASSED [ 20%]
test_main.py::TestLoginRateLimit::test_lockout_after_max_fails PASSED    [ 21%]
test_main.py::TestLoginRateLimit::test_success_resets_fail_count PASSED  [ 21%]
test_main.py::TestNewsEndpoint::test_news_broken_json_row_skipped_not_500 PASSED [ 22%]
test_main.py::TestNewsEndpoint::test_news_dedup_across_tickers_and_sort PASSED [ 23%]
test_main.py::TestNewsEndpoint::test_news_empty_cache_returns_empty_list PASSED [ 23%]
test_main.py::TestNewsEndpoint::test_news_translation_applied PASSED     [ 24%]
test_main.py::TestNewsEndpoint::test_news_untranslated_falls_back_to_english FAILED [ 24%]
test_agents.py::TestSafeFloat::test_actual_float PASSED                  [ 25%]
test_agents.py::TestSafeFloat::test_empty_string_returns_none PASSED     [ 25%]
test_agents.py::TestSafeFloat::test_garbage_string_returns_none PASSED   [ 26%]
test_agents.py::TestSafeFloat::test_integer_string PASSED                [ 26%]
test_agents.py::TestSafeFloat::test_mixed_garbage PASSED                 [ 27%]
test_agents.py::TestSafeFloat::test_negative_float_string PASSED         [ 28%]
test_agents.py::TestSafeFloat::test_negative_price_returns_none PASSED   [ 28%]
test_agents.py::TestSafeFloat::test_none_returns_none PASSED             [ 29%]
test_agents.py::TestSafeFloat::test_placeholder_NaN PASSED               [ 29%]
test_agents.py::TestSafeFloat::test_placeholder_dash PASSED              [ 30%]
test_agents.py::TestSafeFloat::test_placeholder_na PASSED                [ 30%]
test_agents.py::TestSafeFloat::test_placeholder_nan PASSED               [ 31%]
test_agents.py::TestSafeFloat::test_placeholder_none_string PASSED       [ 31%]
test_agents.py::TestSafeFloat::test_placeholder_zero_float_string PASSED [ 32%]
test_agents.py::TestSafeFloat::test_placeholder_zero_string PASSED       [ 32%]
test_agents.py::TestSafeFloat::test_positive_float_string PASSED         [ 33%]
test_agents.py::TestSafeFloat::test_positive_price_ok PASSED             [ 34%]
test_agents.py::TestSafeFloat::test_price_dash_returns_none PASSED       [ 34%]
test_agents.py::TestSafeFloat::test_price_na_returns_none PASSED         [ 35%]
test_agents.py::TestSafeFloat::test_price_none_returns_none PASSED       [ 35%]
test_agents.py::TestSafeFloat::test_whitespace_only PASSED               [ 36%]
test_agents.py::TestSafeFloat::test_zero_price_returns_none PASSED       [ 36%]
test_agents.py::TestNattyFallback::test_all_tiers_fail_skips_ticker PASSED [ 37%]
test_agents.py::TestNattyFallback::test_pe_negative_is_preserved PASSED  [ 37%]
test_agents.py::TestNattyFallback::test_tier1_yfinance_success PASSED    [ 38%]
test_agents.py::TestNattyFallback::test_tier2_finnhub_fallback_on_yfinance_429 PASSED [ 39%]
test_agents.py::TestNattyFallback::test_tier3_alpha_vantage_fallback PASSED [ 39%]
test_agents.py::TestMarketAuxNews::test_format_news_avg_sentiment PASSED [ 40%]
test_agents.py::TestMarketAuxNews::test_format_news_empty_returns_no_news PASSED [ 40%]
test_agents.py::TestMarketAuxNews::test_format_news_negative_sentiment PASSED [ 41%]
test_agents.py::TestMarketAuxNews::test_group_similar_in_url PASSED      [ 41%]
test_agents.py::TestMarketAuxNews::test_limit_6_in_url PASSED            [ 42%]
test_agents.py::TestMarketAuxNews::test_monday_mode_published_after_friday PASSED [ 42%]
test_agents.py::TestMarketAuxNews::test_regular_mode_published_after_yesterday PASSED [ 43%]
test_agents.py::TestNumAnalyzeStocks::test_invalid_signal_defaults_to_hold PASSED [ 43%]
test_agents.py::TestNumAnalyzeStocks::test_json_parse_fail_uses_fallback PASSED [ 44%]
test_agents.py::TestNumAnalyzeStocks::test_negative_pe_included_in_prompt PASSED [ 45%]
test_agents.py::TestNumAnalyzeStocks::test_no_price_data_sets_zero_confidence PASSED [ 45%]
test_agents.py::TestNumAnalyzeStocks::test_valid_buy_signal PASSED       [ 46%]
test_agents.py::TestMudValidation::test_exception_flags_needs_review PASSED [ 46%]
test_agents.py::TestMudValidation::test_json_parse_fail_flags_needs_review PASSED [ 47%]
test_agents.py::TestMudValidation::test_needs_review_ticker_skipped_in_db PASSED [ 47%]
test_agents.py::TestMudValidation::test_valid_pass_result PASSED         [ 48%]
test_agents.py::TestNanQACheck::test_exception_returns_reject PASSED     [ 48%]
test_agents.py::TestNanQACheck::test_html_stripped_from_approval_reason PASSED [ 49%]
test_agents.py::TestNanQACheck::test_html_stripped_from_issues PASSED    [ 50%]
test_agents.py::TestNanQACheck::test_json_parse_fail_returns_reject PASSED [ 50%]
test_agents.py::TestNanQACheck::test_pass_result PASSED                  [ 51%]
test_agents.py::TestNanQACheck::test_report_html_stripped_before_qa PASSED [ 51%]
test_agents.py::TestWorkflow::test_complete_workflow_pass PASSED         [ 52%]
test_agents.py::TestWorkflow::test_empty_analysis_aborts_workflow PASSED [ 52%]
test_agents.py::TestWorkflow::test_empty_news_data_aborts_workflow PASSED [ 53%]
test_agents.py::TestWorkflow::test_no_shared_state_between_claude_calls PASSED [ 53%]
test_agents.py::TestWorkflow::test_qa_reject_retries_up_to_max PASSED    [ 54%]
test_agents.py::TestWorkflow::test_workflow_log_resets_each_run PASSED   [ 54%]
test_agents.py::TestColsonTrade::test_garbage_response_returns_none PASSED [ 55%]
test_agents.py::TestColsonTrade::test_parse_error_returns_none PASSED    [ 56%]
test_agents.py::TestColsonTrade::test_ticker_uppercased PASSED           [ 56%]
test_agents.py::TestColsonTrade::test_valid_buy_trade PASSED             [ 57%]
test_agents.py::TestUpdateDatabase::test_batch_commit_once PASSED        [ 57%]
test_agents.py::TestUpdateDatabase::test_current_price_updated PASSED    [ 58%]
test_agents.py::TestUpdateDatabase::test_needs_review_skipped PASSED     [ 58%]
test_agents.py::TestUpdateDatabase::test_zero_confidence_skipped PASSED  [ 59%]
test_agents.py::TestMarketCapUnit::test_mcap_has_M_USD_suffix PASSED     [ 59%]
test_agents.py::TestMarketCapUnit::test_mcap_none_shows_na PASSED        [ 60%]
test_agents.py::TestMarketCapUnit::test_mcap_small_value PASSED          [ 60%]
test_agents.py::TestNewHighFlag::test_ath_and_atl_mutually_exclusive PASSED [ 61%]
test_agents.py::TestNewHighFlag::test_big_gap_above_clears_range PASSED  [ 62%]
test_agents.py::TestNewHighFlag::test_new_high_flag_set PASSED           [ 62%]
test_agents.py::TestNewHighFlag::test_new_low_below_threshold_clears_range PASSED [ 63%]
test_agents.py::TestNewHighFlag::test_new_low_exact_boundary PASSED      [ 63%]
test_agents.py::TestNewHighFlag::test_new_low_flag_set PASSED            [ 64%]
test_agents.py::TestNewHighFlag::test_new_low_low_updated PASSED         [ 64%]
test_agents.py::TestNewHighFlag::test_price_far_below_low_clears_range PASSED [ 65%]
test_agents.py::TestNewHighFlag::test_within_range_no_flag PASSED        [ 65%]
test_agents.py::TestMudRecommendationFormat::test_pass_fail_only_constraint_in_source PASSED [ 66%]
test_agents.py::TestMudRecommendationFormat::test_pass_with_warning_not_allowed PASSED [ 67%]
test_agents.py::TestCrossCurrencyTickers::test_aapl_not_affected PASSED  [ 67%]
test_agents.py::TestCrossCurrencyTickers::test_asml_cleared PASSED       [ 68%]
test_agents.py::TestCrossCurrencyTickers::test_brkb_cleared PASSED       [ 68%]
test_agents.py::TestCrossCurrencyTickers::test_tsm_cleared PASSED        [ 69%]
test_agents.py::TestCrossCurrencyTickers::test_usd_ticker_not_affected PASSED [ 69%]
test_agents.py::TestHarryPortfolio::test_buy_signal_with_shares_is_aligned PASSED [ 70%]
test_agents.py::TestHarryPortfolio::test_buy_signal_with_zero_shares_is_misaligned PASSED [ 70%]
test_agents.py::TestHarryPortfolio::test_check_alignment_all_cases PASSED [ 71%]
test_agents.py::TestHarryPortfolio::test_db_exception_propagates PASSED  [ 71%]
test_agents.py::TestHarryPortfolio::test_empty_portfolio_returns_zero_holdings PASSED [ 72%]
test_agents.py::TestHarryPortfolio::test_get_action_all_cases PASSED     [ 73%]
test_agents.py::TestHarryPortfolio::test_sell_signal_with_shares_is_misaligned PASSED [ 73%]
test_agents.py::TestHarryPortfolio::test_sell_with_zero_shares_is_aligned PASSED [ 74%]
test_agents.py::TestHarryPortfolio::test_ticker_not_in_analysis_skipped PASSED [ 74%]
test_agents.py::TestARecordImprovements::test_db_error_no_crash PASSED   [ 75%]
test_agents.py::TestARecordImprovements::test_empty_results_no_crash PASSED [ 75%]
test_agents.py::TestARecordImprovements::test_haiku_model_used PASSED    [ 76%]
test_agents.py::TestARecordImprovements::test_signal_counts_passed_to_claude PASSED [ 76%]
test_agents.py::TestNikOptimizeCode::test_agents_py_too_large_returns_none PASSED [ 77%]
test_agents.py::TestNikOptimizeCode::test_db_save_fails_no_crash PASSED  [ 78%]
test_agents.py::TestNikOptimizeCode::test_no_diff_blocks_returns_none PASSED [ 78%]
test_agents.py::TestNikOptimizeCode::test_no_github_token_returns_none PASSED [ 79%]
test_agents.py::TestNikOptimizeCode::test_summary_extracted_from_first_summary_line PASSED [ 79%]
test_agents.py::TestNikOptimizeCode::test_valid_diff_saves_to_db_and_returns PASSED [ 80%]
test_agents.py::TestCheckpointDatabase::test_commit_called_once_for_batch PASSED [ 80%]
test_agents.py::TestCheckpointDatabase::test_db_error_no_crash PASSED    [ 81%]
test_agents.py::TestCheckpointDatabase::test_saves_valid_ticker_and_commits PASSED [ 81%]
test_agents.py::TestCheckpointDatabase::test_skips_needs_review PASSED   [ 82%]
test_agents.py::TestCheckpointDatabase::test_skips_none_s1 PASSED        [ 82%]
test_agents.py::TestCheckpointDatabase::test_skips_zero_confidence PASSED [ 83%]
test_agents.py::TestCalculateROI::test_buy_signal_price_up_is_win PASSED [ 84%]
test_agents.py::TestCalculateROI::test_exception_returns_error_dict_no_crash PASSED [ 84%]
test_agents.py::TestCalculateROI::test_meets_win_target_flag_true_when_above_threshold PASSED [ 85%]
test_agents.py::TestCalculateROI::test_no_data_returns_none_values PASSED [ 85%]
test_agents.py::TestCalculateROI::test_no_future_snapshot_skipped PASSED [ 86%]
test_agents.py::TestCalculateROI::test_portfolio_return_below_target PASSED [ 86%]
test_agents.py::TestCalculateROI::test_portfolio_return_computed_from_latest_snapshot PASSED [ 87%]
test_agents.py::TestCalculateROI::test_portfolio_return_no_snapshot_yet PASSED [ 87%]
test_agents.py::TestCalculateROI::test_sell_signal_price_down_is_win PASSED [ 88%]
test_agents.py::TestCalculateROI::test_signal_too_new_not_evaluated PASSED [ 89%]
test_agents.py::TestSnapshotPortfolio::test_computes_total_value_and_cost_correctly PASSED [ 89%]
test_agents.py::TestSnapshotPortfolio::test_db_error_logs_warning_no_crash PASSED [ 90%]
test_agents.py::TestSnapshotPortfolio::test_empty_portfolio_does_not_add_snapshot PASSED [ 90%]
test_agents.py::TestPortfolioReturnHistory::test_daily_excludes_weekends PASSED [ 91%]
test_agents.py::TestPortfolioReturnHistory::test_monthly_uses_last_snapshot_of_month PASSED [ 91%]
test_agents.py::TestPortfolioReturnHistory::test_no_data_returns_empty_lists PASSED [ 92%]
test_agents.py::TestPegAlphaVantage::test_av_failure_does_not_break_prefetch PASSED [ 92%]
test_agents.py::TestPegAlphaVantage::test_daily_cap_20_of_30_stale PASSED [ 93%]
test_agents.py::TestPegAlphaVantage::test_fetch_success_returns_float PASSED [ 93%]
test_agents.py::TestPegAlphaVantage::test_in_refresh_hour_fresh_value_wins PASSED [ 94%]
test_agents.py::TestPegAlphaVantage::test_outside_refresh_hour_no_av_call_and_carry_forward PASSED [ 95%]
test_agents.py::TestPegAlphaVantage::test_peg_none_dash_missing_are_safe PASSED [ 95%]
test_agents.py::TestPegAlphaVantage::test_per_ticker_exception_skips_and_continues PASSED [ 96%]
test_agents.py::TestPegAlphaVantage::test_rate_limit_information_breaks_batch PASSED [ 96%]
test_agents.py::TestPegAlphaVantage::test_rate_limit_note_breaks_batch PASSED [ 97%]
test_agents.py::TestNewsTranslate::test_news_key_deterministic_and_matches_formula PASSED [ 97%]
test_agents.py::TestNewsTranslate::test_translate_bad_llm_response_does_not_crash PASSED [ 98%]
test_agents.py::TestNewsTranslate::test_translate_new_items_saved PASSED [ 98%]
test_agents.py::TestNewsTranslate::test_translate_respects_max_per_run_cap PASSED [ 99%]
test_agents.py::TestNewsTranslate::test_translate_skips_already_translated PASSED [100%]

================================== FAILURES ===================================
________ TestNewsEndpoint.test_news_untranslated_falls_back_to_english ________

self = <test_main.TestNewsEndpoint testMethod=test_news_untranslated_falls_back_to_english>

    def test_news_untranslated_falls_back_to_english(self):
        """\u0e02\u0e48\u0e32\u0e27\u0e22\u0e31\u0e07\u0e44\u0e21\u0e48\u0e16\u0e39\u0e01\u0e41\u0e1b\u0e25 (\u0e40\u0e1e\u0e34\u0e48\u0e07\u0e40\u0e02\u0e49\u0e32 cache) \u2192 \u0e42\u0e0a\u0e27\u0e4c\u0e2d\u0e31\u0e07\u0e01\u0e24\u0e29\u0e15\u0e49\u0e19\u0e09\u0e1a\u0e31\u0e1a + translated=False \u0e44\u0e21\u0e48 error"""
        import json as _json
        item = {"title": "Fresh news not yet translated", "summary": "orig", "source": "Reuters",
                "published_at": 2000, "from_source": "finnhub"}
        subq = MagicMock()
        newsq = MagicMock()
        newsq.join.return_value.all.return_value = [MagicMock(ticker="NVDA", news_json=_json.dumps([item]))]
        trq = MagicMock()
        trq.filter.return_value.all.return_value = []  # ยังไม่มีคำแปล
        db = MagicMock()
        db.query.side_effect = [subq, newsq, trq]
        app_module.app.dependency_overrides[app_module.get_db] = lambda: (yield db)
    
        resp = self.client.get("/news")
        a = resp.json()["articles"][0]
        self.assertEqual(a["headline"], "Fresh news not yet translated")
>       self.assertIsNone(a["sentiment"])
                          ^^^^^^^^^^^^^^
E       KeyError: 'sentiment'

test_main.py:768: KeyError
============================== warnings summary ===============================
models.py:5
test_main.py::TestNikSuggestionsEndpoint::test_empty_db_returns_zero_count
test_main.py::TestNikSuggestionsEndpoint::test_limit_10_records
test_main.py::TestNikSuggestionsEndpoint::test_pending_count_correct
test_main.py::TestNikSuggestionsEndpoint::test_response_has_required_fields
test_main.py::TestNikSuggestionsEndpoint::test_suggestion_item_has_required_fields
  D:\AI_Project\Dashboard_Share\models.py:5: MovedIn20Warning: The ``declarative_base()`` function is now available as sqlalchemy.orm.declarative_base(). (deprecated since: 2.0) (Background on SQLAlchemy 2.0 at: https://sqlalche.me/e/b8d9)
    Base = declarative_base()

.venv\Lib\site-packages\starlette\_utils.py:17: 28 warnings
test_main.py: 38 warnings
  D:\AI_Project\Dashboard_Share\.venv\Lib\site-packages\starlette\_utils.py:17: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    return asyncio.iscoroutinefunction(obj) or (

.venv\Lib\site-packages\fastapi\routing.py:211: 24 warnings
  D:\AI_Project\Dashboard_Share\.venv\Lib\site-packages\fastapi\routing.py:211: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    is_coroutine = asyncio.iscoroutinefunction(dependant.call)

main.py:312
  D:\AI_Project\Dashboard_Share\main.py:312: DeprecationWarning: 
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

main.py:486
  D:\AI_Project\Dashboard_Share\main.py:486: DeprecationWarning: 
          on_event is deprecated, use lifespan event handlers instead.
  
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    @app.on_event("shutdown")

test_main.py: 37 warnings
  D:\AI_Project\Dashboard_Share\.venv\Lib\site-packages\starlette\_utils.py:18: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    callable(obj) and asyncio.iscoroutinefunction(obj.__call__)

test_main.py: 37 warnings
  D:\AI_Project\Dashboard_Share\.venv\Lib\site-packages\httpx\_client.py:690: DeprecationWarning: The 'app' shortcut is now deprecated. Use the explicit style 'transport=WSGITransport(app=...)' instead.
    warnings.warn(message, DeprecationWarning)

test_main.py::TestWorkflowEndpoint::test_workflow_monday_mode_flag_true
test_main.py::TestWorkflowEndpoint::test_workflow_normal_mode_flag_false
test_main.py::TestWorkflowEndpoint::test_workflow_response_has_job_id
test_main.py::TestWorkflowEndpoint::test_workflow_sets_status_to_running
test_main.py::TestWorkflowEndpoint::test_workflow_starts_immediately_no_blocking
  D:\AI_Project\Dashboard_Share\main.py:932: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    _job["started_at"] = datetime.utcnow().isoformat()

test_main.py::TestWorkflowEndpoint::test_workflow_no_stocks_returns_no_stocks
  D:\AI_Project\Dashboard_Share\main.py:924: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    "timestamp": datetime.utcnow().isoformat()

test_main.py::TestWorkflowResume::test_resume_pending_stocks_starts_workflow
  D:\AI_Project\Dashboard_Share\main.py:1020: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    _job["started_at"]  = datetime.utcnow().isoformat()

test_main.py::TestWorkflowBackground::test_bg_exception_sends_line_notification
test_main.py::TestWorkflowBackground::test_bg_exception_sets_error_status
  D:\AI_Project\Dashboard_Share\main.py:300: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    _job["finished_at"] = datetime.utcnow().isoformat()

test_main.py: 26 warnings
  D:\AI_Project\Dashboard_Share\main.py:165: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    now = datetime.utcnow()

test_main.py::TestLoginRateLimit::test_lock_expires_after_window
  D:\AI_Project\Dashboard_Share\test_main.py:668: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    rec["lock_until"] = _dt.utcnow() - _td(seconds=1)

test_agents.py::TestPegAlphaVantage::test_av_failure_does_not_break_prefetch
  D:\AI_Project\Dashboard_Share\test_agents.py:1779: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    self.orc.PEG_REFRESH_UTC_HOUR = datetime.utcnow().hour

test_agents.py::TestPegAlphaVantage::test_av_failure_does_not_break_prefetch
test_agents.py::TestPegAlphaVantage::test_daily_cap_20_of_30_stale
test_agents.py::TestPegAlphaVantage::test_in_refresh_hour_fresh_value_wins
test_agents.py::TestPegAlphaVantage::test_outside_refresh_hour_no_av_call_and_carry_forward
  D:\AI_Project\Dashboard_Share\agents.py:609: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    if AV_KEY and datetime.utcnow().hour == self.PEG_REFRESH_UTC_HOUR:

test_agents.py::TestPegAlphaVantage::test_daily_cap_20_of_30_stale
  D:\AI_Project\Dashboard_Share\test_agents.py:1762: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    self.orc.PEG_REFRESH_UTC_HOUR = datetime.utcnow().hour

test_agents.py::TestPegAlphaVantage::test_in_refresh_hour_fresh_value_wins
  D:\AI_Project\Dashboard_Share\test_agents.py:1746: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    self.orc.PEG_REFRESH_UTC_HOUR = datetime.utcnow().hour  # บังคับให้ "ในรอบ"

test_agents.py::TestPegAlphaVantage::test_outside_refresh_hour_no_av_call_and_carry_forward
  D:\AI_Project\Dashboard_Share\test_agents.py:1729: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    self.orc.PEG_REFRESH_UTC_HOUR = (datetime.utcnow().hour + 3) % 24  # บังคับให้ "นอกรอบ" เสมอ

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED test_main.py::TestNewsEndpoint::test_news_untranslated_falls_back_to_english
================ 1 failed, 181 passed, 218 warnings in 13.99s =================
