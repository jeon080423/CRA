import sys
import os
import requests

# Add relevant paths
sys.path.append(r"k:\app\1.보고서 분석기")

from api.fss_api import CORP_BASIC_URL, FINA_STAT_URL, SUBSIDIARY_URL

def diagnose_url(name, url, params):
    print(f"--- Diagnosing {name} ---")
    print(f"URL: {url}")
    try:
        resp = requests.get(url, params=params, timeout=10)
        print(f"Status Code: {resp.status_code}")
        if resp.status_code == 200:
            try:
                data = resp.json()
                print("JSON Response: SUCCESS (truncated)")
                body = data.get("response", {}).get("body", {})
                items = body.get("items", {})
                if not items:
                    print("Items: EMPTY")
                else:
                    print("Items: FOUND")
            except:
                print("JSON Parsing: FAILED")
                print(resp.text[:500])
        else:
            print(resp.text[:500])
    except Exception as e:
        print(f"Error: {e}")

# Use a dummy service key for URL format check (if it 401s, it means the endpoint exists)
# Or find a real one if needed, but let's check format first.
service_key = "DUMMY_KEY" # In real use, it would be from config

params = {
    "serviceKey": service_key,
    "numOfRows": 1,
    "pageNo": 1,
    "resultType": "json",
    "corpNm": "삼성전자"
}

diagnose_url("CORP_BASIC_V2", CORP_BASIC_URL, params)
diagnose_url("FINA_STAT_V2", FINA_STAT_URL, {"serviceKey": service_key, "crno": "1101110003247", "bizYear": "2023", "resultType": "json"})
