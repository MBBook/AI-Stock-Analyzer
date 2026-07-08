# Pending Archive — AI Stock Analyzer V4

> ✅ 2026-07-08: แยกออกจาก `Pending.md` เพื่อลดขนาดไฟล์ที่ Cow ต้องอ่านทุกครั้ง (เดิม 109KB) — เนื้อหา
> ทั้งหมดด้านล่างนี้คือ session เก่า (ก่อน 2026-07-08) ที่งานเสร็จ/ปิดเคสไปแล้วเกือบทั้งหมด เก็บไว้อ้างอิง
> ถ้าต้องสืบสาเหตุปัญหาเก่าเท่านั้น **Cow ไม่ต้องอ่านไฟล์นี้ก่อนเริ่มงานปกติ** — อ่าน `Pending.md` (ฉบับสั้น
> เหลือแค่ session ล่าสุด + รายการค้างจริง) กับ `3_CowContext/Blueprint.md` ก็พอ
>
> รายการที่ยังค้างจริงจากไฟล์นี้ (ย้ายสรุปสั้นไปไว้ใน `Pending.md` แล้ว): PEG ratio field ยังไม่ยืนยัน
> (2026-07-05, ยืนยันเพิ่มเติม 2026-07-08 ว่า `peg_ratio` เป็น `null` ทุก ticker จริง — ดู Pending.md)

---

## 📌 2026-07-05 — ปิด session นี้ ก่อน MBBook เปิดแชทใหม่รื้อ UI ทั้งหมด

MBBook จะเปิดแชทใหม่เพื่อออกแบบ UI ใหม่ทั้งหมด — เขียนสรุปสถานะปัจจุบันทั้งหมดไว้ที่
**`3_CowContext/Handoff.md`** (ไฟล์ใหม่) ให้แชทถัดไปอ่านก่อนเริ่มงาน ครอบคลุม: สถานะจริงของทุก tab
หลัง 10 รอบแก้ไขใน session นี้, กติกา/ข้อจำกัดที่ห้ามลืม (JSX-tag anti-pattern, Rules of Hooks,
Desktop≠Mobile, THB/USD คู่กันเสมอ, กราฟสะสมต้องเป็นเส้นเสมอ), รายการ mock/gap backend ที่ยังค้าง

**⚠️ `3_CowContext/UI_Spec.md` เดิมล้าสมัยแล้ว** — ยังเขียนว่า Desktop Portfolio/Tickers เป็นการ์ด
ทั้งที่กลับไปเป็นตารางแล้วตามการตัดสินใจรอบ 5 (Finding 1, "ทำตาม mockup 100%") ไม่ควรใช้อ้างอิงสเปก
UI อีกต่อไปจนกว่าจะเขียนใหม่ — ให้ยึด `Handoff.md` แทน (⚠️ 2026-07-08: Handoff.md เองก็ล้าสมัยไปแล้ว
เช่นกัน ตอนนี้ ดู `Pending.md` entry 2026-07-08 แทน)

**บันทึกลง project memory แล้วด้วย** (`project_ui_handoff.md`) เพื่อให้แชทใหม่เจอ context นี้ทันที
แม้จะไม่ได้เปิดอ่านไฟล์ในโปรเจกต์ก่อน

รายละเอียดทุกรอบ (1-10) อยู่ด้านล่างนี้ เรียงจากล่าสุดขึ้นบน

---

## ✅ 2026-07-05 (รอบ 10) — เพิ่มปุ่ม "ข่าวทดสอบ" จำลองข่าวใหม่เข้ามาให้ MBBook เช็ค

**บริบท**: MBBook อยากทดสอบป้าย "New" กับปุ่ม "อ่านทั้งหมด" ที่เพิ่งทำ แต่ MOCK_NEWS เป็นก้อนคงที่
ไม่มีข่าวใหม่เข้ามาระหว่างใช้งานจริง เลยเพิ่มปุ่มทดสอบชั่วคราวให้กดจำลองได้เอง

**ทำ**:
1. เพิ่ม state `extraNews` (แยกจาก `MOCK_NEWS` ที่เป็นค่าคงที่ ไม่แตะของเดิม)
2. เพิ่ม `getAllNews()` = รวม `MOCK_NEWS` + `extraNews` — ใช้แทนการอ้าง `MOCK_NEWS` ตรงๆ ทุกจุด
   (`NewsHeader` จำนวนข่าว, `NewsPagination` totalPages/startIdx/endIdx, `NewsList` sort, `markAllNewsRead`)
   เพื่อให้ข่าวทดสอบถูกนับรวมทุกที่
3. เพิ่มปุ่ม **"+ ข่าวทดสอบ"** ข้าง "อ่านทั้งหมด" ใน `NewsHeader` — กดแล้ว `addTestNews()` จะสร้างข่าว
   ใหม่ 1 ชิ้น (`timestamp = Date.now()`) เข้า `extraNews`, เด้งกลับหน้า 1 ให้เห็นทันที (ข่าวใหม่ต้องอยู่
   บนสุดเพราะ sort ตาม timestamp) และมันจะยังไม่ถูก mark ว่าอ่าน เลยควรเห็นป้าย "New" ทันที
4. ข่าวทดสอบใช้ `id` เป็นเลขติดลบ (`-Date.now()`) กันชนกับ id ของ MOCK_NEWS (1-24) และมี headline/body
   ระบุชัดว่าเป็นข่าวทดสอบ ไม่ใช่ข่าวจริง

**หมายเหตุ**: ข่าวทดสอบอยู่แค่ใน React state (ไม่ persist ลง localStorage/backend) รีเฟรชหน้าเว็บแล้ว
จะหายไปเอง — ปุ่มนี้เป็นเครื่องมือทดสอบชั่วคราว ลบทิ้งได้พร้อมกับ `MOCK_NEWS` ทั้งก้อนตอนต่อ backend
ข่าวจริง (#51)

---

## ✅ 2026-07-05 (รอบ 9) — ลด font News ลง 2px + เพิ่มปุ่ม "อ่านทั้งหมด"

**ทำ**:
1. ลด font ทุกจุดในหน้า News (header/การ์ด/pagination) และ popup รายละเอียดข่าว ลง 2px จากรอบ 7
2. เพิ่มปุ่ม **"อ่านทั้งหมด"** (`markAllNewsRead`) มุมขวาบนของ `NewsHeader` — โผล่เฉพาะตอนมีข่าวยังไม่
   อ่านเหลืออยู่ (`unreadCount > 0`) กดแล้ว mark ทุก id ใน `MOCK_NEWS` ว่าอ่านแล้วทันที + persist ลง
   localStorage เหมือน `markNewsRead()` เดิม + โชว์ toast ยืนยัน

---

## ✅ 2026-07-05 (รอบ 8) — แก้ mock news ให้เรียงตามเวลาจริง + เพิ่มป้าย "New"

**บริบท**: MBBook สังเกตว่าวันที่ข่าวโดดไปมา — root cause คือ `MOCK_NEWS` เดิมคำนวณ `date` จาก
`(i % 7) + 1` วนซ้ำไม่เกี่ยวกับลำดับ index เลย แล้ว list ก็ไม่เคย sort ตามวันที่เลยสักจุด

**ทำ**:
1. `MOCK_NEWS` — เปลี่ยนจาก `date: (i%7)+1 ก.ค.` เป็น `timestamp` จริง (ms) + format `date` string
2. `NewsList` — sort ตาม timestamp ใหม่→เก่าก่อน slice หน้า
3. เพิ่ม state `readNewsIds` (Set) — persist ผ่าน localStorage (`ai_stock_read_news_ids`)
4. `NewsCard` — เพิ่มป้าย "New" สีทอง แสดงเฉพาะข่าวที่ยังไม่อ่าน

---

## ✅ 2026-07-05 (รอบ 7) — เพิ่ม font หน้า News อีกรอบ (Desktop เยอะ, Mobile ~2 ขนาด)

เพิ่ม font ทั้งหน้า list และ popup รายละเอียดข่าว ตามอัตราส่วนที่ MBBook ขอ + ขยาย popup ข่าวฝั่ง
desktop จาก 480px เป็น 620px

---

## ✅ 2026-07-05 (รอบ 6) — เพิ่ม font ฝั่ง Desktop ทั้งหมด + กราฟสะสมทุก tab เป็นกราฟเส้น

**บริบท**: MBBook ทักท้วง 2 เรื่อง — (1) ตัวหนังสือฝั่ง Desktop เล็กไปทุกจุด (2) กราฟ "สะสม" ทุก tab
ต้องเป็นกราฟเส้น มี animation ไล่ซ้าย→ขวา เส้นขึ้น และมีค่าบอกที่ปลายเส้น

แก้ font ที่ style กลาง (`styles.sectionTitle`/`label`/`input`) + ไล่แก้จุด hardcode ทั่วไฟล์ (ใหญ่ขึ้น
~2-3px ทุกจุด) — สร้าง `CostCumulativeLineChart` เลียนแบบ `CumulativeLineChart` ของ Portfolio (ต่างกัน
จุดเดียว: label ปลายเส้นเป็น $ ไม่ใช่ %)

---

## ✅ 2026-07-05 (รอบ 5) — /scrutinize เจอ 8 finding, MBBook ตัดสินใจครบทุกข้อ, แก้เสร็จแล้ว

**บริบท**: MBBook ส่ง mockup ชุดใหม่มาละเอียดกว่าเดิม + สั่งใช้สกิล `/scrutinize` เทียบกับ App.jsx ที่รื้อไป
ตาม UI_Spec.md (รอบ 3) พบ 8 finding — **Finding 1** ชี้ contradiction ตรงๆ: mockup ใหม่โชว์
Portfolio/Tickers Desktop เป็น**ตาราง** และ News header เป็นคำเต็ม ขัดกับที่เคยสั่งแก้เป็นการ์ด/header
สั้นไปแล้วในรอบ 3 — MBBook ตอบ **"Finding 1-6 ทำตาม mockup 100%"**

**แก้เสร็จครบทั้ง 8 finding**:
1. Portfolio Desktop กลับเป็นตาราง (`HoldingsTable`) + badge "+X% สะสม"/"+X% วันนี้"
2. Tickers Desktop กลับเป็นตาราง (`TickersTable`), header กลับเป็น "หุ้นที่จับตามอง"
3. News header กลับเป็น "ข่าวหุ้น" + การ์ดเพิ่ม snippet + Impact badge
4. System tab restructure ตาม mockup 100% (ตัดการ์ด "รายงานตลาดย้อนหลัง"/budget bar เดิม, เพิ่ม
   subtitle, กราฟต้นทุนระบบใหม่มี period-selector, win rate เป็น progress bar, "รายงานจากนิก" เป็นตาราง)
5. ชื่อเต็มบริษัท + "เกี่ยวกับบริษัทนี้" — ต่อ backend จริงแล้ว (`_fetch_company_profile()`,
   `HourlyCache.company_name/company_description`, fallback ไปที่ `COMPANY_NAMES` dict ถ้ายังไม่มีค่า)

**⚠️ ยังไม่ได้ทำตอนนั้น**: อัพเดต `UI_Spec.md` ให้ตรงกับ Finding 1-8 (ไม่เคยทำ — ไฟล์นี้ล้าสมัยถาวรแล้ว)

---

## ⏳ 2026-07-05 (รอบ 3) — รื้อ App.jsx ครั้งที่ 2 ตาม UI_Spec.md ที่เขียนจากรูป mockup จริงครบทุก tab

**บริบท**: รอบแรกทำจากสรุปความจำที่ไม่ครบ พลาดหลายจุดสำคัญ (ไม่มีกราฟเลย, THB เป็นปุ่ม toggle,
+Trade ลอยบัง, desktop layout โหลงเหลง) — แก้กระบวนการใหม่: ให้ MBBook ส่งภาพหน้าจอจริงทีละใบ
สรุปเป็นข้อความให้ตรวจทานก่อนทุกจุด จนกว่าจะ confirm ครบ แล้วค่อยเขียน `UI_Spec.md`

**รื้อ App.jsx รอบ 2 เสร็จแล้ว ตาม UI_Spec.md ทุกข้อ ที่สำคัญ**:
1. Desktop/Mobile แยก component จริงต่อ tab (ไม่ใช่ responsive breakpoint เดียว)
2. THB/USD แสดงคู่กันเสมอ (ไม่มีปุ่ม toggle)
3. +Trade ย้ายจาก floating FAB → ปุ่มติดแถวคงที่
4. กราฟ Portfolio ครบ 3 แบบ (รายวัน/รายเดือน bar chart + สะสม SVG line chart)
5. Date-range dropdown ต่อกราฟรายวัน-รายเดือน
6. Popup กลาง (Stock Detail) ใช้ร่วม Tickers + Portfolio + แนวรับไม้ 1-3 ใหม่
7. News tab ใหม่ (ใช้ MOCK_NEWS เพราะ backend #51 ยังไม่สร้าง)
8. Tickers tab เป็นการ์ดทั้ง mobile/desktop (ตอนนั้น — ภายหลังกลับเป็นตารางใน desktop ตามรอบ 5)
9. ลบหุ้นเปลี่ยนเป็นเปิด popup ยืนยันก่อน
10. เพิ่มระบบ toast
11. Pulse บน signal badge ใช้ key-remount + CSS แทน hook (เลี่ยง conditional hook call)
12. Auto-refresh poll `/stocks` + `/portfolio` ทุก 5 นาที

**⚠️ งดไว้ก่อนโดยตั้งใจ**: count-up animation ตัวเลข — เพราะทุก tab content เป็น "function ที่ถูกเรียก
กลาง render" ไม่ใช่ React component จริง ใช้ hook แบบมีเงื่อนไขจะผิด Rules of Hooks

**⚠️ Gap ข้อมูลที่พบตอนนั้น (ทั้งคู่แก้ไปแล้วภายหลัง — ดู Pending.md 2026-07-08)**:
1. ชื่อเต็มบริษัท — แก้แล้วในรอบ 5 (ดูด้านบน)
2. % เปลี่ยนแปลงรายวันต่อหุ้น (day change) — แก้แล้ว 2026-07-08 (`change_pct` จาก `signal_history`)

---

## ⏳ 2026-07-05 — เพิ่ม Beta/EPS/PEG/วันประกาศงบ ใน /stocks — PEG ต้อง verify field จริง

**บริบท**: MBBook ขอเพิ่มข้อมูลเชิงลึกใน Tickers tab (task #56) — Beta, EPS, PEG ratio, วันประกาศงบ

**ทำเสร็จ**:
1. `models.py` — เพิ่ม `HourlyCache.beta/eps/peg_ratio/earnings_date/earnings_hour`
2. `agents.py` — `_fetch_finnhub_full()` ดึง `beta`/`epsNormalizedAnnual` เพิ่ม + yfinance fallback
3. `agents.py` — เพิ่ม `_fetch_finnhub_earnings()` เรียก `/calendar/earnings` (ทุก 20 ชม./ครั้ง carry-forward)
4. `main.py` — migration 5 คอลัมน์ใหม่ + `/stocks` join `HourlyCache` เพิ่ม field พวกนี้

**⚠️ PEG Ratio ยังไม่ยืนยัน — field `pegRatio` ใน Finnhub `metric=all`**: ค้นหาจาก doc/GitHub/บทความ
จริงหลายแหล่งไม่เจอ field นี้ยืนยันชัดเจน — Finnhub free tier อาจไม่มี PEG ตรงๆ **MBBook เลือกให้ลอง
field เดาไปก่อน + verify จาก log จริงหลัง deploy** (2026-07-05) — **ยืนยันแล้ว 2026-07-08**: query
`/stocks` จริงพบ `peg_ratio: null` ทุก ticker ยืนยันว่า field เดาผิดจริง (ดู Pending.md รายการค้าง)

**✅ ยืนยันแล้ว 2026-07-05**: MBBook รัน `pytest` — 149 passed, 0 failed (ไม่มี regression)

---

## ✅ 2026-07-04 (รอบ 3) — รัน pytest จริงครั้งแรก เจอบั๊กจริง 10 ตัว แก้ครบแล้ว

MBBook รันจริงที่เครื่องได้ผล 149 items, 10 failed — เป็นบั๊กจริงทั้งหมด:
1. `portfolio_return` พังแล้วลาก win rate ตายไปด้วย (5 FAIL) — แยก try/except ออกจากกัน
2. `_snapshot_portfolio` รันแม้ไม่มี ticker ไหน update สำเร็จเลย (3 FAIL) — เช็ค `if updated:` ก่อน
3. `test_agents_py_too_large_returns_none` ใช้เพดานเก่า 80000 (1 FAIL) — แก้ fake size เป็น 300001

**✅ ยืนยันแล้ว**: รันซ้ำผ่านครบ 149 passed ใน 9.89s

---

## ✅ 2026-07-04 — เพิ่มระบบคำนวณ ROI อัตโนมัติ (Phase 1 evaluation)

**ตกลงนิยามกับ MBBook**: Win rate (BUY ขึ้นจริง/SELL ลงจริง) @14 วัน และ @30 วัน แยกกัน เกณฑ์ 75% +
Avg return % เฉพาะ BUY @30 วัน เป้า 13%/เดือน

สร้างตาราง `signal_history` (insert-only ทุกคืน), migration, `agents.py::calculate_roi()`, endpoint
`GET /roi/summary`, เทสต์ 7 เคส

---

## ✅ 2026-07-04 (รอบ 2) — เพิ่มผลตอบแทนพอร์ตจริง (แยกจาก win rate)

MBBook ชี้แจงว่า "ผลตอบแทนเฉลี่ย" ที่ต้องการจริงๆ คือมูลค่าพอร์ตทั้งก้อน ไม่ใช่ค่าเฉลี่ยต่อสัญญาณ และปฏิเสธ
เกณฑ์ "13%/เดือน" ถูกต้อง (ทบต้น = ~314%/ปี ไม่มีใครทำได้จริง) → เปลี่ยนเป็น **ผลตอบแทนสะสมตั้งแต่ต้นทุน
จริง ไม่มีเส้นตาย เป้า 13% ครั้งเดียว** แยกจาก win rate

สร้างตาราง `portfolio_snapshots`, `agents.py::_snapshot_portfolio()`, key `portfolio_return` ใน
`calculate_roi()`, endpoint `GET /roi/portfolio-history`, เทสต์เพิ่ม 9 เคส

---

## 💼 Portfolio tracking เริ่มใช้งานจริง — 2026-07-03

**การตัดสินใจ**: MBBook เลือกทาง A (บันทึกเทรดจริงที่ทำเอง) ไม่ใช่ B (auto paper-trading simulation)
เพราะสไตล์การลงทุนคือถือยาว 10-15 ปี ไม่ได้ซื้อ-ขายตาม signal ทุกตัว

**Workflow ที่ตกลงกัน**: ส่ง screenshot สลิปคำสั่งจาก Dime app มาให้ Cow อ่านแล้วบันทึกผ่าน
`/trade-update` ให้

**🐛 เจอบั๊ก 2 จุดตอนเตรียมระบบ แก้แล้ว**:
1. `Trade.shares`/`Portfolio.shares` เดิมเป็น Integer — หุ้นเศษส่วนถูกปัดเป็น 0 หมด แก้เป็น Float
2. `/trade-update` เดิมไม่เคยอัพเดต Portfolio จริง — เพิ่ม logic ถัวเฉลี่ยต้นทุน/ลด shares แล้ว

**✅ บันทึกสำเร็จ 2026-07-03**: 3 trades แรกบันทึกแล้ว (WDC BUY, NBIS BUY, P SELL)

---

## ✅ งาน 2026-07-03 เสร็จแล้ว — รอ MBBook เทสต์+push

1. ต่อปุ่ม Trade Update ให้ใช้งานได้จริง (ฟอร์มกรอกฟิลด์ตรงๆ เรียก `/trade-update` โดยตรง)
2. ทำ mobile-responsive ด้วย `clamp()` + `repeat(auto-fit, minmax())`

---

## ✅ งาน 2026-07-03 (รอบ 2) — เพิ่มอัปโหลดรูปสลิปในเว็บแอป

**บริบท**: ทำฟอร์มกรอกมือไปตอนแรก แต่ MBBook ตั้งใจจะ "ส่งรูป" ไม่ใช่พิมพ์เอง

เพิ่ม `agents.py::colson_parse_trade_image()` (โคลสัน Haiku vision อ่านรูปสลิป) + endpoint
`POST /trade-parse-image` + frontend อัปโหลดรูป → pre-fill ฟอร์ม → ตรวจทาน/แก้ก่อนกดบันทึกจริง (2
steps กันเคส AI อ่านรูปผิด)

---

## ✅ งาน 2026-07-03 (รอบ 3) — Mobile UI ออกแบบใหม่จริง (ไม่ใช่ย่อขนาด)

**บริบท**: MBBook ทักท้วงว่า "responsive" รอบก่อน (clamp/auto-fit) คือแค่ย่อเลย์เอาต์เดสก์ท็อป ไม่ใช่
โครงสร้างที่ออกแบบมาสำหรับมือถือจริง

เพิ่ม `isMobile` state (เช็ค `window.innerWidth <= 768`), bottom nav bar แทน top tab bar, header ย่อ,
บังคับกริดสำคัญเป็น 1 คอลัมน์บนมือถือ, ขยาย touch target ≥48px + font-size 16px กัน iOS auto-zoom

---

## ✅ ยืนยันแล้ว 2026-07-03: Trade Update (อัปโหลดรูป) ใช้งานได้จริงบน production

Push จาก root ถูกต้อง (commit `739924b`) deploy Live — เทสต์ผ่านแล้ว

**บั๊กที่เจอ**: รอบแรก push จากใน `frontend/` แทนที่จะเป็น root ของ repo → `git add .` stage แค่ไฟล์
frontend ทำให้ backend ไม่ถูก push เลย — **จำไว้: ต้องรัน git commands จาก root เสมอ**

---

## ✅ 2026-07-03 (รอบ 4) — รื้อออกแบบ UI ใหม่ทั้งหมด

MBBook ทักท้วงตรงๆ ว่า UI "เด๋อ": tab เยอะรก, สีปนกันลายตา, ตัวอักษรอ่านยาก

รื้อ `App.jsx` ใหม่ทั้งไฟล์ — ลด tab จาก 6→4 (พอร์ต/บันทึกเทรด/หุ้น/ระบบ), design system ใหม่ (1 accent
สีม่วง), เปลี่ยน emoji เป็น lucide-react icon, กำหนด spacing scale (SP), Portfolio เป็น tab เริ่มต้น

---

## ✅ 2026-07-03 (รอบ 5) — Audit ความพร้อมระบบ + แก้ gap ข่าว/reasoning หาย

**คำถาม MBBook**: 30 tickers update ทุกคืนไม่ตกหล่นจริงไหม + มีสรุปข่าวใน webapp หรือยัง

**พบ Gap ใหญ่**: หนุ่มสร้าง `reasoning` และเจนเขียนรายงานตลาดฉบับเต็มทุกคืนอยู่แล้ว แต่**ทั้งสองอย่าง
ไม่เคยถูกบันทึกลง DB เลย** อยู่แค่ใน memory ระหว่าง job แล้วหายทันที — นี่คือสาเหตุที่ News tab เดิม
ว่างเปล่ามาตลอด

**แก้**: เพิ่ม `Stock.reasoning`, `WorkflowLog.full_report` ใน models.py + persist จริงใน agents.py +
expose ผ่าน `/stocks` และ endpoint ใหม่ `GET /workflow/latest-report` → ภายหลังเพิ่ม
`GET /workflow/reports?limit=7` (ย้อนหลังได้ ไม่ใช่แค่ล่าสุด)

---

## ✅ 2026-07-04 — Full System Audit ก่อนเริ่มออกแบบ UI

**ผลตรวจ (เช็คสด)**:
1. Workflow อัตโนมัติ 22:00 — 2 คืนติดกันแล้วหลังย้าย cron-job.org
2. **🐛 พบบั๊กใหม่**: นิก (Friday code optimization) ข้ามทำงานทุกสัปดาห์มาโดยไม่มีใครรู้ — agents.py
   โตเกิน hard guard 80000 chars เงียบๆ — แก้ยกเพดานเป็น 300000 (ดู Blueprint Defect #16 สำหรับ
   ข้อจำกัดที่ยังไม่แก้: นิกเห็นแค่ 8000 ตัวอักษรแรกของไฟล์เสมอ)
3. Test suite (133 tests) ยังรันไม่ได้ในเครื่อง (Python 3.14 vs sqlalchemy==2.0.23 เข้ากันไม่ได้)

---

## ✅ 2026-07-04 — แก้ test suite รันไม่ได้ในเครื่อง

**Root cause**: `sqlalchemy==2.0.23` ชนกับ Python 3.14 — แก้อัพเกรดเป็น `sqlalchemy==2.0.51`

**เจอปัญหาเพิ่มระหว่างรันจริง แก้ครบแล้ว**:
1. httpx ไม่เคย pin เวอร์ชัน (23 tests fail) — pin `httpx==0.27.2`
2. 6 เทสต์ค้างตลอดกาล (`patch("threading.Thread")` แบบ global ดักโดน thread ของ starlette TestClient
   เอง) — แก้ mock เช็ค target ก่อน
3. 4 fail ในมด — auto-PASS shortcut (confidence≥0.70) ดักไปก่อนถึง mock, ศัพท์ "FAIL"→"PASS"/
   "NEEDS_REVIEW" เปลี่ยนไปแล้วแต่เทสต์เก่าไม่อัปเดต

**สถานะ: ✅ ปิดเคสแล้ว** — 133/133 ผ่านใน 14.65s

---

## 🧹 ทำความสะอาดงานค้าง (Defect Monitor) — 2026-07-02 22:xx

**✅ Defect #4 ปิดเคสแล้ว**: budget Tue-Thu เฉลี่ย $0.5225/run เทียบ $0.60 budget = เหลือ buffer ~13%

**Defect #8/#2**: อัพเดตพารามิเตอร์รอข้อมูลจริง / Monitor แบบ passive (ดู Blueprint.md Section 13
สำหรับสถานะล่าสุด — ทั้งคู่ปิดเคสไปแล้วตามข้อมูลที่มาทีหลัง)

---

## 🔍 Monitor: Defect #12 แก้แล้ว รอพิสูจน์ตัวจริง (2026-07-01) — ปิดเคสสมบูรณ์ 2026-07-02

**สรุป:** งาน 22:00 ไม่เคยเสร็จอัตโนมัติเลย ~2 สัปดาห์ (ดู Blueprint.md Defect #12) — แก้ 3 จุด:
checkpoint ทีละหุ้น, keepalive self-heal ใช้ `/workflow/resume` แทน `/workflow`, ปิด `resume.yml`
schedule ที่ซ้ำซ้อน

**🚨 พบต้นตอจริง 2026-07-02**: GitHub Actions cron ของทั้งเรพอไม่เสถียร (keepalive.yml รันจริงแค่ 21
ครั้งใน 5.5 วัน ควรรัน ~790 ครั้ง) — ยืนยันจาก GitHub community: scheduled workflow เป็น "best effort"
เท่านั้น

**🔧 แก้เด็ดขาด**: ย้าย trigger ทั้งหมดไป **cron-job.org** (6 jobs, ดู `2_Reference/setup_cronjob_org.py`)
— **🎉 ยืนยันครบวงจร 2026-07-02 22:10 น.**: workflow หลักจบอัตโนมัติเองครั้งแรกในประวัติศาสตร์โปรเจกต์
(run id 9, COMPLETE, 30 หุ้น) trigger โดย cron-job.org ล้วนๆ — ปิด GitHub Actions schedule แล้ว
(เหลือ `workflow_dispatch` เป็น manual backup)

**Defect #13 (BUDGET_EXCEEDED spam ตี 3-4)**: แก้แล้ว — บันทึก WorkflowLog ให้ BUDGET_EXCEEDED ด้วย +
เพิ่ม REJECTED เข้า skip-list + จำกัดหน้าต่าง self-heal เวลา

**Defect #14 (prefetch cache ค้าง 22+ ชม.)**: root cause คือ `/prefetch` ไม่มี lock กันรันซ้อน — แก้
เพิ่ม `_prefetch_lock`

**Jobs cron-job.org (6 ตัว)**: A=keepalive ทุก 10 นาที, B1=prefetch ทุกชั่วโมง :05, B2=prefetch
pre-warm 14:45 UTC, C1=workflow จันทร์ (รวม weekend), C2=workflow อังคาร-ศุกร์, D=workflow/resume
self-heal ทุก 10 นาที 15:00-18:59 UTC — ภายหลังปรับ A/B1 ให้ดึงทุกวันรวมเสาร์-อาทิตย์ด้วย

---

## 💰 ทบทวน Cost จริงหลัง 3 เดือน (เปลี่ยนเป็น "รอระบบนิ่งก่อน" — 2026-07-01)

**บริบท:** เป้างบ $10/เดือน / เพดาน $12/เดือน — เดิมนัดทบทวน ~2026-10-01 เป๊ะ แต่ระบบยังไม่นิ่งตอนนั้น
เปลี่ยนเป็น 2 ขั้นตอน: (1) เช็ค "นิ่งพอหรือยัง" ทุก 2 สัปดาห์ (นัดแรก 2026-07-15) (2) เมื่อนิ่งแล้วล็อก
`stable_since` แล้วนับ 3 เดือนจากวันนั้นแทน

---

## ✅ APScheduler — ปิดเคสแล้ว (สรุปสุดท้าย 2026-07-01 22:xx Bangkok)

**สรุป**: APScheduler เองไม่มีบั๊ก — ต้นเหตุที่บางรอบหายไปคือ **Render free-tier sleep/restart บ่อย**
ไม่ใช่ OOM อย่างที่สงสัยตอนแรก — เพิ่ม `_self_ping_forever()` ใน `main.py` (self-ping ทุก 8 นาที ไม่พึ่ง
GitHub Actions cron เลย) เป็น backup ซ้อนอีกชั้น

*(ประวัติการสืบสวนแบบละเอียดทุกรอบเช็ค ถูกย่อออกจากอาร์ไคฟ์นี้แล้ว เพราะข้อสรุปสุดท้ายด้านบนครอบคลุม
ประเด็นสำคัญครบแล้ว — ต้นฉบับเต็มอยู่ใน git history ของไฟล์นี้ถ้าต้องการจริงๆ)*

---

## 🎮 Pixel Office Model (ไอเดียยังไม่เริ่มทำ)

**เงื่อนไข:** เริ่มทำได้เมื่อ webapp ใช้ได้จริง + ระบบ workflow รันได้ stable แล้ว

**ไอเดีย:** Top-down pixel art office style (ref: Gather.town) — ตัวละครแต่ละตัว = AI agent (นัตตี้,
หนุ่ม, มด, แฮรี่, เจน, นน, เก้า, เอ, โคลสัน, นิก) แสดง status real-time ตาม workflow เดินเล่นได้วัน
เสาร์-อาทิตย์ — Tech: HTML5 Canvas หรือ React ฟรี ไม่มีค่าใช้จ่ายพิเศษ

---
