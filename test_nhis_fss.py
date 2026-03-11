import requests
import json

def test_nhis_fss():
    service_key = "6be75af37c6693a24417c2ed2930e4bd4dd01dddf289552260ce8ce1daf43414"
    
    print("--- NHIS TEST (Odcloud) ---")
    nhis_url = "https://api.odcloud.kr/api/3049051/v1/uddi:71a6826c-7c86-4b4c-8e90-b61607d40214"
    nhis_params = {"serviceKey": service_key, "page": 1, "perPage": 1, "returnType": "JSON"}
    try:
        r = requests.get(nhis_url, params=nhis_params, timeout=10)
        print(f"Status: {r.status_code}")
        print(f"Content: {r.text[:500]}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n--- FSS TEST (Data.go.kr) ---")
    fss_url = "http://apis.data.go.kr/1160100/service/GetCorpBasicInfoService_V2/getCorpOutline"
    fss_params = {"serviceKey": service_key, "corpNm": "삼성전자", "pageNo": 1, "numOfRows": 1, "resultType": "json"}
    try:
        r = requests.get(fss_url, params=fss_params, timeout=10)
        print(f"Status: {r.status_code}")
        print(f"Content: {r.text[:500]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_nhis_fss()
