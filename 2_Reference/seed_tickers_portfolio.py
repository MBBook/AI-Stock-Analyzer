# -*- coding: utf-8 -*-
"""ล้าง + ใส่ tickers/portfolio ชุดจริงจาก Dime — MBBook ส่งสลิป 2026-07-09 00:31
สคริปต์เดียวจบ: DELETE stocks+portfolio เดิมทั้งหมด → INSERT ชุดใหม่ (ไม่ต้องรัน wipe แยก)
เก็บไว้: trades, signal_history, workflow_logs, nik_suggestions

ข้อมูลจากสลิป Dime (มูลค่ารวม $1,973.46 / กำไร +11.62% ณ 00:31 09-07-2026):
- หุ้นถือจริง 13 ตัว (shares + ต้นทุนเฉลี่ย USD ตรงจากแอป)
- Watchlist เพิ่ม 11 ตัว (MBBook พิมพ์): RKLB ASTS MRVL ARM MU IONQ PLTR ONDS OKTA P LWLG
รวม 24 tickers (เพดานระบบ 30)

วิธีรัน (PowerShell ที่ root โปรเจกต์):
    .venv\Scripts\python 2_Reference\seed_tickers_portfolio.py | Tee-Object -FilePath output.md
"""
import os
from datetime import datetime
from dotenv import load_dotenv
import psycopg2

# ===== หุ้นถือจริง 13 ตัว: (ticker, shares, avg_cost_usd) =====
HOLDINGS = [
    ("GOOGL", 1.4463770, 330.6261),
    ("NVDA",  1.1307625, 193.4182),
    ("ASML",  0.0914035, 1280.6952),
    ("TSM",   0.3021887, 330.1580),
    ("AMZN",  0.4350241, 239.0902),
    ("BRK.B", 0.1760013, 492.4397),
    ("WDC",   0.4899218, 412.4128),
    ("NOW",   1.0000000, 103.0000),
    ("VRT",   0.3242444, 311.0000),
    ("NBIS",  0.4809524, 210.0000),
    ("SNDK",  0.0448650, 899.9780),
    ("CCJ",   0.4524823, 98.6337),
    ("OKLO",  0.8713094, 82.2096),
]

# ===== Watchlist เพิ่มอีก 11 ตัว (ไม่ได้ถือ) =====
WATCHLIST = ["RKLB", "ASTS", "MRVL", "ARM", "MU", "IONQ", "PLTR", "ONDS", "OKTA", "P", "LWLG"]

ALL_TICKERS = [h[0] for h in HOLDINGS] + WATCHLIST
assert len(ALL_TICKERS) == len(set(ALL_TICKERS)), "มี ticker ซ้ำ!"
assert len(ALL_TICKERS) <= 30, f"เกินเพดาน 30 ตัว ({len(ALL_TICKERS)})"

load_dotenv()
url = os.getenv("DATABASE_URL")
if not url:
    raise SystemExit("ไม่พบ DATABASE_URL ใน .env")

conn = psycopg2.connect(url, connect_timeout=15)
cur = conn.cursor()
now = datetime.utcnow()

# --- 1) ล้างของเดิม ---
for t in ("stocks", "portfolio"):
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    print(f"{t} ก่อนล้าง: {cur.fetchone()[0]} แถว")
cur.execute("DELETE FROM portfolio")
cur.execute("DELETE FROM stocks")

# --- 2) ใส่ tickers ทั้ง 24 ตัว (ค่า default ให้ครบ — workflow คืนถัดไปเติมของจริงเอง) ---
for tk in ALL_TICKERS:
    cur.execute(
        """INSERT INTO stocks (ticker, signal, confidence, current_price, fair_price,
                               s1, s2, s3, at_new_high, at_new_low, reasoning, updated_at)
           VALUES (%s, 'HOLD', 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, FALSE, FALSE, NULL, %s)""",
        (tk, now),
    )

# --- 3) ใส่ portfolio 13 ตัว (current_value เริ่มที่ต้นทุน — ราคาจริงมาจาก hourly_cache ตอนแสดงผล) ---
total_cost = 0.0
for tk, shares, avg_cost in HOLDINGS:
    cost = shares * avg_cost
    total_cost += cost
    cur.execute(
        """INSERT INTO portfolio (ticker, shares, avg_cost, current_value, total_gain, updated_at)
           VALUES (%s, %s, %s, %s, 0.0, %s)""",
        (tk, shares, avg_cost, cost, now),
    )

conn.commit()

# --- 4) ตรวจผล ---
cur.execute("SELECT COUNT(*) FROM stocks")
print(f"\nstocks หลัง seed: {cur.fetchone()[0]} แถว (ต้องเป็น 24)")
cur.execute("SELECT COUNT(*) FROM portfolio")
print(f"portfolio หลัง seed: {cur.fetchone()[0]} แถว (ต้องเป็น 13)")
print(f"ต้นทุนรวม: ${total_cost:,.2f} (เทียบ Dime ~$1,768 — มูลค่า $1,973.46 คือรวมกำไร +11.62%)")
cur.execute("SELECT ticker, shares, avg_cost FROM portfolio ORDER BY shares*avg_cost DESC")
for r in cur.fetchall():
    print(f"  {r[0]:<6} {r[1]:>10.7f} หุ้น @ ${r[2]:,.4f}")

conn.close()
print("\n✅ Seed เสร็จ — prefetch รอบถัดไป (นาที :05) จะเริ่มดึงราคาชุดใหม่ และ workflow 22:00 คืนนี้วิเคราะห์ครบ 24 ตัว")
