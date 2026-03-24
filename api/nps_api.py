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


def search_and_match_nps(company_name, brn, service_key, address="", input_sido=""):
    """
    NPS 사업장 정보를 검색하고 최적의 결과를 반환합니다.
    [v14.7] LG/엘지 교차 검색 및 상위 후보 상세조회 기반 랭킹 적용
    """
    brn_clean = brn.replace("-", "") if brn else ""
    brn_6 = brn_clean[:6] if len(brn_clean) >= 6 else ""

    try:
        # 1. 검색어 정규화 및 교차 검색 생성 (LG <-> 엘지)
        search_names = [company_name.strip() if company_name else ""]
        if company_name:
            if "LG" in company_name.upper():
                search_names.append(company_name.upper().replace("LG", "엘지"))
            elif "엘지" in company_name:
                search_names.append(company_name.replace("엘지", "LG"))

        all_raw_results = []
        for s_name in search_names:
            if not s_name and not brn_6: continue
            
            # (1) 이름 + 사업자번호 앞6자리
            raw_results = search_nps_by_name(s_name, service_key, brn_6)
            all_raw_results.extend(raw_results)
            
            # (2) 결과가 부족하면 이름만으로 다시 검색
            if not raw_results or len(raw_results) < 3:
                raw_results_name_only = search_nps_by_name(s_name, service_key)
                all_raw_results.extend(raw_results_name_only)
        
        # 2. 중복 제거
        unique_results = []
        seen_seq = set()
        for item in all_raw_results:
            seq = item.get("seq")
            if seq and seq not in seen_seq:
                unique_results.append(item)
                seen_seq.add(seq)
        
        # 3. 상위 후보들에 대해 상세 정보를 조회하여 최적의 매치 선정
        # [v14.9] 모든 검색 결과를 이름 유사도 순으로 정렬하여 상격 높은 후보부터 상세 조회
        from difflib import SequenceMatcher
        def _get_similarity(a, b):
            a_norm = str(a or "").replace(" ", "").upper()
            b_norm = str(b or "").replace(" ", "").upper()
            for w in ["(주)", "㈜", "주식회사"]:
                a_norm = a_norm.replace(w, "")
                b_norm = b_norm.replace(w, "")
            return SequenceMatcher(None, a_norm, b_norm).ratio()

        unique_results.sort(key=lambda x: _get_similarity(company_name, x.get("wkplNm")), reverse=True)

        best_item = None
        max_score = -1
        
        # 상위 30개 후보 조사 (본사 탐색 성공률 극대화)
        for item in unique_results[:30]:
            detail = get_nps_detail(item.get("seq"), service_key)
            if detail:
                item.update(detail)
                cnt = int(detail.get("jnngpCnt", 0) or 0)
                # 본사(wkplStlDvCd='1')인 경우 가중치 부여
                is_main = 1 if str(detail.get("wkplStlDvCd", "")) == "1" else 0
                sim = _get_similarity(company_name, detail.get("wkplNm"))
                
                # [v15.0] 시도 일치 여부 확인 (있을 경우 가중치)
                api_addr = detail.get("wkplRoadNmAddr") or detail.get("wkplRoadNmDtlAddr") or ""
                sido_match = 1 if input_sido and input_sido[:2] in api_addr else 0
                
                # 점수계산: (유사도 가중치) + (본사 여부) + (시도 일치) + (인원수 가중치)
                # [v14.9.1] 인원수가 100명 이상인 경우 매우 강한 가중치 부여 (대기업 본사 우선)
                cnt_weight = cnt * 100 if cnt > 100 else cnt
                score = (sim * 100000) + (is_main * 50000) + (sido_match * 30000) + cnt_weight
                
                if score > max_score:
                    max_score = score
                    best_item = item
        
        return best_item if best_item else (unique_results[0] if unique_results else {})

    except Exception as e:
        return {"_error": f"검색 오류: {str(e)}"}


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
