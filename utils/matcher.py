"""
사업자등록번호 정규화 및 API 데이터 매칭 로직
"""
import pandas as pd


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


def match_api_data(
    df: pd.DataFrame,
    brn_col: str,
    nps_results: dict,
    nhis_results: dict,
    selected_nps_fields: list,
    selected_nhis_fields: list,
) -> pd.DataFrame:
    """
    원본 DataFrame에 API 조회 결과를 병합

    Args:
        df: 원본 DataFrame
        brn_col: 사업자등록번호 컬럼명
        nps_results: {정규화된 사업자번호: API 응답 dict} (국민연금)
        nhis_results: {정규화된 사업자번호: API 응답 dict} (건강보험)
        selected_nps_fields: 사용자가 선택한 국민연금 필드 목록
        selected_nhis_fields: 사용자가 선택한 건강보험 필드 목록

    Returns:
        pd.DataFrame: API 데이터가 병합된 DataFrame
    """
    result_df = df.copy()

    # 정규화된 사업자등록번호 컬럼 생성
    result_df["_brn_normalized"] = result_df[brn_col].apply(normalize_brn)

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
