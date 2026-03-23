import requests
import json
import os
from api.constants import DATA_GO_KR_SERVICE_KEY as SERVICE_KEY

def test_g2b_v2(brn):
    # UsrInfoService02
    base_urls = [
        "https://apis.data.go.kr/1230000/ao/UsrInfoService02",
        "https://apis.data.go.kr/1230000/UsrInfoService02",
        "https://apis.data.go.kr/1230000/MtrlsUserService",
        "https://apis.data.go.kr/1230000/HrcspUserService",
    ]
    
    brn = brn.replace("-", "")
    
    for base_url in base_urls:
        print(f"\n\n>>> Testing Base URL: {base_url} <<<")
        endpoints = {
            "기본정보": f"{base_url}/getPromntCorpBasInfo02",
            "업종정보": f"{base_url}/getPromntCorpIndstryInfo02",
        }
        
        for name, url in endpoints.items():
            print(f"\n--- {name} 조회 ({url}) ---")
            full_url = f"{url}?serviceKey={SERVICE_KEY}"
            params = {
                "bizno": brn,
                "inqryDiv": "3",
                "numOfRows": 1,
                "pageNo": 1
            }
            
            try:
                resp = requests.get(full_url, params=params, timeout=10)
                print(f"Status: {resp.status_code}")
                if resp.status_code == 200:
                    data = resp.json()
                    print(json.dumps(data, indent=2, ensure_ascii=False))
                    if "response" in data: return # Found it!
                else:
                    print(resp.text[:200])
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    # 테스트용 사업자번호 (예: 나비케어 등 또는 흔한 사업자번호)
    # 실제 환경에서 이전에 매칭되었던 번호가 있다면 좋겠지만 없으면 일반적인 것 시도
    test_brn = "1138612939" # 예시 (나비케어 번호가 필요하지만 일단 구조 확인용)
    test_g2b_v2(test_brn)
