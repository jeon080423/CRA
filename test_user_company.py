import requests
import json

key = "6be75af37c6693a24417c2ed2930e4bd4dd01dddf289552260ce8ce1daf43414"

def test_specific_company():
    company = "경현"
    url = "http://apis.data.go.kr/B552015/NpsBplcInfoInqireServiceV2/getBassInfoSearchV2"
    params = {
        "serviceKey": key,
        "wkplNm": company,
        "pageNo": 1,
        "numOfRows": 20,
        "dataType": "json"
    }
    
    print(f"--- Testing NPS for '{company}' ---")
    try:
        resp = requests.get(url, params=params, timeout=10)
        print(f"Status: {resp.status_code}")
        data = resp.json()
        
        body = data.get("response", {}).get("body", {})
        items = body.get("items", {})
        
        if isinstance(items, dict):
            item_list = items.get("item", [])
        elif isinstance(items, list):
            item_list = items
        else:
            item_list = []
            
        print(f"Found {len(item_list)} items.")
        for i, item in enumerate(item_list[:3]):
            print(f"--- Item {i} ---")
            print(json.dumps(item, indent=2, ensure_ascii=False))
            
    except Exception as e:
        print(f"Error: {e}")

def test_fss_specific():
    company = "경현"
    url = "http://apis.data.go.kr/1160100/GetCorpBasicInfoService_V2/getCorpOutline"
    params = {
        "serviceKey": key,
        "corpNm": company,
        "pageNo": 1,
        "numOfRows": 5,
        "resultType": "json"
    }
    print(f"\n--- Testing FSS for '{company}' ---")
    try:
        resp = requests.get(url, params=params, timeout=10)
        print(f"Status: {resp.status_code}")
        data = resp.json()
        items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        if isinstance(items, dict): items = [items]
        
        print(f"Found {len(items)} items.")
        for i, item in enumerate(items):
            print(f"--- Item {i} ---")
            print(json.dumps(item, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_specific_company()
    test_fss_specific()
