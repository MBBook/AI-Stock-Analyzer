# Blueprint — AI Stock Analyzer V4

> อ่านไฟล์นี้ก่อนเริ่มงานทุกครั้ง
> อัพเดตล่าสุด: 2026-07-08

---

## 1. ภาพรวมระบบ

ระบบวิเคราะห์หุ้นอัตโนมัติโดย AI 10 ตัว ทำงานแบบ sequential pipeline ทุกวันธรรมดา (Mon–Fri)
รัน workflow ผ่าน GitHub Actions → Render (FastAPI) → Neon PostgreSQL → LINE notification

**Stack:** Python/FastAPI · SQLAlchemy · Neon PostgreSQL · Anthropic API · Render (free tier) · GitHub Actions · React frontend

---

## 2. AI Agents (10 ตัว)

| Agent | ชื่อ | หน้าที่ | Model |
|-------|------|---------|-------|
| 1 | **นัตตี้** | ดึงราคา + news (3-tier: yfinance → Finnhub → Alpha Vantage) + pre-fetch รายชั่วโมงลง HourlyCache/NewsCache | — |
| 2 | **หนุ่ม** | วิเคราะห์ fundamental + ให้ BUY/HOLD/SELL signal | Sonnet |
| 3 | **มด** | Cross-validate ผล หนุ่ม — flag NEEDS_REVIEW ถ้าน่าสงสัย | Sonnet |
| 4 | **แฮรี่** | ตรวจ portfolio alignment กับ signal | — |
| 5 | **เจน** | สร้าง plain-text report สรุปตลาด (inject signal summary ป้องกัน hallucinate) | Sonnet + cache |
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
| GET | `/stocks` | ดูรายชื่อ + signal ทั้งหมด — ✅ แก้ 2026-07-05 เพิ่ม market_cap/pe_ratio/week52_high/low/beta/eps/peg_ratio/earnings_date_thai (join `hourly_cache` ล่าสุดต่อ ticker) + s1/s2/s3 (แนวรับไม้ 1-3 จาก `stocks` table เอง — หนุ่มคำนวณให้ทุกคืนอยู่แล้ว แค่ไม่เคยถูกส่งออกมาก่อน) + company_name/company_description (รอบ 5 — Finnhub profile2 + yfinance longBusinessSummary, carry-forward เหมือน earnings_date) · ✅ เพิ่ม 2026-07-09 `change_pct` ต่อ ticker (เทียบ 2 แถวล่าสุดจาก `signal_history`, `null` ถ้าข้อมูลไม่ถึง 2 คืน) — ดู Defect #17 เรื่อง outage ที่เกิดตอน deploy ฟีเจอร์นี้ |
| DELETE | `/stocks/{ticker}` | ลบ ticker |
| POST | `/trade-update?ticker=&action=&shares=&price=` | บันทึก trade จริง + อัพเดต position (ถัวเฉลี่ยต้นทุนตอน BUY, ลด shares ตอน SELL) — ✅ แก้ 2026-07-03 เดิม endpoint นี้บันทึกแค่ log เฉยๆ ไม่เคยอัพเดต portfolio จริง |
| POST | `/trade-parse-image` (multipart file) | ✅ เพิ่ม 2026-07-03 — โคลสัน (Haiku vision) อ่านรูปสลิปซื้อขาย (เช่น Dime app) → คืน JSON {ticker, action, shares, price} ให้ frontend pre-fill ฟอร์ม ไม่บันทึก DB ที่ endpoint นี้ (save จริงผ่าน `/trade-update`) |
| GET | `/portfolio` | ดู portfolio holdings — ✅ แก้ 2026-07-05 current_price ดึงจาก `hourly_cache` ล่าสุดก่อน (fallback `Stock.current_price` → `avg_cost`) + เพิ่ม usd_thb_rate/total_value_thb/total_cost_thb/total_gain_thb/current_value_thb ต่อ holding (Frankfurter.app, cache 1 ชม.) |
| GET | `/analysis/latest` | สรุป signal ล่าสุด |
| POST | `/workflow` | เริ่ม workflow ใน background (non-blocking) |
| GET | `/workflow/status` | ดู job status (idle/running/completed/error) |
| GET | `/workflow/logs` | ดู log ของ run ปัจจุบัน |
| POST | `/workflow/resume` | Resume เฉพาะ ticker ที่ยังไม่วิเคราะห์วันนี้ — ใช้โดย cron |
| GET | `/workflow/history` | ดู WorkflowLog ย้อนหลัง 30 รายการ |
| GET | `/workflow/latest-report` | ✅ เพิ่ม 2026-07-03 — รายงานตลาดฉบับเต็มล่าสุดที่เจนเขียน (อันเดียว) |
| GET | `/workflow/reports?limit=7` | ✅ เพิ่ม 2026-07-03 (รอบ 2) — รายงานตลาดย้อนหลังหลายคืน (กันเคส MBBook ไม่ว่างเข้ามาดูหลายวัน) — ใช้ตัวนี้แทน `/workflow/latest-report` ในหน้าเว็บ |
| GET | `/nik/suggestions` | ดู NikSuggestion 10 รายการล่าสุด |
| GET | `/roi/summary` | ✅ เพิ่ม 2026-07-04 — win rate @14d/@30d (เกณฑ์ 75%) + portfolio_return สะสมไม่มีเส้นตาย (เป้า 13%) |
| GET | `/roi/portfolio-history?start_date=&end_date=` | ✅ เพิ่ม 2026-07-04, แก้ 2026-07-05 เพิ่ม query param `start_date`/`end_date` (YYYY-MM-DD, optional) filter ช่วงเวลา — ไม่ส่งมา = คืนทั้งหมดเหมือนเดิม |

---

## 4. Database Schema (Neon PostgreSQL)

| Table | คอลัมน์หลัก | ใช้โดย |
|-------|------------|--------|
| `stocks` | ticker, signal, confidence, price, s1/s2/s3, at_new_high, at_new_low, updated_at | ทุก agent |
| `trades` | ticker, action, shares, price, timestamp | โคลสัน |
| `portfolio` | ticker, shares, avg_cost, current_value, total_gain | แฮรี่ |
| `workflow_logs` | timestamp, status (COMPLETE/REJECTED), stocks_analyzed, buy/sell/hold signals, needs_review, summary, cost_usd | เอ |
| `hourly_cache` | ticker, price, week52_high/low, pe_ratio, market_cap, beta, eps, peg_ratio (✅ ทดลอง — field `pegRatio` ยังไม่ยืนยันจริง ดู Pending.md), earnings_date, earnings_hour (✅ เพิ่ม 2026-07-05), source, at_new_high/low, fetched_at | นัตตี้ prefetch |
| `news_cache` | ticker, news_json, news_count, fetched_at | นัตตี้ prefetch |
| `nik_suggestions` | summary, diff_text, status (pending/complete/failed), error_message, applied_at | นิก |

**Migration:** startup event ใน `main.py` รัน `ALTER TABLE / CREATE TABLE IF NOT EXISTS` อัตโนมัติ

---

## 5. Schedule (GitHub Actions · Bangkok time GMT+7)

> ย้ายจาก cron-job.org → GitHub Actions ทั้งหมด เมื่อ 2026-06-27
> GitHub Secret: `RENDER_URL = https://ai-stock-analyzer-msli.onrender.com`

> ⛔ **2026-07-02 22:xx — ปิด schedule ทั้งหมดใน GitHub Actions แล้ว** (เหลือ `workflow_dispatch` manual backup ทุกไฟล์) ย้าย trigger จริงไปที่ **cron-job.org** ทั้งหมด (ดู Defect #15) — ตารางข้างล่างนี้คือ config เดิมที่ปิดไว้ ดู schedule ปัจจุบันจริงที่ตาราง cron-job.org ด้านล่าง

| Workflow (GitHub Actions, ปิดแล้ว) | Schedule (UTC) | Bangkok | วัน | หน้าที่เดิม |
|----------|---------------|---------|-----|---------|
| `AI_Stocks_Trigger` | 15:00 | 22:00 | Mon–Fri | Main trigger · Monday ส่ง `?include_weekend=true` |
| `AI_Stocks_Prefetch` | 5 2-14 * * 1-5 + 45 14 * * 1-5 | 09:00–21:00 (นาที :05) + pre-warm 21:45 | Mon–Fri | POST `/prefetch` ทุกชั่วโมง |
| `Render Keepalive` | ทุก 10 นาที | ทุก 10 นาที | ทุกวัน | ping `/health` + self-heal `/workflow/resume` |
| `Workflow Resume` | ⛔ ปิด schedule แล้ว 2026-07-01 | — | — | ซ้ำซ้อนกับ Keepalive self-heal |

**cron-job.org (trigger จริงตอนนี้)** — 6 jobs, ตั้งผ่าน `setup_cronjob_org.py` + `update_cronjob_weekends.py`:

| Job | Endpoint | Schedule (UTC) | วัน | หน้าที่ |
|-----|----------|-----------------|-----|---------|
| A - Keepalive Wake | GET `/health` | ทุก 10 นาที 02:00-19:00 | **ทุกวัน** (แก้ 2026-07-02 ตาม MBBook ขอ) | กันไม่ให้ Render dyno หลับ |
| B1 - Prefetch Hourly | POST `/prefetch` | นาที :05 ทุกชั่วโมง 02:00-14:00 | **ทุกวัน** | ดึงราคา+ข่าว ลดคอขวดนัตตี้ |
| B2 - Prefetch Prewarm | POST `/prefetch` | 14:45 | Mon–Fri | pre-warm ก่อน workflow หลัก 22:00 |
| C1 - Workflow Trigger (Monday) | POST `/workflow?include_weekend=true` | 15:00 | Mon เท่านั้น | trigger หลัก + รวมข้อมูลวันหยุด |
| C2 - Workflow Trigger (Tue-Fri) | POST `/workflow` | 15:00 | Tue–Fri | trigger หลัก |
| D - Workflow Resume Self-heal | POST `/workflow/resume` | ทุก 10 นาที 15:00-18:59 | Mon–Fri | self-heal ถ้า workflow ค้าง |

**ยืนยันผลจริง**: 2026-07-02 — B1 ยิงตรงเวลา 2 รอบติด (19:05, 20:05) + C2 trigger workflow หลักสำเร็จอัตโนมัติครั้งแรก (run id 9, COMPLETE, 22:10 น.) — เสถียรกว่า GitHub Actions ชัดเจน (keepalive.yml เดิมยิงจริงแค่ 21/790 ครั้งที่ควรได้)
**อัพเดต 2026-07-04**: คืนที่ 2 (2026-07-03) ก็ COMPLETE อัตโนมัติอีกครั้ง (run id 10, 22:09 น., 30/30, cost $0.499) — 2 คืนติดต่อกันหลังย้าย cron-job.org ครบทุกครั้ง ยังต้องดูต่ออีกสักพักก่อนเรียกว่า "เสถียรแน่นอนทุกคืน" แต่ trend เป็นบวกชัดเจน

**Prefetch mechanism (ปัจจุบัน):** APScheduler ภายใน Render (`scheduler.py`) **ปิดการเรียกใช้แล้ว** (คอมเมนต์ `setup_scheduler()` ออกใน `main.py`) เพราะพบว่าหยุดยิงเงียบๆ นาน 22+ ชม.โดยไม่มี error ให้เห็น — สาเหตุจริงคาดว่าเกี่ยวกับ Render dyno sleep ที่ไม่มีตัวปลุกที่เชื่อถือได้ (ตอนนี้แก้ด้วย cron-job.org Job A แทนแล้ว) — โค้ด `scheduler.py` เก็บไว้เผื่อกลับมาใช้ในอนาคต แต่ตอนนี้ไม่ได้ทำงาน

**หมายเหตุ budget:** `datetime.now()` บน Render ใช้ UTC → budget reset = 00:00 UTC = **07:00 Bangkok**

---

## 6. Daily Budget

> ปรับ 2026-07-01: MBBook ตั้งเป้างบจริงไว้ที่ **$10/เดือน (เป้า) / $12/เดือน (เพดานที่รับได้)** — เดิม DAILY_BUDGET ในโค้ดตั้งเพดานไว้ $19.40 สูงกว่าเป้าจริงเกือบเท่าตัว จึงตึงลงให้เหลือ buffer ~15% เหนือ cost จริงที่วัดได้ (Tue-Wed จริง ~$0.52/run) แทน
>
> ✅ **อัพเดต 2026-07-02 — มีข้อมูลจริง Tue-Thu ครบ 4 รอบแล้ว**: $0.515 / $0.526 / $0.539 / $0.510 เฉลี่ย **$0.5225/run** เทียบ budget $0.60/วัน = ใช้ไป ~87% มี buffer พอสมควร ยืนยันว่า Defect #4 (กลัวงบไม่พอ) **ไม่ได้เกิดขึ้นจริง** — ส่วน Monday/Friday ยังไม่มีข้อมูลจริงกับ config ปัจจุบัน (30 tickers) รอ Monday ถัดไป (2026-07-06) ก่อนสรุป Defect #8

| วัน | Limit/วัน | หมายเหตุ |
|-----|-----------|---------|
| Monday | $0.85 | news 3 วัน (Sat+Sun+Mon) — ข้อมูลเก่า (40 tickers) $1.36 เกิน แต่ตอนนี้ 30 tickers แล้ว รอ 2026-07-06 ยืนยัน |
| Tue–Thu | $0.60 | ✅ ยืนยันจริงแล้ว 4/4 รอบ เฉลี่ย $0.5225/run (87% ของ budget) |
| Friday | $0.75 | + นิก optimize — ยังไม่มีข้อมูลจริงกับ 30 tickers |
| **Monthly ceiling (โค้ด)** | **~$13.60** | เผื่อ buffer เหนือเพดานจริง $12 ไว้ก่อน (ดู [Pending.md](../1_Reports/Pending.md) หัวข้อทบทวนหลัง 3 เดือน) |
| **เป้าหมายจริงของ MBBook** | **$10 เป้า / $12 เพดาน** | ติดตามของจริงผ่าน `GET /costs/summary` (dashboard tab Status) — เทรนด์ Tue-Thu ตอนนี้อยู่ในเป้า |

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

**Checkpoint:** ✅ แก้ 2026-07-01 — บันทึกทันทีหลัง**หนุ่มวิเคราะห์เสร็จแต่ละหุ้น** (ไม่รอมด validate ครบชุดแบบเดิม เพราะเป็นขั้นตอนที่นานสุด/เสี่ยงโดนขัดจังหวะสุด) + บันทึกซ้ำอีกรอบหลังมด validate ครบ (ทับด้วยค่า validate แล้ว)
→ ถ้า Render crash กลางคัน `/workflow/resume` จะวิ่งต่อจากตัวที่ค้างจริง (ไม่ใช่เริ่มใหม่หมด)

**Render free tier:** dyno sleep หลัง 15 นาที idle — มี 2 ชั้นกันหลับ (เพิ่มชั้นที่ 2 เมื่อ 2026-07-01):
1. **GitHub Actions Keepalive** (`keepalive.yml`) ทุก 10 นาที — Step 1 wake+retry (6×15s) + Step 2 self-heal งาน 22:00 + Step 3 self-heal prefetch (cache stale >70 นาที → POST `/prefetch` เอง)
2. **Self-ping ในแอป** (`_self_ping_forever()` ใน `main.py`) — ping ตัวเองทุก 8 นาที ตั้งแต่ startup ตลอดชีวิต process ไม่พึ่ง GitHub Actions cron เลย (กันกรณี GH schedule delay/ข้ามรอบ)

`AI_Stocks_Trigger` เองก็มี wake+retry สูงสุด 15 ครั้ง × 10s = 2.5 นาที ก่อน trigger งานจริงตอน 22:00 (เป็นชั้นที่ 3 เฉพาะงานสำคัญนี้)

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

> ✅ จัดระเบียบใหม่ 2026-07-02 22:xx — แยกไฟล์ core app (ต้องอยู่ root ห้ามย้าย เพราะ Render/GitHub บังคับ path) ออกจากไฟล์เอกสาร/สคริปต์อ้างอิง (ย้ายเข้าโฟลเดอร์แล้ว)

```
Dashboard_Share/
├── agents.py          # AI agents ทั้ง 10 ตัว + AgentOrchestrator (ห้ามย้าย — Render import)
├── main.py            # FastAPI app + endpoints + job state (ห้ามย้าย — Render start command)
├── models.py          # SQLAlchemy models (ห้ามย้าย)
├── database.py        # SessionLocal + engine (ห้ามย้าย)
├── scheduler.py       # APScheduler เดิม ปิดใช้งานแล้ว (ห้ามย้าย — ยัง import อยู่ใน main.py)
├── requirements.txt    # ห้ามย้าย — Render build command
├── test_agents.py     # 107 unit tests (agents)
├── test_main.py       # 26 unit tests (endpoints)
├── .github/workflows/  # ห้ามย้าย — GitHub บังคับ path นี้เป๊ะ
│   ├── trigger_workflow.yml  # AI_Stocks_Trigger — เดิม main cron 22:00 จ–ศ ⛔ ปิด schedule แล้ว (เหลือ workflow_dispatch) trigger จริงอยู่ที่ cron-job.org
│   ├── keepalive.yml         # Render Keepalive ⛔ ปิด schedule แล้ว (เหลือ workflow_dispatch)
│   ├── prefetch_hourly.yml   # AI_Stocks_Prefetch ⛔ ปิด schedule แล้ว (เหลือ workflow_dispatch)
│   ├── resume.yml            # ⛔ ปิด schedule แล้ว — workflow_dispatch เท่านั้น
│   └── rotate-api-key.yml    # หมุน API key ทุกวันที่ 1/15 — ยังทำงานปกติ ไม่เกี่ยวกับ trigger
├── frontend/           # React dashboard — ห้ามย้าย (deploy pipeline แยก)
│   └── src/
│       ├── App.jsx        # component หลักเดียว (DashboardV4) — ทุก tab/popup เป็น helper function
│       │                  # ซ้อนอยู่ข้างในไฟล์เดียวกันทั้งหมด (เจตนา กันบั๊ก remount — ดู comment
│       │                  # บรรทัดบนของไฟล์) 1,973 บรรทัด (2026-07-08, ลดจาก 2,081)
│       └── constants.js   # ✅ เพิ่ม 2026-07-08 — ค่าคงที่ล้วนๆ (COLORS/SP/MOCK_NEWS/COMPANY_NAMES/
│                          # GLOBAL_CSS/API_URL) แยกออกจาก App.jsx ลดขนาดไฟล์ ไม่กระทบ logic
│
├── 1_Reports/          # ไฟล์ที่ Cow เขียนรายงาน/สรุปให้ MBBook
│   ├── Output.md        # ผลลัพธ์คำสั่ง PowerShell ที่ MBBook รัน (ยาวเกิน copy)
│   └── Pending.md       # งานค้าง/ปัญหาที่ยังไม่จบ
│
├── 2_Reference/        # เกี่ยวกับงาน แต่ไม่ได้ import/รันจริงในระบบ
│   ├── setup_cronjob_org.py       # สคริปต์ตั้ง 6 cron jobs ครั้งแรก (รันแล้ว เก็บไว้อ้างอิง/รันซ้ำได้ถ้าต้องสร้างใหม่)
│   ├── update_cronjob_weekends.py # สคริปต์แก้ job ให้รันทุกวัน (รันแล้ว)
│   └── prefetch_check_log_20260702.txt  # log การเช็คนัตตี้วันที่ 2 ก.ค. (ไม่ commit ขึ้น git)
│
└── 3_CowContext/       # ไฟล์ที่ Cow ต้องเปิดอ่านก่อนเริ่มงานทุกครั้ง
    ├── Blueprint.md      # ← ไฟล์นี้ (source of truth ของทั้งระบบ)
    └── README.md
```

**⚠️ หมายเหตุสำคัญสำหรับ Cow**: `Blueprint.md` และ `Pending.md` ย้ายจาก root มาอยู่ `3_CowContext/` และ `1_Reports/` แล้วตั้งแต่ 2026-07-02 — กฎ "อ่าน Blueprint.md ก่อนเริ่มงานทุกครั้ง" ให้หมายถึงไฟล์ที่ path ใหม่นี้ (บันทึกไว้ใน project memory แล้วด้วย กันลืมข้ามเซสชัน)

---

## 12. Tech Stack Decisions (Phase 1)

| เรื่อง | ตัดสินใจ | Phase 2 |
|--------|---------|---------|
| Frontend hosting | Vercel / Netlify (ไม่ใช้ Render — ป้องกัน hours เกิน 750) | — |
| DB Migration | `CREATE TABLE IF NOT EXISTS` + manual `ALTER TABLE` ใน startup | Alembic |

---

## 13. Architectural Defect Log (2026-06-27)

> ✅ 2026-07-08: ย่อให้เหลือแค่สรุปสั้นต่อรายการ — narrative การสืบสวนแบบเต็มย้ายไป
> `3_CowContext/Blueprint_Defect_Archive.md` แล้ว (เปิดอ่านเฉพาะตอนต้องสืบสาเหตุปัญหาเก่าแบบละเอียด)

| # | Defect | สถานะ | สรุปสั้น |
|---|--------|--------|--------|
| 1 | Colson ไม่อยู่ใน workflow order | ✅ แก้แล้ว | เป็น Event-Driven Agent ผ่าน `/trade-update` ไม่ใช่ pipeline |
| 2 | OOM Risk บน Render 512MB | ⏳ Monitor (passive, ไม่มีหลักฐานใหม่) | ไม่ใช่ OOM — instance เปลี่ยนบ่อยมาจาก Render free-tier sleep/wake ปกติ |
| 3 | Race Condition `/workflow/resume` | ❌ ไม่มี defect | มี guard `if _job["status"]=="running"` อยู่แล้ว |
| 4 | Budget $0.85 ไม่พอ 40 tickers | ✅ ปิดเคส — ไม่เกิดขึ้นจริง | เฉลี่ยจริง $0.5225/run เทียบ budget $0.60 มี buffer |
| 5 | Timezone Mismatch (นิก/budget) | ❌ ไม่มี defect | 22:00 Bangkok = 15:00 UTC เสมอ ไม่ข้ามวัน |
| 6 | Resume loop หลัง BUDGET_EXCEEDED | ✅ แก้แล้ว | เช็ค last log วันนี้ก่อน resume |
| 7 | DB Concurrency Lock (Harry vs Colson) | ❌ ไม่มี defect | PostgreSQL MVCC จัดการเอง แฮรี่ read-only |
| 8 | Monday Mode Budget Deficit | ✅ ปิดเคส (ข้อมูลจริง 2026-07-06 อยู่ในเกณฑ์) | ลดเหลือ 30 tickers + budget $0.85 แก้ปัญหาได้ |
| 9 | LLM ล้มเมื่อ PE/MarketCap = None | ❌ ไม่มี defect | Prompt + `_safe_float()` รองรับ N/A แล้ว |
| 10 | LINE Notification Spam | ❌ ไม่มี defect | เรียกแค่ 2 จุด (จบสำเร็จ/exception) ไม่ส่งรายตัว |
| 11 | Prefetch 2 ระบบซ้อนกัน (GH Actions + APScheduler) | ✅ แก้แล้ว | ปิด `prefetch.yml` schedule เดิม เหลือ APScheduler ระบบเดียว |
| 12 | Workflow 22:00 ไม่เคยเสร็จอัตโนมัติเลย ~2 สัปดาห์ | ✅ แก้แล้ว + ยืนยันจริง 2026-07-02 | root cause: checkpoint เดิม save ครั้งเดียวท้าย batch (ไม่ทีละตัว) + self-heal ยิง `/workflow` ผิด endpoint — แก้ทั้งคู่แล้ว |
| 13 | LINE แจ้ง BUDGET_EXCEEDED ตี 3-4 ทุกคืน (3 วันติด) | ✅ แก้แล้ว | BUDGET_EXCEEDED/REJECTED ไม่เคยถูกบันทึก/skip ทำให้ self-heal ไล่ยิงทั้งคืน — แก้บันทึก+skip-list+จำกัดหน้าต่างเวลา |
| 14 | Prefetch cache ค้าง 22+ ชม. | ✅ แก้แล้ว + ยืนยันจริง | `/prefetch` ไม่มี lock กันรันซ้อน ชน rate limit ทั้งวัน — เพิ่ม `_prefetch_lock` |
| 15 | GitHub Actions cron ไม่เสถียรทั้งระบบ | ✅ แก้แล้ว + ยืนยันจริง 2026-07-02 | keepalive.yml รันจริงแค่ 21/790 ครั้ง — ย้าย trigger ทั้งหมดไป **cron-job.org** แล้ว |
| 16 | นิก ข้าม optimization ทุกวันศุกร์มาตลอด | ✅ แก้แล้ว 2026-07-04 | agents.py โตเกิน hard guard 80000 chars เงียบๆ — ยกเพดานเป็น 300000 ⚠️ ยังส่งแค่ 8000 ตัวอักษรแรกให้ Claude วิเคราะห์อยู่ (ไม่แก้) |
| 17 | `/stocks` 500 หลัง deploy `change_pct` (2026-07-08) | ✅ แก้แล้ว + ยืนยันจริงผ่าน browser | `main.py` อ้าง `hc.company_name` ค้าง uncommitted มาตั้งแต่ 07-05 คู่กับ `models.py` — commit `models.py` (`1145680`) แก้ (deploy รอบแรก fail ซ้ำจาก Neon ชั่วคราว, retry ผ่าน) |

**ถ้า Defect 2, 4 หรือ 8 เกิดจริงวันจันทร์:**
- OOM → เพิ่ม `gc.collect()` หลัง checkpoint แต่ละ ticker
- Budget เกิน → ⚠️ (อัพเดต 2026-07-01) **ห้ามแก้โดยเพิ่ม limit แล้ว** เพราะเป้าจริงของ MBBook คือ $10-12/เดือน (ดู section 6) การขึ้น limit จะยิ่งหนีเป้าไปอีก — ให้แก้ที่ต้นทุนแทน เช่น downgrade มด จาก Sonnet → Haiku, ลดจำนวน tickers, หรือขยาย prompt caching ให้ครอบคลุมมากขึ้น

---

## 14. สถานะ Phase 1 Testing

**เป้าหมาย:** รัน 60 วัน → วัด ROI

**✅ อัพเดต 2026-07-04 — นิยาม ROI ชัดเจนแล้ว (เดิมเขียนแค่ "ROI > 50%" กำกวม ไม่รู้หมายถึงอัตราทายถูก
หรือผลตอบแทน — คุยกับ MBBook แล้วสรุปเป็น 2 ตัวชี้วัดแยกกัน):**

1. **Win rate** (BUY ราคาขึ้นจริง / SELL ราคาลงจริง = ถูก) วัด 2 ระยะเวลาแยกกัน:
   - @14 วันหลังสัญญาณ — เกณฑ์ **75%**
   - @30 วันหลังสัญญาณ — เกณฑ์ **75%**
2. **Avg return %** (เฉพาะสัญญาณ BUY — SELL ไม่มีผลตอบแทนที่วัดเป็น % ได้ตรงๆ) ที่ระยะ 30 วัน
   (≈ 1 เดือน) — เป้า **13%/เดือน**

- ทั้งสองตัวชี้วัด < เกณฑ์ → Debug (ดู WorkflowLog + nik suggestions)
- ทั้งสองตัวชี้วัดผ่านเกณฑ์ → Upgrade (เพิ่ม tickers, feature ใหม่)

**Data infra:** ตาราง `signal_history` (insert-only ทุกคืนต่อหุ้น เก็บ ticker/signal/confidence/price/timestamp
— ไม่ทับเหมือน `stocks`) + endpoint `GET /roi/summary` คำนวณให้อัตโนมัติ (`agents.py::calculate_roi`)
สัญญาณที่ยังไม่ครบอายุ (< 14/30 วัน) จะไม่ถูกนับ ต้องรอเวลาให้ข้อมูลสะสมก่อนตัวเลขจะมีความหมาย

**ปัจจุบัน:** 30 tickers · live บน Render · 133 tests pass (ก่อนเพิ่ม ROI tests รอบนี้) · cron-job.org active · cost จริง $0.52/run (เป้า $0.43)
