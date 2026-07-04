from fastapi import FastAPI, Depends, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
import threading
import uuid
import requests
import base64
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

# ✅ เพิ่ม 2026-07-02 (Defect #14 ต่อเนื่อง): lock กัน /prefetch รันซ้อนกัน
# เดิม endpoint นี้ไม่มี lock เลย — keepalive.yml Step 3 self-heal ยิงทุก 10 นาทีถ้า cache stale
# แต่ prefetch 1 รอบใช้เวลาจริง ~11-13 นาที (ดึงข่าวทีละหุ้น sleep 20s) ทำให้ทุกๆ 10 นาทีที่ cache
# ยังไม่ทันอัพเดต (เพราะรอบก่อนยังไม่เสร็จ) จะโดนยิงซ้อนอีกรอบ ซ้อนกันเรื่อยๆ ทั้งวัน แย่งกัน fetch
# ticker เดียวกัน ชน rate limit จนไม่มีรอบไหนเสร็จสมบูรณ์เลย (คือสาเหตุที่แท้จริงที่ cache ค้าง 22+ ชม.)
_prefetch_running = False
_prefetch_lock = threading.Lock()


def _keepalive_ping():
    """Ping /health ตัวเองทุก 10 นาที ป้องกัน Render kill dyno กลางคัน — เฉพาะช่วง workflow กำลังรัน"""
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


def _self_ping_forever():
    """Ping /health ตัวเองทุก 8 นาที ตลอดชีวิตของ process (เริ่มตั้งแต่ startup)
    เพิ่ม 2026-07-01: กัน Render free-tier sleep (>15 นาที idle) โดยไม่ต้องพึ่งแค่
    GitHub Actions Keepalive (cron ภายนอกอาจ delay/ข้ามรอบได้เอง) — thread นี้เป็น
    in-process loop ใช้แค่ time.sleep() ไม่มี dependency ต่อ scheduler ภายนอกเลย
    ทำงานคู่ขนานกับ GitHub Actions Keepalive เดิม (ไม่ได้แทนที่ — เป็น backup ซ้อนอีกชั้น)"""
    import time
    time.sleep(30)  # รอให้ startup migration เสร็จก่อนเริ่ม ping รอบแรก
    host = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:8000").rstrip("/")
    while True:
        try:
            resp = requests.get(f"{host}/health", timeout=15)
            print(f"[SELF-PING] {resp.status_code} — dyno ยังตื่นอยู่ (in-process, ไม่พึ่ง GitHub Actions)")
        except Exception as e:
            print(f"[SELF-PING] Ping failed (จะลองใหม่รอบถัดไป): {e}")
        time.sleep(480)  # 8 นาที — เผื่อ margin ก่อนถึง Render sleep threshold ที่ 15 นาที


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
            # ✅ เพิ่ม 2026-07-03: reasoning ต่อหุ้น (หนุ่มสร้างอยู่แล้วทุกคืนแต่ไม่เคย persist)
            # + full_report ของ workflow_logs (รายงานตลาดฉบับเต็มที่เจนเขียน เดิมอยู่แค่ใน memory)
            conn.execute(text(
                "ALTER TABLE stocks ADD COLUMN IF NOT EXISTS reasoning TEXT"
            ))
            conn.execute(text(
                "ALTER TABLE workflow_logs ADD COLUMN IF NOT EXISTS full_report TEXT"
            ))
            conn.commit()
            print("[MIGRATION] stocks.reasoning / workflow_logs.full_report columns ready")
        except Exception as e:
            print(f"[MIGRATION] {e}")
        try:
            # ✅ แก้ 2026-07-03: trades.shares / portfolio.shares เดิมเป็น INTEGER
            # MBBook ซื้อหุ้นเศษส่วน (fractional shares) ผ่าน Dime app เช่น 0.1874433 หุ้น
            # ต้องแปลงเป็น FLOAT ไม่งั้นข้อมูลถูกปัดเป็น 0 หมด (ตาราง trades/portfolio ว่างอยู่แล้ว
            # ตอนแก้ครั้งนี้ — ALTER TYPE ปลอดภัย ไม่มีข้อมูลเก่าให้เสีย)
            conn.execute(text(
                "ALTER TABLE trades ALTER COLUMN shares TYPE FLOAT"
            ))
            conn.execute(text(
                "ALTER TABLE portfolio ALTER COLUMN shares TYPE FLOAT"
            ))
            conn.commit()
            print("[MIGRATION] trades.shares / portfolio.shares → FLOAT ready")
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
        try:
            # ✅ เพิ่ม 2026-07-04: signal_history — insert-only ทุกคืนต่อหุ้น เก็บสัญญาณ+ราคา
            # ณ เวลานั้น เพื่อคำนวณ ROI (win rate + avg return) ย้อนหลังได้ตอนครบ 60 วัน
            # (Phase 1 evaluation ตาม Blueprint.md) — ต่างจาก stocks ที่ถูกทับทุกคืน
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS signal_history (
                    id SERIAL PRIMARY KEY,
                    ticker VARCHAR(20) NOT NULL,
                    signal VARCHAR(10) NOT NULL,
                    confidence FLOAT DEFAULT 0.0,
                    price FLOAT NOT NULL,
                    timestamp TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_signal_history_ticker ON signal_history (ticker)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_signal_history_timestamp ON signal_history (timestamp)"
            ))
            conn.commit()
            print("[MIGRATION] signal_history table ready")
        except Exception as e:
            print(f"[MIGRATION] {e}")
        try:
            # ✅ เพิ่ม 2026-07-04: portfolio_snapshots — insert-only ทุกคืน เก็บมูลค่ารวม +
            # ต้นทุนรวมของพอร์ตจริง เพื่อคำนวณผลตอบแทนสะสม (ไม่มีเส้นตาย เป้า 13%) แยกจาก win rate
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                    id SERIAL PRIMARY KEY,
                    total_value FLOAT NOT NULL,
                    total_cost FLOAT NOT NULL,
                    timestamp TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_portfolio_snapshots_timestamp ON portfolio_snapshots (timestamp)"
            ))
            conn.commit()
            print("[MIGRATION] portfolio_snapshots table ready")
        except Exception as e:
            print(f"[MIGRATION] {e}")

    # ⛔ ปิด APScheduler แล้ว 2026-07-02 (Defect #14) — หยุดยิง prefetch เงียบๆ นาน 22+ ชม.
    # (รอบ 09:05-13:05 วันที่ 2 ก.ค. ขาดหมด) โดยไม่มี error/log ให้ debug เลย เพราะเป็น
    # in-process scheduler ผูกกับ process เดียว ตรวจสอบยากกว่า GitHub Actions มาก
    # สลับกลับไปใช้ AI_Stocks_Prefetch (GitHub Actions, เห็น run history ชัดเจน) เป็นระบบหลักแทน
    # setup_scheduler()

    # ===== SELF-PING: กัน Render sleep ตลอดชีวิต process ไม่พึ่ง GitHub Actions =====
    threading.Thread(target=_self_ping_forever, daemon=True).start()
    print("✅ Self-ping thread started — ping ตัวเองทุก 8 นาที (backup ซ้อน GitHub Actions Keepalive)")

@app.on_event("shutdown")
async def shutdown():
    shutdown_scheduler()

# ===== ROUTES =====

@app.post("/prefetch")
async def prefetch_prices(background_tasks: BackgroundTasks):
    """Pre-fetch ราคาหุ้นทั้งหมดผ่าน Finnhub → เก็บใน HourlyCache
    เรียกโดย GitHub Actions ทุกชั่วโมง Mon-Fri 09:00-21:00 Bangkok
    ที่ 22:00 นัตตี้จะอ่านจาก cache → ประหยัดเวลา ~10 นาที"""
    global _prefetch_running

    # ✅ กันรันซ้อน (Defect #14): ถ้ารอบก่อนหน้ายังไม่เสร็จ (ใช้เวลาจริง ~11-13 นาที)
    # อย่าปล่อยให้ trigger รอบใหม่ (เช่น keepalive self-heal ทุก 10 นาที) มาแย่งชน rate limit
    with _prefetch_lock:
        if _prefetch_running:
            return {"status": "already_running", "message": "Prefetch is already running — skip this trigger"}
        _prefetch_running = True

    def _run_prefetch():
        global _prefetch_running
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
        finally:
            with _prefetch_lock:
                _prefetch_running = False

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
            "prefetch_running": _prefetch_running,
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
                "reasoning": s.reasoning,  # ✅ เพิ่ม 2026-07-03: เหตุผลภาษาไทยจากหนุ่ม
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
@app.post("/trade-parse-image")
async def parse_trade_image(file: UploadFile = File(...)):
    """✅ เพิ่ม 2026-07-03: MBBook ส่งรูปสลิปซื้อขาย (เช่น Dime app) → โคลสัน (Haiku vision) อ่านค่าให้
    ไม่บันทึก DB ที่ endpoint นี้ — คืนค่า parse แล้วให้ frontend เอาไป pre-fill ฟอร์มให้ตรวจทาน/แก้ก่อน
    แล้วค่อยยิง /trade-update จริงตอนกดยืนยัน (กันเคส AI อ่านผิด)"""
    contents = await file.read()
    image_base64 = base64.b64encode(contents).decode("utf-8")
    media_type = file.content_type or "image/jpeg"

    result = orchestrator.colson_parse_trade_image(image_base64, media_type)

    if result is None or "error" in result:
        return {"status": "error", "message": result.get("error", "อ่านรูปไม่สำเร็จ") if result else "อ่านรูปไม่สำเร็จ"}

    return {"status": "parsed", **result}

@app.post("/trade-update")
async def update_trade(ticker: str, action: str, shares: float, price: float, db: Session = Depends(get_db)):
    """บันทึกประวัติการซื้อขาย + อัพเดต portfolio position จริง
    ✅ แก้ 2026-07-03: เดิม endpoint นี้บันทึกแค่ log ใน Trade table เฉยๆ
    ไม่เคยอัพเดต Portfolio table เลย ทำให้ /portfolio ว่างตลอดแม้บันทึก trade ไปแล้ว
    ตอนนี้เพิ่ม logic คำนวณ position จริง: BUY = ถัวเฉลี่ยต้นทุน, SELL = ลด shares ลง"""
    ticker = ticker.upper().strip()
    action = action.upper().strip()

    trade = Trade(ticker=ticker, action=action, shares=shares, price=price)
    db.add(trade)

    position = db.query(Portfolio).filter(Portfolio.ticker == ticker).first()

    if action == "BUY":
        if position:
            new_shares = position.shares + shares
            # ถัวเฉลี่ยต้นทุนตามน้ำหนักจำนวนหุ้น (weighted average cost)
            position.avg_cost = ((position.shares * position.avg_cost) + (shares * price)) / new_shares
            position.shares = new_shares
            position.updated_at = datetime.utcnow()
        else:
            position = Portfolio(
                ticker=ticker, shares=shares, avg_cost=price,
                current_value=shares * price, total_gain=0.0,
                updated_at=datetime.utcnow()
            )
            db.add(position)

    elif action == "SELL":
        if position:
            remaining = position.shares - shares
            if remaining <= 0.0001:  # ขายหมด (เผื่อ floating point error เล็กน้อย)
                db.delete(position)
            else:
                position.shares = remaining
                position.updated_at = datetime.utcnow()
        # ถ้าไม่มี position อยู่ก่อน (ขายโดยไม่เคยบันทึกซื้อ) — บันทึกแค่ history ใน Trade เฉยๆ ไม่ error

    db.commit()
    db.refresh(trade)
    return {"status": "recorded", "id": trade.id, "ticker": ticker, "action": action}

# Portfolio
@app.get("/portfolio")
async def get_portfolio(db: Session = Depends(get_db)):
    """✅ แก้ 2026-07-03: current_value/gain คำนวณสดจาก Stock.current_price ตอน query
    แทนที่จะพึ่งค่าที่ snapshot ไว้ตอนบันทึก trade (ซึ่งไม่มีอะไรมาอัพเดตให้เป็นปัจจุบัน)"""
    holdings = db.query(Portfolio).all()
    result_holdings = []
    total_value = 0.0
    total_cost = 0.0

    for h in holdings:
        stock = db.query(Stock).filter(Stock.ticker == h.ticker).first()
        current_price = stock.current_price if stock and stock.current_price else h.avg_cost
        current_value = h.shares * current_price
        cost_basis = h.shares * h.avg_cost
        gain = current_value - cost_basis

        total_value += current_value
        total_cost += cost_basis

        result_holdings.append({
            "ticker": h.ticker,
            "shares": h.shares,
            "avg_cost": h.avg_cost,
            "current_price": current_price,
            "current_value": current_value,
            "gain": gain,
            "gain_pct": (gain / cost_basis * 100) if cost_basis else 0.0
        })

    return {
        "total_value": total_value,
        "total_cost": total_cost,
        "total_gain": total_value - total_cost,
        "holdings_count": len(result_holdings),
        "holdings": result_holdings
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
            # ✅ แก้ 2026-07-02: เพิ่ม REJECTED เข้า skip-list (เดิมขาด — ทำให้ self-heal
            # พยายามซ้ำไปเรื่อยๆ หลัง REJECTED จนกว่าจะชน budget แล้วเจอ BUDGET_EXCEEDED ตอนตี 3-4)
            if last_log.status in ("BUDGET_EXCEEDED", "COMPLETE", "ABORTED", "REJECTED"):
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


@app.get("/costs/summary")
async def get_cost_summary(db: Session = Depends(get_db)):
    """สรุปต้นทุน Anthropic API รายเดือน + เทียบเป้าหมาย/เพดานงบของ MBBook
    หมายเหตุ: endpoint นี้แค่ SUM/AVG คอลัมน์ cost_usd ที่ เอ บันทึกไว้อยู่แล้ว — ไม่เรียก LLM เพิ่ม ไม่มีต้นทุนส่วนนี้"""
    from models import WorkflowLog
    from sqlalchemy import desc

    # เป้าหมายงบที่ MBBook ตั้งไว้ (บันทึกเมื่อ 2026-07-01)
    MONTHLY_TARGET_USD  = 10.0
    MONTHLY_CEILING_USD = 12.0
    EST_WEEKDAYS_PER_MONTH = 20  # 4 Mon + 12 Tue-Thu + 4 Fri ตามสูตรเดียวกับ DAILY_BUDGET ใน agents.py

    logs = db.query(WorkflowLog).order_by(desc(WorkflowLog.timestamp)).all()

    now = datetime.utcnow()
    month_key = now.strftime("%Y-%m")

    # เดือนปัจจุบัน (UTC)
    month_logs = [l for l in logs if l.timestamp and l.timestamp.strftime("%Y-%m") == month_key]
    month_cost = sum(l.cost_usd or 0 for l in month_logs)

    # แยกตามวันในสัปดาห์ — ใช้ log ทั้งหมดที่มี เพื่อดู pattern ราคาแต่ละวัน
    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    by_weekday = {name: {"runs": 0, "total_cost_usd": 0.0} for name in weekday_names}
    for l in logs:
        if l.timestamp and l.cost_usd:
            wd = weekday_names[l.timestamp.weekday()]
            by_weekday[wd]["runs"] += 1
            by_weekday[wd]["total_cost_usd"] += l.cost_usd
    for wd in by_weekday:
        r = by_weekday[wd]["runs"]
        by_weekday[wd]["avg_cost_usd"] = round(by_weekday[wd]["total_cost_usd"] / r, 4) if r else None
        by_weekday[wd]["total_cost_usd"] = round(by_weekday[wd]["total_cost_usd"], 4)

    # Projection: เฉลี่ยจาก run ล่าสุดที่ status = COMPLETE เท่านั้น (ตัด run ทดสอบ/debug ที่ cost เพี้ยนออก)
    recent_complete = [l.cost_usd for l in logs if l.status == "COMPLETE" and l.cost_usd][:5]
    avg_recent = (sum(recent_complete) / len(recent_complete)) if recent_complete else None
    projected_month_cost = round(avg_recent * EST_WEEKDAYS_PER_MONTH, 2) if avg_recent else None

    if projected_month_cost is None:
        status = "insufficient_data"
    elif projected_month_cost <= MONTHLY_TARGET_USD:
        status = "within_target"
    elif projected_month_cost <= MONTHLY_CEILING_USD:
        status = "over_target_under_ceiling"
    else:
        status = "over_ceiling"

    return {
        "current_month": month_key,
        "month_to_date": {
            "runs": len(month_logs),
            "total_cost_usd": round(month_cost, 4),
        },
        "recent_avg_cost_per_run_usd": round(avg_recent, 4) if avg_recent else None,
        "projected_month_cost_usd": projected_month_cost,
        "budget": {
            "target_monthly_usd": MONTHLY_TARGET_USD,
            "ceiling_monthly_usd": MONTHLY_CEILING_USD,
            "status": status,
        },
        "by_weekday": by_weekday,
    }


@app.get("/roi/summary")
async def get_roi_summary(db: Session = Depends(get_db)):
    """✅ เพิ่ม 2026-07-04: ROI ของสัญญาณ AI (Phase 1 evaluation — ดู Blueprint.md)
    - win rate (BUY ราคาขึ้น / SELL ราคาลง = ถูก) ที่ระยะ 14d และ 30d เทียบเกณฑ์ 75%
    - avg return % (เฉพาะสัญญาณ BUY) ที่ระยะ 30d เทียบเป้า 13%/เดือน
    ข้อมูลมาจาก signal_history ที่ insert ทุกคืน (insert-only ไม่ทับ) — สัญญาณที่ยังไม่ครบอายุ
    (เช่น เพิ่งออกเมื่อวาน) จะไม่ถูกนับ ต้องรอให้ครบ 14/30 วันก่อนถึงจะตัดสินถูก/ผิดได้"""
    return orchestrator.calculate_roi(db)


@app.get("/roi/portfolio-history")
async def get_roi_portfolio_history(db: Session = Depends(get_db)):
    """✅ เพิ่ม 2026-07-04: ข้อมูลกราฟแท่ง 2 ชุดสำหรับผลตอบแทนพอร์ตจริง — รายวัน (จ-ศ หลังตลาดปิด)
    และรายเดือน (สรุปวันสิ้นเดือน) ให้ frontend ทำกราฟแท่งจากข้อมูลนี้โดยตรง"""
    return orchestrator.portfolio_return_history(db)


@app.get("/workflow/latest-report")
async def get_latest_report(db: Session = Depends(get_db)):
    """✅ เพิ่ม 2026-07-03: รายงานตลาดฉบับเต็มล่าสุดที่เจนเขียน (ภาษาไทย)
    ให้ MBBook อ่านแทนการหาข่าวเองจาก 4-5 แหล่ง — คืนเฉพาะ run ล่าสุดที่มี full_report จริง
    (ข้าม run ที่ BUDGET_EXCEEDED หรือ ABORTED ซึ่งไม่มีรายงาน)
    ⚠️ คืนแค่อันเดียว — ถ้าไม่ได้เข้ามาดูหลายวัน ใช้ /workflow/reports แทนเพื่อดูย้อนหลังได้"""
    from models import WorkflowLog
    from sqlalchemy import desc
    log = (
        db.query(WorkflowLog)
        .filter(WorkflowLog.full_report.isnot(None))
        .order_by(desc(WorkflowLog.timestamp))
        .first()
    )
    if not log:
        return {"status": "no_report_yet", "message": "ยังไม่มีรายงานที่บันทึกไว้ — รอ workflow รันรอบถัดไป (22:00 น.)"}
    return {
        "status": "ok",
        "timestamp": log.timestamp,
        "run_status": log.status,
        "buy_signals": log.buy_signals,
        "hold_signals": log.hold_signals,
        "sell_signals": log.sell_signals,
        "report": log.full_report,
    }


@app.get("/workflow/reports")
async def get_recent_reports(limit: int = 7, db: Session = Depends(get_db)):
    """✅ เพิ่ม 2026-07-03: รายงานตลาดย้อนหลังหลายคืน (ไม่ใช่แค่ล่าสุดอันเดียว)
    เหตุผล: ข้อมูลของทุกคืนไม่เคยถูกทับ (insert แถวใหม่ทุก run ไม่ใช่ update) แต่ endpoint
    /workflow/latest-report เดิมโชว์แค่อันล่าสุด ทำให้ MBBook ไม่มีทางย้อนดูรายงานของคืนก่อนๆ
    ถ้าพลาดไม่ได้เข้ามาดูสักวัน — endpoint นี้แก้ตรงนั้น ให้ดูย้อนหลังได้จริง"""
    from models import WorkflowLog
    from sqlalchemy import desc
    logs = (
        db.query(WorkflowLog)
        .filter(WorkflowLog.full_report.isnot(None))
        .order_by(desc(WorkflowLog.timestamp))
        .limit(limit)
        .all()
    )
    return {
        "count": len(logs),
        "reports": [
            {
                "id": l.id,
                "timestamp": l.timestamp,
                "run_status": l.status,
                "buy_signals": l.buy_signals,
                "hold_signals": l.hold_signals,
                "sell_signals": l.sell_signals,
                "report": l.full_report,
            }
            for l in logs
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
