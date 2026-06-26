# Blueprint — AI Stock Analyzer V4

> อ่านไฟล์นี้ก่อนเริ่มงานทุกครั้ง
> อัพเดตล่าสุด: 2026-06-26

---

## 1. ภาพรวมระบบ

ระบบวิเคราะห์หุ้นอัตโนมัติโดย AI 10 ตัว ทำงานแบบ sequential pipeline ทุกวันธรรมดา (Mon–Fri)
รัน workflow ผ่าน cron-job.org → Render (FastAPI) → Neon PostgreSQL → LINE notification

**Stack:** Python/FastAPI · SQLAlchemy · Neon PostgreSQL · Anthropic API · Render (free tier) · cron-job.org · React frontend

---

## 2. AI Agents (10 ตัว)

| Agent | ชื่อ | หน้าที่ | Model |
|-------|------|---------|-------|
| 1 | **นัตตี้** | ดึงราคา + news (3-tier: yfinance → Finnhub → Alpha Vantage) | — |
| 2 | **หนุ่ม** | วิเคราะห์ fundamental + ให้ BUY/HOLD/SELL signal | Sonnet |
| 3 | **มด** | Cross-validate ผล หนุ่ม — flag NEEDS_REVIEW ถ้าน่าสงสัย | Sonnet |
| 4 | **แฮรี่** | ตรวจ portfolio alignment กับ signal | — |
| 5 | **เจน** | สร้าง HTML report สรุปตลาด | Sonnet + cache |
| 6 | **นน** | QA ตรวจ report — PASS/REJECT | Sonnet + cache |
| 7 | **เก้า** | Retry coordinator ถ้า QA REJECT (max 3 รอบ) | Haiku |
| 8 | **เอ** | บันทึก WorkflowLog ลง DB + สรุป 2-3 ประโยค | Haiku |
| 9 | **โคลสัน** | Parse trade instruction → บันทึก DB | Haiku |
| 10 | **นิก** | ทุกวันศุกร์: วิเคราะห์ log → สร้าง diff suggestion → รอ MBBook อนุมัติ | Sonnet |

**Workflow order:** นัตตี้ → หนุ่ม → มด → checkpoint DB → แฮรี่ → เจน → นน → (เก้า retry) → เอ → นิก (ศุกร์เท่านั้น)

---

## 3. API Endpoints

| Method | Path | หน้าที่ |
|--------|------|---------|
| GET | `/health` | Health check — ต้องตอบ `{status: "ok"}` เสมอ |
| GET | `/` | Root |
| POST | `/stocks` | เพิ่ม ticker |
| GET | `/stocks` | ดูรายชื่อ + signal ทั้งหมด |
| DELETE | `/stocks/{ticker}` | ลบ ticker |
| POST | `/trade-update` | บันทึก trade (โคลสัน ใช้) |
| GET | `/portfolio` | ดู portfolio holdings |
| GET | `/analysis/latest` | สรุป signal ล่าสุด |
| POST | `/workflow` | เริ่ม workflow ใน background (non-blocking) |
| GET | `/workflow/status` | ดู job status (idle/running/completed/error) |
| GET | `/workflow/logs` | ดู log ของ run ปัจจุบัน |
| POST | `/workflow/resume` | Resume เฉพาะ ticker ที่ยังไม่วิเคราะห์วันนี้ — ใช้โดย cron |
| GET | `/workflow/history` | ดู WorkflowLog ย้อนหลัง 30 รายการ |
| GET | `/nik/suggestions` | ดู NikSuggestion 10 รายการล่าสุด |

---

## 4. Database Schema (Neon PostgreSQL)

| Table | คอลัมน์หลัก | ใช้โดย |
|-------|------------|--------|
| `stocks` | ticker, signal, confidence, price, s1/s2/s3, at_new_high, at_new_low, updated_at | ทุก agent |
| `trades` | ticker, action, shares, price, timestamp | โคลสัน |
| `portfolio` | ticker, shares, avg_cost, current_value, total_gain | แฮรี่ |
| `workflow_logs` | timestamp, status, stocks_analyzed, buy/sell/hold signals, needs_review, summary, cost_usd | เอ |
| `nik_suggestions` | summary, diff_text, status (pending/complete/failed), error_message, applied_at | นิก |

**Migration:** startup event ใน `main.py` รัน `ALTER TABLE / CREATE TABLE IF NOT EXISTS` อัตโนมัติ

---

## 5. Cron Schedule (cron-job.org · Bangkok time GMT+7)

| Job | เวลา | วัน | Endpoint | หมายเหตุ |
|-----|------|-----|---------|---------|
| Main workflow | 22:00 | Mon–Fri | `POST /workflow` | Monday ส่ง `?include_weekend=true` |
| Resume (resilience) | ทุก 15 นาที 22:00–23:59 | Mon–Fri | `POST /workflow/resume` | Resume ticker ค้าง ถ้า Render crash |
| Keepalive | ทุก 10 นาที | ทุกวัน | `GET /health` | ป้องกัน Render dyno sleep |

---

## 6. Daily Budget

| วัน | Limit/วัน | หมายเหตุ |
|-----|-----------|---------|
| Monday | $1.20 | news 3 วัน (Sat+Sun+Mon) |
| Tue–Thu | $0.85 | ปกติ |
| Friday | $1.10 | + นิก optimize |
| **Monthly ceiling** | **~$19.40** | ต่ำกว่า $20 |

---

## 7. Environment Variables

```
# Anthropic (หมุนเวียน 4 key)
ANTHROPIC_API_KEY_1 / _2 / _3 / _4

# Database
DATABASE_URL            # Neon PostgreSQL connection string

# Data sources
FINNHUB_API_KEY
ALPHA_VANTAGE_API_KEY
MARKETAUX_API_KEY

# Notifications
LINE_CHANNEL_ACCESS_TOKEN
LINE_USER_ID

# GitHub (นิก ใช้ดึง agents.py)
GITHUB_TOKEN
GITHUB_REPO             # default: MBBook/ai-stock-analyzer

# Render
RENDER_EXTERNAL_URL     # ใช้โดย keepalive ping
```

---

## 8. Resilience Pattern

**Checkpoint:** มด validate เสร็จ → บันทึก signal ทีละ ticker ทันที (ไม่รอ QA pass)
→ ถ้า Render crash กลางคัน `/workflow/resume` จะวิ่งต่อจากตัวที่ค้าง

**Render free tier:** dyno sleep หลัง 15 นาที idle → keepalive ping `/health` ทุก 10 นาที
→ wake time ~50s → cron-job.org ตั้ง timeout 30s + retry

**LINE notification:** ส่งทุก workflow จบ (COMPLETE/REJECTED/ABORTED/BUDGET_EXCEEDED/ERROR)
→ ถ้าไม่มี token → ข้าม ไม่ crash

---

## 9. นิก Suggestion Flow

```
ทุกศุกร์ (22:00 workflow)
  นิก อ่าน WorkflowLog 5 วัน
  → วิเคราะห์ error pattern
  → สร้าง diff blocks (<<<DIFF>>> format)
  → บันทึกลง nik_suggestions (status=pending)

webapp → GET /nik/suggestions → MBBook เห็น pending list
  → "Copy สำหรับขอ Cow ดู diff" → คุยกับ Cow ใน Cowork
  → Cow apply → รัน pytest → ถ้าผ่าน commit+push
  → status เปลี่ยนเป็น complete (manual)
```

---

## 10. Test Coverage (133 tests)

| ไฟล์ | จำนวน | ครอบคลุม |
|------|-------|---------|
| `test_agents.py` | 107 | _safe_float, นัตตี้ 3-tier, MarketAux, หนุ่ม, มด, นน, Workflow, โคลสัน, DB update, MarketCap, ATH/ATL, มด format, Cross-currency, **แฮรี่, เอ, นิก, checkpoint** |
| `test_main.py` | 26 | GET /health, POST /workflow, POST /workflow/resume, LINE notification resilience, background exception, GET /nik/suggestions |

**รันทดสอบ:**
```powershell
python -m pytest test_agents.py test_main.py -v
```

---

## 11. โครงสร้างไฟล์หลัก

```
Dashboard_Share/
├── agents.py          # AI agents ทั้ง 10 ตัว + AgentOrchestrator
├── main.py            # FastAPI app + endpoints + job state
├── models.py          # SQLAlchemy models (Stock, Trade, Portfolio, WorkflowLog, NikSuggestion)
├── database.py        # SessionLocal + engine
├── scheduler.py       # APScheduler (keepalive)
├── test_agents.py     # 107 unit tests (agents)
├── test_main.py       # 26 unit tests (endpoints)
├── Blueprint.md       # ← ไฟล์นี้
├── frontend/
│   └── src/App.jsx    # React dashboard
└── Claude_Profect/    # backup / reference files
```

---

## 12. สถานะ Phase 1 Testing

**เป้าหมาย:** รัน 60 วัน → วัด ROI
- ROI > 50% → Upgrade (เพิ่ม tickers, feature ใหม่)
- ROI < 50% → Debug (ดู WorkflowLog + nik suggestions)

**ปัจจุบัน:** 40 tickers · live บน Render · 133 tests pass · cron-job.org active
