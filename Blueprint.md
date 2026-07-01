# Blueprint — AI Stock Analyzer V4

> อ่านไฟล์นี้ก่อนเริ่มงานทุกครั้ง
> อัพเดตล่าสุด: 2026-07-01

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
| `workflow_logs` | timestamp, status (COMPLETE/REJECTED), stocks_analyzed, buy/sell/hold signals, needs_review, summary, cost_usd | เอ |
| `hourly_cache` | ticker, price, week52_high/low, pe_ratio, market_cap, source, at_new_high/low, fetched_at | นัตตี้ prefetch |
| `news_cache` | ticker, news_json, news_count, fetched_at | นัตตี้ prefetch |
| `nik_suggestions` | summary, diff_text, status (pending/complete/failed), error_message, applied_at | นิก |

**Migration:** startup event ใน `main.py` รัน `ALTER TABLE / CREATE TABLE IF NOT EXISTS` อัตโนมัติ

---

## 5. Schedule (GitHub Actions · Bangkok time GMT+7)

> ย้ายจาก cron-job.org → GitHub Actions ทั้งหมด เมื่อ 2026-06-27
> GitHub Secret: `RENDER_URL = https://ai-stock-analyzer-msli.onrender.com`

| Workflow | Schedule (UTC) | Bangkok | วัน | หน้าที่ |
|----------|---------------|---------|-----|---------|
| `AI_Stocks_Trigger` | 15:00 | 22:00 | Mon–Fri | Main trigger · Monday ส่ง `?include_weekend=true` · wake Render ก่อน (retry 15×) |
| `AI_Stocks_Prefetch` | ⛔ **ปิด schedule แล้ว 2026-07-01** — เหลือ `workflow_dispatch` (manual/debug เท่านั้น) | — | — | เดิม POST `/prefetch` ทุกชั่วโมง — ย้ายหน้าที่ไป APScheduler ภายใน Render แทน (กัน fetch ซ้ำซ้อน 2 ระบบ) |
| `Render Keepalive` | ทุก 10 นาที | ทุก 10 นาที | ทุกวัน | ping `/health` + **self-heal**: ถ้า weekday + หลัง 22:00 + ยังไม่มี run วันนี้ → trigger อัตโนมัติ |
| `Workflow Resume` | 15:15–16:45 ทุก 15 นาที | 22:15–23:45 | Mon–Fri | POST `/workflow/resume` fallback ถ้า crash |

**Prefetch mechanism (ปัจจุบัน):** APScheduler ภายใน Render process เดียว (`scheduler.py`) — cron ในตัว ทุกชั่วโมง 02:00–14:00 UTC (นาที 05) + pre-warm 14:45 UTC · พึ่ง `Render Keepalive` (ping `/health` ทุก 10 นาที) กันไม่ให้ dyno sleep ระหว่างวัน ไม่ต้องพึ่ง GitHub Actions cron แยกแล้ว

**หมายเหตุ budget:** `datetime.now()` บน Render ใช้ UTC → budget reset = 00:00 UTC = **07:00 Bangkok**

---

## 6. Daily Budget

> ปรับ 2026-07-01: MBBook ตั้งเป้างบจริงไว้ที่ **$10/เดือน (เป้า) / $12/เดือน (เพดานที่รับได้)** — เดิม DAILY_BUDGET ในโค้ดตั้งเพดานไว้ $19.40 สูงกว่าเป้าจริงเกือบเท่าตัว จึงตึงลงให้เหลือ buffer ~15% เหนือ cost จริงที่วัดได้ (Tue-Wed จริง ~$0.52/run) แทน

| วัน | Limit/วัน | หมายเหตุ |
|-----|-----------|---------|
| Monday | $0.85 | news 3 วัน (Sat+Sun+Mon) — ยังไม่มีข้อมูลจริง ใช้ประมาณการ + buffer |
| Tue–Thu | $0.60 | ปกติ — cost จริงวัดแล้ว ~$0.52/run |
| Friday | $0.75 | + นิก optimize — ยังไม่มีข้อมูลจริง ใช้ประมาณการ + buffer |
| **Monthly ceiling (โค้ด)** | **~$13.60** | เผื่อ buffer เหนือเพดานจริง $12 ไว้ก่อน (ดู [Pending.md](Pending.md) หัวข้อทบทวนหลัง 3 เดือน) |
| **เป้าหมายจริงของ MBBook** | **$10 เป้า / $12 เพดาน** | ติดตามของจริงผ่าน `GET /costs/summary` (dashboard tab Status) |

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
│   ├── keepalive.yml         # Render Keepalive — ทุก 10 นาที + self-heal trigger
│   ├── prefetch.yml          # AI_Stocks_Prefetch — ทุกชั่วโมง 09:00–21:45 จ–ศ
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
| 2 | OOM Risk บน Render 512MB | ⏳ Monitor (แก้ไข 2026-07-01 ค่ำ) | ตอนแรกสงสัยว่า instance เปลี่ยนบ่อย (cmvkw → 5j8m9 → c5lgt) มาจาก OOM/crash — เช็ค Render Events API แล้วพบว่า**ไม่ใช่** ทุก instance ตรงกับ `deploy_started/ended` ที่สำเร็จทั้งหมด (10 deploys วันนี้ ไม่มี `server_failed`/`server_hardware_failure` เลย) ส่วน instance ที่ไม่ตรง deploy ไหน (~21:40 น.) อธิบายได้จาก Render free-tier sleep/wake ปกติ (keepalive Step 1 wake+retry ทำงานถูกต้อง) ไม่ใช่ OOM — กลับสถานะเป็น Monitor ตามเดิม ยังไม่มีหลักฐาน OOM จริง |
| 3 | Race Condition `/workflow/resume` | ❌ ไม่มี defect | Code มี guard บรรทัด 378 อยู่แล้ว: `if _job["status"] == "running": return already_running` |
| 4 | Budget $0.85 ไม่พอ 40 tickers | ⏳ Monitor | ยังไม่มี cost จริง — prompt caching ลด cost ได้ 10× รอดู `cost_usd` ใน WorkflowLog วันจันทร์ก่อน |
| 5 | Timezone Mismatch (นิก / budget) | ❌ ไม่มี defect | 22:00 Bangkok = 15:00 UTC = วันเดียวกันเสมอ ไม่ข้ามวัน weekday() ถูกต้อง |
| 6 | Resume loop หลัง BUDGET_EXCEEDED | ✅ แก้แล้ว | เพิ่ม check ใน `/workflow/resume`: ถ้า last log วันนี้เป็น BUDGET_EXCEEDED/COMPLETE/ABORTED → return skipped |
| 7 | DB Concurrency Lock (Harry vs Colson) | ❌ ไม่มี defect | PostgreSQL MVCC จัดการ read/write concurrency ได้เอง แฮรี่ read-only → ไม่มี deadlock risk |

| 8 | Monday Mode Budget Deficit | ⏳ Monitor | $1.20 ตั้งไว้แล้วสำหรับ 72hr news — รอดู cost จริงวันจันทร์ก่อน (เหมือน Defect 4) |
| 9 | LLM ล้มเมื่อ PE/MarketCap = None | ❌ ไม่มี defect | Prompt บรรทัด 668 รองรับแล้ว: "ถ้า P/E หรือ Market Cap เป็น N/A ให้วิเคราะห์จาก price แทน" + `_safe_float()` จัดการ edge cases |
| 10 | LINE Notification Spam | ❌ ไม่มี defect | `_send_line_notification()` ถูกเรียกแค่ 2 จุด: จบสำเร็จ 1 ครั้ง + exception 1 ครั้ง ไม่มีการส่งรายตัว |
| 11 | Prefetch 2 ระบบซ้อนกัน (GitHub Actions + APScheduler) | ✅ แก้แล้ว (2026-07-01) | Commit ก่อนหน้าเพิ่ม APScheduler แต่ลืมปิด `AI_Stocks_Prefetch` cron เดิม → log ยืนยันมี POST `/prefetch` จากภายนอก (GH Actions) ทำงานอยู่จริง แยกไม่ออกว่ารอบไหนทำงาน → ปิด schedule ใน `prefetch.yml` เหลือแค่ `workflow_dispatch` (manual/debug) ให้ APScheduler เป็นระบบเดียว |
| 12 | Workflow 22:00 ไม่เคยเสร็จอัตโนมัติเลย ~2 สัปดาห์ | ✅ แก้แล้ว (2026-07-01) | ตรวจ `/workflow/history` พบ 7 runs ทั้งหมดตั้งแต่ 23 มิ.ย. เสร็จเวลาไม่แน่นอน (21:29-21:31 UTC หรือ 01:53 UTC) ไม่เคยใกล้ 22:00-23:00 Bangkok เลย ต้นเหตุ 2 จุด: (1) Render free-tier sleep ฆ่า background thread กลางคัน — ก่อนหน้านี้พึ่งแค่ GitHub Actions Keepalive ภายนอกซึ่งไม่แม่นยำพอ (2) **จุดอ่อนสำคัญกว่า**: `_checkpoint_database()` เดิมเรียกแค่ครั้งเดียวหลังมด validate ครบทั้งชุด 30 ตัว ไม่ได้ save ทีละตัวระหว่างหนุ่มวิเคราะห์ (ขั้นตอนที่นานสุด/เสี่ยงโดนขัดจังหวะสุด) → โดนฆ่ากลางคันแล้วงานหายหมด ไม่มีอะไรให้ resume ต่อ ซ้ำร้าย `keepalive.yml` self-heal เดิมยิง `/workflow` (restart ใหม่ทั้งชุด) ไม่ใช่ `/workflow/resume` → เสียเงินวิเคราะห์ซ้ำ. **แก้แล้ว**: (a) ย้าย checkpoint มา save ทีละตัวทันทีหลังหนุ่มวิเคราะห์แต่ละหุ้นเสร็จ (agents.py `num_analyze_stocks`) (b) แก้ `keepalive.yml` self-heal ให้ยิง `/workflow/resume` แทน `/workflow` (c) ปิด schedule ของ `resume.yml` เดิม (ซ้ำซ้อนกับ keepalive self-heal ที่ครอบคลุมกว้างกว่าแล้ว) เหลือแค่ `workflow_dispatch` — พิจารณา Render Starter ($7/mo, ไม่มี sleep เลย) แล้ว **MBBook เลือกไม่อัพเกรด ใช้ free tier ต่อ** (2026-07-01) |

**ถ้า Defect 2, 4 หรือ 8 เกิดจริงวันจันทร์:**
- OOM → เพิ่ม `gc.collect()` หลัง checkpoint แต่ละ ticker
- Budget เกิน → ⚠️ (อัพเดต 2026-07-01) **ห้ามแก้โดยเพิ่ม limit แล้ว** เพราะเป้าจริงของ MBBook คือ $10-12/เดือน (ดู section 6) การขึ้น limit จะยิ่งหนีเป้าไปอีก — ให้แก้ที่ต้นทุนแทน เช่น downgrade มด จาก Sonnet → Haiku, ลดจำนวน tickers, หรือขยาย prompt caching ให้ครอบคลุมมากขึ้น

---

## 14. สถานะ Phase 1 Testing

**เป้าหมาย:** รัน 60 วัน → วัด ROI
- ROI > 50% → Upgrade (เพิ่ม tickers, feature ใหม่)
- ROI < 50% → Debug (ดู WorkflowLog + nik suggestions)

**ปัจจุบัน:** 30 tickers · live บน Render · 133 tests pass · GitHub Actions active · cost จริง $0.52/run (เป้า $0.43)
