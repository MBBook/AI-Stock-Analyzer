# Output — คำสั่งที่ MBBook รันวันนี้ (2026-07-08)

## 1. Push #1 — feat: day-change % + Portfolio/System chart period ใหม่ + ลบปุ่มลบซ้ำซ้อน
```
(.venv) PS D:\AI_Project\Dashboard_Share> git add main.py frontend/src/App.jsx
>> git commit -m "..."
>> git push origin main | Tee-Object -FilePath push_output.md
[main 5238963] feat: เพิ่ม day-change % ต่อ ticker จาก signal_history + Portfolio/System chart period ใหม่ + ลบปุ่มลบซ้ำซ้อนใน Tickers
 2 files changed
remote: This repository moved. Please use the new location:
remote:   https://github.com/MBBook/AI-Stock-Analyzer.git
To https://github.com/mbbook/ai-stock-analyzer.git
   ...5238963  main -> main
```
(รอบแรกจาก `frontend/` ล้มเหลวแบบเงียบ "Everything up-to-date" เพราะ path ไม่ resolve — ต้อง `cd` กลับ root ก่อน, และเจอ `.git/index.lock` ค้างระหว่างทาง ต้อง `Remove-Item .git\index.lock -Force`)

## 2. Push #2 — hotfix: wrap change_pct calc in try/except
```
[main cb8dde0] fix: hotfix /stocks 500 error — wrap change_pct calc in try/except กัน endpoint ทั้งตัวล่ม
   5238963..cb8dde0  main -> main
```
**ผล**: ไม่ช่วย — `/stocks` ยัง 500 อยู่ (root cause อยู่นอก try/except block นี้)

## 3. Render deploy log — error จริงตอน `/stocks` 500 (commit cb8dde0)
```
File "/opt/render/project/src/main.py", line 560, in get_stocks
    "company_name":        hc.company_name        if hc else None,
AttributeError: 'HourlyCache' object has no attribute 'company_name'
```

## 4. Push #3 — fix: เพิ่ม company_name/company_description column ใน models.py
```
git add models.py
git commit -m "fix: add missing company_name/company_description columns to HourlyCache model (fixes /stocks 500)"
git push origin main | Tee-Object -FilePath push_output.md
[main 1145680] fix: add missing company_name/company_description columns to HourlyCache model (fixes /stocks 500)
   cb8dde0..1145680  main -> main
```

## 5. Render deploy log — deploy 1145680 รอบแรก Fail (คนละสาเหตุ ไม่เกี่ยวกับโค้ด)
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) connection to server at
"ep-morning-heart-aocxjio2.c-2.ap-southeast-1.aws.neon.tech" (13.251.17.193), port 5432 failed:
ERROR:  Control plane request failed
==> Exited with status 1
```
**แก้**: กด Manual Deploy → Deploy latest commit (retry) ผ่าน — Live เวลา ~2:3x PM

## 6. ยืนยันผลจริงหลัง retry — `GET /stocks`
```
{"count":28,"stocks":[{"id":29,"ticker":"OKTA", ... "change_pct":1.32, ...}, ...]}
```
✅ กลับมาใช้งานได้ปกติ — `change_pct` คำนวณถูกต้อง (บางตัว `null` ถ้ามี signal_history ไม่ถึง 2 คืน ตามที่ออกแบบไว้)
