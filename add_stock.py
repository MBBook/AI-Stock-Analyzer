import requests

url = "https://ai-stock-analyzer-msli.onrender.com/stocks"
headers = {"Content-Type": "application/json"}

stocks_to_add = [
    # Already in system
    "GOOGL", "NVDA", "ASML", "TSM", "AMZN", "BRK.B", "MSFT", "AAPL", "TSLA",
    # New additions
    "WDC", "SNDK", "NOW", "OKLO", "CCJ", "PLTR", "ONDS", "NBIS", "VRT",
    "MU", "ARM", "IONQ", "ASTS", "LWLG", "SPCX", "NVTS", "RKLB", "ORCL",
    "ZS", "OKTA", "AMD", "MRVL", "META", "AVGO", "LLY", "BAC", "V",
    "MA", "NFLX", "AXP", "KO",
]

results = []

for ticker in stocks_to_add:
    try:
        response = requests.post(f"{url}?ticker={ticker}", headers=headers, timeout=15)
        line = f"[{response.status_code}] {ticker}: {response.text.strip()}"
    except Exception as e:
        line = f"[ERR] {ticker}: {str(e)}"
    print(line)
    results.append(line)

summary = f"\n--- สรุป: เพิ่มทั้งหมด {len(stocks_to_add)} ตัว ---"
print(summary)
results.append(summary)

with open("output.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(results))

print("บันทึกผลลัพธ์ใน output.txt แล้ว")