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
        
        self.log_action("SYSTEM", f"Loaded {len(self.api_keys)} API keys", "INFO")
        self.log_action("SYSTEM", "Database URL validated", "INFO")

        # ✅ FIX #D: validate API keys ตั้งแต่ boot ไม่รอให้ workflow fail ก่อนค่อยรู้
        if not os.getenv("FINNHUB_API_KEY"):
            self.log_action("SYSTEM", "⚠️ FINNHUB_API_KEY not set — Tier 2 (Finnhub) will be unavailable", "WARNING")
        if not os.getenv("ALPHA_VANTAGE_API_KEY"):
            self.log_action("SYSTEM", "⚠️ ALPHA_VANTAGE_API_KEY not set — Tier 3 (Alpha Vantage) will be unavailable", "WARNING")
        if not os.getenv("MARKETAUX_API_KEY"):
            self.log_action("SYSTEM", "⚠️ MARKETAUX_API_KEY not set — news fetching will be disabled", "WARNING")
    
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

    def claude_call(self, system_prompt, user_message, agent_name="Claude", model=None, use_cache=False):
        """ใช้ Claude API สำหรับ Agent (with auto-fallback + model selection + caching)
        ✅ model: ระบุ model ที่ต้องการ (default = Sonnet)
        ✅ use_cache: เปิด prompt caching บน system_prompt (ลด cost ~50% สำหรับ repeated calls)"""
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
                    max_tokens=4096,
                    system=system_block,
                    messages=messages,
                    extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"} if use_cache else {}
                )
                assistant_message = response.content[0].text
                self.log_action(agent_name, f"Claude call success ({model.split('-')[1]} Key#{self.current_key_index + 1})", "SUCCESS")
                return assistant_message

            except Exception as e:
                error_msg = str(e)
                self.log_action(agent_name, f"Claude call error on Key #{self.current_key_index + 1}: {error_msg}", "ERROR")
                attempt += 1
                if attempt < max_attempts:
                    self.log_action(agent_name, f"Trying next API key ({attempt}/{max_attempts})...", "WARNING")
                    self.rotate_to_next_key()
                else:
                    self.log_action(agent_name, f"All {max_attempts} API keys exhausted", "ERROR")
                    raise

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

            return {
                "symbol":      ticker,
                "price":       price,
                "52week_high": self._safe_positive_float(metric.get("52WeekHigh")),
                "52week_low":  self._safe_positive_float(metric.get("52WeekLow")),
                "pe_ratio":    self._safe_float(metric.get("peNormalizedAnnual")),        # ✅ ลบได้
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

        session = LimiterSession(per_second=2)
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        })
        # ✅ FIX #I: TimeoutAdapter ย้ายไป top-level แล้ว ใช้ได้เลยไม่ต้อง redefine
        session.mount('https://', TimeoutAdapter())
        session.mount('http://', TimeoutAdapter())

        for ticker in stocks:
            data = None

            # ===== TIER 1: yfinance =====
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
                    "pe_ratio":    self._safe_float(info.get('trailingPE')),         # ✅ ลบได้
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

            # log เตือนถ้าขาด P/E (หนุ่มจะได้รับแจ้งใน prompt)
            if data.get("pe_ratio") is None:
                self.log_action("นัตตี้", f"⚠️  {ticker}: P/E unavailable (loss-making co. หรือ API ไม่มีข้อมูล)", "WARNING")

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
                mcap_text = f"${mcap_display:,.0f}" if mcap_display is not None else "N/A (ไม่มีข้อมูล)"

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

                user_message = f"""Analyze this stock:
Symbol: {ticker}
Current Price: ${data.get('price', 0)}
52-week High: ${data.get('52week_high') or 'N/A'}
52-week Low: ${data.get('52week_low') or 'N/A'}
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
- ถ้า Data Source เป็น lower reliability ให้ลด confidence อย่างน้อย 0.15

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
}"""
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

            retry_section = f"\n\nFEEDBACK FROM PREVIOUS ATTEMPT:\n{retry_hint}\nPlease address the above issues in this report." if retry_hint else ""

            user_message = f"""Generate report based on this data:
Analysis Results: {json.dumps(jen_summary, ensure_ascii=False)}
Portfolio Status: {json.dumps(portfolio_status, ensure_ascii=False)}
{retry_section}
Create professional Thai report."""

            response = self.claude_call(system_prompt, user_message, "เจน",
                                        model=self.MODEL_SONNET, use_cache=True)
            report = {
                "timestamp":    datetime.now().isoformat(),
                "summary":      response,
                "total_stocks": len(analysis_results),
                "buy_signals":  sum(1 for a in analysis_results.values() if a.get('signal') == 'BUY'),
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
3. STRICT WARNING: NEVER copy, paste, embed, replicate, or leak raw HTML code strings, layout blocks, table chunks, script templates, or tags (such as <td>, <tr>, <div>, <style>) into any JSON string fields. Keep all output exclusively as plain descriptive text characters."""

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
                    "signal":     data.get("signal"),
                    "confidence": data.get("confidence"),
                    "s1":         data.get("s1"),
                    "s2":         data.get("s2"),
                    "s3":         data.get("s3"),
                    "reasoning":  data.get("reasoning"),
                    "validation": data.get("validation", {}).get("recommendation")
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

            # บันทึกลง DB
            db = None
            try:
                db = SessionLocal()
                try:
                    from models import WorkflowLog
                    log_entry = WorkflowLog(
                        timestamp=datetime.now(),
                        status=workflow_result.get('qa_result', {}).get('status', 'UNKNOWN'),
                        stocks_analyzed=len(validated_results),
                        buy_signals=buy_count,
                        sell_signals=sell_count,
                        hold_signals=hold_count,
                        needs_review=needs_review,
                        summary=summary,
                        include_weekend=workflow_result.get('include_weekend', False)
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
                        shares=int(trade_data.get("shares", 0)),
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

    # ==================== AGENT 10: นิก (Code Optimizer — Every Friday) ====================
    def nik_optimize_code(self):
        """นิก: อ่าน WorkflowLog ย้อนหลัง 5 วันจาก DB → วิเคราะห์ → push GitHub — Haiku"""
        self.log_action("นิก", "Starting weekly code optimization analysis...", "INFO")
        try:
            # ✅ ดึง logs ย้อนหลัง 5 วัน จาก DB จริงๆ (ไม่ใช่แค่ session ปัจจุบัน)
            from datetime import timedelta
            db = None
            db_logs = []
            try:
                db = SessionLocal()
                try:
                    from models import WorkflowLog
                    since = datetime.now() - timedelta(days=5)
                    db_logs = db.query(WorkflowLog).filter(
                        WorkflowLog.timestamp >= since
                    ).order_by(WorkflowLog.timestamp.desc()).all()
                    self.log_action("นิก", f"Loaded {len(db_logs)} workflow runs from DB (past 5 days)", "INFO")
                except ImportError:
                    self.log_action("นิก", "WorkflowLog model not found — using session logs only", "WARNING")
            except Exception as db_err:
                self.log_action("นิก", f"DB read failed: {str(db_err)} — using session logs only", "WARNING")
            finally:
                if db:
                    db.close()

            # สร้าง analysis context จาก DB logs
            if db_logs:
                db_summary = []
                for log in db_logs:
                    db_summary.append({
                        "timestamp":       log.timestamp.isoformat(),
                        "status":          log.status,
                        "stocks_analyzed": log.stocks_analyzed,
                        "buy":             log.buy_signals,
                        "sell":            log.sell_signals,
                        "hold":            log.hold_signals,
                        "needs_review":    log.needs_review,
                        "summary":         log.summary,
                        "include_weekend": log.include_weekend,
                    })
                history_text = json.dumps(db_summary, ensure_ascii=False)
            else:
                # fallback: ใช้ session logs ถ้า DB ว่าง
                error_logs   = [l for l in self.workflow_log if l.get('status') in ('ERROR', 'WARNING')]
                history_text = json.dumps(error_logs[-50:], ensure_ascii=False)

            # รวม error logs ของ session ปัจจุบันด้วย
            session_errors = [l for l in self.workflow_log if l.get('status') in ('ERROR', 'WARNING')]
            session_text   = json.dumps(session_errors[-30:], ensure_ascii=False) if session_errors else "ไม่มี error ใน session นี้"

            system_prompt = """You are นิก (Nik), a code optimization specialist for an AI stock analyzer system.
You have access to workflow run history and error logs from the past 5 days.

Analyze the data and provide specific, actionable improvements for agents.py.
Focus on:
1. Recurring errors or failures (which agents fail most?)
2. QA rejection patterns (what causes REJECT?)
3. Data quality issues (which tickers fail to fetch data?)
4. Performance bottlenecks
5. Signal quality concerns

Reply in Thai with specific recommendations.
Format: numbered list, max 5 items, each with clear action to take."""

            user_message = f"""Weekly optimization analysis for AI Stock Analyzer:

=== Workflow History (past 5 days from DB) ===
{history_text}

=== Current Session Error Logs ===
{session_text}

What are the top 5 specific improvements needed in the agent system?
List each with: ปัญหา, สาเหตุ, วิธีแก้ไข"""

            recommendations = self.claude_call(system_prompt, user_message, "นิก",
                                               model=self.MODEL_HAIKU)

            self.log_action("นิก", f"✅ Optimization recommendations:\n{recommendations}", "SUCCESS")

            # Push ไป GitHub ถ้ามี GITHUB_TOKEN
            github_token = os.getenv("GITHUB_TOKEN")
            github_repo  = os.getenv("GITHUB_REPO", "MBBook/ai-stock-analyzer")

            if github_token:
                self._nik_push_recommendations(recommendations, github_token, github_repo)
            else:
                self.log_action("นิก", "GITHUB_TOKEN not set — recommendations logged only", "WARNING")

            return recommendations

        except Exception as e:
            self.log_action("นิก", f"Optimization failed: {str(e)}", "ERROR")
            return None

    def _nik_push_recommendations(self, recommendations, github_token, repo):
        """นิก push improvement report ไป GitHub เป็น markdown file"""
        try:
            import base64
            filename = f"nik_reports/optimization_{datetime.now().strftime('%Y%m%d')}.md"
            content  = f"# นิก Optimization Report — {datetime.now().strftime('%Y-%m-%d')}\n\n{recommendations}"
            encoded  = base64.b64encode(content.encode()).decode()

            url = f"https://api.github.com/repos/{repo}/contents/{filename}"
            headers = {
                "Authorization": f"token {github_token}",
                "Accept":        "application/vnd.github.v3+json"
            }
            payload = {
                "message": f"นิก: Weekly optimization report {datetime.now().strftime('%Y-%m-%d')}",
                "content": encoded
            }
            res = requests.put(url, headers=headers, json=payload, timeout=15)
            if res.status_code in (200, 201):
                self.log_action("นิก", f"Report pushed to GitHub: {filename}", "SUCCESS")
            else:
                self.log_action("นิก", f"GitHub push failed: {res.status_code} {res.text[:100]}", "ERROR")
        except Exception as e:
            self.log_action("นิก", f"GitHub push error: {str(e)}", "ERROR")

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

                # ✅ เอ: บันทึก improvement log
                self.a_record_improvements({"qa_result": qa_result}, validated_results)

                # ✅ นิก: ทำงานทุกวันศุกร์เท่านั้น
                if datetime.now().weekday() == 4:  # 4 = Friday
                    self.log_action("SYSTEM", "📅 วันศุกร์ — เรียก นิก วิเคราะห์ code optimization", "INFO")
                    self.nik_optimize_code()

                final_status = "COMPLETE"
            else:
                self.log_action("SYSTEM", f"❌ Workflow REJECTED after {self.max_retries} attempts - Database NOT updated", "ERROR")
                final_status = "REJECTED"
            
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
                    stock.updated_at    = datetime.now()
                    updated.append(ticker)

            # ✅ FIX #E: commit ครั้งเดียวหลัง loop จบ (แทน N commits แยก)
            # ลด DB round trips จาก N → 1 ประหยัดเวลาเมื่อมีหุ้น 30-40 ตัว
            db.commit()

            summary = f"Updated: {updated}" if updated else "No stocks updated"
            if skipped:
                summary += f" | Skipped: {skipped}"
            self.log_action("DATABASE", summary, "SUCCESS")
        except Exception as e:
            self.log_action("DATABASE", f"Update failed: {str(e)}", "ERROR")
        finally:
            # ✅ ปิด connection เสมอ ไม่ว่าจะสำเร็จหรือ exception
            if db is not None:
                db.close()


# Initialize orchestrator
orchestrator = AgentOrchestrator()
