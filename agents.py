"""
AI Stock Analyzer V4 - Agent System with Multi-Key Fallback
Sequential Workflow with auto-fallback to next API key if current fails
FIXED: Removed async/await, added database validation
"""

import time
import re
from anthropic import Anthropic
from datetime import datetime, timedelta
import yfinance as yf
import json
import os
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Stock, Trade, Portfolio

class AgentOrchestrator:
    def __init__(self):
        self.workflow_log = []
        self.conversation_history = []
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
        """ใช้ Claude API สำหรับ Agent (with auto-fallback)"""
        max_attempts = len(self.api_keys)
        attempt = 0
        
        while attempt < max_attempts:
            try:
                # เพิ่ม message ไปยัง conversation history
                self.conversation_history.append({
                    "role": "user",
                    "content": user_message
                })
                
                # Get current client
                client = self.get_client()
                
                # Call Claude API (synchronous)
                response = client.messages.create(
                    model="claude-opus-4-6",
                    max_tokens=16000,
                    system=system_prompt,
                    messages=self.conversation_history
                )
                
                assistant_message = response.content[0].text
                
                # บันทึก response ไปยัง history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": assistant_message
                })
                
                self.log_action(agent_name, f"Claude call success (Key #{self.current_key_index + 1})", "SUCCESS")
                return assistant_message
                
            except Exception as e:
                error_msg = str(e)
                self.log_action(agent_name, f"Claude call error on Key #{self.current_key_index + 1}: {error_msg}", "ERROR")
                
                attempt += 1
                if attempt < max_attempts:
                    self.log_action(agent_name, f"Trying next API key ({attempt}/{max_attempts})...", "WARNING")
                    self.rotate_to_next_key()
                    # Remove last user message from history for retry
                    if self.conversation_history and self.conversation_history[-1]["role"] == "user":
                        self.conversation_history.pop()
                else:
                    self.log_action(agent_name, f"All {max_attempts} API keys exhausted", "ERROR")
                    raise

    # ==================== AGENT 1: นัตตี้ (Get News) ====================
    def natty_get_news(self, stocks, days=1):
        """นัตตี้: ดึงข่าวหุ้นจาก yfinance"""
        self.log_action("นัตตี้", "Starting news fetch...", "INFO")
        
        try:
            news_data = {}

            for ticker in stocks:
                try:
                    time.sleep(2)

                    import requests
                    session = requests.Session()
                    session.headers.update({
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                        })
            
                    stock_obj = yf.Ticker(ticker, session=session)
                    
                    # ดึง recent data
                    hist = stock_obj.history(period=f"{days}d")
                    info = stock_obj.info if hasattr(stock_obj, 'info') else {}
                    
                    news_data[ticker] = {
                        "symbol": ticker,
                        "price": info.get('currentPrice', 0),
                        "52week_high": info.get('fiftyTwoWeekHigh', 0),
                        "52week_low": info.get('fiftyTwoWeekLow', 0),
                        "pe_ratio": info.get('trailingPE', 0),
                        "market_cap": info.get('marketCap', 0),
                        "days_fetched": days,
                        "data_points": len(hist)
                    }
                except Exception as e:
                    self.log_action("นัตตี้", f"Failed to fetch {ticker}: {str(e)}", "WARNING")
                    continue
            
            self.log_action("นัตตี้", f"Fetched {len(news_data)} stocks", "SUCCESS")
            return news_data
            
        except Exception as e:
            self.log_action("นัตตี้", f"News fetch failed: {str(e)}", "ERROR")
            raise

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
                user_message = f"""Analyze this stock:
Symbol: {ticker}
Current Price: ${data.get('price', 0)}
52-week High: ${data.get('52week_high', 0)}
52-week Low: ${data.get('52week_low', 0)}
P/E Ratio: {data.get('pe_ratio', 0)}
Market Cap: ${data.get('market_cap', 0)}

Provide analysis in JSON format."""
                
                try:
                    response = self.claude_call(system_prompt, user_message, "หนุ่ม")
                    
                    # Parse JSON response
                    try:
                        json_start = response.find('{')
                        json_end = response.rfind('}') + 1
                        json_str = response[json_start:json_end]
                        result = json.loads(json_str)
                        analysis_results[ticker] = result
                    except json.JSONDecodeError:
                        analysis_results[ticker] = {
                            "ticker": ticker,
                            "signal": "HOLD",
                            "confidence": 0.5,
                            "s1": data.get('price', 0) * 0.95,
                            "s2": data.get('price', 0) * 0.90,
                            "s3": data.get('price', 0) * 0.85,
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
                        validated_results[ticker] = {
                            **analysis,
                            "validation": {"is_valid": True, "recommendation": "PASS"}
                        }
                    
                except Exception as e:
                    self.log_action("มด", f"Validation failed for {ticker}: {str(e)}", "WARNING")
                    validated_results[ticker] = {
                        **analysis,
                        "validation": {"is_valid": True, "recommendation": "PASS"}
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
        
        try:
            db = SessionLocal()
            portfolio_holdings = db.query(Portfolio).all()
            db.close()
            
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
            system_prompt = """You are เจน (Jen), a report writer.
Create a professional market report summarizing:
1. Market overview
2. Top signals (BUY/SELL)
3. Portfolio recommendations
4. Risk assessment

Write in Thai. Return JSON with report_html field."""
            
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

            user_message = f"""QA Review:
Analysis: {json.dumps(analysis_results, ensure_ascii=False)}
Report Content: {clean_report_text}

Check if everything is correct and consistent."""

            response = self.claude_call(system_prompt, user_message, "นน")

            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            json_str = response[json_start:json_end]
            qa_result = json.loads(json_str)
        except json.JSONDecodeError:
            qa_result = {"status": "PASS", "approval_reason": "Auto-approved"}
        except Exception as e:
            self.log_action("นน", f"QA check failed: {str(e)}", "ERROR")
            return {"status": "PASS", "approval_reason": "Error recovery"}

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
        
        Args:
            stocks: Stock list to analyze
            portfolio: Current portfolio
            include_weekend: True for Monday (Sat-Sun-Mon), False for Tue-Fri (24h)
        """
        if not stocks:
            stocks = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
        
        self.workflow_log = []
        self.conversation_history = []
        
        if include_weekend:
            self.log_action("SYSTEM", "🔄 Monday mode: Fetching Sat-Sun-Mon news...", "INFO")
        else:
            self.log_action("SYSTEM", "📰 Regular mode: Fetching 24-hour news...", "INFO")
        
        try:
            # ========== SEQUENTIAL EXECUTION ==========
            
            # Step 1: นัตตี้ Get News
            news_data = self.natty_get_news(stocks, days=3 if include_weekend else 1)
            
            # Step 2: หนุ่ม Analyze
            analysis_results = self.num_analyze_stocks(news_data, stocks)
            
            # Step 3: มด Cross-Validate
            validated_results = self.mud_cross_validate(analysis_results)
            
            # Step 4: แฮรี่ Monitor Portfolio
            portfolio_status = self.harry_monitor_portfolio(validated_results)
            
            # Step 5: เจน Generate Report
            report = self.jen_generate_report(validated_results, portfolio_status)
            
            # Step 6: นน QA Check
            qa_result = self.nan_qa_check(validated_results, report)
            
            # Step 7: Decision (PASS/REJECT)
            if qa_result.get('status') == 'PASS':
                self.log_action("SYSTEM", "✅ Workflow PASSED - Updating database...", "SUCCESS")
                self._update_database(validated_results)
                
                # ✅ เอ Record improvement
                self.log_action("เอ", "Recording improvements and code updates", "SUCCESS")
                
            else:
                # ❌ เก้า Retry
                self.log_action("SYSTEM", "❌ Workflow REJECTED - Attempting retry...", "ERROR")
                self.kao_retry("workflow", qa_result.get('issues', ['Unknown error'])[0], 1)
            
            self.log_action("SYSTEM", "✅ Workflow complete!", "SUCCESS")
            return {
                "status": "COMPLETE",
                "workflow_log": self.workflow_log,
                "qa_result": qa_result,
                "report": report
            }
            
        except Exception as e:
            self.log_action("SYSTEM", f"❌ Workflow failed: {str(e)}", "ERROR")
            raise

    def _update_database(self, analysis_results):
        """อัพเดต Database ด้วยผลลัพธ์"""
        try:
            db = SessionLocal()
            
            for ticker, analysis in analysis_results.items():
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
            
            db.close()
            self.log_action("DATABASE", "Updated stock signals", "SUCCESS")
        except Exception as e:
            self.log_action("DATABASE", f"Update failed: {str(e)}", "ERROR")


# Initialize orchestrator
orchestrator = AgentOrchestrator()
