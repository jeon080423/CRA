"""
국민연금공단 - 국민연금 가입 사업장 내역 API 호출 모듈
공공데이터포털 API ID: 3046071 (15083277)

전체 데이터셋 일괄 다운로드 → 로컬 매칭 방식
"""
import requests
import pandas as pd


API_URL = "https://api.odcloud.kr/api/15083277/v1/uddi:d7e2de87-da03-4ec4-9741-ef4208ce393c"

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

NPS_FIELD_MAP = {
    "사업장명": "사업장명",
    "사업자등록번호": "사업자등록번호",
    "사업장도로명상세주소": "사업장도로명상세주소",
}


def fetch_nps_total_count(service_key: str) -> int:
    """전체 데이터 건수 조회"""
    params = {
        "page": 1,
        "perPage": 1,
        "returnType": "JSON",
        "serviceKey": service_key,
    }
    try:
        resp = requests.get(API_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("totalCount", 0)
    except Exception:
        return 0


def download_nps_dataset(service_key: str, progress_callback=None) -> pd.DataFrame:
    """
    국민연금 가입 사업장 전체 데이터를 페이지네이션으로 다운로드

    Args:
        service_key: 공공데이터포털 서비스키
        progress_callback: fn(current_page, total_pages, status_msg) 콜백

    Returns:
        pd.DataFrame: 전체 사업장 데이터 (사업자등록번호 정규화 포함)
    """
    PER_PAGE = 1000
    all_records = []

    # 먼저 전체 건수 확인
    total_count = fetch_nps_total_count(service_key)
    if total_count == 0:
        return pd.DataFrame()

    total_pages = (total_count + PER_PAGE - 1) // PER_PAGE

    for page in range(1, total_pages + 1):
        params = {
            "page": page,
            "perPage": PER_PAGE,
            "returnType": "JSON",
            "serviceKey": service_key,
        }
        try:
            resp = requests.get(API_URL, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            # 인증 오류 체크
            if isinstance(data, dict) and data.get("result", {}).get("code") in ["INVALID_KEY", "LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR"]:
                error_msg = data.get("result", {}).get("message", "API 인증 오류")
                raise PermissionError(f"API 인증 실패: {error_msg}")

            records = data.get("data", [])
            if not records:
                break
            all_records.extend(records)

            if progress_callback:
                progress_callback(page, total_pages, f"국민연금 데이터 다운로드 중... ({page}/{total_pages}페이지, {len(all_records):,}건)")

        except PermissionError:
            raise  # 인증 오류는 상위로 전파
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code
            if status in (401, 403):
                raise PermissionError(f"API 키 인증 실패 (HTTP {status})")
            # 기타 오류는 건너뛰고 계속
            continue
        except Exception:
            continue

    if not all_records:
        return pd.DataFrame()

    df = pd.DataFrame(all_records)

    # 사업자등록번호 정규화 컬럼 추가
    if "사업자등록번호" in df.columns:
        df["_brn"] = df["사업자등록번호"].astype(str).str.replace("-", "", regex=False).str.replace(" ", "", regex=False).str.zfill(10)

    return df
