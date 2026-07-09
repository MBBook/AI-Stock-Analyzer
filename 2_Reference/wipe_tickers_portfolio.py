# -*- coding: utf-8 -*-
"""ล้าง tickers (stocks) + portfolio ทั้งหมด — MBBook สั่ง 2026-07-09 (เตรียมใส่หุ้นจริง + watchlist ใหม่)
เก็บไว้: trades (ประวัติเทรดจริง), signal_history (ข้อมูล ROI), workflow_logs, nik_suggestions
hourly_cache/news_cache ไม่ต้องลบ — ระบบ purge เองใน 25 ชม. และ /stocks อ่านจากตาราง stocks เป็นหลัก

วิธีรัน (PowerShell ที่ root โปรเจกต์):
    .venv\Scripts\python 2_Reference\wipe_tickers_portfolio.py | Tee-Object -FilePath output.md
"""
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
url = os.getenv("DATABASE_URL")
if not url:
    raise SystemExit("ไม่พบ DATABASE_URL ใน .env")

conn = psycopg2.connect(url, connect_timeout=15)
cur = conn.cursor()

for t in ("stocks", "portfolio"):
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    print(f"{t} ก่อนล้าง: {cur.fetchone()[0]} แถว")

cur.execute("DELETE FROM portfolio")
cur.execute("DELETE FROM stocks")
conn.commit()

for t in ("stocks", "portfolio"):
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    print(f"{t} หลังล้าง: {cur.fetchone()[0]} แถว")

cur.execute("SELECT COUNT(*) FROM trades")
print(f"trades (เก็บไว้เป็นประวัติ): {cur.fetchone()[0]} แถว")
cur.execute("SELECT COUNT(*) FROM signal_history")
print(f"signal_history (เก็บไว้เพื่อ ROI): {cur.fetchone()[0]} แถว")

conn.close()
print("\n✅ ล้างเสร็จ — ส่งรายการหุ้นจริง + watchlist ให้ Cow ได้เลย")
