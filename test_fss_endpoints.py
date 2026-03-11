import requests

def compare_fss_endpoints():
    service_key = "6be75af37c6693a24417c2ed2930e4bd4dd01dddf289552260ce8ce1daf43414"
    
    # Try different URL patterns for CorpBasicInfo
    urls = [
        "https://apis.data.go.kr/1160100/service/GetCorpBasicInfoService_V2/getCorpOutline",
        "https://apis.data.go.kr/1160100/GetCorpBasicInfoService_V2/getCorpOutline",
        "https://apis.data.go.kr/1160100/service/GetCorpBasicInfoService/getCorpOutline",
        "https://apis.data.go.kr/1160100/GetCorpBasicInfoService/getCorpOutline"
    ]
    
    for url in urls:
        print(f"Testing URL: {url}")
        try:
            r = requests.get(url, params={"serviceKey": service_key, "corpNm": "삼성전자", "resultType": "json"}, timeout=10)
            print(f"Status: {r.status_code}")
            print(f"Content: {r.text[:200]}")
        except Exception as e:
            print(f"Error: {e}")
        print("-" * 20)

if __name__ == "__main__":
    compare_fss_endpoints()
