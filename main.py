from fastapi import FastAPI, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
import threading
import uuid
import requests
from dotenv import load_dotenv
from database import get_db, engine
from models import Base, Stock, Trade, Portfolio
from datetime import datetime, timezone, timedelta
from scheduler import setup_scheduler, shutdown_scheduler
from agents import orchestrator

load_dotenv()

# ===== LINE NOTIFICATION =====

def _send_line_notification(message: str):
    """ส่ง LINE push message ไปหา user"""
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    user_id = os.getenv("LINE_USER_ID", "")
    if not token or not user_id:
        print("[LINE] ไม่มี credentials — ข้าม")
        return
    try:
        resp = requests.post(
            "https://api.line.me/v2/bot/message/push",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"to": user_id, "messages": [{"type": "text", "text": message}]},
            timeout=10,
        )
        if resp.status_code == 200:
            print("[LINE] ส่งสำเร็จ")
        else:
            print(f"[LINE] ส่งไม่สำเร็จ: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"[LINE] Error: {e}")

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

# ===== JOB STATE (in-memory) =====
_job: dict = {
    "job_id": None,
    "status": "idle",       # idle | running | completed | error
    "started_at": None,
    "finished_at": None,
    "result": None,
    "error": None,
}
_job_lock = threading.Lock()


def _run_workflow_bg(stocks: list, include_weekend: bool):
    """รัน workflow ใน background thread แล้วเก็บผลใน _job"""
    try:
        result = orchestrator.run_workflow(stocks=stocks, include_weekend=include_weekend)
        qa = result.get("qa_result") or {}
        qa_status = qa.get("status", "N/A")
        bkk = datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M")

        with _job_lock:
            _job["status"] = "completed"
            _job["finished_at"] = datetime.utcnow().isoformat()
            _job["result"] = {
                "workflow_status": result.get("status"),
                "qa_result": qa,
                "report": result.get("report"),
            }

        # นับ signal จาก report (ถ้ามี)
        report = result.get("report", {}) or {}
        summaries = report.get("stock_summaries", []) or []
        buy_count  = sum(1 for s in summaries if s.get("signal") == "BUY")
        hold_count = sum(1 for s in summaries if s.get("signal") == "HOLD")
        sell_count = sum(1 for s in summaries if s.get("signal") == "SELL")
        signal_line = f"📈 BUY: {buy_count}  ⚖️ HOLD: {hold_count}  📉 SELL: {sell_count}" if summaries else ""

        msg = (
            f"✅ AI Stock Analysis เสร็จแล้ว\n"
            f"⏰ {bkk} (Bangkok)\n"
            f"📊 หุ้น: {len(stocks)} ตัว\n"
            f"🎯 QA: {qa_status}"
        )
        if signal_line:
            msg += f"\n{signal_line}"
        _send_line_notification(msg)

    except Exception as e:
        bkk = datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M")
        with _job_lock:
            _job["status"] = "error"
            _job["finished_at"] = datetime.utcnow().isoformat()
            _job["error"] = str(e)

        _send_line_notification(
            f"❌ AI Stock Analysis ล้มเหลว\n"
            f"⏰ {bkk} (Bangkok)\n"
            f"💥 Error: {str(e)[:200]}"
        )


# ===== LIFECYCLE =====

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

# ===== WORKFLOW ENDPOINTS =====

@app.post("/workflow")
async def start_workflow(include_weekend: bool = False, db: Session = Depends(get_db)):
    """เริ่ม workflow ใน background — return ทันที ไม่รอให้เสร็จ"""
    with _job_lock:
        if _job["status"] == "running":
            return {
                "status": "already_running",
                "job_id": _job["job_id"],
                "started_at": _job["started_at"],
                "message": "Workflow is already running. Check GET /workflow/status"
            }

        stocks_list = db.query(Stock).all()
        if not stocks_list:
            return {
                "status": "no_stocks",
                "message": "Add stocks first using POST /stocks",
                "timestamp": datetime.utcnow().isoformat()
            }

        stocks = [s.ticker for s in stocks_list]
        job_id = str(uuid.uuid4())[:8]

        _job["job_id"] = job_id
        _job["status"] = "running"
        _job["started_at"] = datetime.utcnow().isoformat()
        _job["finished_at"] = None
        _job["result"] = None
        _job["error"] = None

    t = threading.Thread(
        target=_run_workflow_bg,
        args=(stocks, include_weekend),
        daemon=True
    )
    t.start()

    return {
        "status": "started",
        "job_id": job_id,
        "stocks_count": len(stocks),
        "started_at": _job["started_at"],
        "message": "Workflow running in background. Poll GET /workflow/status for result."
    }


@app.get("/workflow/status")
async def get_workflow_status():
    """ดูสถานะ workflow ปัจจุบัน"""
    with _job_lock:
        snapshot = dict(_job)

    if snapshot["status"] == "idle":
        return {"status": "idle", "message": "No workflow has been started yet."}

    response = {
        "status": snapshot["status"],
        "job_id": snapshot["job_id"],
        "started_at": snapshot["started_at"],
        "finished_at": snapshot["finished_at"],
    }

    if snapshot["status"] == "completed":
        response["result"] = snapshot["result"]

    if snapshot["status"] == "error":
        response["error"] = snapshot["error"]

    return response


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
