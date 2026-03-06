"""
국민연금공단 - 국민연금 가입 사업장 내역 API 호출 모듈
공공데이터포털 API ID: 3046071 (15083277)
"""
import requests


def fetch_nps_info(business_no: str, service_key: str) -> dict:
    """
    사업자등록번호로 국민연금 가입 사업장 정보 조회

    Args:
        business_no: 하이픈 없는 10자리 문자열
        service_key: 공공데이터포털 서비스키 (Decoding Key)

    Returns:
        dict: API 응답 데이터 (첫 번째 매칭 결과) 또는 빈 dict
    """
    url = "https://api.odcloud.kr/api/15083277/v1/uddi:d7e2de87-da03-4ec4-9741-ef4208ce393c"
    params = {
        "page": 1,
        "perPage": 1,
        "returnType": "JSON",
        "serviceKey": service_key,
        "cond[사업자등록번호::EQ]": business_no,
    }
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get("data"):
            return data["data"][0]
        return {}
    except requests.exceptions.Timeout:
        return {"_error": "API 호출 시간 초과 (15초)"}
    except requests.exceptions.HTTPError as e:
        return {"_error": f"HTTP 오류: {e.response.status_code}"}
    except Exception as e:
        return {"_error": f"조회 실패: {str(e)}"}


# 국민연금 API 반환 필드 매핑 (API 필드명 → 표시명)
NPS_FIELD_MAP = {
    "가입자수": "가입자수",
    "당월고지금액": "당월고지금액",
    "신규취득자수": "신규취득자수",
    "상실가입자수": "상실가입자수",
    "사업장가입상태코드": "사업장가입상태",
    "사업장형태구분": "사업장형태",
    "사업장업종코드명": "업종코드명",
    "자료생성년월": "자료생성년월",
}

# 사용자 선택 가능 항목 목록 (체크박스용)
NPS_SELECTABLE_FIELDS = [
    "가입자수",
    "당월고지금액",
    "신규취득자수",
    "상실가입자수",
    "사업장가입상태코드",
    "사업장형태구분",
    "사업장업종코드명",
    "자료생성년월",
]

NPS_FIELD_LABELS = {
    "가입자수": "가입자수",
    "당월고지금액": "당월고지금액",
    "신규취득자수": "신규취득자수",
    "상실가입자수": "상실가입자수",
    "사업장가입상태코드": "사업장가입상태 (유지/탈퇴)",
    "사업장형태구분": "사업장형태 (법인/개인)",
    "사업장업종코드명": "업종코드명",
    "자료생성년월": "자료생성년월",
}
