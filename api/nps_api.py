"""
국민연금공단 - 국민연금 가입 사업장 내역 API (V2)
공공데이터포털 서비스 ID: 15083277
엔드포인트: apis.data.go.kr/B552015/NpsBplcInfoInqireServiceV2

V2 API는 사업장명을 기반으로 검색하는 REST API입니다.
사업자등록번호 직접 검색은 지원되지 않으므로, 사업장명으로 검색 후
사업자등록번호로 매칭합니다.
"""
import requests


# V2 API 엔드포인트
BASE_URL = "https://apis.data.go.kr/B552015/NpsBplcInfoInqireServiceV2"
SEARCH_URL = f"{BASE_URL}/getBassInfoSearchV2"
DETAIL_URL = f"{BASE_URL}/getDetailInfoSearchV2"
PERIOD_URL = f"{BASE_URL}/getPdAcctoSttusInfoSearchV2" # 기간별 현황 조회

# NPS API 에러 코드 매핑
NPS_ERROR_CODES = {
    "00": "정상 (NORMAL_CODE)",
    "10": "INVALID_REQUEST_PARAMETER_ERROR (잘못된 요청 파라미터)",
    "20": "NO_OPENAPI_SERVICE_ERROR (해당 서비스 없음)",
    "22": "LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR (요청 제한 횟수 초과)",
    "30": "SERVICE_KEY_IS_NOT_REGISTERED_ERROR (등록되지 않은 서비스키)",
    "31": "DEADLINE_HAS_EXPIRED_ERROR (기한 만료된 서비스키)",
    "32": "UNREGISTERED_IP_ERROR (등록되지 않은 IP)",
    "99": "UNKNOWN_ERROR (기타 에러)"
}

# 사용자 선택 가능 항목 목록 (V2 가이드 기준 확장)
NPS_SELECTABLE_FIELDS = [
    "jnngpCnt",       # 가입자수
    "crrmmNtcAmt",    # 당월고지금액
    "avgBasSalary",   # 추정 평균 기준소득월액 (계산 필드)
    "nwAcqzrCnt",     # 신규취득자수
    "lssJnngpCnt",    # 상실가입자수
    "bzowrRgstNo",    # 사업자등록번호 (앞6자리)
    "wkplJnngStcd",   # 사업장가입상태코드 (1:등록, 2:탈퇴)
    "wkplStlDvCd",    # 사업장형태구분 (1:법인, 2:개인)
    "wkplRoadNmDtlAddr", # 사업장도로명상세주소
    "wkplIntpCd",     # 사업장업종코드
    "vldtVlKrnNm",    # 사업장업종코드명
    "adptDt",         # 사업장등록일
    "scsnDt",         # 사업장탈퇴일
]

NPS_FIELD_LABELS = {
    "jnngpCnt": "가입자수",
    "crrmmNtcAmt": "당월고지금액",
    "avgBasSalary": "추정 평균 기준소득월액",
    "nwAcqzrCnt": "신규취득자수",
    "lssJnngpCnt": "상실가입자수",
    "bzowrRgstNo": "사업자등록번호(6자리)",
    "wkplJnngStcd": "사업장가입상태 (1:등록/2:탈퇴)",
    "wkplStlDvCd": "사업장형태 (1:법인/2:개인)",
    "wkplRoadNmDtlAddr": "도로명주소",
    "wkplIntpCd": "업종코드",
    "vldtVlKrnNm": "업종명",
    "adptDt": "등록일(가입일)",
    "scsnDt": "탈퇴일(상실일)",
}


def search_nps_by_name(company_name: str, service_key: str, brn_6: str = "") -> list:
    """
    사업장명 또는 사업자번호(앞6자리)로 국민연금 가입 사업장을 검색 (V2 API)
    가이드북 기준: wkplNm과 bzowrRgstNo(앞6자리) 중 하나만 입력해도 됨
    """
    params = {
        "serviceKey": service_key,
        "pageNo": 1,
        "numOfRows": 100,
        "dataType": "json",
    }
    if company_name:
        params["wkplNm"] = company_name
    if brn_6 and len(brn_6) >= 6:
        params["bzowrRgstNo"] = brn_6[:6]

    if not params.get("wkplNm") and not params.get("bzowrRgstNo"):
        return []

    try:
        resp = requests.get(SEARCH_URL, params=params, timeout=15)
        if resp.status_code != 200: return []

        data = resp.json()
        header = data.get("response", {}).get("header", {})
        res_code = header.get("resultCode", "00")
        if res_code != "00":
            return []

        body = data.get("response", {}).get("body", {})
        items = body.get("items", {})

        item_list = []
        if isinstance(items, dict):
            item_list = items.get("item", [])
        elif isinstance(items, list):
            item_list = items
            
        if isinstance(item_list, dict):
            item_list = [item_list]

        return item_list

    except Exception:
        return []


def get_nps_detail(seq: str, service_key: str) -> dict:
    """
    순번(seq)을 기반으로 상세 정보를 조회 (V2)
    """
    if not seq:
        return {}
    params = {
        "serviceKey": service_key,
        "seq": seq,
        "dataType": "json",
    }
    try:
        resp = requests.get(DETAIL_URL, params=params, timeout=10)
        if resp.status_code != 200: return {}
        
        data = resp.json()
        header = data.get("response", {}).get("header", {})
        if header.get("resultCode") != "00":
            return {}

        items = data.get("response", {}).get("body", {}).get("items", {})
        item = items.get("item")
        
        if isinstance(item, list) and item:
            return item[0]
        return item if isinstance(item, dict) else {}
    except Exception:
        return {}


def get_nps_period_status(seq: str, period: str, service_key: str) -> dict:
    """
    기간별 현황 정보 조회 (V2)
    period: YYYYMM 형식
    """
    if not seq or not period:
        return {}
    params = {
        "serviceKey": service_key,
        "seq": seq,
        "dataCrtym": period,
        "dataType": "json",
    }
    try:
        resp = requests.get(PERIOD_URL, params=params, timeout=10)
        if resp.status_code != 200: return {}
        
        data = resp.json()
        items = data.get("response", {}).get("body", {}).get("items", {})
        item = items.get("item")
        
        if isinstance(item, list) and item:
            return item[0]
        return item if isinstance(item, dict) else {}
    except Exception:
        return {}


def search_and_match_nps(
    company_name: str,
    brn: str,
    service_key: str,
    address: str = "",
    input_sido: str = "",
) -> dict:
    """
    사업장명 및 사업자번호(앞6자리)로 검색 후 정밀 매칭 (시도 검증 포함)
    """
    if not company_name and not brn:
        return {"_error": "회사명 또는 사업자번호 부족"}

    brn_clean = str(brn).replace("-", "").strip()
    brn_6 = brn_clean[:6] if len(brn_clean) >= 6 else ""

    try:
        # 6자리 번호와 회사명으로 시너지 검색
        results = search_nps_by_name(company_name.strip() if company_name else "", service_key, brn_6)
    except Exception as e:
        return {"_error": f"검색 오류: {str(e)}"}

    if not results:
        return {"_error": "검색결과 없음"}

    # 1) 사업자등록번호로 매칭 시도 (마스킹 포함)
    target_brn_norm = brn_clean.zfill(10) if brn_clean else ""
    for item in results:
        api_brn = str(item.get("bzowrRgstNo", "")).replace("-", "").replace(" ", "").zfill(10)
        
        # 완전 일치 또는 마스킹 일치 확인
        match = False
        if target_brn_norm and api_brn == target_brn_norm:
            match = True
        elif target_brn_norm and "*" in api_brn and len(api_brn) == 10:
            match = True
            for i in range(10):
                if api_brn[i] != "*" and api_brn[i] != target_brn_norm[i]:
                    match = False
                    break
        
        if match:
            detail = get_nps_detail(item.get("seq"), service_key)
            if detail: item.update(detail)
            return item

    # 2) 상호명 및 주소 유사도 기반 매칭
    from difflib import SequenceMatcher
    def _get_sim(a, b):
        if not a or not b: return 0.0
        a_norm = str(a).replace(" ", "").lower()
        b_norm = str(b).replace(" ", "").lower()
        return SequenceMatcher(None, a_norm, b_norm).ratio()

    search_name_norm = company_name.strip().replace(" ", "").lower() if company_name else ""
    best_item = None
    max_score = 0.0

    for item in results:
        api_name = str(item.get("wkplNm", "")).strip().replace(" ", "").lower()
        api_addr = item.get("wkplRoadNmDtlAddr", "") or item.get("wkplNmAdrs", "")
        
        name_sim = _get_sim(search_name_norm, api_name) if search_name_norm else 0.5
        addr_sim = _get_sim(address, api_addr) if address else 0.5
        
        # ── [v12.7] 시도(Sido) 검증 로직 추가 ──────────────────────
        sido_match = True
        if input_sido and api_addr:
            # 주소에서 첫 단어(시도) 추출
            api_sido = api_addr.split()[0][:2] # '서울', '경기' 등 2글자만 비교
            user_sido = input_sido[:2]
            if api_sido != user_sido:
                sido_match = False

        # 이름 일치 시 가중치 부여
        score = name_sim * 0.7 + addr_sim * 0.3
        
        # 시도가 다른 경우 강력한 페널티 (매칭 제외 수준)
        if not sido_match:
            score *= 0.5
        
        if score > max_score:
            max_score = score
            best_item = item

    # 최종 점수 기반 결과 반환
    # (사업자번호 10자리 완전 일치는 위에서 이미 리턴됨)
    if best_item and max_score >= 0.6:
        detail = get_nps_detail(best_item.get("seq"), service_key)
        if detail: best_item.update(detail)
        best_item["_match_score"] = round(max_score, 2)
        return best_item

    return {"_error": f"검색결과 {len(results)}건 중 신뢰할 수 있는 매칭 실패 (최고유사도: {max_score:.2f})", "_candidates": len(results)}


def estimate_avg_salary(nps_data: dict) -> str:
    """
    국민연금 데이터에서 추정 평균 기준소득월액 계산
    공식: 당월고지금액(crrmmNtcAmt) ÷ 연금보험료율(0.09) ÷ 가입자수(jnngpCnt)
    """
    if not nps_data or "_error" in nps_data:
        return "조회불가"

    try:
        ntc_amt = float(nps_data.get("crrmmNtcAmt", 0))
        jnngp_cnt = int(nps_data.get("jnngpCnt", 0))

        if jnngp_cnt <= 0 or ntc_amt <= 0:
            return "산출불가"

        # 국민연금 보험료율: 9%
        avg_salary = ntc_amt / 0.09 / jnngp_cnt
        return f"{int(round(avg_salary)):,}원"
    except (ValueError, TypeError, ZeroDivisionError):
        return "산출불가"
