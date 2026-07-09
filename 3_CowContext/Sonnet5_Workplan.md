# Sonnet5_Workplan — แผนงานที่ Fable วางไว้ให้ (2026-07-09 · รอบ 3)

> **ผู้เขียน:** Claude Fable 5 — รอบ 3 (เที่ยงคืน 09 ก.ค.): Fable ทำจบเกือบหมดแล้ว —
> **โค้ดเขียนเสร็จ + pytest ผ่าน 158 passed (รันจริงใน sandbox) + commit แล้วทั้ง 2 ก้อน**
>
> ## ⚡ สถานะจริงตอนนี้ — เหลือแค่ 2 อย่าง
> 1. **MBBook รัน `git push` ที่ terminal** (commit `510d595` code + docs commit รออยู่ local)
>    → Render auto-deploy เอง ~5 นาที
> 2. **Sonnet 5 ทำเฉพาะงาน D (verify 2 นัด) + งาน E (ปิดเอกสาร)** — งาน A/B/C ข้ามได้เลย
>    Fable ทำหมดแล้ว (งาน A: 158 passed ยืนยันแล้ว · งาน B.1-B.2/C: commit แล้ว ยกเว้น push)
>    ⚠️ ยกเว้น B.3 (verify deploy หลัง push) ยังต้องทำ
>
> ## ⛔ กฎการใช้แผนนี้ — อ่านก่อนทำอะไรทั้งสิ้น
> 1. **ทำตาม flow ในไฟล์นี้เท่านั้น ห้ามคิดออกแบบเอง ห้ามแก้โค้ดที่ Fable เขียนไว้ ห้ามเพิ่มงานเอง ห้ามข้ามขั้น**
> 2. เจออะไร**ไม่ตรงกับ Expected** ที่ระบุไว้ → **หยุดทันที รายงาน MBBook** ห้ามเดา ห้ามแก้เอง
> 3. ทุก 🛑 STOP-POINT ต้องรอ MBBook ยืนยันก่อนไปต่อ
> 4. ทำเรียงลำดับ A → B → C → D → E เท่านั้น

---

## Phase 0 — อ่าน context ก่อนเริ่ม (บังคับ, ตามลำดับนี้)

1. `3_CowContext/Blueprint.md` — ภาพรวมระบบ (source of truth)
2. `3_CowContext/Handoff.md` — กฎ 8 ข้อ frontend + กฎ bash stale
3. `1_Reports/Pending.md` — สถานะล่าสุด (entry บนสุด = สิ่งที่ Fable เพิ่งทำ)
4. ไฟล์นี้ทั้งไฟล์

### กฎเหล็กตลอดทุกงาน

- **MBBook ใช้ VS Code + PowerShell** — ทุกคำสั่งเป็น PowerShell + pipe ลง output.md: `<คำสั่ง> | Tee-Object -FilePath output.md`
- **ห้ามเชื่อผล bash sandbox กับไฟล์ที่เพิ่งถูกแก้** — ตรวจไฟล์ด้วย Read/Grep tool เท่านั้น, pytest/npm รันโดย MBBook ที่เครื่องจริงเสมอ
- ห้ามแต่งข้อมูลที่ไม่มีจริง · ห้าม `git add .` (ระบุไฟล์ทุกครั้ง — บทเรียน Defect #17)
- ทุกงานจบ: อัพเดต `1_Reports/Pending.md` (entry ใหม่บนสุด) + สรุปสั้นให้ MBBook
- ตอบภาษาไทย เรียกผู้ใช้ว่า MBBook แทนตัวเองว่า Cow

---

## ✅ สิ่งที่ Fable ทำเสร็จแล้ว (2026-07-08 — ห้ามทำซ้ำ ห้ามแก้)

| # | งาน | ผล |
|---|-----|----|
| 1 | ลบ NUL bytes 7,024 ตัวท้าย `frontend/src/App.jsx` (เศษจาก write ที่ crash) | ไฟล์กลับมาตรงกับ HEAD เป๊ะ — **App.jsx ไม่ต้อง commit แล้ว** (`git diff` = ว่าง) |
| 2 | ตรวจโค้ด company profile ใน `agents.py` (Step 1.3 เดิม) | ✅ ผ่าน — `_fetch_company_profile` 2 จุด, `_func`/`yfinance` import ครบ, chain ถึง `HourlyCache(...)` ครบ |
| 3 | เทียบ `UI_Redesign_Prompt_v2.txt` vs `v3.txt` | **ต่างกันจริง** (byte 3378, บรรทัด 20) → เก็บทั้งคู่ ห้ามลบ |
| 4 | ลบ `3_CowContext/UI_Spec.md` (MBBook สั่ง — ล้าสมัยถาวร) | ✅ ลบแล้ว |
| 5 | เพิ่ม `.claude/` เข้า `.gitignore` | ✅ แล้ว |
| 6 | **เขียนโค้ด PEG ratio ทั้งหมด** ใน `agents.py` | ✅ ตาม design เดิม: constants 3 ตัว (บรรทัด ~118-120), method `_fetch_peg_alpha_vantage` (~359), carry-forward + refresh block ใน `natty_prefetch_prices` (~578-615), จุด apply ต่อ ticker (~682-687) |
| 7 | **เขียน tests 9 ตัว** ใน `test_agents.py` (class `TestPegAlphaVantage` ท้ายไฟล์) | ✅ ครอบ: fetch สำเร็จ / rate-limit Note+Information break / "None"/"-"/dict ว่าง / exception รายตัว / นอกรอบไม่ยิง+carry / ในรอบค่าใหม่ชนะ / cap 20 จาก 30 / AV ล่มทั้งระบบ prefetch ไม่ล้ม |

**Design PEG ที่ implement ไปแล้ว (อ้างอิงเวลาตรวจ):** refresh เฉพาะ prefetch รอบ `02:xx UTC` (= 09:05 Bangkok), สูงสุด 20 ตัว/วัน (เหลือ quota 5/25 ให้ Tier-3 price fallback), เรียงจาก stale สุด, PEG อายุ ≤ 48 ชม. ถือว่า fresh, รอบอื่น carry-forward เหมือน `earnings_date`, เจอ `{"Note"}`/`{"Information"}` = rate limit → break ทั้ง batch, ทุก error ห่อ try/except ไม่กระทบ prefetch ราคา

---

## งาน A — รัน test ทั้งชุด (ให้ MBBook รันที่เครื่อง)

```powershell
python -m pytest test_agents.py test_main.py -v | Tee-Object -FilePath output.md
```

**Expected: `158 passed`** (149 เดิม + 9 ใหม่ของ PEG)
🛑 **STOP-POINT A:** fail แม้แต่ตัวเดียว → หยุด อ่าน output.md รายงาน MBBook พร้อมชื่อ test + error เต็มๆ — **ห้ามแก้โค้ด/test เองโดยไม่ได้รับอนุมัติ** (โค้ดนี้ Fable เขียน ถ้า fail ให้ MBBook เอา error กลับไปถาม Fable ได้)

---

## งาน B — Commit #1: โค้ด backend → deploy

### B.1 ยืนยันรายการไฟล์ก่อน commit

```powershell
git status --short | Tee-Object -FilePath output.md
```
**Expected modified:** `.gitignore, agents.py, database.py, test_agents.py` + ไฟล์ .md docs (`1_Reports/*, 3_CowContext/*, output.md, frontend/output.md`) — **ต้องไม่มี `frontend/src/App.jsx`** (Fable ล้างแล้ว) และ **ต้องไม่มีไฟล์ .py อื่นนอกจากที่ระบุ**
🛑 **STOP-POINT B:** รายการไม่ตรงนี้ → หยุด รายงาน MBBook

### B.2 Commit + push (เฉพาะโค้ด — docs ไว้ Commit #2)

```powershell
git add agents.py test_agents.py database.py .gitignore
git commit -m "feat: company profile fetch (ค้างจาก 07-05) + PEG ratio via Alpha Vantage OVERVIEW (rotation <=20/day, 48h carry-forward, rate-limit guard) + 9 tests"
git push | Tee-Object -FilePath output.md
```

หมายเหตุ: commit เดียวพอ — company profile กับ PEG อยู่ใน `agents.py` ไฟล์เดียวกัน แยก deploy ไม่ได้อยู่แล้ว · `database.py` เปลี่ยนแค่ line-ending (commit ให้ tree สะอาด)

### B.3 Verify deploy บน Render

1. รอ auto-deploy ~5 นาที → `GET https://ai-stock-analyzer-msli.onrender.com/health` ต้อง `{"status":"ok"}`
2. ถ้า deploy fail และ log เป็น `Control plane request failed` (Neon ชั่วคราว — เคยเกิดกับ `1145680`) → MBBook กด Manual Deploy retry ได้สูงสุด 2 ครั้ง
3. 🛑 **STOP-POINT C:** retry 2 ครั้งยัง fail หรือ error อื่น → หยุด รายงาน MBBook พร้อม log

---

## งาน C — Commit #2: docs

```powershell
git add 1_Reports/ 3_CowContext/ output.md frontend/output.md
git commit -m "docs: Sonnet5_Workplan + UI mockup/redesign prompt เข้า repo, ลบ UI_Spec.md ล้าสมัย, อัพเดต Pending/Blueprint/Handoff"
git push | Tee-Object -FilePath output.md
```
(git จะเห็น `UI_Spec.md` เป็น deleted ถ้าเคย tracked — ถ้าไม่เคย tracked ก็ไม่มีรายการ ไม่ต้องทำอะไร)

---

## งาน D — Verify ข้อมูลจริง (2 นัด)

### D.1 นัดแรก — company profile (ชั่วโมงถัดไปหลัง deploy)

- Prefetch ยิงนาที :05 ทุกชั่วโมง (09:05–21:05 Bangkok) → หลังรอบแรกผ่านไป เช็ค `GET /stocks`
- **Expected:** `company_name` มีค่าจริง (ส่วนใหญ่ของ ~30 ตัว), `company_description` มีข้อความ
- **อย่าตกใจ:** prefetch รอบแรกช้าขึ้น ~20-40 วิ (เรียก Finnhub profile2 + yfinance 30 ตัว, มี sleep 0.5s/ตัว) — รอบถัดไป carry-forward ไม่เรียกซ้ำ
- 🛑 **STOP-POINT D:** ยัง null ทั้งหมดหลัง prefetch สำเร็จ → หยุด ดู Render log รายงาน MBBook

### D.2 นัดสอง — PEG ratio (เช้าวันถัดไป หลัง 09:10 Bangkok)

- PEG refresh ทำงานเฉพาะรอบ 09:05 Bangkok (02:xx UTC) → **ต้องรอเช้าวันถัดไป**
- **Expected:** `GET /stocks` → `peg_ratio` มีค่าจริง ~20 ตัว (ที่เหลือ ~10 ตัวครบเช้าวันถัดไปอีกวัน — rotation 2 วัน)
- หมายเหตุ: บาง ticker PEG อาจเป็น null จริงๆ (AV ไม่มีข้อมูล เช่น ETF) — ถ้าส่วนใหญ่มีค่าถือว่าผ่าน
- **บันทึกนัดนี้ลง `Pending.md` ให้ชัดว่ารอเช็ควันไหน** กันหลุด
- 🛑 **STOP-POINT E:** เช้าวันถัดไปยัง null หมดทุกตัว → หยุด ดู Render log (คำว่า "PEG" ใน log_action) รายงาน MBBook

---

## งาน E — ปิดงาน + เอกสาร

1. `Pending.md`: entry ใหม่บนสุด (ทำอะไร, commit hash, ผล verify D.1/D.2) + **ปิดรายการค้างข้อ 1 (PEG)** เมื่อ D.2 ผ่าน
2. `Blueprint.md`: (ก) ตาราง schema `hourly_cache` — ลบหมายเหตุ "field pegRatio ยังไม่ยืนยัน" เปลี่ยนเป็น "PEG จาก Alpha Vantage rotation ≤20/วัน" (ข) section 10 Test Coverage — อัพเดตตัวเลขเป็น 158 (ค) ถ้า D.1 ผ่าน — อัพเดตหมายเหตุ `/stocks` ว่า company_name ใช้งานจริงแล้ว
3. สรุปทั้งหมดให้ MBBook แล้ว**รอคำสั่ง — ห้ามหยิบงานใหม่เอง**

### Routine monitoring (ทำท้าย session)

- `GET /workflow/history` — คืนล่าสุดต้อง COMPLETE, cost ในเกณฑ์ ($0.60 Tue-Thu / $0.85 Mon / $0.75 Fri)
- วันเสาร์/หลังศุกร์: `GET /nik/suggestions` — มี pending ใหม่ → แจ้ง MBBook (ห้าม apply เอง)
- ROI: ห้ามตีความตัวเลข `/roi/summary` ก่อน ~18 ก.ค. (signal_history เริ่มเก็บ 04 ก.ค. ยังไม่ครบ 14 วัน)

---

## ⛔ รายการห้ามทำเด็ดขาด

1. **ห้ามแก้โค้ดที่ Fable เขียน** (agents.py PEG block + tests) — ถ้า test fail ให้รายงาน ไม่ใช่แก้
2. **ห้ามแตะ App.jsx / component extrac