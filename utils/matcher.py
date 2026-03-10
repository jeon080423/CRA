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


# ── 주소 정제 및 분리 ────────────────────────────────────

def clean_address(addr) -> str:
    """
    주소에서 우편번호를 제거하고 공백을 정규화
    예: (03171) 서울특별시 종로구 -> 서울특별시 종로구
    """
    if pd.isna(addr) or not str(addr).strip():
        return ""
    
    s = str(addr).strip()
    
    # 1. 우편번호 관련 텍스트 제거
    # (우) 12345, [우]12345, 우)12345 등
    s = re.sub(r'[\(\[\{]?우[\)\]\}]?\s*', '', s)
    
    # 2. 우편번호 숫자 제거 (앞/뒤 5~6자리)
    s = re.sub(r'^\(?\d{5,6}\)?\s*', '', s)
    s = re.sub(r'\s*\(?\d{5,6}\)?$', '', s)
    
    # 3. 기타 불필요한 기호 제거 및 공백 정규화
    s = re.sub(r'\s+', ' ', s).strip()
    
    return s


def split_address(addr):
    """
    주소를 시도, 시군구, 이후 주소로 분리
    Returns: (sido, sigungu, rest)
    """
    # [v8.2] 정제된 주소 기준
    s = clean_address(addr)
    if not s:
        return "", "", ""
    
    parts = s.split(' ')
    if len(parts) == 0:
        return "", "", ""
    
    sido = parts[0]
    sigungu = ""
    rest = ""
    
    # 세종특별자치시는 기초지자체가 없음
    if "세종" in sido:
        sigungu = ""
        rest = " ".join(parts[1:])
        return sido, sigungu, rest

    if len(parts) > 1:
        # 시군구 처리 (구가 있는 시의 경우 2단어일 수 있음: 예: 수원시 팔달구)
        if len(parts) > 2 and parts[1].endswith(('시', '군')) and parts[2].endswith('구'):
            sigungu = f"{parts[1]} {parts[2]}"
            rest = " ".join(parts[3:])
        else:
            sigungu = parts[1]
            rest = " ".join(parts[2:])
    
    return sido, sigungu, rest


def clean_addresses_bulk(df: pd.DataFrame, addr_col: str):
    """
    DataFrame의 주소 컬럼을 정제/분리하여 새로운 컬럼 추가
    """
    result_df = df.copy()
    raw_addresses = result_df[addr_col].astype(str).fillna("")
    
    cleaned = []
    sidos = []
    sigungus = []
    
    for addr in raw_addresses:
        c = clean_address(addr)
        sd, sgg, _ = split_address(c)
        cleaned.append(c)
        sidos.append(sd)
        sigungus.append(sgg)
        
    idx = result_df.columns.get_loc(addr_col)
    result_df.insert(idx + 1, "주소_정제", cleaned)
    result_df.insert(idx + 2, "시도", sidos)
    result_df.insert(idx + 3, "시군구", sigungus)
    
    return result_df
