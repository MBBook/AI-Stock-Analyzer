"""
update_cronjob_weekends.py
=============================
แก้ job "A - Keepalive Wake" และ "B1 - Prefetch Hourly" บน cron-job.org
ให้ทำงานทุกวัน (รวมเสาร์-อาทิตย์) แทนที่จะเป็นแค่จันทร์-ศุกร์
(2026-07-02 — ตามคำขอ MBBook: ลดคอขวดงานนัตตี้ กระจาย load ไม่ให้กองรอวันจันทร์)

ใช้ API_KEY เดียวกับตอนสร้าง job (setup_cronjob_org.py) — ไม่ต้องสร้าง key ใหม่

วิธีใช้:
  1. แก้ค่า API_KEY ด้านล่างให้ตรงกับที่ใช้ตอน setup_cronjob_org.py
  2. รัน: python update_cronjob_weekends.py
  3. สคริปต์จะหา job ที่ตรงชื่อ "A - Keepalive Wake" และ "B1 - Prefetch Hourly" เองอัตโนมัติ
     แล้วอัพเดต schedule ให้เป็นทุกวัน (wdays = [-1])
"""

import json
import urllib.request
import urllib.error

API_KEY = "mMjneo7UQQd7pxV1R2Kl8rfh1CKwlCI85NtdXy00LxY="

API_ENDPOINT = "https://api.cron-job.org"
TARGET_TITLES = ["A - Keepalive Wake", "B1 - Prefetch Hourly"]


def api_get(path):
    req = urllib.request.Request(
        API_ENDPOINT + path,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def api_patch(path, payload):
    req = urllib.request.Request(
        API_ENDPOINT + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        method="PATCH",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def main():
    if "ใส่" in API_KEY:
        print("⚠️  ยังไม่ได้แก้ API_KEY ในไฟล์นี้ — แก้ก่อนแล้วรันใหม่")
        return

    print("🔍 กำลังหา jobs...")
    result = api_get("/jobs")
    jobs = result.get("jobs", [])

    found = 0
    for job in jobs:
        title = job.get("title", "")
        if title in TARGET_TITLES:
            job_id = job["jobId"]
            print(f"   พบ: {title} (jobId {job_id})")
            api_patch(f"/jobs/{job_id}", {
                "job": {
                    "schedule": {
                        "timezone": "UTC",
                        "hours": job["schedule"]["hours"],
                        "minutes": job["schedule"]["minutes"],
                        "mdays": job["schedule"]["mdays"],
                        "months": job["schedule"]["months"],
                        "wdays": [-1],  # ทุกวัน
                    }
                }
            })
            print(f"   ✅ อัพเดตแล้ว → ทำงานทุกวัน (รวมเสาร์-อาทิตย์)")
            found += 1

    if found < len(TARGET_TITLES):
        print(f"\n⚠️  เจอแค่ {found}/{len(TARGET_TITLES)} job — เช็คชื่อ job ใน console.cron-job.org ว่าตรงกับที่คาดไว้มั้ย")
    else:
        print(f"\n🎉 อัพเดตครบ {found} jobs แล้ว — เช็คผลที่ https://console.cron-job.org")


if __name__ == "__main__":
    main()
