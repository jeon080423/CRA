"""
사업자등록번호 정규화, 회사명 정제, 데이터 매칭 로직

전체 데이터셋 다운로드 → 로컬 매칭 방식
"""
import re
import pandas as pd
from difflib import SequenceMatcher


def normalize_brn(brn) -> str:
    """
    사업자등록번호를 하이픈 없는 10자리 문자열로 정규화
    """
    if pd.isna(brn):
        return ""
    brn_str = str(brn).strip().replace("-", "").replace(" ", "")
    if "." in brn_str:
        brn_str = brn_str.split(".")[0]
    return brn_str.zfill(10)


# ── 회사명 정제 ──────────────────────────────────────────

def clean_company_name(name) -> str:
    """
    회사명에서 법인 유형 표기를 제거하고 순수 회사명만 반환
    제거: (주), (유), (사), 주식회사, 유한회사, 사단법인, 합자회사
    유지: 영문 괄호, 지점/공장 괄호, 구 상호 표기, 신협
    """
    if pd.isna(name) or name is None:
        return ""
    s = str(name).strip()
    if not s:
        return ""

    s = re.sub(r'(?<![가-힣a-zA-Z.\,])\(주\)(?![)])', '', s)
    s = re.sub(r'\(주\)$', '', s)
    s = re.sub(r'(?<![가-힣a-zA-Z.\,])\(유\)(?![)])', '', s)
    s = re.sub(r'\(유\)$', '', s)
    s = re.sub(r'(?<![가-힣a-zA-Z.\,])\(사\)(?![)])', '', s)
    s = re.sub(r'\(사\)$', '', s)

    s = re.sub(r'주식회사\s*', '', s)
    s = re.sub(r'\s*주식회사', '', s)
    s = re.sub(r'유한회사\s*', '', s)
    s = re.sub(r'\s*유한회사', '', s)
    s = re.sub(r'사단법인\s*', '', s)
    s = re.sub(r'합자회사\s*', '', s)

    s = re.sub(r'\s+', ' ', s).strip()
    return s


def clean_company_names_bulk(df: pd.DataFrame, name_col: str):
    """
    DataFrame의 회사명 컬럼을 정제하여 '회사명_정제' 컬럼 추가
    Returns: (수정된 df, stats_dict)
    """
    result_df = df.copy()
    originals = result_df[name_col].astype(str).fillna("")
    cleaned = originals.apply(clean_company_name)

    name_idx = result_df.columns.get_loc(name_col)
    result_df.insert(name_idx + 1, "회사명_정제", cleaned)

    changed_mask = originals != cleaned
    total = len(result_df)
    changed = int(changed_mask.sum())

    type_counts = {}
    for label, pattern in {"(주)": r'\(주\)', "(유)": r'\(유\)', "(사)": r'\(사\)',
                           "주식회사": r'주식회사', "유한회사": r'유한회사',
                           "사단법인": r'사단법인', "합자회사": r'합자회사'}.items():
        count = int(originals.str.contains(pattern, regex=True, na=False).sum())
        if count > 0:
            type_counts[label] = count

    changed_indices = changed_mask[changed_mask].index[:10]
    samples = [(originals.iloc[i], cleaned.iloc[i]) for i in changed_indices]

    return result_df, {
        'total': total, 'changed': changed, 'unchanged': total - changed,
        'type_counts': type_counts, 'samples': samples,
    }


# ── 텍스트 유사도 ──────────────────────────────────────────

def _normalize_text(text) -> str:
    """비교를 위한 텍스트 정규화"""
    if pd.isna(text) or text is None:
        return ""
    s = str(text).strip()
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


# ── 로컬 매칭 (전체 데이터셋 기반) ──────────────────────────────

def match_with_datasets(
    upload_df: pd.DataFrame,
    brn_col: str,
    nps_df: pd.DataFrame,
    nhis_df: pd.DataFrame,
    selected_nps_fields: list,
    selected_nhis_fields: list,
    name_col: str = "",
    addr_col: str = "",
    similarity_threshold: float = 0.0,
    progress_callback=None,
) -> pd.DataFrame:
    """
    업로드 데이터를 전체 API 데이터셋과 사업자등록번호 기반으로 로컬 매칭

    Args:
        upload_df: 업로드된 엑셀 DataFrame
        brn_col: 사업자등록번호 컬럼명
        nps_df: 국민연금 전체 데이터셋 DataFrame (download_nps_dataset 결과)
        nhis_df: 건강보험 전체 데이터셋 DataFrame (download_nhis_dataset 결과)
        selected_nps_fields: 선택된 국민연금 필드 목록
        selected_nhis_fields: 선택된 건강보험 필드 목록
        name_col: 회사명(정제) 컬럼명 (유사도 계산용)
        addr_col: 주소 컬럼명 (유사도 계산용)
        similarity_threshold: 유사도 하한선 (0~100)
        progress_callback: fn(current, total, msg) 진행 콜백

    Returns:
        pd.DataFrame: 매칭 결과 DataFrame
    """
    result_df = upload_df.copy()

    # 업로드 데이터 사업자번호 정규화
    result_df["_brn"] = result_df[brn_col].apply(normalize_brn)

    # 국민연금 데이터 인덱싱 (사업자번호 → 행)
    nps_lookup = {}
    if not nps_df.empty and "_brn" in nps_df.columns:
        for _, row in nps_df.iterrows():
            brn = row["_brn"]
            if brn and len(brn) == 10:
                nps_lookup[brn] = row

    # 건강보험 데이터 인덱싱
    nhis_lookup = {}
    if not nhis_df.empty and "_brn" in nhis_df.columns:
        for _, row in nhis_df.iterrows():
            brn = row["_brn"]
            if brn and len(brn) == 10:
                nhis_lookup[brn] = row

    # 매칭 수행
    total = len(result_df)
    nps_data_rows = []
    nhis_data_rows = []
    similarities = []

    for idx, row in result_df.iterrows():
        brn = row["_brn"]

        if progress_callback and idx % 100 == 0:
            progress_callback(idx, total, f"로컬 매칭 중... ({idx:,}/{total:,})")

        # 국민연금 매칭
        nps_match = nps_lookup.get(brn, None)
        nps_row = {}
        for field in selected_nps_fields:
            if nps_match is not None and field in nps_match.index:
                nps_row[f"[국민연금] {field}"] = str(nps_match[field]) if pd.notna(nps_match[field]) else "해당없음"
            else:
                nps_row[f"[국민연금] {field}"] = "조회불가"
        nps_data_rows.append(nps_row)

        # 건강보험 매칭
        nhis_match = nhis_lookup.get(brn, None)
        nhis_row = {}
        for field in selected_nhis_fields:
            if nhis_match is not None and field in nhis_match.index:
                nhis_row[f"[건강보험] {field}"] = str(nhis_match[field]) if pd.notna(nhis_match[field]) else "해당없음"
            else:
                nhis_row[f"[건강보험] {field}"] = "조회불가"
        nhis_data_rows.append(nhis_row)

        # 유사도 계산
        sim = _compute_similarity(
            row, brn, name_col, addr_col,
            nps_match, nhis_match,
        )
        similarities.append(sim)

    if progress_callback:
        progress_callback(total, total, "매칭 완료!")

    # 결과 컬럼 추가
    result_df["유사도(%)"] = similarities

    if selected_nps_fields:
        nps_result_df = pd.DataFrame(nps_data_rows, index=result_df.index)
        result_df = pd.concat([result_df, nps_result_df], axis=1)

    if selected_nhis_fields:
        nhis_result_df = pd.DataFrame(nhis_data_rows, index=result_df.index)
        result_df = pd.concat([result_df, nhis_result_df], axis=1)

    # 내부 컬럼 제거
    result_df.drop(columns=["_brn"], inplace=True, errors="ignore")

    # 유사도 필터링
    if similarity_threshold > 0:
        result_df = result_df[result_df["유사도(%)"] >= similarity_threshold].reset_index(drop=True)

    return result_df


def _compute_similarity(row, brn, name_col, addr_col, nps_match, nhis_match) -> float:
    """한 행의 유사도 계산 (0.0 ~ 100.0)"""
    scores = []
    weights = []

    # 1) 사업자등록번호 매칭 여부 (30%)
    has_match = nps_match is not None or nhis_match is not None
    scores.append(1.0 if has_match else 0.0)
    weights.append(30)

    # 2) 회사명 비교 (40%)
    if name_col and name_col != "(선택 안 함)":
        uploaded_name = row.get(name_col, "")
        if uploaded_name and not pd.isna(uploaded_name):
            api_name = ""
            if nps_match is not None and "사업장명" in nps_match.index:
                api_name = str(nps_match["사업장명"]) if pd.notna(nps_match["사업장명"]) else ""
            elif nhis_match is not None and "사업장명" in nhis_match.index:
                api_name = str(nhis_match["사업장명"]) if pd.notna(nhis_match["사업장명"]) else ""
            sim = text_similarity(uploaded_name, api_name) if api_name else 0.0
            scores.append(sim)
            weights.append(40)

    # 3) 주소 비교 (30%)
    if addr_col and addr_col != "(선택 안 함)":
        uploaded_addr = row.get(addr_col, "")
        if uploaded_addr and not pd.isna(uploaded_addr):
            api_addr = ""
            if nps_match is not None and "사업장도로명상세주소" in nps_match.index:
                api_addr = str(nps_match["사업장도로명상세주소"]) if pd.notna(nps_match["사업장도로명상세주소"]) else ""
            elif nhis_match is not None and "주소" in nhis_match.index:
                api_addr = str(nhis_match["주소"]) if pd.notna(nhis_match["주소"]) else ""
            sim = text_similarity(uploaded_addr, api_addr) if api_addr else 0.0
            scores.append(sim)
            weights.append(30)

    if not weights:
        return 0.0

    weighted = sum(s * w for s, w in zip(scores, weights)) / sum(weights)
    return round(weighted * 100, 1)
