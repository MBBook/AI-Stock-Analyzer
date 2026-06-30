from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Stock(Base):
    __tablename__ = "stocks"
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String, unique=True, index=True)
    signal = Column(String, default="HOLD")
    confidence = Column(Float, default=0.0)
    current_price = Column(Float, default=0.0)
    fair_price = Column(Float, default=0.0)
    s1 = Column(Float, default=0.0)
    s2 = Column(Float, default=0.0)
    s3 = Column(Float, default=0.0)
    at_new_high = Column(Boolean, default=False)
    at_new_low  = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String, index=True)
    action = Column(String)
    shares = Column(Integer)
    price = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Portfolio(Base):
    __tablename__ = "portfolio"
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String, unique=True)
    shares = Column(Integer)
    avg_cost = Column(Float)
    current_value = Column(Float)
    total_gain = Column(Float)
    updated_at = Column(DateTime, default=datetime.utcnow)

class WorkflowLog(Base):
    """บันทึก workflow run ทุกครั้ง — ใช้โดย เอ (record) และ นิก (weekly analysis)"""
    __tablename__ = "workflow_logs"

    id              = Column(Integer, primary_key=True, index=True)
    timestamp       = Column(DateTime, default=datetime.utcnow)
    status          = Column(String)               # COMPLETE / REJECTED / ABORTED
    stocks_analyzed = Column(Integer, default=0)
    buy_signals     = Column(Integer, default=0)
    sell_signals    = Column(Integer, default=0)
    hold_signals    = Column(Integer, default=0)
    needs_review    = Column(Integer, default=0)
    summary         = Column(Text,    nullable=True)  # เอ สรุปด้วย Haiku
    include_weekend = Column(Boolean, default=False)  # True = Monday mode
    cost_usd        = Column(Float,   default=0.0)    # ค่าใช้จ่าย API ของ run นี้ (USD)

class HourlyCache(Base):
    """Cache ราคา + fundamentals ของหุ้นแต่ละตัว — pre-fetch รายชั่วโมงโดย GitHub Actions
    ที่ 22:00 นัตตี้อ่านจากตารางนี้แทนการ fetch live → ประหยัดเวลา 10-15 นาที"""
    __tablename__ = "hourly_cache"

    id          = Column(Integer,  primary_key=True, index=True)
    ticker      = Column(String,   nullable=False, index=True)
    price       = Column(Float,    nullable=True)
    week52_high = Column(Float,    nullable=True)
    week52_low  = Column(Float,    nullable=True)
    pe_ratio    = Column(Float,    nullable=True)
    market_cap  = Column(Float,    nullable=True)
    source      = Column(String,   nullable=True)   # 'finnhub' | 'yfinance'
    at_new_high = Column(Boolean,  default=False)
    at_new_low  = Column(Boolean,  default=False)
    fetched_at  = Column(DateTime, default=datetime.utcnow, index=True)

class NikSuggestion(Base):
    """บันทึก suggestion ของนิก — รอ MBBook อนุมัติ แล้วให้ Cow apply"""
    __tablename__ = "nik_suggestions"

    id            = Column(Integer, primary_key=True, index=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    summary       = Column(Text,    nullable=False)  # สรุปสั้นว่านิกอยากแก้อะไร
    diff_text     = Column(Text,    nullable=False)  # diff จริงที่นิกสร้าง
    status        = Column(String,  default="pending")  # pending / complete / failed
    error_message = Column(Text,    nullable=True)   # เหตุผลที่ fail (ถ้ามี)
    applied_at    = Column(DateTime, nullable=True)  # เวลาที่ apply สำเร็จ
