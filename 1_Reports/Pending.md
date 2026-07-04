# Pending — AI Stock Analyzer V4

> รายการที่รอดำเนินการในอนาคต
> อัพเดตล่าสุด: 2026-07-03 (01:xx Bangkok)

---

## 💼 Portfolio tracking เริ่มใช้งานจริง — 2026-07-03

**การตัดสินใจ**: MBBook เลือกทาง A (บันทึกเทรดจริงที่ทำเอง) ไม่ใช่ B (auto paper-trading simulation) เพราะสไตล์การลงทุนคือถือยาว 10-15 ปี ไม่ได้ซื้อ-ขายตาม signal ทุกตัว (งบจำกัด) — วัตถุประสงค์หลักของระบบคือช่วยกรอง/วิเคราะห์ข่าวแทนการตามเอง ไม่ใช่ระบบเทรดอัตโนมัติ

**Workflow ที่ตกลงกัน**: ทุกครั้งที่ MBBook ซื้อ-ขายหุ้นจริงผ่าน Dime app จะส่ง screenshot สลิปคำสั่งมาให้ Cow อ่านแล้วบันทึกผ่าน `/trade-update` ให้

**🐛 เจอบั๊ก 2 จุดตอนเตรียมระบบ แก้แล้ว**:
1. `Trade.shares` / `Portfolio.shares` เดิมเป็น Integer — หุ้นเศษส่วน (fractional shares) จาก Dime จะถูกปัดเป็น 0 หมด แก้เป็น Float แล้ว (models.py + ALTER TABLE migration ใน main.py startup())
2. `/trade-update` เดิมบันทึกแค่ log ใน Trade table ไม่เคยอัพเดต Portfolio จริง — เพิ่ม logic ถัวเฉลี่ยต้นทุนตอน BUY / ลด shares ตอน SELL แล้ว + `/portfolio` GET คำนวณ current_value/gain สดจาก Stock.current_price

**✅ บันทึกสำเร็จ 2026-07-03**: 3 trades แรกบันทึกแล้ว (WDC BUY, NBIS BUY, P SELL) เช็ค `/portfolio` ยืนยันคำนวณถูก — WDC +5.79 USD (+5.74%), NBIS +3.12 USD (+3.09%)

---

## ✅ งาน 2026-07-03 เสร็จแล้ว — รอ MBBook เทสต์+push

1. **ต่อปุ่ม Trade Update ให้ใช้งานได้จริง** — เปลี่ยนจาก free-text textarea เป็นฟอร์มกรอกฟิลด์ตรงๆ (ticker/action BUY-SELL/shares/price) เรียก `/trade-update` โดยตรง ไม่ผ่าน โคลสัน/Haiku (เร็วกว่า ไม่เสีย LLM cost ต่อเทรด) submit แล้วรีเฟรช portfolio อัตโนมัติ + เพิ่มรายการ holdings แสดงในหน้า Portfolio ด้วย (เดิมมีแค่ตัวเลขรวม ไม่เห็นรายตัว)
2. **ทำ mobile-responsive** — ใช้ `clamp()` สำหรับ font-size/padding (ปรับสัดส่วนตามขนาดจออัตโนมัติ ไม่ต้องพึ่ง JS/media query) + เปลี่ยน grid แบบ fixed column เป็น `repeat(auto-fit, minmax())` (Portfolio summary, Status cost summary, weekday breakdown) ให้ reflow เป็นคอลัมน์เดียวอัตโนมัติบนจอแคบ

**หมายเหตุ**: ทดสอบ build ในเครื่อง sandbox ไม่สำเร็จ (bash timeout ซ้ำๆ ไม่ทราบสาเหตุแน่ชัด — น่าจะ resource/cold-cache ไม่เกี่ยวกับโค้ด) ตรวจโค้ดด้วยการอ่านทวนทั้งไฟล์แทน (syntax ครบถ้วน สมดุล) **ให้ MBBook รัน `npm start` เช็คจริงในเครื่องก่อน push** เพื่อความชัวร์

---

## ✅ งาน 2026-07-03 (รอบ 2) — เพิ่มอัปโหลดรูปสลิปในเว็บแอป

**บริบท**: ทำฟอร์มกรอกมือไปตอนแรก แต่ MBBook ทักท้วงว่าตั้งใจจะ "ส่งรูป" (แบบสลิป Dime ที่เคยส่งให้) ไม่ใช่พิมพ์เอง — เลยเปลี่ยนแผน (ผมพลาดเองที่ไปตีความเป็นฟอร์มกรอกมือโดยไม่เช็คก่อน)

**ทำเสร็จ**:
1. `agents.py` — เพิ่ม `colson_parse_trade_image()`: โคลสัน (Haiku vision) อ่านรูปสลิป → คืน JSON {ticker, action, shares, price} (ไม่บันทึก DB ในนี้)
2. `main.py` — เพิ่ม `POST /trade-parse-image` (multipart file upload) → เรียกโคลสัน parse รูป → คืนผลให้ frontend (ยังไม่บันทึก DB — save จริงผ่าน `/trade-update` เดิมตอนกด "บันทึกรายการ")
3. `requirements.txt` — เพิ่ม `python-multipart==0.0.6` (FastAPI UploadFile ต้องใช้)
4. `frontend/src/App.jsx` — TradeTab เพิ่มช่องอัปโหลดรูป (รองรับกล้องมือถือ `capture="environment"`) + ปุ่ม "🔍 อ่านข้อมูลจากรูป" → pre-fill ฟอร์มเดิม (ticker/action/shares/price) ให้ตรวจทาน/แก้ก่อนกดบันทึกจริง — ออกแบบเป็น 2 steps (parse-preview → confirm-save) กันเคส AI อ่านรูปผิด

**สถานะ**: โค้ดพร้อม รอ push + deploy + ทดสอบด้วยรูปจริง (ดู "ขั้นต่อไป" ในแชท)

---

## ✅ งาน 2026-07-03 (รอบ 3) — Mobile UI ออกแบบใหม่จริง (ไม่ใช่ย่อขนาด)

**บริบท**: MBBook ทักท้วงว่า "responsive" ที่ทำไปรอบก่อน (clamp/auto-fit) คือแค่ย่อเลย์เอาต์เดสก์ท็อป ไม่ใช่โครงสร้างที่ออกแบบมาสำหรับมือถือจริง — เลือกให้ทำใหม่แบบเต็มรูปแบบ

**ทำเสร็จใน `frontend/src/App.jsx`**:
1. เพิ่ม `isMobile` state (เช็ค `window.innerWidth <= 768` + resize listener) — ไม่ใช้ CSS media query เพราะไฟล์นี้ไม่มี CSS แยก ใช้ inline style ทั้งหมด
2. **Bottom nav bar** (fixed ติดล่างจอ, icon+label สั้น, กดง่ายด้วยนิ้วโป้ง) แทน top tab bar เมื่อ isMobile — top tab bar เดิมยังอยู่สำหรับเดสก์ท็อป
3. Header ย่อให้กระชับบนมือถือ (ตัดคำโปรยออก, ชื่อสั้นลง) ประหยัดพื้นที่แนวตั้งให้ bottom nav
4. บังคับกริดสำคัญ (Portfolio summary, Status cost summary) เป็น 1 คอลัมน์เสมอบนมือถือ (ไม่ใช่ auto-fit ที่อาจยังเรียง 2 คอลัมน์)
5. ขยาย touch target ปุ่ม/ช่องกรอกสำคัญเป็น ≥48px บนมือถือ (BUY/SELL toggle, ปุ่มบันทึกรายการ, ปุ่มอ่านรูป, ปุ่มเพิ่มหุ้น, ช่องกรอก ticker/shares/price) + font-size 16px ในช่องกรอก (กัน iOS Safari auto-zoom ตอน focus)

**สถานะ**: โค้ดพร้อม รอ push + deploy + ทดสอบจริงบนมือถือ

---

## ✅ ยืนยันแล้ว 2026-07-03: Trade Update (อัปโหลดรูป) ใช้งานได้จริงบน production

Push จาก root ถูกต้อง (commit `739924b`) deploy Live 5:05 PM — เทสต์ผ่านแล้ว: อัปโหลดรูป → parse → กด "บันทึกรายการ" → เข้า portfolio จริง

**บั๊กที่เจอระหว่างทาง**: รอบแรก push จากใน `frontend/` แทนที่จะเป็น root ของ repo → `git add .` stage แค่ไฟล์ frontend ทำให้ backend (main.py, agents.py, requirements.txt) ไม่ถูก push เลย แก้โดยสั่ง `cd D:\AI_Project\Dashboard_Share` ก่อน add/commit/push — **จำไว้: ต้องรัน git commands จาก root เสมอ ไม่ใช่จาก frontend/**

**Pending — MBBook ขอ**: ปรับรายละเอียดที่แสดงตอน "add หุ้น" ในหน้า Trade Update (บอกว่ายัง "งงๆ" กับ flow ปัจจุบัน — parse กับ save เป็นคนละปุ่มกัน) รอรายละเอียดเพิ่มเติมว่าอยากให้ปรับตรงไหน

---

## ✅ 2026-07-03 (รอบ 4) — รื้อออกแบบ UI ใหม่ทั้งหมด

MBBook ทักท้วงตรงๆ ว่า UI "เด๋อ" ไม่โมเดิร์น/มินิมอล: tab เยอะรก, สีปนกันลายตา, ตัวอักษรอ่านยาก, ดูเหมือนแปะๆ กันไว้ให้ครบ

**แก้**: รื้อ `frontend/src/App.jsx` ใหม่ทั้งไฟล์
- ลด tab จาก 6 → 4: **พอร์ต, บันทึกเทรด, หุ้น, ระบบ** (ยุบ News ที่เป็นแค่ placeholder ประโยคเดียว + Agents เข้า "ระบบ")
- Design system ใหม่: จำกัดสีเหลือ 1 accent (ม่วง) + เขียว/แดงเฉพาะความหมายกำไร-ขาดทุน/ซื้อ-ขายเท่านั้น ที่เหลือเป็นเฉดเทา
- เปลี่ยน emoji ทั้งหมดเป็น lucide-react icon (Briefcase, ArrowLeftRight, TrendingUp, Settings, Eye, Plus, Trash2, Upload, Search, Check, Camera, Info) — มีอยู่แล้วใน package.json
- กำหนด spacing scale (SP: xs/sm/md/lg/xl/xxl) + style helper (`styles.card`, `styles.input`, `btn()`) ใช้ซ้ำทั้งไฟล์แทนตัวเลขสุ่ม
- Agent pipeline ที่เคย ASCII-art แนวตั้งยาว ย่อเป็นแถว chip สั้นๆ
- Portfolio ตั้งเป็น tab เริ่มต้น (เดิมเป็น News ที่ไม่มีเนื้อหา)
- คงฟังก์ชันเดิมทั้งหมดไว้ครบ (parse รูป, submit trade, add/remove stock, cost summary, นิก suggestions)

**หมายเหตุ**: sandbox bash mount ไฟล์นี้ค้างเวอร์ชันเก่า (2026-07-01) มาตลอดทั้ง session ตรวจ build อัตโนมัติไม่ได้ ใช้การอ่านทวนทั้งไฟล์แทน (โครงสร้างสมบูรณ์) **ต้อง `npm start` เช็คจริงก่อน push**

---

## ✅ 2026-07-03 (รอบ 5) — Audit ความพร้อมระบบ + แก้ gap ข่าว/reasoning หาย

**คำถาม MBBook**: 30 tickers update ทุกคืนไม่ตกหล่นจริงไหม + มีสรุปข่าวใน webapp หรือยัง + เช็คส่วนอื่นพร้อมทำงานไหม

**พบ**:
1. **Gap ใหญ่**: หนุ่มสร้าง `reasoning` (เหตุผลภาษาไทย 2-3 ประโยค อ้างอิงข่าว/sentiment) ต่อหุ้นทุกคืนอยู่แล้ว และเจนเขียนรายงานตลาดฉบับเต็ม (market overview/signals/portfolio/risk) ทุกคืนเช่นกัน — แต่**ทั้งสองอย่างไม่เคยถูกบันทึกลง DB เลย** อยู่แค่ใน memory ระหว่าง job แล้วหายทันทีที่ job ถัดไปทับ นี่คือสาเหตุที่ News tab เดิมว่างเปล่า (เป็นแค่ placeholder ประโยคเดียวมาตลอด) — MBBook ไม่เคยเห็นสิ่งที่ AI วิเคราะห์จริงเลยแม้จะรันมาหลายรอบแล้ว
2. **30 tickers update**: เช็คจาก `/workflow/history` พบ run ล่าสุด (id 9, 2026-07-02 22:10 Bangkok) COMPLETE 30/30 ครบ — แต่เป็นข้อมูลจุดเดียวหลังย้ายไป cron-job.org (แค่ 1 คืน) **ยังเรียกว่า "พิสูจน์แล้วทุกคืน" ไม่ได้** ต้องรอดูอีกหลายคืนก่อนฟันธง (run ก่อนหน้านั้นช่วง GH Actions ไม่เสถียร มีทั้ง COMPLETE/PASS กระจายเวลาแปลกๆ ไม่นับเป็น baseline)
3. **Budget เดือน ก.ค.**: projected $10.46 (เป้า $10 / เพดาน $12) — เกินเป้าเล็กน้อยแต่ยังไม่เกินเพดาน สถานะปกติ
4. **Prefetch/cron-job.org**: เช็ค `/prefetch/status` วันนี้ (2026-07-03) พบ fetch ล่าสุด 19:15 Bangkok ยืนยันว่ายังทำงานปกติ

**แก้**:
- `models.py`: เพิ่ม `Stock.reasoning` (Text) + `WorkflowLog.full_report` (Text)
- `agents.py`: persist `reasoning` ใน `_checkpoint_database` และ `_update_database` (เดิมมีอยู่ใน `analysis` dict แล้วแต่ไม่เคยเขียนลง DB) + ส่ง `report` เข้า `a_record_improvements` แล้วดึง `report["summary"]` (text เต็มของเจน) บันทึกเป็น `full_report`
- `main.py`: migration ALTER TABLE 2 คอลัมน์ใหม่ + expose `reasoning` ใน `/stocks` + endpoint ใหม่ `GET /workflow/latest-report`
- `App.jsx`: แท็บ "ระบบ" เพิ่มการ์ด "รายงานตลาดล่าสุด" ไว้บนสุด (เนื้อหาเต็มจากเจน) + แท็บ "หุ้น" แสดง reasoning ต่อตัวใต้ signal/confidence

**ผลลัพธ์ที่คาดหวัง**: หลัง deploy + รัน workflow รอบถัดไป (22:00 คืนนี้) MBBook จะเห็นรายงานตลาดจริงในแท็บระบบ และเหตุผลต่อหุ้นในแท็บหุ้น เป็นครั้งแรก — รอบนี้จะเห็นผลได้ก็ต่อเมื่อ workflow รันรอบใหม่เท่านั้น (ข้อมูลเก่าไม่มี reasoning/report ย้อนหลัง เพราะไม่เคยถูกบันทึกไว้)

**แก้เพิ่ม (รอบ 2 วันเดียวกัน)**: MBBook ถามคมมาก — "ถ้าไม่ว่างเข้ามาอ่านสักวัน รายงานหายไปเลยหรอ" คำตอบคือข้อมูลไม่หาย (insert แถวใหม่ทุกคืน ไม่ทับของเก่า) แต่ endpoint เดิม (`/workflow/latest-report`) โชว์แค่อันล่าสุดอันเดียว ไม่มีทางย้อนดู — เพิ่ม endpoint ใหม่ `/workflow/reports?limit=7` คืนรายงานย้อนหลังสูงสุด 7 คืน + แก้ frontend ให้แสดงเป็นลิสต์ย้อนหลังในแท็บ "ระบบ" แทนที่จะโชว์แค่ล่าสุด

---

## ✅ 2026-07-04 — Full System Audit ก่อนเริ่มออกแบบ UI

MBBook ขอให้เช็คทั้งระบบให้แน่ใจว่าทำงานปกติ ก่อนเริ่มคุยเรื่องหน้าตา UI ใหม่จริงจัง (มี mockup คร่าวๆ อยากเอามาคุยตอนถึงขั้นนั้น)

**ผลตรวจ (เช็คสด ไม่ใช่เดา)**:

1. **Workflow อัตโนมัติ 22:00**: คืน 2026-07-03 (ศุกร์) ก็ COMPLETE อัตโนมัติอีกครั้ง (run id 10, 22:09 น., 30/30, cost $0.499) — **2 คืนติดกันแล้ว** หลังย้าย cron-job.org (2 ก.ค. + 3 ก.ค.) แนวโน้มดีมาก แต่ยังไม่พอจะเรียก "เสถียร 100%" (ต้องดูอีกสัก 5 คืน)
2. **🐛 พบบั๊กใหม่ — นิก (Friday code optimization) ข้ามทำงานทุกสัปดาห์มาโดยไม่มีใครรู้**: เช็ค `/workflow/logs` ของ run วันศุกร์ที่ผ่านมา พบ log `"agents.py ใหญ่เกินไป (105872 chars) — ข้าม optimization รอบนี้"` — โค้ดมี hard guard `if len(current_code) > 80000: return None` แต่ agents.py โตเกิน 80000 ไปนานแล้ว ไม่มี error โผล่ที่ไหนเลย มีแค่ WARNING เงียบๆ ที่ไม่มีใครไปดู **แก้แล้ว**: ยกเพดานเป็น 300000 chars — ⚠️ ข้อจำกัดที่เหลือ (ยังไม่แก้): นิกส่งแค่ 8000 ตัวอักษรแรกของไฟล์ให้ Claude วิเคราะห์เสมอ ไม่เห็นโค้ดท้ายไฟล์เลย — คุณภาพ suggestion จะจำกัดอยู่แค่ต้นไฟล์ (ดู Blueprint Defect #16)
3. **นิก suggestions ปัจจุบัน**: `/nik/suggestions` count=0 — ตอนนี้เข้าใจแล้วว่าเป็นเพราะบั๊กข้อ 2 ไม่ใช่เพราะไม่มีอะไรต้องแก้
4. **QA (นน) คุณภาพ**: run ล่าสุด PASS พร้อม issue ระดับ LOW 3 จุด (คำอธิบายเล็กน้อยไม่ตรงเป๊ะ เช่น ORCL อ้าง S1 เป็น 52-week low ผิด) — ไม่กระทบความน่าเชื่อถือ QA ทำงานตามที่ออกแบบไว้ถูกต้อง
5. **Budget เดือน ก.ค.**: ยังอยู่ระดับ over_target_under_ceiling ปกติ ไม่มีอะไรน่าห่วง
6. **⚠️ ยังไม่ได้ทำ — Test suite (133 tests)**: ยังรันไม่ได้ในเครื่อง (Python 3.14 กับ sqlalchemy==2.0.23 เข้ากันไม่ได้ เป็นปัญหา local environment เดิมที่ค้างมาตั้งแต่ 2026-07-03 ไม่เกี่ยวกับโค้ด) หมายความว่าการเปลี่ยนโค้ดหลายรอบใน session นี้ (models.py, agents.py, main.py) **ยังไม่เคยผ่านการรัน automated test ยืนยันเลย** อาศัยการตรวจสดผ่าน live endpoint หลัง deploy แทน (ใช้ได้แต่ไม่เท่า unit test) — ควรแก้ environment นี้ในบางจังหวะ

**สรุปให้ MBBook**: ระบบ core (workflow, trade update, portfolio, prefetch) ทำงานพร้อมใช้จริงระดับหนึ่งแล้ว มี 1 บั๊กเงียบที่เพิ่งแก้ (นิก) และ 1 gap ด้าน dev process ที่ยังไม่แก้ (test suite รันไม่ได้ในเครื่อง) — เหมาะจะเริ่มคุยเรื่อง UI ต่อได้ แต่ควรรู้ไว้ว่า risk ของการไม่มี automated test ยังอยู่

---

## ✅ 2026-07-04 — แก้ test suite รันไม่ได้ในเครื่อง

MBBook ขอให้แก้ก่อนทำ mockup UI จะได้สมบูรณ์ไปเลย

**Root cause**: `requirements.txt` ล็อก `sqlalchemy==2.0.23` (ก.ค. 2024 — ก่อน Python 3.13/3.14 จะออก) ชนกับ Python 3.14 ในเครื่อง MBBook (`AssertionError: TypingOnly`)

**แก้**: อัพเกรดเป็น `sqlalchemy==2.0.51` (ล่าสุดในสาย 2.0.x ไม่ใช่ 2.1 beta — เช็คจาก SQLAlchemy release notes แล้วว่ารองรับ 3.14 เต็มที่ตั้งแต่ 2.0.41) ความเสี่ยง breaking change ต่ำเพราะยังอยู่ในสาย 2.0 เดียวกัน — Render (production) ไม่เคยเจอปัญหานี้อยู่แล้วเพราะใช้ Python คนละเวอร์ชัน ไม่กระทบ production

**ต้องทำต่อ**: MBBook ต้อง `pip install -r requirements.txt` ใหม่ในเครื่อง แล้วรัน `python -m pytest test_agents.py test_main.py -v` เพื่อยืนยันว่า 133 tests ยังผ่านหมดหลังอัพเกรด (ยังไม่ได้รันจริง ณ ตอนบันทึกนี้)

**อัพเดต 2026-07-04 (รอบ 2) — เจอปัญหาเพิ่มอีก 2 ชุด ระหว่างพยายามรันจริง แก้ครบแล้ว ผลสุดท้าย 133 passed:**

1. **httpx ไม่เคย pin เวอร์ชัน** — pip install ใหม่ได้ httpx 0.28+ มา ซึ่งเอา `Client(app=...)` shortcut ออกแล้ว แต่ `fastapi==0.104.1` (starlette เก่า) `TestClient` ยังเรียกแบบนั้นอยู่ → `TypeError: unexpected keyword argument 'app'` (23 tests fail) แก้ด้วย pin `httpx==0.27.2` ใน requirements.txt

2. **6 เทสต์ค้างตลอดกาล (ต้อง Ctrl+C)** — `test_workflow_*` และ `test_resume_pending_stocks_starts_workflow` ทำ `patch("threading.Thread")` แบบ global ซึ่งไปดักโดน thread ภายในของ starlette TestClient เอง (ใช้เปิด async portal สำหรับยิง request จำลอง) ด้วย ทำให้ portal ไม่เคย start จริง แล้ว `self.client.post(...)` ค้างรอตลอดไป (ยืนยันสาเหตุผ่าน `pytest-timeout` เห็น stack trace ค้างใน `anyio.from_thread.start_blocking_portal`) แก้โดยให้ mock เช็คก่อนว่า `target` ตรงกับ `_run_workflow_bg` จริงมั้ย ถ้าไม่ใช่ให้ปล่อยผ่านไปสร้าง thread จริง (แก้ใน `test_main.py` 6 จุด)

3. **4 fail ในมด (validation agent) — ไม่ใช่บั๊กจริง เป็น test เก่าไม่อัปเดตตามโค้ด:**
   - 3 เทสต์ใน `TestMudValidation` ใช้ fixture `confidence=0.85` ซึ่งโดน auto-PASS shortcut (cost-saving optimization ที่ข้ามการเรียก Sonnet เมื่อ confidence ≥ 0.70 — ของจริง ไม่ใช่บั๊ก) ดักไปก่อนถึง mock เลย แก้โดยลด fixture เป็น `confidence=0.65`
   - `TestMudRecommendationFormat::test_pass_fail_only_constraint_in_source` หา string "FAIL" ในซอร์ส แต่ agents.py เปลี่ยนศัพท์เป็น "PASS"/"NEEDS_REVIEW" ไปนานแล้ว (ตรงกับเทสต์อื่นทั้งชุด) แก้ให้เช็ค "NEEDS_REVIEW" แทน

**สถานะ: ✅ ปิดเคสแล้ว** — `python -m pytest test_agents.py test_main.py -v` ผ่านครบ 133/133 ใน 14.65s ไม่มีอะไรค้าง ไม่มีอะไร fail พร้อม push ของทั้งชุด (sqlalchemy, httpx, thread-mock fix ใน test_main.py, mud test fix ใน test_agents.py, reasoning/full_report, นิก size guard) จาก repo root

---

## 🧹 ทำความสะอาดงานค้าง (Defect Monitor) — 2026-07-02 22:xx

**✅ Defect #4 ปิดเคสแล้ว**: budget Tue-Thu มีข้อมูลจริงครบ 4 รอบ เฉลี่ย $0.5225/run เทียบ $0.60 budget = เหลือ buffer ~13% ไม่มีปัญหาจริง ดู Blueprint.md Section 13

**⏳ Defect #8 อัพเดตพารามิเตอร์แล้ว รอข้อมูลจริง**: ของเก่าอ้างอิง $1.20/40 tickers (เกิน 13%) แต่ตอนนี้เปลี่ยนเป็น $0.85/30 tickers แล้ว ยังไม่มีข้อมูลจริงกับ config นี้ — **ตั้ง scheduled task `check-monday-budget-jul6` เช็คอัตโนมัติ 22:20 น. วันจันทร์ 6 ก.ค. 2026** จะเทียบ cost จริงกับ $0.85 แล้วปิด/อัพเดต defect ให้เอง พร้อมแจ้ง MBBook ทันที

**⏳ Defect #2 (OOM) ยังคง Monitor แบบ passive**: ไม่มี tool เข้าถึง Render Events API ได้ตรงๆ ในเซสชันนี้ ไม่มีหลักฐานใหม่ทั้งด้านดีและด้านเสีย ถ้า MBBook สังเกตอาการแปลกๆ (deploy ล้ม, response ช้าผิดปกติ) ค่อยเช็คซ้ำจาก Render dashboard เอง

---

## 🔍 Monitor: Defect #12 แก้แล้ว รอพิสูจน์ตัวจริง (2026-07-01)

**สรุป:** งาน 22:00 ไม่เคยเสร็จอัตโนมัติเลย ~2 สัปดาห์ (ดู Blueprint.md Defect #12) — แก้แล้ว 3 จุด: checkpoint ทีละหุ้น, keepalive self-heal ใช้ `/workflow/resume` แทน `/workflow`, ปิด `resume.yml` schedule ที่ซ้ำซ้อน คืนนี้ trigger เองล้มเหลว (deploy ชนช่วง 22:00 พอดี) ต้อง manual trigger เอง — job_id `a035af29` เริ่ม 22:44:57 น.

**ต้องติดตาม:** คืนถัดๆ ไป เช็คว่า workflow จบเองโดยไม่ต้อง manual trigger ไหม (ดู `/workflow/history` ว่า timestamp ใกล้ 22:00-23:00 Bangkok หรือยัง) ถ้ายังหลุดอีกหลังแก้ 3 จุดนี้ → ต้องพิจารณา Render Starter plan ($7/mo, ไม่มี sleep เลย) จริงจัง (MBBook ปฏิเสธไปรอบนี้ 2026-07-01 เพราะอยากลอง free tier + fix ก่อน)

**อย่า deploy code ช่วง 21:45-23:30 Bangkok** — ช่วงนี้ trigger + workflow กำลังรัน deploy จะฆ่า process กลางคัน (สาเหตุที่คืนนี้พลาด)

**ยืนยันแล้วคืน 2026-07-01**: LINE ตอน 22:54 มาจาก manual trigger (job `a035af29`) ไม่ใช่ auto — เพราะ fix (checkpoint+resume self-heal) push หลัง 22:00 ไปแล้ว ยังไม่เคยเทสต์ fix จริง

**เจอ Defect #13 เพิ่ม (2026-07-02 เช้ามืด)**: LINE แจ้ง BUDGET_EXCEEDED ตอนตี 3-4 มา 3 คืนติด — สาเหตุคือ keepalive self-heal ไม่มีเพดานเวลาบน + BUDGET_EXCEEDED ไม่เคยบันทึกลง DB + REJECTED ไม่อยู่ใน skip-list ทำให้ไล่ยิง resume ทั้งคืนจนชน budget ดูรายละเอียดที่ Blueprint.md Defect #13 — แก้แล้วทั้ง 3 จุด push แล้ว (ยืนยันขึ้น GitHub ครบ)

**⚠️→🔧 GitHub Actions cron ของ AI_Stocks_Prefetch ไม่ยอมยิงเองเลย 3 รอบติด (15:05, 16:05, 17:05)**: ลอง manual trigger + ย้าย comment/push resync ก็ไม่ช่วย **แก้แบบเด็ดขาดแล้ว 2026-07-02 17:33 น.**: ลบ `prefetch.yml` เดิมทิ้ง สร้างไฟล์ใหม่คนละ path `prefetch_hourly.yml` (บังคับ GitHub ลงทะเบียนเป็น workflow ใหม่ทั้งหมด) **ต้อง push รอบนี้ด้วย git rm ไฟล์เก่า + git add ไฟล์ใหม่** — รอผลรอบ 18:05/18:25 ถ้ายังไม่ยิงอีก แผนถัดไป (ตกลงกับ MBBook แล้วว่าทำได้เลยไม่ต้องถามซ้ำ): เปิด APScheduler กลับมา + จ่าย Render Starter ($7/mo) เพื่อตัดปัญหา sleep ที่อาจเป็นสาเหตุเดิมออก

**เจอ Defect #14 เพิ่ม (2026-07-02 บ่าย) — แก้ครบแล้ว + ยืนยันผลจริง**: prefetch cache ค้าง 22+ ชม. root cause จริงคือ `/prefetch` ไม่มี lock กันรันซ้อน (รอบใช้เวลา ~11-13 นาที แต่ keepalive self-heal ยิงทุก 10 นาที ซ้อนกันจนชน rate limit ไม่มีรอบไหนเสร็จ) แก้ 2 ชั้น: (1) สลับ trigger กลับไป GitHub Actions `AI_Stocks_Prefetch` (2) เพิ่ม `_prefetch_lock` กันรันซ้อนใน `main.py` — push แล้ว (commit `8782ad1`) **ทดสอบ manual trigger 14:22 น. 2026-07-02 สำเร็จ**: price_cache latest_fetch 14:22 น., news_cache latest_fetch 14:32 น. (~10 นาที) จบสมบูรณ์ครั้งแรกในรอบ 22+ ชม. ดูรายละเอียดที่ Blueprint.md Defect #14

**บั๊กของ Cow เอง**: scheduled task `monitor-prefetch-jul2` ที่ตั้งไว้เช็คทุกชั่วโมง self-reschedule ตัวเองไม่ทำงาน (เช็คแค่รอบเดียว 09:26 แล้วหยุด แม้เจอ anomaly ถูกต้องและ log ไว้ใน `prefetch_check_log_20260702.txt`) — เปลี่ยนแนวทาง `monitor-workflow-jul2` เป็นชุด one-shot tasks แยกกัน (ไม่พึ่ง self-reschedule) แทนแล้ว เพื่อความชัวร์คืนนี้

**🚨 พบต้นตอจริงแล้ว 2026-07-02 18:xx น. — GitHub Actions cron ไม่เสถียรทั้งระบบ ไม่ใช่แค่ prefetch.yml**: เช็คย้อนหลัง `keepalive.yml` (ตั้ง cron ทุก 10 นาที ตั้งแต่ 26 มิ.ย. 21:50 น.) พบว่ารันจริงแค่ **21 ครั้ง ใน 5.5 วัน** (ควรรัน ~790 ครั้ง — ห่างเกือบ 40 เท่า) แปลว่า self-heal ทั้งฝั่งกลางวัน (prefetch) และกลางคืน (workflow resume) ที่พึ่ง keepalive.yml อยู่ตลอด ไม่เคยทำงานได้จริงเลยตลอด 2 สัปดาห์ที่ผ่านมา — การแก้ไฟล์ `prefetch.yml`→`prefetch_hourly.yml` ก่อนหน้านี้ (17:33 น.) จึงมีโอกาสสูงว่าไม่ช่วยอะไร เพราะรากปัญหาคือ GitHub Actions cron ของทั้งเรพอไม่น่าเชื่อถือ (ยืนยันจาก GitHub community discussions: scheduled workflow เป็น "best effort" เท่านั้น อาจโดน delay/skip ตอนโหลดสูงโดยไม่มี alert)

**🔧 แผนแก้ที่ตกลงกับ MBBook แล้ว (2026-07-02 18:xx)**: ย้าย trigger ทั้งหมดจาก GitHub Actions ไปเป็น **cron-job.org** (external cron service ฟรี ยิงได้ถี่สุด 1 นาที เชื่อถือได้กว่าสำหรับงานแบบนี้เพราะเป็น core product ไม่ใช่ฟีเจอร์เสริมของ CI/CD) — MBBook เคยมีปัญหาจริงกับ cron-job.org มาก่อน (รายละเอียดไม่ทราบแน่ชัด สาเหตุที่ย้ายมา GitHub Actions รอบก่อน) จึงต้องเฝ้าดูใกล้ชิดช่วงแรกว่าจะเจอปัญหาเดิมซ้ำหรือไม่ — **ไม่ปิด GitHub Actions schedule ทันที** (ปล่อยรันคู่ขนานไปก่อน เพราะ endpoint ทุกตัวมี lock/idempotency guard อยู่แล้ว ยิงซ้อนกันได้อย่างปลอดภัย) รอ cron-job.org พิสูจน์ตัวว่าเสถียรจริงสัก 2-3 วันค่อยปิด GitHub Actions schedule ทิ้ง

Job ที่ออกแบบไว้ (6 jobs, ดู `setup_cronjob_org.py`):
- A: GET `/health` ทุก 10 นาที 02:00-19:00 UTC จ-ศ (keepalive/wake)
- B1: POST `/prefetch` ทุกชั่วโมง :05 น. 02:00-14:00 UTC จ-ศ
- B2: POST `/prefetch` pre-warm 14:45 UTC จ-ศ
- C1: POST `/workflow?include_weekend=true` 15:00 UTC เฉพาะจันทร์
- C2: POST `/workflow` 15:00 UTC อังคาร-ศุกร์
- D: POST `/workflow/resume` ทุก 10 นาที 15:00-18:59 UTC จ-ศ (self-heal)

**✅ ตั้งเสร็จแล้ว 2026-07-02 18:33 น.**: MBBook รัน `setup_cronjob_org.py` สำเร็จ ครบทั้ง 6 jobs บน console.cron-job.org (A/B1/B2/C1/C2/D) เช็ค "Next execution" ตรงกับที่คำนวณไว้ทุกตัว — Job A (Keepalive Wake) ยิงสำเร็จไปแล้ว 1 ครั้ง (18:30:37 น., 227ms, Successful) ยืนยันว่า cron-job.org ยิงตรงเวลาจริง ต่างจาก GitHub Actions ที่ปล่อยไว้คู่ขนาน (ยังไม่ปิด schedule)

**✅ ยืนยันสำเร็จ 2026-07-02 19:32-20:43 น.**: Job B1 ยิงตรงเวลา 2 รอบติด (19:05, 20:05) prefetch จบสมบูรณ์ทุกครั้ง — cron-job.org เสถียรจริง

**🎉 ยืนยันครบวงจร 2026-07-02 22:10 น. — Defect #12 ปิดเคสได้จริงเป็นครั้งแรก!**: workflow หลักจบอัตโนมัติเองครั้งแรกในประวัติศาสตร์โปรเจกต์ (run id 9, COMPLETE, 30 หุ้น, QA PASS, BUY 6/HOLD 24/SELL 0, cost $0.51) trigger โดย cron-job.org (Job C2) ล้วนๆ ไม่ต้อง manual — LINE แจ้งเตือนมาเอง 22:10 น. (10 นาทีหลัง trigger ตามที่คาดไว้) ยืนยันจาก `/workflow/history` ตรงกันเป๊ะ — 2 สัปดาห์ที่รอมาจบแล้ว

**✅ ปิด schedule ฝั่ง GitHub Actions แล้ว 2026-07-02 22:xx** (ตาม MBBook ขอให้เดินหน้าต่อทันทีหลังเห็นผลจริง ไม่ต้องรอ 2-3 วัน) — comment out schedule: ใน `keepalive.yml`, `prefetch_hourly.yml`, `trigger_workflow.yml` เหลือ `workflow_dispatch` เป็น manual backup ทุกไฟล์ (revert ง่าย แค่เอา # ออกแล้ว push) **รอ MBBook commit+push** — cron-job.org เป็นระบบ trigger หลักเพียงระบบเดียวแล้วตั้งแต่นี้

**🔧 แก้เพิ่ม 2026-07-02 (หลังตั้งเสร็จ)**: MBBook ขอให้ Job A (Keepalive Wake) และ B1 (Prefetch Hourly) ดึง**ทุกวัน**รวมเสาร์-อาทิตย์ (เดิมจันทร์-ศุกร์) เหตุผล: ลดคอขวดงานนัตตี้ (กระจาย load ไม่ให้กองไว้รอวันจันทร์อย่างเดียว) — B2/C1/C2/D ยังคงจันทร์-ศุกร์เหมือนเดิม (workflow วิเคราะห์หลักไม่รันวันหยุดตลาด) **✅ แก้เสร็จแล้ว 2026-07-02**: ใช้สคริปต์ `update_cronjob_weekends.py` (ผ่าน cron-job.org API แทนการติ๊ก UI เอง) อัพเดตสำเร็จครบ 2 jobs — B1 (jobId 7978364), A (jobId 7978362) ทำงานทุกวันแล้วยืนยันจาก terminal output จริง — อัพเดต `setup_cronjob_org.py` ให้ตรงกันแล้วเผื่อต้องสร้างใหม่ในอนาคต

**ตั้ง scheduled task ตรวจสอบแล้ว (2 ตัว, เฉพาะวันที่ 2026-07-02 วันเดียว ไม่ถาวร):**
- เช็ค workflow หลัก (22:00): 5 one-shot tasks — `monitor-workflow-jul2` (22:30), `-2300`, `-0000`, `-0100`, `-0200` (02:00 คือรอบสรุปผลสุดท้าย)
- เช็ค prefetch ระบบใหม่ (GitHub Actions) **ระหว่างวัน** ก่อนถึง 22:00 (ตามที่ MBBook ท้วงว่าต้องจับปัญหาให้ทันก่อนรันจริง ไม่ใช่เช็คแต่หลัง 22:00): `monitor-prefetch-jul2-1425/1525/1625/1725/1825/1925/2025` (แจ้งเฉพาะเจอ anomaly) + `-2150` (รอบสุดท้ายหลัง pre-warm 21:45 — แจ้งผลเสมอไม่ว่า OK/ANOMALY เพราะเป็นจังหวะสุดท้ายก่อนรันจริง)
- `monitor-prefetch-jul2`: เช็คนัตตี้ hourly prefetch (ราคา+ข่าว) ทุกชั่วโมง **09:25-21:25 น.** (13 รอบ — เลื่อนจาก :15 เป็น :25 เพราะนัตตี้ 1 รอบใช้เวลาจริง ~11-13 นาที เช็คเร็วไปจะชนกันกลางคัน) เก็บ log ไว้ที่ `prefetch_check_log_20260702.txt` แจ้งทันทีถ้าเจอความผิดปกติ + สรุปภาพรวมท้ายวันตอน 21:25 น.

---

## 💰 ทบทวน Cost จริงหลัง 3 เดือน (เปลี่ยนเป็น "รอระบบนิ่งก่อน" — 2026-07-01)

**บริบท:** MBBook ตั้งเป้างบไว้ $10/เดือน (เป้า) / $12/เดือน (เพดานที่รับได้) วันนี้ (2026-07-01) ปรับ `DAILY_BUDGET` ใน `agents.py` ให้ตึงขึ้น (เพดานโค้ด ~$13.60/เดือน) พร้อมเพิ่ม `/costs/summary` endpoint + dashboard widget

**แก้ไข (2026-07-01 ค่ำ):** เดิมนัดทบทวนตรง ~2026-10-01 (3 เดือนจากวันนี้เป๊ะ) แต่ MBBook ท้วงว่าวันนี้ระบบยังไม่นิ่ง (APScheduler ยังไม่ยืนยันว่าทำงาน, เพิ่งปิด dual-prefetch bug, เพิ่งปรับ budget) นับ 3 เดือนจากวันนี้เลยไม่แฟร์ — **เปลี่ยนเป็น 2 ขั้นตอน:**

1. **เช็ค "นิ่งพอหรือยัง" ทุก 2 สัปดาห์** (นัดแรก 2026-07-15 09:00 น.) เกณฑ์: APScheduler ยืนยันทำงานแล้ว + ไม่มี BUDGET_EXCEEDED/error ผิดปกติ 1-2 สัปดาห์ + ไม่มีปัญหาใหญ่ค้างใน Pending + config ไม่เปลี่ยนกลางทาง
2. **เมื่อนิ่งแล้ว** — ล็อกวันที่เป็น `stable_since` แล้วค่อยตั้งงานทบทวน cost จริง 3 เดือนถัดจากวันนั้น (ไม่ใช่จากวันนี้)

**เมื่อถึงเวลาทบทวนจริง (ไม่ว่าจะเป็นวันไหน) ให้ทำ:**
1. ดึง cost เฉลี่ยจริงต่อเดือน จาก `/costs/summary` และ `/workflow/history` (ข้อมูล 3 เดือนเต็ม รวม pattern จันทร์-ศุกร์)
2. เทียบกับเป้า $10 / เพดาน $12
3. **ถ้าเกินงบ** — หาจุดลดต้นทุนที่ **ไม่กระทบประสิทธิภาพการวิเคราะห์และความเสถียรของระบบ** เช่น ขยาย prompt caching, ทบทวนว่า agent ไหนใช้ Sonnet เกินจำเป็น, ทบทวนจำนวน tickers, เช็ค retry loop (เก้า) ถี่ผิดปกติไหม
4. **ถ้าอยู่ในงบ** — พิจารณาคลาย `DAILY_BUDGET` buffer ให้ตรงกับของจริงมากขึ้น

---

## ✅ APScheduler — ปิดเคสแล้ว (สรุปสุดท้าย 2026-07-01 22:xx Bangkok)

**สรุปเคสทั้งหมด:**
1. APScheduler เองไม่มีบั๊ก — พิสูจน์แล้วจาก pre-warm job ที่ยิงตรงเวลา (21:45:27 น.)
2. ต้นเหตุที่รอบ 20:05/21:05 น. หายไปคือ **Render free-tier sleep** (ไม่ใช่ OOM อย่างที่สงสัยตอนแรก — เช็ค Render Events API แล้วพบว่าทุก restart วันนี้เป็น `deploy_started/ended` ที่สำเร็จหมด ไม่มี `server_failed`)
3. **แก้ไขข้อมูลที่บันทึกผิดไว้ด้านล่าง:** POST `/prefetch` ตอน 12:21:25 UTC ที่เคยสรุปว่ามาจาก "GitHub Actions Prefetch เดิม" จริงๆ แล้วน่าจะมาจาก **`keepalive.yml` Step 3 (prefetch self-heal — เช็ค cache stale >70 นาทีแล้วยิง POST `/prefetch` เอง)** ซึ่งไม่เคยถูกปิดเลย ไม่ใช่ workflow ที่เราปิดไป
4. `keepalive.yml` มีระบบกันหลับที่แข็งแรงอยู่แล้ว (wake+retry 90s + self-heal งาน 22:00 + self-heal prefetch) — จุดอ่อนที่เหลือคือพึ่ง GitHub Actions cron scheduler เพียงอย่างเดียว (อาจ delay/ข้ามรอบได้)

**Fix ที่ทำ (2026-07-01 ค่ำ):** เพิ่ม `_self_ping_forever()` ใน `main.py` — self-ping ในตัวแอปเองทุก 8 นาที เริ่มตั้งแต่ startup ตลอดชีวิต process ไม่พึ่ง GitHub Actions cron เลย เป็น backup ซ้อนอีกชั้นเหนือ `keepalive.yml` เดิม (ยังคงไว้ ไม่ได้ปิด) — commit + push แล้วรอ deploy

**ผลกระทบจริง:** ต่ำมาก — งานหลัก 22:00 มี wake-retry ของตัวเองอยู่แล้ว (`AI_Stocks_Trigger`) ไม่เคยเสี่ยงเลยตลอดเรื่องนี้ กระทบแค่ความสดของ cache รายชั่วโมงเท่านั้น

---

## ⚠️ APScheduler — ประวัติการสืบสวน (เก็บไว้อ้างอิง มีจุดที่แก้ไขแล้วด้านบน)

**Log ที่ MBBook ดึงมา (output.md, ช่วง 12:16:59–12:23:15 UTC) พบว่า:**
- มี `POST /prefetch` จาก IP ภายนอก (52.159.243.24) ตอน 12:21:25 UTC → นัตตี้ prefetch ราคา 30/30 + ข่าวสำเร็จ
- เช็ค `/prefetch/status` ซ้ำ (ต้องใส่ cache-buster `?cb=` เพราะรอบแรกโดน cache เก่าค้าง) → ยืนยันข้อมูลสดจริง: `price_cache latest_fetch = 2026-07-01T12:21:49`, `news_cache latest_fetch = 2026-07-01T12:24:39`
- **แต่ log 100 บรรทัดนี้ไม่มีข้อความ `[Scheduler] 🕐 Starting scheduled prefetch` เลย** → POST ที่ 12:21:25 น่าจะมาจาก **GitHub Actions `AI_Stocks_Prefetch` เดิม** (ยิง POST ผ่าน HTTP) ไม่ใช่ APScheduler ตัวใหม่ (ซึ่งเรียก orchestrator ตรงในโปรเซส ไม่มี HTTP request เข้ามา)
- Log ที่ดึงมาเริ่มที่ 12:16:59 UTC พอดี — ไม่ครอบคลุมช่วง 12:05 UTC ที่ APScheduler รอบแรกหลัง restart ควรยิง เลยยังฟันธงไม่ได้ว่ารอบนั้นทำงานหรือ error

**สรุป: ข้อมูลราคา/ข่าวสดแล้ว (ดีต่อระบบ) แต่ยังไม่มีหลักฐานว่า APScheduler ตัวใหม่ทำงานจริง — อาจจะยังไม่ยิง หรือยิงแล้วแต่ log บัง**

**เสี่ยงเพิ่ม:** ถ้า GitHub Actions Prefetch (เดิม) + APScheduler (ใหม่) ทำงานคู่ขนาน จะ fetch ซ้ำ → เปลือง API quota/cost โดยไม่จำเป็น ต้องตัดสินใจว่าจะปิด workflow เดิมทิ้งเมื่อ APScheduler พิสูจน์แล้วว่าเสถียร

**เช็คซ้ำ 20:33 Bangkok (13:33 UTC) หลัง deploy ล่าสุด (cost dashboard + DAILY_BUDGET):**
- `/prefetch/status` ยังโชว์ `price_cache latest_fetch = 12:21:49 UTC`, `news_cache latest_fetch = 12:32:02 UTC` — เหมือนเดิมทุกตัวเลข ไม่มีอะไรขยับเลยตลอด ~1 ชม.ที่ผ่านมา
- **รอบ 13:05 UTC ที่ APScheduler ควรยิง (ก่อน deploy รอบนี้) ไม่มีหลักฐานว่าทำงาน** — cache ไม่ขยับตามที่คาด นี่เริ่มเป็นสัญญาณลบมากกว่าแค่ "ยังพิสูจน์ไม่ได้"
- ดีอย่างคือ GitHub Actions Prefetch ปิดไปแล้วจริง (ยืนยันจาก commit ที่ push) ตั้งแต่จุดนี้เป็นต้นไป **ถ้า cache ขยับ = ต้องเป็น APScheduler เท่านั้น** (ไม่มีตัวอื่นที่จะยิงได้แล้ว) ไม่ต้องงมหา log keyword `[Scheduler]` อีกต่อไป เช็คแค่ `/prefetch/status` (ใส่ cache-buster) พอ
- Deploy ล่าสุด (cost dashboard) เพิ่ง restart โปรเซสไป → รีเซ็ตรอบ cron ใหม่ รอบถัดไปคือ **14:05 UTC (21:05 Bangkok)** — ตั้ง auto-check ไว้ที่ 21:07 Bangkok แล้ว ถ้ารอบนี้ก็ไม่ขยับอีก แปลว่า APScheduler มีปัญหาจริง ต้องเปิด Render log ดู error ตรงๆ

**ต่อไป:**
- รอถึง 20:05 Bangkok (13:05 UTC) แล้วดึง Render log อีกรอบ หา keyword `[Scheduler]` โดยเฉพาะ เพื่อยืนยันชัดๆ ว่า APScheduler ยิงเองจริง
  ```powershell
  $h = @{Authorization = "Bearer rnd_uMDBVn9T9zI5uf5qcSyt2ZzABO15"}
  Invoke-WebRequest -Uri "https://api.render.com/v1/logs?ownerId=tea-d8r3qhkvikkc7384elq0&resource=srv-d8r3vlnavr4c73e2kugg&limit=100&direction=backward" -Headers $h | Select-Object -ExpandProperty Content | Tee-Object -FilePath output.md
  ```

**เช็ครอบ 20:07 Bangkok (13:07 UTC) — เช็คอัตโนมัติ (Cow):**
- เรียก `GET /prefetch/status` ได้ผล: `price_cache latest_fetch = 2026-07-01T07:50:27`, `news_cache latest_fetch = 2026-07-01T08:00:42`
- **ผลนี้ใช้ฟันธงไม่ได้ — ตัวเลขเก่ากว่า baseline เดิม (12:21:49 / 12:24:39) ทั้งที่เวลาผ่านมาแล้ว** แปลว่าเป็น response แคชเก่า ไม่ใช่ข้อมูลสด (เจอปัญหาเดิมที่เคยบันทึกไว้ข้างบน — endpoint นี้ค้าง cache ถ้าเรียกซ้ำ URL เดิม)
- รอบนี้ **ใส่ cache-buster ไม่ได้** เพราะเครื่องมือ web_fetch ของ Cow เปลี่ยน restriction ใหม่ (อนุญาตเฉพาะ URL ที่ตรงเป๊ะกับที่ปรากฏในข้อความ) และ sandbox ไม่มี internet ทั่วไป (curl โดน proxy บล็อก 403 blocked-by-allowlist) เลยเรียกซ้ำด้วย query param ต่างกันไม่ได้เหมือนที่เคยทำ
- **สถานะ: ยังยืนยันไม่ได้ (ไม่ใช่ "ผ่าน" หรือ "ไม่ผ่าน" ที่เชื่อถือได้)** — ต้องให้ MBBook เช็คเองจากเครื่องตัวเองด้วย cache-buster หรือดึง Render log ตามคำสั่ง PowerShell ด้านบน หา keyword `[Scheduler]` ช่วง 13:05 UTC เพื่อฟันธง

**เช็ครอบ 21:36 Bangkok (14:36 UTC) — เช็คอัตโนมัติ (Cow), ตรวจรอบ 21:05 น.:**
- เรียก `GET /prefetch/status` (2 ครั้งซ้ำ ห่างกันไม่กี่วินาที) ได้ผลเหมือนกันทั้งคู่: `price_cache latest_fetch = 2026-07-01T07:50:27`, `news_cache latest_fetch = 2026-07-01T08:00:42` — **ตัวเลขเดียวกับที่เจอตอนเช็ครอบ 20:07 น. เป๊ะ** (ซึ่งตอนนั้นก็เก่ากว่า baseline 12:21:49/12:32:02 UTC แล้ว) ทั้งที่เวลาผ่านมา ~1.5 ชม. และมี deploy คั่นกลางไปด้วย
- **สรุปว่านี่คือ response แคชเก่าค้าง ไม่ใช่ข้อมูลสดจริง** — เพราะเวลาจริงเดินหน้าไม่มีทางถอยหลังจาก 12:xx ไปเป็น 07:xx ได้ นี่คือปัญหา cache เดิมที่เคยบันทึกไว้ (endpoint นี้ค้าง cache ถ้าเรียกซ้ำ URL เดิมเป๊ะ)
- **ข้อจำกัดเครื่องมือ (บันทึกตรงๆ ตามที่งานสั่ง):** web_fetch ของ Cow ตอนนี้อนุญาตเฉพาะ URL ที่ปรากฏในข้อความ user เท่านั้น (provenance restriction) — ใส่ query param แบบ `?cb=<random>` เพื่อ bust cache เองไม่ได้ เพราะ URL ที่มี query param ใหม่ไม่เคยปรากฏในข้อความมาก่อน เลยโดนบล็อกตั้งแต่ชั้น tool ก่อนจะยิง request ด้วยซ้ำ
- **ผลคือ: เช็ครอบ 21:05 น. นี้ "ยังฟันธงไม่ได้" จากฝั่ง sandbox** — ไม่ใช่ "ไม่ผ่าน" เพราะข้อมูลที่ได้ไม่น่าเชื่อถือ (แคชเก่า) ไม่ใช่ "ผ่าน" เพราะไม่เห็นตัวเลขสดที่ขยับไปทาง 14:05-14:25 UTC เลย
- **ทางออกเดียวตอนนี้คือให้ MBBook เช็คเองจากเครื่องจริง** ด้วยคำสั่ง PowerShell (ใส่ cache-buster ได้เต็มที่):
  ```powershell
  Invoke-RestMethod -Uri "https://ai-stock-analyzer-msli.onrender.com/prefetch/status?cb=$(Get-Date -UFormat %s)" | ConvertTo-Json | Tee-Object -FilePath output.md
  ```
  ดูว่า `price_cache.latest_fetch` ขยับไปถึง/เกิน `2026-07-01T14:04` หรือไม่ (=21:04 น.ไทย) ถ้าใช่ = price fetch รอบ 21:05 ผ่านแน่นอน แล้วดู `news_cache.latest_fetch` ว่าขยับไปช่วง `14:05`–`14:25` ด้วยไหม (=21:05-21:25 น.ไทย) ถ้าใช่ทั้งคู่ = ผ่านสมบูรณ์
- **ถ้า MBBook เช็คแล้วเจอว่ายังไม่ขยับจริง (ไม่ใช่แค่แคช)** ให้ดึง Render log ช่วง 14:00-14:10 UTC (21:00-21:10 น.ไทย) หา keyword `[Scheduler]` หรือ exception ใน `_run_prefetch`:
  ```powershell
  $h = @{Authorization = "Bearer rnd_uMDBVn9T9zI5uf5qcSyt2ZzABO15"}
  Invoke-WebRequest -Uri "https://api.render.com/v1/logs?ownerId=tea-d8r3qhkvikkc7384elq0&resource=srv-d8r3vlnavr4c73e2kugg&limit=100&direction=backward" -Headers $h | Select-Object -ExpandProperty Content | Tee-Object -FilePath output.md
  ```
  ถ้ารอบ 14:05 UTC ก็ไม่มี log `[Scheduler]` เหมือนรอบก่อนๆ = APScheduler มีปัญหาจริง 2 รอบติด (20:05 และ 21:05 น.) ต้องเจาะหา exception หรือเช็คว่า cron register ผิดพลาดตรงไหนใน `scheduler.py`

**✅ เฉลยแล้ว (21:5x น.) — APScheduler ไม่มีบั๊ก ปัญหาคือ Render process restart บ่อย:**
- Log ที่ MBBook ดึงมาล่าสุดเจอ instance ใหม่ `srv-d8r3vlnavr4c73e2kugg-c5lgt` เริ่มบูตตอน **21:40:50 น.** (`✅ Scheduler started...`) แล้ว **21:45:27 น. มี `[Scheduler] 🕐 Starting scheduled prefetch for 30 tickers...` ยิงจริง** → cache 30/30 สำเร็จ + เริ่ม news fetch ต่อ — นี่คือ job "pre-warm" (hour=14,minute=45 UTC) ที่ตั้งไว้เพื่อวอร์ม cache ก่อน workflow 22:00 พอดี
- **สรุป: APScheduler ทำงานถูกต้อง 100%** เมื่อ process อยู่รอดถึงเวลาที่ตั้งไว้ ไม่ใช่บั๊กในโค้ด `scheduler.py`
- **ปัญหาจริงคือ Render restart process บ่อยเกินไป** — วันนี้เจอ instance คนละตัวกันอย่างน้อย 3 รอบ (`cmvkw` ตอนเช้า → `5j8m9` ~12:1x น. → `c5lgt` ~21:40 น.) ทุกครั้งที่ restart รอบ cron จะรีเซ็ตใหม่ ถ้า process ตายก่อนถึงนาทีที่ 05 ของชั่วโมงนั้น รอบนั้นจะหายไปเลย (นี่คือสาเหตุที่รอบ 20:05 และ 21:05 น. หายไป)
- 2 ใน 3 ครั้งอธิบายได้จาก deploy ที่เราสั่งเอง (ปิด prefetch.yml, เพิ่ม cost dashboard) แต่ instance `c5lgt` ตอน 21:40 น. **ไม่ตรงกับ deploy ไหนที่เราทำเลย** — แปลว่า Render restart เองโดยไม่มีใครสั่ง (ต้องดู Render dashboard → Events/system log ว่าเป็น crash/OOM หรือ free-tier auto-recycle เพราะ API log endpoint ที่ใช้อยู่เห็นแค่ log ระดับแอป ไม่เห็นเหตุผลการ restart ระดับ infra)
- **ผลกระทบคืนนี้: ไม่มี** — job สำคัญที่สุด (pre-warm ก่อน 22:00) ยิงสำเร็จแล้ว workflow คืนนี้จะมี cache สดใช้แน่นอน
- **งานต่อ (ไม่เร่งด่วน):** เชื่อมโยงกับ Defect #2 ใน Blueprint (OOM Risk บน Render 512MB) ที่ค้างสถานะ "Monitor" มานาน — ตอนนี้มีหลักฐานว่า process restart ถี่ผิดปกติจริง ควรยกระดับไปดูสาเหตุจริงจัง (เช่น เพิ่ม `gc.collect()` ตามที่ Blueprint แนะนำไว้แล้ว หรือดู Render metrics เรื่อง memory usage)

### คืนนี้ 22:00 Bangkok
- **LINE notification** — ควรมาตรงเวลา 22:00-22:15 น. (keepalive self-heal + APScheduler pre-warm 21:45)
- **cost** — ควรใกล้เคียง $0.43–0.52 ต่อ run

---

## 🎮 Pixel Office Model

**เงื่อนไข:** เริ่มทำได้เมื่อ webapp ใช้ได้จริง + ระบบ workflow รันได้ stable แล้ว

**ไอเดีย:**
- Top-down pixel art office style (ref: Gather.town)
- ตัวละครแต่ละตัว = AI agent (นัตตี้, หนุ่ม, มด, แฮรี่, เจน, นน, เก้า, เอ, โคลสัน, นิก)
- แสดง status real-time ตาม workflow
- เดินเล่นได้ในวันเสาร์-อาทิตย์

**Tech:** HTML5 Canvas หรือ React — ฟรี ไม่มีค่าใช้จ่ายพิเศษ

---
