Looking at the logs, I can identify the **TOP 3 issues**:

1. **Yahoo Finance 429 Rate Limiting** — Tier 1 fails for nearly every stock due to `Too Many Requests`. The current `time.sleep(1.2)` + `LimiterSession(per_second=2)` is not enough for cloud IPs. Need exponential backoff retry within Tier 1 before falling to Tier 2.

2. **Tier 2 (Finnhub) Not Being Triggered Fast Enough** — When Tier 1 gets 429, code falls through to Tier 2 correctly, but there's no backoff/retry on the 429 itself before giving up on Tier 1. Many stocks that *could* succeed with a brief wait are being handed off unnecessarily.

3. **MarketAux "no news" Warnings Are Expected But Flood Logs** — The WARNING status for "no news found" is not an error, it's a normal market condition. Logging it as WARNING pollutes the error log and makes real issues harder to spot.

```python
"""
AI Stock Analyzer V4 - Agent System with Multi-Key Fallback
Sequential Workflow with auto-fallback to next API key if current fails
FIXED: Removed async/await, added database validation
"""

import time
import re
import requests
from requests.adapters import HTTPAdapter
from anthropic import Anthropic
from datetime import datetime
import yfinance as yf
from requests_ratelimiter import LimiterSession
import json
import os
from database import SessionLocal
from models import Stock, Trade, Portfolio

# ✅ FIX #I: define TimeoutAdapter ที่ top-level ไม่ redefine ในลูปทุกครั้งที่เรียก natty
class TimeoutAdapter(HTTPAdapter):
    """Force 10-second timeout on all requests — ป้องกัน workflow ค้างถ้า server รับแต่ไม่ตอบ"""
    def send(self, request, **kwargs):
        kwargs.setdefault('timeout', 10)
        return super().send(request, **kwargs)

class AgentOrchestrator:
    def __init__(self):
        self.workflow_log = []
        self.max_retries = 3
        
        # Load multiple API keys from environment
        self.api_keys = [
            os.getenv("ANTHROPIC_API_KEY_1"),
            os.getenv("ANTHROPIC_API_KEY_2"),
            os.getenv("ANTHROPIC_API_KEY_3"),
            os.getenv("ANTHROPIC_API_KEY_4"),
        ]
        # Filter out None values
        self.api_keys = [k for k in self.api_keys if k]
        self.current_key_index = 0
        
        if not self.api_keys:
            raise ValueError("No API keys found in environment variables!")
        
        # Validate DATABASE_URL
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            raise ValueError("DATABASE_URL not set in environment!")
        
        self.session_cost_usd = 0.0  # สะสม cost ทั้ง workflow run นี้

        self.log_action("SYSTEM", f"Loaded {len(self.api_keys)} API keys", "INFO")
        self.log_action("SYSTEM", "Database URL validated", "INFO")

        # ✅ FIX #D: validate API keys ตั้งแต่ boot ไม่รอให้ workflow fail ก่อนค่อยรู้
        if not os.getenv("FINNHUB_API_KEY"):
            self.log_action("SYSTEM", "⚠️ FINNHUB_API_KEY not set — Tier 2 (Finnhub) will be unavailable", "WARNING")
        if not os.getenv("ALPHA_VANTAGE_API_KEY"):
            self.log_action("SYSTEM", "⚠️ ALPHA_VANTAGE_API_KEY not set — Tier 3 (Alpha Vantage) will be unavailable", "WARNING")
        if not os.getenv("MARKETAUX_API_KEY"):
            self.log_action("SYSTEM", "⚠️ MARKETAUX_API_KEY not set — news fetching will be disabled", "WARNING")
        if not os.getenv("GITHUB_TOKEN"):
            self.log_action("SYSTEM", "⚠️ GITHUB_TOKEN not set — นิก cannot push to GitHub (Friday optimization disabled)", "WARNING")
    
    def get_client(self):
        """Get Anthropic client with current API key"""
        api_key = self.api_keys[self.current_key_index]
        return Anthropic(api_key=api_key)
    
    def rotate_to_next_key(self):
        """Switch to next API key on failure"""
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        self.log_action("SYSTEM", f"Rotated to API key #{self.current_key_index + 1}", "WARNING")
    
    def log_action(self, agent_name, action, status="INFO"):
        """บันทึกการทำงานของแต่ละ Agent"""
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "agent": agent_name,
            "action": action,
            "status": status
        }
        self.workflow_log.append(log_entry)
        print(f"[{agent_name}] {action} ({status})")
    
    # Model constants — ใช้ตามประเภทงาน
    MODEL_SONNET = "claude-sonnet-4-6"   # วิเคราะห์หุ้น, validate, report, QA
    MODEL_HAIKU  = "claude-haiku-4-5-20251001"  # งานทั่วไป, สรุป, parse, log

    # ==================== BUDGET GUARD ====================
    # ราคาต่อ 1 ล้าน token (USD) — อ้างอิง Anthropic pricing
    COST_PER_MTK = {
        "sonnet": {"input": 3.0, "output": 15.0, "cache_write": 3.75, "cache_read": 0.30},
        "haiku":  {"input": 0.80, "output": 4.0,  "cache_write": 1.00, "cache_read": 0.08},
    }

    # Limit รายวัน (USD) — จันทร์สูงกว่าเพราะดึงข่าว 72 ชม., ศุกร์บวกค่า นิก
    # Monthly ceiling: (4×1.20) + (12×0.85) + (4×1.10) = $19.40 ✅ ใต้ $20
    DAILY_BUDGET = {
        0: 1.20,  # Monday    — news 72hr
        1: 0.85,  # Tuesday
        2: 0.85,  # Wednesday
        3: 0.85,  # Thursday
        4: 1.10,  # Friday    — + นิก optimize
    }

    def claude_call(self, system_prompt, user_message, agent_name="Claude", model=None, use_cache=False, max_tokens=4096):
        """ใช้ Claude API สำหรับ Agent (with auto-fallback + model selection + caching)
        ✅ model: ระบุ model ที่ต้องการ (default = Sonnet)
        ✅ use_cache: เปิด prompt caching บน system_prompt (ลด cost ~50%)
        ✅ max_tokens: ปรับได้ตามงาน (นิก ต้องการ 8192+ เพื่อเขียน agents.py ทั้งไฟล์)"""
        if model is None:
            model = self.MODEL_SONNET

        max_attempts = len(self.api_keys)
        attempt = 0

        # Build system prompt block — with caching if requested
        if use_cache:
            system_block = [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}]
        else:
            system_block = system_prompt

        messages = [{"role": "user", "content": user_message}]

        while attempt < max_attempts:
            try:
                client = self.get_client()
                response = client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system_block,
                    messages=messages,
                    extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"} if use_cache else {}
                )
                assistant_message = response.content[0].text

                # ✅ BUDGET: นับ token และสะสม cost session
                if hasattr(response, 'usage'):
                    u = response.usage
                    model_key = "haiku" if "haiku" in model else "sonnet"
                    rates = self.COST_PER_MTK[model_key]
                    cache_write  = int(getattr(u, 'cache_creation_input_tokens', 0) or 0)
                    cache_read   = int(getattr(u, 'cache_read_input_tokens', 0) or 0)
                    fresh_input  = max(0, int(getattr(u, 'input_tokens', 0) or 0) - cache_write - cache_read)
                    output_toks  = int(getattr(u, 'output_tokens', 0) or 0)
                    call_cost = (
                        (fresh_input  / 1_000_000) * rates["input"] +
                        (output_toks  / 1_000_000) * rates["output"] +
                        (cache_write  / 1_000_000) * rates["cache_write"] +
                        (cache_read   / 1_000_000) * rates["cache_read"]
                    )
                    self.session_cost_usd += call_cost

                self.log_action(agent_name, f"Claude call success ({model.split('-')[1]} Key#{self.current_key_index + 1})", "SUCCESS")
                return assistant_message

            except Exception as e:
                error_msg = str(e)
                self.log_action(agent_name, f"Claude call error on Key #{self.current_key_index + 1}: {error_msg}", "ERROR")
                # 529 Overloaded — รอก่อน rotate (ไม่ใช่ key ผิด แต่ server busy)
                if "529" in error_msg or "overloaded" in error_msg.lower():
                    self.log_action(agent_name, "⏳ 529 Overloaded — waiting 30s before retry...", "WARNING")
                    time.sleep(30)
                attempt += 1
                if attempt < max_attempts:
                    self.log_action(agent_name, f"Trying next API key ({attempt}/{max_attempts})...", "WARNING")
                    self.rotate_to_next_key()
                else:
                    self.log_action(agent_name, f"All {max_attempts} API keys exhausted", "ERROR")
                    raise

    # ==================== BUDGET CHECK ====================
    def _check_daily_budget(self, db):
        """ตรวจสอบ cost วันนี้ก่อนรัน workflow
        Returns: (ok: bool, today_spent: float, daily_limit: float)"""
        today = datetime.now()
        limit = self.DAILY_BUDGET.get(today.weekday(), 0.85)
        try:
            from models import WorkflowLog
            from sqlalchemy import func
            day_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end   = today.replace(hour=23, minute=59, second=59, microsecond=999999)
            today_cost = db.query(func.sum(WorkflowLog.cost_usd)).filter(
                WorkflowLog.timestamp >= day_start,
                WorkflowLog.timestamp <= day_end
            ).scalar() or 0.0
            return today_cost < limit, today_cost, limit
        except Exception as e:
            self.log_action("BUDGET", f"Budget check error: {str(e)} — proceeding with caution", "WARNING")
            return True, 0.0, limit  # fail-open: ถ้าเช็คไม่ได้ให้รันต่อ

    # ==================== AGENT 1: นัตตี้ (Get News) ====================

    @staticmethod
    def _safe_float(val):
        """แปลงค่าเป็น float อย่างปลอดภัย — ใช้กับ fundamental data (P/E, Market Cap, 52-week)
        ✅ FIX #F: รองรับค่าลบ (เช่น P/E ติดลบกรณีบริษัทขาดทุน) — คืน None เฉพาะ placeholder
        ต่างจาก _safe_positive_float ที่ใช้กับ price ซึ่งต้องเป็นบวกเสมอ"""
        if val is None:
            return None
        cleaned = str(val).strip()
        if cleaned in ("", "None", "N/A", "-", "0", "0.0", "nan", "NaN"):
            return None
        try:
            return float(cleaned)  # ✅ รับค่าลบได้ — P/E ติดลบ = บริษัทขาดทุน ≠ "ไม่มีข้อมูล"
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_positive_float(val):
        """แปลงค่าเป็น float บวกอย่างปลอดภัย — ใช้กับ price เท่านั้น
        ✅ FIX #F: price ต้องเป็นบวกเสมอ ค่าลบหรือ 0 = ข้อมูลเสีย"""
        if val is None:
            return None
        cleaned = str(val).strip()
        if cleaned in ("", "None", "N/A", "-", "0", "0.0", "nan", "NaN"):
            return None
        try:
            result = float(cleaned)
            return result if result > 0 else None
        except (ValueError, TypeError):
            return None

    def _fetch_finnhub_full(self, ticker, api_key):
        """ดึงข้อมูลครบจาก Finnhub: ราคา + 52-week + P/E + Market Cap
        ✅ FIX #2: ใช้ /stock/metric แทน /quote เพื่อได้ 52WeekHigh/Low จริง (ไม่ใช่ intraday)
        Finnhub free tier: 60 req/min — รองรับพอร์ต 30-40 ตัวได้สบาย"""
        try:
            # Call 1: ราคาปัจจุบัน real-time
            quote_url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={api_key}"
            quote = requests.get(quote_url, timeout=10).json()
            price = self._safe_positive_float(quote.get("c"))  # price ต้องบวกเสมอ

            if not price:
                return None

            metric_url = f"https://finnhub.io/api/v1/stock/metric?symbol={ticker}&metric=all&token={api_key}"
            metric = requests.get(metric_url, timeout=10).json().get("metric", {})

            week52_high = self._safe_positive_float(metric.get("52WeekHigh"))
            week52_low  = self._safe_positive_float(metric.get("52WeekLow"))

            # ✅ Sanity check: ราคาต้องอยู่ใน 52-week range
            # ถ้าไม่ใช่ = Finnhub mix currency หรือ share class ผิด (เช่น TSM TWD, ASML Amsterdam)
            at_new_high = False
            at_new_low  = False
            if week52_high and price > week52_high * 1.05:
                # currency/class mismatch — data ไม่น่าเชื่อถือ
                self.log_action("นัตตี้", f"⚠️ {ticker}: price ${price} > 52w_high ${week52_high} — range data unreliable (currency/class mismatch?)", "WARNING")
                week52_high = None
                week52_low  = None
            elif week52_high and price > week52_high:
                # ATH: ราคาทำ New High จริง (เกิน 52w แต่ < 5% = ไม่ใช่ currency mismatch)
                self.log_action("นัตตี้", f"📈 {ticker}: ATH — price ${price} > 52w_high ${week52_high} → updating high", "INFO")
                week52_high = price
                at_new_high = True
            elif week52_low and price < week52_low * 0.95:
                # currency/class mismatch — data ไม่น่าเชื่อถือ
                self.log_action("นัตตี้", f"⚠️ {ticker}: price ${price} < 52w_low ${week52_low} — range data unreliable (currency/class mismatch?)", "WARNING")
                week52_high = None
                week52_low  = None
            elif week52_low and price < week52_low:
                # ATL: ราคาทำ New Low จริง (ต่ำกว่า 52w แต่ไม่เกิน 5% = ไม่ใช่ currency mismatch)
                self.log_action("นัตตี้", f"📉 {ticker}: ATL — price ${price} < 52w_low ${week52_low} → updating low", "INFO")
                week52_low = price
                at_new_low = True

            return {
                "symbol":      ticker,
                "price":       price,
                "52week_high": week52_high,
                "52week_low":  week52_low,
                "at_new_high": at_new_high,
                "at_new_low":  at_new_low,
                "pe_ratio":    self._safe_float(metric.get("peNormalizedAnnual")),
                "market_cap":  self._safe_positive_float(metric.get("marketCapitalization")),
                "source":      "finnhub"
            }
        except Exception as e:
            self.log_action("นัตตี้", f"Finnhub full fetch fail for {ticker}: {str(e)}", "WARNING")
            return None

    def _fetch_alpha_vantage_overview(self, ticker, api_key):
        """ดึงข้อมูลจาก Alpha Vantage OVERVIEW endpoint (Tier 3 - last resort)
        ✅ FIX #3: safe_float อัปเดตรองรับ edge cases ครบ ("-", "N/A", " " ฯลฯ)
        ⚠️  Rate limit: 5 req/min, 25 req/day — ใช้เฉพาะกรณี Tier 1+2 ล้มเหลว"""
        try:
            url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={api_key}"
            res = requests.get(url, timeout=10).json()

            return {
                "pe_ratio":       self._safe_float(res.get("PERatio")),                         # ✅ ลบได้
                "market_cap":     self._safe_positive_float(res.get("MarketCapitalization")),
                "52week_high":    self._safe_positive_float(res.get("52WeekHigh")),
                "52week_low":     self._safe_positive_float(res.get("52WeekLow")),
                "price_fallback": self._safe_positive_float(res.get("200DayMovingAverage")),    # price ต้องบวก
            }
        except Exception as e:
            self.log_action("นัตตี้", f"Alpha Vantage OVERVIEW fail for {ticker}: {str(e)}", "WARNING")
            return {"pe_ratio": None, "market_cap": None, "52week_high": None, "52week_low": None, "price_fallback": None}

    def _fetch_marketaux_news(self, ticker, api_key, include_weekend=False):
        """ดึงข่าวจาก MarketAux — 6 ข่าวใน 1 call พร้อม sentiment score
        
        ✅ P3: ใช้ limit=6 แทน 2 calls → ใช้แค่ 40/100 calls ต่อวัน
        ✅ published_after แบบ smart:
           - ปกติ (อ-ศ): ดึงข่าว 22:00 เมื่อวาน ถึงตอนนี้
           - วันจันทร์ (include_weekend=True): ดึงข่าวตั้งแต่ศุกร์ 22:00 ถึงตอนนี้
        ✅ group_similar=true: MarketAux กรอง near-duplicate อัตโนมัติ
        ✅ sentiment_score: -1 ถึง +1 ต่อ ticker → หนุ่มใช้วิเคราะห์ได้ทันที"""
        try:
            from datetime import timedelta

            # คำนวณ published_after ตาม mode
            now = datetime.now()
            if include_weekend:
                # วันจันทร์ → ดึงตั้งแต่ศุกร์ที่แล้ว 22:00
                days_back = (now.weekday() + 3) % 7  # จันทร์=0 → 3 วัน = ศุกร์
                days_back = max(days_back, 3)  # ย้อนไปอย่างน้อย 3 วัน
                since = (now - timedelta(days=days_back)).replace(
                    hour=22, minute=0, second=0, microsecond=0)
            else:
                # อ-ศ ปกติ → ดึงตั้งแต่เมื่อวาน 22:00
                since = (now - timedelta(days=1)).replace(
                    hour=22, minute=0, second=0, microsecond=0)

            published_after = since.strftime('%Y-%m-%dT%H:%M')

            url = (
                f"https://api.marketaux.com/v1/news/all"
                f"?symbols={ticker}"
                f"&filter_entities=true"
                f"&must_have_entities=true"
                f"&language=en"
                f"&limit=6"
                f"&group_similar=true"
                f"&published_after={published_after}"
                f"&api_token={api_key}"
            )

            res = requests.get(url, timeout=10).json()
            articles = res.get("data", [])

            if not articles:
                # ✅ FIX #3: "no news" เป็น normal market condition ไม่ใช่ error
                # ลด log level จาก WARNING → INFO เพื่อไม่ให้ flood error dashboard
                self.log_action("นัตตี้", f"MarketAux: no news for {ticker} since {published_after}", "INFO")
                return []

            news = []
            for item in articles:
                # หา entity ที่ตรงกับ ticker นี้โดยเฉพาะ
                entity = next(
                    (e for e in item.get("entities", []) if e.get("symbol") == ticker),
                    {}
                )
                news.append({
                    "uuid":            item.get("uuid", ""),
                    "headline":        item.get("title", ""),
                    "snippet":         item.get("snippet", "")[:250],
                    "source":          item.get("source", ""),
                    "published_at":    item.get("published_at", ""),
                    "sentiment_score": entity.get("sentiment_score"),  # -1 ถึง +1
                    "highlights":      entity.get("highlights", [])[:2],
                })

            self.log_action("นัตตี้", f"MarketAux: {len(news)} news for {ticker} (since {published_after})", "SUCCESS")
            return news

        except Exception as e:
            self.log_action("นัตตี้", f"MarketAux news fail for {ticker}: {str(e)}", "WARNING")
            return []

    def _format_news_for_prompt(self, ticker, news_list):
        """แปลง news list เป็น text สำหรับส่งให้หนุ่ม
        ✅ ไม่ต้องเรียก Haiku สรุปแล้ว — ใช้ sentiment_score + highlights โดยตรง
        ประหยัด token และได้ sentiment ที่แม่นกว่า"""
        if not news_list:
            return "ไม่มีข่าวล่าสุด"

        # คำนวณ avg sentiment
        scores = [n["sentiment_score"] for n in news_list if n.get("sentiment_score") is not None]
        avg_sentiment = sum(scores) / len(scores) if scores else None

        if avg_sentiment is not None:
            if avg_sentiment > 0.2:
                sentiment_label = f"เชิงบวก ({avg_sentiment:.2f})"
            elif avg_sentiment < -0.2:
                sentiment_label = f"เชิงลบ ({avg_sentiment:.2f})"
            else:
                sentiment_label = f"กลาง ({avg_sentiment:.2f})"
        else:
            sentiment_label = "ไม่มีข้อมูล"

        lines = [f"📊 Sentiment รวม: {sentiment_label}", f"📰 ข่าวล่าสุด {len(news_list)} ข่าว:"]
        for n in news_list:
            score_str = f"[{n['sentiment_score']:+.2f}]" if n.get("sentiment_score") is not None else ""
            lines.append(f"• {score_str} [{n['source']}] {n['headline']}")
            if n.get("highlights"):
                lines.append(f"  → {n['highlights'][0]}")

        return "\n".join(lines)

    def natty_get_news(self, stocks, days=1, include_weekend=False):
        """นัตตี้: ดึงข้อมูลหุ้นแบบ 3-tier fallback + ข่าวจาก MarketAux
        Tier 1 (yfinance):      ฟรี ครบ แต่ติด 429 บน cloud IP
        Tier 2 (Finnhub):       60 req/min ไม่จำกัด daily
        Tier 3 (Alpha Vantage): 5 req/min 25/day — สำรองสุดท้าย
        ข่าว: MarketAux 6 ข่าว/ticker, sentiment score สำเร็จรูป
        include_weekend=True: วันจันทร์ — ดึงข่าวตั้งแต่ศุกร์ 22:00"""
        self.log_action("นัตตี้", f"Starting fetch ({'Monday mode' if include_weekend else 'regular mode'})...", "INFO")

        FINNHUB_KEY       = os.getenv("FINNHUB_API_KEY")
        ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
        MARKETAUX_KEY     = os.getenv("MARKETAUX_API_KEY")

        if not FINNHUB_KEY:
            self.log_action("นัตตี้", "⚠️  FINNHUB_API_KEY not set — Tier 2 disabled", "WARNING")
        if not ALPHA_VANTAGE_KEY:
            self.log_action("นัตตี้", "⚠️  ALPHA_VANTAGE_API_KEY not set — Tier 3 disabled", "WARNING")
        if not MARKETAUX_KEY:
            self.log_action("นัตตี้", "⚠️  MARKETAUX_API_KEY not set — news disabled", "WARNING")

        news_data = {}

        # ✅ FIX #1a: ลด per_second จาก 2 → 1 เพื่อลด 429 rate จาก Yahoo Finance
        # Cloud IP โดน throttle ง่ายกว่า residential — conservative rate ช่วยได้
        session = LimiterSession(per_second=1)
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        })
        # ✅ FIX #I: TimeoutAdapter ย้ายไป top-level แล้ว ใช้ได้เลยไม่ต้อง redefine
        session.mount('https://', TimeoutAdapter())
        session.mount('http://', TimeoutAdapter())

        for ticker in stocks:
            data = None

            # ===== TIER 1: yfinance =====
            # ✅ FIX #1b: เพิ่ม retry loop สำหรับ 429 ใน Tier 1 ด้วย exponential backoff
            # แทนที่จะ fail ทันทีและ fallback ไป Tier 2 ทุกครั้ง
            # 429 = rate limited ชั่วคราว — รอแล้วลองใหม่มักสำเร็จ
            YFINANCE_MAX_RETRIES = 3
            YFINANCE_BACKOFF_BASE = 5  # วินาที — 5s, 10s, 20s
            for yf_attempt in range(YFINANCE_MAX_RETRIES):
                try:
                    # ✅ FIX #1c: เพิ่ม sleep ก่อน attempt แรกเป็น 2s (แทน 1.2s)
                    # เพราะ log แสดงว่า 1.2s ไม่พอสำหรับ cloud IP
                    sleep_time = YFINANCE_BACKOFF_BASE * (2 ** yf_attempt) if yf_attempt > 0 else 2.0
                    time.sleep(sleep_time)

                    self.log_action("นัตตี้", f"[Tier 1] Fetching {ticker} via yfinance (attempt {yf_attempt + 1}/{YFINANCE_MAX_RETRIES})...", "INFO")
                    stock_obj = yf.Ticker(ticker, session=session)

                    if not stock_obj.info or 'currentPrice' not in stock_obj.info:
                        raise Exception("yfinance: no currentPrice returned")

                    info  = stock_obj.info
                    price = self._safe_positive_float(info.get('currentPrice'))
                    if not price:
                        raise Exception("yfinance: currentPrice is 0 or None")

                    data = {
                        "symbol":      ticker,
                        "price":       price,
                        "52week_high": self._safe_positive_float(info.get('fiftyTwoWeekHigh')),
                        "52week_low":  self._safe_positive_float(info.get('fiftyTwoWeekLow')),
                        "pe_ratio":    self._safe_float(info.get('trailingPE')),         # ✅ ลบได้
                        "market_cap":  self._safe_positive_float(info.get('marketCap')),
                        "source":      "yfinance"
                    }
                    self.log_action("นัตตี้", f"[Tier 1] ✅ {ticker} OK (price={price})", "SUCCESS")
                    break  # ✅ สำเร็จ — ออกจาก retry loop

                except Exception as e:
                    err_str = str(e)
                    is_429 = "429" in err_str or "Too Many Requests" in err_str

                    if is_429 and yf_attempt < YFINANCE_MAX_RETRIES - 1:
                        # ✅ FIX #1d: 429 ไม่ใช่ fatal error — log เป็น INFO ไม่ใช่ WARNING
                        # เพื่อไม่ให้ flood error dashboard (ทุก ticker ก็ 429 ตลอด)
                        next_wait = YFINANCE_BACKOFF_BASE * (2 ** (yf_attempt + 1))
                        self.log_action("นัตตี้", f"[Tier 1] {ticker} 429 rate-limited — waiting {next_wait}s before retry...", "INFO")
                        # ไม่ต้อง sleep ที่นี่ — loop จะ sleep ที่ต้นลูปถัดไป
                    else:
                        # ล้มเหลวถาวร (ไม่ใช่ 429) หรือ exhausted retries
                        self.log_action("นัตตี้", f"[Tier 1] {ticker} failed: {err_str}", "WARNING")
                        break  # ออก retry loop → ลอง Tier 2

            # ===== TIER 2: Finnhub (ถ้า Tier 1 fail) =====
            if data is None and FINNHUB_KEY:
                self.log_action("นัตตี้", f"[Tier 2] Trying Finnhub for {ticker}...", "INFO")
                fh_data = self._fetch_finnhub_full(ticker, FINNHUB_KEY)
                if fh_data:
                    data = fh_data
                    self.log_action("นัตตี้", f"[Tier 2] ✅ {ticker} OK via Finnhub (price={fh_data['price']})", "SUCCESS")

                    # ✅ CROSS-VALIDATE: ถ้า Finnhub ให้ข้อมูลไม่ครบหรือดูผิดปกติ
                    # → ดึง Alpha Vantage OVERVIEW มา patch เฉพาะ field ที่ขาด (ประหยัด AV quota)
                    # Condition: 52w range ถูก sanity check ล้างออก หรือ market_cap น้อยกว่า price
                    # (Finnhub market_cap หน่วยเป็น ล้าน USD — ถ้า < price ใน USD = implied shares < 1M = ผิดแน่)

                    # หุ้ที่ Finnhub ส่ง 52w range สกุลเงินผิด → บังคับใช้ AV แทนเสมอ
                    CROSS_CURRENCY_TICKERS = {'ASML', 'TSM', 'BRK.B'}
                    if ticker in CROSS_CURRENCY_TICKERS and data.get("52week_high") is not None:
                        self.log_action("นัตตี้", f"[Cross-currency] {ticker}: forcing AV 52w range (Finnhub may be wrong currency)", "INFO")
                        data["52week_high"] = None
                        data["52week_low"]  = None

                    mcap = data.get("market_cap")
                    price_now = data.get("price", 0)
                    mcap_suspect = mcap is not None and price_now > 0 and mcap < price_now
                    range_missing = data.get("52week_high") is None or data.get("52week_low") is None

                    if (range_missing or mcap_suspect) and ALPHA_VANTAGE_KEY:
                        reasons = []
                        if range_missing: reasons.append("52w range missing")
                        if mcap_suspect:  reasons.append(f"market_cap {mcap} < price {price_now} (unit mismatch?)")
                        self.log_action("นัตตี้", f"[AV cross-check] {ticker}: {', '.join(reasons)} — fetching AV OVERVIEW...", "INFO")
                        ov = self._fetch_alpha_vantage_overview(ticker, ALPHA_VANTAGE_KEY)

                        # Patch 52w range (AV คืน USD ตรง — ใช้ได้เลย)
                        if range_missing and ov.get("52week_high") and ov.get("52week_low"):
                            av_h = ov["52week_high"]
                            av_l = ov["52week_low"]
                            # sanity check: AV ส่ง USD ตรง — ยอมรับถ้า price ไม่ห่างจาก range เกิน 10%
                            price_in_range = av_l * 0.90 <= price_now <= av_h * 1.10
                            if price_in_range:
                                data["52week_high"] = av_h
                                data["52week_low"]  = av_l
                                self.log_action("นัตตี้", f"[AV patch ✅] {ticker}: 52w range → ${av_l:.2f}–${av_h:.2f}", "SUCCESS")
                            else:
                                self.log_action("นัตตี้", f"[AV patch ⚠️] {ticker}: AV 52w range also unreliable (price=${price_now:.2f} vs ${av_l:.2f}–${av_h:.2f}) — skipping", "WARNING")

                        # Patch market_cap (AV คืน full USD → หาร 1M ให้ตรง unit Finnhub)
                        if mcap_suspect and ov.get("market_cap") and ov["market_cap"] > price_now * 1_000_000:
                            data["market_cap"] = ov["market_cap"] / 1_000_000  # normalize → ล้าน USD
                            self.log_action("นัตตี้", f"[AV patch ✅] {ticker}: market_cap patched → ${data['market_cap']:,.0f}M", "SUCCESS")
                else:
                    self.log_action("นัตตี้", f"[Tier 2] Finnhub returned no usable data for {ticker}", "WARNING")

            # ===== TIER 3: Alpha Vantage (ถ้า Tier 1+2 fail) =====
            if data is None and ALPHA_VANTAGE_KEY:
                self.log_action("นัตตี้", f"[Tier 3] Trying Alpha Vantage for {ticker}...", "INFO")
                ov = self._fetch_alpha_vantage_overview(ticker, ALPHA_VANTAGE_KEY)
                price = ov.get("price_fallback")
                if price:
                    data = {
                        "symbol":      ticker,
                        "price":       price,
                        "52week_high": ov.get("52week_high"),
                        "52week_low":  ov.get("52week_low"),
                        "pe_ratio":    ov.get("pe_ratio"),
                        "market_cap":  ov.get("market_cap"),
                        "source":      "alpha_vantage"
                    }
                    self.log_action("นัตตี้", f"[Tier 3] ✅ {ticker} OK via Alpha Vantage", "SUCCESS")
                else:
                    self.log_action("นัตตี้", f"[Tier 3] Alpha Vantage returned no price for {ticker}", "WARNING")

            # ===== ทุก Tier fail → skip ticker นี้ ไม่ส่งข้อมูลไม่ครบให้หนุ่ม =====
            if data is None:
                self.log_action("นัตตี้", f"❌ All tiers failed for {ticker} — skipping (ไม่วิเคราะห์ด้วยข้อมูลไม่ครบ)", "ERROR")
                continue

            # ===== ATH/ATL sanity check สำหรับ yfinance / Alpha Vantage (Finnhub จัดการใน _fetch_finnhub_full แล้ว) =====
            if "at_new_high" not in data:
                p   = data.get("price", 0)
                w52h = data.get("52week_high")
                w52l = data.get("52week_low")
                ath, atl = False, False
                if w52h and w52l:
                    if p > w52h * 1.05 or p < w52l * 0.95:
                        data["52week_high"] = None
                        data["52week_low"]  = None
                    elif p > w52h:
                        data["52week_high"] = p
                        ath = True
                        self.log_action("นัตตี้", f"📈 {ticker}: ATH — price ${p} > 52w_high ${w52h} → updating high", "INFO")
                    elif p < w52l:
                        data["52week_low"] = p
                        atl = True
                        self.log_action("นัตตี้", f"📉 {ticker}: ATL — price ${p} < 52w_low ${w52l} → updating low", "INFO")
                data["at_new_high"] = ath
                data["at_new_low"]  = atl
            elif "at_new_low" not in data:
                data["at_new_low"] = False

            # log เตือนถ้าขาด P/E (หนุ่มจะได้รับแจ้งใน prompt)
            # ✅ FIX #2: ลด P/E warning เป็น INFO — ปกติมากสำหรับ growth/loss-making stocks
            # ZS, OKTA เป็นบริษัทที่ขาดทุนอยู่แล้ว การ log WARNING ทุกครั้งทำให้ noise สูง
            if data.get("pe_ratio") is None:
                self.log_action("นัตตี้", f"ℹ️  {ticker}: P/E unavailable (loss-making co. หรือ API ไม่มีข้อมูล)", "INFO")

            # ✅ P3: ดึงข่าวจาก MarketAux (sentiment score สำเร็จรูป ไม่ต้องสรุปด้วย Haiku)
            if MARKETAUX_KEY:
                news_list = self._fetch_marketaux_news(ticker, MARKETAUX_KEY, include_weekend=include_weekend)
                data["news_summary"] = self._format_news_for_prompt(ticker, news_list)
                data["news_count"]   = len(news_list)
                data["avg_sentiment"] = (
                    sum(n["sentiment_score"] for n in news_list if n.get("sentiment_score") is not None)
                    / max(1, sum(1 for n in news_list if n.get("sentiment_score") is not None))
                ) if news_list else None
            else:
                data["news_summary"]  = "ไม่มี MarketAux key — ไม่ได้ดึงข่าว"
                data["news_count"]    = 0
                data["avg_sentiment"] = None

            news_data[ticker] = data

        self.log_action("นัตตี้", f"Fetched {len(news_data)}/{len(stocks)} stocks (source breakdown in logs above)", "SUCCESS")
        return news_data


    # ==================== AGENT 2: หนุ่ม (Analyze Stocks) ====================
    def num_analyze_stocks(self, news_data, stocks):
        """หนุ่ม: วิเคราะห์หุ้นด้วย Claude Sonnet + ข่าวจากนัตตี้
        ✅ Sonnet: reasoning แม่นสำหรับ signal ที่กระทบการลงทุน
        ✅ Prompt caching: ประหยัด ~50% บน system_prompt ที่เหมือนกันทุก ticker"""
        self.log_action("หนุ่ม", "Starting stock analysis...", "INFO")
        
        try:
            system_prompt = """You are หนุ่ม (Num), a professional stock analyst.
Analyze the stock data AND recent news to provide:
1. BUY/HOLD/SELL signal
2. Confidence score (0-1)
3. 3 support/resistance levels (S1, S2, S3)
4. Brief reasoning in Thai (รวม sentiment ข่าวด้วย)

IMPORTANT:
- ถ้า P/E ติดลบ = บริษัทขาดทุน ให้ factor นี้เข้าไปใน signal
- ถ้า Data Source เป็น lower reliability ให้ลด confidence อย่างน้อย 0.15
- ถ้าข่าวเป็นลบมาก ให้ลด confidence หรือเปลี่ยน signal เป็น HOLD/SELL

Return ONLY JSON format:
{
    "ticker": "AAPL",
    "signal": "BUY",
    "confidence": 0.85,
    "s1": 150.0,
    "s2": 145.0,
    "s3": 140.0,
    "reasoning": "..."
}"""

            analysis_results = {}

            skipped_no_data = [t for t in stocks if t not in news_data]
            if skipped_no_data:
                self.log_action("หนุ่ม", f"Skipping {skipped_no_data} — no data from นัตตี้", "WARNING")

            for ticker, data in news_data.items():
                pe_display = data.get('pe_ratio')
                if pe_display is not None:
                    pe_text = f"{pe_display:.2f}" + (" (ขาดทุน — P/E ติดลบ)" if pe_display < 0 else "")
                else:
                    pe_text = "N/A (ไม่มีข้อมูล)"

                mcap_display = data.get('market_cap')
                mcap_text = f"${mcap_display:,.0f}M USD" if mcap_display is not None else "N/A (ไม่มีข้อมูล)"

                source = data.get('source', 'unknown')
                source_note = {
                    'yfinance':      "Real-time price (high reliability)",
                    'finnhub':       "Real-time price via Finnhub (high reliability)",
                    'alpha_vantage': "200-day moving average as price proxy (lower reliability — not real-time)",
                }.get(source, f"Unknown source: {source} (treat with caution)")

                news_summary  = data.get('news_summary', 'ไม่มีข่าว')
                avg_sentiment = data.get('avg_sentiment')
                sentiment_note = (
                    f"Market Sentiment Score: {avg_sentiment:+.2f} "
                    f"({'เชิงบวก' if avg_sentiment > 0.2 else 'เชิงลบ' if avg_sentiment < -0.2 else 'กลาง'})"
                    if avg_sentiment is not None else "Market Sentiment Score: N/A"
                )

                new_high_note = "\n- ⚠️ ATH: ราคาทำ NEW 52-WEEK HIGH — ไม่มีแนวต้านชัดเจนด้านบน ให้ระบุใน reasoning และระวัง overextension" if data.get('at_new_high') else ""
                new_low_note  = "\n- ⚠️ ATL: ราคาทำ NEW 52-WEEK LOW — momentum เป็นลบ ให้ระบุใน reasoning ว่าเป็น capitulation หรือ breakdown" if data.get('at_new_low') else ""

                user_message = f"""Analyze this stock:
Symbol: {ticker}
Current Price: ${data.get('price', 0)}
52-week High: ${data.get('52week_high') or 'N/A'}{'  ← ATH (ราคาปัจจุบัน = 52w high)' if data.get('at_new_high') else ''}
52-week Low: ${data.get('52week_low') or 'N/A'}{'  ← ATL (ราคาปัจจุบัน = 52w low)' if data.get('at_new_low') else ''}
P/E Ratio: {pe_text}
Market Cap: {mcap_text}
Data Source: {source_note}
{sentiment_note}

Recent News:
{news_summary}

Note:
- ถ้า P/E หรือ Market Cap เป็น N/A ให้วิเคราะห์จาก price และ 52-week range แทน และลด confidence
- ถ้า P/E ติดลบ = บริษัทขาดทุน ให้ factor นี้เข้าใน signal
- ถ้า sentiment score ต่ำกว่า -0.3 ให้ระวัง อาจปรับ signal เป็น HOLD/SELL
- ถ้า Data Source เป็น lower reliability ให้ลด confidence อย่างน้อย 0.15{new_high_note}{new_low_note}

Provide analysis in JSON format."""

                try:
                    # ✅ Sonnet + caching บน system_prompt
                    response = self.claude_call(system_prompt, user_message, "หนุ่ม",
                                                model=self.MODEL_SONNET, use_cache=True)
                    try:
                        json_start = response.find('{')
                        json_end   = response.rfind('}') + 1
                        result     = json.loads(response[json_start:json_end])

                        if result.get('signal') not in ('BUY', 'HOLD', 'SELL'):
                            self.log_action("หนุ่ม", f"{ticker}: invalid signal '{result.get('signal')}' → defaulting HOLD", "WARNING")
                            result['signal'] = 'HOLD'

                        # Merge นัตตี้ flags เข้า result เพื่อ flow ต่อไปถึง DB
                        result['price']       = data.get('price', 0)
                        result['at_new_high'] = data.get('at_new_high', False)
                        result['at_new_low']  = data.get('at_new_low', False)
                        analysis_results[ticker] = result

                    except json.JSONDecodeError:
                        fallback_price = data.get('price') or 0
                        if not fallback_price:
                            analysis_results[ticker] = {"ticker": ticker, "signal": "HOLD", "confidence": 0.0,
                                                        "s1": None, "s2": None, "s3": None,
                                                        "reasoning": "No price data — analysis skipped"}
                        else:
                            analysis_results[ticker] = {"ticker": ticker, "signal": "HOLD", "confidence": 0.5,
                                                        "s1": fallback_price * 0.95,
                                                        "s2": fallback_price * 0.90,
                                                        "s3": fallback_price * 0.85,
                                                        "reasoning": "Could not parse analysis"}
                except Exception as e:
                    self.log_action("หนุ่ม", f"Analysis failed for {ticker}: {str(e)}", "WARNING")
                    continue

            self.log_action("หนุ่ม", f"Analyzed {len(analysis_results)} stocks", "SUCCESS")
            return analysis_results

        except Exception as e:
            self.log_action("หนุ่ม", f"Analysis failed: {str(e)}", "ERROR")
            raise

    # ==================== AGENT 3: มด (Cross-Validate) ====================
    def mud_cross_validate(self, analysis_results):
        """มด: ตรวจสอบความถูกต้องของ signals — Sonnet + caching"""
        self.log_action("มด", "Starting cross-validation...", "INFO")
        try:
            system_prompt = """You are มด (Mud), a validation expert.
Review the stock analysis and validate:
1. Signal consistency with confidence score
2. Confidence score reasonableness (0-1)
3. Support/Resistance levels logic (S1 > S2 > S3 for downside levels)

Return JSON:
{
    "ticker": "AAPL",
    "is_valid": true,
    "issues": [],
    "recommendation": "PASS"
}

IMPORTANT: "recommendation" must be exactly "PASS" or "FAIL" — no other values allowed (e.g. PASS_WITH_WARNING is NOT valid)."""
            validated_results = {}

            for ticker, analysis in analysis_results.items():
                mud_input = {
                    "ticker":     ticker,
                    "signal":     analysis.get("signal"),
                    "confidence": analysis.get("confidence"),
                    "s1":         analysis.get("s1"),
                    "s2":         analysis.get("s2"),
                    "s3":         analysis.get("s3"),
                    "reasoning":  analysis.get("reasoning"),
                }
                user_message = f"""Validate this analysis:
{json.dumps(mud_input, indent=2)}

Check if signal, confidence, and S-levels are consistent."""

                try:
                    response = self.claude_call(system_prompt, user_message, "มด",
                                                model=self.MODEL_SONNET, use_cache=True)
                    try:
                        result = json.loads(response[response.find('{'):response.rfind('}')+1])
                        validated_results[ticker] = {**analysis, "validation": result}
                    except json.JSONDecodeError:
                        self.log_action("มด", f"Parse fail for {ticker} — NEEDS_REVIEW", "WARNING")
                        validated_results[ticker] = {**analysis, "validation": {"is_valid": None, "recommendation": "NEEDS_REVIEW", "issues": ["Parse failed"]}}
                except Exception as e:
                    self.log_action("มด", f"Validation failed for {ticker}: {str(e)}", "WARNING")
                    validated_results[ticker] = {**analysis, "validation": {"is_valid": None, "recommendation": "NEEDS_REVIEW", "issues": [str(e)]}}

            self.log_action("มด", f"Validated {len(validated_results)} stocks", "SUCCESS")
            return validated_results
        except Exception as e:
            self.log_action("มด", f"Cross-validation failed: {str(e)}", "ERROR")
            raise
    # ==================== AGENT 4: แฮรี่ (Monitor Portfolio) ====================
    def harry_monitor_portfolio(self, analysis_results):
        """แฮรี่: ตรวจสอบ Portfolio ว่า align กับ signals ไหม"""
        self.log_action("แฮรี่", "Monitoring portfolio...", "INFO")
        
        db = None
        try:
            db = SessionLocal()
            portfolio_holdings = db.query(Portfolio).all()
            
            portfolio_status = {
                "total_holdings": len(portfolio_holdings),
                "portfolio_alignment": [],
                "recommendations": []
            }
            
            for holding in portfolio_holdings:
                if holding.ticker in analysis_results:
                    analysis = analysis_results[holding.ticker]
                    signal = analysis.get('signal', 'HOLD')
                    
                    alignment = {
                        "ticker": holding.ticker,
                        "current_signal": signal,
                        "shares": holding.shares,
                        "is_aligned": self._check_alignment(signal, holding.shares),
                        "action": self._get_action(signal, holding.shares)
                    }
                    portfolio_status["portfolio_alignment"].append(alignment)
            
            self.log_action("แฮรี่", f"Monitored {len(portfolio_holdings)} holdings", "SUCCESS")
            return portfolio_status
            
        except Exception as e:
            self.log_action("แฮรี่", f"Portfolio monitoring failed: {str(e)}", "ERROR")
            raise
        finally:
            # ✅ ปิด connection เสมอ ไม่ว่าจะสำเร็จหรือ exception เพื่อป้องกัน connection leak
            if db is not None:
                db.close()
    
    def _check_alignment(self, signal, shares):
        """ตรวจสอบว่า signal align กับ holdings ไหม"""
        if signal == "SELL" and shares > 0:
            return False
        if signal == "BUY" and shares == 0:
            return False
        return True
    
    def _get_action(self, signal, shares):
        """แนะนำ action สำหรับ portfolio"""
        if signal == "BUY" and shares == 0:
            return "CONSIDER_BUYING"
        if signal == "SELL" and shares > 0:
            return "CONSIDER_SELLING"
        return "HOLD"

    # ==================== AGENT 5: เจน (Generate Report) ====================
    def jen_generate_report(self, analysis_results, portfolio_status, retry_hint=None):
        """เจน: สร้าง Report — Sonnet + caching"""
        self.log_action("เจน", f"Generating report{'  (retry with hint)' if retry_hint else ''}...", "INFO")
        try:
            system_prompt = """You are เจน (Jen), a market report writer.
Create a professional market report summarizing:
1. Market overview
2. Top signals (BUY/SELL)
3. Portfolio recommendations
4. Risk assessment

CRITICAL RULES:
1. Write in Thai.
2. Return JSON with a 'report_html' field containing the complete formatted report.
3. DO NOT embed or include ANY raw JavaScript code, scripts, dynamic templates, or tags like 'new Date()' or '.toLocaleDateString()' inside the HTML content.
4. All dates, times, and statistics must be rendered as plain static Thai text only. No dynamic calculations allowed inside the report."""

            jen_summary = {
                ticker: {
                    "signal":       data.get("signal"),
                    "confidence":   data.get("confidence"),
                    "s1":           data.get("s1"),
                    "s2":           data.get("s2"),
                    "s3":           data.get("s3"),
                    "reasoning":    data.get("reasoning"),
                    "pe_ratio":     data.get("pe_ratio"),
                    "price":        data.get("price"),
                    "news_summary": data.get("news_summary", ""),
                }
                for ticker, data in analysis_results.items()
            }

            retry_section = f"\n\nFEEDBACK FROM PREVIOUS ATTEMPT:\n{retry_hint}\nPlease address the above issues in this report." if retry