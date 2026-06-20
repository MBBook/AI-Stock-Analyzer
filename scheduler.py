from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from datetime import datetime

# Set Bangkok timezone
bangkok_tz = pytz.timezone('Asia/Bangkok')

scheduler = BackgroundScheduler(timezone=bangkok_tz)

async def run_daily_analysis():
    """วันอังคาร-ศุกร์ 22:00 ดึงข่าวปกติ 24 ชั่วโมง"""
    print(f"[{datetime.now(bangkok_tz)}] Starting daily analysis...")
    from agents import orchestrator
    await orchestrator.run_workflow()

async def run_monday_weekend_analysis():
    """วันจันทร์ 22:00 ดึงข่าว Sat-Sun-Mon (72 ชั่วโมง)"""
    print(f"[{datetime.now(bangkok_tz)}] Starting Monday weekend analysis...")
    from agents import orchestrator
    # Pass flag for weekend data
    await orchestrator.run_workflow(include_weekend=True)

def setup_scheduler():
    """Setup all scheduled jobs"""
    
    # วันอังคาร-ศุกร์ เวลา 22:00 น.
    scheduler.add_job(
        run_daily_analysis,
        CronTrigger(hour=22, minute=0, day_of_week='1-4', timezone=bangkok_tz),
        id='daily_analysis',
        name='Daily Analysis (Tue-Fri)',
        misfire_grace_time=60
    )
    
    # วันจันทร์ เวลา 22:00 น. (ดึงข่าว 3 วัน)
    scheduler.add_job(
        run_monday_weekend_analysis,
        CronTrigger(hour=22, minute=0, day_of_week='0', timezone=bangkok_tz),
        id='monday_weekend_analysis',
        name='Monday Weekend Analysis (Sat-Sun-Mon)',
        misfire_grace_time=60
    )
    
    scheduler.start()
    print("✅ Scheduler started!")
    print(f"   Next run: {scheduler.get_jobs()}")

def shutdown_scheduler():
    """Shutdown scheduler"""
    scheduler.shutdown()
