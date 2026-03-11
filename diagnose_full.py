import requests
import json

def diagnose_full():
    service_key = "6be75af37c6693a24417c2ed2930e4bd4dd01dddf289552260ce8ce1daf43414"
    
    apis = [
        ("NPS (HTTPS)", "https://apis.data.go.kr/B552015/NpsBplcInfoInqireServiceV2/getBassInfoSearchV2", {"serviceKey": service_key, "wkplNm": "삼성전자", "dataType": "json"}),
        ("NHIS (Odcloud)", "https://api.odcloud.kr/api/3049051/v1/uddi:71a6826c-7c86-4b4c-8e90-b61607d40214", {"serviceKey": service_key, "page": 1, "perPage": 1}),
        ("FSS Corp (HTTPS)", "https://apis.data.go.kr/1160100/GetCorpBasicInfoService_V2/getCorpOutline", {"serviceKey": service_key, "corpNm": "LG화학", "resultType": "json"}),
        ("FSS Fina (HTTPS)", "https://apis.data.go.kr/1160100/GetFinaStatInfoService_V2/getSummFinaStat", {"serviceKey": service_key, "crno": "1101111978280", "bizYear": "2023", "resultType": "json"}),
    ]
    
    results = {}
    for name, url, params in apis:
        try:
            r = requests.get(url, params=params, timeout=15)
            results[name] = {
                "status": r.status_code,
                "msg": r.text[:100]
            }
        except Exception as e:
            results[name] = {"error": str(e)}
            
    print(json.dumps(results, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    diagnose_full()
