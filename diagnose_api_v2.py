import requests
import json
from urllib.parse import unquote

def diagnose():
    service_key = "6be75af37c6693a24417c2ed2930e4bd4dd01dddf289552260ce8ce1daf43414"
    print(f"Testing with Key: {service_key[:10]}...")

    tests = [
        ("NTS (Working Ref)", "https://api.odcloud.kr/api/nts-businessman/v1/status", {"serviceKey": service_key}, "POST", {"b_no": ["2158635051"]}),
        ("NPS (HTTP)", "http://apis.data.go.kr/B552015/NpsBplcInfoInqireServiceV2/getBassInfoSearchV2", {"serviceKey": service_key, "wkplNm": "삼성전자", "dataType": "json"}, "GET", None),
        ("NPS (HTTPS)", "https://apis.data.go.kr/B552015/NpsBplcInfoInqireServiceV2/getBassInfoSearchV2", {"serviceKey": service_key, "wkplNm": "삼성전자", "dataType": "json"}, "GET", None),
        ("FSS (HTTP)", "http://apis.data.go.kr/1160100/service/GetCorpBasicInfoService_V2/getCorpOutline", {"serviceKey": service_key, "corpNm": "삼성전자", "resultType": "json"}, "GET", None),
        ("NHIS (Odcloud)", "https://api.odcloud.kr/api/3049051/v1/uddi:71a6826c-7c86-4b4c-8e90-b61607d40214", {"serviceKey": service_key, "page": 1, "perPage": 1}, "GET", None),
    ]

    for name, url, params, method, payload in tests:
        print(f"\n--- Testing {name} ---")
        try:
            if method == "POST":
                resp = requests.post(url, params=params, data=json.dumps(payload) if payload else None, headers={'Content-Type': 'application/json'} if payload else None, timeout=10)
            else:
                resp = requests.get(url, params=params, timeout=10)
            
            print(f"Status: {resp.status_code}")
            print(f"Content: {resp.text[:200]}")
            
            if "SERVICE_KEY_IS_NOT_REGISTERED" in resp.text:
                 print("Result: ❌ Key not registered for this SPECIFIC service.")
            elif "INVALID_KEY" in resp.text:
                 print("Result: ❌ Invalid Key.")
            elif resp.status_code == 200 and ("삼성전자" in resp.text or "totalCount" in resp.text or "status_code" in resp.text):
                 print("Result: ✅ SUCCESS.")
            else:
                 print("Result: ⚠️ Failure or Empty result.")
                 
        except Exception as e:
            print(f"Result: ❌ Error: {e}")

if __name__ == "__main__":
    diagnose()
