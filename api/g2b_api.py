"""
조달청_나라장터 사용자정보 서비스 연동 모듈
- 사업자등록번호로 조달업체 정보(대표자, 업종, 전화번호 등) 조회
"""
import requests
import xml.etree.ElementTree as ET

# ── 나라장터 사용자정보 서비스 (조달청) ──
# 가이드북 기준: UsrInfoService02
G2B_BASE_URL = "http://apis.data.go.kr/1230000/ao/UsrInfoService02"
G2B_CORP_INFO_URL   = f"{G2B_BASE_URL}/getPromntCorpBasInfo02"       # 조달업체 기본정보
G2B_CORP_INDST_URL  = f"{G2B_BASE_URL}/getPromntCorpIndstryInfo02"   # 조달업체 업종정보
G2B_CORP_PRDCT_URL  = f"{G2B_BASE_URL}/getPromntCorpSplyPrdctInfo02"  # 조달업체 공급물품정보
G2B_UNPT_INFO_URL   = f"{G2B_BASE_URL}/getUnptRsttCorpInfo02"       # 부정당업자 제재정보
G2B_INST_INFO_URL   = f"{G2B_BASE_URL}/getDminstInfo02"              # 수요기관 기본정보

# PPS 에러 코드 매핑
G2B_ERROR_CODES = {
    "00": "정상",
    "01": "Application Error (애플리케이션 에러)",
    "03": "No Data (데이터 없음)",
    "10": "Invalid Request Parameter (잘못된 요청 파라미터)",
    "12": "No OpenAPI Service (해당 서비스 없음)",
    "20": "Service Access Denied (서비스 접근 거부)",
    "22": "Limited Number of Requests Exceeded (요청 제한 횟수 초과)",
    "30": "Service Key Not Registered (등록되지 않은 서비스키)"
}

# 사용자 선택 가능 항목 목록 (체크박스용)
G2B_SELECTABLE_FIELDS = [
    "bizType",          # 업종 (indstryNm)
    "telno",            # 전화번호 (telNo)
    "corpSizeNm",       # 기업구분 (대/중/소)
    "main_product",     # 주요공취물품 (dtlPrdctClsfNoNm)
    "restriction",      # 부정당업자 제재정보
]

G2B_FIELD_LABELS = {
    "bizType":      "나라장터 등록업종",
    "telno":        "전화번호 📞",
    "corpSizeNm":   "기업구분 (대/중/소/기타)",
    "main_product": "주요공급물품",
    "restriction":  "부정당업자 제재정보",
}

def get_g2b_corp_info(brn: str, service_key: str) -> dict:
    """
    사업자등록번호(10자리)로 나라장터 정보를 조회
    1) 조달업체 기본정보 조회
    2) 성공 시 업종, 공급물품, 제재정보 추가 조회
    3) 실패 시 수요기관 조회
    """
    clean_brn = brn.replace("-", "").strip()
    if not clean_brn or len(clean_brn) != 10:
        return {}

    # 1. 조달업체 기본정보 조회 (inqryDiv: 3 - 사업자등록번호)
    res = _request_g2b(G2B_CORP_INFO_URL, service_key, {"bizno": clean_brn, "inqryDiv": "3"})
    
    if res:
        # 가이드북 규격 표준화
        parsed = _parse_g2b_item(res)
        
        # 추가 정보 (업종)
        indst_res = _request_g2b(G2B_CORP_INDST_URL, service_key, {"bizno": clean_brn, "inqryDiv": "3"})
        if indst_res and "indstryNm" in indst_res:
            parsed["bizType"] = indst_res.get("indstryNm")
            
        # 추가 정보 (물품 - 첫 번째 품명만)
        prdct_res = _request_g2b(G2B_CORP_PRDCT_URL, service_key, {"bizno": clean_brn, "inqryDiv": "3"})
        if prdct_res and "dtlPrdctClsfNoNm" in prdct_res:
            parsed["main_product"] = prdct_res.get("dtlPrdctClsfNoNm")

        # 추가 정보 (제재정보)
        unpt_res = _request_g2b(G2B_UNPT_INFO_URL, service_key, {"bizno": clean_brn, "inqryDiv": "1"})
        if unpt_res and "rsttBgnDate" in unpt_res:
            parsed["restriction"] = f"제재중 ({unpt_res.get('rsttBgnDate')} ~ {unpt_res.get('rsttEndDate')})"
        
        return parsed

    # 2. 수요기관 조회 (조달업체에 없는 경우)
    res = _request_g2b(G2B_INST_INFO_URL, service_key, {"bizno": clean_brn, "inqryDiv": "3"})
    if res: 
        return _parse_g2b_item(res)
    
    return {}

def _request_g2b(url: str, service_key: str, extra_params: dict) -> dict:
    params = {
        "serviceKey": service_key,
        "type": "json",
        "numOfRows": 10,
        "pageNo": 1
    }
    params.update(extra_params)
    
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            header = data.get("response", {}).get("header", {})
            res_code = header.get("resultCode", "00")
            
            if res_code != "00":
                return {}

            body = data.get("response", {}).get("body", {})
            items = body.get("items", [])
            if items:
                if isinstance(items, dict): items = [items]
                return items[0]
    except:
        pass
    return {}

def _parse_g2b_item(item: dict) -> dict:
    """G2B V2 응답 데이터를 공통 포맷으로 파싱 (get_g2b_corp_info 내부에서 필요한 필드 추출용)"""
    return {
        "corp_name": item.get("corpNm") or item.get("dminstNm") or "",
        "brn": item.get("bizno", ""),
        "ceo_nm": item.get("rprsntvNm", ""),
        "addr": item.get("adres", ""),
        "telno": item.get("telNo") or item.get("telno") or "",
        "corpSizeNm": item.get("corpSizeNm") or "", # 기업구분 (대/중/소 등)
        "source": "G2B_V2"
    }
