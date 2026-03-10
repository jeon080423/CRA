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


def _normalize_sido(sido: str) -> str:
    """시도 명칭을 표준 단축형으로 변환"""
    if not sido: return ""
    s = sido.strip()
    mapping = {
        "서울특별시": "서울", "서울시": "서울",
        "부산광역시": "부산", "부산시": "부산",
        "대구광역시": "대구", "대구시": "대구",
        "인천광역시": "인천", "인천시": "인천",
        "광주광역시": "광주", "광주시": "광주",
        "대전광역시": "대전", "대전시": "대전",
        "울산광역시": "울산", "울산시": "울산",
        "세종특별자치시": "세종", "세종시": "세종",
        "경기도": "경기",
        "강원특별자치도": "강원", "강원도": "강원",
        "충청북도": "충북",
        "충청남도": "충남",
        "전라북도": "전북", "전북특별자치도": "전북",
        "전라남도": "전남",
        "경상북도": "경북", "경상북": "경북",
        "경상남도": "경남",
        "제주특별자치도": "제주", "제주시": "제주", "제주도": "제주"
    }
    return mapping.get(s, s)


def split_address(addr):
    """
    주소를 시도, 시군구, 이후 주소로 분리 및 정규화
    Returns: (sido, sigungu, rest)
    """
    s = clean_address(addr)
    if not s:
        return "", "", ""
    
    parts = s.split(' ')
    if len(parts) == 0:
        return "", "", ""
    
    # 1. 시도 처리 및 정규화
    raw_sido = parts[0]
    sido = _normalize_sido(raw_sido)
    
    sigungu = ""
    rest = ""
    
    # 세종특별자치시는 기초지자체가 없음
    if "세종" in sido:
        sigungu = ""
        rest = " ".join(parts[1:])
        return sido, sigungu, rest

    if len(parts) > 1:
        # 2. 시군구 처리
        # [v9.0] 접미사(시, 군, 구) 보완 매커니즘
        def _ensure_suffix(word, suffixes):
            if not word: return ""
            if word.endswith(suffixes): return word
            # 특정 예외나 빈번한 누락 케이스 대응 (필요 시 확장)
            if word in ["수원", "성남", "안양", "용인", "고양", "안산", "창원", "천안", "청주", "포항"]:
                return word + "시"
            if word in ["팔달", "영통", "권선", "장안", "수정", "중원", "분당", "만안", "동안", "처인", "기흥", "수지"]:
                return word + "구"
            # 기본적으로 뒤에 오는 단어가 있으면 '시' 또는 '구'일 가능성이 높음
            # 여기서는 보수적으로 시/군/구 중 하나가 아예 없는 경우에만 추측 (사용자 요청 반영)
            return word

        # 구가 있는 시의 경우 (예: 수원시 팔달구)
        if len(parts) > 2:
            p1, p2 = parts[1], parts[2]
            # p1이 시/군으로 끝나거나 p2가 구로 끝나는 경우 조합
            if (p1.endswith(('시', '군')) and p2.endswith('구')) or \
               (p1 in ["수원", "성남", "안양", "용인", "고양", "안산", "창원", "천안", "청주", "포항"] and p2.endswith('구')) or \
               (p1.endswith(('시', '군')) and p2 in ["팔달", "영통", "권선", "장구", "수정", "중원", "분당", "만안", "동안", "처인", "기흥", "수지"]):
                
                sgg1 = _ensure_suffix(p1, ('시', '군'))
                sgg2 = _ensure_suffix(p2, ('구'))
                sigungu = f"{sgg1} {sgg2}"
                rest = " ".join(parts[3:])
            else:
                sigungu = _ensure_suffix(p1, ('시', '군', '구'))
                rest = " ".join(parts[2:])
        else:
            sigungu = _ensure_suffix(parts[1], ('시', '군', '구'))
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
