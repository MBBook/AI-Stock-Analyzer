# Pending — AI Stock Analyzer V4

> ✅ 2026-07-08: เคลียร์ไฟล์นี้ให้เล็กลงแล้ว — ประวัติงานเก่า (ก่อน 2026-07-08 ทั้งหมด) ย้ายไป
> `1_Reports/Pending_Archive.md` แยกแล้ว (เก็บไว้อ้างอิงถ้าต้องสืบสาเหตุปัญหาเก่า ไม่ต้องอ่านตอนเริ่มงาน
> ปกติ) ไฟล์นี้เหลือแค่ session ล่าสุด + รายการที่ยังค้างจริงเท่านั้น

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

## 🔴 รายการที่ยังค้างจริง (ไม่ใช่ประวัติ — ต้องติดตามต่อ)

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
