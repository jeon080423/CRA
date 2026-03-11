import requests
import json
import datetime
import sys
import os

# Ensure the constants can be imported from api folder
sys.path.append(os.getcwd())
try:
    from api.constants import DATA_GO_KR_SERVICE_KEY
except ImportError:
    DATA_GO_KR_SERVICE_KEY = "dummy"

def test_fss_v2(crno="1101110003000"): # Samsung Electronics as example
    print(f"\n--- Testing FSS V2 (CRNO: {crno}) ---")
    url = "https://apis.data.go.kr/1160100/service/GetFinaStatInfoService_V2/getSummFinaStat_V2"
    params = {
        "serviceKey": DATA_GO_KR_SERVICE_KEY,
        "crno": crno,
        "bizYear": "2024",
        "resultType": "json"
    }
    try:
        print(f"URL: {url}")
        resp = requests.get(url, params=params, timeout=12)
        print(f"Status Code: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print("Response Header:", json.dumps(data.get("response", {}).get("header", {}), indent=2, ensure_ascii=False))
            body = data.get("response", {}).get("body", {})
            items = body.get("items", {})
            if items:
                item_list = items.get("item", [])
                if item_list:
                    print(f"Found {len(item_list)} items.")
                    print("First Item Keys:", list(item_list[0].keys()))
                else:
                    print("Body structure exists but item list is empty.")
            else:
                print("No items found.")
        else:
            print(f"Error Response: {resp.text[:500]}")
    except Exception as e:
        print(f"Exception: {e}")

def test_nps_v2(name="삼성전자"):
    print(f"\n--- Testing NPS V2 (Name: {name}) ---")
    url = "https://apis.data.go.kr/B552015/NpsBplcInfoInqireServiceV2/getBassInfoSearchV2"
    params = {
        "serviceKey": DATA_GO_KR_SERVICE_KEY,
        "wkplNm": name,
        "pageNo": 1,
        "numOfRows": 5,
        "dataType": "json"
    }
    try:
        resp = requests.get(url, params=params, timeout=12)
        print(f"Status Code: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            body = data.get("response", {}).get("body", {})
            items = body.get("items", {}).get("item", [])
            if items:
                if isinstance(items, dict): items = [items]
                print(f"Found {len(items)} items.")
                for i, item in enumerate(items[:2]):
                    print(f"Item {i+1} BRN (bzowrRgstNo): {item.get('bzowrRgstNo')}")
                    print(f"Item {i+1} Name (wkplNm): {item.get('wkplNm')}")
            else:
                print("No items found.")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_fss_v2()
    test_nps_v2()
