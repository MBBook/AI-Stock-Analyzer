from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv
from database import get_db, engine
from models import Base, Stock, Trade, Portfolio
from datetime import datetime
from scheduler import setup_scheduler, shutdown_scheduler
from agents import orchestrator

load_dotenv()

app = FastAPI(title="AI Stock Analyzer")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# สร้าง tables
Base.metadata.create_all(bind=engine)

@app.on_event("startup")
async def startup():
    setup_scheduler()

@app.on_event("shutdown")
async def shutdown():
    shutdown_scheduler()

# ===== ROUTES =====

@app.get("/")
async def root():
    return {"message": "AI Stock Analyzer API v1", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "ok"}

# Stock Management
@app.post("/stocks")
async def add_stock(ticker: str, db: Session = Depends(get_db)):
    
    ticker = ticker.upper()

    existing = db.query(Stock).filter(Stock.ticker == ticker).first()
    if existing:
        return {"status": "exists", "ticker": ticker}
    
    new_stock = Stock(ticker=ticker)
    db.add(new_stock)
    db.commit()
    db.refresh(new_stock)
    return {"status": "added", "ticker": ticker, "id": new_stock.id}

@app.get("/stocks")
async def get_stocks(db: Session = Depends(get_db)):
    stocks = db.query(Stock).all()
    return {
        "count": len(stocks),
        "stocks": [
            {
                "id": s.id,
                "ticker": s.ticker,
                "signal": s.signal,
                "confidence": s.confidence,
                "price": s.current_price,
                "fair_price": s.fair_price,
                "updated_at": s.updated_at
            }
            for s in stocks
        ]
    }

@app.delete("/stocks/{ticker}")
async def remove_stock(ticker: str, db: Session = Depends(get_db)):
    stock = db.query(Stock).filter(Stock.ticker == ticker).first()
    if not stock:
        return {"status": "not_found", "ticker": ticker}
    
    db.delete(stock)
    db.commit()
    return {"status": "deleted", "ticker": ticker}

# Trade Updates
@app.post("/trade-update")
async def update_trade(ticker: str, action: str, shares: int, price: float, db: Session = Depends(get_db)):
    trade = Trade(ticker=ticker, action=action, shares=shares, price=price)
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return {"status": "recorded", "id": trade.id, "ticker": ticker}

# Portfolio
@app.get("/portfolio")
async def get_portfolio(db: Session = Depends(get_db)):
    holdings = db.query(Portfolio).all()
    total_value = sum(h.current_value for h in holdings) if holdings else 0
    total_cost = sum(h.avg_cost * h.shares for h in holdings) if holdings else 0
    total_gain = total_value - total_cost
    
    return {
        "total_value": total_value,
        "total_cost": total_cost,
        "total_gain": total_gain,
        "holdings_count": len(holdings),
        "holdings": [
            {
                "ticker": h.ticker,
                "shares": h.shares,
                "avg_cost": h.avg_cost,
                "current_value": h.current_value,
                "gain": h.total_gain
            }
            for h in holdings
        ]
    }

# Analysis
@app.get("/analysis/latest")
async def get_latest_analysis(db: Session = Depends(get_db)):
    stocks = db.query(Stock).all()
    return {
        "timestamp": datetime.utcnow(),
        "stocks_tracked": len(stocks),
        "buy_signals": len([s for s in stocks if s.signal == "BUY"]),
        "hold_signals": len([s for s in stocks if s.signal == "HOLD"]),
        "sell_signals": len([s for s in stocks if s.signal == "SELL"]),
        "workflow_status": "pending"
    }

# ===== WORKFLOW ENDPOINT =====

@app.post("/workflow")
async def run_workflow(include_weekend: bool = False, db: Session = Depends(get_db)):
    """Run complete agent workflow
    
    Args:
        include_weekend: True for Monday (Sat-Sun-Mon), False for Tue-Fri (24h)
    """
    try:
        # Get all stocks from database
        stocks_list = db.query(Stock).all()
        
        if not stocks_list:
            return {
                "status": "no_stocks",
                "message": "Add stocks first using POST /stocks",
                "timestamp": datetime.utcnow()
            }
        
        stocks = [s.ticker for s in stocks_list]
        
        # Run workflow
        result = await orchestrator.run_workflow(
            stocks=stocks,
            include_weekend=include_weekend
        )
        
        return {
            "status": "success",
            "workflow_log": result.get("workflow_log"),
            "qa_result": result.get("qa_result"),
            "report": result.get("report"),
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "workflow_log": orchestrator.workflow_log,
            "timestamp": datetime.utcnow()
        }

# ===== WORKFLOW LOGS ENDPOINT =====

@app.get("/workflow/logs")
async def get_workflow_logs():
    """Get latest workflow logs"""
    return {
        "logs": orchestrator.workflow_log,
        "timestamp": datetime.utcnow()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)