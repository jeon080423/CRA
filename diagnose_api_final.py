import requests
import json

def test_api(name, url, params, headers=None):
    try:
        print(f"--- Testing {name} ---")
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        print(f"Body: {resp.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")
    print("\n")

if __name__ == "__main__":
    key = "6be75af37c6693a24417c2ed2930e4bd4dd01dddf289552260ce8ce1daf43414"
    
    # NPS
    test_api("NPS", "http://apis.data.go.kr/B552015/NpsBplcInfoInqireServiceV2/getBassInfoSearchV2", 
             {"serviceKey": key, "wkpl_nm": "전국", "pageNo": 1, "numOfRows": 1, "type": "json"})

    # FSS V2 (With /service/)
    test_api("FSS V2 (/service/)", "http://apis.data.go.kr/1160100/service/GetCorpBasicInfoService_V2/getCorpOutline",
             {"serviceKey": key, "corpNm": "삼성전자", "numOfRows": 1, "resultType": "json"})

    # FSS V2 (Without /service/)
    test_api("FSS V2 (No /service/)", "http://apis.data.go.kr/1160100/GetCorpBasicInfoService_V2/getCorpOutline",
             {"serviceKey": key, "corpNm": "삼성전자", "numOfRows": 1, "resultType": "json"})

    # NHIS
    test_api("NHIS (Param)", "https://api.odcloud.kr/api/3049051/v1/uddi:3049051",
             {"serviceKey": key, "page": 1, "perPage": 1})

    test_api("NHIS (Header)", "https://api.odcloud.kr/api/3049051/v1/uddi:3049051",
             {"page": 1, "perPage": 1}, headers={"Authorization": f"Infra-Key {key}"})
