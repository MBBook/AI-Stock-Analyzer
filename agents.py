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
    def _fetch_alpha_vantage_overview(self, ticker, api_key):
        """ดึง P/E ratio, Market Cap และ 52-week range จาก Alpha Vantage OVERVIEW endpoint
        คืนค่า None (ไม่ใช่ 0) เมื่อหาไม่เจอ เพื่อไม่ให้ปนกับค่าจริง"""
        try:
            url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={api_key}"
            res = requests.get(url, timeout=10).json()
            
            def safe_float(val):
                return float(val) if val not in (None, "None", "") else None
            
            return {
                "pe_ratio":    safe_float(res.get("PERatio")),
                "market_cap":  safe_float(res.get("MarketCapitalization")),
                "52week_high": safe_float(res.get("52WeekHigh")),
                "52week_low":  safe_float(res.get("52WeekLow")),
            }
        except Exception as e:
            self.log_action("นัตตี้", f"Alpha Vantage OVERVIEW fail for {ticker}: {str(e)}", "WARNING")
            return {"pe_ratio": None, "market_cap": None, "52week_high": None, "52week_low": None}

    def natty_get_news(self, stocks, days=1):
        """นัตตี้: ดึงข้อมูลและข่าวสารหุ้นพร้อมระบบ Fallback ไป Alpha Vantage เมื่อเจอ 429
        ดึง P/E ratio และ Market Cap เสมอ (ทั้ง yfinance path และ Alpha Vantage path)
        เพื่อให้หนุ่มวิเคราะห์ได้ครบ ไม่ขาดข้อมูลสำคัญ"""
        self.log_action("นัตตี้", "Starting news and data fetch...", "INFO")
        
        ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
        if not ALPHA_VANTAGE_KEY:
            self.log_action("นัตตี้", "ALPHA_VANTAGE_API_KEY not set — fallback will be skipped if yfinance fails", "WARNING")
        news_data = {}

        session = LimiterSession(per_second=2)
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        })
        # ✅ ป้องกัน workflow ค้างไม่จบ ถ้า Yahoo เซิร์ฟเวอร์รับ request แต่ไม่ตอบกลับ
        from requests.adapters import HTTPAdapter
        class TimeoutAdapter(HTTPAdapter):
            def send(self, request, **kwargs):
                kwargs.setdefault('timeout', 10)
                return super().send(request, **kwargs)
        session.mount('https://', TimeoutAdapter())
        session.mount('http://', TimeoutAdapter())

        for ticker in stocks:
            try:
                time.sleep(2)
                self.log_action("นัตตี้", f"Fetching {ticker} from yfinance...", "INFO")
                stock_obj = yf.Ticker(ticker, session=session)
                
                if not stock_obj.info or 'currentPrice' not in stock_obj.info:
                    raise Exception("Trigger Fallback: yfinance rate limited.")
                
                info = stock_obj.info
                news_data[ticker] = {
                    "symbol": ticker,
                    "price": info.get('currentPrice', 0),
                    "52week_high": info.get('fiftyTwoWeekHigh', 0),
                    "52week_low": info.get('fiftyTwoWeekLow', 0),
                    "pe_ratio": info.get('trailingPE'),
                    "market_cap": info.get('marketCap')
                }
                
            except Exception as e:
                self.log_action("นัตตี้", f"yfinance blocked! Switching to Alpha Vantage for {ticker}...", "WARNING")
                
                if not ALPHA_VANTAGE_KEY:
                    self.log_action("นัตตี้", f"Skipping Alpha Vantage for {ticker}: no API key configured", "ERROR")
                    news_data[ticker] = {"symbol": ticker, "price": 0, "52week_high": 0, "52week_low": 0, "pe_ratio": None, "market_cap": None}
                    continue
                
                try:
                    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={ALPHA_VANTAGE_KEY}"
                    res = requests.get(url, timeout=10).json()
                    quote = res.get("Global Quote", {})
                    
                    if quote:
                        # ✅ ดึง P/E + Market Cap + 52-week range จาก OVERVIEW endpoint
                        # หมายเหตุ: GLOBAL_QUOTE มีแค่ intraday high/low ไม่ใช่ 52-week
                        # ต้องใช้ OVERVIEW ซึ่งมี 52WeekHigh / 52WeekLow จริง ๆ
                        overview = self._fetch_alpha_vantage_overview(ticker, ALPHA_VANTAGE_KEY)
                        news_data[ticker] = {
                            "symbol": ticker,
                            "price": float(quote.get("05. price", 0)),
                            "52week_high": overview.get("52week_high"),
                            "52week_low": overview.get("52week_low"),
                            "pe_ratio": overview["pe_ratio"],
                            "market_cap": overview["market_cap"]
                        }
                    else:
                        news_data[ticker] = {"symbol": ticker, "price": 0, "52week_high": 0, "52week_low": 0, "pe_ratio": None, "market_cap": None}
                except Exception as av_err:
                    self.log_action("นัตตี้", f"Alpha Vantage fail: {str(av_err)}", "ERROR")
                    news_data[ticker] = {"symbol": ticker, "price": 0, "52week_high": 0, "52week_low": 0, "pe_ratio": None, "market_cap": None}

        self.log_action("นัตตี้", f"Fetched {len(news_data)} stocks data successfully.", "INFO")
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
        """เจน: สร้าง Report สรุปจากการวิเคราะห์"""
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

            user_message = f"""Generate report based on this data:
Analysis Results: {json.dumps(analysis_results, ensure_ascii=False)}
Portfolio Status: {json.dumps(portfolio_status, ensure_ascii=False)}

Create professional Thai report."""
            
            response = self.claude_call(system_prompt, user_message, "เจน")
            
            report = {
                "timestamp": datetime.now().isoformat(),
                "summary": response,
                "total_stocks": len(analysis_results),
                "buy_signals": sum(1 for a in analysis_results.values() if a.get('signal') == 'BUY'),
                "sell_signals": sum(1 for a in analysis_results.values() if a.get('signal') == 'SELL'),
            }
            
            self.log_action("เจน", "Report generated", "SUCCESS")
            return report
            
        except Exception as e:
            self.log_action("เจน", f"Report generation failed: {str(e)}", "ERROR")
            raise

    # ==================== AGENT 6: นน (QA Manager Check) ====================
    def nan_qa_check(self, analysis_results, report):
        """นน: ตรวจสอบคุณภาพก่อนส่ง (PASS/REJECT)"""
        self.log_action("นน", "QA checking...", "INFO")

        try:
            system_prompt = """You are นน (Nan), QA Manager.
Review the analysis and report:
1. Data consistency
2. Logic soundness
3. Report quality
4. Risk assessment

Return JSON:
{
"status": "PASS" or "REJECT",
"issues": [],
"approval_reason": "..."
}"""

            raw_report = report.get('summary', '')
            clean_report_text = re.sub(r'<style[^>]*>.*?</style>', '', raw_report, flags=re.DOTALL)
            clean_report_text = re.sub(r'<[^>]+>', ' ', clean_report_text)
            clean_report_text = re.sub(r'\s+', ' ', clean_report_text).strip()

            # ✅ ส่งเฉพาะ field ที่ นน ต้องการจริง ๆ (ไม่ส่ง full object รวม HTML ด้วย)
            # เพื่อลด token ที่ใช้และป้องกัน context overflow
            qa_summary = {
                ticker: {
                    "signal": data.get("signal"),
                    "confidence": data.get("confidence"),
                    "s1": data.get("s1"),
                    "s2": data.get("s2"),
                    "s3": data.get("s3"),
                    "reasoning": data.get("reasoning"),
                    "validation": data.get("validation", {}).get("recommendation")
                }
                for ticker, data in analysis_results.items()
            }

            user_message = f"""QA Review:
Analysis Summary: {json.dumps(qa_summary, ensure_ascii=False)}
Report Content: {clean_report_text[:3000]}

Check if everything is correct and consistent."""

            response = self.claude_call(system_prompt, user_message, "นน")

            try:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                json_str = response[json_start:json_end]
                qa_result = json.loads(json_str)
            except json.JSONDecodeError:
                # ✅ ไม่ auto-PASS แบบหลอกๆ — QA จริงๆ ทำไม่สำเร็จ ต้อง REJECT เพื่อความปลอดภัย
                self.log_action("นน", "Could not parse QA response JSON — defaulting to REJECT for safety", "WARNING")
                qa_result = {
                    "status": "REJECT",
                    "issues": ["QA response could not be parsed; QA was not actually performed"],
                    "approval_reason": "Auto-rejected: unparseable QA response"
                }
        except Exception as e:
            self.log_action("นน", f"QA check failed: {str(e)}", "ERROR")
            # ✅ ไม่ auto-PASS แบบหลอกๆ — error ระหว่าง QA ต้อง REJECT เพื่อความปลอดภัย
            return {
                "status": "REJECT",
                "issues": [f"QA call failed: {str(e)}"],
                "approval_reason": "Auto-rejected: QA system error"
            }

        self.log_action("นน", f"QA Status: {qa_result.get('status', 'PASS')}", "INFO")
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
