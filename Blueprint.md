# Blueprint — AI Stock Analyzer V4

> อ่านไฟล์นี้ก่อนเริ่มงานทุกครั้ง
> อัพเดตล่าสุด: 2026-06-27

---

## 1. ภาพรวมระบบ

ระบบวิเคราะห์หุ้นอัตโนมัติโดย AI 10 ตัว ทำงานแบบ sequential pipeline ทุกวันธรรมดา (Mon–Fri)
รัน workflow ผ่าน GitHub Actions → Render (FastAPI) → Neon PostgreSQL → LINE notification

**Stack:** Python/FastAPI · SQLAlchemy · Neon PostgreSQL · Anthropic API · Render (free tier) · GitHub Actions · React frontend

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
| 9 | **โคลสัน** | Parse trade instruction → บันทึก DB *(Event-Driven — ไม่อยู่ใน sequential pipeline)* | Haiku |
| 10 | **นิก** | ทุกวันศุกร์: วิเคราะห์ log → สร้าง diff suggestion → รอ MBBook อนุมัติ | Sonnet |

**Workflow order (sequential):** นัตตี้ → หนุ่ม → มด → checkpoint DB → แฮรี่ → เจน → นน → (เก้า retry) → เอ → นิก (ศุกร์เท่านั้น)

**โคลสัน (Event-Driven):** ทำงานแยกผ่าน `POST /trade-update` webhook — ไม่ได้ถูกเรียกโดย AgentOrchestrator แต่รับ request โดยตรงจาก MBBook เมื่อมีการ trade

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

## 5. Schedule (GitHub Actions · Bangkok time GMT+7)

> ย้ายจาก cron-job.org → GitHub Actions ทั้งหมด เมื่อ 2026-06-27
> GitHub Secret: `RENDER_URL = https://ai-stock-analyzer-msli.onrender.com`

| Workflow | Schedule (UTC) | Bangkok | วัน | หน้าที่ |
|----------|---------------|---------|-----|---------|
| `AI_Stocks_Trigger` | 15:00 | 22:00 | Mon–Fri | Main trigger · Monday ส่ง `?include_weekend=true` · wake Render ก่อน (retry 15×) |
| `Render Keepalive` | ทุก 10 นาที | ทุก 10 นาที | ทุกวัน | ping `/health` ป้องกัน dyno sleep |
| `Workflow Resume` | 15:15–16:45 ทุก 15 นาที | 22:15–23:45 | Mon–Fri | POST `/workflow/resume` fallback ถ้า crash |

**หมายเหตุ budget:** `datetime.now()` บน Render ใช้ UTC → budget reset = 00:00 UTC = **07:00 Bangkok**

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

**Render free tier:** dyno sleep หลัง 15 นาที idle → keepalive ping `/health` ทุก 10 นาที (GitHub Actions)
→ wake time ~50s → `AI_Stocks_Trigger` retry สูงสุด 15 ครั้ง × 10s = 2.5 นาที ก่อน trigger จริง

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
├── .github/workflows/
│   ├── trigger_workflow.yml  # AI_Stocks_Trigger — main cron 22:00 จ–ศ
│   ├── keepalive.yml         # Render Keepalive — ทุก 10 นาที
│   └── resume.yml            # Workflow Resume — 22:15–23:45 จ–ศ
├── frontend/
│   └── src/App.jsx    # React dashboard
└── Claude_Profect/    # backup / reference files
```

---

## 12. Tech Stack Decisions (Phase 1)

| เรื่อง | ตัดสินใจ | Phase 2 |
|--------|---------|---------|
| Frontend hosting | Vercel / Netlify (ไม่ใช้ Render — ป้องกัน hours เกิน 750) | — |
| DB Migration | `CREATE TABLE IF NOT EXISTS` + manual `ALTER TABLE` ใน startup | Alembic |

---

## 13. Architectural Defect Log (2026-06-27)

| # | Defect | สถานะ | Action |
|---|--------|--------|--------|
| 1 | Colson ไม่อยู่ใน workflow order | ✅ แก้แล้ว | เพิ่ม note ใน Blueprint ว่าเป็น Event-Driven Agent ผ่าน `/trade-update` |
| 2 | OOM Risk บน Render 512MB | ⏳ Monitor | ระบบยังไม่ OOM — รอดูผลวันจันทร์ full 40 tickers ก่อน ถ้า crash ค่อย add `gc.collect()` |
| 3 | Race Condition `/workflow/resume` | ❌ ไม่มี defect | Code มี guard บรรทัด 378 อยู่แล้ว: `if _job["status"] == "running": return already_running` |
| 4 | Budget $0.85 ไม่พอ 40 tickers | ⏳ Monitor | ยังไม่มี cost จริง — prompt caching ลด cost ได้ 10× รอดู `cost_usd` ใน WorkflowLog วันจันทร์ก่อน |
| 5 | Timezone Mismatch (นิก / budget) | ❌ ไม่มี defect | 22:00 Bangkok = 15:00 UTC = วันเดียวกันเสมอ ไม่ข้ามวัน weekday() ถูกต้อง |
| 6 | Resume loop หลัง BUDGET_EXCEEDED | ✅ แก้แล้ว | เพิ่ม check ใน `/workflow/resume`: ถ้า last log วันนี้เป็น BUDGET_EXCEEDED/COMPLETE/ABORTED → return skipped |
| 7 | DB Concurrency Lock (Harry vs Colson) | ❌ ไม่มี defect | PostgreSQL MVCC จัดการ read/write concurrency ได้เอง แฮรี่ read-only → ไม่มี deadlock risk |

| 8 | Monday Mode Budget Deficit | ⏳ Monitor | $1.20 ตั้งไว้แล้วสำหรับ 72hr news — รอดู cost จริงวันจันทร์ก่อน (เหมือน Defect 4) |
| 9 | LLM ล้มเมื่อ PE/MarketCap = None | ❌ ไม่มี defect | Prompt บรรทัด 668 รองรับแล้ว: "ถ้า P/E หรือ Market Cap เป็น N/A ให้วิเคราะห์จาก price แทน" + `_safe_float()` จัดการ edge cases |
| 10 | LINE Notification Spam | ❌ ไม่มี defect | `_send_line_notification()` ถูกเรียกแค่ 2 จุด: จบสำเร็จ 1 ครั้ง + exception 1 ครั้ง ไม่มีการส่งรายตัว |

**ถ้า Defect 2, 4 หรือ 8 เกิดจริงวันจันทร์:**
- OOM → เพิ่ม `gc.collect()` หลัง checkpoint แต่ละ ticker
- Budget เกิน → ปรับ limit เป็น $2.00 (Tue-Thu) / $2.50 (Mon) หรือ downgrade มด จาก Sonnet → Haiku

---

## 14. สถานะ Phase 1 Testing

**เป้าหมาย:** รัน 60 วัน → วัด ROI
- ROI > 50% → Upgrade (เพิ่ม tickers, feature ใหม่)
- ROI < 50% → Debug (ดู WorkflowLog + nik suggestions)

**ปัจจุบัน:** 40 tickers · live บน Render · 133 tests pass · GitHub Actions active (ย้ายจาก cron-job.org แล้ว)
