# Pending — AI Stock Analyzer V4

> รายการที่รอดำเนินการในอนาคต
> อัพเดตล่าสุด: 2026-07-01 (19:15 Bangkok)

---

## ⚠️ APScheduler — ยังพิสูจน์ไม่ได้ว่าทำงาน (อัพเดต 2026-07-01 19:25 Bangkok)

**Log ที่ MBBook ดึงมา (output.md, ช่วง 12:16:59–12:23:15 UTC) พบว่า:**
- มี `POST /prefetch` จาก IP ภายนอก (52.159.243.24) ตอน 12:21:25 UTC → นัตตี้ prefetch ราคา 30/30 + ข่าวสำเร็จ
- เช็ค `/prefetch/status` ซ้ำ (ต้องใส่ cache-buster `?cb=` เพราะรอบแรกโดน cache เก่าค้าง) → ยืนยันข้อมูลสดจริง: `price_cache latest_fetch = 2026-07-01T12:21:49`, `news_cache latest_fetch = 2026-07-01T12:24:39`
- **แต่ log 100 บรรทัดนี้ไม่มีข้อความ `[Scheduler] 🕐 Starting scheduled prefetch` เลย** → POST ที่ 12:21:25 น่าจะมาจาก **GitHub Actions `AI_Stocks_Prefetch` เดิม** (ยิง POST ผ่าน HTTP) ไม่ใช่ APScheduler ตัวใหม่ (ซึ่งเรียก orchestrator ตรงในโปรเซส ไม่มี HTTP request เข้ามา)
- Log ที่ดึงมาเริ่มที่ 12:16:59 UTC พอดี — ไม่ครอบคลุมช่วง 12:05 UTC ที่ APScheduler รอบแรกหลัง restart ควรยิง เลยยังฟันธงไม่ได้ว่ารอบนั้นทำงานหรือ error

**สรุป: ข้อมูลราคา/ข่าวสดแล้ว (ดีต่อระบบ) แต่ยังไม่มีหลักฐานว่า APScheduler ตัวใหม่ทำงานจริง — อาจจะยังไม่ยิง หรือยิงแล้วแต่ log บัง**

**เสี่ยงเพิ่ม:** ถ้า GitHub Actions Prefetch (เดิม) + APScheduler (ใหม่) ทำงานคู่ขนาน จะ fetch ซ้ำ → เปลือง API quota/cost โดยไม่จำเป็น ต้องตัดสินใจว่าจะปิด workflow เดิมทิ้งเมื่อ APScheduler พิสูจน์แล้วว่าเสถียร

**ต่อไป:**
- รอถึง 20:05 Bangkok (13:05 UTC) แล้วดึง Render log อีกรอบ หา keyword `[Scheduler]` โดยเฉพาะ เพื่อยืนยันชัดๆ ว่า APScheduler ยิงเองจริง
  ```powershell
  $h = @{Authorization = "Bearer rnd_uMDBVn9T9zI5uf5qcSyt2ZzABO15"}
  Invoke-WebRequest -Uri "https://api.render.com/v1/logs?ownerId=tea-d8r3qhkvikkc7384elq0&resource=srv-d8r3vlnavr4c73e2kugg&limit=100&direction=backward" -Headers $h | Select-Object -ExpandProperty Content | Tee-Object -FilePath output.md
  ```

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
