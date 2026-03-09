import requests
import json

def test():
    key = "6be75af37c6693a24417c2ed2930e4bd4dd01dddf289552260ce8ce1daf43414"
    url = "http://apis.data.go.kr/B552015/NpsBplcInfoInqireServiceV2/getBassInfoSearchV2"
    params = {
        "serviceKey": key,
        "wkpl_nm": "삼성전자",
        "pageNo": 1,
        "numOfRows": 1,
    }
    print(f"Testing URL: {url}")
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Body: {response.text[:500]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test()
