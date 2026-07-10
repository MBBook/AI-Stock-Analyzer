# UI Reskin Phase 2 — แผนพอร์ตรายละเอียด component ให้ตรง UI_Preview_v1.html

> เขียนโดย Fable 2026-07-09 (~10:00) — **Phase 1 (design tokens) เสร็จแล้ว** commit `845faee`:
> COLORS/GLOBAL_CSS ใน `constants.js` ตรง `:root` ของ mockup แล้วทั้งชุด (พื้น+glow, glass, ม่วง
> `#8b7bf7`, gradient ม่วง/ทอง, เขียว `#33d692`/แดง `#ff6570`, ฟอนต์ Inter+Noto Sans Thai, tabular-nums)
> เหลือ**รายละเอียดต่อ component** ที่ hardcode inline style ใน `App.jsx` — ไฟล์นี้คือ checklist ทำต่อ
>
> **กติกา:** อ่าน `Handoff.md` ก่อน (กฎ 8 ข้อ) · แก้ทีละข้อ → esbuild check → ให้ MBBook เปิดแอปเทียบ
> mockup (มีปุ่ม toggle Desktop/Mobile ในไฟล์ preview) → confirm แล้วค่อยข้อถัดไป · **ห้ามรื้อโครง
> component ใหม่** (โครง layout ตรง mockup อยู่แล้วจากงาน 07-08) · commit เป็นช่วงๆ ทุก 2-3 ข้อ

## Checklist (เรียงตาม impact ที่มองเห็น)

1. **Desktop nav → pill bar** (mockup `.desktop-nav`): container กระจก `borderRadius:999, padding:5`,
   ปุ่ม active = `COLORS.purpleGradient` + `boxShadow:'0 6px 16px -6px rgba(139,123,247,0.55)'`,
   hover `translateY(-2px)` (มี .nav-btn อยู่แล้ว), navdot ทอง (unread news) มุมขวาบน
2. **Mobile bottom nav** (`.mobile-bottomnav`): `background:rgba(13,17,28,0.92)` + `backdropFilter:blur(14px)`,
   item active สีม่วง, navdot gradient ทอง `fontSize:9`
3. **ปุ่มทอง** (+ Trade / +) (`.gold-btn`): `background:COLORS.goldGradient`, `color:'#3a2405'`,
   `boxShadow:'0 10px 22px -9px rgba(239,159,39,0.6), inset 0 1px 0 rgba(255,255,255,0.55), inset 0 -3px 5px rgba(140,74,3,0.35)'`,
   hover scale 1.06 — อัพเดต `.clay-btn` ใน GLOBAL_CSS ให้ใช้ค่าชุดนี้แทนของเดิม
4. **Badge BUY/SELL/HOLD** (`.badge-*`): `fontSize:10.5, fontWeight:700, padding:'3px 9px', borderRadius:999`
   สีพื้น `COLORS.greenSoft/redSoft/purpleSoft` ตัวอักษร `green/red/purple`
5. **Avatar หุ้น** (`.avatar`): วงกลม 34px, ตัวอักษรย่อ 11.5px/800 — สีพื้นต่อ ticker (mockup มี palette ต่อตัว)
6. **KPI cards** (`.kpi-*`): label 11.5/600 faint · THB 22/700 · USD 12 faint · change pill 11.5/700
7. **ตาราง dtable ทั้งสองแท็บ**: thead `background:rgba(255,255,255,0.035)` มุมโค้ง 14 หัวท้าย, font 11/700,
   zebra แถวคี่ `rgba(255,255,255,0.015)`, hover `0.05`, แถวสูง 44px, td `padding:'11px 14px'`
8. **SlidingPill**: highlight เป็น `COLORS.purpleGradient` + shadow ม่วง, ปุ่ม `minWidth:88, fontSize:12`
9. **News unread treatment** (ตาม Redesign Prompt v3 ข้อที่ confirm 07-07): การ์ด unread = ขอบซ้ายทอง 3px
   + headline หนา, การ์ดอ่านแล้ว = จาง (opacity glass ต่ำลง + headline น้ำหนักปกติ), จุดทอง "New" ที่ footer
   (pulse ครั้งเดียวตอน mount — ห้ามกะพริบต่อเนื่อง), unread-count badge บน nav (ข้อ 1-2)
10. **Popup/Modal + confirm delete**: กระจก strong + `borderRadius:24`, ปุ่มยืนยันแดง/ยกเลิก ghost ตาม mockup
11. **กวาด borderRadius ทั้งไฟล์**: การ์ดใหญ่ 24 / กล่องกลาง 14 / เล็ก 9 / pill 999 (mockup `--r-*`)

## วิธี verify แต่ละข้อ
เปิด `3_CowContext/UI_Preview_v1.html` ใน browser (double-click) เทียบข้างกันกับแอปจริง (localhost หรือ
Vercel) ทีละแท็บ ทีละ view (ปุ่ม toggle ใน preview) — MBBook เป็นคนตัดสิน ผ่าน/ไม่ผ่าน ต่อข้อ

## หมายเหตุ
- แนะนำทำใน**แชทใหม่** (แชทปัจจุบันยาวมากแล้ว) — อ่านไฟล์นี้ + Handoff.md ก็เริ่มได้เลย
- ระวัง sandbox mount ตัดไฟล์/NUL bytes — ตรวจ `wc -l` + esbuild + grep sentinel ก่อน commit เสมอ
  (ดู memory `sandbox-mount-truncation` — เจอมาแล้ว 3 รอบใน 2 วัน)
