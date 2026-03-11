import requests

def test_fss_corrected():
    service_key = "6be75af37c6693a24417c2ed2930e4bd4dd01dddf289552260ce8ce1daf43414"
    
    # Try without /service/
    fss_url = "http://apis.data.go.kr/1160100/GetCorpBasicInfoService_V2/getCorpOutline"
    fss_params = {"serviceKey": service_key, "corpNm": "삼성전자", "pageNo": 1, "numOfRows": 1, "resultType": "json"}
    
    print(f"Testing FSS with URL: {fss_url}")
    try:
        r = requests.get(fss_url, params=fss_params, timeout=10)
        print(f"Status: {r.status_code}")
        print(f"Content: {r.text[:500]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_fss_corrected()
