"""
금융위원회 기업정보 API 모듈
1. 기업기본정보 (GetCorpBasicInfoService_V2/getCorpOutline)
   - 회사명으로 법인등록번호, 1인평균급여, 종업원수 등 조회
2. 기업재무정보 (GetFinaStatInfoService_V2/getSummFinaStat)
   - 법인등록번호로 매출액, 영업이익, 당기순이익 등 조회

공공데이터포털(data.go.kr) 동일 서비스키 사용 가능
"""
import requests
import re

# ── 기업기본정보 API ──
# 가이드북 기준: GetCorpBasicInfoService_V2 (data.go.kr 서비스명)
CORP_BASIC_URL = "https://apis.data.go.kr/1160100/service/GetCorpBasicInfoService_V2/getCorpOutline_V2"
SUBSIDIARY_URL = "https://apis.data.go.kr/1160100/service/GetCorpBasicInfoService_V2/getConsSubsComp_V2"

# 기업기본정보에서 선택 가능한 항목 (V2 가이드 기준 필드명 업데이트)
FSS_CORP_SELECTABLE_FIELDS = [
    "enpPn1AvgSlryAmt",   # 1인평균급여금액
    "enpEmpeCnt",         # 종업원수
    "enpEstbDt",          # 설립일
    "sicNm",              # 표준산업분류명
    "smenpYn",            # 중소기업여부
    "empeAvgCnwkTermCtt", # 종업원평균근속기간
]

FSS_CORP_FIELD_LABELS = {
    "enpPn1AvgSlryAmt":   "1인평균급여금액",
    "enpEmpeCnt":         "종업원수",
    "enpEstbDt":          "설립일",
    "sicNm":              "표준산업분류명",
    "smenpYn":            "중소기업여부 (Y/N)",
    "empeAvgCnwkTermCtt": "종업원평균근속기간",
}


# ── 기업재무정보 API ──
# ── 기업 재무정보 서비스 (금융위원회) ──
# 가이드북 기준: GetFinaStatInfoService_V2
FINA_BASE_URL = "http://apis.data.go.kr/1160100/service/GetFinaStatInfoService_V2"
FINA_SUMM_URL = f"{FINA_BASE_URL}/getSummFinaStat_V2" # 요약재무제표
FINA_BS_URL   = f"{FINA_BASE_URL}/getBs_V2"           # 재무상태표
FINA_IS_URL   = f"{FINA_BASE_URL}/getIncoStat_V2"     # 손익계산서
# 기존 하위호환용 FINA_STAT_URL (임시 유지)
FINA_STAT_URL = FINA_SUMM_URL

# 기업재무정보에서 선택 가능한 항목
FSS_FINA_SELECTABLE_FIELDS = [
    "enpSaleAmt",     # 매출액
    "enpBzopPft",     # 영업이익
    "enpCrtmNpf",     # 당기순이익
    "enpTastAmt",     # 총자산
    "enpTdbtAmt",     # 총부채
    "enpCptlAmt",     # 자본금
]

FSS_FINA_FIELD_LABELS = {
    "enpSaleAmt":     "매출액",
    "enpBzopPft":     "영업이익",
    "enpCrtmNpf":     "당기순이익",
    "enpTastAmt":     "총자산",
    "enpTdbtAmt":     "총부채",
    "enpCptlAmt":     "자본금",
}


def _normalize_brn(brn: str) -> str:
    """사업자등록번호 정규화 (하이픈/공백 제거, 10자리 zero-fill)"""
    if not brn:
        return ""
    # 마스킹(*) 포함 가능하도록 하이픈과 공백만 제거
    brn_str = str(brn).strip().replace("-", "").replace(" ", "")
    if "." in brn_str:
        brn_str = brn_str.split(".")[0]
        
    if not brn_str or not any(c.isdigit() or c == "*" for c in brn_str):
        return ""
        
    return brn_str.zfill(10)


def search_corp_by_name(company_name: str, service_key: str, brn: str = "", address: str = "", crno: str = "") -> dict:
    """
    기업기본정보 API: 회사명 또는 법인등록번호로 기업 개황 조회
    """
    if not company_name and not crno:
        return {"_error": "회사명 또는 법인등록번호 없음"}

    # 정규화된 검색어 준비
    search_name_clean = company_name.strip().replace("(주)", "").replace("주식회사", "").strip() if company_name else ""
    clean_crno = str(crno).replace("-", "").strip() if crno else ""
    
    params = {
        "serviceKey": service_key,
        "numOfRows": 30,
        "pageNo": 1,
        "resultType": "json",
    }
    
    # 검색 파라미터 구성 (BRN > CRNO > CorpName 순으로 우선순위 부여)
    brn_clean = _normalize_brn(brn)
    if brn_clean and "*" not in brn_clean and len(brn_clean) == 10:
        params["bzno"] = brn_clean
    elif clean_crno and len(clean_crno) == 13:
        params["crno"] = clean_crno
    else:
        params["corpNm"] = search_name_clean or company_name.strip()

    urls = [
        CORP_BASIC_URL,
        CORP_BASIC_URL.replace("/GetCorp", "/service/GetCorp"),
        CORP_BASIC_URL.replace("https://", "http://")
    ]

    last_error = "검색결과 없음"
    for url in urls:
        try:
            resp = requests.get(url, params=params, timeout=12)
            if resp.status_code != 200: continue
            
            data = resp.json()
            body = data.get("response", {}).get("body", {})
            items = body.get("items", {})
            
            item_list = []
            if isinstance(items, dict):
                item_list = items.get("item", [])
            elif isinstance(items, list):
                item_list = items
            
            if not item_list: continue
            # [v12.5] V2 필드 매핑 보완 (가이드북 기준)
            # - enpBsadr(기본주소) + enpDtadr(상세주소) -> enpAddr
            # - enpRprfNm(대표자명) -> ceoNm
            for item in item_list:
                # 주소 병합
                bs_addr = str(item.get("enpBsadr", "")).strip()
                dt_addr = str(item.get("enpDtadr", "")).strip()
                if bs_addr and "enpAddr" not in item:
                    item["enpAddr"] = f"{bs_addr} {dt_addr}".strip()
                
                # 대표자명 매핑
                if "enpRprfNm" in item and "ceoNm" not in item:
                    item["ceoNm"] = item.get("enpRprfNm")
                
                # 가이드북 예제에 bzno(사업자번호), crno(법인번호) 존재 확인

            # 1) CRNO가 제공된 경우 CRNO 일치 확인
            if clean_crno:
                for item in item_list:
                    if str(item.get("crno", "")).replace("-", "") == clean_crno:
                        return item

            # 2) BRN 매칭 (Exact or Fit Match for Masking)
            brn_clean = _normalize_brn(brn)
            if brn_clean:
                is_input_masked = "*" in brn_clean
                for item in item_list:
                    api_brn = _normalize_brn(item.get("bzno", ""))
                    if not api_brn: continue
                    
                    if api_brn == brn_clean:
                        return item
                    
                    if is_input_masked and len(api_brn) == 10 and "*" not in api_brn:
                        match = True
                        for i in range(10):
                            if brn_clean[i] != "*" and brn_clean[i] != api_brn[i]:
                                match = False
                                break
                        if match:
                            return item

            # 3) 이름 및 주소 유사도 매칭
            from difflib import SequenceMatcher
            def _get_sim(a, b):
                if not a or not b: return 0.0
                a1 = str(a).replace(" ", "").lower()
                b1 = str(b).replace(" ", "").lower()
                return SequenceMatcher(None, a1, b1).ratio()

            best_item = None
            max_score = 0.0
            search_name_norm = company_name.replace(" ", "").lower() if company_name else ""

            for item in item_list:
                api_name = str(item.get("corpNm", "")).replace(" ", "").lower()
                api_addr = str(item.get("enpAddr", "")) # 상단에서 병합된 주소 사용
                
                name_sim = _get_sim(search_name_norm, api_name) if search_name_norm else 0.5
                is_name_match = (name_sim >= 0.8) or (search_name_clean.replace(" ","") in api_name) or (api_name in search_name_clean.replace(" ",""))
                
                if is_name_match:
                    addr_sim = _get_sim(address, api_addr) if address else 0.5
                    name_weight = 0.7
                    addr_weight = 0.3
                    score = name_sim * name_weight + addr_sim * addr_weight
                    
                    if name_sim >= 0.95:
                        score = max(score, 0.85)
                    if score > max_score:
                        max_score = score
                        best_item = item

            if best_item and max_score >= 0.5:
                return best_item
            
            last_error = "매칭되는 기업을 찾을 수 없음"
        except Exception as e:
            last_error = f"조회 오류: {str(e)}"
            continue
            
    return {"_error": last_error}


# FSC 재무정보 에러 코드 매핑
FSC_ERROR_CODES = {
    "00": "정상",
    "01": "APPLICATION_ERROR (애플리케이션 에러)",
    "03": "NO_DATA (데이터 없음)",
    "10": "INVALID_REQUEST_PARAMETER_ERROR (잘못된 요청 파라미터)",
    "12": "NO_OPENAPI_SERVICE_ERROR (해당 서비스 없음)",
    "20": "SERVICE_ACCESS_DENIED_ERROR (서비스 접근 거부)",
    "22": "LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR (요청 제한 횟수 초과)",
    "30": "SERVICE_KEY_IS_NOT_REGISTERED_ERROR (등록되지 않은 서비스키)",
    "31": "DEADLINE_HAS_EXPIRED_ERROR (기한 만료된 서비스키)",
    "32": "UNREGISTERED_IP_ERROR (등록되지 않은 IP)",
    "99": "UNKNOWN_ERROR (기타 에러)"
}

def search_financial_by_crno(crno: str, biz_year: str, service_key: str) -> dict:
    """
    기업재무정보 API: 법인등록번호로 요약 재무제표 조회 (연도 fallback 지원)
    가이드북 기준: GetFinaStatInfoService_V2/getSummFinaStat_V2
    """
    if not crno: return {"_error": "법인등록번호 없음"}

    # 정규화: 13자리 숫자만 사용
    clean_crno = str(crno).replace("-", "").strip()
    if len(clean_crno) != 13:
        return {"_error": f"유효하지 않은 법인등록번호: {crno}"}

    years_to_try = [biz_year, str(int(biz_year)-1), str(int(biz_year)-2)]
    
    # 가이드북 권장 URL 우선 사용
    urls = [FINA_SUMM_URL, FINA_STAT_URL]

    last_fsc_msg = "조회결과 없음"
    for year in years_to_try:
        for url in urls:
            params = {
                "serviceKey": service_key,
                "crno": clean_crno,
                "bizYear": year,
                "numOfRows": 10, # 충분히 가져옴
                "resultType": "json",
            }
            try:
                resp = requests.get(url, params=params, timeout=12)
                if resp.status_code != 200: continue
                
                data = resp.json()
                header = data.get("response", {}).get("header", {})
                res_code = header.get("resultCode", "00")
                res_msg = header.get("resultMsg", "")

                if res_code != "00":
                    last_fsc_msg = FSC_ERROR_CODES.get(res_code, res_msg or f"Error {res_code}")
                    continue

                body = data.get("response", {}).get("body", {})
                items = body.get("items", {})
                if not items: continue
                
                item_list = items.get("item", [])
                if not item_list: continue
                
                # 결과 반환 (리스트인 경우 첫 번째 항목 우위)
                if isinstance(item_list, dict): return item_list
                if isinstance(item_list, list) and len(item_list) > 0: return item_list[0]
            except Exception as e:
                last_fsc_msg = f"API 연동 오류: {str(e)}"
                continue
                
    return {"_error": last_fsc_msg}


def validate_crno(crno: str) -> bool:
    """
    법인등록번호(CRNO) 유효성 검사 (13자리 숫자 + 체크섬)
    """
    if not crno:
        return False
    
    clean_crno = str(crno).replace("-", "").strip()
    if not clean_crno.isdigit() or len(clean_crno) != 13:
        return False
    
    # 체크섬 로직 (KOR CRNO)
    # 1*a + 2*b + 1*c + 2*d + ... + 1*l
    # 10 - (sum % 10) == last digit
    try:
        weight = [1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2]
        s = sum(int(clean_crno[i]) * weight[i] for i in range(12))
        remainder = s % 10
        check_digit = (10 - remainder) % 10
        return check_digit == int(clean_crno[12])
    except:
        return False
