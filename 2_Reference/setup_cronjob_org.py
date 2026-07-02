"""
setup_cronjob_org.py
=====================
สร้าง cron jobs บน cron-job.org แทนที่ GitHub Actions schedule ทั้งหมด
(2026-07-02 — GitHub Actions cron พิสูจน์แล้วว่าไม่เสถียร: keepalive.yml ตั้งทุก 10 นาที
แต่รันจริงแค่ 21 ครั้งใน 5.5 วัน ควรรัน ~790 ครั้ง)

วิธีใช้:
  1. สมัครบัญชีฟรีที่ https://console.cron-job.org
  2. ไปที่ Settings > API Keys > สร้าง API key ใหม่
  3. แก้ค่า API_KEY และ RENDER_URL ด้านล่างให้เป็นของจริง
  4. รัน: python setup_cronjob_org.py
  5. เช็คผลที่ https://console.cron-job.org (ควรเห็น 6 jobs ใหม่)

หมายเหตุ: สคริปต์นี้สร้าง job ใหม่ทุกครั้งที่รัน (ไม่เช็ค duplicate) —
ถ้ารันซ้ำจะได้ job ซ้อนกัน ให้ลบ job เก่าออกก่อนถ้าต้องการรันใหม่
"""

import json
import time
import urllib.request
import urllib.error

# ⚠️ แก้ 2 ค่านี้ก่อนรัน
API_KEY = "mMjneo7UQQd7pxV1R2Kl8rfh1CKwlCI85NtdXy00LxY="
RENDER_URL = "https://ai-stock-analyzer-msli.onrender.com"  # ห้ามมี / ปิดท้าย

API_ENDPOINT = "https://api.cron-job.org"

GET, POST = 0, 1


def create_job(title, url, method, hours, minutes, wdays, mdays=None, months=None):
    payload = {
        "job": {
            "title": title,
            "url": url,
            "enabled": True,
            "saveResponses": True,
            "requestMethod": method,
            "schedule": {
                "timezone": "UTC",  # ใช้ UTC ตรงกับ cron เดิมใน .github/workflows เป๊ะ ไม่ต้องแปลงเวลา
                "hours": hours,
                "minutes": minutes,
                "mdays": mdays or [-1],
                "months": months or [-1],
                "wdays": wdays,
            },
            "notification": {
                "onFailure": True,
                "onFailureCount": 1,
                "onDisable": True,
            },
        }
    }
    req = urllib.request.Request(
        API_ENDPOINT + "/jobs",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        method="PUT",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            print(f"✅ {title} → jobId {result['jobId']}")
            return result["jobId"]
    except urllib.error.HTTPError as e:
        print(f"❌ {title} ล้มเหลว: HTTP {e.code} — {e.read().decode()}")
        return None


def main():
    if "ใส่" in API_KEY or "ใส่" in RENDER_URL:
        print("⚠️  ยังไม่ได้แก้ API_KEY / RENDER_URL ในไฟล์นี้ — แก้ก่อนแล้วรันใหม่")
        return

    jobs = [
        # (title, path, method, hours, minutes, wdays)
        # A, B1: ดึงทุกวัน (รวมเสาร์-อาทิตย์) แก้ 2026-07-02 ตามคำขอ MBBook — ลดคอขวดงานนัตตี้
        # (0=Sun...6=Sat ตาม cron-job.org API — ใช้ [-1] = ทุกวัน)
        ("A - Keepalive Wake", "/health", GET,
         list(range(2, 20)), [0, 10, 20, 30, 40, 50], [-1]),

        ("B1 - Prefetch Hourly", "/prefetch", POST,
         list(range(2, 15)), [5], [-1]),

        ("B2 - Prefetch Prewarm", "/prefetch", POST,
         [14], [45], [1, 2, 3, 4, 5]),

        ("C1 - Workflow Trigger (Monday, include_weekend)", "/workflow?include_weekend=true", POST,
         [15], [0], [1]),

        ("C2 - Workflow Trigger (Tue-Fri)", "/workflow", POST,
         [15], [0], [2, 3, 4, 5]),

        ("D - Workflow Resume Self-heal", "/workflow/resume", POST,
         [15, 16, 17, 18], [0, 10, 20, 30, 40, 50], [1, 2, 3, 4, 5]),
    ]

    for i, (title, path, method, hours, minutes, wdays) in enumerate(jobs):
        create_job(title, RENDER_URL + path, method, hours, minutes, wdays)
        if i < len(jobs) - 1:
            time.sleep(13)  # cron-job.org limit: 5 requests/min ตอนสร้าง job

    print("\n🎉 เสร็จแล้ว — เช็คผลที่ https://console.cron-job.org")
    print("   แนะนำ: เปิด job แต่ละตัวแล้วเช็คว่า 'Next execution' ตรงกับที่คาดไว้ก่อนวางใจ")


if __name__ == "__main__":
    main()
