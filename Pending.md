# Pending — AI Stock Analyzer V4

> รายการที่รอดำเนินการในอนาคต
> อัพเดตล่าสุด: 2026-07-01 (22:50 Bangkok)

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
