"""
사업자등록번호 정규화 및 API 데이터 매칭 로직
"""
import pandas as pd
from difflib import SequenceMatcher


def normalize_brn(brn) -> str:
    """
    사업자등록번호를 하이픈 없는 10자리 문자열로 정규화

    Args:
        brn: 사업자등록번호 (다양한 형식 가능: '123-45-67890', 1234567890 등)

    Returns:
        str: 하이픈 없는 10자리 문자열
    """
    if pd.isna(brn):
        return ""
    brn_str = str(brn).strip().replace("-", "").replace(" ", "")
    # 소수점 제거 (엑셀에서 숫자로 읽힌 경우)
    if "." in brn_str:
        brn_str = brn_str.split(".")[0]
    return brn_str.zfill(10)


def _normalize_text(text) -> str:
    """비교를 위한 텍스트 정규화 (공백·특수문자 제거, 소문자)"""
    if pd.isna(text) or text is None:
        return ""
    s = str(text).strip()
    # 괄호, 주식회사 등 제거
    for rm in ["(주)", "(유)", "주식회사", "(사)", "(재)", "(합)"]:
        s = s.replace(rm, "")
    s = s.replace(" ", "").replace("-", "").replace(".", "").lower()
    return s


def text_similarity(a, b) -> float:
    """두 텍스트 사이의 유사도 (0.0 ~ 1.0)"""
    na, nb = _normalize_text(a), _normalize_text(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def compute_row_similarity(
    row,
    brn_col: str,
    name_col: str,
    addr_col: str,
    nps_results: dict,
    nhis_results: dict,
) -> float:
    """
    한 행의 업로드 데이터와 API 반환 데이터 간 유사도를 계산

    비교 항목 (가중치):
      - 사업자등록번호 완전 일치 여부 (30%)
      - 회사명 vs API 사업장명 (40%)
      - 주소 vs API 주소 (30%)

    Returns:
        float: 0.0 ~ 100.0 (퍼센트)
    """
    brn = normalize_brn(row.get(brn_col, ""))
    if not brn or len(brn) != 10:
        return 0.0

    # API 결과 가져오기 (국민연금 우선, 없으면 건강보험)
    api_data = nps_results.get(brn, {})
    api_data_nhis = nhis_results.get(brn, {})

    if "_error" in api_data and "_error" in api_data_nhis:
        return 0.0
    if "_error" in api_data:
        api_data = {}
    if "_error" in api_data_nhis:
        api_data_nhis = {}

    scores = []
    weights = []

    # 1) 사업자등록번호 일치 확인 (API에서 결과가 돌아온 것 자체가 일치)
    has_nps = bool(api_data)
    has_nhis = bool(api_data_nhis)
    if has_nps or has_nhis:
        scores.append(1.0)
        weights.append(30)
    else:
        scores.append(0.0)
        weights.append(30)

    # 2) 회사명 비교
    if name_col and name_col != "(선택 안 함)":
        uploaded_name = row.get(name_col, "")
        if uploaded_name and not pd.isna(uploaded_name):
            api_name = api_data.get("사업장명", "") or api_data_nhis.get("사업장명", "")
            sim = text_similarity(uploaded_name, api_name) if api_name else 0.0
            scores.append(sim)
            weights.append(40)

    # 3) 주소 비교
    if addr_col and addr_col != "(선택 안 함)":
        uploaded_addr = row.get(addr_col, "")
        if uploaded_addr and not pd.isna(uploaded_addr):
            api_addr = (
                api_data.get("사업장도로명상세주소", "")
                or api_data_nhis.get("주소", "")
            )
            sim = text_similarity(uploaded_addr, api_addr) if api_addr else 0.0
            scores.append(sim)
            weights.append(30)

    if not weights:
        return 0.0

    weighted = sum(s * w for s, w in zip(scores, weights)) / sum(weights)
    return round(weighted * 100, 1)


def match_api_data(
    df: pd.DataFrame,
    brn_col: str,
    nps_results: dict,
    nhis_results: dict,
    selected_nps_fields: list,
    selected_nhis_fields: list,
    name_col: str = "",
    addr_col: str = "",
    similarity_threshold: float = 0.0,
) -> pd.DataFrame:
    """
    원본 DataFrame에 API 조회 결과를 병합하고 유사도를 계산

    Args:
        df: 원본 DataFrame
        brn_col: 사업자등록번호 컬럼명
        nps_results: {정규화된 사업자번호: API 응답 dict} (국민연금)
        nhis_results: {정규화된 사업자번호: API 응답 dict} (건강보험)
        selected_nps_fields: 사용자가 선택한 국민연금 필드 목록
        selected_nhis_fields: 사용자가 선택한 건강보험 필드 목록
        name_col: 회사명 컬럼명 (유사도 계산용)
        addr_col: 주소 컬럼명 (유사도 계산용)
        similarity_threshold: 유사도 하한선 (0~100, 이 값 이상만 포함)

    Returns:
        pd.DataFrame: API 데이터가 병합된 DataFrame
    """
    result_df = df.copy()

    # 정규화된 사업자등록번호 컬럼 생성
    result_df["_brn_normalized"] = result_df[brn_col].apply(normalize_brn)

    # 유사도 계산
    result_df["유사도(%)"] = result_df.apply(
        lambda row: compute_row_similarity(
            row, brn_col, name_col, addr_col,
            nps_results, nhis_results,
        ),
        axis=1,
    )

    # 국민연금 필드 추가
    for field in selected_nps_fields:
        col_name = f"[국민연금] {field}"
        result_df[col_name] = result_df["_brn_normalized"].apply(
            lambda brn, f=field: _get_field_value(nps_results, brn, f)
        )

    # 건강보험 필드 추가
    for field in selected_nhis_fields:
        col_name = f"[건강보험] {field}"
        result_df[col_name] = result_df["_brn_normalized"].apply(
            lambda brn, f=field: _get_field_value(nhis_results, brn, f)
        )

    # 정규화 컬럼 제거
    result_df.drop(columns=["_brn_normalized"], inplace=True)

    # 유사도 필터링
    if similarity_threshold > 0:
        result_df = result_df[result_df["유사도(%)"] >= similarity_threshold].reset_index(drop=True)

    return result_df


def _get_field_value(results: dict, brn: str, field: str) -> str:
    """API 결과에서 특정 필드 값 추출"""
    if not brn:
        return "사업자번호 없음"
    data = results.get(brn, {})
    if not data:
        return "조회불가"
    if "_error" in data:
        return data["_error"]
    value = data.get(field, "해당없음")
    return str(value) if value is not None else "해당없음"

