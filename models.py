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
    # ✅ เพิ่ม 2026-07-03: หนุ่มสร้าง reasoning (เหตุผลภาษาไทย 2-3 ประโยค อ้างอิงข่าว/sentiment)
    # ต่อหุ้นทุกคืนอยู่แล้ว แต่ไม่เคยถูกบันทึกลง DB เลย — MBBook ต้องการอ่านเหตุผลนี้แทนการ
    # หาข่าวเองจาก 4-5 แหล่ง (ดู workflow_trade_screenshots.md / project memory)
    reasoning = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True)
    ticker = Column(String, index=True)
    action = Column(String)
    # ✅ แก้ 2026-07-03: เดิม Integer — MBBook ซื้อหุ้นเศษส่วน (fractional shares) ผ่าน Dime app
    # เช่น 0.1874433 หุ้น ถ้าเก็บเป็น Integer จะถูกปัดเป็น 0 ข้อมูลหายหมด
    shares = Column(Float)
    price = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Portfolio(Base):
    __tablename__ = "portfolio"

    id = Column(Integer, primary_key=True)
    ticker = Column(String, unique=True)
    shares = Column(Float)  # ✅ แก้ 2026-07-03: เหตุผลเดียวกับ Trade.shares (fractional shares)
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
    summary         = Column(Text,    nullable=True)  # เอ สรุปด้วย Haiku (2-3 ประโยค เกี่ยวกับ run เอง ไม่ใช่ข่าว)
    # ✅ เพิ่ม 2026-07-03: รายงานตลาดฉบับเต็มที่เจนเขียนทุกคืน (market overview, top signals,
    # portfolio recommendations, risk) เดิมอยู่แค่ใน memory ระหว่าง job หายทันทีที่ job ถัดไปทับ
    # เก็บถาวรตรงนี้ให้ MBBook อ่านย้อนหลังได้ผ่าน /workflow/latest-report
    full_report     = Column(Text,    nullable=True)
    include_weekend = Column(Boolean, default=False)  # True = Monday mode
    cost_usd        = Column(Float,   default=0.0)    # ค่าใช้จ่าย API ของ run นี้ (USD)

class SignalHistory(Base):
    """✅ เพิ่ม 2026-07-04: เก็บสัญญาณ + ราคา ณ เวลานั้นทุกคืน แบบ insert-only (ไม่ทับเหมือน
    ตาราง stocks) เพื่อคำนวณ ROI ย้อนหลังได้จริงตอนครบ 60 วัน (Phase 1 evaluation)
    วิธีจับคู่ราคาอนาคต: หา row ของ ticker เดียวกันที่ timestamp ห่างจากวันสัญญาณ ~14/~30 วัน
    (มีอยู่แล้วเพราะ insert ทุกคืนทุกหุ้นอยู่แล้ว ไม่ต้องมีตารางราคาแยกต่างหาก)
    นิยาม ROI ที่ตกลงกับ MBBook (ดู Blueprint.md):
      - win rate (BUY ราคาขึ้น / SELL ราคาลง = ถูก) เทียบเกณฑ์ 75% ที่ระยะ 14 และ 30 วัน
      - avg return % (เฉพาะสัญญาณ BUY) เทียบเป้า 13%/เดือน ที่ระยะ 30 วัน"""
    __tablename__ = "signal_history"

    id         = Column(Integer, primary_key=True, index=True)
    ticker     = Column(String,  nullable=False, index=True)
    signal     = Column(String,  nullable=False)   # BUY / HOLD / SELL
    confidence = Column(Float,   default=0.0)
    price      = Column(Float,   nullable=False)
    timestamp  = Column(DateTime, default=datetime.utcnow, index=True)

class PortfolioSnapshot(Base):
    """✅ เพิ่ม 2026-07-04: snapshot มูลค่ารวมของพอร์ตทั้งก้อนทุกคืน (insert-only ไม่ทับ)
    ใช้คำนวณผลตอบแทนสะสมของพอร์ตจริง (ไม่มีเส้นตาย ต่างจาก win rate ที่มีกรอบ 60 วัน)
    เทียบเป้า 13% ที่ตกลงกับ MBBook — baseline = total_cost (ต้นทุนจริงตอนซื้อ ไม่ใช่วันที่เริ่ม track)
    ดู Blueprint.md Section 14 และ agents.py::calculate_roi"""
    __tablename__ = "portfolio_snapshots"

    id          = Column(Integer, primary_key=True, index=True)
    total_value = Column(Float, nullable=False)   # มูลค่าปัจจุบันรวมทั้งพอร์ต (current_price × shares)
    total_cost  = Column(Float, nullable=False)   # ต้นทุนรวมจริงทั้งพอร์ต (avg_cost × shares) — baseline
    timestamp   = Column(DateTime, default=datetime.utcnow, index=True)

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
    # ✅ เพิ่ม 2026-07-05 (task #56): Beta/EPS ดึงจาก Finnhub metric=all response เดิม
    # (ไม่ต้องเรียก API เพิ่ม) — PEG ยังไม่ยืนยัน field ชัดเจน ลอง 'pegRatio' ไปก่อน
    # ต้อง verify จาก log จริงหลัง deploy ว่าได้ค่าจริงหรือ None ตลอด (ดู Pending.md)
    beta        = Column(Float,    nullable=True)
    eps         = Column(Float,    nullable=True)
    peg_ratio   = Column(Float,    nullable=True)
    # ✅ เพิ่ม 2026-07-05 (task #56): วันประกาศงบถัดไป — ดึงจาก Finnhub /calendar/earnings
    # เปลี่ยนไม่บ่อย (ทุกไตรมาส) จึงไม่เรียกทุกรอบ prefetch รายชั่วโมง (ดู natty_prefetch_prices)
    # แค่รีเฟรชถ้าข้อมูลเก่ากว่า 20 ชม. กัน rate limit Finnhub (60 req/min)
    earnings_date = Column(DateTime, nullable=True)   # วันที่ (UTC/US) จาก Finnhub ตรงๆ ยังไม่แปลงเวลาไทย
    earnings_hour = Column(String,  nullable=True)    # 'bmo' (ก่อนตลาดเปิด) / 'amc' (หลังตลาดปิด) / 'dmh'
    # ✅ เพิ่ม 2026-07-05 (รอบ 5): ชื่อเต็มบริษัท (Finnhub /stock/profile2 field 'name' — ยืนยันจริง)
    # + คำอธิบายบริษัท (yfinance 'longBusinessSummary' — ไม่มีใน Finnhub free tier) เปลี่ยนไม่บ่อย
    # (แทบไม่เปลี่ยนเลย) ใช้ carry-forward เหมือน earnings_date กัน rate limit
    company_name        = Column(String, nullable=True)
    company_description = Column(Text,   nullable=True)
    source      = Column(String,   nullable=True)   # 'finnhub' | 'yfinance'
    at_new_high = Column(Boolean,  default=False)
    at_new_low  = Column(Boolean,  default=False)
    fetched_at  = Column(DateTime, default=datetime.utcnow, index=True)

class NewsCache(Base):
    """Cache ข่าวของหุ้นแต่ละตัว — pre-fetch รายชั่วโมงจาก yfinance + Finnhub
    ที่ 22:00 นัตตี้อ่านจากตารางนี้แทนการ call MarketAux live"""
    __tablename__ = "news_cache"

    id         = Column(Integer,  primary_key=True, index=True)
    ticker     = Column(String,   nullable=False, index=True)
    news_json  = Column(Text,     nullable=True)   # JSON list ของ news items
    news_count = Column(Integer,  default=0)
    fetched_at = Column(DateTime, default=datetime.utcnow, index=True)

class NewsTranslation(Base):
    """✅ เพิ่ม 2026-07-11 — คำแปลไทย + sentiment/impact ของข่าวแต่ละชิ้น (Haiku วิเคราะห์)
    ตาม Language rule ใน UI_Redesign_Prompt_v3 (confirmed 2026-07-07): news content ต้องเป็นไทย
    - id = md5(title.strip().lower()[:50])[:12] — คีย์เดียวกับ id ใน GET /news (main.py) และ
      ตัวแปลใน agents.py::natty_translate_news ต้องตรงกันเสมอ 3 จุด
    - ข่าวละแถวเดียวถาวร (แปลครั้งเดียว ไม่แปลซ้ำ) — ไม่ผูก FK กับ news_cache เพราะ cache
      ถูกลบทุก 25 ชม. แต่คำแปลเก็บไว้ได้เลย เผื่อข่าวเดิมโผล่มาอีกจากหลาย ticker"""
    __tablename__ = "news_translations"

    id           = Column(String,   primary_key=True, index=True)  # md5 12 ตัว
    headline_th  = Column(Text,     nullable=True)
    summary_th   = Column(Text,     nullable=True)
    sentiment    = Column(String,   nullable=True)   # Positive | Negative | Neutral
    impact       = Column(String,   nullable=True)   # สูง | ปานกลาง | ต่ำ
    created_at   = Column(DateTime, default=datetime.utcnow)

class NikSuggestion(Base):
    """บันทึก suggestion ของนิก — รอ MBBook อนุมัติ แล้วให้ Cow apply"""
    __tablename__ = "nik_suggestions"

    id            = Column(Integer, primary_key=True, index=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    summary       = Column(Text,    nullable=False)  # สรุปสั้นว่านิกอยากแก้อะไร
    diff_text     = Column(Text,    nullable=False)  # diff จริงที่นิกสร้าง
    status        = Column(String,  default="pending")  # pending / complete / failed / rejected (✅ เพิ่ม 2026-07-11)
    error_message = Column(Text,    nullable=True)   # เหตุผลที่ fail (ถ้ามี)
    applied_at    = Column(DateTime, nullable=True)  # เวลาที่ apply สำเร็จ
    # ✅ เพิ่ม 2026-07-11: MBBook ขอให้รายงานนิกอธิบายเหตุผล — เก็บคำอธิบายว่าทำไมถึงแก้ตรงนี้
    # (nullable เพราะ suggestion เก่าก่อนอัพเดต prompt จะไม่มีค่านี้)
    reasoning     = Column(Text,    nullable=True)   # เหตุผลที่นิกเสนอแก้ตรงนี้ (ภาษาไทย)
