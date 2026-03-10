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
CORP_BASIC_URL = "https://apis.data.go.kr/1160100/GetCorpBasicInfoService_V2/getCorpOutline"

# 기업기본정보에서 선택 가능한 항목
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
FINA_STAT_URL = "https://apis.data.go.kr/1160100/GetFinaStatInfoService_V2/getSummFinaStat"

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
    """사업자등록번호 정규화 (하이픈 제거, 10자리 zero-fill)"""
    if not brn:
        return ""
    return re.sub(r"[^0-9]", "", str(brn)).zfill(10)


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
    
    # 법인등록번호가 있으면 이를 우선적으로 검색 파라미터로 시도
    if clean_crno and len(clean_crno) == 13:
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
            if isinstance(item_list, dict): item_list = [item_list]

            # 1) CRNO가 제공된 경우 CRNO 일치 확인 (params에 넣었어도 리스트 중 재검증)
            if clean_crno:
                for item in item_list:
                    if str(item.get("crno", "")).replace("-", "") == clean_crno:
                        return item

            # 2) BRN 매칭
            brn_clean = _normalize_brn(brn)
            if brn_clean and "*" not in brn_clean and len(brn_clean) == 10:
                for item in item_list:
                    if _normalize_brn(item.get("bzno", "")) == brn_clean:
                        return item

            # 3) 이름 및 주소 유사도 매칭 (CRNO가 없을 때만 수행하거나 fallback)
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
                api_addr = str(item.get("enpAddr", ""))
                
                # 이름 유사도 (0.7 이상 or 포함관계)
                name_sim = _get_sim(search_name_norm, api_name) if search_name_norm else 0.5
                is_name_match = (name_sim >= 0.8) or (search_name_clean.replace(" ","") in api_name) or (api_name in search_name_clean.replace(" ",""))
                
                if is_name_match:
                    addr_sim = _get_sim(address, api_addr) if address else 0.5
                    # 가중치 점수
                    score = name_sim * 0.4 + addr_sim * 0.6
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


def search_financial_by_crno(crno: str, biz_year: str, service_key: str) -> dict:
    """
    기업재무정보 API: 법인등록번호로 요약 재무제표 조회 (연도 fallback 지원)
    """
    if not crno: return {"_error": "법인등록번호 없음"}

    years_to_try = [biz_year, str(int(biz_year)-1), str(int(biz_year)-2)]
    
    urls = [
        FINA_STAT_URL,
        FINA_STAT_URL.replace("/GetFina", "/service/GetFina"),
        FINA_STAT_URL.replace("https://", "http://")
    ]

    for year in years_to_try:
        for url in urls:
            params = {
                "serviceKey": service_key,
                "crno": crno,
                "bizYear": year,
                "numOfRows": 1,
                "resultType": "json",
            }
            try:
                resp = requests.get(url, params=params, timeout=12)
                if resp.status_code != 200: continue
                
                data = resp.json()
                items = data.get("response", {}).get("body", {}).get("items", {})
                if not items: continue
                
                item_list = items.get("item", [])
                if not item_list: continue
                if isinstance(item_list, dict): return item_list
                if isinstance(item_list, list) and len(item_list) > 0: return item_list[0]
            except:
                continue
                
    return {"_error": "최근 3개년 재무정보 없음"}


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
