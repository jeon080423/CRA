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

