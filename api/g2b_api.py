"""
G2B User Info API module
- Query procurement information by BRN
"""
import requests
import xml.etree.ElementTree as ET

# G2B API Endpoints (Updated based on 2025 User Guide)
G2B_BASE_URL = "http://apis.data.go.kr/1230000/ao/UsrInfoService02"
G2B_CORP_INFO_URL   = f"{G2B_BASE_URL}/getPrcrmntCorpBasicInfo02"
G2B_CORP_INDST_URL  = f"{G2B_BASE_URL}/getPrcrmntCorpIndstryInfo02"
G2B_CORP_PRDCT_URL  = f"{G2B_BASE_URL}/getPrcrmntCorpSplyPrdctInfo02"
G2B_UNPT_INFO_URL   = f"{G2B_BASE_URL}/getUnptRsttCorpInfo02"
G2B_INST_INFO_URL   = f"{G2B_BASE_URL}/getDminsttInfo02"

G2B_SELECTABLE_FIELDS = [
    "bizType",
    "telno",
    "corpSizeNm",
    "main_product",
    "restriction",
]

G2B_FIELD_LABELS = {
    "bizType":      "나라장터 등록업종",
    "telno":        "전화번호 📞",
    "corpSizeNm":   "기업구분 (대/중/소/기타)",
    "main_product": "주요공급물품",
    "restriction":  "부정당업자 제재정보",
}

def get_g2b_corp_info(brn: str, service_key: str) -> dict:
    clean_brn = brn.replace("-", "").strip()
    if not clean_brn or len(clean_brn) != 10:
        return {}

    # Query basic corp info
    res = _request_g2b(G2B_CORP_INFO_URL, service_key, {"bizno": clean_brn, "inqryDiv": "3"})
    
    if res:
        parsed = _parse_g2b_item(res)
        
        # Industry info
        indst_res = _request_g2b(G2B_CORP_INDST_URL, service_key, {"bizno": clean_brn, "inqryDiv": "3"})
        if indst_res and "indstryNm" in indst_res:
            parsed["bizType"] = indst_res.get("indstryNm")
            
        # Product info
        prdct_res = _request_g2b(G2B_CORP_PRDCT_URL, service_key, {"bizno": clean_brn, "inqryDiv": "3"})
        if prdct_res and "dtlPrdctClsfNoNm" in prdct_res:
            parsed["main_product"] = prdct_res.get("dtlPrdctClsfNoNm")

        # Unfair supplier info
        unpt_res = _request_g2b(G2B_UNPT_INFO_URL, service_key, {"bizno": clean_brn, "inqryDiv": "1"})
        if unpt_res and "rsttBgnDate" in unpt_res:
            parsed["restriction"] = f"제재중 ({unpt_res.get('rsttBgnDate')} ~ {unpt_res.get('rsttEndDate')})"
        
        return parsed

    # Query institution info if corp info not found
    res = _request_g2b(G2B_INST_INFO_URL, service_key, {"bizno": clean_brn, "inqryDiv": "3"})
    if res: 
        return _parse_g2b_item(res)
    
    return {}

def _request_g2b(url: str, service_key: str, extra_params: dict) -> dict:
    # [v13.5] serviceKey를 URL에 직접 포함하여 double-encoding 방지 (data.go.kr 표준 대응)
    # [v14.1] ServiceKey는 대문자 S로 시작 (가이드북 기준)
    full_url = f"{url}?ServiceKey={service_key}"
    
    params = {
        "type": "json", # [v14.0] dataType -> type로 변경 (가이드북 기준)
        "numOfRows": 10,
        "pageNo": 1
    }
    params.update(extra_params)
    
    try:
        resp = requests.get(full_url, params=params, timeout=15)
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
    return {
        "corp_name": item.get("corpNm", ""),
        "brn": item.get("bizno", ""),
        "ceo_nm": item.get("ceoNm", ""),
        "addr": item.get("adrs", ""),
        "telno": item.get("telNo") or item.get("telno") or "",
        "corpSizeNm": item.get("corpSizeNm") or "",
        "bizType": item.get("indstryNm") or item.get("bizType") or "",  # 업종명
        "source": "G2B_V2"
    }
