# Pending — AI Stock Analyzer V4

## ✅ 2026-07-11 (รอบ 7 — Cow) — แก้ test fail ตัวสุดท้าย (KeyError sentiment ใน /news)

**ที่มา:** รันเทสต์รอบ 6 แล้วเจอ 2 fail (1 ตัวใหม่จากรอบ 6 เอง — แก้ไปแล้วในเทสต์, 1 ตัวเดิม
`test_news_untranslated_falls_back_to_english` ที่ carry มาตั้งแต่รอบ 4) MBBook ถามตรงๆ ว่าทำไม
ไม่แก้ให้ผ่านหมดเลย — ไม่มีเหตุผลจะไม่แก้ (บั๊ก 1 บรรทัด แยกจากงาน Nik) เลยแก้ให้

**ทำเสร็จ (ยังไม่ commit/push — รวมกับก้อนรอบ 4-6 ที่รอ push อยู่):**
- `main.py::get_news` — else-branch (ข่าวไม่มีคำแปล) เพิ่ม `a["sentiment"] = None` /
  `a["impact"] = None` (เดิมไม่ set เลย ทำให้ key หายไปจาก response) + except-branch (translation
  join พัง) เพิ่ม `a.setdefault("sentiment", None)` / `.setdefault("impact", None)` ด้วยเผื่อ robust
- ไม่เพิ่ม/ลบเทสต์ (แก้ production code ให้ตรงกับที่เทสต์เดิมคาดหวังอยู่แล้ว) รวมยังคง **210 tests**
- คาดผลรันครั้งถัดไป: **210 passed / 210** (ครั้งแรกที่ทุกเทสต์ผ่านหมดตั้งแต่เริ่มเจอบั๊กนี้)

## ✅ 2026-07-11 (รอบ 6 — Cow) — ปุ่ม "ตรวจสอบสถานะ" + แก้บั๊ก 5-day filter + กันนิกเสนอซ้ำ

**ที่มา:** MBBook ทักว่าระบบ manual 100% (รอบ 5) ไม่ตรงกับที่คุยกันตอนออกแบบ ("Cow แก้/reject แล้วนิกน่าจะ
รู้เอง") ถามด้วยว่าถ้า reject แล้วนิกจะเสนอปัญหาเดิมซ้ำไหม (เพราะปัญหาที่มองยังไม่ถูกแก้จริง) — เสนอเพิ่ม
ปุ่ม "ตรวจสอบสถานะ" ให้นิกเช็คเอง โดยมีเงื่อนไข**ห้ามเพิ่มต้นทุนระบบ**

**ทำเสร็จ (ยังไม่ commit/push — รวมกับก้อนรอบ 4-5 ที่รอ push อยู่):**
1. **`POST /nik/suggestions/{id}/check-status`** (`main.py`) — เช็คว่า pending suggestion ถูกแก้แล้ว
   หรือยัง ด้วย **deterministic string match ล้วนๆ ไม่เรียก Claude เลย** (เทียบ FIND block ของ diff
   กับ agents.py ปัจจุบันบน GitHub ตรงๆ — GitHub API ฟรีอยู่แล้ว + string compare ในเครื่อง = **ต้นทุน
   เพิ่ม $0**) หายไปหมด (โดนแก้แล้ว) → `status=complete` + `applied_at` อัตโนมัติ ยังเจออย่างน้อย 1 จุด
   → คง `pending`
2. **`Orchestrator._nik_parse_diff_blocks()`** (`agents.py`, static method ใหม่) — parser แยก FIND
   block จาก diff_text (รองรับหลาย `<<<DIFF>>>` block ในไฟล์เดียว)
3. **ปุ่ม "ตรวจสอบสถานะ"** สีม่วง คู่กับปุ่มปฏิเสธในป๊อปอัพนิก (`App.jsx`) — โชว์เฉพาะ pending
4. **แก้บั๊ก `filter()` ว่างเปล่า** ใน `nik_optimize_code()` — เดิมคำนวณ `since` (5 วัน) แต่ไม่เคยใช้กรอง
   จริง ดึง WorkflowLog ทั้งหมดตั้งแต่วันแรกมาตลอด แก้เป็น `filter(WorkflowLog.timestamp >= since)` จริง
5. **กันนิกเสนอเรื่องเดิมซ้ำ** — เพิ่ม step 1b ดึง summary ของ suggestion ที่เคย `rejected` (limit 10)
   ยัดเข้า prompt นิก (`=== Previously rejected suggestions ===`) + เพิ่ม RULE ใน system prompt ห้าม
   เสนอ SUMMARY ซ้ำ — ไม่เพิ่ม LLM call ใหม่ (query DB เพิ่มเฉยๆ)
6. **Tests +17** (9 ใน `test_agents.py`: 3 สำหรับ nik prompt/filter + 6 สำหรับ `_nik_parse_diff_blocks`,
   8 ใน `test_main.py` สำหรับ `/nik/suggestions/{id}/check-status`) รวม **210 tests**
7. แก้ `test_db_save_fails_no_crash` เดิม (`test_agents.py`) — เพิ่ม mock db ตัวที่ 3 ใน `side_effect`
   list กัน SessionLocal() call ใหม่ (step 1b) ไปกิน slot ของ db_save เดิม ทำให้เทสต์ไม่ได้ทดสอบตามชื่อจริง
8. อัพเดต `Blueprint.md` หัวข้อ 3/9/10 — **แก้คำอธิบายเดิมที่บอกว่าระบบเป็น "manual 100%" ผิด** (รอบ 5
   เขียนไว้ผิด ตอนนี้แก้ว่าเป็นกึ่งอัตโนมัติผ่านปุ่มตรวจสอบสถานะ)

**สังเกตเพิ่ม (ไม่ใช่บั๊ก แต่น่าสนใจ):** suggestion #1 ที่ถูกปฏิเสธไปฝ่าฝืน RULE ที่มีอยู่แล้วในนิกเอง
("Do NOT change model names") — Claude สร้าง suggestion ที่ขัดกับ system prompt ของตัวเอง อาจคุ้มค่า
เพิ่ม guard กรอง diff block ที่แตะ `MODEL_SONNET`/`MODEL_HAIKU` ออกอัตโนมัติก่อนบันทึกลง DB (ยังไม่ทำ
รอ MBBook ตัดสินใจว่าคุ้มไหม)

⚠️ **ยังไม่ได้กดปุ่มไหนจริงในระบบ** — ต้องรอ push+deploy รอบนี้ก่อน

## ✅ 2026-07-11 (รอบ 5 — Cow) — รีวิว suggestion #1 ของนิก + เพิ่มสถานะ "ปฏิเสธ" (rejected)

**ที่มา:** MBBook ดาวน์โหลด `nik-suggestion-1.md` จากปุ่มที่เพิ่งสร้างรอบ 4 (ยืนยันปุ่มทำงานจริง) ส่งให้ Cow
อ่าน — Cow ตรวจแล้วพบว่า suggestion นี้**ห้าม apply**: diff หลักเสนอเปลี่ยน
`MODEL_HAIKU = "claude-haiku-4-5-20251001"` → `"claude-haiku-4-5"` โดยอ้างว่าชื่อเดิม "malformed" —
**ผิด** ชื่อเดิมถูกต้องตามที่ Anthropic กำหนดจริง ถ้าแก้ตามนี้จะกลายเป็นชื่อโมเดลที่ไม่มีอยู่จริง
API จะ reject ทันที (ตรงข้ามกับที่นิกอ้างว่าจะแก้ปัญหา rejection) นอกจากนี้ diff ยังมีบล็อกซ้ำ 2 ครั้ง
+ 1 บล็อกที่ FIND=REPLACE เหมือนกันทุกตัวอักษร (ไม่ทำอะไรเลย) — คุณภาพต่ำทั้งก้อน เกิดจาก prompt เก่า
ก่อนอัพเดต (รอบ 3) **แนะนำ MBBook ไม่ apply** suggestion นี้

MBBook ถามต่อว่าจะปิด pending ของ suggestion นี้ยังไงถ้าไม่ apply — ตอนนั้นยังไม่มีทาง (status enum เดิม
มีแค่ pending/complete/failed ไม่มีคำที่แปลว่า "ตรวจแล้ว ไม่ apply")

**ทำเสร็จ (ยังไม่ commit/push — รวมกับก้อนรอบ 4 ที่รอ push อยู่):**
1. **status ใหม่ `rejected`** (`models.py::NikSuggestion.status` — ยังเป็น String เดิม ไม่ต้อง migrate
   schema เพิ่ม)
2. **`POST /nik/suggestions/{id}/reject`** (`main.py`) — เปลี่ยน pending → rejected เท่านั้น (ปฏิเสธซ้ำ/
   ปฏิเสธ suggestion ที่ไม่ใช่ pending → 400, ไม่มี id → 404) dashboard auth ปกติ (ไม่อยู่ใน PUBLIC_ROUTES
   เพราะเป็น write action ที่ทำจากเว็บที่ล็อกอินแล้ว ไม่ใช่ Cow เรียกเอง)
3. **ปุ่ม "ปฏิเสธ"** ใน popup รายละเอียดนิก (`NikDetailContent`, `App.jsx`) — โชว์เฉพาะตอน
   `status === 'pending'`, มี `window.confirm` กันกดพลาด (ไม่เพิ่ม useState/popup แยก กัน rule
   Handoff ข้อ 2), เรียกสำเร็จแล้ว `fetchNikSuggestions()` + `closePopup()` + toast
4. อัพเดต `NIK_STATUS_LABEL_TH`/`sColor` ให้รองรับ `rejected` (สีเทาจาง ต่างจาก pending สีทอง)
5. **Tests +5** (`TestNikRejectEndpoint`) รวม **193 tests**
6. อัพเดต `Blueprint.md` หัวข้อ 3/9/10

⚠️ **ยังไม่ได้กดปฏิเสธ suggestion #1 จริงในระบบ** — ต้องรอ push+deploy รอบนี้ก่อน ถึงจะกดปุ่ม "ปฏิเสธ"
บนเว็บได้จริง (ตอนนี้ endpoint ยังไม่อยู่บน production)

## ✅ 2026-07-11 (รอบ 4 — Cow) — Cow ดึงรายงานนิกเองได้ (`/nik/export`) + ปุ่ม copy/download สำรอง

**ที่มา:** ตรวจ deploy รอบ 3 พบว่านิก pending ค้าง (ปกติ — flow manual ตามออกแบบ) แต่ MBBook ทักว่า
ตอนออกแบบระบบตั้งใจให้ Cow ดึงรายงานนิกมาอ่านเองได้เมื่อถาม ไม่ใช่ต้องรอ MBBook copy-paste ให้ทุกครั้ง
— ไปเช็คแล้วพบว่า `/nik/suggestions` ต้อง dashboard auth (X-Auth-Token จาก PIN) ที่ Cow ไม่มีสิทธิ์ถือ
เลยยังไม่เคยมีทางให้ Cow เข้าถึงได้จริง

**ทำเสร็จ (ยังไม่ commit/push):**
1. **`GET /nik/export?token=&limit=`** (`main.py`) — เหมือน `/nik/suggestions` ทุกอย่าง แต่ auth ด้วย
   `COW_EXPORT_TOKEN` (query param, คนละตัวกับ `DASHBOARD_PASSWORD`) — Cow เรียกเองผ่าน web_fetch/Chrome
   ได้ทันที ไม่ต้องรอ MBBook · อยู่ใน PUBLIC_ROUTES (ข้าม dashboard auth middleware, เช็ค token เอง) ·
   ไม่ตั้ง `COW_EXPORT_TOKEN` = ปิดสนิท 403 · `limit` cap 20 กันดึงทั้งตาราง
   - ทดสอบแล้วจริง (ไม่ใช่แค่ทฤษฎี): sandbox bash เรียก `api.render.com`/Neon DB ตรงไม่ได้ (proxy
     allowlist บล็อก) แต่ **Chrome browser MCP เรียก `ai-stock-analyzer-msli.onrender.com` ได้ปกติ**
     (ทดสอบกับ `/health` และ `/nik/suggestions` แบบไม่มี token → เจอ 401 ตามคาด) — ดังนั้น `/nik/export`
     จะใช้งานได้จริงผ่านช่องทางนี้หลัง deploy
2. **`COW_EXPORT_TOKEN`** — generate random token ใหม่ใส่ `.env` local แล้ว (`secrets.token_urlsafe(32)`)
   + เพิ่ม placeholder ใน `.env.example` พร้อม comment วิธี generate
3. **ปุ่ม "คัดลอกเป็น Markdown" + "ดาวน์โหลด .md"** ใน popup นิก (`NikDetailContent`, `App.jsx`) — ทางสำรอง
   export summary/reasoning/diff/status ครบ ถ้า Cow ดึงผ่าน endpoint ไม่ได้ด้วยเหตุผลอะไรก็ตาม — ไม่ใช้
   `useState` เก็บ "copied" state (กัน rule Handoff ข้อ 2) ใช้ DOM manipulation ตรงที่ปุ่มแทน
4. **Tests +6** (`test_main.py::TestNikExportEndpoint` — no-token-env-403 / missing-token-401 /
   wrong-token-401 / valid-200 / limit-cap-20 / bypass-dashboard-auth) รวม **188 tests**
5. อัพเดต `Blueprint.md` หัวข้อ 3 (endpoints table), 9 (นิก flow), 10 (test coverage) ให้ตรงของจริง

⚠️ **ต้อง push + ตั้ง env ที่ Render ก่อนใช้งานได้จริง**:
- Push `main.py`/`frontend/src/App.jsx`/`.env.example`/`test_main.py` ขึ้น Render
- **ตั้ง `COW_EXPORT_TOKEN` ใน Render Environment ด้วย** (ค่าเดียวกับใน `.env` local — เปิดไฟล์ `.env`
  ดู ไม่ generate ใหม่ ไม่งั้นค่าไม่ตรงกัน) ไม่งั้น endpoint จะตอบ 403 ตลอด (ปิดสนิทตามที่ตั้งใจ)

**จุดที่ยังไม่แก้ (พบระหว่างตรวจ ไม่เกี่ยวกับงานรอบนี้):**
- `test_news_untranslated_falls_back_to_english` fail อยู่ก่อนรอบนี้แล้ว (`KeyError: 'sentiment'`) —
  `/news` ไม่ set `sentiment`/`impact` เป็น `None` ตอนข่าวยังไม่ถูกแปล ดู Blueprint หัวข้อ 10

## ✅ 2026-07-11 (รอบ 3 — Cow) — News ไทยเต็ม 100% + รายงานนิกไทย + popup รายละเอียด

**ที่มา:** MBBook ตรวจรายงานนิกแล้วขอแก้ 2 จุด — (1) หน้า News ยังมีคำอังกฤษหลุด (sentiment badge,
"New", "Impact:") ทั้งการ์ดและ popup (2) รายงานนิกเป็นอังกฤษล้วน (SUMMARY มาจาก system prompt
ภาษาอังกฤษ) และไม่มีทางดูเหตุผลเบื้องหลังแต่ละข้อเสนอเลย

**ทำเสร็จ (ยังไม่ commit/push):**
1. **News ไทย 100%** — `App.jsx`: เพิ่ม `NEWS_SENTIMENT_LABEL_TH` map (Positive/Negative/Neutral →
   เชิงบวก/เชิงลบ/เป็นกลาง) ใช้แทนที่ enum ดิบใน `NewsCard` + `NewsDetailContent` (popup) ·
   "New" → "ใหม่" · "Impact: " → "ผลกระทบ: " ทั้งการ์ดและ popup — ไม่แตะ enum เดิมที่ใช้ map สี
2. **รายงานนิกเป็นไทย + เพิ่มเหตุผล (reasoning)**:
   - `models.py::NikSuggestion` เพิ่มคอลัมน์ `reasoning` (Text, nullable — รายการเก่าจะเป็น NULL)
   - `main.py` เพิ่ม migration block `ALTER TABLE nik_suggestions ADD COLUMN IF NOT EXISTS reasoning`
     + expose `reasoning` ใน response ของ `GET /nik/suggestions`
   - `agents.py::nik_optimize_code()` แก้ system prompt: บังคับ `SUMMARY:`/`REASON:` เป็นภาษาไทย
     (FIND/REPLACE ยังเป็นโค้ดจริง ไม่แปล) + เพิ่ม logic ดึง `REASON:` คู่กับ `SUMMARY:` เดิม เก็บลง
     `reasoning` ตอนบันทึก `NikSuggestion`
3. **Popup รายละเอียดรายงานนิก (ของใหม่ทั้งหมด)** — `App.jsx`: เพิ่ม `NikDetailContent` component
   (โชว์วันที่/สถานะ/summary/reasoning — มี fallback ข้อความสำหรับรายการเก่าที่ยังไม่มี reasoning/
   error_message ถ้า failed/diff_text เต็ม) + คลิกได้ทั้งแถว desktop table และการ์ด mobile
   (`openPopup('nikDetail', ...)`) + เพิ่ม case `'nikDetail'` ใน `popupTitle()`/`PopupModal()` ·
   แปล status label เดิม (Complete/Failed/Pending → เสร็จแล้ว/ล้มเหลว/รอดำเนินการ) เป็น
   `NIK_STATUS_LABEL_TH` map + badge "X pending" → "X รอดำเนินการ"

⚠️ **ต้อง push + redeploy ก่อนเห็นผลจริง**: reasoning จะว่างเปล่า (NULL) จนกว่านิกจะรันรอบใหม่ภายใต้
prompt ที่แก้แล้ว (รอบถัดไปที่ optimization job ยิง) — ต้อง push `models.py`/`main.py`/`agents.py`
ขึ้น Render ก่อน ไม่งั้น migration ไม่รัน คอลัมน์ยังไม่มีจริงใน DB

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

## ✅ 2026-07-11 (รอบ 2 — Fable) — แปลข่าวเป็นไทย + sentiment/impact (Language rule v3)

**ที่มา:** MBBook เปิด production แล้วเจอข่าวอังกฤษล้วน — requirement "news content ต้องเป็นไทย"
มีอยู่จริงใน `UI_Redesign_Prompt_v3.txt` บรรทัด 20 (Language rule, confirmed 07-07) แต่ไม่เคยถูกยก
ไปเป็น backend requirement ตอนสร้างงาน #51 → Cow ทำ /news รอบแรกส่งอังกฤษดิบออกไป
**แก้แล้ว + ยก Language rule ขึ้น Blueprint ให้เป็น requirement ถาวรกันหลุดอีก**

**สิ่งที่ทำ (ยังไม่ commit — รวมกับก้อน UI Phase 2 ที่รอ push อยู่):**
1. `models.py` — ตาราง `news_translations` (id = md5(title)[:12] คีย์เดียวกับ /news, ข่าวละแถวถาวร)
2. `agents.py` — `natty_translate_news()`: Haiku แปลข่าวใหม่ + วิเคราะห์ sentiment (Positive/Negative/
   Neutral) + impact (สูง/กลาง/ต่ำ) ท้าย prefetch ทุกรอบ — batch 20 ข่าว/call, cap 60/รอบ,
   แปลข่าวละครั้งเดียว, ล้มแล้วไม่กระทบ prefetch หลัก · ประมาณการ cost ~$0.02-0.05/วัน ($0.6-1.5/เดือน)
3. `main.py` — /news join คำแปล (`translated` flag ต่อข่าว) — ข่าวที่ยังไม่แปลโชว์อังกฤษไปก่อน
4. frontend — `getAllNews` รับ sentiment/impact จริง (ป้ายในการ์ด/popup กลับมาแสดงอัตโนมัติ)
5. tests +7 (**รวม 182**: TestNewsTranslate 5 ใน test_agents + translation-join 2 ใน test_main)

**📌 ตัดสินใจไว้ (MBBook ถามเรื่อง AI ฟรี):** เริ่มด้วย Haiku เพราะ infra (key rotation/cost tracking)
มีครบ ไม่ต้องเพิ่ม dependency — **ทบทวนหลังใช้ 2 สัปดาห์**: ถ้า cost แปลข่าวเกิน ~$1/เดือนจริง
ให้สลับไส้ `natty_translate_news` เป็น **Gemini Flash free tier** (แก้จุดเดียว ดีไซน์รองรับไว้แล้ว)

**หลัง deploy:** ข่าวเก่าใน cache จะถูก backfill แปลใน prefetch รอบแรกหลัง deploy (สูงสุด 60 ข่าว/รอบ
ที่เหลือรอบถัดไป) — ถ้าเปิดแอปแล้วบางข่าวยังอังกฤษ = ยังไม่ถึงคิวแปล รอชั่วโมงถัดไป

---

**⏳ Pending ระยะยาว (MBBook สั่งเอง 2026-07-11):**
- **ตรวจกราฟ Portfolio เทียบ mockup อีกครั้งหลังระบบใช้งานจริง ~90 วัน (ครบกำหนด ~2026-10-09)**
  — ตอนนี้ข้อมูล portfolio_history ยังไม่พอให้กราฟขึ้นรูปทรงจริง (Monthly ต้องมี snapshot ปิดเดือน
  2-3 เดือน, Cumulative เริ่มเห็นเส้นชัดหลัง ~2 สัปดาห์) จุดที่ต้องเทียบตอนนั้น: แท่ง Monthly
  gradient ม่วง + ค่ากำกับทอง, เส้น Cumulative วาดซ้าย→ขวา + จุดทอง + label ปลายเส้น,
  สัดส่วน hero 70:30 ฝั่ง Desktop

**MBBook ต้องทำ (ตามลำดับ):**
1. `cd D:\AI_Project\Dashboard_Share` → `.\.venv\Scripts\python.exe -m pytest test_main.py test_agents.py -v > 1_Reports\Output.md 2>&1` (ต้อง **182** passed — อัพเดตหลังเพิ่มระบบแปลข่าว)
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
