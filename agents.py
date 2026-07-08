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
from datetime import datetime, timedelta
import yfinance as yf
from requests_ratelimiter import LimiterSession
import json
import os
from database import SessionLocal
from models import Stock, Trade, Portfolio, SignalHistory, PortfolioSnapshot

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
    # ปรับ 2026-07-01: เดิมเพดาน $19.40/เดือน สูงกว่าเป้าจริงของ MBBook ($10 เป้า / $12 เพดานที่รับได้) เกือบเท่าตัว
    #   → ตึงลงเหลือ buffer ~15% เหนือ cost จริงโดยประมาณของแต่ละวัน (Tue-Wed วัดจริงแล้ว ~$0.52/run)
    # Monthly ceiling: (4×0.85) + (12×0.60) + (4×0.75) = $13.60 (เผื่อ buffer เหนือเพดาน $12 ไว้ก่อน
    #   เพราะยังไม่มีข้อมูลจริงของวันจันทร์ — ดู Pending.md หัวข้อ "ทบทวน cost หลัง 3 เดือน" แล้วปรับอีกทีเมื่อมีข้อมูลจริง)
    DAILY_BUDGET = {
        0: 0.85,  # Monday    — news 72hr
        1: 0.60,  # Tuesday
        2: 0.60,  # Wednesday
        3: 0.60,  # Thursday
        4: 0.75,  # Friday    — + นิก optimize
    }

    # ==================== PEG RATIO (Alpha Vantage) ====================
    # ✅ เพิ่ม 2026-07-08: Finnhub field 'pegRatio' เดาผิด (null ทุกตัว — ยืนยันจาก prod จริง)
    # ใช้ Alpha Vantage OVERVIEW.PEGRatio แทน (ยืนยันจาก doc ว่ามีจริง) แต่ free tier
    # จำกัด 25 req/day → refresh เฉพาะ prefetch รอบชั่วโมง PEG_REFRESH_UTC_HOUR
    # สูงสุด PEG_DAILY_CAP ตัว/วัน เรียงจาก stale สุด (หมุนครบ 30 ตัวใน 2 วัน)
    # รอบ prefetch อื่นๆ carry-forward ค่าล่าสุดจาก DB เหมือน earnings_date
    PEG_REFRESH_UTC_HOUR = 2   # 02:xx UTC = prefetch รอบ 09:05 Bangkok (รอบแรกของวัน)
    PEG_DAILY_CAP = 20         # เหลือ quota 5/25 ให้ Tier-3 price fallback ที่ใช้ Alpha Vantage อยู่แล้ว
    PEG_STALE_HOURS = 48       # PEG เปลี่ยนช้า — อายุเกิน 48 ชม. ค่อยถือว่า stale

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
        limit = self.DAILY_BUDGET.get(today.weekday(), 0.60)
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
                # ✅ เพิ่ม 2026-07-05 (task #56): beta ยืนยันแล้วว่ามี field นี้จริงใน metric=all
                # eps ใช้คู่กับ pe_ratio ("peNormalizedAnnual" → "epsNormalizedAnnual")
                # peg_ratio ยังไม่ยืนยัน field ชัดเจน — ลองชื่อ "pegRatio" ไปก่อน ต้องเช็ค log จริง
                "beta":        self._safe_float(metric.get("beta")),
                "eps":         self._safe_float(metric.get("epsNormalizedAnnual")),
                "peg_ratio":   self._safe_float(metric.get("pegRatio")),
                "source":      "finnhub"
            }
        except Exception as e:
            self.log_action("นัตตี้", f"Finnhub full fetch fail for {ticker}: {str(e)}", "WARNING")
            return None

    def _fetch_finnhub_earnings(self, ticker, api_key):
        """ดึงวันประกาศงบถัดไป/ล่าสุดจาก Finnhub /calendar/earnings
        ✅ เพิ่ม 2026-07-05 (task #56) — เรียกไม่บ่อย (เช็คเงื่อนไขที่ natty_prefetch_prices ก่อนเรียก
        เพราะข้อมูลนี้เปลี่ยนแค่ทุกไตรมาส ต่างจากราคาที่ต้องอัพเดตทุกชั่วโมง กันชน rate limit Finnhub
        คืน (earnings_date: datetime|None, earnings_hour: 'bmo'/'amc'/'dmh'|None)"""
        try:
            from datetime import date, timedelta as _td
            today = date.today()
            to_date = today + _td(days=180)
            url = (f"https://finnhub.io/api/v1/calendar/earnings?"
                   f"from={today.isoformat()}&to={to_date.isoformat()}&symbol={ticker}&token={api_key}")
            rows = requests.get(url, timeout=10).json().get("earningsCalendar", [])
            if not rows:
                return None, None
            rows.sort(key=lambda r: r.get("date") or "9999-99-99")
            nearest = rows[0]
            earnings_date = (
                datetime.strptime(nearest["date"], "%Y-%m-%d") if nearest.get("date") else None
            )
            return earnings_date, nearest.get("hour")
        except Exception as e:
            self.log_action("นัตตี้", f"Finnhub earnings calendar fail for {ticker}: {str(e)}", "WARNING")
            return None, None

    def _fetch_company_profile(self, ticker, api_key):
        """✅ เพิ่ม 2026-07-05 (รอบ 5): ชื่อเต็มบริษัท + คำอธิบายบริษัท — MBBook ขอให้หามาเพิ่ม
        (popup Tickers/Portfolio ไม่มีข้อมูลนี้เลยมาตลอด)
        - ชื่อเต็ม: Finnhub /stock/profile2 field 'name' — endpoint ฟรี ยืนยันจาก doc จริง
        - คำอธิบาย: Finnhub profile2 ไม่มี field คำอธิบายธุรกิจ ต้องใช้ yfinance
          'longBusinessSummary' แทน (ภาษาอังกฤษ ยาว ตัดเหลือ ~400 ตัวอักษรกันยาวเกินไปใน popup)
        เรียกไม่บ่อย (เหมือน earnings_date) เพราะข้อมูลนี้แทบไม่เปลี่ยนเลย"""
        name = None
        description = None
        try:
            profile_url = f"https://finnhub.io/api/v1/stock/profile2?symbol={ticker}&token={api_key}"
            profile = requests.get(profile_url, timeout=10).json()
            name = profile.get("name") or None
        except Exception as e:
            self.log_action("นัตตี้", f"Finnhub profile2 fail for {ticker}: {str(e)}", "WARNING")

        try:
            import time as _time
            _time.sleep(0.5)
            info = yf.Ticker(ticker).info
            summary = info.get("longBusinessSummary")
            if summary:
                description = summary[:400].rsplit(" ", 1)[0] + "..." if len(summary) > 400 else summary
            if not name:
                name = info.get("longName") or info.get("shortName") or None
        except Exception as e:
            self.log_action("นัตตี้", f"yfinance longBusinessSummary fail for {ticker}: {str(e)}", "WARNING")

        return name, description

    def _fetch_peg_alpha_vantage(self, tickers, api_key):
        """✅ เพิ่ม 2026-07-08: ดึง PEG ratio จาก Alpha Vantage OVERVIEW (field 'PEGRatio')
        เรียกทีละตัว + sleep 1s ระหว่างตัว (free tier: 5 req/min, 25 req/day)
        - เจอ rate-limit response ({'Note':...}/{'Information':...}) → หยุดทั้ง batch ทันที ไม่ยิงต่อ
        - error รายตัว → log แล้วข้ามไปตัวถัดไป
        Returns: {ticker: peg_float_หรือ_None} เฉพาะตัวที่ได้ response ปกติ"""
        import time as _time
        fresh = {}
        for i, ticker in enumerate(tickers):
            try:
                if i > 0:
                    _time.sleep(1)  # กัน 5 req/min limit
                url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={api_key}"
                resp = requests.get(url, timeout=10).json()
                if not isinstance(resp, dict) or "Note" in resp or "Information" in resp:
                    self.log_action("นัตตี้-prefetch",
                                    f"⚠️ Alpha Vantage rate limit ระหว่างดึง PEG ({ticker}) — หยุด batch นี้ "
                                    f"(ได้มา {len(fresh)}/{len(tickers)} ตัว ที่เหลือ carry-forward)", "WARNING")
                    break
                fresh[ticker] = self._safe_float(resp.get("PEGRatio"))
            except Exception as e:
                self.log_action("นัตตี้-prefetch", f"PEG fetch fail {ticker}: {str(e)}", "WARNING")
        return fresh

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
                self.log_action("นัตตี้", f"MarketAux: no news for {ticker} since {published_after}", "WARNING")
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

    def natty_prefetch_prices(self, stocks):
        """Pre-fetch ราคา + fundamentals ผ่าน Finnhub → เก็บใน HourlyCache
        เรียกโดย GitHub Actions ทุกชั่วโมง Mon-Fri 09:00-21:00 Bangkok
        ที่ 22:00 natty_get_news() จะอ่านจาก cache แทนการ fetch live → เร็วขึ้น ~10 นาที
        Returns: dict {ticker: data} ที่ fetch สำเร็จ"""
        from models import HourlyCache
        from sqlalchemy import func as _func
        FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")
        if not FINNHUB_KEY:
            self.log_action("นัตตี้-prefetch", "⚠️ FINNHUB_API_KEY not set — prefetch aborted", "ERROR")
            return {}

        self.log_action("นัตตี้-prefetch", f"Pre-fetching {len(stocks)} tickers via Finnhub...", "INFO")
        fetched = {}

        # ✅ เพิ่ม 2026-07-05 (task #56): earnings_date เปลี่ยนแค่ทุกไตรมาส ไม่ต้องเรียก
        # /calendar/earnings ทุกรอบ prefetch รายชั่วโมงเหมือนราคา (กัน rate limit Finnhub 60 req/min)
        # หา row ล่าสุดที่มี earnings_date ต่อ ticker — ถ้า fetch มาไม่เกิน 20 ชม. ใช้ค่าเดิม (carry forward
        # ไปใส่ row ใหม่ทุกชั่วโมง เพราะแต่ละรอบ insert row ใหม่เสมอ ไม่ overwrite row เก่า)
        # ถ้าเก่ากว่า 20 ชม. (หรือไม่เคยมีเลย) ค่อยเรียก Finnhub ใหม่รอบนี้
        earnings_carry = {}    # {ticker: (earnings_date, earnings_hour)}
        earnings_is_fresh = {} # {ticker: True/False}
        db_check = None
        try:
            db_check = SessionLocal()
            latest_sq = (
                db_check.query(HourlyCache.ticker, _func.max(HourlyCache.fetched_at).label("max_at"))
                .filter(HourlyCache.ticker.in_(stocks), HourlyCache.earnings_date.isnot(None))
                .group_by(HourlyCache.ticker)
                .subquery()
            )
            rows = (
                db_check.query(HourlyCache)
                .join(latest_sq, (HourlyCache.ticker == latest_sq.c.ticker) &
                                 (HourlyCache.fetched_at == latest_sq.c.max_at))
                .all()
            )
            recent_cutoff = datetime.now() - __import__("datetime").timedelta(hours=20)
            for row in rows:
                earnings_carry[row.ticker] = (row.earnings_date, row.earnings_hour)
                earnings_is_fresh[row.ticker] = row.fetched_at >= recent_cutoff
        except Exception as e:
            self.log_action("นัตตี้-prefetch", f"เช็ค earnings freshness ล้มเหลว (ไม่กระทบราคา): {str(e)}", "WARNING")
        finally:
            if db_check:
                db_check.close()

        # ✅ เพิ่ม 2026-07-05 (รอบ 5): ชื่อเต็มบริษัท/คำอธิบาย — carry-forward เหมือน earnings
        # (เปลี่ยนแทบไม่เคยเปลี่ยนเลย ไม่ต้องเรียก Finnhub/yfinance ใหม่ทุกชั่วโมง)
        profile_carry = {}
        profile_is_fresh = {}
        db_check2 = None
        try:
            db_check2 = SessionLocal()
            latest_sq2 = (
                db_check2.query(HourlyCache.ticker, _func.max(HourlyCache.fetched_at).label("max_at"))
                .filter(HourlyCache.ticker.in_(stocks), HourlyCache.company_name.isnot(None))
                .group_by(HourlyCache.ticker)
                .subquery()
            )
            rows2 = (
                db_check2.query(HourlyCache)
                .join(latest_sq2, (HourlyCache.ticker == latest_sq2.c.ticker) &
                                   (HourlyCache.fetched_at == latest_sq2.c.max_at))
                .all()
            )
            recent_cutoff2 = datetime.now() - __import__("datetime").timedelta(hours=20)
            for row in rows2:
                profile_carry[row.ticker] = (row.company_name, row.company_description)
                profile_is_fresh[row.ticker] = row.fetched_at >= recent_cutoff2
        except Exception as e:
            self.log_action("นัตตี้-prefetch", f"เช็ค company profile freshness ล้มเหลว (ไม่กระทบราคา): {str(e)}", "WARNING")
        finally:
            if db_check2:
                db_check2.close()

        # ✅ เพิ่ม 2026-07-08: PEG ratio — carry-forward จาก row ล่าสุดที่มีค่า + refresh ผ่าน
        # Alpha Vantage เฉพาะรอบ PEG_REFRESH_UTC_HOUR สูงสุด PEG_DAILY_CAP ตัว/วัน (ดู constants)
        peg_carry = {}  # {ticker: peg ล่าสุดที่ไม่ null}
        peg_age = {}    # {ticker: fetched_at ของ row นั้น}
        db_check3 = None
        try:
            db_check3 = SessionLocal()
            latest_sq3 = (
                db_check3.query(HourlyCache.ticker, _func.max(HourlyCache.fetched_at).label("max_at"))
                .filter(HourlyCache.ticker.in_(stocks), HourlyCache.peg_ratio.isnot(None))
                .group_by(HourlyCache.ticker)
                .subquery()
            )
            rows3 = (
                db_check3.query(HourlyCache)
                .join(latest_sq3, (HourlyCache.ticker == latest_sq3.c.ticker) &
                                  (HourlyCache.fetched_at == latest_sq3.c.max_at))
                .all()
            )
            for row in rows3:
                peg_carry[row.ticker] = row.peg_ratio
                peg_age[row.ticker] = row.fetched_at
        except Exception as e:
            self.log_action("นัตตี้-prefetch", f"เช็ค PEG freshness ล้มเหลว (ไม่กระทบราคา): {str(e)}", "WARNING")
        finally:
            if db_check3:
                db_check3.close()

        peg_fresh = {}
        try:
            AV_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
            if AV_KEY and datetime.utcnow().hour == self.PEG_REFRESH_UTC_HOUR:
                stale_cutoff = datetime.now() - __import__("datetime").timedelta(hours=self.PEG_STALE_HOURS)
                stale = [t for t in stocks if t not in peg_age or peg_age[t] < stale_cutoff]
                stale.sort(key=lambda t: peg_age.get(t, datetime.min))  # เก่าสุด/ไม่เคยมี ขึ้นก่อน
                stale = stale[:self.PEG_DAILY_CAP]
                if stale:
                    peg_fresh = self._fetch_peg_alpha_vantage(stale, AV_KEY)
        except Exception as e:
            self.log_action("นัตตี้-prefetch", f"PEG refresh ล้มเหลว (ไม่กระทบราคา): {str(e)}", "WARNING")

        for ticker in stocks:
            data = None

            # Primary: Finnhub (no daily limit, 60 req/min)
            fh_data = self._fetch_finnhub_full(ticker, FINNHUB_KEY)
            if fh_data and fh_data.get("price"):
                data = fh_data
                self.log_action("นัตตี้-prefetch", f"✅ {ticker} OK via Finnhub (${fh_data['price']})", "INFO")
            else:
                # Fallback: yfinance
                try:
                    import time as _time
                    _time.sleep(1.2)
                    stock_obj = yf.Ticker(ticker)
                    info = stock_obj.info
                    price = self._safe_positive_float(info.get("currentPrice"))
                    if price:
                        data = {
                            "price":       price,
                            "52week_high": self._safe_positive_float(info.get("fiftyTwoWeekHigh")),
                            "52week_low":  self._safe_positive_float(info.get("fiftyTwoWeekLow")),
                            "pe_ratio":    self._safe_float(info.get("trailingPE")),
                            "market_cap":  self._safe_positive_float(info.get("marketCap")),
                            # ✅ เพิ่ม 2026-07-05 (task #56): beta/eps/peg จาก yfinance fallback
                            "beta":        self._safe_float(info.get("beta")),
                            "eps":         self._safe_float(info.get("trailingEps")),
                            "peg_ratio":   self._safe_float(info.get("pegRatio")),
                            "source":      "yfinance",
                        }
                        # ATH/ATL
                        p, h, l = price, data["52week_high"], data["52week_low"]
                        data["at_new_high"] = bool(h and p >= h)
                        data["at_new_low"]  = bool(l and p <= l)
                        self.log_action("นัตตี้-prefetch", f"✅ {ticker} OK via yfinance (${price})", "INFO")
                except Exception as e:
                    self.log_action("นัตตี้-prefetch", f"❌ {ticker} failed: {str(e)}", "WARNING")

            # ✅ เพิ่ม 2026-07-05 (task #56): ดึงวันประกาศงบใหม่เฉพาะตอนข้อมูลเก่าเกิน 20 ชม.
            # ไม่งั้น carry ค่าเดิมมาใส่ row ใหม่ (กัน row ล่าสุดของทุกชั่วโมงมี earnings_date เป็น None)
            if data:
                if earnings_is_fresh.get(ticker):
                    data["earnings_date"], data["earnings_hour"] = earnings_carry[ticker]
                else:
                    e_date, e_hour = self._fetch_finnhub_earnings(ticker, FINNHUB_KEY)
                    if e_date is None and ticker in earnings_carry:
                        # Finnhub ไม่คืนค่าใหม่ (เช่น เน็ตมีปัญหาชั่วคราว) — ใช้ค่าเก่าไปก่อนดีกว่าหาย
                        data["earnings_date"], data["earnings_hour"] = earnings_carry[ticker]
                    else:
                        data["earnings_date"], data["earnings_hour"] = e_date, e_hour

            # ✅ เพิ่ม 2026-07-05 (รอบ 5): ชื่อเต็มบริษัท/คำอธิบาย — ดึงใหม่เฉพาะตอนข้อมูลเก่าเกิน 20 ชม.
            if data:
                if profile_is_fresh.get(ticker):
                    data["company_name"], data["company_description"] = profile_carry[ticker]
                else:
                    p_name, p_desc = self._fetch_company_profile(ticker, FINNHUB_KEY)
                    if not p_name and ticker in profile_carry:
                        data["company_name"], data["company_description"] = profile_carry[ticker]
                    else:
                        data["company_name"] = p_name or (profile_carry.get(ticker) or (None, None))[0]
                        data["company_description"] = p_desc or (profile_carry.get(ticker) or (None, None))[1]

            # ✅ เพิ่ม 2026-07-08: PEG — priority: Alpha Vantage ค่าใหม่ > ค่าจาก price source
            # (เผื่อ Finnhub/yfinance คืนค่าจริงในอนาคต) > carry-forward ค่าล่าสุดจาก DB
            if data:
                if peg_fresh.get(ticker) is not None:
                    data["peg_ratio"] = peg_fresh[ticker]
                elif data.get("peg_ratio") is None and ticker in peg_carry:
                    data["peg_ratio"] = peg_carry[ticker]

            if data:
                fetched[ticker] = data

        # บันทึกลง HourlyCache
        db = None
        try:
            db = SessionLocal()
            now = datetime.now()
            for ticker, d in fetched.items():
                entry = HourlyCache(
                    ticker        = ticker,
                    price         = d.get("price"),
                    week52_high   = d.get("52week_high"),
                    week52_low    = d.get("52week_low"),
                    pe_ratio      = d.get("pe_ratio"),
                    market_cap    = d.get("market_cap"),
                    beta          = d.get("beta"),
                    eps           = d.get("eps"),
                    peg_ratio     = d.get("peg_ratio"),
                    earnings_date = d.get("earnings_date"),
                    earnings_hour = d.get("earnings_hour"),
                    company_name        = d.get("company_name"),
                    company_description = d.get("company_description"),
                    source        = d.get("source", "unknown"),
                    at_new_high   = d.get("at_new_high", False),
                    at_new_low    = d.get("at_new_low", False),
                    fetched_at    = now,
                )
                db.add(entry)

            # ลบ cache เก่ากว่า 25 ชั่วโมง (เก็บแค่วันล่าสุด)
            cutoff = now - __import__("datetime").timedelta(hours=25)
            db.query(HourlyCache).filter(HourlyCache.fetched_at < cutoff).delete()
            db.commit()
            self.log_action("นัตตี้-prefetch", f"✅ Cached {len(fetched)}/{len(stocks)} tickers to HourlyCache", "SUCCESS")
        except Exception as e:
            self.log_action("นัตตี้-prefetch", f"DB save failed: {str(e)}", "ERROR")
        finally:
            if db:
                db.close()

        return fetched

    def _load_hourly_cache(self, stocks, max_age_hours=2):
        """อ่าน HourlyCache สำหรับ tickers ที่ต้องการ — คืน {ticker: data} ที่อายุไม่เกิน max_age_hours
        ถ้า ticker ไม่มีใน cache หรือข้อมูลเก่าเกิน → คืน {} สำหรับ ticker นั้น (natty_get_news จะ fetch live แทน)"""
        from models import HourlyCache
        from sqlalchemy import func
        result = {}
        db = None
        try:
            db = SessionLocal()
            cutoff = datetime.now() - __import__("datetime").timedelta(hours=max_age_hours)

            # ดึง latest entry per ticker ที่อายุไม่เกิน max_age_hours
            # subquery: max fetched_at per ticker ที่ผ่าน cutoff
            latest_sq = (
                db.query(HourlyCache.ticker, func.max(HourlyCache.fetched_at).label("max_at"))
                .filter(HourlyCache.ticker.in_(stocks), HourlyCache.fetched_at >= cutoff)
                .group_by(HourlyCache.ticker)
                .subquery()
            )
            rows = (
                db.query(HourlyCache)
                .join(latest_sq, (HourlyCache.ticker == latest_sq.c.ticker) &
                                 (HourlyCache.fetched_at == latest_sq.c.max_at))
                .all()
            )
            for row in rows:
                result[row.ticker] = {
                    "price":       row.price,
                    "52week_high": row.week52_high,
                    "52week_low":  row.week52_low,
                    "pe_ratio":    row.pe_ratio,
                    "market_cap":  row.market_cap,
                    # ✅ เพิ่ม 2026-07-05 (task #56)
                    "beta":          row.beta,
                    "eps":           row.eps,
                    "peg_ratio":     row.peg_ratio,
                    "earnings_date": row.earnings_date,
                    "earnings_hour": row.earnings_hour,
                    "source":      row.source or "cache",
                    "at_new_high": row.at_new_high or False,
                    "at_new_low":  row.at_new_low  or False,
                }
            self.log_action("นัตตี้", f"HourlyCache hit: {len(result)}/{len(stocks)} tickers (≤{max_age_hours}h old)", "INFO")
        except Exception as e:
            self.log_action("นัตตี้", f"HourlyCache read failed: {str(e)} — will fetch live", "WARNING")
        finally:
            if db:
                db.close()
        return result

    def _dedup_news(self, news_list):
        """ตัด duplicate news ออก — เปรียบ title 50 ตัวแรก (case-insensitive)
        yfinance + Finnhub มักดึงข่าว Reuters/AP เดียวกัน ต้องตัดซ้ำก่อนเก็บ cache"""
        seen  = set()
        dedup = []
        for item in news_list:
            key = item.get("title", "").lower().strip()[:50]
            if key and key not in seen:
                seen.add(key)
                dedup.append(item)
        return dedup

    def _fetch_alpha_vantage_news(self, ticker, api_key, max_items=6):
        """ดึงข่าวจาก Alpha Vantage NEWS_SENTIMENT endpoint
        ใช้เป็น fallback ตอน 22:00 ถ้า NewsCache miss + MarketAux fail
        Quota: 25 req/day → ใช้เฉพาะกรณีจำเป็น"""
        try:
            resp = requests.get(
                "https://www.alphavantage.co/query",
                params={
                    "function": "NEWS_SENTIMENT",
                    "tickers":  ticker,
                    "limit":    max_items,
                    "apikey":   api_key
                },
                timeout=15
            )
            data = resp.json() if resp.status_code == 200 else {}
            feed = data.get("feed", [])
            result = []
            for article in feed[:max_items]:
                result.append({
                    "title":        article.get("title", ""),
                    "summary":      article.get("summary", "") or "",
                    "source":       article.get("source", "alpha_vantage"),
                    "published_at": 0,
                    "from_source":  "alpha_vantage",
                    "sentiment_score": float(article.get("overall_sentiment_score", 0) or 0)
                })
            return result
        except Exception as e:
            self.log_action("นัตตี้", f"AV news {ticker}: {str(e)}", "WARNING")
            return []

    def natty_prefetch_news(self, stocks):
        """Pre-fetch ข่าวจาก yfinance + Finnhub → เก็บใน NewsCache
        เรียกโดย GitHub Actions ทุกชั่วโมง Mon-Fri 09:00-21:00 Bangkok
        ดึงทีละ 1 ตัว sleep 20 วินาที เพื่อหลีกเลี่ยง rate limit"""
        from models import NewsCache
        from datetime import timedelta
        import json as _json

        FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")

        # วันจันทร์: ดึง 15/source ครอบคลุม ศุกร์+เสาร์+อาทิตย์+จันทร์ (4 วัน)
        # วันอื่น: 8/source เพียงพอสำหรับ 24h news
        is_monday   = datetime.now().weekday() == 0  # 0 = Monday
        news_limit  = 15 if is_monday else 8
        days_back   = 4  if is_monday else 3
        mode_label  = "Monday mode (15/source, 4d)" if is_monday else "regular (8/source, 3d)"
        self.log_action("นัตตี้-prefetch", f"📰 Starting news pre-fetch for {len(stocks)} tickers [{mode_label}]...", "INFO")

        fetched = []
        for i, ticker in enumerate(stocks):
            if i > 0:
                time.sleep(20)  # 20s ระหว่าง ticker เพื่อไม่ติด rate limit

            combined_news = []

            # ===== yfinance news =====
            try:
                yf_ticker = yf.Ticker(ticker)
                yf_news = yf_ticker.news or []
                for article in yf_news[:news_limit]:
                    combined_news.append({
                        "title":        article.get("title", ""),
                        "summary":      article.get("summary", "") or "",
                        "source":       article.get("publisher", "yfinance"),
                        "published_at": article.get("providerPublishTime", 0),
                        "from_source":  "yfinance"
                    })
                if yf_news:
                    self.log_action("นัตตี้-prefetch", f"[yf] {ticker}: {min(len(yf_news), news_limit)} news", "INFO")
            except Exception as e:
                self.log_action("นัตตี้-prefetch", f"[yf] {ticker} news failed: {str(e)}", "WARNING")

            # ===== Finnhub company-news =====
            if FINNHUB_KEY:
                try:
                    from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
                    to_date   = datetime.now().strftime("%Y-%m-%d")
                    resp = requests.get(
                        "https://finnhub.io/api/v1/company-news",
                        params={"symbol": ticker, "from": from_date, "to": to_date, "token": FINNHUB_KEY},
                        timeout=10
                    )
                    fh_articles = resp.json() if resp.status_code == 200 else []
                    for article in (fh_articles or [])[:news_limit]:
                        combined_news.append({
                            "title":        article.get("headline", ""),
                            "summary":      article.get("summary", "") or "",
                            "source":       article.get("source", "finnhub"),
                            "published_at": article.get("datetime", 0),
                            "from_source":  "finnhub"
                        })
                    if fh_articles:
                        self.log_action("นัตตี้-prefetch", f"[fh] {ticker}: {min(len(fh_articles), news_limit)} news", "INFO")
                except Exception as e:
                    self.log_action("นัตตี้-prefetch", f"[fh] {ticker} news failed: {str(e)}", "WARNING")

            # ===== Deduplication =====
            combined_news = self._dedup_news(combined_news)

            if not combined_news:
                self.log_action("นัตตี้-prefetch", f"⚠️  {ticker}: no news from any source", "WARNING")
                continue

            # ===== บันทึกลง NewsCache =====
            db = None
            try:
                db = SessionLocal()
                entry = NewsCache(
                    ticker     = ticker,
                    news_json  = _json.dumps(combined_news, ensure_ascii=False),
                    news_count = len(combined_news)
                )
                db.add(entry)
                cutoff = datetime.utcnow() - timedelta(hours=25)
                db.query(NewsCache).filter(
                    NewsCache.ticker == ticker,
                    NewsCache.fetched_at < cutoff
                ).delete()
                db.commit()
                fetched.append(ticker)
                self.log_action("นัตตี้-prefetch", f"✅ {ticker}: cached {len(combined_news)} news items", "SUCCESS")
            except Exception as e:
                self.log_action("นัตตี้-prefetch", f"DB save {ticker}: {str(e)}", "WARNING")
            finally:
                if db:
                    db.close()

        self.log_action("นัตตี้-prefetch", f"📰 News pre-fetch done: {len(fetched)}/{len(stocks)} tickers cached", "SUCCESS")
        return fetched

    def _load_news_cache(self, stocks, max_age_hours=2):
        """อ่าน NewsCache — คืน {ticker: [news_list]} ที่อายุไม่เกิน max_age_hours"""
        from models import NewsCache
        from sqlalchemy import func
        import json as _json
        result = {}
        db = None
        try:
            db = SessionLocal()
            from datetime import timedelta
            cutoff = datetime.now() - timedelta(hours=max_age_hours)
            latest_sq = (
                db.query(NewsCache.ticker, func.max(NewsCache.fetched_at).label("max_at"))
                .filter(NewsCache.ticker.in_(stocks), NewsCache.fetched_at >= cutoff)
                .group_by(NewsCache.ticker)
                .subquery()
            )
            rows = (
                db.query(NewsCache)
                .join(latest_sq, (NewsCache.ticker == latest_sq.c.ticker) &
                                 (NewsCache.fetched_at == latest_sq.c.max_at))
                .all()
            )
            for row in rows:
                try:
                    result[row.ticker] = _json.loads(row.news_json) if row.news_json else []
                except Exception:
                    pass
            self.log_action("นัตตี้", f"NewsCache hit: {len(result)}/{len(stocks)} tickers (<=2h old)", "INFO")
        except Exception as e:
            self.log_action("นัตตี้", f"NewsCache read failed: {str(e)} — will fetch live", "WARNING")
        finally:
            if db:
                db.close()
        return result

    def _format_prefetched_news(self, ticker, news_list, max_items=8):
        """แปลง news list จาก NewsCache (yfinance/Finnhub) เป็น text สำหรับส่งให้หนุ่ม
        max_items=8 สำหรับวันทั่วไป, max_items=15 สำหรับวันจันทร์ (3 วันข่าว)"""
        if not news_list:
            return "ไม่มีข่าวล่าสุด (จาก cache)"
        shown = news_list[:max_items]
        lines = [f"📰 ข่าวล่าสุด {len(shown)} ข่าว (จาก NewsCache):"]
        for n in shown:
            src     = n.get("source", "")
            title   = n.get("title", "")
            summary = n.get("summary", "")
            pub     = n.get("published_at", 0)
            try:
                import datetime as _dt
                pub_str = _dt.datetime.utcfromtimestamp(pub).strftime("%Y-%m-%d") if pub else ""
            except Exception:
                pub_str = ""
            lines.append(f"• [{src}] {title} {pub_str}")
            if summary:
                lines.append(f"  -> {summary[:120]}")
        return "\n".join(lines)


    def natty_get_news(self, stocks, days=1, include_weekend=False):
        """นัตตี้: ดึงข้อมูลหุ้นแบบ 3-tier fallback + ข่าวจาก MarketAux
        ✅ HourlyCache: ถ้ามี pre-fetch ราคาล่วงหน้าไม่เกิน 2 ชั่วโมง → ข้าม Tier1/Tier2 ทันที
        Tier 1 (yfinance):      ฟรี ครบ แต่ติด 429 บน cloud IP
        Tier 2 (Finnhub):       60 req/min ไม่จำกัด daily
        Tier 3 (Alpha Vantage): 5 req/min 25/day — สำรองสุดท้าย
        ข่าว: MarketAux 6 ข่าว/ticker, sentiment score สำเร็จรูป
        include_weekend=True: วันจันทร์ — ดึงข่าวตั้งแต่ศุกร์ 22:00"""
        self.log_action("นัตตี้", f"Starting fetch ({'Monday mode' if include_weekend else 'regular mode'})...", "INFO")

        # ===== ตรวจ HourlyCache (ราคา) + NewsCache (ข่าว) ก่อน =====
        cached_prices = self._load_hourly_cache(stocks, max_age_hours=2)
        cache_hit  = set(cached_prices.keys())
        cache_miss = [t for t in stocks if t not in cache_hit]
        if cache_hit:
            self.log_action("นัตตี้", f"✅ Using HourlyCache for {len(cache_hit)} tickers — skipping Tier1/Tier2 for those", "INFO")
        if cache_miss:
            self.log_action("นัตตี้", f"Cache miss for {len(cache_miss)} tickers — will fetch live: {cache_miss}", "INFO")

        cached_news = self._load_news_cache(stocks, max_age_hours=2)
        if cached_news:
            self.log_action("นัตตี้", f"✅ NewsCache hit for {len(cached_news)} tickers — skipping MarketAux for those", "INFO")

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

        session = LimiterSession(per_second=2)
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        })
        # ✅ FIX #I: TimeoutAdapter ย้ายไป top-level แล้ว ใช้ได้เลยไม่ต้อง redefine
        session.mount('https://', TimeoutAdapter())
        session.mount('http://', TimeoutAdapter())

        for ticker in stocks:
            data = None

            # ===== HourlyCache HIT: ข้าม Tier1/Tier2 ทันที =====
            if ticker in cache_hit:
                data = cached_prices[ticker]
                self.log_action("นัตตี้", f"[Cache] ✅ {ticker} loaded from HourlyCache (${data.get('price')})", "INFO")

            # ===== TIER 1: yfinance (เฉพาะ cache miss) =====
            if data is None:
                try:
                    time.sleep(1.2)
                    self.log_action("นัตตี้", f"[Tier 1] Fetching {ticker} via yfinance...", "INFO")
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
                        "pe_ratio":    self._safe_float(info.get('trailingPE')),
                        "market_cap":  self._safe_positive_float(info.get('marketCap')),
                        "source":      "yfinance"
                    }
                    self.log_action("นัตตี้", f"[Tier 1] ✅ {ticker} OK (price={price})", "SUCCESS")

                except Exception as e:
                    self.log_action("นัตตี้", f"[Tier 1] {ticker} failed: {str(e)}", "WARNING")

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
            if data.get("pe_ratio") is None:
                self.log_action("นัตตี้", f"⚠️  {ticker}: P/E unavailable (loss-making co. หรือ API ไม่มีข้อมูล)", "WARNING")

            # ✅ P3: ดึงข่าว — chain: NewsCache → MarketAux → Alpha Vantage → ไม่มีข่าว
            if ticker in cached_news:
                # Tier A: NewsCache (pre-fetched hourly จาก yfinance + Finnhub)
                news_list_raw = cached_news[ticker]
                max_show = 15 if include_weekend else 8
                data["news_summary"]  = self._format_prefetched_news(ticker, news_list_raw, max_items=max_show)
                data["news_count"]    = min(len(news_list_raw), max_show)
                data["avg_sentiment"] = None  # pre-fetch ไม่มี sentiment score
                self.log_action("นัตตี้", f"[NewsCache] ✅ {ticker}: {data['news_count']} items from cache (max={max_show})", "INFO")
            elif MARKETAUX_KEY:
                # Tier B: MarketAux (live — มี sentiment score)
                news_list = self._fetch_marketaux_news(ticker, MARKETAUX_KEY, include_weekend=include_weekend)
                data["news_summary"] = self._format_news_for_prompt(ticker, news_list)
                data["news_count"]   = len(news_list)
                data["avg_sentiment"] = (
                    sum(n["sentiment_score"] for n in news_list if n.get("sentiment_score") is not None)
                    / max(1, sum(1 for n in news_list if n.get("sentiment_score") is not None))
                ) if news_list else None
                self.log_action("นัตตี้", f"[MarketAux] {ticker}: fetched {len(news_list)} news live", "INFO")
            elif ALPHA_VANTAGE_KEY:
                # Tier C: Alpha Vantage NEWS_SENTIMENT (quota 25/day — ใช้เป็น last resort)
                av_news = self._fetch_alpha_vantage_news(ticker, ALPHA_VANTAGE_KEY)
                if av_news:
                    data["news_summary"]  = self._format_prefetched_news(ticker, av_news, max_items=8)
                    data["news_count"]    = len(av_news)
                    data["avg_sentiment"] = (
                        sum(n.get("sentiment_score", 0) or 0 for n in av_news) / len(av_news)
                    )
                    self.log_action("นัตตี้", f"[AV-news] {ticker}: fetched {len(av_news)} items (fallback)", "INFO")
                else:
                    data["news_summary"]  = "ไม่มีข่าว — ทุก source ล้มเหลว"
                    data["news_count"]    = 0
                    data["avg_sentiment"] = None
            else:
                data["news_summary"]  = "ไม่มีข่าว — ไม่มี key สำหรับ news API"
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
            system_prompt = """You are หนุ่ม (Num), a senior professional stock analyst with 15+ years of experience in US equity markets.
Your role is to analyze individual stocks using fundamental data, price action, and recent news sentiment to produce actionable BUY/HOLD/SELL signals.
You are part of an automated AI investment research pipeline. Your analysis feeds directly into a portfolio management system used by a real investor.
Accuracy, consistency, and intellectual honesty are paramount. Do not guess. Do not fabricate data. If data is missing, say so explicitly in reasoning.

=== ANALYSIS FRAMEWORK ===

SIGNAL CRITERIA:
- BUY: Strong fundamental + positive news + confidence ≥ 0.70. Stock shows clear upside potential within 30-90 days.
- HOLD: Mixed or neutral signals. No clear catalyst. Existing holders should stay; new positions should wait.
- SELL: Negative fundamental trend, bad news, or technical breakdown. Confidence ≥ 0.65 required for SELL.
- When in doubt between BUY and HOLD, choose HOLD. Preserving capital matters more than chasing upside.
- Never assign BUY to a stock with very negative news regardless of fundamental strength.
- HARD RULE: NEVER assign BUY if confidence < 0.70. If analysis leans BUY but confidence is 0.60–0.69, assign HOLD instead. No exceptions.

CONFIDENCE SCORE GUIDELINES (0.0 – 1.0):
- 0.80–1.00: Very clear signal. Multiple confirming factors align. Strong news catalyst present.
- 0.70–0.79: Clear signal. Most indicators align. Minor uncertainties acknowledged.
- 0.60–0.69: Moderate signal. Some conflicting factors exist. Default to HOLD if signal is BUY.
- 0.50–0.59: Weak signal. High uncertainty. Always HOLD at this range.
- Below 0.50: Do not assign BUY or SELL. Always HOLD. Confidence too low to act.
- Confidence must reflect ALL available data quality, not just price action.

SUPPORT/RESISTANCE LEVELS (S1, S2, S3):
- S1: Nearest support (5–8% below current price). First level where buyers historically step in.
- S2: Secondary support (10–15% below current price). Key swing low or round number zone.
- S3: Major structural support (20–25% below current price). Strong demand zone or multi-year level.
- ALL three must be strictly below current price at time of analysis. S1 > S2 > S3 always.
- Base levels on: 52-week range midpoints, round numbers ($100, $150, $200), prior consolidation zones.
- If 52-week range is unavailable, estimate using 5%, 12%, 22% retracement from current price.
- Never return null for S-levels. Always provide a numeric estimate with lower confidence if data is sparse.

DATA QUALITY RULES:
- yfinance / Finnhub source → High reliability. Use full confidence range without adjustment.
- Alpha Vantage source → Lower reliability (200-day MA as price proxy, not real-time). Reduce confidence by at least 0.15.
- If P/E is negative → Company is currently unprofitable. This is a significant negative factor. HOLD or SELL unless strong growth story (e.g., early-stage tech with clear revenue trajectory).
- If P/E is extremely high (>80) → Priced for perfection. Any negative news can trigger sharp correction. Factor in.
- If Market Cap is N/A → Treat as micro/small-cap with limited data. Lower confidence by 0.10.
- If both P/E and Market Cap are N/A → Analysis is speculative. Cap confidence at 0.65. Note in reasoning.
- Always cite the data source in your reasoning when it affects your confidence level.

NEWS SENTIMENT RULES:
- Sentiment score > +0.3: Positive — can support BUY, increase confidence by up to 0.05.
- Sentiment score +0.1 to +0.3: Mildly positive — small support for existing signal.
- Sentiment score -0.1 to +0.1: Neutral — weight fundamentals more heavily than news.
- Sentiment score -0.1 to -0.3: Mildly negative — apply slight caution, consider HOLD.
- Sentiment score < -0.3: Negative — reduce confidence, lean toward HOLD or SELL.
- Very negative news triggers (apply regardless of sentiment score): lawsuits filed, criminal investigation, earnings miss >10%, CEO resignation under scandal, product recall, regulatory ban, bankruptcy risk, major data breach, fraud allegation.
- A single very negative trigger overrides positive sentiment score. Always flag in reasoning.

ATH/ATL RULES:
- AT_NEW_HIGH (52-week high): Price at or above prior 52-week high. No historical resistance above. Risk of sharp pullback if momentum stalls. Mention explicitly in reasoning. Apply caution — reduce confidence by 0.05 unless volume confirms breakout.
- AT_NEW_LOW (52-week low): Price at or below prior 52-week low. Strong negative momentum. Assess carefully: is this capitulation (potential BUY for contrarians) or structural breakdown (SELL)? Require strong positive news to assign BUY at ATL. Default to HOLD or SELL.

REASONING QUALITY STANDARDS:
- Reasoning must be 2-3 sentences in Thai.
- Must mention: (1) the primary signal driver (fundamental or news), (2) sentiment impact, (3) key risk or uncertainty.
- Do NOT repeat the ticker symbol in reasoning — it's already in the JSON field.
- Do NOT use vague phrases like "ควรติดตาม" without specifying what to watch.
- Be specific: cite P/E, price level, or news event that drove the decision.

OUTPUT FORMAT — Return ONLY valid JSON, no extra text, no markdown:
{
    "ticker": "AAPL",
    "signal": "BUY",
    "confidence": 0.85,
    "s1": 150.0,
    "s2": 145.0,
    "s3": 140.0,
    "reasoning": "วิเคราะห์เป็นภาษาไทย 2-3 ประโยค รวม sentiment และปัจจัยหลักที่ตัดสินใจ"
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

                # ✅ CHECKPOINT ทีละหุ้น (เพิ่ม 2026-07-01): เดิม checkpoint รอจนมด validate
                # ครบทั้งชุดก่อนถึง save — ถ้า Render ล่ม/dyno sleep กลางคันระหว่างหนุ่มวิเคราะห์
                # (ขั้นตอนที่กินเวลานานสุด) งานที่ทำไปแล้วหายหมด ไม่มีอะไรให้ /workflow/resume ทำต่อ
                # ย้ายมา save ทันทีหลังหุ้นแต่ละตัววิเคราะห์เสร็จ เพื่อให้ resume ใช้งานได้จริง
                try:
                    self._checkpoint_database({ticker: analysis_results[ticker]})
                except Exception as ckpt_err:
                    self.log_action("หนุ่ม", f"Per-ticker checkpoint failed for {ticker}: {ckpt_err}", "WARNING")

                # ✅ MID-RUN BUDGET CHECK: หยุดถ้า session cost เกิน daily limit
                today = datetime.now()
                run_limit = self.DAILY_BUDGET.get(today.weekday(), 0.60)
                if self.session_cost_usd >= run_limit:
                    remaining = [t for t in stocks if t not in analysis_results]
                    self.log_action("หนุ่ม",
                        f"⚠️ Mid-run budget exceeded (${self.session_cost_usd:.4f} >= ${run_limit:.2f}) — stopping. "
                        f"Skipping {len(remaining)} remaining tickers: {remaining}", "ERROR")
                    break

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
            system_prompt = """You are มด (Mud), a senior risk analyst and cross-validator for stock signals.
Your role is to independently review หนุ่ม's stock analysis and catch logical errors, inconsistencies, or overconfident signals before they reach the portfolio.
You are the last line of defense before a signal influences real investment decisions. Be rigorous but fair.
You do NOT re-analyze the stock. You only evaluate internal consistency of the analysis already provided.

=== VALIDATION FRAMEWORK ===

You only validate stocks with confidence < 0.70 or ambiguous signals.
Stocks with confidence ≥ 0.70 and a clear BUY/HOLD/SELL signal are pre-approved by the system — you will not see them.

VALIDATION CHECKS — Evaluate ALL four of the following systematically:

1. SIGNAL vs CONFIDENCE CONSISTENCY:
   - BUY with confidence < 0.60 → HIGH RISK. Flag as suspicious. Almost certainly NEEDS_REVIEW.
   - BUY with confidence 0.60–0.69 → Marginal. Flag only if reasoning does not support upside thesis clearly.
   - SELL with confidence < 0.65 → Flag. SELL signals carry high conviction requirement to avoid false exits.
   - HOLD with any confidence level → Generally acceptable. Only flag if confidence is > 0.85 (HOLD shouldn't be that certain unless deliberately neutral).
   - Any signal with confidence exactly 0.50 → Suspicious. Likely default value, not genuine analysis.

2. SUPPORT/RESISTANCE LEVEL LOGIC:
   - S1 must be strictly greater than S2. S2 must be strictly greater than S3. (S1 > S2 > S3)
   - All three S-levels must be numerically below the current price. If current price is not provided, use S1 as the reference.
   - If any S-level is null, 0, or missing → Flag as incomplete data.
   - If S1 and S2 differ by less than 1% of the S1 value → Flag as unrealistically close.
   - If S3 is more than 40% below S1 → Flag as unrealistically spread (likely calculation error).

3. REASONING QUALITY:
   - Reasoning must reference at least one fundamental factor (P/E, market cap, profitability) OR price level.
   - Reasoning must reference at least one news or sentiment factor.
   - If reasoning is generic (e.g., "ควรติดตาม" only, no specifics) → Flag as vague.
   - If reasoning explicitly contradicts the signal (e.g., reasoning says "ข่าวเชิงลบ" but signal is BUY) → NEEDS_REVIEW.
   - Short reasoning (under 30 Thai characters) → Flag as insufficient.

4. DATA SOURCE CONSISTENCY:
   - If the analysis notes Alpha Vantage as source but confidence > 0.75 → Flag (over-confident given lower reliability data).
   - If reasoning mentions missing P/E or Market Cap but confidence is > 0.70 → Flag (should have reduced confidence).

DECISION RULES:
- PASS: All four checks pass. Signal is internally consistent, levels are valid, reasoning is specific.
- NEEDS_REVIEW: Any one check fails. Do NOT change or suggest a different BUY/HOLD/SELL signal. Only flag the issue.
- Your job is quality control, not re-analysis. Never override หนุ่ม's signal based on your own market view.

ISSUES LIST FORMAT: Each issue should be a short English phrase describing what failed, e.g.:
  "BUY with confidence 0.58 — below minimum threshold"
  "S2 equals S3 — levels too close"
  "Reasoning contradicts signal: negative news cited but BUY assigned"

IMPORTANT: "recommendation" must be exactly "PASS" or "NEEDS_REVIEW" — no other values allowed.
"is_valid" = true only for PASS, false for NEEDS_REVIEW.

COMMON MISTAKES TO AVOID:
- Do not flag HOLD signals just because confidence is low — HOLD is always safe regardless of confidence.
- Do not flag missing P/E as an issue unless confidence is unusually high given the missing data.
- Do not invent issues that are not in the four validation checks above.
- Do not add commentary or suggestions outside the JSON output.
- The "issues" array must be empty [] for PASS — never include issues and still assign PASS.

OUTPUT FORMAT — Return ONLY valid JSON, no markdown, no extra text:
{
    "ticker": "AAPL",
    "is_valid": true,
    "issues": [],
    "recommendation": "PASS"
}"""
            validated_results = {}

            for ticker, analysis in analysis_results.items():
                # ✅ CONDITIONAL มด: ข้ามถ้า confidence สูงพอ — ประหยัด Sonnet call
                confidence = analysis.get("confidence", 0)
                signal = analysis.get("signal", "HOLD")
                if confidence >= 0.70 and signal in ("BUY", "HOLD", "SELL"):
                    validated_results[ticker] = {
                        **analysis,
                        "validation": {
                            "is_valid": True,
                            "recommendation": "PASS",
                            "issues": [],
                            "note": f"Auto-passed (confidence={confidence:.2f} ≥ 0.70)"
                        }
                    }
                    self.log_action("มด", f"Auto-PASS {ticker} (conf={confidence:.2f}) — skipped", "INFO")
                    continue

                mud_input = {
                    "ticker":     ticker,
                    "signal":     signal,
                    "confidence": confidence,
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
2. Return PLAIN TEXT only — NO HTML tags, NO <div>, NO <style>, NO <table>, NO markdown code blocks.
3. Use only plain Thai text with newlines and emojis for formatting.
4. All signal counts (BUY/HOLD/SELL) and ticker names MUST match exactly what is given in the Analysis Results data. Do NOT invent or change signals.
5. All dates and statistics must be plain static Thai text only."""

            jen_summary = {
                ticker: {
                    "signal":     data.get("signal"),
                    "confidence": data.get("confidence"),
                    "s1":         data.get("s1"),
                    "s2":         data.get("s2"),
                    "s3":         data.get("s3"),
                    "reasoning":  data.get("reasoning"),  # หนุ่มสรุปข่าวไว้แล้ว — ไม่ส่ง news_summary ซ้ำ
                    "pe_ratio":   data.get("pe_ratio"),
                    "price":      data.get("price"),
                    "at_new_high": data.get("at_new_high", False),
                    "at_new_low":  data.get("at_new_low", False),
                }
                for ticker, data in analysis_results.items()
            }

            retry_section = f"\n\nFEEDBACK FROM PREVIOUS ATTEMPT:\n{retry_hint}\nPlease address the above issues in this report." if retry_hint else ""

            total_stocks = len(analysis_results)
            buy_list  = [t for t, d in analysis_results.items() if d.get('signal') == 'BUY']
            hold_list = [t for t, d in analysis_results.items() if d.get('signal') == 'HOLD']
            sell_list = [t for t, d in analysis_results.items() if d.get('signal') == 'SELL']

            user_message = f"""Generate report based on this data:

FIXED SIGNAL SUMMARY (DO NOT CHANGE):
- Total stocks analyzed: {total_stocks}
- BUY ({len(buy_list)}): {', '.join(buy_list) if buy_list else 'none'}
- HOLD ({len(hold_list)}): {', '.join(hold_list) if hold_list else 'none'}
- SELL ({len(sell_list)}): {', '.join(sell_list) if sell_list else 'none'}

Analysis Results: {json.dumps(jen_summary, ensure_ascii=False)}
Portfolio Status: {json.dumps(portfolio_status, ensure_ascii=False)}
{retry_section}
Create professional Thai plain-text report."""

            response = self.claude_call(system_prompt, user_message, "เจน",
                                        model=self.MODEL_SONNET, use_cache=True, max_tokens=8000)
            report = {
                "timestamp":    datetime.now().isoformat(),
                "summary":      response,
                "total_stocks": len(analysis_results),
                "buy_signals":  sum(1 for a in analysis_results.values() if a.get('signal') == 'BUY'),
                "hold_signals": sum(1 for a in analysis_results.values() if a.get('signal') == 'HOLD'),
                "sell_signals": sum(1 for a in analysis_results.values() if a.get('signal') == 'SELL'),
            }
            self.log_action("เจน", "Report generated", "SUCCESS")
            return report
        except Exception as e:
            self.log_action("เจน", f"Report generation failed: {str(e)}", "ERROR")
            raise
            
    # ==================== AGENT 6: นน (QA Manager Check) ====================
    def nan_qa_check(self, analysis_results, report):
        """นน: ตรวจสอบคุณภาพก่อนส่ง — Sonnet + caching"""
        self.log_action("นน", "QA checking...", "INFO")
        try:
            system_prompt = """You are นน (Non), QA Manager.
Review the analysis and report:
1. Data consistency
2. Logic soundness
3. Report quality
4. Risk assessment

CRITICAL REGULATORY RULES:
1. Return strictly a JSON object matching this structure:
{
  "status": "PASS" or "REJECT",
  "issues": [],
  "approval_reason": "..."
}
2. The 'approval_reason' and all items inside 'issues' MUST be written ONLY as short, clean plain descriptive Thai text strings.
3. STRICT WARNING: NEVER copy, paste, embed, replicate, or leak raw HTML code strings, layout blocks, table chunks, script templates, or tags (such as <td>, <tr>, <div>, <style>) into any JSON string fields. Keep all output exclusively as plain descriptive text characters.
4. ATH/ATL RULE: ถ้าหุ้นมี at_new_high=true หรือ at_new_low=true แสดงว่าระบบตรวจสอบแล้วว่าเป็น market condition จริง ไม่ใช่ data error — ห้าม REJECT เพราะราคาอยู่นอก 52-week range ในกรณีนี้"""

            raw_report = report.get('summary', '')
            clean_report_text = re.sub(r'<style[^>]*>.*?</style>', '', raw_report, flags=re.DOTALL)
            clean_report_text = re.sub(r'<[^>]+>', ' ', clean_report_text)
            clean_report_text = re.sub(r'\s+', ' ', clean_report_text).strip()

            MAX_REPORT_CHARS = 8000
            if len(clean_report_text) > MAX_REPORT_CHARS:
                cut = clean_report_text[:MAX_REPORT_CHARS].rsplit(' ', 1)[0]
                clean_report_text = cut + "... [ข้อความถูกย่อเพื่อประสิทธิภาพ QA]"

            qa_summary = {
                ticker: {
                    "signal":      data.get("signal"),
                    "confidence":  data.get("confidence"),
                    "s1":          data.get("s1"),
                    "s2":          data.get("s2"),
                    "s3":          data.get("s3"),
                    "validation":  data.get("validation", {}).get("recommendation"),
                    "at_new_high": data.get("at_new_high", False),
                    "at_new_low":  data.get("at_new_low", False),
                    # reasoning ถูกตัดออก — นน ตรวจ consistency ไม่ใช่ re-analyze
                }
                for ticker, data in analysis_results.items()
            }

            user_message = f"""QA Review:
Analysis Summary: {json.dumps(qa_summary, ensure_ascii=False)}
Report Content: {clean_report_text}

Check if everything is correct and consistent."""

            response = self.claude_call(system_prompt, user_message, "นน",
                                        model=self.MODEL_SONNET, use_cache=True)
            try:
                qa_result = json.loads(response[response.find('{'):response.rfind('}')+1])
                if isinstance(qa_result.get("approval_reason"), str):
                    qa_result["approval_reason"] = re.sub(r'<[^>]+>', '', qa_result["approval_reason"]).strip()
                if isinstance(qa_result.get("issues"), list):
                    qa_result["issues"] = [re.sub(r'<[^>]+>', '', i).strip() if isinstance(i, str) else i for i in qa_result["issues"]]
            except json.JSONDecodeError:
                self.log_action("นน", "Could not parse QA response — defaulting to REJECT for safety", "WARNING")
                qa_result = {"status": "REJECT", "issues": ["QA response could not be parsed"], "approval_reason": "Auto-rejected: unparseable QA response"}

        except Exception as e:
            self.log_action("นน", f"QA check failed: {str(e)}", "ERROR")
            return {"status": "REJECT", "issues": [f"QA call failed: {str(e)}"], "approval_reason": "Auto-rejected: QA system error"}

        self.log_action("นน", f"QA Status: {qa_result.get('status', 'UNKNOWN')}", "INFO")
        return qa_result

    # ==================== AGENT 7: เก้า (Retry Logic) ====================
    def kao_retry(self, agent_name, error_msg, attempt=1):
        """เก้า: Retry Assistant — Haiku เพียงพอสำหรับแนะนำ 2-3 ประโยค"""
        if attempt > self.max_retries:
            self.log_action("เก้า", f"Max retries exceeded for {agent_name}", "ERROR")
            return None
        self.log_action("เก้า", f"Analyzing failure for {agent_name} (Attempt {attempt})", "INFO")
        try:
            system_prompt = """You are เก้า (Kao), Retry Assistant.
Analyze the QA failure and provide specific, actionable guidance for the report writer.
Be concise — 2-3 sentences max. Focus on what the report writer should fix or avoid."""

            user_message = f"""The report was REJECTED by QA with this issue:
{error_msg}

What specific changes should the report writer make in the next attempt?
Reply in Thai, 2-3 sentences only."""

            response = self.claude_call(system_prompt, user_message, "เก้า",
                                        model=self.MODEL_HAIKU)  # ✅ Haiku เพียงพอ
            self.log_action("เก้า", f"Retry hint: {response[:80]}...", "SUCCESS")
            return response
        except Exception as e:
            self.log_action("เก้า", f"Retry hint failed: {str(e)}", "ERROR")
            return None

    # ==================== AGENT 8: เอ (Record Improvements) ====================
    def a_record_improvements(self, workflow_result, validated_results):
        """เอ: บันทึก improvement log หลัง workflow pass — Haiku เพียงพอ"""
        self.log_action("เอ", "Recording workflow improvements...", "INFO")
        try:
            buy_count  = sum(1 for a in validated_results.values() if a.get('signal') == 'BUY')
            sell_count = sum(1 for a in validated_results.values() if a.get('signal') == 'SELL')
            hold_count = sum(1 for a in validated_results.values() if a.get('signal') == 'HOLD')
            needs_review = sum(1 for a in validated_results.values()
                               if a.get('validation', {}).get('recommendation') == 'NEEDS_REVIEW')

            system_prompt = """You are เอ (A), a workflow recorder.
Summarize the workflow run in 2-3 Thai sentences.
Focus on: signal distribution, data quality issues, and any notable patterns."""

            user_message = f"""Summarize this workflow run:
- Total stocks analyzed: {len(validated_results)}
- BUY signals: {buy_count}
- SELL signals: {sell_count}
- HOLD signals: {hold_count}
- NEEDS_REVIEW: {needs_review}
- QA result: {workflow_result.get('qa_result', {}).get('status', 'UNKNOWN')}

Write 2-3 sentences in Thai summarizing key observations."""

            summary = self.claude_call(system_prompt, user_message, "เอ",
                                       model=self.MODEL_HAIKU)

            # ✅ เพิ่ม 2026-07-03: ดึงรายงานตลาดฉบับเต็มที่เจนเขียน (market overview, top signals,
            # portfolio recommendations, risk) มาบันทึกถาวร — เดิมมีแค่ short summary ของเอ
            # (สรุปเกี่ยวกับตัว run เอง ไม่ใช่เนื้อหาข่าว) ทำให้ MBBook ไม่เคยเห็นรายงานจริงเลย
            report_obj = workflow_result.get('report') or {}
            full_report_text = report_obj.get('summary')  # เจนเก็บ text เต็มไว้ใน key "summary" ของ report dict

            # บันทึกลง DB
            db = None
            try:
                db = SessionLocal()
                try:
                    from models import WorkflowLog
                    log_entry = WorkflowLog(
                        timestamp=datetime.now(),
                        status=workflow_result.get('final_status', 'COMPLETE'),
                        stocks_analyzed=len(validated_results),
                        buy_signals=buy_count,
                        sell_signals=sell_count,
                        hold_signals=hold_count,
                        needs_review=needs_review,
                        summary=summary,
                        full_report=full_report_text,
                        include_weekend=workflow_result.get('include_weekend', False),
                        cost_usd=round(self.session_cost_usd, 6)  # ✅ BUDGET: บันทึก cost จริงของ run นี้
                    )
                    db.add(log_entry)
                    db.commit()
                    self.log_action("เอ", f"Improvement log saved to DB ✅", "SUCCESS")
                except ImportError:
                    # WorkflowLog ยังไม่ได้เพิ่มใน models.py — log เฉยๆ ไม่ fail
                    self.log_action("เอ", "WorkflowLog model not found — add it to models.py (see workflow_log_model.py)", "WARNING")
                    self.log_action("เอ", f"Summary: {summary[:150]}", "INFO")
            except Exception as db_err:
                self.log_action("เอ", f"DB error: {str(db_err)}", "WARNING")
            finally:
                if db:
                    db.close()

        except Exception as e:
            self.log_action("เอ", f"Record failed: {str(e)}", "ERROR")

    # ==================== AGENT 9: โคลสัน (Manual Trade Update) ====================
    def colson_parse_trade(self, trade_text):
        """โคลสัน: รับ trade text จาก user → parse → บันทึก DB — Haiku เพียงพอ"""
        self.log_action("โคลสัน", f"Parsing trade: {trade_text[:50]}...", "INFO")
        try:
            system_prompt = """You are โคลสัน (Colson), a trade recorder.
Parse the trade instruction and return ONLY JSON:
{
    "ticker": "AAPL",
    "action": "BUY" or "SELL",
    "shares": 100,
    "price": 150.25
}
If you cannot parse, return {"error": "reason"}."""

            response = self.claude_call(system_prompt, trade_text, "โคลสัน",
                                        model=self.MODEL_HAIKU)
            try:
                trade_data = json.loads(response[response.find('{'):response.rfind('}')+1])
                if "error" in trade_data:
                    self.log_action("โคลสัน", f"Parse error: {trade_data['error']}", "WARNING")
                    return None

                # บันทึกลง DB
                db = None
                try:
                    db = SessionLocal()
                    trade = Trade(
                        ticker=trade_data.get("ticker", "").upper(),
                        action=trade_data.get("action", ""),
                        # ✅ แก้ 2026-07-03: shares เดิม int() ปัดเศษหุ้นทิ้งหมด (MBBook ซื้อ fractional shares)
                        shares=float(trade_data.get("shares", 0)),
                        price=float(trade_data.get("price", 0))
                    )
                    db.add(trade)
                    db.commit()
                    self.log_action("โคลสัน", f"Trade recorded: {trade_data}", "SUCCESS")
                    return trade_data
                finally:
                    if db:
                        db.close()

            except json.JSONDecodeError:
                self.log_action("โคลสัน", "Could not parse trade response", "ERROR")
                return None

        except Exception as e:
            self.log_action("โคลสัน", f"Trade parse failed: {str(e)}", "ERROR")
            return None

    # ✅ เพิ่ม 2026-07-03: โคลสัน อ่านรูปสลิปซื้อขาย (เช่น screenshot จาก Dime app) แทนพิมพ์มือ
    # MBBook ยืนยันแล้วว่าอยากส่งรูปสลิปเข้าเว็บแอปโดยตรง ไม่ใช่กรอกฟอร์มเอง
    # ไม่บันทึก DB ในเมธอดนี้ — แค่ parse แล้วคืนค่าให้ endpoint ตัดสินใจ (ให้ user preview/แก้ก่อน save จริง)
    def colson_parse_trade_image(self, image_base64, media_type="image/jpeg"):
        """โคลสัน: อ่านรูปสลิปคำสั่งซื้อขาย (เช่น Dime app) → parse ticker/action/shares/price ด้วย vision
        คืนค่า dict {ticker, action, shares, price} หรือ {"error": reason}"""
        self.log_action("โคลสัน", "Parsing trade slip image...", "INFO")
        try:
            system_prompt = """You are โคลสัน (Colson), a trade slip reader.
You will see a screenshot of a stock trade confirmation from a brokerage app (e.g. Dime).
Read the slip and return ONLY JSON, no other text:
{
    "ticker": "AAPL",
    "action": "BUY" or "SELL",
    "shares": 12.345,
    "price": 150.25
}
Rules:
- action: look at the header/title of the slip — "ซื้อ"/"Buy" = BUY, "ขาย"/"Sell" = SELL
- shares: often a fractional number (e.g. 0.1874433) since orders are amount-based, not share-count-based. Read exactly as shown, do not round.
- price: use the ACTUAL EXECUTED price field (e.g. "ราคาที่ได้จริง" / "ราคาเฉลี่ย" / "avg fill price"), NOT the limit price the user set (e.g. NOT "ราคาที่คุณตั้ง").
- If the image is not a trade slip or required fields are unreadable, return {"error": "reason in Thai"}."""

            content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_base64,
                    },
                },
                {
                    "type": "text",
                    "text": "อ่านสลิปนี้แล้วคืนค่า JSON ตามที่กำหนด",
                },
            ]

            response = self.claude_call(system_prompt, content, "โคลสัน", model=self.MODEL_HAIKU)

            try:
                trade_data = json.loads(response[response.find('{'):response.rfind('}')+1])
                if "error" in trade_data:
                    self.log_action("โคลสัน", f"Image parse error: {trade_data['error']}", "WARNING")
                    return trade_data

                trade_data["ticker"] = str(trade_data.get("ticker", "")).upper().strip()
                trade_data["action"] = str(trade_data.get("action", "")).upper().strip()
                trade_data["shares"] = float(trade_data.get("shares", 0))
                trade_data["price"] = float(trade_data.get("price", 0))

                self.log_action("โคลสัน", f"Image parsed: {trade_data}", "SUCCESS")
                return trade_data

            except (json.JSONDecodeError, ValueError) as e:
                self.log_action("โคลสัน", f"Could not parse image response: {str(e)}", "ERROR")
                return {"error": "อ่านค่าจากรูปไม่สำเร็จ ลองส่งรูปใหม่หรือกรอกมือแทน"}

        except Exception as e:
            self.log_action("โคลสัน", f"Trade image parse failed: {str(e)}", "ERROR")
            return {"error": str(e)}

    # ==================== AGENT 10: นิก (Code Optimizer — Every Friday) ====================
    def nik_optimize_code(self):
        """นิก: อ่าน WorkflowLog 5 วัน → วิเคราะห์ → สร้าง diff → บันทึกลง DB รอ MBBook อนุมัติ
        ไม่ push GitHub โดยตรง — Cow เป็นคน apply หลัง MBBook กดอนุมัติบน webapp"""
        self.log_action("นิก", "Starting weekly code optimization (diff mode)...", "INFO")
        try:
            from datetime import timedelta

            # ===== Step 1: ดึง WorkflowLog ย้อนหลัง 5 วัน =====
            db = None
            db_logs = []
            try:
                db = SessionLocal()
                from models import WorkflowLog
                since = datetime.now() - timedelta(days=5)
                db_logs = db.query(WorkflowLog).filter(
                ).order_by(WorkflowLog.timestamp.desc()).all()
                self.log_action("นิก", f"Loaded {len(db_logs)} runs from DB", "INFO")
            except Exception as e:
                self.log_action("นิก", f"DB read failed: {str(e)}", "WARNING")
            finally:
                if db:
                    db.close()

            history = json.dumps([{
                "timestamp":    l.timestamp.isoformat(),
                "status":       l.status,
                "stocks":       l.stocks_analyzed,
                "buy":          l.buy_signals,
                "sell":         l.sell_signals,
                "needs_review": l.needs_review,
                "summary":      l.summary,
            } for l in db_logs], ensure_ascii=False) if db_logs else json.dumps(
                [l for l in self.workflow_log if l.get('status') in ('ERROR', 'WARNING')][-50:],
                ensure_ascii=False
            )

            session_errors = [l for l in self.workflow_log if l.get('status') in ('ERROR', 'WARNING')]
            session_text = json.dumps(session_errors[-30:], ensure_ascii=False) if session_errors else "ไม่มี error"

            # ===== Step 2: Pre-flight — ตรวจขนาด agents.py ก่อนส่ง Claude =====
            github_token = os.getenv("GITHUB_TOKEN")
            github_repo  = os.getenv("GITHUB_REPO", "MBBook/ai-stock-analyzer")
            current_code = None
            if github_token:
                current_code, _ = self._nik_get_current_agents_py(github_token, github_repo)
            if not current_code:
                self.log_action("นิก", "Cannot read agents.py — aborting", "ERROR")
                return None
            # ✅ แก้ 2026-07-04: agents.py โตเกิน 80000 chars ไปแล้วจริง (105872 chars ตอนพบปัญหา)
            # ทำให้นิกข้าม optimization ทุกวันศุกร์มาโดยไม่มีใครรู้ (แค่ log WARNING เงียบๆ ไม่มี error โผล่ที่ไหน)
            # เห็นตอน audit ระบบ 2026-07-04 — ดู Blueprint.md Defect #16 — ยกเพดานขึ้นเพื่อให้นิกกลับมาทำงานได้
            if len(current_code) > 300000:
                self.log_action("นิก", f"agents.py ใหญ่เกินไป ({len(current_code)} chars) — ข้าม optimization รอบนี้", "WARNING")
                return None

            # ===== Step 3: ให้ Claude วิเคราะห์ + สร้าง diff =====
            system_prompt = """You are นิก (Nik), an expert Python developer.

You will receive workflow error logs and the current agents.py.

Your job:
1. Identify TOP 3 issues from the logs
2. For each fix, output a DIFF block in this exact format:

<<<DIFF>>>
SUMMARY: one-line description of this change
FILE: agents.py
FIND:
<exact lines to replace — copy verbatim, include enough context to be unique>
REPLACE:
<new lines>
<<<END_DIFF>>>

RULES:
- Output ONLY diff blocks, no explanations outside them
- Each FIND block must be unique in the file (include enough context lines)
- Make MINIMAL changes — do not rewrite functions entirely
- Do NOT change model names, API keys, or database schema
- Max 3 diff blocks total"""

            user_message = f"""=== Workflow History (5 days) ===
{history}

=== Current Session Errors ===
{session_text}

=== Current agents.py (first 8000 chars for context) ===
{current_code[:8000]}

Identify top issues and output diff blocks."""

            self.log_action("นิก", "Analyzing logs and generating diff...", "INFO")
            diff_output = self.claude_call(
                system_prompt, user_message, "นิก",
                model=self.MODEL_SONNET,
                max_tokens=4096
            )

            # ===== Step 4: ตรวจ diff มีอยู่จริง =====
            if "<<<DIFF>>>" not in diff_output:
                self.log_action("นิก", "No valid diff blocks found in response — aborting", "WARNING")
                return None

            # สรุป summary จาก diff แรก
            summary_line = "ไม่ระบุ"
            for line in diff_output.split("\n"):
                if line.startswith("SUMMARY:"):
                    summary_line = line.replace("SUMMARY:", "").strip()
                    break

            # ===== Step 5: บันทึกลง NikSuggestion DB รอ MBBook อนุมัติ =====
            db2 = None
            try:
                db2 = SessionLocal()
                from models import NikSuggestion
                suggestion = NikSuggestion(
                    summary=summary_line,
                    diff_text=diff_output,
                    status="pending"
                )
                db2.add(suggestion)
                db2.commit()
                self.log_action("นิก", f"✅ Suggestion saved to DB (pending) — รอ MBBook อนุมัติบน webapp", "SUCCESS")
            except Exception as e:
                self.log_action("นิก", f"Cannot save suggestion to DB: {str(e)}", "ERROR")
            finally:
                if db2:
                    db2.close()

            return diff_output

        except Exception as e:
            self.log_action("นิก", f"Optimization failed: {str(e)}", "ERROR")
            return None

    def _nik_get_current_agents_py(self, github_token, repo):
        """ดึง agents.py ปัจจุบันจาก GitHub"""
        try:
            url = f"https://api.github.com/repos/{repo}/contents/agents.py"
            headers = {
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            res = requests.get(url, headers=headers, timeout=15).json()
            if "content" in res:
                import base64
                content = base64.b64decode(res["content"]).decode("utf-8")
                sha = res.get("sha", "")
                return content, sha
            return None, None
        except Exception as e:
            self.log_action("นิก", f"Could not fetch agents.py from GitHub: {str(e)}", "ERROR")
            return None, None

    # ==================== MAIN WORKFLOW ====================
    def run_workflow(self, stocks=None, portfolio=None, include_weekend=False):
        """Execute complete 10-agent workflow — Sequential
        นัตตี้ → หนุ่ม → มด → แฮรี่ → เจน → นน → (เก้า retry) → เอ → นิก(ศุกร์)
        Args:
            stocks: Stock list to analyze
            include_weekend: True for Monday (Sat-Sun-Mon news), False for Tue-Fri (24h news)
        """
        if not stocks:
            stocks = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]

        self.workflow_log = []
        self.session_cost_usd = 0.0  # reset ทุก run ใหม่

        # ===== BUDGET GUARD: ตรวจก่อนเริ่มเสมอ =====
        db_budget = None
        try:
            db_budget = SessionLocal()
            budget_ok, today_spent, daily_limit = self._check_daily_budget(db_budget)
            self.log_action("BUDGET", f"Today spent: ${today_spent:.4f} / Limit: ${daily_limit:.2f}", "INFO")
            if not budget_ok:
                self.log_action("BUDGET",
                    f"⚠️  Daily budget exceeded (${today_spent:.4f} >= ${daily_limit:.2f}) — workflow skipped to protect monthly cap",
                    "ERROR")
                # ✅ แก้ 2026-07-02: บันทึก WorkflowLog แม้ BUDGET_EXCEEDED (เดิมไม่บันทึกเลย)
                # เหตุผล: ถ้าไม่บันทึก /workflow/resume จะไม่เห็นว่าวันนี้เจอ BUDGET_EXCEEDED ไปแล้ว
                # แล้ว self-heal (ทุก 10 นาที) จะพยายามซ้ำไปเรื่อยๆ จนกว่า UTC date จะเปลี่ยน — ไม่มี LLM call
                # (ไม่เสียเงินซ้ำ) แค่ insert record ตรงๆ
                try:
                    from models import WorkflowLog
                    db_budget.add(WorkflowLog(
                        timestamp=datetime.now(),
                        status="BUDGET_EXCEEDED",
                        stocks_analyzed=0,
                        buy_signals=0, sell_signals=0, hold_signals=0, needs_review=0,
                        summary=f"Budget exceeded: spent ${today_spent:.4f} / limit ${daily_limit:.2f} — skipped",
                        include_weekend=include_weekend,
                        cost_usd=0.0,
                    ))
                    db_budget.commit()
                except Exception as log_err:
                    self.log_action("BUDGET", f"BUDGET_EXCEEDED log save failed: {log_err}", "WARNING")
                return {
                    "status": "BUDGET_EXCEEDED",
                    "reason": f"Daily limit ${daily_limit:.2f} reached (spent ${today_spent:.4f} today). Workflow skipped.",
                    "workflow_log": self.workflow_log,
                    "qa_result": None,
                    "report": None
                }
        finally:
            if db_budget:
                db_budget.close()

        if include_weekend:
            self.log_action("SYSTEM", "🔄 Monday mode: Fetching Sat-Sun-Mon news...", "INFO")
        else:
            self.log_action("SYSTEM", "📰 Regular mode: Fetching 24-hour news...", "INFO")

        try:
            # Step 1: นัตตี้ Get News + ราคา
            news_data = self.natty_get_news(
                stocks,
                days=3 if include_weekend else 1,
                include_weekend=include_weekend
            )

            # ✅ FIX #A: early exit ถ้าไม่มีข้อมูลหุ้นเลย ไม่ให้ workflow รันต่อแบบ COMPLETE ปลอม
            if not news_data:
                self.log_action("SYSTEM", "❌ No stock data fetched from any source — aborting workflow", "ERROR")
                return {
                    "status": "ABORTED",
                    "reason": "All data sources failed — yfinance, Finnhub, and Alpha Vantage all returned no data",
                    "workflow_log": self.workflow_log,
                    "qa_result": None,
                    "report": None
                }

            # Step 2: หนุ่ม Analyze
            analysis_results = self.num_analyze_stocks(news_data, stocks)

            # ✅ FIX #H: early exit ถ้า Claude วิเคราะห์ไม่ได้เลย ไม่ให้เจน/นน เสีย token โดยเปล่าประโยชน์
            if not analysis_results:
                self.log_action("SYSTEM", "❌ No analysis results from หนุ่ม — aborting workflow", "ERROR")
                return {
                    "status": "ABORTED",
                    "reason": "หนุ่ม could not analyze any stocks — all Claude calls failed",
                    "workflow_log": self.workflow_log,
                    "qa_result": None,
                    "report": None
                }

            # Step 3: มด Cross-Validate
            validated_results = self.mud_cross_validate(analysis_results)

            # ✅ CHECKPOINT: บันทึก signal ทีละตัวหลัง มด validate เสร็จ
            # ถ้า Render ล่มกลางทาง ข้อมูลที่วิเคราะห์แล้วจะยังอยู่ใน DB
            self._checkpoint_database(validated_results)

            # Step 4: แฮรี่ Monitor Portfolio
            portfolio_status = self.harry_monitor_portfolio(validated_results)

            # ========== REPORT + QA LOOP (real retry up to max_retries) ==========
            report = None
            qa_result = None
            qa_passed = False
            retry_hint = None  # ✅ FIX #C: เก็บ hint จากเก้าเพื่อส่งให้เจนในรอบถัดไป

            for attempt in range(1, self.max_retries + 1):
                # Step 5: เจน Generate Report (ส่ง retry_hint ถ้ามี)
                report = self.jen_generate_report(validated_results, portfolio_status, retry_hint=retry_hint)

                # Step 6: นน QA Check
                qa_result = self.nan_qa_check(validated_results, report)

                if qa_result.get('status') == 'PASS':
                    qa_passed = True
                    break

                # ❌ REJECT — เก้า วิเคราะห์ failure และคืน hint ให้เจนรอบถัดไป
                self.log_action("SYSTEM", f"❌ QA REJECTED (attempt {attempt}/{self.max_retries})", "ERROR")
                issue_msg = qa_result.get('issues', ['Unknown error'])[0] if qa_result.get('issues') else 'Unknown error'

                # ✅ FIX #C: เก็บ hint จากเก้าเพื่อส่งต่อให้เจน (ไม่เสีย token เปล่า)
                retry_hint = self.kao_retry("เจน+นน", issue_msg, attempt)

                if attempt < self.max_retries:
                    self.log_action("SYSTEM", f"🔄 Retrying report generation + QA (attempt {attempt + 1}/{self.max_retries})...", "INFO")
            
            # Step 7: Final Decision
            if qa_passed:
                self.log_action("SYSTEM", "✅ Workflow PASSED - Updating database...", "SUCCESS")
                self._update_database(validated_results)

                # ✅ เอ: บันทึก improvement log (+ ส่ง report เต็มของเจนให้บันทึกถาวรด้วย 2026-07-03)
                self.a_record_improvements({"qa_result": qa_result, "final_status": "COMPLETE", "report": report}, validated_results)

                # ✅ นิก: ทำงานทุกวันศุกร์เท่านั้น
                if datetime.now().weekday() == 4:  # 4 = Friday
                    self.log_action("SYSTEM", "📅 วันศุกร์ — เรียก นิก วิเคราะห์ code optimization", "INFO")
                    self.nik_optimize_code()

                final_status = "COMPLETE"
            else:
                self.log_action("SYSTEM", f"❌ Workflow REJECTED after {self.max_retries} attempts - Database NOT updated", "ERROR")
                final_status = "REJECTED"
                # ✅ บันทึก REJECTED run ลง DB ด้วย — ไม่งั้นหายจาก history (+ report ฉบับสุดท้ายที่ยังไม่ผ่าน QA เผื่ออ้างอิง)
                self.a_record_improvements({"qa_result": qa_result, "final_status": "REJECTED", "report": report}, validated_results)
            
            self.log_action("SYSTEM", f"Workflow finished with status: {final_status}", "SUCCESS" if qa_passed else "ERROR")
            return {
                "status": final_status,
                "workflow_log": self.workflow_log,
                "qa_result": qa_result,
                "report": report
            }
            
        except Exception as e:
            self.log_action("SYSTEM", f"❌ Workflow failed: {str(e)}", "ERROR")
            raise

    def _checkpoint_database(self, analysis_results):
        """CHECKPOINT: บันทึก signal ทันที — ป้องกันข้อมูลหายถ้า Render ล่ม/dyno sleep กลางคัน
        เรียก 2 จุด: (1) ทีละตัวทันทีหลังหนุ่มวิเคราะห์เสร็จแต่ละหุ้น (เพิ่ม 2026-07-01 — จุดที่ใช้เวลานานสุด
        และเสี่ยงโดนขัดจังหวะมากสุด) (2) อีกรอบหลังมด validate ครบทั้งชุด (ทับด้วยค่าที่ validate แล้ว)
        ใช้ flag checkpoint=True เพื่อแยกจาก _update_database ที่รันตอน QA pass เท่านั้น"""
        db = None
        try:
            db = SessionLocal()
            saved = []
            for ticker, analysis in analysis_results.items():
                if analysis.get('s1') is None or analysis.get('confidence', 0) == 0.0:
                    continue
                validation = analysis.get('validation', {})
                if validation.get('recommendation') == 'NEEDS_REVIEW':
                    continue
                stock = db.query(Stock).filter(Stock.ticker == ticker).first()
                if stock:
                    stock.signal        = analysis.get('signal', 'HOLD')
                    stock.confidence    = analysis.get('confidence', 0.5)
                    stock.current_price = analysis.get('price', stock.current_price) or stock.current_price
                    stock.at_new_high   = analysis.get('at_new_high', False)
                    stock.at_new_low    = analysis.get('at_new_low', False)
                    # ✅ เพิ่ม 2026-07-03: บันทึก reasoning ที่หนุ่มสร้างไว้แล้ว แต่ไม่เคย persist
                    stock.reasoning     = analysis.get('reasoning', stock.reasoning)
                    stock.updated_at    = datetime.now()
                    saved.append(ticker)
            db.commit()
            self.log_action("CHECKPOINT", f"Saved {len(saved)} tickers to DB: {saved}", "INFO")
        except Exception as e:
            self.log_action("CHECKPOINT", f"Checkpoint save failed: {str(e)}", "WARNING")
        finally:
            if db is not None:
                db.close()

    def _update_database(self, analysis_results):
        """อัพเดต Database ด้วยผลลัพธ์
        ✅ FIXED: ข้าม ticker ที่ มด flag เป็น NEEDS_REVIEW (ยังไม่ผ่านการตรวจสอบจริง)
        เพื่อไม่ให้ signal ที่ไม่ได้ validate หลุดเข้า DB เหมือนกับ validate ผ่านแล้ว"""
        db = None
        try:
            db = SessionLocal()
            skipped = []
            updated = []

            for ticker, analysis in analysis_results.items():
                validation = analysis.get('validation', {})
                if validation.get('recommendation') == 'NEEDS_REVIEW':
                    skipped.append(ticker)
                    self.log_action("DATABASE", f"Skipped {ticker}: flagged NEEDS_REVIEW by มด", "WARNING")
                    continue

                if analysis.get('s1') is None or analysis.get('confidence', 0) == 0.0:
                    skipped.append(ticker)
                    self.log_action("DATABASE", f"Skipped {ticker}: no real price data, not writing placeholder signal", "WARNING")
                    continue

                stock = db.query(Stock).filter(Stock.ticker == ticker).first()
                if stock:
                    stock.signal        = analysis.get('signal', 'HOLD')
                    stock.confidence    = analysis.get('confidence', 0.5)
                    stock.current_price = analysis.get('price', stock.current_price) or stock.current_price
                    stock.fair_price    = analysis.get('fair_price', stock.current_price)
                    stock.s1            = analysis.get('s1', stock.current_price)
                    stock.s2            = analysis.get('s2', stock.current_price)
                    stock.s3            = analysis.get('s3', stock.current_price)
                    stock.at_new_high   = analysis.get('at_new_high', False)
                    stock.at_new_low    = analysis.get('at_new_low', False)
                    # ✅ เพิ่ม 2026-07-03: บันทึก reasoning ที่หนุ่มสร้างไว้แล้ว แต่ไม่เคย persist
                    stock.reasoning     = analysis.get('reasoning', stock.reasoning)
                    stock.updated_at    = datetime.now()
                    updated.append(ticker)

                    # ✅ เพิ่ม 2026-07-04: insert-only snapshot ลง signal_history สำหรับคำนวณ ROI
                    # ย้อนหลัง (win rate 14d/30d เทียบ 75%, avg return 30d เทียบ 13%/เดือน — เฉพาะ BUY)
                    # เงื่อนไข skip เดียวกับด้านบน (ผ่าน มด แล้ว + มีราคาจริง) ให้ตรงกับที่เขียนลง stocks จริง
                    db.add(SignalHistory(
                        ticker=ticker,
                        signal=analysis.get('signal', 'HOLD'),
                        confidence=analysis.get('confidence', 0.5),
                        price=analysis.get('price', stock.current_price) or stock.current_price,
                    ))

            # ✅ เพิ่ม 2026-07-04: snapshot มูลค่าพอร์ตทั้งก้อนคืนนี้ (insert-only) สำหรับ
            # คำนวณผลตอบแทนสะสมของพอร์ตจริง (ไม่มีเส้นตาย เป้า 13% — ดู Blueprint.md Section 14)
            # ใช้ current_price ที่เพิ่ง update ในเซสชันนี้เอง (ยังไม่ commit แต่ query ซ้ำในเซสชัน
            # เดียวกันจะได้ค่าที่เพิ่งแก้ ผ่าน SQLAlchemy identity map)
            # ✅ แก้ 2026-07-04: ทำเฉพาะตอนมีอย่างน้อย 1 ticker ที่ update จริง — ถ้าคืนนี้ทุกตัวโดน
            # skip หมด (NEEDS_REVIEW/ไม่มีราคา) ไม่ต้อง query Portfolio เลย (ตรงกับพฤติกรรมเดิม
            # ที่เทสต์ยึดไว้อยู่แล้วว่า skip ทั้งหมด = ไม่แตะ DB เพิ่ม)
            if updated:
                self._snapshot_portfolio(db)

            db.commit()

            summary = f"Updated: {updated}" if updated else "No stocks updated"
            if skipped:
                summary += f" | Skipped: {skipped}"
            self.log_action("DATABASE", summary, "SUCCESS")
        except Exception as e:
            self.log_action("DATABASE", f"Update failed: {str(e)}", "ERROR")
        finally:
            if db is not None:
                db.close()

    def _snapshot_portfolio(self, db):
        """✅ เพิ่ม 2026-07-04: คำนวณมูลค่ารวม + ต้นทุนรวมของพอร์ตทั้งก้อน แล้ว insert
        ลง portfolio_snapshots (ไม่ commit เอง — ให้ผู้เรียกเป็นคน commit ในเซสชันเดียวกัน)
        สูตรเดียวกับ endpoint GET /portfolio ใน main.py (คำนวณสดจาก Stock.current_price)"""
        try:
            holdings = db.query(Portfolio).all()
            if not holdings:
                return  # ยังไม่มีพอร์ตให้ snapshot (เช่น ยังไม่เคยบันทึก trade เลย)

            total_value = 0.0
            total_cost = 0.0
            for h in holdings:
                stock = db.query(Stock).filter(Stock.ticker == h.ticker).first()
                current_price = stock.current_price if stock and stock.current_price else h.avg_cost
                total_value += h.shares * current_price
                total_cost += h.shares * h.avg_cost

            db.add(PortfolioSnapshot(total_value=total_value, total_cost=total_cost))
        except Exception as e:
            self.log_action("SYSTEM", f"Portfolio snapshot failed: {str(e)}", "WARNING")

    def calculate_roi(self, db=None):
        """✅ เพิ่ม 2026-07-04, แก้ 2026-07-04 (รอบ 2): ROI 2 ชั้น ตามที่ตกลงกับ MBBook —
        แยกวัด "ความแม่นของ AI" กับ "ผลตอบแทนจริงของบุ๊คเอง" คนละตัวชี้วัด (ดู Blueprint.md Section 14):
          1. win rate (BUY ราคาขึ้น = ถูก, SELL ราคาลง = ถูก) จาก signal_history ที่ระยะ 14 และ 30 วัน
             เทียบเกณฑ์ 75% — วัดความแม่นของ AI ล้วนๆ ไม่ขึ้นกับว่าบุ๊คเทรดตามจริงมั้ย
          2. ผลตอบแทนพอร์ตจริงสะสม (ไม่มีเส้นตาย) จาก portfolio_snapshots เทียบเป้า 13% —
             วัดผลจริงของบุ๊ค (ขึ้นกับการตัดสินใจเทรดของบุ๊คเองด้วย ไม่ใช่ AI ล้วนๆ)
        เฉพาะสัญญาณที่ "อายุครบ" (เกิดมาแล้ว >= N วัน) เท่านั้นที่ตัดสินถูก/ผิดได้ — สัญญาณใหม่ที่ยัง
        ไม่ถึงอายุ ถูกข้ามไปเงียบๆ ไม่นับทั้งถูกและผิด (ยังไม่มีคำตอบ)
        หมายเหตุ: avg_return_pct ในผลลัพธ์ 14d/30d เป็นแค่ค่าเฉลี่ยผลตอบแทนต่อสัญญาณ BUY (ข้อมูล
        diagnostic เสริม) ไม่มี target ผูกอยู่ — เป้า 13% อยู่ที่ portfolio_return เท่านั้น"""
        own_db = False
        if db is None:
            db = SessionLocal()
            own_db = True
        try:
            now = datetime.now()
            result = {}

            # ✅ ดึงข้อมูลทั้งหมดมาครั้งเดียว แล้วคำนวณ 14d/30d ใน Python แทนการ query
            # ซ้ำต่อสัญญาณ (N+1) — เร็วกว่า และง่ายต่อการเทสต์
            all_rows = db.query(SignalHistory).order_by(SignalHistory.timestamp.asc()).all()
            by_ticker = {}
            for row in all_rows:
                by_ticker.setdefault(row.ticker, []).append(row)

            for horizon_days in (14, 30):
                cutoff = now - timedelta(days=horizon_days)
                wins = 0
                losses = 0
                buy_returns = []

                for row in all_rows:
                    if row.signal not in ("BUY", "SELL"):
                        continue
                    if not row.timestamp or row.timestamp > cutoff:
                        continue  # ยังไม่ครบอายุ — ตัดสินไม่ได้ ข้ามเงียบๆ
                    if not row.price:
                        continue  # ไม่มีราคาตั้งต้น ตัดสินไม่ได้

                    target_time = row.timestamp + timedelta(days=horizon_days)
                    nearby = [
                        r for r in by_ticker.get(row.ticker, [])
                        if r.price and abs((r.timestamp - target_time).total_seconds()) <= 5 * 86400
                    ]
                    if not nearby:
                        continue  # ไม่มี snapshot ราคาในช่วงนั้น (เช่น หุ้นเพิ่งเพิ่มเข้าระบบ) — ข้าม

                    future_row = min(nearby, key=lambda r: abs((r.timestamp - target_time).total_seconds()))

                    price_then  = row.price
                    price_later = future_row.price

                    if row.signal == "BUY":
                        correct = price_later > price_then
                        buy_returns.append((price_later - price_then) / price_then * 100)
                    else:  # SELL
                        correct = price_later < price_then

                    if correct:
                            wins += 1
                    else:
                        losses += 1

                evaluated  = wins + losses
                win_rate   = round(wins / evaluated * 100, 1) if evaluated else None
                avg_return = round(sum(buy_returns) / len(buy_returns), 2) if buy_returns else None

                result[f"{horizon_days}d"] = {
                    "win_rate_pct": win_rate,
                    "win_rate_target_pct": 75,
                    "meets_win_target": (win_rate >= 75) if win_rate is not None else None,
                    "evaluated_signals": evaluated,
                    "wins": wins,
                    "losses": losses,
                    "avg_return_pct": avg_return,  # diagnostic เสริม — ไม่มี target ผูก (ดู portfolio_return)
                    "buy_signals_counted": len(buy_returns),
                }

            # ✅ เพิ่ม 2026-07-04 (รอบ 2): ผลตอบแทนพอร์ตจริงสะสม ไม่มีเส้นตาย เทียบเป้า 13%
            # ใช้ snapshot ล่าสุดเทียบกับต้นทุนจริง (ไม่ใช่มูลค่าวันแรกที่เริ่ม track)
            # ✅ แก้ 2026-07-04: แยก try/except ของส่วนนี้ออกมาต่างหาก — ถ้า query
            # portfolio_snapshots พังด้วยเหตุผลอะไรก็ตาม ต้องไม่ทำให้ผลลัพธ์ win rate
            # (14d/30d) ที่คำนวณสำเร็จไปแล้วด้านบนหายไปด้วย (คนละส่วนกัน ไม่ควรผูกชะตากรรมกัน)
            try:
                latest_snapshot = (
                    db.query(PortfolioSnapshot)
                    .order_by(PortfolioSnapshot.timestamp.desc())
                    .first()
                )
                if latest_snapshot and latest_snapshot.total_cost:
                    return_pct = round(
                        (latest_snapshot.total_value - latest_snapshot.total_cost) / latest_snapshot.total_cost * 100,
                        2
                    )
                    result["portfolio_return"] = {
                        "return_pct": return_pct,
                        "target_pct": 13,
                        "meets_target": return_pct >= 13,
                        "has_deadline": False,  # ไม่มีเส้นตาย ต่างจาก win rate ที่มีกรอบ 14/30 วันชัดเจน
                        "total_value": round(latest_snapshot.total_value, 2),
                        "total_cost": round(latest_snapshot.total_cost, 2),
                        "as_of": latest_snapshot.timestamp,
                    }
                else:
                    result["portfolio_return"] = {
                        "return_pct": None,
                        "target_pct": 13,
                        "meets_target": None,
                        "has_deadline": False,
                        "total_value": None,
                        "total_cost": None,
                        "as_of": None,
                    }
            except Exception as e:
                self.log_action("SYSTEM", f"Portfolio return calculation failed: {str(e)}", "WARNING")
                result["portfolio_return"] = {"error": str(e)}

            return result
        except Exception as e:
            self.log_action("SYSTEM", f"ROI calculation failed: {str(e)}", "ERROR")
            return {"error": str(e)}
        finally:
            if own_db:
                db.close()

    def portfolio_return_history(self, db=None):
        """✅ เพิ่ม 2026-07-04: ข้อมูลสำหรับกราฟแท่ง 2 อัน ตามที่ MBBook ขอ —
        รายวัน (จันทร์-ศุกร์ หลังตลาดปิด) และรายเดือน (snapshot สุดท้ายของแต่ละเดือน)
        ใช้ snapshot ล่าสุดของแต่ละวัน/เดือน (กัน duplicate จากกรณีรัน resume หลายรอบในวันเดียว)"""
        own_db = False
        if db is None:
            db = SessionLocal()
            own_db = True
        try:
            rows = db.query(PortfolioSnapshot).order_by(PortfolioSnapshot.timestamp.asc()).all()

            by_day = {}
            by_month = {}
            for r in rows:
                if not r.timestamp or not r.total_cost:
                    continue
                by_day[r.timestamp.strftime("%Y-%m-%d")] = r    # เรียง asc แล้ว แถวหลังสุดทับแถวก่อนเสมอ
                by_month[r.timestamp.strftime("%Y-%m")] = r

            def _point(period, row):
                return_pct = round((row.total_value - row.total_cost) / row.total_cost * 100, 2)
                return {"period": period, "return_pct": return_pct, "total_value": round(row.total_value, 2)}

            daily = [
                _point(k, r) for k, r in sorted(by_day.items())
                if r.timestamp.weekday() < 5  # จันทร์-ศุกร์เท่านั้น
            ]
            monthly = [_point(k, r) for k, r in sorted(by_month.items())]

            return {"daily": daily, "monthly": monthly}
        except Exception as e:
            self.log_action("SYSTEM", f"Portfolio history calculation failed: {str(e)}", "ERROR")
            return {"error": str(e)}
        finally:
            if own_db:
                db.close()


# Initialize orchestrator
orchestrator = AgentOrchestrator()
