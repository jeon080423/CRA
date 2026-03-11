import requests
import json
import traceback

URL = "http://apis.data.go.kr/1160100/GetCorpBasicInfoService_V2/getCorpOutline"
SERVICE_KEY = "6be75af37c6693a24417c2ed2930e4bd4dd01dddf289552260ce8ce1daf43414"

def test_fss_masking(corp_nm):
    params = {
        "serviceKey": SERVICE_KEY,
        "corpNm": corp_nm,
        "numOfRows": 5,
        "pageNo": 1,
        "resultType": "xml",
    }
    print(f"\n--- Testing: {corp_nm} ---")
    try:
        resp = requests.get(URL, params=params, timeout=15)
        print(f"Status: {resp.status_code}")
        print(f"Raw: {resp.text[:1000]}")
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    test_fss_masking("경현건설")
    test_fss_masking("삼성전자")
