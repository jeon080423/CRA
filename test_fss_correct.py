import requests

key = "6be75af37c6693a24417c2ed2930e4bd4dd01dddf289552260ce8ce1daf43414"

def test_fss_no_service():
    # WITHOUT /service/
    base_url = "apis.data.go.kr/1160100/GetCorpBasicInfoService_V2/getCorpOutline"
    
    variations = [
        ("HTTP + params", f"http://{base_url}", {"serviceKey": key}),
        ("HTTPS + params", f"https://{base_url}", {"serviceKey": key}),
    ]
    
    for name, url, params in variations:
        print(f"--- Testing {name} ---")
        try:
            p = {"corpNm": "삼성전자", "pageNo": 1, "numOfRows": 1, "resultType": "json"}
            p.update(params)
            resp = requests.get(url, params=p, timeout=10)
            print(f"Status: {resp.status_code}")
            print(f"Body: {resp.text[:200]}")
        except Exception as e:
            print(f"Error: {e}")
        print("\n")

if __name__ == "__main__":
    test_fss_no_service()
