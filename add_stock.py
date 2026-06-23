import requests
import json

# ลิงก์ URL ตัวจริงของโปรเจกต์นายแบบระบุปลายทางชัดเจน 100%
url = "https://ai-stock-analyzer-msli.onrender.com/stocks"
headers = {"Content-Type": "application/json"}

# 📦 รายชื่อหุ้นกลุ่มใหญ่ของนายที่ต้องการแอดเข้าสู่ตารางระบบ
stocks_to_add = ["NVDA", "AMZN", "BRK.B", "GOOGL", "ASML", "TSM"]

try:
    for ticker in stocks_to_add:
        print(f"กำลังยิงแอดหุ้น {ticker} เข้าตารางระบบ...")
        response = requests.post(f"{url}?ticker={ticker}", headers=headers, timeout=15)


    
    print("\n--- ผลลัพธ์จากการยิงแอดหุ้น ---")
    print(f"Status Code: {response.status_code}")
    print(f"Response Text: {response.text}")
    print("-------------------------------")
    
except Exception as e:
    print(f"เกิดข้อผิดพลาดในการเชื่อมต่อ: {str(e)}")