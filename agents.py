import anthropic
import yfinance as yf
from datetime import datetime
import os

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

class AgentOrchestrator:
    def __init__(self):
        self.model = "claude-opus-4-6"
        self.workflow_log = []
    
    async def natty_get_news(self, stocks: list) -> dict:
        """นัตตี้: Fetch and analyze news for stocks"""
        stocks_str = ", ".join(stocks)
        prompt = f"""
        Analyze latest news for these stocks: {stocks_str}
        Return sentiment (positive/negative/neutral) for each.
        Format: {{'STOCK': 'sentiment', ...}}
        """
        response = client.messages.create(
            model=self.model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        self.workflow_log.append({"agent": "นัตตี้", "status": "done"})
        return response.content[0].text

    async def hnum_analyze_stock(self, stocks: list, news: str) -> dict:
        """หนุ่ม: Analyze stocks using news + yfinance"""
        price_data = {}
        for stock in stocks:
            ticker = yf.Ticker(stock)
            info = ticker.info
            price_data[stock] = {
                "price": info.get("currentPrice", 0),
                "market_cap": info.get("marketCap", 0)
            }
        
        prompt = f"""
        Stock prices: {price_data}
        News sentiment: {news}
        Provide BUY/HOLD/SELL signal for each stock with confidence.
        Format: {{'STOCK': {{'signal': 'BUY', 'confidence': 0.85}}, ...}}
        """
        response = client.messages.create(
            model=self.model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        self.workflow_log.append({"agent": "หนุ่ม", "status": "done"})
        return response.content[0].text

    async def mud_cross_validate(self, news: str, signals: str) -> dict:
        """มด: Cross-validate news sentiment vs stock signals"""
        prompt = f"""
        News analysis: {news}
        Stock signals: {signals}
        Cross-validate: Do they align?
        Flag conflicts and confidence scores.
        """
        response = client.messages.create(
            model=self.model,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        self.workflow_log.append({"agent": "มด", "status": "done"})
        return response.content[0].text

    async def harry_monitor_portfolio(self, portfolio: dict) -> dict:
        """แฮรี่: Monitor portfolio status"""
        prompt = f"""
        Current portfolio: {portfolio}
        Check portfolio health, allocation, risk.
        Return: {{total_value, total_gain, alerts}}
        """
        response = client.messages.create(
            model=self.model,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        self.workflow_log.append({"agent": "แฮรี่", "status": "done"})
        return response.content[0].text

    async def jen_generate_report(self, all_data: str) -> dict:
        """เจน: Generate daily report"""
        prompt = f"""
        Generate investment report from:
        {all_data}
        Include: Summary, Signals, Portfolio Status, Risks
        """
        response = client.messages.create(
            model=self.model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        self.workflow_log.append({"agent": "เจน", "status": "done"})
        return response.content[0].text

    async def nun_qa_check(self, report: str) -> dict:
        """นน: QA Manager - Validate report quality"""
        prompt = f"""
        QA Check report:
        {report}
        Issues: (list any problems)
        Quality Score: 0-100
        Recommendation: PASS or REJECT
        """
        response = client.messages.create(
            model=self.model,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        
        result = response.content[0].text
        self.workflow_log.append({"agent": "นน", "status": "done", "result": result})
        
        # Check if PASS or REJECT
        if "PASS" in result.upper():
            return {"status": "PASS", "data": report}
        else:
            return {"status": "REJECT", "reason": result}

    async def run_workflow(self, stocks: list = None, portfolio: dict = None, include_weekend: bool = False):
    """Execute complete workflow - SEQUENTIAL
    
    Args:
        stocks: Stock list to analyze
        portfolio: Current portfolio
        include_weekend: True for Monday (Sat-Sun-Mon), False for Tue-Fri (24h)
    """
    if not stocks:
        stocks = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
    
    if include_weekend:
        print("🔄 Monday mode: Fetching Sat-Sun-Mon news...")
    else:
        print("📰 Regular mode: Fetching 24-hour news...")
        
        print(f"[{datetime.now()}] Starting workflow...")
        
        try:
            # Sequential execution
            news = await self.natty_get_news(stocks)
            print("✓ นัตตี้ done")
            
            signals = await self.hnum_analyze_stock(stocks, news)
            print("✓ หนุ่ม done")
            
            validated = await self.mud_cross_validate(news, signals)
            print("✓ มด done")
            
            port_status = await self.harry_monitor_portfolio(portfolio or {})
            print("✓ แฮรี่ done")
            
            all_data = f"News: {news}\nSignals: {signals}\nValidation: {validated}\nPortfolio: {port_status}"
            report = await self.jen_generate_report(all_data)
            print("✓ เจน done")
            
            qa_result = await self.nun_qa_check(report)
            print(f"✓ นน done - {qa_result['status']}")
            
            if qa_result['status'] == "PASS":
                print("✓ Workflow PASSED - Updating dashboard...")
                # Update dashboard with report
                return {"status": "success", "report": qa_result['data']}
            else:
                print(f"✗ Workflow REJECTED - {qa_result['reason']}")
                # เก้า would retry here
                return {"status": "rejected", "reason": qa_result['reason']}
                
        except Exception as e:
            print(f"✗ Workflow error: {e}")
            return {"status": "error", "message": str(e)}

# Initialize
orchestrator = AgentOrchestrator()
