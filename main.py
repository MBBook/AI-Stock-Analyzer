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


def _keepalive_ping():
    """Ping /health ตัวเองทุก 10 นาที ป้องกัน Render kill dyno กลางคัน"""
    import time
    host = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:8000").rstrip("/")
    while True:
        time.sleep(600)  # 10 นาที
        with _job_lock:
            if _job["status"] != "running":
                break
        try:
            requests.get(f"{host}/health", timeout=10)
            print("[KEEPALIVE] Ping sent — dyno ยังตื่นอยู่")
        except Exception as e:
            print(f"[KEEPALIVE] Ping failed: {e}")


def _run_workflow_bg(stocks: list, include_weekend: bool):
    """รัน workflow ใน background thread แล้วเก็บผลใน _job"""
    # ===== KEEPALIVE: ป้องกัน Render sleep กลางคัน =====
    keepalive = threading.Thread(target=_keepalive_ping, daemon=True)
    keepalive.start()

    try:
        result = orchestrator.run_workflow(stocks=stocks, include_weekend=include_weekend)
        wf_status = result.get("status", "UNKNOWN")
        qa        = result.get("qa_result") or {}
        qa_status = qa.get("status", "N/A")
        bkk       = datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M")

        with _job_lock:
            _job["status"] = "completed"
            _job["finished_at"] = datetime.utcnow().isoformat()
            _job["result"] = {
                "workflow_status": wf_status,
                "qa_result": qa,
                "report": result.get("report"),
            }

        # แยก notification ตาม workflow status
        if wf_status == "BUDGET_EXCEEDED":
            msg = (
                f"💰 Budget หมดวันนี้ — ข้ามการวิเคราะห์\n"
                f"⏰ {bkk} (Bangkok)\n"
                f"📊 หุ้น: {len(stocks)} ตัว"
            )
        elif wf_status == "ABORTED":
            msg = (
                f"⚠️ Workflow ABORTED — ข้อมูลไม่ครบ\n"
                f"⏰ {bkk} (Bangkok)"
            )
        else:
            # COMPLETE หรือ REJECTED
            report     = result.get("report", {}) or {}
            buy_count  = report.get("buy_signals", 0)
            hold_count = report.get("hold_signals", 0)
            sell_count = report.get("sell_signals", 0)
            signal_line = f"📈 BUY: {buy_count}  ⚖️ HOLD: {hold_count}  📉 SELL: {sell_count}"

            icon = "✅" if wf_status == "COMPLETE" else "❌"
            msg = (
                f"{icon} AI Stock Analysis เสร็จแล้ว\n"
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
    # ===== DB MIGRATION: เพิ่ม column ใหม่ที่ยังไม่มีใน PostgreSQL =====
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            conn.execute(text(
                "ALTER TABLE stocks ADD COLUMN IF NOT EXISTS at_new_high BOOLEAN DEFAULT FALSE"
            ))
            conn.execute(text(
                "ALTER TABLE stocks ADD COLUMN IF NOT EXISTS at_new_low BOOLEAN DEFAULT FALSE"
            ))
            conn.commit()
            print("[MIGRATION] at_new_high / at_new_low columns ready")
        except Exception as e:
            print(f"[MIGRATION] {e}")
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS nik_suggestions (
                    id SERIAL PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT NOW(),
                    summary TEXT NOT NULL,
                    diff_text TEXT NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    error_message TEXT,
                    applied_at TIMESTAMP
                )
            """))
            conn.commit()
            print("[MIGRATION] nik_suggestions table ready")
        except Exception as e:
            print(f"[MIGRATION] {e}")
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS hourly_cache (
                    id SERIAL PRIMARY KEY,
                    ticker VARCHAR(20) NOT NULL,
                    price FLOAT,
                    week52_high FLOAT,
                    week52_low FLOAT,
                    pe_ratio FLOAT,
                    market_cap FLOAT,
                    source VARCHAR(20),
                    at_new_high BOOLEAN DEFAULT FALSE,
                    at_new_low BOOLEAN DEFAULT FALSE,
                    fetched_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_hourly_cache_ticker ON hourly_cache (ticker)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_hourly_cache_fetched_at ON hourly_cache (fetched_at)"
            ))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS news_cache (
                    id SERIAL PRIMARY KEY,
                    ticker VARCHAR(20) NOT NULL,
                    news_json TEXT,
                    news_count INTEGER DEFAULT 0,
                    fetched_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_news_cache_ticker ON news_cache (ticker)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_news_cache_fetched_at ON news_cache (fetched_at)"
            ))
            conn.commit()
            print("[MIGRATION] hourly_cache + news_cache tables ready")
        except Exception as e:
            print(f"[MIGRATION] {e}")
    setup_scheduler()

@app.on_event("shutdown")
async def shutdown():
    shutdown_scheduler()

# ===== ROUTES =====

@app.post("/prefetch")
async def prefetch_prices(background_tasks: BackgroundTasks):
    """Pre-fetch ราคาหุ้นทั้งหมดผ่าน Finnhub → เก็บใน HourlyCache
    เรียกโดย GitHub Actions ทุกชั่วโมง Mon-Fri 09:00-21:00 Bangkok
    ที่ 22:00 นัตตี้จะอ่านจาก cache → ประหยัดเวลา ~10 นาที"""
    def _run_prefetch():
        try:
            db = __import__("database").SessionLocal()
            from models import Stock
            stocks = [s.ticker for s in db.query(Stock).all()]
            db.close()
            if not stocks:
                print("[PREFETCH] No stocks in DB — skipping")
                return
            print(f"[PREFETCH] Starting pre-fetch for {len(stocks)} tickers...")
            orchestrator.natty_prefetch_prices(stocks)
            print("[PREFETCH] Prices done — starting news pre-fetch...")
            orchestrator.natty_prefetch_news(stocks)
            print("[PREFETCH] All done (prices + news)")
        except Exception as e:
            print(f"[PREFETCH] Error: {e}")

    background_tasks.add_task(_run_prefetch)
    return {"status": "prefetch_started", "message": "Pre-fetching prices in background"}

@app.get("/prefetch/status")
async def prefetch_status():
    """ดูจำนวน tickers ใน HourlyCache + NewsCache และเวลา fetch ล่าสุด"""
    try:
        from models import HourlyCache, NewsCache
        from sqlalchemy import func
        db_s = __import__("database").SessionLocal()
        price_count  = db_s.query(func.count(HourlyCache.id)).scalar() or 0
        price_latest = db_s.query(func.max(HourlyCache.fetched_at)).scalar()
        news_count   = db_s.query(func.count(NewsCache.id)).scalar() or 0
        news_latest  = db_s.query(func.max(NewsCache.fetched_at)).scalar()
        db_s.close()
        return {
            "price_cache":  {"entries": price_count, "latest_fetch": price_latest.isoformat() if price_latest else None},
            "news_cache":   {"entries": news_count,  "latest_fetch": news_latest.isoformat()  if news_latest  else None},
        }
    except Exception as e:
        return {"error": str(e)}

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
                "at_new_high": s.at_new_high or False,
                "at_new_low":  s.at_new_low or False,
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


@app.post("/workflow/resume")
async def resume_workflow(db: Session = Depends(get_db)):
    """รันเฉพาะ ticker ที่ยังไม่ได้วิเคราะห์วันนี้ — ใช้โดย GitHub Actions ทุก 15 นาที 22:15-23:45"""
    with _job_lock:
        if _job["status"] == "running":
            return {"status": "already_running", "message": "Workflow is already running"}

    # ถ้า workflow วันนี้ BUDGET_EXCEEDED หรือ COMPLETE แล้ว → ไม่ต้อง resume
    today = datetime.now().date()
    try:
        from models import WorkflowLog
        last_log = db.query(WorkflowLog).order_by(WorkflowLog.timestamp.desc()).first()
        if last_log and last_log.timestamp.date() == today:
            if last_log.status in ("BUDGET_EXCEEDED", "COMPLETE", "ABORTED"):
                return {
                    "status": "skipped",
                    "reason": f"Today's workflow already ended with status: {last_log.status}"
                }
    except Exception:
        pass  # ถ้าเช็ค log ไม่ได้ → ให้รันต่อ (fail-open)
    all_stocks = db.query(Stock).all()
    pending = [s.ticker for s in all_stocks
               if not s.updated_at or s.updated_at.date() < today]

    if not pending:
        return {"status": "already_complete", "message": "All stocks analyzed today"}

    with _job_lock:
        job_id = str(uuid.uuid4())[:8]
        _job["job_id"]      = job_id
        _job["status"]      = "running"
        _job["started_at"]  = datetime.utcnow().isoformat()
        _job["finished_at"] = None
        _job["result"]      = None
        _job["error"]       = None

    include_weekend = datetime.now().weekday() == 0
    t = threading.Thread(
        target=_run_workflow_bg,
        args=(pending, include_weekend),
        daemon=True
    )
    t.start()

    return {
        "status": "resumed",
        "job_id": job_id,
        "pending_stocks": len(pending),
        "tickers": pending,
        "message": f"Resuming workflow for {len(pending)} remaining stocks"
    }


@app.get("/nik/suggestions")
async def get_nik_suggestions(db: Session = Depends(get_db)):
    """ดู suggestion ของนิก 10 รายการล่าสุด"""
    from models import NikSuggestion
    from sqlalchemy import desc
    items = db.query(NikSuggestion).order_by(desc(NikSuggestion.created_at)).limit(10).all()
    return {
        "count": len(items),
        "pending_count": sum(1 for i in items if i.status == "pending"),
        "suggestions": [
            {
                "id":            i.id,
                "created_at":    i.created_at,
                "summary":       i.summary,
                "diff_text":     i.diff_text,
                "status":        i.status,
                "error_message": i.error_message,
                "applied_at":    i.applied_at,
            }
            for i in items
        ]
    }


@app.get("/workflow/history")
async def get_workflow_history(limit: int = 30, db: Session = Depends(get_db)):
    """ดู workflow run history + cost จาก DB (ล่าสุดก่อน)"""
    from models import WorkflowLog
    from sqlalchemy import desc
    logs = db.query(WorkflowLog).order_by(desc(WorkflowLog.timestamp)).limit(limit).all()
    total_cost = sum(l.cost_usd or 0 for l in logs)
    return {
        "count": len(logs),
        "total_cost_usd": round(total_cost, 4),
        "runs": [
            {
                "id":              l.id,
                "timestamp":       l.timestamp,
                "status":          l.status,
                "stocks_analyzed": l.stocks_analyzed,
                "buy_signals":     l.buy_signals,
                "hold_signals":    l.hold_signals,
                "sell_signals":    l.sell_signals,
                "cost_usd":        l.cost_usd,
            }
            for l in logs
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
