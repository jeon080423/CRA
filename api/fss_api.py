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


def search_corp_by_name(company_name: str, service_key: str, brn: str = "", address: str = "") -> dict:
    """
    기업기본정보 API: 회사명으로 기업 개황 조회

    Args:
        company_name: 검색할 회사명
        service_key: 공공데이터포털 서비스키
        brn: 사업자등록번호 (매칭 검증용, 선택)

    Returns:
        dict: 매칭된 기업 정보. 실패 시 {"_error": "..."} 반환
    """
    if not company_name or not company_name.strip():
        return {"_error": "회사명 없음"}

    params = {
        "serviceKey": service_key,
        "corpNm": company_name.strip(),
        "numOfRows": 20,
        "pageNo": 1,
        "resultType": "json",
    }

    try:
        resp = requests.get(CORP_BASIC_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        # 응답 구조 파싱
        body = data.get("response", {}).get("body", {})
        items = body.get("items", {})

        if isinstance(items, dict):
            item_list = items.get("item", [])
        elif isinstance(items, list):
            item_list = items
        else:
            return {"_error": "검색결과 없음"}

        if isinstance(item_list, dict):
            item_list = [item_list]

        if not item_list:
            return {"_error": "검색결과 없음"}

        # 2) 사업자등록번호로 매칭 시도 (마스킹되지 않은 10자리인 경우만)
        brn_clean = _normalize_brn(brn) if brn else ""
        if brn_clean and "*" not in brn_clean and len(brn_clean) == 10:
            for item in item_list:
                item_brn = _normalize_brn(item.get("bzno", ""))
                if item_brn == brn_clean:
                    return item

        # 3) 상호명 및 주소 유사도 기반 정밀 매칭 (BRN 매칭 실패 혹은 마스킹된 경우)
        from difflib import SequenceMatcher
        def _get_sim(a, b):
            if not a or not b: return 0.0
            a_norm = str(a).replace(" ", "").lower()
            b_norm = str(b).replace(" ", "").lower()
            return SequenceMatcher(None, a_norm, b_norm).ratio()

        search_name_norm = company_name.strip().replace(" ", "").lower()
        best_item = None
        max_addr_sim = 0.0

        for item in item_list:
            api_name = str(item.get("corpNm", "")).strip().replace(" ", "").lower()
            api_addr = item.get("enpAddr", "")
            
            # 상호명이 포함되거나 일치하는 경우
            if search_name_norm in api_name or api_name in search_name_norm:
                sim = _get_sim(address, api_addr) if address else 0.5
                if sim > max_addr_sim:
                    max_addr_sim = sim
                    best_item = item
        
        # 신뢰도 조건 체크 (유사도 0.6 이상)
        if best_item and (max_addr_sim >= 0.6 or (not address and len(item_list) == 1)):
            return best_item

        return {"_error": "신뢰할 수 있는 매칭 기업 없음 (상호/주소 불일치)"}

        # 첫 번째 결과 반환 (단일 결과인 경우)
        if len(item_list) == 1:
            return item_list[0]

        # 여러 결과 중 매칭 실패
        return {"_error": f"검색결과 {len(item_list)}건 중 매칭 실패 (주소 불일치)"}

    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else 0
        if status in (401, 403):
            raise PermissionError(f"API 키 인증 실패 (HTTP {status})")
        return {"_error": f"HTTP 오류 ({status})"}
    except Exception as e:
        return {"_error": f"조회 실패: {str(e)[:50]}"}


def search_financial_by_crno(crno: str, biz_year: str, service_key: str) -> dict:
    """
    기업재무정보 API: 법인등록번호로 요약 재무제표 조회

    Args:
        crno: 법인등록번호 (13자리)
        biz_year: 사업연도 (예: "2024")
        service_key: 공공데이터포털 서비스키

    Returns:
        dict: 재무 데이터. 실패 시 {"_error": "..."} 반환
    """
    if not crno:
        return {"_error": "법인등록번호 없음"}

    params = {
        "serviceKey": service_key,
        "crno": crno,
        "bizYear": biz_year,
        "numOfRows": 1,
        "pageNo": 1,
        "resultType": "json",
    }

    try:
        resp = requests.get(FINA_STAT_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        body = data.get("response", {}).get("body", {})
        items = body.get("items", {})

        if isinstance(items, dict):
            item_list = items.get("item", [])
        elif isinstance(items, list):
            item_list = items
        else:
            return {"_error": "재무정보 없음"}

        if isinstance(item_list, dict):
            item_list = [item_list]

        if not item_list:
            return {"_error": "재무정보 없음"}

        return item_list[0]

    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else 0
        if status in (401, 403):
            raise PermissionError(f"API 키 인증 실패 (HTTP {status})")
        return {"_error": f"HTTP 오류 ({status})"}
    except Exception as e:
        return {"_error": f"재무정보 조회 실패: {str(e)[:50]}"}


