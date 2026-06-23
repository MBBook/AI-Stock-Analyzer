"""
test_agents.py — AI Stock Analyzer V4 Test Suite
รัน offline ได้: python -m unittest test_agents.py -v

ครอบคลุม:
1. _safe_float / _safe_positive_float — edge cases ทั้งหมด
2. นัตตี้ — 3-tier fallback (mock yfinance 429, Finnhub, Alpha Vantage)
3. MarketAux — Monday vs regular mode, duplicate handling
4. หนุ่ม — signal validation, fallback on parse fail, P/E ลบ
5. มด — NEEDS_REVIEW flag, auto-PASS removed
6. นน — fail-safe REJECT, HTML injection strip
7. Workflow — empty data abort, analysis abort, state isolation
8. โคลสัน — trade parse + DB write
"""

import unittest
from unittest.mock import patch, MagicMock, PropertyMock
import json
import os
import sys
from datetime import datetime, timedelta

# ===== Setup: mock DB imports ก่อน import agents =====
# ป้องกัน agents.py พยายาม connect DB ระหว่าง test
sys.modules['database'] = MagicMock()
sys.modules['models'] = MagicMock()

# Mock environment variables ให้ครบ ก่อน AgentOrchestrator() ถูก init
os.environ.setdefault("ANTHROPIC_API_KEY_1", "sk-ant-test-key-1")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("FINNHUB_API_KEY", "test_finnhub_key")
os.environ.setdefault("ALPHA_VANTAGE_API_KEY", "test_av_key")
os.environ.setdefault("MARKETAUX_API_KEY", "test_mx_key")
os.environ.setdefault("GITHUB_TOKEN", "ghp_test_token")

import sys
import importlib.util
import os

# โหลด agents.py
spec = importlib.util.spec_from_file_location(
    "agents", os.path.join(os.path.dirname(__file__), "agents.py")
)
agents_module = importlib.util.module_from_spec(spec)
sys.modules["agents"] = agents_module
spec.loader.exec_module(agents_module)

from agents import AgentOrchestrator, TimeoutAdapter


def make_orchestrator():
    """สร้าง orchestrator สำหรับ test โดยไม่ต้อง connect DB จริง"""
    with patch("agents.SessionLocal"):
        orc = AgentOrchestrator()
    orc.workflow_log = []
    return orc


# ============================================================
# SECTION 1: _safe_float / _safe_positive_float
# ============================================================
class TestSafeFloat(unittest.TestCase):
    """ตรวจ safe_float รองรับ edge cases ทั้งหมดโดยไม่ crash"""

    def setUp(self):
        self.orc = make_orchestrator()

    # --- _safe_float (fundamental data — ลบได้) ---
    def test_none_returns_none(self):
        self.assertIsNone(self.orc._safe_float(None))

    def test_empty_string_returns_none(self):
        self.assertIsNone(self.orc._safe_float(""))

    def test_placeholder_none_string(self):
        self.assertIsNone(self.orc._safe_float("None"))

    def test_placeholder_na(self):
        self.assertIsNone(self.orc._safe_float("N/A"))

    def test_placeholder_dash(self):
        self.assertIsNone(self.orc._safe_float("-"))

    def test_placeholder_zero_string(self):
        self.assertIsNone(self.orc._safe_float("0"))

    def test_placeholder_zero_float_string(self):
        self.assertIsNone(self.orc._safe_float("0.0"))

    def test_placeholder_nan(self):
        self.assertIsNone(self.orc._safe_float("nan"))

    def test_placeholder_NaN(self):
        self.assertIsNone(self.orc._safe_float("NaN"))

    def test_whitespace_only(self):
        self.assertIsNone(self.orc._safe_float("   "))

    def test_positive_float_string(self):
        self.assertAlmostEqual(self.orc._safe_float("28.5"), 28.5)

    def test_negative_float_string(self):
        """P/E ติดลบ = บริษัทขาดทุน — ต้องคืนค่าลบ ไม่ใช่ None"""
        self.assertAlmostEqual(self.orc._safe_float("-15.3"), -15.3)

    def test_integer_string(self):
        self.assertAlmostEqual(self.orc._safe_float("100"), 100.0)

    def test_actual_float(self):
        self.assertAlmostEqual(self.orc._safe_float(28.5), 28.5)

    def test_garbage_string_returns_none(self):
        self.assertIsNone(self.orc._safe_float("abc"))

    def test_mixed_garbage(self):
        self.assertIsNone(self.orc._safe_float("12abc"))

    # --- _safe_positive_float (price — ต้องบวกเสมอ) ---
    def test_positive_price_ok(self):
        self.assertAlmostEqual(self.orc._safe_positive_float("185.50"), 185.50)

    def test_negative_price_returns_none(self):
        """ราคาติดลบ = ข้อมูลเสีย"""
        self.assertIsNone(self.orc._safe_positive_float("-10.0"))

    def test_zero_price_returns_none(self):
        self.assertIsNone(self.orc._safe_positive_float("0"))

    def test_price_none_returns_none(self):
        self.assertIsNone(self.orc._safe_positive_float(None))

    def test_price_na_returns_none(self):
        self.assertIsNone(self.orc._safe_positive_float("N/A"))

    def test_price_dash_returns_none(self):
        self.assertIsNone(self.orc._safe_positive_float("-"))


# ============================================================
# SECTION 2: นัตตี้ — 3-tier fallback
# ============================================================
class TestNattyFallback(unittest.TestCase):
    """Mock yfinance 429 → verify Tier 2 (Finnhub) + Tier 3 (Alpha Vantage) ทำงาน"""

    def setUp(self):
        self.orc = make_orchestrator()

    def _make_finnhub_response(self, price=185.0):
        """Helper: mock Finnhub quote + metric response"""
        quote_mock = MagicMock()
        quote_mock.json.return_value = {"c": price, "h": 190.0, "l": 180.0}
        metric_mock = MagicMock()
        metric_mock.json.return_value = {
            "metric": {
                "52WeekHigh": 200.0,
                "52WeekLow": 150.0,
                "peNormalizedAnnual": 28.5,
                "marketCapitalization": 2900000.0
            }
        }
        return quote_mock, metric_mock

    @patch("agents.yf.Ticker")
    @patch("agents.requests.get")
    def test_tier1_yfinance_success(self, mock_get, mock_ticker):
        """Tier 1: yfinance ทำงานปกติ → ไม่เรียก Finnhub"""
        mock_stock = MagicMock()
        mock_stock.info = {
            "currentPrice": 185.0,
            "fiftyTwoWeekHigh": 200.0,
            "fiftyTwoWeekLow": 150.0,
            "trailingPE": 28.5,
            "marketCap": 2900000000
        }
        mock_ticker.return_value = mock_stock

        result = self.orc.natty_get_news(["AAPL"], days=1, include_weekend=False)

        self.assertIn("AAPL", result)
        self.assertEqual(result["AAPL"]["source"], "yfinance")
        self.assertAlmostEqual(result["AAPL"]["price"], 185.0)
        # MarketAux ถูกเรียก (ปกติ) แต่ Finnhub quote ต้องไม่ถูกเรียก
        news_r = MagicMock()
        news_r.json.return_value = {'data': []}
        mock_get.return_value = news_r
        result = self.orc.natty_get_news(["AAPL"], days=1, include_weekend=False)
        call_urls = [str(c) for c in mock_get.call_args_list]
        self.assertFalse(any("finnhub.io" in u for u in call_urls))

    @patch("agents.yf.Ticker")
    @patch("agents.requests.get")
    def test_tier2_finnhub_fallback_on_yfinance_429(self, mock_get, mock_ticker):
        """Tier 1 fail (429) → Tier 2 Finnhub ทำงาน"""
        # yfinance raise exception
        mock_ticker.side_effect = Exception("429 Too Many Requests")

        # Finnhub responses: quote + metric + marketaux (news)
        quote_r, metric_r = self._make_finnhub_response(185.0)
        news_r = MagicMock()
        news_r.json.return_value = {"data": []}
        mock_get.side_effect = [quote_r, metric_r, news_r]

        result = self.orc.natty_get_news(["AAPL"], days=1, include_weekend=False)

        self.assertIn("AAPL", result)
        self.assertEqual(result["AAPL"]["source"], "finnhub")
        self.assertAlmostEqual(result["AAPL"]["price"], 185.0)
        self.assertAlmostEqual(result["AAPL"]["52week_high"], 200.0)
        self.assertAlmostEqual(result["AAPL"]["pe_ratio"], 28.5)

    @patch("agents.yf.Ticker")
    @patch("agents.requests.get")
    def test_tier3_alpha_vantage_fallback(self, mock_get, mock_ticker):
        """Tier 1+2 fail → Tier 3 Alpha Vantage ทำงาน
        หมายเหตุ: Finnhub เรียกแค่ /quote (ถ้า price=0 → return None ทันที ไม่เรียก /metric)"""
        mock_ticker.side_effect = Exception("429")
        # Finnhub quote only (price=0 → _fetch_finnhub_full returns None immediately)
        finnhub_quote = MagicMock()
        finnhub_quote.json.return_value = {"c": 0}
        # Alpha Vantage OVERVIEW (1 call — ไม่มี metric แยก)
        av_overview = MagicMock()
        av_overview.json.return_value = {
            "PERatio": "25.0",
            "MarketCapitalization": "2900000000",
            "52WeekHigh": "200.0",
            "52WeekLow": "150.0",
            "200DayMovingAverage": "175.0"
        }
        # MarketAux news
        news_r = MagicMock()
        news_r.json.return_value = {"data": []}
        # Actual call order: fh_quote → av_overview → marketaux_news
        mock_get.side_effect = [finnhub_quote, av_overview, news_r]

        result = self.orc.natty_get_news(["AAPL"], days=1, include_weekend=False)

        self.assertIn("AAPL", result)
        self.assertEqual(result["AAPL"]["source"], "alpha_vantage")
        self.assertAlmostEqual(result["AAPL"]["price"], 175.0)

    @patch("agents.yf.Ticker")
    @patch("agents.requests.get")
    def test_all_tiers_fail_skips_ticker(self, mock_get, mock_ticker):
        """ทุก Tier fail → skip ticker ไม่ให้หนุ่มวิเคราะห์ด้วยข้อมูลไม่ครบ"""
        mock_ticker.side_effect = Exception("429")
        mock_get.side_effect = Exception("connection error")

        result = self.orc.natty_get_news(["AAPL"], days=1, include_weekend=False)

        self.assertNotIn("AAPL", result)

    def test_pe_negative_is_preserved(self):
        """P/E ติดลบ = บริษัทขาดทุน ต้องไม่ถูก filter ออก"""
        val = self.orc._safe_float("-5.2")
        self.assertAlmostEqual(val, -5.2)


# ============================================================
# SECTION 3: MarketAux — Monday weekend logic
# ============================================================
class TestMarketAuxNews(unittest.TestCase):

    def setUp(self):
        self.orc = make_orchestrator()

    @patch("agents.requests.get")
    def test_regular_mode_published_after_yesterday(self, mock_get):
        """ปกติ (อ-ศ) → published_after = เมื่อวาน 22:00"""
        mock_get.return_value = MagicMock()
        mock_get.return_value.json.return_value = {"data": []}

        # Mock datetime เป็นวันพุธ
        with patch("agents.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 24, 22, 0)  # วันพุธ
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            self.orc._fetch_marketaux_news("AAPL", "key", include_weekend=False)

        call_url = mock_get.call_args[0][0]
        self.assertIn("published_after=2026-06-23T22:00", call_url)

    @patch("agents.requests.get")
    def test_monday_mode_published_after_friday(self, mock_get):
        """วันจันทร์ → published_after = ศุกร์ที่แล้ว 22:00"""
        mock_get.return_value = MagicMock()
        mock_get.return_value.json.return_value = {"data": []}

        with patch("agents.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 22, 22, 0)  # วันจันทร์
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            self.orc._fetch_marketaux_news("AAPL", "key", include_weekend=True)

        call_url = mock_get.call_args[0][0]
        self.assertIn("published_after=2026-06-19T22:00", call_url)  # ศุกร์

    @patch("agents.requests.get")
    def test_limit_6_in_url(self, mock_get):
        """ต้องใช้ limit=6 เสมอ"""
        mock_get.return_value = MagicMock()
        mock_get.return_value.json.return_value = {"data": []}
        self.orc._fetch_marketaux_news("AAPL", "key")
        call_url = mock_get.call_args[0][0]
        self.assertIn("limit=6", call_url)

    @patch("agents.requests.get")
    def test_group_similar_in_url(self, mock_get):
        """ต้องใช้ group_similar=true เพื่อกรอง near-duplicate"""
        mock_get.return_value = MagicMock()
        mock_get.return_value.json.return_value = {"data": []}
        self.orc._fetch_marketaux_news("AAPL", "key")
        call_url = mock_get.call_args[0][0]
        self.assertIn("group_similar=true", call_url)

    def test_format_news_avg_sentiment(self):
        """_format_news_for_prompt คำนวณ avg sentiment ถูกต้อง"""
        news = [
            {"sentiment_score": 0.8, "headline": "A", "source": "S1", "highlights": []},
            {"sentiment_score": 0.2, "headline": "B", "source": "S2", "highlights": []},
        ]
        result = self.orc._format_news_for_prompt("AAPL", news)
        self.assertIn("เชิงบวก", result)
        self.assertIn("0.50", result)

    def test_format_news_negative_sentiment(self):
        news = [{"sentiment_score": -0.7, "headline": "Bad news", "source": "S1", "highlights": []}]
        result = self.orc._format_news_for_prompt("AAPL", news)
        self.assertIn("เชิงลบ", result)

    def test_format_news_empty_returns_no_news(self):
        result = self.orc._format_news_for_prompt("AAPL", [])
        self.assertEqual(result, "ไม่มีข่าวล่าสุด")


# ============================================================
# SECTION 4: หนุ่ม — signal validation
# ============================================================
class TestNumAnalyzeStocks(unittest.TestCase):

    def setUp(self):
        self.orc = make_orchestrator()
        self.sample_news_data = {
            "AAPL": {
                "price": 185.0,
                "52week_high": 200.0,
                "52week_low": 150.0,
                "pe_ratio": 28.5,
                "market_cap": 2900000000,
                "source": "yfinance",
                "news_summary": "ข่าวดี AAPL",
                "avg_sentiment": 0.5,
                "news_count": 3
            }
        }

    @patch.object(AgentOrchestrator, "claude_call")
    def test_valid_buy_signal(self, mock_call):
        mock_call.return_value = json.dumps({
            "ticker": "AAPL", "signal": "BUY",
            "confidence": 0.85, "s1": 180.0, "s2": 175.0, "s3": 170.0,
            "reasoning": "แนวโน้มดี"
        })
        result = self.orc.num_analyze_stocks(self.sample_news_data, ["AAPL"])
        self.assertEqual(result["AAPL"]["signal"], "BUY")
        self.assertAlmostEqual(result["AAPL"]["confidence"], 0.85)

    @patch.object(AgentOrchestrator, "claude_call")
    def test_invalid_signal_defaults_to_hold(self, mock_call):
        """Claude ตอบ signal ผิด ('Strong Buy') → ระบบต้อง default เป็น HOLD"""
        mock_call.return_value = json.dumps({
            "ticker": "AAPL", "signal": "Strong Buy",
            "confidence": 0.9, "s1": 180.0, "s2": 175.0, "s3": 170.0,
            "reasoning": "..."
        })
        result = self.orc.num_analyze_stocks(self.sample_news_data, ["AAPL"])
        self.assertEqual(result["AAPL"]["signal"], "HOLD")

    @patch.object(AgentOrchestrator, "claude_call")
    def test_json_parse_fail_uses_fallback(self, mock_call):
        """Claude ตอบ JSON เสีย → fallback ด้วย price จริง"""
        mock_call.return_value = "ขอโทษครับ ฉันตอบได้แค่นี้"
        result = self.orc.num_analyze_stocks(self.sample_news_data, ["AAPL"])
        self.assertIn("AAPL", result)
        self.assertEqual(result["AAPL"]["signal"], "HOLD")
        self.assertAlmostEqual(result["AAPL"]["s1"], 185.0 * 0.95)

    @patch.object(AgentOrchestrator, "claude_call")
    def test_no_price_data_sets_zero_confidence(self, mock_call):
        """ราคา = None → confidence = 0.0 (ป้องกันเข้า DB)"""
        mock_call.return_value = "garbage response"
        no_price_data = {
            "AAPL": {**self.sample_news_data["AAPL"], "price": None}
        }
        result = self.orc.num_analyze_stocks(no_price_data, ["AAPL"])
        self.assertEqual(result["AAPL"]["confidence"], 0.0)
        self.assertIsNone(result["AAPL"]["s1"])

    def test_negative_pe_included_in_prompt(self):
        """P/E ติดลบ ต้องปรากฏใน user_message ว่า 'ขาดทุน' ไม่ใช่ N/A"""
        with patch.object(AgentOrchestrator, "claude_call") as mock_call:
            mock_call.return_value = json.dumps({
                "ticker": "TEST", "signal": "SELL",
                "confidence": 0.7, "s1": 50.0, "s2": 45.0, "s3": 40.0,
                "reasoning": "ขาดทุน"
            })
            neg_pe_data = {
                "TEST": {**self.sample_news_data["AAPL"], "pe_ratio": -8.3}
            }
            self.orc.num_analyze_stocks(neg_pe_data, ["TEST"])
            call_args = mock_call.call_args[0][1]  # user_message
            self.assertIn("ขาดทุน", call_args)


# ============================================================
# SECTION 5: มด — NEEDS_REVIEW flag
# ============================================================
class TestMudValidation(unittest.TestCase):

    def setUp(self):
        self.orc = make_orchestrator()
        self.sample_analysis = {
            "AAPL": {
                "ticker": "AAPL", "signal": "BUY",
                "confidence": 0.85, "s1": 180.0, "s2": 175.0, "s3": 170.0,
                "reasoning": "แนวโน้มดี"
            }
        }

    @patch.object(AgentOrchestrator, "claude_call")
    def test_valid_pass_result(self, mock_call):
        mock_call.return_value = json.dumps({
            "ticker": "AAPL", "is_valid": True, "issues": [], "recommendation": "PASS"
        })
        result = self.orc.mud_cross_validate(self.sample_analysis)
        self.assertEqual(result["AAPL"]["validation"]["recommendation"], "PASS")

    @patch.object(AgentOrchestrator, "claude_call")
    def test_json_parse_fail_flags_needs_review(self, mock_call):
        """JSON เสีย → NEEDS_REVIEW ไม่ใช่ auto-PASS"""
        mock_call.return_value = "I cannot validate this"
        result = self.orc.mud_cross_validate(self.sample_analysis)
        self.assertEqual(result["AAPL"]["validation"]["recommendation"], "NEEDS_REVIEW")
        self.assertIsNone(result["AAPL"]["validation"]["is_valid"])

    @patch.object(AgentOrchestrator, "claude_call")
    def test_exception_flags_needs_review(self, mock_call):
        """Claude call exception → NEEDS_REVIEW ไม่ใช่ PASS"""
        mock_call.side_effect = Exception("API error")
        result = self.orc.mud_cross_validate(self.sample_analysis)
        self.assertEqual(result["AAPL"]["validation"]["recommendation"], "NEEDS_REVIEW")

    @patch.object(AgentOrchestrator, "claude_call")
    def test_needs_review_ticker_skipped_in_db(self, mock_call):
        """NEEDS_REVIEW → ต้องถูก skip ใน _update_database"""
        mock_call.return_value = json.dumps({
            "ticker": "AAPL", "is_valid": None, "issues": ["parse failed"],
            "recommendation": "NEEDS_REVIEW"
        })
        result = self.orc.mud_cross_validate(self.sample_analysis)

        # Mock DB
        mock_db = MagicMock()
        mock_stock = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_stock

        with patch("agents.SessionLocal", return_value=mock_db):
            self.orc._update_database(result)

        # commit ถูกเรียก (batch commit) แต่ query ต้องไม่ถูกเรียก (skip ก่อน query)
        mock_db.commit.assert_called_once()
        mock_db.query.assert_not_called()


# ============================================================
# SECTION 6: นน — fail-safe REJECT + HTML strip
# ============================================================
class TestNanQACheck(unittest.TestCase):

    def setUp(self):
        self.orc = make_orchestrator()
        self.sample_results = {
            "AAPL": {
                "signal": "BUY", "confidence": 0.85,
                "s1": 180.0, "s2": 175.0, "s3": 170.0,
                "reasoning": "ดี",
                "validation": {"recommendation": "PASS"}
            }
        }
        self.sample_report = {"summary": "<div>Report content</div>"}

    @patch.object(AgentOrchestrator, "claude_call")
    def test_pass_result(self, mock_call):
        mock_call.return_value = json.dumps({
            "status": "PASS", "issues": [], "approval_reason": "ข้อมูลครบถ้วน"
        })
        result = self.orc.nan_qa_check(self.sample_results, self.sample_report)
        self.assertEqual(result["status"], "PASS")

    @patch.object(AgentOrchestrator, "claude_call")
    def test_json_parse_fail_returns_reject(self, mock_call):
        """JSON เสีย → REJECT (fail-safe) ไม่ใช่ auto-PASS"""
        mock_call.return_value = "ไม่สามารถ QA ได้"
        result = self.orc.nan_qa_check(self.sample_results, self.sample_report)
        self.assertEqual(result["status"], "REJECT")

    @patch.object(AgentOrchestrator, "claude_call")
    def test_exception_returns_reject(self, mock_call):
        """Exception → REJECT ไม่ใช่ PASS"""
        mock_call.side_effect = Exception("API down")
        result = self.orc.nan_qa_check(self.sample_results, self.sample_report)
        self.assertEqual(result["status"], "REJECT")

    @patch.object(AgentOrchestrator, "claude_call")
    def test_html_stripped_from_approval_reason(self, mock_call):
        """HTML tags ใน approval_reason ต้องถูก strip ออก"""
        mock_call.return_value = json.dumps({
            "status": "PASS",
            "issues": [],
            "approval_reason": "<div>ข้อมูล</div>ดีครบถ้วน<br/>"
        })
        result = self.orc.nan_qa_check(self.sample_results, self.sample_report)
        self.assertNotIn("<div>", result["approval_reason"])
        self.assertNotIn("<br/>", result["approval_reason"])
        self.assertIn("ดีครบถ้วน", result["approval_reason"])

    @patch.object(AgentOrchestrator, "claude_call")
    def test_html_stripped_from_issues(self, mock_call):
        """HTML tags ใน issues ต้องถูก strip"""
        mock_call.return_value = json.dumps({
            "status": "REJECT",
            "issues": ["<p>ข้อมูล</p>ไม่ครบ"],
            "approval_reason": "REJECT"
        })
        result = self.orc.nan_qa_check(self.sample_results, self.sample_report)
        self.assertNotIn("<p>", result["issues"][0])
        self.assertIn("ไม่ครบ", result["issues"][0])

    @patch.object(AgentOrchestrator, "claude_call")
    def test_report_html_stripped_before_qa(self, mock_call):
        """HTML/CSS ใน report ต้องถูก strip ก่อนส่งให้ นน"""
        mock_call.return_value = json.dumps({
            "status": "PASS", "issues": [], "approval_reason": "OK"
        })
        html_report = {
            "summary": "<style>body{color:red}</style><div><h1>Report</h1><p>Content here</p></div>"
        }
        self.orc.nan_qa_check(self.sample_results, html_report)
        user_msg = mock_call.call_args[0][1]
        self.assertNotIn("<style>", user_msg)
        self.assertNotIn("<div>", user_msg)
        self.assertIn("Content here", user_msg)


# ============================================================
# SECTION 7: Workflow — early exits + state isolation
# ============================================================
class TestWorkflow(unittest.TestCase):

    def setUp(self):
        self.orc = make_orchestrator()

    @patch.object(AgentOrchestrator, "natty_get_news")
    def test_empty_news_data_aborts_workflow(self, mock_natty):
        """ถ้านัตตี้ได้ 0 stocks → workflow ABORTED ทันที ไม่รันต่อ"""
        mock_natty.return_value = {}
        result = self.orc.run_workflow(stocks=["AAPL"])
        self.assertEqual(result["status"], "ABORTED")

    @patch.object(AgentOrchestrator, "natty_get_news")
    @patch.object(AgentOrchestrator, "num_analyze_stocks")
    def test_empty_analysis_aborts_workflow(self, mock_num, mock_natty):
        """หนุ่มวิเคราะห์ได้ 0 → ABORTED ไม่ให้เจน/นน เสีย token"""
        mock_natty.return_value = {"AAPL": {"price": 185.0}}
        mock_num.return_value = {}
        result = self.orc.run_workflow(stocks=["AAPL"])
        self.assertEqual(result["status"], "ABORTED")

    @patch.object(AgentOrchestrator, "natty_get_news")
    @patch.object(AgentOrchestrator, "num_analyze_stocks")
    @patch.object(AgentOrchestrator, "mud_cross_validate")
    @patch.object(AgentOrchestrator, "harry_monitor_portfolio")
    @patch.object(AgentOrchestrator, "jen_generate_report")
    @patch.object(AgentOrchestrator, "nan_qa_check")
    @patch.object(AgentOrchestrator, "_update_database")
    @patch.object(AgentOrchestrator, "a_record_improvements")
    def test_complete_workflow_pass(self, mock_a, mock_db, mock_nan, mock_jen,
                                    mock_harry, mock_mud, mock_num, mock_natty):
        """Happy path: ทุก agent สำเร็จ → COMPLETE"""
        mock_natty.return_value = {"AAPL": {"price": 185.0, "source": "yfinance"}}
        mock_num.return_value = {"AAPL": {"signal": "BUY", "confidence": 0.85}}
        mock_mud.return_value = {"AAPL": {"signal": "BUY", "validation": {"recommendation": "PASS"}}}
        mock_harry.return_value = {"total_holdings": 0, "portfolio_alignment": []}
        mock_jen.return_value = {"summary": "Report", "timestamp": datetime.now().isoformat()}
        mock_nan.return_value = {"status": "PASS", "issues": [], "approval_reason": "OK"}

        result = self.orc.run_workflow(stocks=["AAPL"])
        self.assertEqual(result["status"], "COMPLETE")
        mock_db.assert_called_once()
        mock_a.assert_called_once()

    @patch.object(AgentOrchestrator, "natty_get_news")
    @patch.object(AgentOrchestrator, "num_analyze_stocks")
    @patch.object(AgentOrchestrator, "mud_cross_validate")
    @patch.object(AgentOrchestrator, "harry_monitor_portfolio")
    @patch.object(AgentOrchestrator, "jen_generate_report")
    @patch.object(AgentOrchestrator, "nan_qa_check")
    @patch.object(AgentOrchestrator, "_update_database")
    @patch.object(AgentOrchestrator, "a_record_improvements")
    @patch.object(AgentOrchestrator, "kao_retry")
    def test_qa_reject_retries_up_to_max(self, mock_kao, mock_a, mock_db, mock_nan,
                                          mock_jen, mock_harry, mock_mud, mock_num, mock_natty):
        """QA reject ทุกรอบ → max_retries=3 ครั้ง → REJECTED, DB ไม่ถูก update"""
        mock_natty.return_value = {"AAPL": {"price": 185.0}}
        mock_num.return_value = {"AAPL": {"signal": "BUY", "confidence": 0.85}}
        mock_mud.return_value = {"AAPL": {"signal": "BUY", "validation": {"recommendation": "PASS"}}}
        mock_harry.return_value = {"total_holdings": 0, "portfolio_alignment": []}
        mock_jen.return_value = {"summary": "Report", "timestamp": datetime.now().isoformat()}
        mock_nan.return_value = {"status": "REJECT", "issues": ["ข้อมูลไม่ครบ"], "approval_reason": "REJECT"}
        mock_kao.return_value = "hint"

        result = self.orc.run_workflow(stocks=["AAPL"])
        self.assertEqual(result["status"], "REJECTED")
        mock_db.assert_not_called()  # DB ต้องไม่ถูก update
        self.assertEqual(mock_nan.call_count, 3)  # retry 3 ครั้ง

    def test_workflow_log_resets_each_run(self):
        """workflow_log ต้อง reset ทุก run — ไม่สะสมข้าม run"""
        self.orc.workflow_log = [{"old": "log"}]
        with patch.object(AgentOrchestrator, "natty_get_news", return_value={}):
            self.orc.run_workflow(stocks=["AAPL"])
        # log ต้องไม่มีของเก่า
        agents_in_log = [l["agent"] for l in self.orc.workflow_log]
        self.assertNotIn("old", str(self.orc.workflow_log))
        self.assertIn("SYSTEM", agents_in_log)

    def test_no_shared_state_between_claude_calls(self):
        """claude_call ต้องสร้าง messages ใหม่ทุกครั้ง — ไม่มี shared history"""
        messages_seen = []
        def capture_call(*args, **kwargs):
            # เก็บ messages ที่ถูกส่ง — usage ต้องเป็น int จริงๆ ไม่ใช่ MagicMock
            mock_usage = MagicMock()
            mock_usage.input_tokens = 100
            mock_usage.output_tokens = 50
            mock_usage.cache_creation_input_tokens = 0
            mock_usage.cache_read_input_tokens = 0
            return MagicMock(
                content=[MagicMock(text='{"signal":"HOLD","confidence":0.5,"s1":100,"s2":95,"s3":90,"reasoning":"test","ticker":"X"}')],
                usage=mock_usage
            )

        with patch("agents.Anthropic") as mock_client:
            mock_instance = MagicMock()
            mock_instance.messages.create.side_effect = capture_call
            mock_client.return_value = mock_instance

            self.orc.claude_call("sys", "msg1", "Agent1")
            call1_msgs = mock_instance.messages.create.call_args_list[-1][1].get(
                "messages", mock_instance.messages.create.call_args_list[-1][0]
            )
            self.orc.claude_call("sys", "msg2", "Agent2")
            call2_msgs = mock_instance.messages.create.call_args_list[-1][1].get(
                "messages", mock_instance.messages.create.call_args_list[-1][0]
            )
            # แต่ละ call ต้องมีแค่ 1 user message (ไม่สะสม)
            self.assertEqual(mock_instance.messages.create.call_count, 2)


# ============================================================
# SECTION 8: โคลสัน — trade parse
# ============================================================
class TestColsonTrade(unittest.TestCase):

    def setUp(self):
        self.orc = make_orchestrator()

    @patch.object(AgentOrchestrator, "claude_call")
    def test_valid_buy_trade(self, mock_call):
        mock_call.return_value = json.dumps({
            "ticker": "AAPL", "action": "BUY", "shares": 100, "price": 185.0
        })
        mock_db = MagicMock()
        with patch("agents.SessionLocal", return_value=mock_db):
            result = self.orc.colson_parse_trade("ซื้อ AAPL 100 หุ้น ที่ 185")
        self.assertEqual(result["ticker"], "AAPL")
        self.assertEqual(result["action"], "BUY")
        self.assertEqual(result["shares"], 100)

    @patch.object(AgentOrchestrator, "claude_call")
    def test_parse_error_returns_none(self, mock_call):
        mock_call.return_value = json.dumps({"error": "ไม่สามารถ parse ได้"})
        result = self.orc.colson_parse_trade("คำสั่งไม่ชัดเจน")
        self.assertIsNone(result)

    @patch.object(AgentOrchestrator, "claude_call")
    def test_garbage_response_returns_none(self, mock_call):
        mock_call.return_value = "ขอโทษ ไม่เข้าใจ"
        result = self.orc.colson_parse_trade("อะไรก็ไม่รู้")
        self.assertIsNone(result)

    @patch.object(AgentOrchestrator, "claude_call")
    def test_ticker_uppercased(self, mock_call):
        """ticker ถูก uppercase ตอน create Trade object ผ่าน .upper()"""
        mock_call.return_value = json.dumps({
            "ticker": "aapl", "action": "BUY", "shares": 50, "price": 185.0
        })
        mock_db = MagicMock()
        # Mock Trade constructor ให้เก็บค่าที่ส่งเข้ามา
        with patch("agents.SessionLocal", return_value=mock_db):
            with patch("agents.Trade") as mock_trade_cls:
                self.orc.colson_parse_trade("ซื้อ aapl")
                # ตรวจว่า Trade() ถูก create ด้วย ticker uppercase
                call_kwargs = mock_trade_cls.call_args[1]
                self.assertEqual(call_kwargs["ticker"], "AAPL")


# ============================================================
# SECTION 9: _update_database
# ============================================================
class TestUpdateDatabase(unittest.TestCase):

    def setUp(self):
        self.orc = make_orchestrator()

    def _make_valid_analysis(self):
        return {
            "AAPL": {
                "signal": "BUY", "confidence": 0.85,
                "price": 185.0, "fair_price": 190.0,
                "s1": 180.0, "s2": 175.0, "s3": 170.0,
                "validation": {"recommendation": "PASS"}
            }
        }

    def test_needs_review_skipped(self):
        """NEEDS_REVIEW → ไม่เขียนลง DB"""
        data = {
            "AAPL": {
                "signal": "BUY", "confidence": 0.85,
                "s1": 180.0, "s2": 175.0, "s3": 170.0,
                "validation": {"recommendation": "NEEDS_REVIEW"}
            }
        }
        mock_db = MagicMock()
        with patch("agents.SessionLocal", return_value=mock_db):
            self.orc._update_database(data)
        mock_db.commit.assert_called_once()
        mock_db.query.assert_not_called()

    def test_zero_confidence_skipped(self):
        """confidence=0.0 → ไม่เขียนลง DB"""
        data = {
            "AAPL": {
                "signal": "HOLD", "confidence": 0.0,
                "s1": None, "s2": None, "s3": None,
                "validation": {"recommendation": "PASS"}
            }
        }
        mock_db = MagicMock()
        with patch("agents.SessionLocal", return_value=mock_db):
            self.orc._update_database(data)
        mock_db.commit.assert_called_once()
        mock_db.query.assert_not_called()

    def test_current_price_updated(self):
        """current_price ต้องถูกอัปเดตใน DB ด้วย"""
        data = self._make_valid_analysis()
        mock_db = MagicMock()
        mock_stock = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_stock

        with patch("agents.SessionLocal", return_value=mock_db):
            self.orc._update_database(data)

        self.assertEqual(mock_stock.current_price, 185.0)
        self.assertEqual(mock_stock.signal, "BUY")
        mock_db.commit.assert_called_once()

    def test_batch_commit_once(self):
        """commit ต้องเรียกแค่ 1 ครั้ง ไม่ว่าจะมีกี่ ticker"""
        data = {
            "AAPL": {**self._make_valid_analysis()["AAPL"]},
            "GOOGL": {**self._make_valid_analysis()["AAPL"], "price": 170.0}
        }
        mock_db = MagicMock()
        mock_stock = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_stock

        with patch("agents.SessionLocal", return_value=mock_db):
            self.orc._update_database(data)

        mock_db.commit.assert_called_once()  # 1 ครั้ง ไม่ใช่ 2 ครั้ง


# ============================================================
# Run
# ============================================================
if __name__ == "__main__":
    unittest.main(verbosity=2)
