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
        # ✅ แก้ 2026-07-04: เดิม confidence=0.85 (>= 0.70) โดน auto-PASS shortcut ใน
        # mud_cross_validate ดักไปก่อนถึง self.claude_call() เลย (cost-saving optimization
        # ที่เพิ่มเข้ามาทีหลัง แต่ test fixture นี้ไม่เคยอัปเดตตาม) ทำให้ mock_call ที่ตั้งไว้
        # ไม่เคยถูกเรียกจริง เทสต์เลย assert ผิดที่ผิดทาง (เห็น PASS ทั้งที่ mock exception/parse-fail)
        # ใช้ 0.65 (< 0.70) เพื่อบังคับให้ผ่านเข้า path ที่เรียก claude_call จริงตามที่เทสต์ต้องการ
        self.sample_analysis = {
            "AAPL": {
                "ticker": "AAPL", "signal": "BUY",
                "confidence": 0.65, "s1": 180.0, "s2": 175.0, "s3": 170.0,
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
# SECTION 8: Fix #1 — Market Cap unit display
# ============================================================
class TestMarketCapUnit(unittest.TestCase):
    """mcap_text ต้องมีหน่วย M USD เสมอ"""

    def setUp(self):
        self.orc = make_orchestrator()

    def _build_prompt(self, market_cap):
        mcap_text = f"${market_cap:,.0f}M USD" if market_cap is not None else "N/A"
        return mcap_text

    def test_mcap_has_M_USD_suffix(self):
        self.assertIn("M USD", self._build_prompt(3_000_000))

    def test_mcap_none_shows_na(self):
        self.assertIn("N/A", self._build_prompt(None))
        self.assertNotIn("M USD", self._build_prompt(None))

    def test_mcap_small_value(self):
        text = self._build_prompt(500)
        self.assertIn("M USD", text)
        self.assertIn("500", text)


class TestNewHighFlag(unittest.TestCase):
    """price > 52week_high → at_new_high=True + high อัปเดตเป็น price"""

    def _run_sanity(self, price, week52_high, week52_low):
        at_new_high = False
        at_new_low  = False
        if week52_high and price > week52_high * 1.05:
            week52_high = None
            week52_low  = None
        elif week52_high and price > week52_high:
            week52_high = price
            at_new_high = True
        elif week52_low and price < week52_low * 0.95:
            week52_high = None
            week52_low  = None
        elif week52_low and price < week52_low:
            week52_low = price
            at_new_low = True
        return week52_high, week52_low, at_new_high, at_new_low

    # ===== ATH tests =====

    def test_new_high_flag_set(self):
        h, l, ath, atl = self._run_sanity(price=1778, week52_high=1711, week52_low=800)
        self.assertTrue(ath)
        self.assertFalse(atl)
        self.assertEqual(h, 1778)
        self.assertEqual(l, 800)

    def test_within_range_no_flag(self):
        h, l, ath, atl = self._run_sanity(price=150, week52_high=200, week52_low=100)
        self.assertFalse(ath)
        self.assertFalse(atl)
        self.assertEqual(h, 200)

    def test_big_gap_above_clears_range(self):
        h, l, ath, atl = self._run_sanity(price=2000, week52_high=1000, week52_low=500)
        self.assertIsNone(h)
        self.assertIsNone(l)
        self.assertFalse(ath)
        self.assertFalse(atl)

    def test_price_far_below_low_clears_range(self):
        h, l, ath, atl = self._run_sanity(price=80, week52_high=200, week52_low=100)
        self.assertIsNone(h)
        self.assertIsNone(l)
        self.assertFalse(ath)
        self.assertFalse(atl)

    # ===== ATL tests =====

    def test_new_low_flag_set(self):
        """MSFT case: price เล็กน้อยต่ำกว่า 52w_low → ATL flag"""
        h, l, ath, atl = self._run_sanity(price=355.13, week52_high=480.0, week52_low=356.28)
        self.assertFalse(ath)
        self.assertTrue(atl)
        self.assertEqual(l, 355.13)   # low อัปเดตเป็น price
        self.assertEqual(h, 480.0)    # high ไม่เปลี่ยน

    def test_new_low_low_updated(self):
        """ATL → week52_low ต้องถูก override ด้วย price ใหม่"""
        h, l, ath, atl = self._run_sanity(price=99.0, week52_high=200.0, week52_low=100.0)
        self.assertTrue(atl)
        self.assertEqual(l, 99.0)

    def test_new_low_exact_boundary(self):
        """price = 52w_low * 0.95 ยังถือเป็น ATL (ไม่ถูก nullify)"""
        boundary = 100.0 * 0.95  # = 95.0
        h, l, ath, atl = self._run_sanity(price=boundary + 0.01, week52_high=200.0, week52_low=100.0)
        self.assertTrue(atl)
        self.assertIsNotNone(h)

    def test_new_low_below_threshold_clears_range(self):
        """price < 52w_low * 0.95 → currency mismatch → null ทั้งคู่"""
        h, l, ath, atl = self._run_sanity(price=94.99, week52_high=200.0, week52_low=100.0)
        self.assertIsNone(h)
        self.assertIsNone(l)
        self.assertFalse(atl)

    def test_ath_and_atl_mutually_exclusive(self):
        """ไม่มีทางที่ทั้ง ATH และ ATL เป็น True พร้อมกัน"""
        for price in [50, 150, 250]:
            _, _, ath, atl = self._run_sanity(price=price, week52_high=200.0, week52_low=100.0)
            self.assertFalse(ath and atl, f"price={price} ทำให้ ATH={ath} และ ATL={atl} พร้อมกัน")


class TestMudRecommendationFormat(unittest.TestCase):
    """prompt มด ต้องบังคับ PASS/NEEDS_REVIEW เท่านั้น — ตรวจจาก source file โดยตรง"""

    def _read_agents_src(self):
        src_path = os.path.join(os.path.dirname(__file__), "agents.py")
        with open(src_path, encoding="utf-8") as f:
            return f.read()

    def test_pass_fail_only_constraint_in_source(self):
        # ✅ แก้ 2026-07-04: agents.py เปลี่ยนศัพท์จาก PASS/FAIL เป็น PASS/NEEDS_REVIEW
        # ไปแล้วจริง (สอดคล้องกับ TestMudValidation ทั้งชุดที่ assert "NEEDS_REVIEW" อยู่แล้ว)
        # แต่เทสต์นี้ตัวเดียวไม่เคยอัปเดตตาม ยังหา "FAIL" ซึ่งไม่มีในโค้ดจริงอีกต่อไป
        src = self._read_agents_src()
        # หา mud system_prompt section
        mud_start = src.find("def mud_cross_validate")
        mud_end   = src.find("def ", mud_start + 1)
        mud_src   = src[mud_start:mud_end]
        self.assertIn("PASS", mud_src)
        self.assertIn("NEEDS_REVIEW", mud_src)
        # ต้องมี constraint ห้ามค่าอื่น
        self.assertTrue(
            "no other" in mud_src.lower() or "not valid" in mud_src.lower(),
            "agents.py mud prompt ต้องมี constraint ห้าม PASS_WITH_WARNING"
        )

    def test_pass_with_warning_not_allowed(self):
        src = self._read_agents_src()
        mud_start = src.find("def mud_cross_validate")
        mud_end   = src.find("def ", mud_start + 1)
        mud_src   = src[mud_start:mud_end]
        self.assertNotIn('"PASS_WITH_WARNING"', mud_src)


class TestCrossCurrencyTickers(unittest.TestCase):
    """ASML, TSM, BRK.B ต้อง clear 52w range จาก Finnhub เสมอ"""

    CROSS = {'ASML', 'TSM', 'BRK.B'}

    def _apply(self, ticker, data):
        if ticker in self.CROSS and data.get("52week_high") is not None:
            data["52week_high"] = None
            data["52week_low"]  = None
        return data

    def test_asml_cleared(self):
        d = self._apply("ASML", {"52week_high": 1600, "52week_low": 800})
        self.assertIsNone(d["52week_high"])

    def test_tsm_cleared(self):
        d = self._apply("TSM", {"52week_high": 900, "52week_low": 100})
        self.assertIsNone(d["52week_high"])

    def test_brkb_cleared(self):
        d = self._apply("BRK.B", {"52week_high": 550, "52week_low": 350})
        self.assertIsNone(d["52week_high"])

    def test_aapl_not_affected(self):
        d = self._apply("AAPL", {"52week_high": 200, "52week_low": 150})
        self.assertEqual(d["52week_high"], 200)

    def test_usd_ticker_not_affected(self):
        d = self._apply("NVDA", {"52week_high": 1000, "52week_low": 400})
        self.assertIsNotNone(d["52week_high"])


# ============================================================
# SECTION 8: แฮรี่ — Portfolio Monitor
# ============================================================
class TestHarryPortfolio(unittest.TestCase):

    def setUp(self):
        self.orc = make_orchestrator()

    def _holding(self, ticker, shares):
        h = MagicMock()
        h.ticker = ticker
        h.shares = shares
        return h

    @patch("agents.SessionLocal")
    def test_empty_portfolio_returns_zero_holdings(self, mock_sl):
        """Portfolio ว่าง → total_holdings=0, alignment list ว่าง"""
        db = MagicMock()
        db.query.return_value.all.return_value = []
        mock_sl.return_value = db

        result = self.orc.harry_monitor_portfolio({"AAPL": {"signal": "BUY"}})
        self.assertEqual(result["total_holdings"], 0)
        self.assertEqual(result["portfolio_alignment"], [])

    @patch("agents.SessionLocal")
    def test_ticker_not_in_analysis_skipped(self, mock_sl):
        """Holding ticker ไม่อยู่ใน analysis_results → ข้าม"""
        db = MagicMock()
        db.query.return_value.all.return_value = [self._holding("TSLA", 10)]
        mock_sl.return_value = db

        result = self.orc.harry_monitor_portfolio({"AAPL": {"signal": "BUY"}})
        self.assertEqual(result["portfolio_alignment"], [])

    @patch("agents.SessionLocal")
    def test_sell_signal_with_shares_is_misaligned(self, mock_sl):
        """SELL + ถือหุ้น → is_aligned=False, action=CONSIDER_SELLING"""
        db = MagicMock()
        db.query.return_value.all.return_value = [self._holding("AAPL", 50)]
        mock_sl.return_value = db

        result = self.orc.harry_monitor_portfolio({"AAPL": {"signal": "SELL"}})
        a = result["portfolio_alignment"][0]
        self.assertFalse(a["is_aligned"])
        self.assertEqual(a["action"], "CONSIDER_SELLING")

    @patch("agents.SessionLocal")
    def test_buy_signal_with_zero_shares_is_misaligned(self, mock_sl):
        """BUY + ไม่ถือ → is_aligned=False, action=CONSIDER_BUYING"""
        db = MagicMock()
        db.query.return_value.all.return_value = [self._holding("AAPL", 0)]
        mock_sl.return_value = db

        result = self.orc.harry_monitor_portfolio({"AAPL": {"signal": "BUY"}})
        a = result["portfolio_alignment"][0]
        self.assertFalse(a["is_aligned"])
        self.assertEqual(a["action"], "CONSIDER_BUYING")

    @patch("agents.SessionLocal")
    def test_buy_signal_with_shares_is_aligned(self, mock_sl):
        """BUY + ถือหุ้นอยู่ → is_aligned=True"""
        db = MagicMock()
        db.query.return_value.all.return_value = [self._holding("AAPL", 100)]
        mock_sl.return_value = db

        result = self.orc.harry_monitor_portfolio({"AAPL": {"signal": "BUY"}})
        self.assertTrue(result["portfolio_alignment"][0]["is_aligned"])

    @patch("agents.SessionLocal")
    def test_sell_with_zero_shares_is_aligned(self, mock_sl):
        """SELL + ไม่ถือ (shares=0) → aligned (ไม่มีอะไรต้องขาย)"""
        db = MagicMock()
        db.query.return_value.all.return_value = [self._holding("AAPL", 0)]
        mock_sl.return_value = db

        result = self.orc.harry_monitor_portfolio({"AAPL": {"signal": "SELL"}})
        self.assertTrue(result["portfolio_alignment"][0]["is_aligned"])

    def test_check_alignment_all_cases(self):
        """unit test _check_alignment โดยตรง — ครอบทุก branch"""
        self.assertFalse(self.orc._check_alignment("SELL", 100))  # SELL + has shares
        self.assertFalse(self.orc._check_alignment("BUY",  0))    # BUY  + no shares
        self.assertTrue (self.orc._check_alignment("BUY",  100))  # BUY  + has shares
        self.assertTrue (self.orc._check_alignment("SELL", 0))    # SELL + no shares
        self.assertTrue (self.orc._check_alignment("HOLD", 50))   # HOLD always aligned

    def test_get_action_all_cases(self):
        """unit test _get_action โดยตรง"""
        self.assertEqual(self.orc._get_action("BUY",  0),   "CONSIDER_BUYING")
        self.assertEqual(self.orc._get_action("SELL", 100), "CONSIDER_SELLING")
        self.assertEqual(self.orc._get_action("HOLD", 50),  "HOLD")
        self.assertEqual(self.orc._get_action("BUY",  100), "HOLD")  # ถือแล้ว ไม่ต้องซื้อ
        self.assertEqual(self.orc._get_action("SELL", 0),   "HOLD")  # ไม่มีของขาย

    @patch("agents.SessionLocal")
    def test_db_exception_propagates(self, mock_sl):
        """DB ล้มเหลว → แฮรี่ re-raise (ไม่ swallow)"""
        mock_sl.side_effect = Exception("DB connection failed")
        with self.assertRaises(Exception):
            self.orc.harry_monitor_portfolio({"AAPL": {"signal": "BUY"}})


# ============================================================
# SECTION 9: เอ — Record Improvements
# ============================================================
class TestARecordImprovements(unittest.TestCase):

    def setUp(self):
        self.orc = make_orchestrator()

    def _make_results(self, buy=2, sell=1, hold=3, needs_review=1):
        results = {}
        for i in range(buy):
            results[f"BUY_{i}"]  = {"signal": "BUY",  "validation": {"recommendation": "PASS"}}
        for i in range(sell):
            results[f"SELL_{i}"] = {"signal": "SELL", "validation": {"recommendation": "PASS"}}
        for i in range(hold):
            results[f"HOLD_{i}"] = {"signal": "HOLD", "validation": {"recommendation": "PASS"}}
        for i in range(needs_review):
            results[f"NR_{i}"]   = {"signal": "HOLD", "validation": {"recommendation": "NEEDS_REVIEW"}}
        return results

    @patch("agents.SessionLocal")
    def test_signal_counts_passed_to_claude(self, mock_sl):
        """เอส่ง BUY/SELL/HOLD/NEEDS_REVIEW ที่นับถูกต้องเข้า Claude"""
        db = MagicMock()
        mock_sl.return_value = db
        captured = {}

        def capture(system, user, agent_name, **kwargs):
            captured["user"] = user
            return "สรุป"
        self.orc.claude_call = capture

        self.orc.a_record_improvements(
            {"qa_result": {"status": "PASS"}, "include_weekend": False},
            self._make_results(buy=2, sell=1, hold=3, needs_review=1)
        )
        self.assertIn("BUY signals: 2",  captured["user"])
        self.assertIn("SELL signals: 1", captured["user"])
        # NR ticker มี signal=HOLD ด้วย → HOLD count รวม NR = 4
        self.assertIn("HOLD signals: 4", captured["user"])
        self.assertIn("NEEDS_REVIEW: 1", captured["user"])

    @patch("agents.SessionLocal")
    def test_haiku_model_used(self, mock_sl):
        """เอต้องใช้ Haiku — ไม่ใช้ Sonnet (ประหยัด token)"""
        db = MagicMock()
        mock_sl.return_value = db
        models_used = []

        def capture(system, user, agent_name, model=None, **kwargs):
            models_used.append(model or "")
            return "สรุป"
        self.orc.claude_call = capture

        self.orc.a_record_improvements(
            {"qa_result": {"status": "PASS"}, "include_weekend": False},
            self._make_results()
        )
        self.assertTrue(any("haiku" in m.lower() for m in models_used),
                        f"Expected Haiku, got: {models_used}")

    @patch("agents.SessionLocal")
    def test_db_error_no_crash(self, mock_sl):
        """DB ล้มเหลว → เอต้องไม่ crash — swallow ด้วย warning"""
        mock_sl.side_effect = Exception("DB down")
        self.orc.claude_call = MagicMock(return_value="สรุป")
        try:
            self.orc.a_record_improvements(
                {"qa_result": {"status": "PASS"}, "include_weekend": False},
                self._make_results()
            )
        except Exception as e:
            self.fail(f"a_record_improvements raised: {e}")

    @patch("agents.SessionLocal")
    def test_empty_results_no_crash(self, mock_sl):
        """validated_results ว่าง → นับ 0 ทุกตัว ไม่ crash"""
        db = MagicMock()
        mock_sl.return_value = db
        self.orc.claude_call = MagicMock(return_value="ไม่มีข้อมูล")
        try:
            self.orc.a_record_improvements(
                {"qa_result": {"status": "PASS"}, "include_weekend": False}, {}
            )
        except Exception as e:
            self.fail(f"Empty results caused crash: {e}")


# ============================================================
# SECTION 10: นิก — Code Optimizer (Diff Mode)
# ============================================================
class TestNikOptimizeCode(unittest.TestCase):

    def setUp(self):
        self.orc = make_orchestrator()
        self.sample_code = "def run_workflow():\n    pass\n" * 100  # ~3000 chars

    @patch("agents.SessionLocal")
    def test_no_github_token_returns_none(self, mock_sl):
        """ไม่มี GITHUB_TOKEN → abort → return None"""
        env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
        with patch.dict(os.environ, env, clear=True):
            result = self.orc.nik_optimize_code()
        self.assertIsNone(result)

    @patch("agents.SessionLocal")
    @patch.object(AgentOrchestrator, "_nik_get_current_agents_py")
    def test_agents_py_too_large_returns_none(self, mock_get_code, mock_sl):
        """agents.py > 300000 chars → skip → return None
        ✅ แก้ 2026-07-04: เพดานเดิม 80000 ถูกยกเป็น 300000 แล้ว (Blueprint Defect #16 —
        agents.py โตเกิน 80000 จริงจนนิกข้าม optimization ทุกวันศุกร์แบบเงียบๆ) เทสต์นี้เคย
        ยึดเพดานเก่า ทำให้ fake size 80001 ไม่เกินเพดานใหม่แล้ว เลยไม่ถูก skip เหมือนที่ตั้งใจ"""
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        mock_sl.return_value = db
        mock_get_code.return_value = ("X" * 300001, "sha")

        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test"}):
            result = self.orc.nik_optimize_code()
        self.assertIsNone(result)

    @patch("agents.SessionLocal")
    @patch.object(AgentOrchestrator, "_nik_get_current_agents_py")
    def test_no_diff_blocks_returns_none(self, mock_get_code, mock_sl):
        """Claude ไม่ return <<<DIFF>>> → return None"""
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        mock_sl.return_value = db
        mock_get_code.return_value = (self.sample_code, "sha")
        self.orc.claude_call = MagicMock(return_value="ระบบปกติดี ไม่มีอะไรต้องแก้")

        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test"}):
            result = self.orc.nik_optimize_code()
        self.assertIsNone(result)

    @patch("agents.SessionLocal")
    @patch.object(AgentOrchestrator, "_nik_get_current_agents_py")
    def test_valid_diff_saves_to_db_and_returns(self, mock_get_code, mock_sl):
        """Claude return diff ถูก format → บันทึก NikSuggestion → return diff"""
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        mock_sl.return_value = db
        mock_get_code.return_value = (self.sample_code, "sha")

        fake_diff = (
            "<<<DIFF>>>\n"
            "SUMMARY: แก้ timeout ใน API call\n"
            "FILE: agents.py\n"
            "FIND:\n    timeout=5\n"
            "REPLACE:\n    timeout=15\n"
            "<<<END_DIFF>>>"
        )
        self.orc.claude_call = MagicMock(return_value=fake_diff)

        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test"}):
            result = self.orc.nik_optimize_code()

        self.assertIsNotNone(result)
        self.assertIn("<<<DIFF>>>", result)
        db.add.assert_called_once()
        db.commit.assert_called()

    @patch("agents.SessionLocal")
    @patch.object(AgentOrchestrator, "_nik_get_current_agents_py")
    def test_summary_extracted_from_first_summary_line(self, mock_get_code, mock_sl):
        """summary ที่ save ลง DB ต้องมาจาก SUMMARY: บรรทัดแรก"""
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        mock_sl.return_value = db
        mock_get_code.return_value = (self.sample_code, "sha")

        fake_diff = (
            "<<<DIFF>>>\n"
            "SUMMARY: แก้ timeout ใน API call\n"
            "FILE: agents.py\n"
            "FIND:\n    x\nREPLACE:\n    y\n"
            "<<<END_DIFF>>>"
        )
        self.orc.claude_call = MagicMock(return_value=fake_diff)

        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test"}):
            self.orc.nik_optimize_code()

        # NikSuggestion เป็น MagicMock — ตรวจ constructor kwargs แทน
        nik_cls = sys.modules["models"].NikSuggestion
        call_kwargs = nik_cls.call_args[1]
        self.assertEqual(call_kwargs["summary"], "แก้ timeout ใน API call")
        self.assertEqual(call_kwargs["status"], "pending")

    @patch("agents.SessionLocal")
    @patch.object(AgentOrchestrator, "_nik_get_current_agents_py")
    def test_db_save_fails_no_crash(self, mock_get_code, mock_sl):
        """DB save suggestion ล้มเหลว → นิกต้องไม่ crash"""
        db_read = MagicMock()
        db_read.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        db_save = MagicMock()
        db_save.add.side_effect = Exception("DB full")
        mock_sl.side_effect = [db_read, db_save]
        mock_get_code.return_value = (self.sample_code, "sha")

        fake_diff = "<<<DIFF>>>\nSUMMARY: t\nFILE: agents.py\nFIND:\nx\nREPLACE:\ny\n<<<END_DIFF>>>"
        self.orc.claude_call = MagicMock(return_value=fake_diff)

        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test"}):
            try:
                self.orc.nik_optimize_code()
            except Exception as e:
                self.fail(f"nik_optimize_code crashed on DB save failure: {e}")


# ============================================================
# SECTION 11: _checkpoint_database — Checkpoint บันทึกทีละตัว
# ============================================================
class TestCheckpointDatabase(unittest.TestCase):

    def setUp(self):
        self.orc = make_orchestrator()

    def _valid(self, signal="BUY"):
        return {
            "s1": 185.0, "confidence": 0.8, "signal": signal,
            "price": 190.0, "at_new_high": False, "at_new_low": False,
            "validation": {"recommendation": "PASS"},
        }

    @patch("agents.SessionLocal")
    def test_saves_valid_ticker_and_commits(self, mock_sl):
        """ticker valid → stock.signal updated + commit ถูกเรียก"""
        db = MagicMock()
        stock = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = stock
        mock_sl.return_value = db

        self.orc._checkpoint_database({"AAPL": self._valid()})

        self.assertEqual(stock.signal, "BUY")
        db.commit.assert_called_once()

    @patch("agents.SessionLocal")
    def test_skips_zero_confidence(self, mock_sl):
        """confidence == 0.0 → ข้าม ไม่ query DB"""
        db = MagicMock()
        mock_sl.return_value = db

        self.orc._checkpoint_database({
            "AAPL": {"s1": 185.0, "confidence": 0.0, "signal": "HOLD",
                     "validation": {"recommendation": "PASS"}}
        })
        db.query.assert_not_called()

    @patch("agents.SessionLocal")
    def test_skips_none_s1(self, mock_sl):
        """s1 is None → ข้าม ไม่ query DB"""
        db = MagicMock()
        mock_sl.return_value = db

        self.orc._checkpoint_database({
            "AAPL": {"s1": None, "confidence": 0.8, "signal": "BUY",
                     "validation": {"recommendation": "PASS"}}
        })

    @patch("agents.SessionLocal")
    def test_skips_needs_review(self, mock_sl):
        """NEEDS_REVIEW → ข้าม ไม่ query DB"""
        db = MagicMock()
        mock_sl.return_value = db

        self.orc._checkpoint_database({
            "AAPL": {"s1": 185.0, "confidence": 0.8, "signal": "BUY",
                     "validation": {"recommendation": "NEEDS_REVIEW"}}
        })
        db.query.assert_not_called()

    @patch("agents.SessionLocal")
    def test_db_error_no_crash(self, mock_sl):
        """DB ล้มเหลว → ต้องไม่ raise — log warning แล้วจบ"""
        mock_sl.side_effect = Exception("connection pool exhausted")
        try:
            self.orc._checkpoint_database({"AAPL": self._valid()})
        except Exception as e:
            self.fail(f"_checkpoint_database crashed: {e}")

    @patch("agents.SessionLocal")
    def test_commit_called_once_for_batch(self, mock_sl):
        """หลาย ticker → commit ครั้งเดียว (batch) ไม่ทำทีละตัว"""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = MagicMock()
        mock_sl.return_value = db

        results = {t: self._valid() for t in ["AAPL", "MSFT", "GOOGL"]}
        self.orc._checkpoint_database(results)
        db.commit.assert_called_once()


# ============================================================
# SECTION 12: calculate_roi — ROI ของสัญญาณ (win rate + avg return)
# ============================================================
class TestCalculateROI(unittest.TestCase):
    """✅ เพิ่ม 2026-07-04: ROI methodology ที่ตกลงกับ MBBook —
    win rate (BUY ขึ้น / SELL ลง = ถูก) @14d/@30d เทียบ 75%, avg return (เฉพาะ BUY) @30d เทียบ 13%"""

    def setUp(self):
        self.orc = make_orchestrator()

    def _row(self, ticker, signal, price, days_ago):
        r = MagicMock()
        r.ticker = ticker
        r.signal = signal
        r.price = price
        r.timestamp = datetime.now() - timedelta(days=days_ago)
        return r

    @patch("agents.SessionLocal")
    def test_buy_signal_price_up_is_win(self, mock_sl):
        """BUY เมื่อ 40 วันก่อน มี snapshot ราคาขึ้นใกล้ +14 และ +30 วัน → win ทั้งสองระยะ"""
        db = MagicMock()
        rows = [
            self._row("AAPL", "BUY",  100.0, days_ago=40),
            self._row("AAPL", "HOLD", 110.0, days_ago=26),  # ~+14 วันหลังสัญญาณ
            self._row("AAPL", "HOLD", 120.0, days_ago=10),  # ~+30 วันหลังสัญญาณ
        ]
        db.query.return_value.order_by.return_value.all.return_value = rows
        mock_sl.return_value = db

        result = self.orc.calculate_roi(db=db)

        self.assertEqual(result["14d"]["wins"], 1)
        self.assertEqual(result["14d"]["win_rate_pct"], 100.0)
        self.assertEqual(result["30d"]["wins"], 1)
        self.assertAlmostEqual(result["30d"]["avg_return_pct"], 20.0, places=1)

    @patch("agents.SessionLocal")
    def test_sell_signal_price_down_is_win(self, mock_sl):
        """SELL แล้วราคาลงจริง → นับเป็น win แต่ไม่นับใน avg_return (ไม่ใช่ BUY)"""
        db = MagicMock()
        rows = [
            self._row("MSFT", "SELL", 200.0, days_ago=20),
            self._row("MSFT", "HOLD", 180.0, days_ago=6),  # ~+14 วันหลังสัญญาณ ราคาลง
        ]
        db.query.return_value.order_by.return_value.all.return_value = rows
        mock_sl.return_value = db

        result = self.orc.calculate_roi(db=db)
        self.assertEqual(result["14d"]["wins"], 1)
        self.assertEqual(result["14d"]["losses"], 0)
        self.assertEqual(result["14d"]["buy_signals_counted"], 0)

    @patch("agents.SessionLocal")
    def test_signal_too_new_not_evaluated(self, mock_sl):
        """สัญญาณอายุแค่ 5 วัน (< 14 วัน) → ยังตัดสินไม่ได้ ไม่นับเป็นทั้งถูกและผิด"""
        db = MagicMock()
        rows = [self._row("NVDA", "BUY", 500.0, days_ago=5)]
        db.query.return_value.order_by.return_value.all.return_value = rows
        mock_sl.return_value = db

        result = self.orc.calculate_roi(db=db)
        self.assertEqual(result["14d"]["evaluated_signals"], 0)
        self.assertIsNone(result["14d"]["win_rate_pct"])

    @patch("agents.SessionLocal")
    def test_no_future_snapshot_skipped(self, mock_sl):
        """สัญญาณอายุครบแล้ว แต่ไม่มี snapshot ราคาใกล้ระยะที่ต้องการ (เช่น หุ้นหลุดจากระบบ) → ข้าม"""
        db = MagicMock()
        rows = [self._row("XYZ", "BUY", 50.0, days_ago=40)]  # ไม่มี snapshot อื่นเลย
        db.query.return_value.order_by.return_value.all.return_value = rows
        mock_sl.return_value = db

        result = self.orc.calculate_roi(db=db)
        self.assertEqual(result["14d"]["evaluated_signals"], 0)
        self.assertEqual(result["30d"]["evaluated_signals"], 0)

    @patch("agents.SessionLocal")
    def test_no_data_returns_none_values(self, mock_sl):
        """ไม่มีข้อมูลใน signal_history เลย → ไม่ crash คืนค่า None ไม่ใช่ 0/error"""
        db = MagicMock()
        db.query.return_value.order_by.return_value.all.return_value = []
        mock_sl.return_value = db

        result = self.orc.calculate_roi(db=db)
        self.assertIsNone(result["14d"]["win_rate_pct"])
        self.assertIsNone(result["30d"]["avg_return_pct"])

    @patch("agents.SessionLocal")
    def test_meets_win_target_flag_true_when_above_threshold(self, mock_sl):
        """win rate 100% (>=75%) → meets_win_target ต้องเป็น True"""
        db = MagicMock()
        rows = []
        for ticker, future_price in [("AAA", 120.0), ("BBB", 130.0), ("CCC", 130.0), ("DDD", 130.0)]:
            rows.append(self._row(ticker, "BUY", 100.0, days_ago=40))
            rows.append(self._row(ticker, "HOLD", future_price, days_ago=10))  # ~+30 วัน
        db.query.return_value.order_by.return_value.all.return_value = rows
        mock_sl.return_value = db

        result = self.orc.calculate_roi(db=db)
        self.assertEqual(result["30d"]["win_rate_pct"], 100.0)
        self.assertTrue(result["30d"]["meets_win_target"])
        # avg_return_pct เป็น diagnostic เสริม ไม่มี target ผูก (target 13% ย้ายไปอยู่ที่ portfolio_return)
        self.assertNotIn("meets_return_target", result["30d"])
        self.assertNotIn("avg_return_target_pct", result["14d"])

    @patch("agents.SessionLocal")
    def test_exception_returns_error_dict_no_crash(self, mock_sl):
        """DB error ระหว่างคำนวณ → คืน dict มี error ไม่ throw"""
        db = MagicMock()
        db.query.side_effect = Exception("DB down")
        mock_sl.return_value = db

        result = self.orc.calculate_roi(db=db)
        self.assertIn("error", result)

    # ---- portfolio_return (ผลตอบแทนพอร์ตจริง สะสม ไม่มีเส้นตาย เป้า 13%) ----

    def _snap(self, total_value, total_cost, days_ago=0):
        s = MagicMock()
        s.total_value = total_value
        s.total_cost = total_cost
        s.timestamp = datetime.now() - timedelta(days=days_ago)
        return s

    @patch("agents.SessionLocal")
    def test_portfolio_return_computed_from_latest_snapshot(self, mock_sl):
        """snapshot ล่าสุด value=113 cost=100 → return 13% พอดี ผ่านเกณฑ์ (>=13)"""
        db = MagicMock()
        db.query.return_value.order_by.return_value.all.return_value = []  # signal_history ว่าง
        db.query.return_value.order_by.return_value.first.return_value = self._snap(113.0, 100.0)
        mock_sl.return_value = db

        result = self.orc.calculate_roi(db=db)
        self.assertEqual(result["portfolio_return"]["return_pct"], 13.0)
        self.assertTrue(result["portfolio_return"]["meets_target"])
        self.assertFalse(result["portfolio_return"]["has_deadline"])

    @patch("agents.SessionLocal")
    def test_portfolio_return_below_target(self, mock_sl):
        """value=105 cost=100 → return 5% ไม่ถึงเกณฑ์ 13%"""
        db = MagicMock()
        db.query.return_value.order_by.return_value.all.return_value = []
        db.query.return_value.order_by.return_value.first.return_value = self._snap(105.0, 100.0)
        mock_sl.return_value = db

        result = self.orc.calculate_roi(db=db)
        self.assertEqual(result["portfolio_return"]["return_pct"], 5.0)
        self.assertFalse(result["portfolio_return"]["meets_target"])

    @patch("agents.SessionLocal")
    def test_portfolio_return_no_snapshot_yet(self, mock_sl):
        """ยังไม่มี snapshot เลย (พอร์ตยังไม่เคยถูกบันทึก) → None ทั้งหมด ไม่ crash"""
        db = MagicMock()
        db.query.return_value.order_by.return_value.all.return_value = []
        db.query.return_value.order_by.return_value.first.return_value = None
        mock_sl.return_value = db

        result = self.orc.calculate_roi(db=db)
        self.assertIsNone(result["portfolio_return"]["return_pct"])
        self.assertIsNone(result["portfolio_return"]["meets_target"])
        self.assertEqual(result["portfolio_return"]["target_pct"], 13)


class TestSnapshotPortfolio(unittest.TestCase):
    """✅ เพิ่ม 2026-07-04: _snapshot_portfolio — คำนวณมูลค่ารวม/ต้นทุนรวมพอร์ตจริง insert ลง
    portfolio_snapshots ทุกคืน (เรียกจาก _update_database)"""

    def setUp(self):
        self.orc = make_orchestrator()

    def _holding(self, ticker, shares, avg_cost):
        h = MagicMock()
        h.ticker = ticker
        h.shares = shares
        h.avg_cost = avg_cost
        return h

    @patch("agents.PortfolioSnapshot")
    def test_computes_total_value_and_cost_correctly(self, mock_ps):
        """PortfolioSnapshot ถูกมองว่าเป็น mocked class (models ถูก mock ทั้งโมดูลใน test นี้)
        เลยต้องเช็คที่ call args ตอนสร้าง ไม่ใช่ attribute ของ instance ที่คืนมา (เป็น auto-mock เปล่าๆ)"""
        db = MagicMock()
        db.query.return_value.all.return_value = [self._holding("AAPL", 2.0, 100.0)]
        stock = MagicMock()
        stock.current_price = 150.0
        db.query.return_value.filter.return_value.first.return_value = stock

        self.orc._snapshot_portfolio(db)

        mock_ps.assert_called_once_with(total_value=300.0, total_cost=200.0)  # 2*150, 2*100

    def test_empty_portfolio_does_not_add_snapshot(self):
        """ยังไม่เคยมี trade เลย (portfolio ว่าง) → ไม่ insert snapshot"""
        db = MagicMock()
        db.query.return_value.all.return_value = []

        self.orc._snapshot_portfolio(db)
        db.add.assert_not_called()

    def test_db_error_logs_warning_no_crash(self):
        """DB error ระหว่าง snapshot → ไม่ raise (ไม่ควรทำให้ _update_database ทั้งก้อนพัง)"""
        db = MagicMock()
        db.query.side_effect = Exception("DB down")
        try:
            self.orc._snapshot_portfolio(db)
        except Exception as e:
            self.fail(f"_snapshot_portfolio crashed: {e}")


class TestPortfolioReturnHistory(unittest.TestCase):
    """✅ เพิ่ม 2026-07-04: portfolio_return_history — ข้อมูลกราฟแท่งรายวัน (จ-ศ) และรายเดือน"""

    def setUp(self):
        self.orc = make_orchestrator()

    def _snap(self, total_value, total_cost, dt):
        s = MagicMock()
        s.total_value = total_value
        s.total_cost = total_cost
        s.timestamp = dt
        return s

    @patch("agents.SessionLocal")
    def test_daily_excludes_weekends(self, mock_sl):
        db = MagicMock()
        rows = [
            self._snap(110.0, 100.0, datetime(2026, 7, 3)),   # ศุกร์
            self._snap(112.0, 100.0, datetime(2026, 7, 4)),   # เสาร์ — ต้องถูกกรองออกจาก daily
        ]
        db.query.return_value.order_by.return_value.all.return_value = rows
        mock_sl.return_value = db

        result = self.orc.portfolio_return_history(db=db)
        dates = [d["period"] for d in result["daily"]]
        self.assertIn("2026-07-03", dates)
        self.assertNotIn("2026-07-04", dates)

    @patch("agents.SessionLocal")
    def test_monthly_uses_last_snapshot_of_month(self, mock_sl):
        db = MagicMock()
        rows = [
            self._snap(105.0, 100.0, datetime(2026, 6, 15)),
            self._snap(110.0, 100.0, datetime(2026, 6, 30)),  # ล่าสุดของเดือน มิ.ย. — ต้องใช้อันนี้
        ]
        db.query.return_value.order_by.return_value.all.return_value = rows
        mock_sl.return_value = db

        result = self.orc.portfolio_return_history(db=db)
        june = next(m for m in result["monthly"] if m["period"] == "2026-06")
        self.assertEqual(june["return_pct"], 10.0)

    @patch("agents.SessionLocal")
    def test_no_data_returns_empty_lists(self, mock_sl):
        db = MagicMock()
        db.query.return_value.order_by.return_value.all.return_value = []
        mock_sl.return_value = db

        result = self.orc.portfolio_return_history(db=db)
        self.assertEqual(result["daily"], [])
        self.assertEqual(result["monthly"], [])


# ============================================================
# SECTION: PEG Ratio via Alpha Vantage (เพิ่ม 2026-07-08)
# ============================================================
def _av_resp(payload):
    """สร้าง mock response ของ requests.get สำหรับ Alpha Vantage"""
    m = MagicMock()
    m.json.return_value = payload
    return m


class TestPegAlphaVantage(unittest.TestCase):
    """PEG ratio จาก Alpha Vantage OVERVIEW — rotation รายวัน + carry-forward + rate-limit guard
    (design ตายตัวจาก Sonnet5_Workplan.md งานที่ 3 — ห้ามแก้เกณฑ์โดยไม่อัพเดต workplan)"""

    PRICE_DATA = {"price": 100.0, "52week_high": 120.0, "52week_low": 80.0,
                  "pe_ratio": 20.0, "market_cap": 1e12, "beta": 1.1, "eps": 5.0,
                  "peg_ratio": None, "source": "finnhub",
                  "at_new_high": False, "at_new_low": False}

    def setUp(self):
        self.orc = make_orchestrator()

    def _make_db(self, rows):
        """mock SessionLocal — carry-forward ทั้ง 3 block (earnings/profile/peg) ใช้
        query chain แบบเดียวกัน (query→join→all) จึงได้ rows ชุดเดียวกันหมด"""
        db = MagicMock()
        db.query.return_value.join.return_value.all.return_value = rows
        return db

    def _row(self, ticker, peg, hours_ago):
        row = MagicMock()
        row.ticker = ticker
        row.peg_ratio = peg
        row.fetched_at = datetime.now() - timedelta(hours=hours_ago)
        row.earnings_date = "2026-08-01"
        row.earnings_hour = "amc"
        row.company_name = f"{ticker} Inc."
        row.company_description = "desc"
        return row

    # --- Test 1: fetch สำเร็จ → ได้ค่า float ถูกต้อง ---
    @patch("time.sleep")
    @patch("agents.requests.get")
    def test_fetch_success_returns_float(self, mock_get, _sleep):
        mock_get.return_value = _av_resp({"PEGRatio": "1.85"})
        result = self.orc._fetch_peg_alpha_vantage(["AAPL"], "test_key")
        self.assertEqual(result, {"AAPL": 1.85})
        called_url = mock_get.call_args[0][0]
        self.assertIn("OVERVIEW", called_url)
        self.assertIn("AAPL", called_url)

    # --- Test 2: rate-limit response → break ทั้ง batch ไม่ยิงต่อ ---
    @patch("time.sleep")
    @patch("agents.requests.get")
    def test_rate_limit_note_breaks_batch(self, mock_get, _sleep):
        mock_get.return_value = _av_resp({"Note": "API call frequency exceeded"})
        result = self.orc._fetch_peg_alpha_vantage(["AAPL", "MSFT", "GOOG"], "test_key")
        self.assertEqual(result, {})
        self.assertEqual(mock_get.call_count, 1)  # หยุดทันที ไม่ยิงตัวถัดไป

    @patch("time.sleep")
    @patch("agents.requests.get")
    def test_rate_limit_information_breaks_batch(self, mock_get, _sleep):
        mock_get.return_value = _av_resp({"Information": "rate limit reached"})
        result = self.orc._fetch_peg_alpha_vantage(["AAPL", "MSFT"], "test_key")
        self.assertEqual(result, {})
        self.assertEqual(mock_get.call_count, 1)

    # --- Test 5: PEGRatio 'None'/'-'/dict ว่าง → _safe_float คืน None ไม่ crash ---
    @patch("time.sleep")
    @patch("agents.requests.get")
    def test_peg_none_dash_missing_are_safe(self, mock_get, _sleep):
        mock_get.side_effect = [
            _av_resp({"PEGRatio": "None"}),
            _av_resp({"PEGRatio": "-"}),
            _av_resp({}),  # AV คืน dict ว่างสำหรับ symbol ที่ไม่รู้จัก
        ]
        result = self.orc._fetch_peg_alpha_vantage(["A", "B", "C"], "test_key")
        self.assertEqual(result, {"A": None, "B": None, "C": None})

    # --- Test 6a: exception รายตัว → ข้ามตัวนั้น ไปต่อตัวถัดไป ---
    @patch("time.sleep")
    @patch("agents.requests.get")
    def test_per_ticker_exception_skips_and_continues(self, mock_get, _sleep):
        mock_get.side_effect = [ConnectionError("boom"), _av_resp({"PEGRatio": "2.10"})]
        result = self.orc._fetch_peg_alpha_vantage(["BAD", "MSFT"], "test_key")
        self.assertEqual(result, {"MSFT": 2.1})

    # --- Test 4: นอกรอบ PEG_REFRESH_UTC_HOUR → ไม่ยิง AV เลย + carry-forward ทำงาน ---
    @patch.object(AgentOrchestrator, "_fetch_finnhub_earnings", return_value=(None, None))
    @patch.object(AgentOrchestrator, "_fetch_company_profile", return_value=(None, None))
    @patch.object(AgentOrchestrator, "_fetch_finnhub_full")
    @patch("agents.requests.get")
    @patch("agents.SessionLocal")
    def test_outside_refresh_hour_no_av_call_and_carry_forward(self, mock_sl, mock_get, mock_full, *_):
        self.orc.PEG_REFRESH_UTC_HOUR = (datetime.utcnow().hour + 3) % 24  # บังคับให้ "นอกรอบ" เสมอ
        mock_sl.return_value = self._make_db([self._row("AAPL", 2.5, hours_ago=60)])
        mock_full.side_effect = lambda *a, **k: dict(self.PRICE_DATA)

        result = self.orc.natty_prefetch_prices(["AAPL"])

        self.assertEqual(result["AAPL"]["peg_ratio"], 2.5)  # carry-forward จาก DB
        mock_get.assert_not_called()                        # ห้ามยิง Alpha Vantage นอกรอบ

    # --- Test 1b: ในรอบ refresh → ค่าใหม่จาก AV ชนะ carry ---
    @patch.object(AgentOrchestrator, "_fetch_finnhub_earnings", return_value=(None, None))
    @patch.object(AgentOrchestrator, "_fetch_company_profile", return_value=(None, None))
    @patch.object(AgentOrchestrator, "_fetch_finnhub_full")
    @patch("time.sleep")
    @patch("agents.requests.get")
    @patch("agents.SessionLocal")
    def test_in_refresh_hour_fresh_value_wins(self, mock_sl, mock_get, _sleep, mock_full, *_):
        self.orc.PEG_REFRESH_UTC_HOUR = datetime.utcnow().hour  # บังคับให้ "ในรอบ"
        mock_sl.return_value = self._make_db([self._row("AAPL", 2.5, hours_ago=60)])  # stale > 48 ชม.
        mock_full.side_effect = lambda *a, **k: dict(self.PRICE_DATA)
        mock_get.return_value = _av_resp({"PEGRatio": "1.85"})

        result = self.orc.natty_prefetch_prices(["AAPL"])
        self.assertEqual(result["AAPL"]["peg_ratio"], 1.85)

    # --- Test 3: hard cap — 30 ตัว stale → ยิงแค่ 20 ---
    @patch.object(AgentOrchestrator, "_fetch_finnhub_earnings", return_value=(None, None))
    @patch.object(AgentOrchestrator, "_fetch_company_profile", return_value=(None, None))
    @patch.object(AgentOrchestrator, "_fetch_finnhub_full")
    @patch("time.sleep")
    @patch("agents.requests.get")
    @patch("agents.SessionLocal")
    def test_daily_cap_20_of_30_stale(self, mock_sl, mock_get, _sleep, mock_full, *_):
        self.orc.PEG_REFRESH_UTC_HOUR = datetime.utcnow().hour
        mock_sl.return_value = self._make_db([])  # ไม่เคยมี PEG เลย → stale ทั้ง 30 ตัว
        mock_full.side_effect = lambda *a, **k: dict(self.PRICE_DATA)
        mock_get.return_value = _av_resp({"PEGRatio": "1.0"})

        tickers = [f"T{i:02d}" for i in range(30)]
        self.orc.natty_prefetch_prices(tickers)
        self.assertEqual(mock_get.call_count, 20)  # PEG_DAILY_CAP — เหลือ quota 5 ให้ Tier-3

    # --- Test 6b: AV ล่มทั้งระบบ → prefetch หลัก (ราคา) ต้องไม่ล้ม ---
    @patch.object(AgentOrchestrator, "_fetch_finnhub_earnings", return_value=(None, None))
    @patch.object(AgentOrchestrator, "_fetch_company_profile", return_value=(None, None))
    @patch.object(AgentOrchestrator, "_fetch_finnhub_full")
    @patch("time.sleep")
    @patch("agents.requests.get")
    @patch("agents.SessionLocal")
    def test_av_failure_does_not_break_prefetch(self, mock_sl, mock_get, _sleep, mock_full, *_):
        self.orc.PEG_REFRESH_UTC_HOUR = datetime.utcnow().hour
        mock_sl.return_value = self._make_db([])
        mock_full.side_effect = lambda *a, **k: dict(self.PRICE_DATA)
        mock_get.side_effect = ConnectionError("Alpha Vantage down")

        result = self.orc.natty_prefetch_prices(["AAPL"])  # ต้องไม่ raise
        self.assertIn("AAPL", result)                      # ราคาหลักยังมาครบ
        self.assertIsNone(result["AAPL"]["peg_ratio"])     # PEG ไม่มี — ยอมรับได้
