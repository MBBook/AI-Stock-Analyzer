# Pending Issues — AI Stock Analyzer

รายการปัญหาที่ยังไม่ได้แก้ไข เรียงตามความสำคัญ

---

*ไม่มี pending issues ในขณะนี้ — ทุกปัญหาได้รับการแก้ไขแล้ว*

---

## ✅ แก้ไขแล้ว (2026-06-24)

| ปัญหา | แก้ใน |
|-------|--------|
| Market Cap หน่วยไม่ชัด (WDC, SNDK, MU, NFLX, ASTS) | agents.py — เพิ่ม "M USD" ใน display |
| ASML ราคา New High เกิน 52-week High | agents.py — เพิ่ม at_new_high flag + update high = price |
| NFLX validation status PASS_WITH_WARNING ผิด format | agents.py — บังคับ มด ส่งแค่ PASS/FAIL |
| BRK.B, ASML, TSM ขาด 52-week range | agents.py — CROSS_CURRENCY_TICKERS บังคับ AV fallback |
| Agent เอ 529 Overloaded | agents.py — sleep(30) ก่อน retry เมื่อ 529 |

*อัปเดตล่าสุด: 2026-06-24*
