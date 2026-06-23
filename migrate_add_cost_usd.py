"""
Migration: เพิ่ม cost_usd column ใน workflow_logs
รันครั้งเดียว: python migrate_add_cost_usd.py

ใช้ psycopg2 แทน SQLAlchemy — compatible กับ Python 3.14
"""
import os
import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    try:
        from dotenv import load_dotenv
        load_dotenv()
        DATABASE_URL = os.getenv("DATABASE_URL")
    except ImportError:
        pass

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not set — set it as env var or add to .env")

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# ตรวจว่า column มีอยู่แล้วหรือยัง
cursor.execute("""
    SELECT column_name FROM information_schema.columns
    WHERE table_name = 'workflow_logs' AND column_name = 'cost_usd'
""")
exists = cursor.fetchone()

if exists:
    print("✅ cost_usd column already exists — nothing to do")
else:
    cursor.execute("ALTER TABLE workflow_logs ADD COLUMN cost_usd FLOAT DEFAULT 0.0")
    conn.commit()
    print("✅ cost_usd column added to workflow_logs")

cursor.close()
conn.close()
