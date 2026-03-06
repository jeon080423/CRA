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
BASE_URL = "http://apis.data.go.kr/B552015/NpsBplcInfoInqireServiceV2"
SEARCH_URL = f"{BASE_URL}/getBassInfoSearchV2"
DETAIL_URL = f"{BASE_URL}/getDetailInfoSearchV2"

# 사용자 선택 가능 항목 목록 (체크박스용)
NPS_SELECTABLE_FIELDS = [
    "jnngpCnt",       # 가입자수
    "crrmmNtcAmt",    # 당월고지금액
    "avgBasSalary",   # 추정 평균 기준소득월액 (계산 필드)
    "nwAcqzrCnt",     # 신규취득자수
    "lssJnngpCnt",    # 상실가입자수
    "bzowrRgstNo",    # 사업자등록번호
    "wkplJnngStCd",   # 사업장가입상태코드 (1:등록, 2:탈퇴)
    "wkplStylDvCd",   # 사업장형태구분 (1:법인, 2:개인)
    "ldongAddrMgpDgCd",  # 사업장주소
]

NPS_FIELD_LABELS = {
    "jnngpCnt": "가입자수",
    "crrmmNtcAmt": "당월고지금액",
    "avgBasSalary": "추정 평균 기준소득월액",
    "nwAcqzrCnt": "신규취득자수",
    "lssJnngpCnt": "상실가입자수",
    "bzowrRgstNo": "사업자등록번호",
    "wkplJnngStCd": "사업장가입상태 (1:등록/2:탈퇴)",
    "wkplStylDvCd": "사업장형태 (1:법인/2:개인)",
    "ldongAddrMgpDgCd": "법정동주소 관리지역코드",
}

NPS_FIELD_MAP = {
    "wkplNm": "사업장명",
    "bzowrRgstNo": "사업자등록번호",
}


def search_nps_by_name(company_name: str, service_key: str) -> list:
    """
    사업장명으로 국민연금 가입 사업장을 검색 (V2 API)

    Args:
        company_name: 검색할 사업장명
        service_key: 공공데이터포털 서비스키

    Returns:
        list: 검색 결과 목록 (dict의 리스트)
    """
    params = {
        "serviceKey": service_key,
        "wkpl_nm": company_name,
        "pageNo": 1,
        "numOfRows": 100,
        "type": "json",
    }
    try:
        resp = requests.get(SEARCH_URL, params=params, timeout=15)
        resp.raise_for_status()

        data = resp.json()

        # API 응답 구조 파싱
        body = data.get("response", {}).get("body", {})
        items = body.get("items", {})

        if isinstance(items, dict):
            item_list = items.get("item", [])
        elif isinstance(items, list):
            item_list = items
        else:
            return []

        if isinstance(item_list, dict):
            item_list = [item_list]

        return item_list

    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else 0
        if status in (401, 403):
            raise PermissionError(f"API 키 인증 실패 (HTTP {status})")
        return []
    except Exception:
        return []


def search_and_match_nps(
    company_name: str,
    brn: str,
    service_key: str,
) -> dict:
    """
    사업장명으로 검색 후 사업자등록번호로 매칭

    Args:
        company_name: 검색할 사업장명 (정제된 이름 권장)
        brn: 사업자등록번호 (정규화된 10자리)
        service_key: API 서비스 키

    Returns:
        dict: 매칭된 사업장 정보, 없으면 {"_error": "..."} 반환
    """
    if not company_name or not company_name.strip():
        return {"_error": "회사명 없음"}

    try:
        results = search_nps_by_name(company_name.strip(), service_key)
    except PermissionError:
        raise  # 인증 오류는 상위로 전파

    if not results:
        return {"_error": "검색결과 없음"}

    # 사업자등록번호로 매칭 시도
    brn_clean = brn.replace("-", "").replace(" ", "").zfill(10) if brn else ""
    for item in results:
        item_brn = str(item.get("bzowrRgstNo", "")).replace("-", "").replace(" ", "").zfill(10)
        if item_brn == brn_clean:
            return item

    # 정확한 매칭이 안 되면 첫 번째 결과라도 반환 (유사도로 판별)
    if len(results) == 1:
        return results[0]

    # 여러 결과 중 매칭 실패
    return {"_error": f"검색결과 {len(results)}건 중 사업자번호 매칭 실패", "_candidates": len(results)}


def estimate_avg_salary(nps_data: dict) -> str:
    """
    국민연금 데이터에서 추정 평균 기준소득월액 계산

    공식: 당월고지금액(crrmmNtcAmt) ÷ 연금보험료율(0.09) ÷ 가입자수(jnngpCnt)

    Args:
        nps_data: NPS API 검색 결과 dict

    Returns:
        str: 추정 평균 기준소득월액 (원) 또는 "산출불가"
    """
    if not nps_data or "_error" in nps_data:
        return "조회불가"

    try:
        ntc_amt = float(nps_data.get("crrmmNtcAmt", 0))
        jnngp_cnt = int(nps_data.get("jnngpCnt", 0))

        if jnngp_cnt <= 0 or ntc_amt <= 0:
            return "산출불가"

        # 국민연금 보험료율: 9% (사업주 4.5% + 근로자 4.5%)
        avg_salary = ntc_amt / 0.09 / jnngp_cnt
        return f"{int(round(avg_salary)):,}원"
    except (ValueError, TypeError, ZeroDivisionError):
        return "산출불가"
