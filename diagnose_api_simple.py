import requests
import json

def test_single(name, url, params, headers=None):
    print(f"[{name}]")
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        print(f"Status: {r.status_code}")
        print(f"Body: {r.text[:300]}")
    except Exception as e:
        print(f"Error: {e}")
    print("-" * 30)

if __name__ == "__main__":
    key = "6be75af37c6693a24417c2ed2930e4bd4dd01dddf289552260ce8ce1daf43414"
    
    # 1. NPS
    test_single("NPS", "http://apis.data.go.kr/B552015/NpsBplcInfoInqireServiceV2/getBassInfoSearchV2", 
                {"serviceKey": key, "wkpl_nm": "삼성전자", "pageNo": 1, "numOfRows": 1})
    
    # 2. FSS V2 (With Underscore)
    test_single("FSS_V2_U", "http://apis.data.go.kr/1160100/service/GetCorpBasicInfoService_V2/getCorpOutline",
                {"serviceKey": key, "corpNm": "삼성전자", "resultType": "json"})

    # 2.4 FSS V2 (Full Params, No /service/)
    test_single("FSS_V2_FULL", "http://apis.data.go.kr/1160100/GetCorpBasicInfoService_V2/getCorpOutline",
                {"serviceKey": key, "corpNm": "삼성전자", "pageNo": 1, "numOfRows": 1, "resultType": "json"})

    # 2.5 FSS V2 (Full Params, No /service/, No Underscore)
    test_single("FSS_V2_FULL_NO_U", "http://apis.data.go.kr/1160100/GetCorpBasicInfoServiceV2/getCorpOutline",
                {"serviceKey": key, "corpNm": "삼성전자", "pageNo": 1, "numOfRows": 1, "resultType": "json"})
    
    # 4. NHIS Odcloud
    test_single("NHIS_OD", "https://api.odcloud.kr/api/3049051/v1/uddi:3049051",
                {"serviceKey": key, "page": 1, "perPage": 1})

    # 5. NHIS Odcloud Header
    test_single("NHIS_OD_HDR", "https://api.odcloud.kr/api/3049051/v1/uddi:3049051",
                {"page": 1, "perPage": 1}, headers={"Authorization": f"Infra-Key {key}"})
