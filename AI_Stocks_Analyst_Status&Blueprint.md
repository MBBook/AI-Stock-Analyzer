# 📊 AI Stock Analyzer V4 — Project Status & Plan

**Last Updated:** June 23, 2026  
**Status:** 🟢 Production Ready — Phase 1 Complete  
**Repository:** https://github.com/MBBook/ai-stock-analyzer  
**Deployment:** https://ai-stock-analyzer-msli.onrender.com  

---

## 🎯 **Project Goal**

ระบบ Multi-Agent AI วิเคราะห์หุ้น 30-40 ตัว อัตโนมัติทุกวัน ให้สัญญาณ BUY/HOLD/SELL  
พร้อม ROI tracking 60-90 วัน เพื่อพิสูจน์ว่าระบบสร้างผลตอบแทนได้จริง

**Success Criteria:** ROI > 40% ของรายจ่ายต่อเดือน → Upgrade ระบบครั้งใหญ่

---

## ✅ **สิ่งที่ทำเสร็จแล้ว (Phase 1 Complete)**

### **Backend — agents.py (1,279 lines)**

| Agent | หน้าที่ | Model | สถานะ |
|-------|---------|-------|-------|
| **นัตตี้** | ดึงราคาหุ้น (3-tier) + ข่าว MarketAux | ไม่ใช้ LLM | ✅ |
| **หนุ่ม** | วิเคราะห์หุ้น → BUY/HOLD/SELL | Sonnet 4.6 + cache | ✅ |
| **มด** | Cross-validate signals | Sonnet 4.6 + cache | ✅ |
| **แฮรี่** | Monitor portfolio alignment | ไม่ใช้ LLM | ✅ |
| **เจน** | สร้าง HTML report | Sonnet 4.6 + cache | ✅ |
| **นน** | QA check (PASS/REJECT) | Sonnet 4.6 + cache | ✅ |
| **เก้า** | Retry hint เมื่อ QA fail | Haiku 4.5 | ✅ |
| **เอ** | บันทึก WorkflowLog ลง DB | Haiku 4.5 | ✅ |
| **โคลสัน** | Parse manual trade → DB | Haiku 4.5 | ✅ |
| **นิก** | ทุกศุกร์: อ่าน DB → แก้ agents.py → push GitHub | Sonnet 4.6 (max_tokens=16000) | ✅ |

### **Data Sources — นัตตี้ 3-tier fallback**

```
Tier 1: yfinance          — ฟรี, ครบ (ราคา + P/E + MarketCap + 52-week)
Tier 2: Finnhub           — 60 req/min, ครบ (/quote + /stock/metric)
Tier 3: Alpha Vantage     — 5 req/min, 25/day (สำรองสุดท้าย)
ข่าว:   MarketAux         — 6 ข่าว/ticker, sentiment score, 40 calls/day
```

### **Key Features ที่ implement แล้ว**

- ✅ **3-tier data fallback** — yfinance → Finnhub → Alpha Vantage ไม่มี single point of failure
- ✅ **P/E ลบรองรับ** — บริษัทขาดทุน ≠ ไม่มีข้อมูล
- ✅ **Source-aware confidence** — Alpha Vantage (200DMA) → ลด confidence 0.15 อัตโนมัติ
- ✅ **MarketAux sentiment** — avg sentiment score ส่งให้หนุ่มวิเคราะห์
- ✅ **Monday weekend mode** — วันจันทร์ดึงข่าวตั้งแต่ศุกร์ 22:00
- ✅ **Prompt caching** — ลด cost ~50% สำหรับ Sonnet agents
- ✅ **HTML injection guard** — นน ป้องกัน HTML tags ใน DB
- ✅ **Word-boundary limit** — 8,000 chars แทน [:3000] ที่ตัดกลาง JSON
- ✅ **Early abort** — news = {} หรือ analysis = {} → ABORTED ทันที ไม่เสีย token
- ✅ **Real retry loop** — QA REJECT → เก้าวิเคราะห์ → hint → เจน retry (max 3x)
- ✅ **Batch DB commit** — commit 1 ครั้งหลัง loop ไม่ใช่ N ครั้ง
- ✅ **Boot validation** — ตรวจ API keys ทุกตัวตั้งแต่ server start
- ✅ **นิก Fully Auto** — อ่าน WorkflowLog DB → Sonnet แก้ code → push GitHub → Render auto-deploy

### **Database — models.py**

```python
Stock        — ticker, signal, confidence, current_price, fair_price, s1/s2/s3
Trade        — ticker, action, shares, price, timestamp
Portfolio    — ticker, shares, avg_cost, current_value, total_gain
WorkflowLog  — timestamp, status, stocks_analyzed, buy/sell/hold, needs_review, summary
```

### **Test Suite — test_agents.py**

```
63/63 tests PASS ✅

Coverage:
- _safe_float / _safe_positive_float  (20 tests)
- นัตตี้ 3-tier fallback              (6 tests)
- MarketAux / Monday mode             (7 tests)
- หนุ่ม signal validation             (5 tests)
- มด NEEDS_REVIEW flag                (4 tests)
- นน HTML injection + fail-safe       (6 tests)
- Workflow early exit + retry loop    (6 tests)
- โคลสัน trade parse                  (4 tests)
- _update_database                    (5 tests)
```

### **Infrastructure**

| Component | Detail | สถานะ |
|-----------|--------|-------|
| Deployment | Render (auto-deploy from GitHub) | ✅ Live |
| Database | Neon.tech PostgreSQL | ✅ Connected |
| Repo | MBBook/ai-stock-analyzer (main) | ✅ |
| API Keys | Render ENV (11 keys) | ✅ ครบ |

### **Render ENV Variables (ครบแล้ว)**

```
ANTHROPIC_API_KEY_1-4   ✅
DATABASE_URL             ✅
FINNHUB_API_KEY          ✅
ALPHA_VANTAGE_API_KEY    ✅
MARKETAUX_API_KEY        ✅
GITHUB_TOKEN             ✅ (90 days, repo scope)
GITHUB_REPO              ✅ MBBook/ai-stock-analyzer
PYTHON_VERSION           ✅
```

---

## 💰 **ต้นทุนรายเดือน**

| รายการ | Model | ต้นทุน/เดือน |
|--------|-------|-------------|
| Workflow รายวัน (35 tickers × 22 วัน) | Sonnet + Haiku | $10.56 |
| นิก (4 ศุกร์/เดือน) | Sonnet | $1.14 |
| **รวม** | | **~$11.70/เดือน** |

**งบ $30 → อยู่ได้ ~77 วัน**

---

## 🔴 **สิ่งที่ยังต้องทำต่อ (ทำทันที)**

### **1. รัน Workflow ใหม่ (สำคัญมาก)**

Workflow ที่รันไปครั้งแรก (2026-06-23) ใช้ **code เก่า** (ก่อน push ครั้งสุดท้าย)  
ยังไม่มี MarketAux, ยังไม่มี Sonnet, ยังไม่มี _fetch_finnhub_full

```bash
curl -X POST https://ai-stock-analyzer-msli.onrender.com/workflow -o workflow_result2.json
```

ผลที่ควรเห็นหลังรันด้วย code ใหม่:
- ✅ `[Tier 2] ✅ NVDA OK via Finnhub (price=XXX)` — ไม่ใช่ "Switching to Finnhub"
- ✅ `MarketAux: X news for NVDA` — มีข่าวและ sentiment
- ✅ P/E + Market Cap ไม่เป็น N/A อีกต่อไป
- ✅ Confidence สูงขึ้นจาก 48% เฉลี่ย

### **2. ตั้ง Scheduler ใน Render**

สร้าง Cron Job 2 ตัวใน Render Dashboard:

**Cron Job #1 — วันอังคาร-ศุกร์ 22:00 BKK (15:00 UTC)**
```
Name:     daily-workflow-tue-fri
Schedule: 0 15 * * 2-5
Command:  curl -X POST https://ai-stock-analyzer-msli.onrender.com/workflow
```

**Cron Job #2 — วันจันทร์ 22:00 BKK (weekend mode)**
```
Name:     monday-workflow-weekend
Schedule: 0 15 * * 1
Command:  curl -X POST "https://ai-stock-analyzer-msli.onrender.com/workflow?include_weekend=true"
```

### **3. เพิ่มหุ้น Watchlist**

ตอนนี้มีแค่ 9 ตัว (NVDA, AMZN, BRK.B, GOOGL, ASML, TSM, AAPL, MSFT, TSLA)  
เพิ่มให้ครบ 30-40 ตัวตามแผน:

```bash
# ตัวอย่าง batch add
for ticker in META NFLX AMZN JPM V MA UNH LLY JNJ PG; do
  curl -X POST "https://ai-stock-analyzer-msli.onrender.com/stocks?ticker=$ticker"
done
```

### **4. เริ่ม ROI Tracking**

- บันทึกราคาหุ้น + signal วันนี้เป็น baseline
- ติดตามทุกวัน 60-90 วัน
- เปรียบเทียบ signal กับผลจริง

---

## 📅 **Timeline**

| วัน | งาน |
|-----|-----|
| **วันนี้** | รัน workflow ใหม่, ตรวจผล, ตั้ง scheduler |
| **สัปดาห์นี้** | เพิ่มหุ้น 30-40 ตัว, verify scheduler รันครั้งแรก |
| **ทุกวันศุกร์** | นิก auto-optimize agents.py → push GitHub |
| **Day 60** | ประเมิน ROI |
| **ถ้า ROI > 40%** | Upgrade ระบบครั้งใหญ่ |

---

## 🚀 **Phase 2 — เมื่อ ROI > 40% (Future)**

สิ่งที่จะเพิ่มเมื่อ upgrade:

- **นน** — ตรวจ sentiment consistency (ข่าวลบ + signal BUY = flag)
- **แฮรี่** — ตรวจ holdings นอก watchlist
- **เอ** — บันทึก avg_sentiment ลง WorkflowLog
- **หนุ่ม** — เพิ่ม RSI, MACD, Volume จาก Finnhub Technical Indicators
- **ระบบแจ้งเตือน** — LINE/Telegram เมื่อมี BUY/SELL signal
- **Dashboard upgrade** — แสดง ROI tracking, sentiment trend, signal history

---

## 📋 **API Endpoints**

```
GET    /health                    — Server status
GET    /stocks                    — รายการหุ้นทั้งหมด + signals
POST   /stocks?ticker=AAPL        — เพิ่มหุ้น
DELETE /stocks/{ticker}           — ลบหุ้น
POST   /workflow                  — รัน workflow ทันที
POST   /workflow?include_weekend=true — Monday mode
GET    /workflow/logs             — ดู logs ล่าสุด
GET    /portfolio                 — ดู portfolio
POST   /trade-update              — บันทึก trade manual
```

---

## ⚠️ **Known Issues & Limitations**

| Issue | ระดับ | แผนแก้ |
|-------|-------|--------|
| yfinance blocked บน cloud IP | 🟡 | Finnhub fallback ทำงานได้ดี |
| Finnhub free tier — 52-week range แคบบางตัว | 🟡 | Phase 2: เพิ่มแหล่งข้อมูลสำรอง |
| นิก (Sonnet) อาจแก้ code พลาดได้บ้าง | 🟡 | Safety check: "class AgentOrchestrator" ต้องอยู่ใน output |
| Render free tier sleep 15 นาที | 🟢 | Scheduler wake-up call ก่อนรัน |
| $30 อยู่ได้ 77 วัน (ไม่ถึง 90) | 🟢 | ยอมรับได้ หรือลด prompt length |

---

*สร้างโดย Claude Sonnet 4.6 — AI Stock Analyzer V4 Development Session*  
*June 23, 2026*
