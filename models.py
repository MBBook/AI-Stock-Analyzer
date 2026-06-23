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
