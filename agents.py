"""
AI Stock Analyzer V4 - Agent System with Multi-Key Fallback
Sequential Workflow with auto-fallback to next API key if current fails
FIXED: Removed async/await, added database validation
"""

import time
import re
import requests
from anthropic import Anthropic
from datetime import datetime, timedelta
import yfinance as yf
from requests_ratelimiter import LimiterSession
import json
import os
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Stock, Trade, Portfolio

class AgentOrchestrator:
    def __init__(self):
        self.workflow_log = []
        self.error_count = {}
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
    
    def claude_call(self, system_prompt, user_message, agent_name="Claude"):
        """ใช้ Claude API สำหรับ Agent (with auto-fallback)
        ✅ FIXED: แต่ละ call เป็น single-turn อิสระ ไม่ share history ข้าม agent/ticker
        เพื่อป้องกัน: (1) token บวมสะสมตลอด workflow (2) Claude สับสน persona ข้าม agent"""
        max_attempts = len(self.api_keys)
        attempt = 0
        messages = [{"role": "user", "content": user_message}]
        
        while attempt < max_attempts:
            try:
                # Get current client
                client = self.get_client()
                
                # Call Claude API (synchronous, isolated single-turn)
                response = client.messages.create(
                    model="claude-opus-4-6",
                    max_tokens=16000,
                    system=system_prompt,
                    messages=messages
                )
                
                assistant_message = response.content[0].text
                
                self.log_action(agent_name, f"Claude call success (Key #{self.current_key_index + 1})", "SUCCESS")
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
        """แปลงค่าเป็น float อย่างปลอดภัย
        ✅ FIX #3: รองรับ edge cases ทั้งหมดที่ Alpha Vantage / Finnhub อาจส่งมา
        คืน None เมื่อค่าว่าง, placeholder, หรือแปลงไม่ได้ — ไม่ crash ด้วย ValueError"""
        if val is None:
            return None
        cleaned = str(val).strip()
        # placeholder strings ที่ API มักส่งมาเมื่อไม่มีข้อมูล
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
            price = self._safe_float(quote.get("c"))  # c = current price

            if not price:
                return None  # ถ้าไม่มีราคาเลย → ไม่มีประโยชน์วิเคราะห์

            # Call 2: fundamental + 52-week range (แยก endpoint)
            metric_url = f"https://finnhub.io/api/v1/stock/metric?symbol={ticker}&metric=all&token={api_key}"
            metric = requests.get(metric_url, timeout=10).json().get("metric", {})

            return {
                "symbol":      ticker,
                "price":       price,
                "52week_high": self._safe_float(metric.get("52WeekHigh")),
                "52week_low":  self._safe_float(metric.get("52WeekLow")),
                "pe_ratio":    self._safe_float(metric.get("peNormalizedAnnual")),
                "market_cap":  self._safe_float(metric.get("marketCapitalization")),
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
                "pe_ratio":       self._safe_float(res.get("PERatio")),
                "market_cap":     self._safe_float(res.get("MarketCapitalization")),
                "52week_high":    self._safe_float(res.get("52WeekHigh")),
                "52week_low":     self._safe_float(res.get("52WeekLow")),
                # 200DMA เป็น fallback price (ไม่ real-time แต่ดีกว่าส่ง 0 ให้หนุ่ม)
                "price_fallback": self._safe_float(res.get("200DayMovingAverage")),
            }
        except Exception as e:
            self.log_action("นัตตี้", f"Alpha Vantage OVERVIEW fail for {ticker}: {str(e)}", "WARNING")
            return {"pe_ratio": None, "market_cap": None, "52week_high": None, "52week_low": None, "price_fallback": None}

    def natty_get_news(self, stocks, days=1):
        """นัตตี้: ระบบสายสำรอง 3 ชั้น รองรับพอร์ต 30-40 ตัวได้สบาย
        Tier 1 (yfinance):      ฟรี ครบ แต่ติด 429 บน cloud IP
        Tier 2 (Finnhub):       60 req/min ไม่จำกัด daily ✅ ข้อมูลครบ P/E + 52-week จริง
        Tier 3 (Alpha Vantage): 5 req/min 25/day ⚠️  สำรองสุดท้ายเท่านั้น
        ✅ FIX #1: API keys โหลดจาก environment variables ไม่ hardcode ใน code"""
        self.log_action("นัตตี้", "Starting news and data fetch (3-tier fallback)...", "INFO")

        # ✅ FIX #1: ดึง keys จาก Render ENV ไม่ hardcode ใน source code
        FINNHUB_KEY       = os.getenv("FINNHUB_API_KEY")
        ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

        if not FINNHUB_KEY:
            self.log_action("นัตตี้", "⚠️  FINNHUB_API_KEY not set — Tier 2 disabled", "WARNING")
        if not ALPHA_VANTAGE_KEY:
            self.log_action("นัตตี้", "⚠️  ALPHA_VANTAGE_API_KEY not set — Tier 3 disabled", "WARNING")

        news_data = {}

        session = LimiterSession(per_second=2)
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        })
        from requests.adapters import HTTPAdapter
        class TimeoutAdapter(HTTPAdapter):
            def send(self, request, **kwargs):
                kwargs.setdefault('timeout', 10)
                return super().send(request, **kwargs)
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
                price = self._safe_float(info.get('currentPrice'))
                if not price:
                    raise Exception("yfinance: currentPrice is 0 or None")

                data = {
                    "symbol":      ticker,
                    "price":       price,
                    "52week_high": self._safe_float(info.get('fiftyTwoWeekHigh')),
                    "52week_low":  self._safe_float(info.get('fiftyTwoWeekLow')),
                    "pe_ratio":    self._safe_float(info.get('trailingPE')),
                    "market_cap":  self._safe_float(info.get('marketCap')),
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

            news_data[ticker] = data

        self.log_action("นัตตี้", f"Fetched {len(news_data)}/{len(stocks)} stocks (source breakdown in logs above)", "SUCCESS")
        return news_data


    # ==================== AGENT 2: หนุ่ม (Analyze Stocks) ====================
    def num_analyze_stocks(self, news_data, stocks):
        """หนุ่ม: วิเคราะห์หุ้นด้วย Claude + yfinance"""
        self.log_action("หนุ่ม", "Starting stock analysis...", "INFO")
        
        try:
            system_prompt = """You are หนุ่ม (Num), a professional stock analyst.
Analyze the stock data and provide:
1. BUY/HOLD/SELL signal
2. Confidence score (0-1)
3. 3 support/resistance levels (S1, S2, S3)
4. Brief reasoning in Thai

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
            
            for ticker, data in news_data.items():
                pe_display = data.get('pe_ratio')
                pe_text = f"{pe_display}" if pe_display is not None else "N/A (ไม่มีข้อมูล)"
                
                mcap_display = data.get('market_cap')
                mcap_text = f"${mcap_display:,.0f}" if mcap_display is not None else "N/A (ไม่มีข้อมูล)"
                
                user_message = f"""Analyze this stock:
Symbol: {ticker}
Current Price: ${data.get('price', 0)}
52-week High: ${data.get('52week_high', 0)}
52-week Low: ${data.get('52week_low', 0)}
P/E Ratio: {pe_text}
Market Cap: {mcap_text}

Note: If P/E Ratio or Market Cap is marked N/A, base your analysis primarily on price levels and the 52-week range, and lower your confidence score accordingly since fundamental data is incomplete.

Provide analysis in JSON format."""
                
                try:
                    response = self.claude_call(system_prompt, user_message, "หนุ่ม")
                    
                    # Parse JSON response
                    try:
                        json_start = response.find('{')
                        json_end = response.rfind('}') + 1
                        json_str = response[json_start:json_end]
                        result = json.loads(json_str)
                        
                        # ✅ ตรวจว่า signal เป็นค่าที่ระบบรองรับจริง ไม่งั้น frontend แสดงผลผิด
                        if result.get('signal') not in ('BUY', 'HOLD', 'SELL'):
                            self.log_action("หนุ่ม", f"{ticker}: invalid signal value '{result.get('signal')}' from Claude, defaulting to HOLD", "WARNING")
                            result['signal'] = 'HOLD'
                        
                        analysis_results[ticker] = result
                    except json.JSONDecodeError:
                        fallback_price = data.get('price', 0)
                        if fallback_price <= 0:
                            # ✅ ราคาไม่มีข้อมูลจริง (0 จาก fetch fail) — ห้ามคำนวณ S-levels ปลอม
                            self.log_action("หนุ่ม", f"{ticker}: price data unavailable, flagging instead of guessing", "WARNING")
                            analysis_results[ticker] = {
                                "ticker": ticker,
                                "signal": "HOLD",
                                "confidence": 0.0,
                                "s1": None,
                                "s2": None,
                                "s3": None,
                                "reasoning": "No price data available — analysis skipped, not a real signal"
                            }
                        else:
                            analysis_results[ticker] = {
                                "ticker": ticker,
                                "signal": "HOLD",
                                "confidence": 0.5,
                                "s1": fallback_price * 0.95,
                                "s2": fallback_price * 0.90,
                                "s3": fallback_price * 0.85,
                                "reasoning": "Unable to parse detailed analysis"
                            }
                    
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
        """มด: ตรวจสอบความถูกต้องของ signals จากหนุ่ม"""
        self.log_action("มด", "Starting cross-validation...", "INFO")
        
        try:
            system_prompt = """You are มด (Mud), a validation expert.
Review the stock analysis and validate:
1. Signal consistency
2. Confidence score reasonableness (0-1)
3. Support/Resistance levels logic

Return JSON:
{
    "ticker": "AAPL",
    "is_valid": true,
    "issues": [],
    "recommendation": "PASS"
}"""
            
            validated_results = {}
            
            for ticker, analysis in analysis_results.items():
                user_message = f"""Validate this analysis:
{json.dumps(analysis, indent=2)}

Check if signal, confidence, and S-levels are consistent."""
                
                try:
                    response = self.claude_call(system_prompt, user_message, "มด")
                    
                    try:
                        json_start = response.find('{')
                        json_end = response.rfind('}') + 1
                        json_str = response[json_start:json_end]
                        result = json.loads(json_str)
                        
                        validated_results[ticker] = {
                            **analysis,
                            "validation": result
                        }
                    except json.JSONDecodeError:
                        # ✅ ไม่ auto-PASS แบบหลอกๆ — flag ตามจริงว่า "ยังไม่ได้ตรวจสอบ"
                        self.log_action("มด", f"Could not parse validation JSON for {ticker} — flagging for review", "WARNING")
                        validated_results[ticker] = {
                            **analysis,
                            "validation": {
                                "is_valid": None,
                                "recommendation": "NEEDS_REVIEW",
                                "issues": ["Validation response could not be parsed; not actually validated"]
                            }
                        }
                    
                except Exception as e:
                    self.log_action("มด", f"Validation failed for {ticker}: {str(e)}", "WARNING")
                    # ✅ ไม่ auto-PASS แบบหลอกๆ — flag ตามจริงว่า "ยังไม่ได้ตรวจสอบ"
                    validated_results[ticker] = {
                        **analysis,
                        "validation": {
                            "is_valid": None,
                            "recommendation": "NEEDS_REVIEW",
                            "issues": [f"Validation call failed: {str(e)}"]
                        }
                    }
            
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
    def jen_generate_report(self, analysis_results, portfolio_status):
        """เจน: สร้าง Report สรุปจากการวิเคราะห์
        ✅ FIX #6: ส่งแค่ field ที่จำเป็นให้เจน ไม่ส่ง nested validation object ทั้งก้อน
        ลด token ต่อ call และป้องกัน context overflow เมื่อมีหุ้น 30-40 ตัว"""
        self.log_action("เจน", "Generating report...", "INFO")
        
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

            # ✅ FIX #6: ส่งเฉพาะ field ที่เจนต้องการวิเคราะห์จริง ๆ
            # ตัด nested validation object ออก เพื่อลด token โดยไม่กระทบคุณภาพ report
            jen_summary = {
                ticker: {
                    "signal":     data.get("signal"),
                    "confidence": data.get("confidence"),
                    "s1":         data.get("s1"),
                    "s2":         data.get("s2"),
                    "s3":         data.get("s3"),
                    "reasoning":  data.get("reasoning"),
                    "pe_ratio":   data.get("pe_ratio"),
                    "price":      data.get("price"),
                }
                for ticker, data in analysis_results.items()
            }

            user_message = f"""Generate report based on this data:
Analysis Results: {json.dumps(jen_summary, ensure_ascii=False)}
Portfolio Status: {json.dumps(portfolio_status, ensure_ascii=False)}

Create professional Thai report."""
            
            response = self.claude_call(system_prompt, user_message, "เจน")
            
            report = {
                "timestamp":   datetime.now().isoformat(),
                "summary":     response,
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
        """นน: ตรวจสอบคุณภาพก่อนส่ง (PASS/REJECT)
        ✅ FIX #4: system_prompt เพิ่ม HTML injection rules ป้องกัน HTML tags ใน approval_reason
        ✅ FIX #5: clean_report_text ใช้ word-boundary limit 8000 chars แทน [:3000] ที่ตัดกลาง JSON"""
        self.log_action("นน", "QA checking...", "INFO")

        try:
            # ✅ FIX #4: เพิ่ม CRITICAL RULES ห้าม Claude embed HTML ใน JSON fields
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

            # Strip HTML/CSS จาก report ก่อนส่งให้ นน
            raw_report = report.get('summary', '')
            clean_report_text = re.sub(r'<style[^>]*>.*?</style>', '', raw_report, flags=re.DOTALL)
            clean_report_text = re.sub(r'<[^>]+>', ' ', clean_report_text)
            clean_report_text = re.sub(r'\s+', ' ', clean_report_text).strip()

            # ✅ FIX #5: word-boundary limit 8000 chars (แทน [:3000] ที่ตัดกลาง JSON/คำ)
            # plain text หลัง strip HTML มักสั้นกว่า original 60-70%
            # 8000 chars ≈ 2000 tokens — สมดุลระหว่าง QA coverage และ cost
            MAX_REPORT_CHARS = 8000
            if len(clean_report_text) > MAX_REPORT_CHARS:
                cut = clean_report_text[:MAX_REPORT_CHARS].rsplit(' ', 1)[0]
                clean_report_text = cut + "... [ข้อความถูกย่อเพื่อประสิทธิภาพ QA]"

            # ส่งเฉพาะ field ที่ นน ต้องการจริง ๆ
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

            response = self.claude_call(system_prompt, user_message, "นน")

            try:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                json_str = response[json_start:json_end]
                qa_result = json.loads(json_str)

                # ✅ FIX #4: post-process strip HTML ออกจาก approval_reason และ issues
                # กรณี Claude ยังส่ง HTML มาทั้งที่ prompt บอกแล้ว
                if isinstance(qa_result.get("approval_reason"), str):
                    qa_result["approval_reason"] = re.sub(r'<[^>]+>', '', qa_result["approval_reason"]).strip()
                if isinstance(qa_result.get("issues"), list):
                    qa_result["issues"] = [
                        re.sub(r'<[^>]+>', '', issue).strip()
                        if isinstance(issue, str) else issue
                        for issue in qa_result["issues"]
                    ]

            except json.JSONDecodeError:
                # ✅ fail-safe: QA ทำไม่สำเร็จ → REJECT เพื่อความปลอดภัย (ไม่ auto-PASS)
                self.log_action("นน", "Could not parse QA response JSON — defaulting to REJECT for safety", "WARNING")
                qa_result = {
                    "status": "REJECT",
                    "issues": ["QA response could not be parsed; QA was not actually performed"],
                    "approval_reason": "Auto-rejected: unparseable QA response"
                }

        except Exception as e:
            self.log_action("นน", f"QA check failed: {str(e)}", "ERROR")
            return {
                "status": "REJECT",
                "issues": [f"QA call failed: {str(e)}"],
                "approval_reason": "Auto-rejected: QA system error"
            }

        self.log_action("นน", f"QA Status: {qa_result.get('status', 'UNKNOWN')}", "INFO")
        return qa_result


    # ==================== AGENT 7: เก้า (Retry Logic) ====================
    def kao_retry(self, agent_name, error_msg, attempt=1):
        """เก้า: Retry Assistant (max 3 times)"""
        if attempt > self.max_retries:
            self.log_action("เก้า", f"Max retries exceeded for {agent_name}", "ERROR")
            return False
        
        self.log_action("เก้า", f"Retrying {agent_name} (Attempt {attempt})", "INFO")
        
        try:
            system_prompt = """You are เก้า (Kao), Retry Assistant.
Suggest how to fix the error and retry."""
            
            user_message = f"""Agent {agent_name} failed with error:
{error_msg}

Suggest retry strategy."""
            
            response = self.claude_call(system_prompt, user_message, "เก้า")
            self.log_action("เก้า", f"Retry suggestion provided", "SUCCESS")
            return True
            
        except Exception as e:
            self.log_action("เก้า", f"Retry failed: {str(e)}", "ERROR")
            return False

    # ==================== MAIN WORKFLOW ====================
    def run_workflow(self, stocks=None, portfolio=None, include_weekend=False):
        """Execute complete workflow - SEQUENTIAL
        ✅ FIXED: เมื่อ QA REJECT จะ re-run เจน(report) + นน(QA) จริงๆ สูงสุด max_retries ครั้ง
        แทนที่จะแค่ log คำแนะนำแล้วถือว่า "complete" ทั้งที่ reject
        
        Args:
            stocks: Stock list to analyze
            portfolio: Current portfolio
            include_weekend: True for Monday (Sat-Sun-Mon), False for Tue-Fri (24h)
        """
        if not stocks:
            stocks = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
        
        self.workflow_log = []
        
        if include_weekend:
            self.log_action("SYSTEM", "🔄 Monday mode: Fetching Sat-Sun-Mon news...", "INFO")
        else:
            self.log_action("SYSTEM", "📰 Regular mode: Fetching 24-hour news...", "INFO")
        
        try:
            # ========== SEQUENTIAL EXECUTION (runs once) ==========
            
            # Step 1: นัตตี้ Get News
            news_data = self.natty_get_news(stocks, days=3 if include_weekend else 1)
            
            # Step 2: หนุ่ม Analyze
            analysis_results = self.num_analyze_stocks(news_data, stocks)
            
            # Step 3: มด Cross-Validate
            validated_results = self.mud_cross_validate(analysis_results)
            
            # Step 4: แฮรี่ Monitor Portfolio
            portfolio_status = self.harry_monitor_portfolio(validated_results)
            
            # ========== REPORT + QA LOOP (real retry up to max_retries) ==========
            report = None
            qa_result = None
            qa_passed = False
            
            for attempt in range(1, self.max_retries + 1):
                # Step 5: เจน Generate Report
                report = self.jen_generate_report(validated_results, portfolio_status)
                
                # Step 6: นน QA Check
                qa_result = self.nan_qa_check(validated_results, report)
                
                if qa_result.get('status') == 'PASS':
                    qa_passed = True
                    break
                
                # ❌ REJECT — ask เก้า for guidance, then actually retry (re-run เจน + นน)
                self.log_action("SYSTEM", f"❌ QA REJECTED (attempt {attempt}/{self.max_retries})", "ERROR")
                self.kao_retry("เจน+นน", qa_result.get('issues', ['Unknown error'])[0], attempt)
                
                if attempt < self.max_retries:
                    self.log_action("SYSTEM", f"🔄 Retrying report generation + QA (attempt {attempt + 1}/{self.max_retries})...", "INFO")
            
            # Step 7: Final Decision
            if qa_passed:
                self.log_action("SYSTEM", "✅ Workflow PASSED - Updating database...", "SUCCESS")
                self._update_database(validated_results)
                self.log_action("เอ", "Recording improvements and code updates", "SUCCESS")
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
            
            for ticker, analysis in analysis_results.items():
                validation = analysis.get('validation', {})
                if validation.get('recommendation') == 'NEEDS_REVIEW':
                    skipped.append(ticker)
                    self.log_action("DATABASE", f"Skipped {ticker}: flagged NEEDS_REVIEW by มด, not writing unvalidated signal", "WARNING")
                    continue
                
                if analysis.get('s1') is None or analysis.get('confidence', 0) == 0.0:
                    skipped.append(ticker)
                    self.log_action("DATABASE", f"Skipped {ticker}: no real price data available, not writing placeholder signal", "WARNING")
                    continue
                
                stock = db.query(Stock).filter(Stock.ticker == ticker).first()
                if stock:
                    stock.signal = analysis.get('signal', 'HOLD')
                    stock.confidence = analysis.get('confidence', 0.5)
                    stock.fair_price = analysis.get('fair_price', stock.current_price)
                    stock.s1 = analysis.get('s1', stock.current_price)
                    stock.s2 = analysis.get('s2', stock.current_price)
                    stock.s3 = analysis.get('s3', stock.current_price)
                    stock.updated_at = datetime.now()
                    db.commit()
            
            if skipped:
                self.log_action("DATABASE", f"Updated stock signals (skipped {len(skipped)}: {', '.join(skipped)})", "SUCCESS")
            else:
                self.log_action("DATABASE", "Updated stock signals", "SUCCESS")
        except Exception as e:
            self.log_action("DATABASE", f"Update failed: {str(e)}", "ERROR")
        finally:
            # ✅ ปิด connection เสมอ ไม่ว่าจะสำเร็จหรือ exception
            if db is not None:
                db.close()


# Initialize orchestrator
orchestrator = AgentOrchestrator()
