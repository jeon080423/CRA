"""
건강보험공단 - 사업장관리 현황 API 호출 모듈
공공데이터포털 파일 데이터 ID: 3049051
"""
import requests


def fetch_nhis_info(business_no: str, service_key: str) -> dict:
    """
    사업자등록번호로 건강보험공단 사업장관리 현황 조회

    Args:
        business_no: 하이픈 없는 10자리 문자열
        service_key: 공공데이터포털 서비스키 (Decoding Key)

    Returns:
        dict: API 응답 데이터 (첫 번째 매칭 결과) 또는 빈 dict
    """
    url = "https://api.odcloud.kr/api/3049051/v1/uddi:3049051"
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


# 건강보험 API 반환 필드 매핑
NHIS_FIELD_MAP = {
    "직장가입자수": "직장가입자수",
    "사업장관리상태": "사업장관리상태",
    "업종코드": "건강보험 업종코드",
}

# 사용자 선택 가능 항목 목록 (체크박스용)
NHIS_SELECTABLE_FIELDS = [
    "직장가입자수",
    "사업장관리상태",
    "업종코드",
]

NHIS_FIELD_LABELS = {
    "직장가입자수": "직장가입자수",
    "사업장관리상태": "사업장관리상태 (정상/말소)",
    "업종코드": "건강보험 업종코드",
}
