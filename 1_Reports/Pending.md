# Pending — AI Stock Analyzer V4

## ✅ 2026-07-11 (Fable) — UI Reskin Phase 2 ครบ 11 ข้อ + ต่อข่าวจริง (ปิด #51)

**ทำเสร็จ (ยังไม่ commit — รอ MBBook verify ที่เครื่องจริงก่อน):**
1. **UI Reskin Phase 2 ครบทั้ง 11 ข้อ** ตาม `3_CowContext/UI_Reskin_Phase2_Plan.md`:
   nav pill bar Desktop + bottom nav Mobile + navdot ทอง (unread) · ปุ่มทองสเปค .gold-btn ·
   badge BUY/SELL/HOLD สเปคเดียว (HOLD เทา→ม่วง) · avatar วงกลม 34px สีต่อ ticker (palette จาก
   mockup) · KPI cards 22/700 + change pill 999 · ตาราง dtable (header strip โค้ง 14, zebra,
   row 44px, hover 0.05 ผ่าน class .trow) · SlidingPill gradient ม่วง · news unread treatment
   (ขอบซ้ายทอง + จุดทอง pulse 2 ครั้ง + การ์ดอ่านแล้วจาง) · modal กระจก strong radius 24 +
   danger-btn · กวาด radius ทั้งไฟล์ (24/14/9/999)
2. **🔥 ต่อข่าวจริงเข้า News tab (MBBook ทักว่าข่าว 4 ข่าววนซ้ำทุกวัน)** — root cause: หน้า News
   โชว์ MOCK_NEWS มาตลอด ไม่เคยต่อ backend (ข่าวจริงของนัตตี้อยู่ใน news_cache ครบ ไม่ได้เสียของ) →
   เพิ่ม `GET /news` ใน main.py (dedup ข้าม ticker + id md5 คงที่) + ลบ MOCK_NEWS/ปุ่มข่าวทดสอบ/
   extraNews ออกจาก frontend ทั้งหมด + fetchNews ใน initial load และ poll 5 นาที + tests 3 ตัว
   (`TestNewsEndpoint` ใน test_main.py → รวมเป็น 175)
   ⚠️ ข้อจำกัดปัจจุบัน: news_cache เก็บย้อนหลัง ~25 ชม./ticker (cleanup ใน prefetch) — ถ้าอยากได้
   ข่าวย้อน 7 วันจริงต้องขยาย retention (คุยกันก่อน ยังไม่แก้) · sentiment/impact ไม่มีในข่าวจริง
   (yfinance/Finnhub ไม่ให้มา) UI ซ่อนป้ายให้แล้ว ไม่แต่งข้อมูลเอง
3. **Skeleton loading ทุกแท็บ** (MBBook ทวงถาม — อยู่ใน UX baseline ของ Redesign Prompt v2/v3
   แต่ตกหล่นจาก Phase 2 Plan): shimmer CSS จาก mockup + skeleton cards ตอนโหลดแรก —
   Portfolio (กราฟ+KPI+รายการ), Tickers (เพิ่ม state `stocksLoaded` แยกเคสโหลดอยู่/โหลดแล้วว่าง),
   News (แทนข้อความ "กำลังโหลด..." + error state ถ้า /news ล้ม ไม่ shimmer ค้าง), System
   (กราฟต้นทุน + Win Rate + นิก)
4. sandbox mount stale รอบที่ 4 (bash เห็น App.jsx สั้นกว่าจริง 2038 vs 2085 บรรทัด) — ตรวจทุกอย่าง
   ผ่าน Read/Grep ฝั่ง Windows แทน esbuild ใน sandbox ตามกฎ Handoff ข้อ 5 → MBBook ต้อง verify เอง

**MBBook ต้องทำ (ตามลำดับ):**
1. `cd D:\AI_Project\Dashboard_Share` → `.\.venv\Scripts\python.exe -m pytest test_main.py test_agents.py -v > 1_Reports\Output.md 2>&1` (ต้อง 175 passed)
   ⚠️ ต้องใช้ python ใน `.venv` เท่านั้น — `python` เฉยๆ ชี้ไป Python 3.14 ของเครื่องที่ไม่มี pytest
   (เจอจริง 2026-07-11: Output.md ขึ้น "No module named pytest")
2. `cd frontend` → `npm start` → เทียบ mockup (`3_CowContext/UI_Preview_v1.html`) ทีละแท็บ/view
3. ผ่านแล้ว: `git add -A` → commit → `git push` → Render auto-deploy → เปิดแอปดูหน้า News
   ว่าข่าวจริงขึ้น (ถ้า cache ว่างรอ prefetch รอบถัดไป นาที :05)

---

> ## 🎯 สถานะส่งไม้ต่อ (2026-07-09 ~10:45 — จบแชทยาว Fable)
> **เสร็จวันนี้:** deploy PEG+company profile (`510d595`) · ระบบ password + PIN 6 หลัก + lockout (`2de63a4`/`efb3da9`, 172 tests) ·
> seed พอร์ตจริง 24 tickers · Vercel setup (`vercel.json` + แก้ unused vars หลัง build fail) · UI Reskin **Phase 1** tokens (`845faee`)
> **แชทใหม่ทำต่อ:** (1) **UI Phase 2** → `3_CowContext/UI_Reskin_Phase2_Plan.md` + `UI_Reskin_Phase2_Preview.html` (รอ MBBook confirm รายข้อ)
> (2) **Backend** → รายการค้างด้านล่าง: verify PEG/company_name (หลัง prefetch 09:05) · เคส run 08 ก.ค. ไม่ลง history · costSummary/reportList
> **MBBook ค้าง:** `git push` รอบล่าสุด (Reskin Phase 1 + docs) + ดูผล Vercel build

> ✅ 2026-07-08: เคลียร์ไฟล์นี้ให้เล็กลงแล้ว — ประวัติงานเก่า (ก่อน 2026-07-08 ทั้งหมด) ย้ายไป
> `1_Reports/Pending_Archive.md` แยกแล้ว (เก็บไว้อ้างอิงถ้าต้องสืบสาเหตุปัญหาเก่า ไม่ต้องอ่านตอนเริ่มงาน
> ปกติ) ไฟล์นี้เหลือแค่ session ล่าสุด + รายการที่ยังค้างจริงเท่านั้น

---

## ✅ 2026-07-08 (รอบ 2 — Fable) — เขียนโค้ด PEG + เคลียร์ไฟล์ค้าง + Workplan ให้ Sonnet 5

**Fable ทำเสร็จ (ยังไม่ commit — Sonnet 5 รัน flow ต่อตาม `3_CowContext/Sonnet5_Workplan.md`):**
1. พบ+ลบ **NUL bytes 7,024 ตัว**ท้าย `App.jsx` (เศษ write crash) → diff กับ HEAD เป็นศูนย์ ไม่ต้อง commit
2. ตรวจโค้ด company profile ใน `agents.py` (ค้าง uncommitted ตั้งแต่ 05 ก.ค. — เสี่ยงแบบ Defect #17)
   → import/chain ครบ พร้อม deploy
3. **เขียนโค้ด PEG ratio ใหม่ทั้งชุด**ใน `agents.py`: Alpha Vantage OVERVIEW rotation ≤20 ตัว/วัน
   (เฉพาะ prefetch 02:xx UTC = 09:05 Bangkok), carry-forward 48 ชม., rate-limit guard (Note/Information
   → break batch), ห่อ try/except ไม่กระทบ prefetch ราคา + **tests 9 ตัว** (`TestPegAlphaVantage`)
4. ลบ `UI_Spec.md` (MBBook สั่ง), เพิ่ม `.claude/` ใน `.gitignore`, ยืนยัน v2/v3 redesign prompt ต่างกันจริง (เก็บทั้งคู่)

**อัพเดตเที่ยงคืน 09 ก.ค. (MBBook token ใกล้หมด — Fable ทำต่อเองจนสุดทาง):**
- เจอ **sandbox mount stale หนัก**: `test_agents.py`/`.gitignore` ไม่ sync + `agents.py` โดนตัดท้ายหาย
  107 บรรทัด (มองจาก bash) — ซ่อมครบโดยเทียบกับไฟล์จริงฝั่ง Windows แล้ว py_compile ผ่านทุกไฟล์
  (ยืนยันกฎ Handoff ข้อ 5 อีกครั้ง — bash เชื่อไม่ได้กับไฟล์ที่เพิ่งแก้)
- **รัน pytest จริงใน sandbox** (uv venv, Python 3.10, pin เดียวกับ requirements.txt): ✅ **158 passed**
- **Commit แล้ว 2 ก้อน**: `510d595` (code: agents.py + test_agents.py + database.py + .gitignore)
  + docs commit ถัดไป — **ยังไม่ push** (sandbox ไม่มี GitHub credential)

**เหลือทำจริงๆ แค่นี้:**
1. **MBBook รัน `git push` เองที่ terminal** (คำสั่งเดียว ไม่เปลือง token) → Render auto-deploy
2. Verify D.1 (company_name หลัง prefetch รอบถัดไป) + D.2 (peg_ratio เช้าวันถัดไปหลัง 09:10) — flow อยู่ใน
   `3_CowContext/Sonnet5_Workplan.md` งาน D

---

## ✅ 2026-07-08 — Portfolio/System React port + day-change % + production outage (เกิด-แก้ในวันเดียว)

**1. พอร์ต mockup (`UI_Preview_v1.html`, confirm แล้วรอบก่อน) เข้า `App.jsx` จริง**
- Portfolio period selector: Monthly/Yearly/Cumulative (ตัด Daily, ใช้ English label) — ลบ
  `dateRangeMode`/`customStart`/`customEnd`/`dateDropdownOpen` (dead code)
- Desktop portfolio-hero layout: กราฟ 70% + 3 การ์ด KPI 30% เคียงข้างกัน (`grid-template-columns:2.3fr 1fr`)
- ลบ `DesktopValueBarChart` (กราฟ ฿ มูลค่ารวม) — MBBook ยืนยันให้ Desktop ใช้กราฟ % เหมือน Mobile ทั้งหมด
- System tab: Monthly cost view (6 เดือนรวมเดือนปัจจุบัน) + Daily แสดงยอดจริงวันนี้ + English label
  (Daily/Monthly/Cumulative)
- Pill button centering fix (`SlidingPill` เพิ่ม `minWidth:84, textAlign:center`)
- **ลบปุ่มลบ (ถังขยะ) ที่การ์ด/แถว Tickers ออก** — เหลือลบได้ทางเดียวคือใน popup รายละเอียดหุ้นเท่านั้น
  ตามที่ MBBook เคยขอไว้ (ทั้ง `TickerCard` Mobile และ `TickersTable` Desktop)

**2. เพิ่ม day-change % ("เปลี่ยนแปลง") ต่อ ticker ใน Tickers tab**
- เดิม column นี้ว่างเปล่าไม่มีข้อมูลเลย — MBBook ถามว่าควรโชว์อะไร เลือก "เพิ่ม backend คำนวณจริง"
- ใช้ตาราง `signal_history` ที่มีอยู่แล้ว (insert-only บันทึกราคาทุกคืนต่อ ticker เพื่อคำนวณ win rate)
  เอา 2 แถวล่าสุดมาเทียบกันได้เลย ไม่ต้องเพิ่มตารางใหม่ — เพิ่ม `change_pct` ใน response ของ `GET /stocks`
  (`main.py`) + แสดงผลใน `TickerCard`/`TickersTable` (ลูกศร ▲/▼ + สี เขียว/แดง, `—` ถ้าข้อมูลไม่ถึง 2 คืน)

**3. 🔥 Production outage: `/stocks` 500 Internal Server Error หลัง deploy (เกิด-วินิจฉัย-แก้ในวันเดียว)**
- อาการ: หลัง push `change_pct` (commit `5238963`) หน้า Tickers ขึ้น "0/30 ตัว" + กดเพิ่มหุ้นก็ไม่มา
- **ไม่ใช่บั๊กจาก `change_pct` ที่เพิ่งเพิ่ม** — hotfix ห่อ try/except (commit `cb8dde0`) ไม่ช่วย เช็ค log
  จริงจาก Render เจอ root cause แท้จริง: `main.py` มีโค้ดอ้าง `hc.company_name`/`hc.company_description`
  (จาก `HourlyCache`) ค้าง **uncommitted มาตั้งแต่ 2026-07-05 (รอบ 5)** — commit `5238963`/`cb8dde0` วันนี้
  เป็นครั้งแรกที่โค้ดนี้ขึ้น production จริง แต่ `models.py` (ที่ประกาศ field พวกนี้เป็น SQLAlchemy Column)
  ก็ค้าง uncommitted คู่กันเหมือนกัน → `AttributeError: 'HourlyCache' object has no attribute 'company_name'`
- แก้: commit `models.py` (เพิ่ม `company_name`/`company_description` Column บน `HourlyCache`) → push
  commit `1145680`
- **Deploy รอบแรกของ `1145680` Fail ต่ออีกชั้น** — สาเหตุคนละเรื่อง: Neon Postgres ตอบ
  `Control plane request failed` ชั่วคราวตอน startup migration พยายาม connect DB (ไม่เกี่ยวกับโค้ด) —
  กด Manual Deploy retry ผ่าน ยืนยันผลจริงผ่าน browser ว่า `/stocks` กลับมาใช้งานได้ปกติแล้ว (28 tickers,
  `change_pct` ขึ้นถูกต้อง)
- **บทเรียน**: ไฟล์ที่ `git status` ขึ้น `modified` ค้างนาน (ไม่ commit) เสี่ยงมาก ถ้ามีไฟล์อื่นที่พึ่งพา field
  จากมันแล้วดัน commit ไปก่อนโดยไม่รู้ตัว — ควรเช็ค `git status`/`git diff` ให้ครบทุกไฟล์ที่เกี่ยวข้องก่อน
  push งานใหญ่ ไม่ใช่แค่ไฟล์ที่ตั้งใจแก้

**4. ✅ แก้ขนาดการ์ด Portfolio hero (Desktop) — MBBook ยืนยันแล้วว่าสวยงามเรียบร้อยดี**
- หลัง fix #1 การ์ดกราฟ vs 3 การ์ด KPI สูงไม่เท่ากัน (การ์ดกราฟเตี้ยกว่าเพราะ `height:200` ตายตัว ไม่ยอมโต
  ตาม grid stretch) → เพิ่ม `fill` prop ให้ `BarChart`/`CumulativeLineChart` (`flex:1` แทน `height:200`
  เฉพาะ Desktop, Mobile ไม่กระทบ)
- แก้แล้วพบว่าสูงเท่ากันจริง แต่ "สูงเกินไปทั้งคู่" (KPI cards ใช้ font/padding/badge ใหญ่กว่า mockup ต้นฉบับ
  มาก — label 13.5px vs mockup 11.5px, badge padding 4px 12px vs mockup 3px 9px) → ย่อ font/padding/gap
  เฉพาะโหมด `sidebar` ให้ตรงกับ mockup มากขึ้น

**5. ✅ แก้ตัวเลข "+X%" ในกราฟ Cumulative เพี้ยนไม่สมส่วน (ผลข้างเคียงจาก fix #4)**
- root cause: label เดิมเป็น SVG `<text>` ในหน่วย viewBox ตายตัว (600×180) ร่วมกับ
  `preserveAspectRatio="none"` (ยืด SVG เต็ม container แบบไม่รักษาสัดส่วน) — พอการ์ดกราฟเปลี่ยนความสูงจาก
  fix #4 สัดส่วนกว้าง:สูงจริงเบี้ยวไปจาก viewBox เดิมมาก ตัวเลขเลยถูกยืดเพี้ยนไปด้วย (เฉพาะโหมด Cumulative
  — Monthly/Yearly ใช้ font ปกติไม่ใช่ SVG text เลยไม่โดน)
- แก้: ย้าย label ออกมาเป็น `<span>` HTML ธรรมดา วางตำแหน่งด้วย % ของ container แต่ font-size เป็น px จริง
  ไม่ยืดตาม viewBox — MBBook ยืนยันแล้วว่าสวยงามเรียบร้อยดี ตรงอื่นทำงานปกติทั้งหมด

**6. ✅ แยก `constants.js` ออกจาก `App.jsx` (ลดขนาดไฟล์ — เสี่ยงศูนย์)**
- ย้าย `COLORS`/`SP`/`MAX_TICKERS`/`MOCK_NEWS`/`COMPANY_NAMES`/`GLOBAL_CSS`/`API_URL` (ค่าคงที่ระดับ
  module ไม่แตะ state/hook เลย) ไปไฟล์ `frontend/src/constants.js` แยก แล้ว `import` กลับเข้า `App.jsx`
  เหมือนเดิมทุกค่า — `App.jsx` ลดจาก 2,081 → 1,973 บรรทัด ไม่กระทบการทำงานใดๆ (verify แล้วไม่มีไฟล์อื่น
  import ค่าพวกนี้จาก `App.jsx` โดยตรง)
- **ยังไม่ได้ทำต่อ (ตัดสินใจหยุดไว้ก่อน)**: การแยก component ที่ยังผูก state ผ่าน closure (เช่น `BarChart`
  ใช้ `isMobile`) ไปไฟล์แยก — เสี่ยงกว่า (ต้องเปลี่ยนวิธีเรียกจาก `Foo()` เป็น `<Foo prop=.../>` และไม่มี
  automated test คอยจับ) รอ MBBook ตัดสินใจว่าจะเดินหน้าต่อไหม

**7. ✅ เคลียร์ไฟล์เอกสารให้เล็กลง** — `Pending.md` (109KB→เล็กลงมาก), `Blueprint.md`, `Handoff.md`
ลดความซ้ำซ้อน/ประวัติเก่าออก ตามที่ MBBook ขอ (ดูรายละเอียดการจัดระเบียบท้ายไฟล์นี้)

---

## ✅ 2026-07-09 (~01:30) — ระบบ password dashboard (Fable ทำจบ รอ MBBook push + ตั้งรหัส)

- **Backend** (`main.py`): middleware เช็ค `X-Auth-Token` ทุก endpoint ยกเว้น PUBLIC_ROUTES
  (/, /health, /auth/login, /prefetch, /workflow, /workflow/resume, /docs — ที่ cron-job.org ใช้)
  + `POST /auth/login` แลก password → token (sha256, ไม่เก็บรหัสตรงใน browser) — เปิดใช้โดยตั้ง env
  `DASHBOARD_PASSWORD` (ไม่ตั้ง = auth ปิด, backward compatible, OPTIONS/CORS ผ่านเสมอ + 401 มี ACAO)
- **Frontend**: หน้า login กลางจอ (ตามกติกา Handoff — LoginView() เรียกเป็น function, hooks top-level)
  + `authFetch` ใน constants.js แนบ token อัตโนมัติทั้ง 12 จุด — login สำเร็จ → reload โหลดข้อมูลใหม่
- **Tests: 168 passed** (158 + 10 auth) รันจริงใน sandbox venv — commit `2de63a4` (รวม seed/wipe scripts)
- **เจอ mount ตัดไฟล์อีกรอบ** (main.py ขาดท้าย, test_main/App.jsx ไม่ sync) — ซ่อมด้วยวิธี
  git HEAD + re-apply edits ผ่าน bash (pattern เดิมจาก agents.py เมื่อคืน ใช้ได้ผลอีกครั้ง)
- **รอ MBBook**: (1) `git push` (2) ตั้ง `DASHBOARD_PASSWORD` ใน Render → Environment (redeploy อัตโนมัติ)
  + ใส่ใน `.env` local ด้วย (3) รัน seed script ถ้ายังไม่ได้รัน (4) Vercel deploy เมื่อพร้อม
- **รอบ 2 (~02:00)**: เปลี่ยนเป็น **PIN 6 หลัก** ตาม MBBook ขอ (numeric keypad บนมือถือ, auto-submit
  เมื่อครบ 6 หลัก) + **lockout ฝั่ง server**: ผิด 5 ครั้ง/IP → ล็อก 5 นาที (ชดเชย PIN สั้น brute-force ง่าย)
  — **172 tests passed**, commit `efb3da9` — ⚠️ MBBook ต้องตั้ง `DASHBOARD_PASSWORD` เป็น**ตัวเลข 6 หลัก**
  (ใน Render + .env) ไม่งั้นหน้า PIN พิมพ์รหัสแบบอื่นไม่ได้
- งานต่อยอด (ยังไม่ทำ): auto-logout เมื่อเจอ 401 กลางทาง / ปุ่ม logout / จำกัด POST /workflow

---

## 🔴 รายการที่ยังค้างจริง (ไม่ใช่ประวัติ — ต้องติดตามต่อ)

0000. **UI ไม่ตรง UI_Preview_v1 (MBBook ทัก 2026-07-09 ~09:50)** — สาเหตุ: งาน 07-08 พอร์ตแค่
      layout แต่ design system (สี/กระจก/ฟอนต์/ปุ่มทอง) ไม่เคยถูกพอร์ต → **Phase 1 เสร็จแล้ว**
      (commit `845faee` — tokens ทั้งชุดใน constants.js ตรง mockup) · **Phase 2 (รายละเอียด
      component 11 ข้อ) → ทำตาม `3_CowContext/UI_Reskin_Phase2_Plan.md` ในแชทใหม่**

000. **costSummary/reportList: fetch แล้วไม่ได้แสดงผล** (เจอ 2026-07-09 ตอน Vercel build fail จาก
     no-unused-vars) — `App.jsx` ยิง `/costs/summary` + `/workflow/reports` ทุกครั้งที่โหลด แต่ค่าไม่ถูก
     อ่านไปแสดงที่ไหนเลย (เศษจากรอบรื้อ UI 07-08 — เดิม System tab เคยใช้) → ตัดสินใจ: เอากลับมาโชว์
     หรือลบ fetch ทิ้ง (ลด request ฟรีๆ 2 ตัว/โหลด) — ตอนนี้ silence warning ไว้ด้วย `const [, setX]`

00. ✅ **เสร็จแล้ว (MBBook รันเช้า 09 ก.ค.)** ล้าง + seed ชุดจริง: **stocks=24, portfolio=13** (ดู output.md) —
    MBBook ส่งสลิป Dime ครบแล้ว: **หุ้นถือจริง 13 ตัว** (GOOGL/NVDA/ASML/TSM/AMZN/BRK.B/WDC/
    NOW/VRT/NBIS/SNDK/CCJ/OKLO — ต้นทุนรวม ~$1,768, มูลค่า $1,973.46, +11.62%) + **watchlist
    11 ตัว** (RKLB/ASTS/MRVL/ARM/MU/IONQ/PLTR/ONDS/OKTA/P/LWLG) = **24 tickers**
    → Fable เขียน `2_Reference/seed_tickers_portfolio.py` (ล้าง+seed จบในตัว ตัวเลขจากสลิปฝังในสคริปต์)
    รอ MBBook รัน + ยืนยันผล (stocks=24, portfolio=13) — สคริปต์ `wipe_tickers_portfolio.py` ไม่ต้องใช้แล้ว
    · หมายเหตุ: ข้อมูลพอร์ตเก่าผิดจริง (NBIS เดิม 0.96@155.5 จริง 0.48@210 / WDC เดิม 0.75@538
    จริง 0.49@412) · หลัง seed: prefetch รอบถัดไปดึงราคาชุดใหม่, workflow 22:00 วิเคราะห์ 24 ตัว

0. **Run คืน 08 ก.ค. COMPLETE แต่ไม่ลง WorkflowLog** (เจอ 2026-07-09 00:25) — `/workflow/status`
   แสดง completed (15:01→15:12 UTC, 27/30 ตัว, 3 BUY) แต่ `/workflow/history` ยังจบที่ run 12 (07 ก.ค.)
   → เอ อาจบันทึก DB fail เงียบๆ หรือเกี่ยวกับ deploy timing — เช็ค Render log + งบ `/costs/summary`
   ของวันนี้ แล้วดูว่าคืน 09 ก.ค. บันทึกปกติไหม · ประเด็นรอง: รายงานคืนนี้มั่วชื่อบริษัท (NOW → "Pandora/
   SiriusXM" ทั้งที่คือ ServiceNow) — company_name จริงที่เพิ่ง deploy (`510d595`) ควรถูกส่งเข้า prompt
   ของเจน/หนุ่มในอนาคตเพื่อตัดปัญหานี้ (ยังไม่ได้ทำ — เป็นงานต่อยอด)

1. **PEG Ratio field ยังไม่ยืนยัน** (เปิดมาตั้งแต่ 2026-07-05) — `models.py`/`agents.py` ลองเดา field
   `pegRatio` จาก Finnhub `metric=all` ไปก่อน แต่หายืนยันจาก doc จริงไม่เจอ — **ยืนยันแล้ว 2026-07-08**:
   query `/stocks` จริงพบ `peg_ratio: null` ทุก ticker แปลว่า field เดาผิดจริง ต้องหาแหล่งข้อมูลอื่น (เช่น
   Alpha Vantage `OVERVIEW.PEGRatio` ที่ยืนยันแล้วว่ามีจริง แต่ rate limit 25 req/day ใช้แทนทั้ง 30
   tickers ทุกชั่วโมงไม่ได้ — ต้องคิดวิธีใหม่ถ้าจะเอาจริง) ดูบริบทเต็มใน `Pending_Archive.md`
   ("2026-07-05 — เพิ่ม Beta/EPS/PEG...")

2. **App.jsx component extraction ขั้นต่อไป** (เปิดมา 2026-07-08) — ทำแค่ส่วนเสี่ยงศูนย์ไปแล้ว
   (constants.js) ยังไม่ได้ตัดสินใจว่าจะแยก component ที่ผูก `isMobile` (เช่น `BarChart`) ไปไฟล์แยกด้วย
   ไหม — รอ MBBook

3. **`UI_Spec.md` ล้าสมัยถาวร** (เปิดมา 2026-07-05) — ไม่เคยอัพเดตให้ตรงกับการตัดสินใจ Finding 1-8 (รื้อ
   กลับเป็นตาราง Desktop) และตอนนี้ล้าสมัยไปอีกชั้นจากงาน 2026-07-08 (portfolio-hero layout) —
   ไม่กระทบการทำงาน แค่ห้ามใช้อ้างอิงสเปกอีกต่อไป (ยึด `Pending.md` entry ล่าสุดแทน)

---

## 📁 ประวัติงานเก่า (ก่อน 2026-07-08)

ย้ายไป `1_Reports/Pending_Archive.md` ทั้งหมดแล้ว (ประวัติ 2026-07-01 ถึง 2026-07-05, ~25 รอบงาน) —
เปิดอ่านเฉพาะตอนต้องสืบสาเหตุปัญหาเก่าหรืออยากรู้ที่มาของการตัดสินใจ ไม่ต้องอ่านตอนเริ่มงานปกติ
