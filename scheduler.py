# Scheduling is handled by cron-job.org (external) — this file is a no-op.
# cron-job.org POSTs to /workflow at 22:00 Bangkok (Tue-Fri) and /workflow?include_weekend=true on Monday.
# Render is woken up at 21:50 via GET /health.

def setup_scheduler():
    print("ℹ️  Scheduler: using cron-job.org (external) — no internal jobs registered.")

def shutdown_scheduler():
    pass
