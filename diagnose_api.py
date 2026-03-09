import requests
import streamlit as st
import sys

def test_api(name, url, params, headers=None):
    try:
        print(f"--- Testing {name} ---")
        print(f"URL: {url}")
        print(f"Params: {params}")
        if headers:
            print(f"Headers: {headers}")
            
        response = requests.get(url, params=params, headers=headers, timeout=15)
        print(f"Status Code: {response.status_code}")
        
        # Display response body for debugging
        content = response.text[:500]
        print(f"Response Body (partial): {content}")
        
        if response.status_code == 200:
            if "<returnReasonCode>11</returnReasonCode>" in response.text or "SERVICE_KEY_IS_NOT_REGISTERED" in response.text:
                print("Result: ❌ ERROR - Service Key Not Registered or Expired")
            elif "INVALID_KEY" in response.text:
                print("Result: ❌ ERROR - Invalid Key")
            elif "<item>" in response.text or "<items>" in response.text or "resultCode" in response.text or "totalCount" in response.text:
                 print("Result: ✅ SUCCESS - API is working and returning data.")
            else:
                 print("Result: ⚠️ UNKNOWN - Success status but content looks suspicious.")
        else:
            print(f"Result: ❌ ERROR - HTTP {response.status_code}")
            
    except Exception as e:
        print(f"Result: ❌ CRITICAL ERROR - {str(e)}")
    print("\n")

if __name__ == "__main__":
    # The hex key that worked for NPS
    service_key = "6be75af37c6693a24417c2ed2930e4bd4dd01dddf289552260ce8ce1daf43414"
    print(f"Using test key: {service_key[:10]}...")
    print("WARNING: If approval was done today (2026-03-06), sync might take 1-2 hours.\n")

    # 1. NPS (국민연금) - Already proven working
    test_api("국민연금 (NPS) V2", "http://apis.data.go.kr/B552015/NpsBplcInfoInqireServiceV2/getBassInfoSearchV2", 
             {"serviceKey": service_key, "wkplNm": "삼성전자", "pageNo": 1, "numOfRows": 1, "dataType": "json"})
    
    # 2. FSS (금융위) variations
    # V2 HTTP
    test_api("금융위 (FSS) Basic V2 HTTP", "http://apis.data.go.kr/1160100/service/GetCorpBasicInfoService_V2/getCorpOutline",
             {"serviceKey": service_key, "corpNm": "삼성전자", "pageNo": 1, "numOfRows": 1, "resultType": "json"})
    
    # V2 HTTPS
    test_api("금융위 (FSS) Basic V2 HTTPS", "https://apis.data.go.kr/1160100/service/GetCorpBasicInfoService_V2/getCorpOutline",
             {"serviceKey": service_key, "corpNm": "삼성전자", "pageNo": 1, "numOfRows": 1, "resultType": "json"})

    # V1 HTTP
    test_api("금융위 (FSS) Basic V1 HTTP", "http://apis.data.go.kr/1160100/service/GetCorpBasicInfoService/getCorpOutline",
             {"serviceKey": service_key, "corpNm": "삼성전자", "pageNo": 1, "numOfRows": 1, "resultType": "json"})

    # 3. NHIS (건강보험) variations
    # Odcloud Standard
    test_api("건강보험 (NHIS) Odcloud Standard", "https://api.odcloud.kr/api/3049051/v1/uddi:3049051",
             {"serviceKey": service_key, "page": 1, "perPage": 1})
    
    # Odcloud with Authorization Header
    test_api("건강보험 (NHIS) Odcloud with Header", "https://api.odcloud.kr/api/3049051/v1/uddi:3049051",
             {"page": 1, "perPage": 1}, 
             headers={"Authorization": f"Infra-Key {service_key}"})
    
    # Data.go.kr Proxy (if exists)
    test_api("건강보험 (NHIS) Data.go.kr Proxy", "http://apis.data.go.kr/B550928/bizInfoService/getBizInfo",
             {"serviceKey": service_key, "wkplNm": "삼성전자", "pageNo": 1, "numOfRows": 1})
