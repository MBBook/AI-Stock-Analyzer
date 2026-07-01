"""
Internal APScheduler — prefetch prices + news ทุกชั่วโมง Mon-Fri 09:00-21:00 Bangkok
ไม่พึ่ง GitHub Actions cron เลย — รันใน Render process ตลอดเวลา
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
import threading

_scheduler = None
_prefetch_lock = threading.Lock()


def _run_prefetch():
    """Job จริงที่รันทุกชั่วโมง — import orchestrator ที่นี่ป้องกัน circular import"""
    if not _prefetch_lock.acquire(blocking=False):
        print("[Scheduler] ⚠️ Prefetch already running — skip this round")
        return
    try:
        from agents import orchestrator
        from database import SessionLocal
        from models import Stock

        db = SessionLocal()
        stocks = [s.ticker for s in db.query(Stock).all()]
        db.close()

        if not stocks:
            print("[Scheduler] No stocks in DB — skipping prefetch")
            return

        print(f"[Scheduler] 🕐 Starting scheduled prefetch for {len(stocks)} tickers...")
        orchestrator.natty_prefetch_prices(stocks)
        orchestrator.natty_prefetch_news(stocks)
        print("[Scheduler] ✅ Scheduled prefetch complete (prices + news)")
    except Exception as e:
        print(f"[Scheduler] ❌ Prefetch error: {e}")
    finally:
        _prefetch_lock.release()


def setup_scheduler():
    global _scheduler
    _scheduler = BackgroundScheduler(timezone=pytz.utc)

    # ทุกชั่วโมง Mon-Fri 02:00-14:00 UTC = 09:00-21:00 Bangkok
    _scheduler.add_job(
        _run_prefetch,
        CronTrigger(
            day_of_week="mon-fri",
            hour="2-14",
            minute=5,          # :05 ของทุกชั่วโมง — ห่างจาก :00 เพื่อหลีกเลี่ยง cold-start
            timezone=pytz.utc,
        ),
        id="prefetch_hourly",
        replace_existing=True,
        max_instances=1,       # ป้องกัน double-run
    )

    # รอบพิเศษ 14:45 UTC = 21:45 Bangkok — pre-warm ก่อน workflow 22:00
    _scheduler.add_job(
        _run_prefetch,
        CronTrigger(
            day_of_week="mon-fri",
            hour=14,
            minute=45,
            timezone=pytz.utc,
        ),
        id="prefetch_prewarm",
        replace_existing=True,
        max_instances=1,
    )

    _scheduler.start()
    print("✅ Scheduler started: prefetch every hour Mon-Fri 09:00-21:00 Bangkok + pre-warm 21:45")


def shutdown_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        print("Scheduler shut down.")
