# Handoff — AI Stock Analyzer V4 Frontend — กติกา/ข้อจำกัดที่ต้องรักษาไว้เสมอ

> ✅ 2026-07-08: ย่อไฟล์นี้ให้เล็กลงแล้ว — ของเดิม (เขียน 2026-07-05) บรรยายสถานะ UI ตอนนั้นซึ่งล้าสมัย
> ไปแล้ว ย้ายไป `Handoff_Archive_2026-07-05.md` (อ้างอิงประวัติเท่านั้น)
>
> **สถานะปัจจุบันจริงของ UI/backend ดูที่ `1_Reports/Pending.md`** (session ล่าสุดอยู่บนสุด) และ
> `3_CowContext/Blueprint.md` (ภาพรวมระบบ) แทน — ไฟล์นี้เหลือแค่**กฎที่ต้องรักษาไว้เสมอ**เมื่อแก้
> `frontend/src/App.jsx` (ยังใช้จริง ไม่ล้าสมัย)

---

## กติกา/ข้อจำกัดที่ต้องรักษาไว้เสมอ (เจอบั๊กมาแล้วจริง อย่าลืมตอนแก้ไฟล์นี้)

1. **ห้ามเรียก helper function เป็น JSX tag** (เช่น `<Foo/>`) — ต้องเรียกเป็น `Foo()` ตรงๆ เพราะ
   function ถูกสร้างใหม่ทุก re-render ของ `DashboardV4` มองเป็นคนละ component type ทุกครั้ง ทำให้
   React unmount/remount ทั้ง subtree (input เสีย focus ตอนพิมพ์)
2. **ห้ามเรียก `useState`/`useEffect` จากใน helper function แบบมีเงื่อนไข** (เช่น สลับ tab) เพราะผิดกฎ
   Rules of Hooks ทันที — ต้องอยู่ที่ state ระดับบนสุดของ `DashboardV4` เท่านั้น (เหตุผลที่ count-up
   animation ตัวเลขยังไม่ implement)
3. **Desktop ≠ Mobile จริง** ต้องแยก component tree จริง (`Mobile*`/`Desktop*` คนละฟังก์ชัน) ไม่ใช่แค่
   responsive breakpoint เดียวที่ย่อ/ขยาย — ยกเว้น System tab ที่ MBBook ยอมรับให้ใช้ร่วมกันได้
4. **THB/USD ต้องโชว์คู่กันเสมอ** (THB ใหญ่เด่น, USD เล็กสีเทาใต้) **ห้ามทำเป็นปุ่ม toggle สลับสกุล**
5. **Sandbox bash mount stale เสมอสำหรับไฟล์ที่เพิ่งแก้ผ่าน Windows tool** — ห้ามเชื่อผลจาก
   `npm start`/`node`/`wc -l`/`py_compile` ที่รันผ่าน bash ในเซสชันนี้ทันทีหลังแก้ไฟล์ (เคยเห็นไฟล์สั้นกว่า
   จริงมาก, เคยเจอ syntax error ปลอมจากไฟล์ค้าง) ตรวจโครงสร้างไฟล์ผ่าน Read/Grep tool เท่านั้น แล้วให้
   MBBook รัน `npm start`/`pytest` เองที่เครื่องจริงเสมอเพื่อยืนยัน
6. **ห้ามแต่งข้อมูลที่ไม่มีจริง** — ชื่อเต็มบริษัท/คำอธิบายบริษัทต้องมาจาก backend field จริง
   (`stock.company_name`/`stock.company_description`) หรือ fallback ไป `COMPANY_NAMES` dict ที่ระบุ
   ชัดว่าเป็นข้อมูลสาธารณะจริงเท่านั้น ไม่ใช่เดา — ถ้าไม่มีข้อมูลให้โชว์ข้อความสถานะจริง ไม่ใช่ปั้นเนื้อหา
7. **กราฟ "สะสม" ทุกจุดต้องเป็นกราฟเส้น** (ไม่ใช่แท่ง) มี animation วาดจากซ้ายไปขวา เส้นขึ้น และมีค่ากำกับ
   ที่ปลายเส้น — ใช้ CSS class `.line-draw` ที่มีอยู่แล้วใน `constants.js` (`GLOBAL_CSS`)
8. **✅ เพิ่ม 2026-07-08**: SVG ที่ใช้ `preserveAspectRatio="none"` (ยืดเต็ม container ไม่รักษาสัดส่วน)
   ห้ามใส่ `<text>` label ในหน่วย viewBox ข้างใน — ตัวเลขจะยืดเพี้ยนไม่สมส่วนทันทีถ้าสัดส่วน container
   เปลี่ยนจาก viewBox เดิม (เจอจริงกับ `CumulativeLineChart`) ให้ย้าย label ออกมาเป็น `<span>` HTML
   ธรรมดา วางตำแหน่งด้วย % ของ container แทน (font-size เป็น px จริง ไม่ยืดตาม viewBox)

---

*อ้างอิงเพิ่มเติม: `Pending.md` (สถานะ+ประวัติล่าสุด), `Blueprint.md` (ภาพรวมระบบ backend),
`Handoff_Archive_2026-07-05.md` (สถานะ UI เก่า ณ 2026-07-05 — ล้าสมัยแล้ว)*
