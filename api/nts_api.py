import requests
import json

# 국세청_사업자등록정보 진위확인 및 상태조회 서비스 (ODCloud/공공데이터포털)
# https://www.data.go.kr/data/15081808/openapi.do

NTS_STATUS_URL = "https://api.odcloud.kr/api/nts-businessman/v1/status"

def get_nts_business_status(brn_list, api_key):
    """
    사업자등록번호 목록으로 현재 상태(계속, 휴업, 폐업) 및 과세유형 조회
    
    Args:
        brn_list (list): 사업자등록번호 리스트 (최대 100개)
        api_key (str): 공공데이터포털 서비스키
        
    Returns:
        dict: {brn: {status_code, status_msg, tax_type, ...}}
    """
    if not brn_list:
        return {}
        
    # 하이픈 제거 및 중복 제거
    clean_brns = list(set([str(b).replace("-", "").replace(" ", "") for b in brn_list if b]))
    if not clean_brns:
        return {}

    # 최대 100개씩 분할 처리 (API 제한)
    results = {}
    for i in range(0, len(clean_brns), 100):
        batch = clean_brns[i:i+100]
        params = {"serviceKey": api_key}
        payload = {"b_no": batch}
        
        try:
            resp = requests.post(
                NTS_STATUS_URL, 
                params=params, 
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'},
                timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            
            # 응답 데이터 파싱
            # data structure: {"status_code": "OK", "request_cnt": 1, "match_cnt": 1, "data": [{"b_no": "...", "b_stt": "...", "b_stt_cd": "...", "tax_type": "...", ...}]}
            if data.get("status_code") == "OK" and "data" in data:
                for item in data["data"]:
                    b_no = item.get("b_no")
                    if b_no:
                        results[b_no] = {
                            "status": item.get("b_stt", "조회실패"),      # 사업자상태 (계속사업자, 폐업사업자 등)
                            "status_cd": item.get("b_stt_cd", ""),    # 상태코드 (01: 계속, 02: 휴업, 03: 폐업)
                            "tax_type": item.get("tax_type", ""),     # 과세유형 (일반과세자, 간이과세자 등)
                            "end_dt": item.get("end_dt", ""),          # 폐업일 (YYYYMMDD)
                            "utcc_yn": item.get("utcc_yn", ""),        # 단위과세여부
                            "tax_type_cd": item.get("tax_type_cd", "") # 과세유형코드
                        }
        except Exception as e:
            print(f"NTS API Proxy Error (Batch {i}): {e}")
            
    return results
