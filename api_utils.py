import requests
import pandas as pd
import datetime
import streamlit as st

# [v6.0] 행정안전부 주민등록 인구현황 API 연동 유틸리티
# [v6.15] stdgSexdAgePpltn (법정동별 통반단위 성/연령별) 엔드포인트 추가

# 사용자 발급 인증키 (공공데이터포털 stdgSexdAgePpltn 승인)
SERVICE_KEY = "6be75af37c6693a24417c2ed2930e4bd4dd01dddf289552260ce8ce1daf43414"
DART_API_KEY = "7482f082735913da589f86b94d2a0639a6673fcd"

# ① 법정동별(통반단위) 성/연령별 → 승인된 API
STDG_BASE_URL = "https://apis.data.go.kr/1741000/stdgSexdAgePpltn"
STDG_OPERATION = "selectStdgSexdAgePpltn"

# ② 행정동별 (기존 fallback)
BASE_URL = "https://apis.data.go.kr/1741000/admmSexdAgePpltn"

# 17개 광역시도 목록 (순서 고정)
SIDO_LIST = [
    "서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시",
    "대전광역시", "울산광역시", "세종특별자치시", "경기도",
    "강원특별자치도", "충청북도", "충청남도", "전북특별자치도",
    "전라남도", "경상북도", "경상남도", "제주특별자치도"
]

SIDO_MAP = {
    "서울특별시": "11",
    "부산광역시": "26",
    "대구광역시": "27",
    "인천광역시": "28",
    "광주광역시": "29",
    "대전광역시": "30",
    "울산광역시": "31",
    "세종특별자치시": "36",
    "경기도": "41",
    "강원특별자치도": "42",
    "충청북도": "43",
    "충청남도": "44",
    "전북특별자치도": "45",
    "전라남도": "46",
    "경상북도": "47",
    "경상남도": "48",
    "제주특별자치도": "50"
}

def get_latest_ym():
    """가장 최근 통계 연월 반환 (매월 말일 기준, 당월은 다음달 1일 이후 공표)"""
    import datetime
    now = datetime.datetime.now()
    # 당월 데이터는 익월 1일 이후 공표되므로 전월 반환
    if now.day < 5:
        prev = now.replace(day=1) - datetime.timedelta(days=1)
        return prev.strftime("%Y%m")
    # 전월 데이터가 안전
    prev = now.replace(day=1) - datetime.timedelta(days=1)
    return prev.strftime("%Y%m")


def fetch_population_data(sido_cd="", sigungu_cd="", ym=None, service_key=None):
    """
    행정안전부 API를 통해 인구 데이터 수신.
    [v6.15] 사용자 승인된 stdgSexdAgePpltn(법정동별 통반단위)을 우선 호출.
    시도/시군구 단위로 집계 후 반환.
    """
    if not ym:
        ym = get_latest_ym()

    actual_key = service_key if service_key else SERVICE_KEY
    st_year = ym[:4]
    st_month = ym[4:]

    # ── ① stdgSexdAgePpltn (승인된 API) ──────────────────────────────
    full_url = f"{STDG_BASE_URL}/{STDG_OPERATION}?serviceKey={actual_key}"
    params = {
        "pageNo": 1,
        "numOfRows": 1000,
        "dataType": "JSON",
        "stYear": st_year,
        "stMonth": st_month,
    }
    if sido_cd:
        params["sidoCd"] = sido_cd
    if sigungu_cd:
        params["sigunguCd"] = sigungu_cd

    try:
        resp = requests.get(full_url, params=params, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            # 응답 키 탐색 (stdgSexdAgePpltn 또는 response > body > items)
            items = None
            if "stdgSexdAgePpltn" in data:
                raw = data["stdgSexdAgePpltn"]
                items = raw.get("item", raw.get("items", []))
            elif "response" in data:
                body = data["response"].get("body", {})
                items = body.get("items", {}).get("item", [])
            if items:
                if isinstance(items, dict):
                    items = [items]
                return pd.DataFrame(items)
            # 빈 응답이면 fallback
    except Exception:
        pass

    # ── ② 기존 admmSexdAgePpltn (fallback) ──────────────────────────
    full_url2 = f"{BASE_URL}?serviceKey={actual_key}"
    params2 = {
        "pageNo": 1,
        "numOfRows": 500,
        "dataType": "JSON",
        "administStatsYm": ym,
    }
    if sido_cd:
        params2["sidoCd"] = sido_cd
    if sigungu_cd:
        params2["sigunguCd"] = sigungu_cd

    try:
        resp2 = requests.get(full_url2, params=params2, timeout=15)
        if resp2.status_code != 200:
            st.error(f"API 오류 {resp2.status_code}: {resp2.text[:300]}")
            return None
        data2 = resp2.json()
        if "admmSexdAgePpltn" in data2:
            items2 = data2["admmSexdAgePpltn"].get("item", [])
            if isinstance(items2, dict):
                items2 = [items2]
            return pd.DataFrame(items2)
        st.error(f"API 응답에 데이터가 없습니다.\n{data2}")
        return None
    except Exception as e:
        st.error(f"네트워크 오류: {e}")
        return None


def process_population_df(df, min_age=0, max_age=100):
    """
    API 응답 데이터프레임을 표본 설계용(성별, 연령대별)으로 재정의
    """
    if df is None or df.empty:
        return None
        
    # 만 연령별 컬럼 추출 및 멜팅
    # 컬럼명 예시: man_0_ppltn_cnt, woman_100_below_ppltn_cnt 등
    
    records = []
    for _, row in df.iterrows():
        area_name = f"{row.get('sidoNm', '')} {row.get('sigunguNm', '')} {row.get('admNm', '')}".strip()
        
        for age in range(0, 101):
            # 남성
            m_col = f"man_{age}_ppltn_cnt"
            if m_col in row:
                count = int(row[m_col])
                if min_age <= age <= max_age:
                    records.append({"Area": area_name, "Gender": "남", "Age": age, "Population": count})
            
            # 여성
            w_col = f"woman_{age}_ppltn_cnt"
            if w_col in row:
                count = int(row[w_col])
                if min_age <= age <= max_age:
                    records.append({"Area": area_name, "Gender": "여", "Age": age, "Population": count})
                    
    return pd.DataFrame(records)

def aggregate_by_groups(df, interval=10):
    """
    1세 단위 데이터를 사용자 정의 단위(1세, 5세, 10세 등)로 그룹화
    """
    if df is None or df.empty:
        return None
        
    def map_age_group(age):
        start = (age // interval) * interval
        end = start + interval - 1
        if interval == 1:
            return f"{age}세"
        return f"{start}세-{end}세"

    df["AgeGroup"] = df["Age"].apply(map_age_group)
    
    # 지역(Area)은 시도 단위로 축소 (너무 세밀하면 할당이 어려움)
    df["Sido"] = df["Area"].apply(lambda x: x.split()[0])
    
    # 정렬을 위해 숫자형 연령대 컬럼 추가
    df["AgeSort"] = df["Age"].apply(lambda x: (x // interval) * interval)
    
    agg_df = df.groupby(["Sido", "Gender", "AgeSort", "AgeGroup"])["Population"].sum().reset_index()
    agg_df = agg_df.sort_values(["Sido", "Gender", "AgeSort"])
    return agg_df.drop(columns=["AgeSort"])


def detect_and_load_mois_excel(uploaded_file):
    """행정안전부 연령별 인구현황 Excel 자동 감지 후 로드.
    Returns: (df, is_mois)  — MOIS 포맷이면 skiprows=3 적용"""
    try:
        # 엑셀의 헤더와 구성을 살짝 봄
        df_peek = pd.read_excel(uploaded_file, header=None, nrows=5)
        
        # 행안부 파일 특징: 컬럼수가 매우 많고(나이별), 헤더 근처에 '행정' '인구' 등의 키워드가 있음
        is_mois = (
            len(df_peek.columns) >= 100 or 
            any(any(kw in str(v) for kw in ["행정", "인구현황", "연령별"]) 
                for v in df_peek.iloc[:3, 0].values)
        )
        
        uploaded_file.seek(0)
        if is_mois:
            # 행안부 엑셀은 보통 위 3줄이 제목/설명이므로 3줄 건너뛰고 4행을 헤더로 읽음
            df = pd.read_excel(uploaded_file, skiprows=3, header=0)
        else:
            df = pd.read_excel(uploaded_file)
            
        return df, is_mois
    except Exception:
        uploaded_file.seek(0)
        try:
            return pd.read_excel(uploaded_file), False
        except:
            return None, False

# ─────────────────────────────────────────────────────────────────
# [v6.14] MOIS 연령별 인구현황 엑셀 자동 파싱
# ─────────────────────────────────────────────────────────────────

def get_mois_region_levels(df):
    """MOIS 데이터의 행정구역 코드 분석하여 가용한 계층(광역/기초/상세) 반환"""
    if df is None or df.empty:
        return []
    
    code_col = df.columns[0]
    codes = df[code_col].astype(str).str.strip()
    
    levels = []
    # 1. 광역 시도
    if any(codes.str.endswith("00000000") & (codes != "0000000000")):
        levels.append("광역 시도 단위")
    
    # 기초/상세를 구분하기 위해 '구가 있는 시'를 감지
    # (끝 5자리가 00000인 코드 중, 상위 4자리는 같으면서 5번째 자리가 0인 것과 0이 아닌 것이 공존하면 상세 레벨 존재)
    sigungu_codes = codes[codes.str.endswith("00000") & ~codes.str.endswith("00000000")]
    if not sigungu_codes.empty:
        levels.append("기초 시/군/구 단위")
        
        # 상세 레벨 존재 여부 확인: 41110(수원시)와 41111(장안구)가 모두 존재하는지
        parents = sigungu_codes[sigungu_codes.str.endswith("000000")]
        children = sigungu_codes[~sigungu_codes.str.endswith("000000")]
        
        has_sub_districts = False
        for p in parents:
            p_prefix = p[:4]
            if any(children.str.startswith(p_prefix)):
                has_sub_districts = True
                break
        
        if has_sub_districts:
            levels.append("시군구별 상세 단위")
        
    return levels

def parse_mois_excel_with_gender(df, regions=None, level="광역 시도 단위", min_age=0, max_age=100,
                                  interval=10, include_sejong_in_chungnam=False,
                                  school_level_option=False,
                                  upper_age_cutoff=None):
    """MOIS 와이드 포맷 → 지역·성별·연령대 롱 포맷 변환.
    level: "광역 시도 단위", "기초 시/군/구 단위", "시군구별 상세 단위"
    """
    code_col = df.columns[0]
    region_col = df.columns[1]

    # 세종 → 충남 합산
    if include_sejong_in_chungnam:
        df = df.copy()
        df[region_col] = df[region_col].astype(str).replace("세종특별자치시", "충청남도")
        num_cols = df.columns[2:]
        df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
        df = df.groupby(region_col, as_index=False)[list(df.columns[2:])].sum()

    df_filtered = df.copy()
    df_filtered[code_col] = df_filtered[code_col].astype(str).str.strip()
    cvals = df_filtered[code_col]
    rvals = df_filtered[region_col].astype(str)
    
    # 기본 필터: 전국계 및 무효 행 제외
    mask = ~rvals.isin(["전", "전국", "nan"]) & ~cvals.str.startswith("0000")
    
    if level == "광역 시도 단위":
        mask &= cvals.str.endswith("00000000")
    elif level == "기초 시/군/구 단위":
        # 시군구(00000) 중, 하위 구(Child)가 있는 부모 시(Parent)는 남기고, 자식 구들은 제외
        # 서울처럼 부모-자식 관계가 없으면 그냥 모든 구 포함
        base_mask = cvals.str.endswith("00000") & ~cvals.str.endswith("00000000")
        sigungu_codes = cvals[base_mask].unique()
        
        parents_with_children = []
        children_to_exclude = []
        
        # 부모-자식 관계 분석
        # (예: 41110 수원시는 41111 장안구의 부모)
        parents = [c for c in sigungu_codes if c.endswith("000000")]
        children = [c for c in sigungu_codes if not c.endswith("000000")]
        
        for p in parents:
            p_prefix = p[:4]
            if any(c.startswith(p_prefix) for c in children):
                parents_with_children.append(p)
                children_to_exclude.extend([c for c in children if c.startswith(p_prefix)])
        
        # 필터: 기본 시군구 중 자식 구들만 제외하면 '기초' 단위가 됨
        mask &= base_mask & ~cvals.isin(children_to_exclude)
        
    elif level == "시군구별 상세 단위":
        # 하위 구가 있는 시의 경우, 부모 시를 제외하고 자식 구들만 남김
        base_mask = cvals.str.endswith("00000") & ~cvals.str.endswith("00000000")
        sigungu_codes = cvals[base_mask].unique()
        
        parents_to_exclude = []
        parents = [c for c in sigungu_codes if c.endswith("000000")]
        children = [c for c in sigungu_codes if not c.endswith("000000")]
        
        for p in parents:
            p_prefix = p[:4]
            if any(c.startswith(p_prefix) for c in children):
                parents_to_exclude.append(p)
        
        mask &= base_mask & ~cvals.isin(parents_to_exclude)
    
    df = df_filtered[mask]

    if regions:
        # 지역명으로 시작하는 행만 필터링
        df = df[df[region_col].apply(lambda x: any(str(x).strip().startswith(r) for r in regions))]
    if df.empty:
        return None

    all_cols = df.columns.tolist()
    n_cols = len(all_cols)

    # 성별 컬럼 범위 결정
    gender_sections = {}
    if n_cols >= 208:
        gender_sections = {"남": (107, 208), "여": (210, min(311, n_cols))}
    elif n_cols >= 105:
        gender_sections = {"계": (4, 105)}

    def safe_int(val):
        try:
            return int(float(str(val).replace(",", "").replace(" ", "")))
        except (ValueError, TypeError):
            return 0

    def age_label(age):
        if interval == 1:
            return f"{age}세"

        # [v6.16] 학교급별 구분 옵션 적용 (19세 이하)
        if school_level_option and age <= 19:
            if 8 <= age <= 13: return "8~13세(초등)"
            if 14 <= age <= 16: return "14~16세(중등)"
            if 17 <= age <= 19: return "17~19세(고등)"
            if age < 8: return f"{min_age}~7세"

        # [v6.21] 시작연령이 18세 또는 19세인 경우 20대와 통합 ("19~29세" 등)
        # 단, 학교급별 옵션이 꺼져 있을 때만 적용 (켜져 있으면 '고등' 등으로 표시됨)
        if not school_level_option and (min_age == 18 or min_age == 19) and age <= 29:
            fe = min(29, max_age, 100)
            return f"{min_age}~{fe}세"

        # [v6.16] 18세 미만 시작 시 19세 이하 "10대" 통합
        if min_age < 18 and age <= 19:
            return "10대"

        # [v6.23] 상위 연령대 통합 (60대 이상, 70대 이상, 80대 이상)
        if upper_age_cutoff is not None and age >= upper_age_cutoff:
            return f"{upper_age_cutoff}세 이상"

        # 20세 이상 그룹핑
        if age >= 20:
             # 19세 이하가 특수 처리된 경우 20세부터 정규 구간(20, 30...)으로 시작
             if school_level_option or min_age < 18:
                 s = (age // interval) * interval
                 e = min(s + interval - 1, max_age, 100)
                 return "100세이상" if s >= 100 else f"{s}~{e}세"

             # [v6.21] 18/19세 통합 케이스를 제외한 나머지 변칙 시작점 처리
             if min_age % interval != 0:
                 nb = ((min_age // interval) + 1) * interval
                 if age < nb + interval:
                     fe = min(nb + interval - 1, max_age, 100)
                     return "100세이상" if min_age >= 100 else f"{min_age}~{fe}세"

        # 표준 그룹핑
        s = (age // interval) * interval
        e = min(s + interval - 1, max_age, 100)
        return "100세이상" if s >= 100 else f"{s}~{e}세"

    def age_sort_key(age):
        """그룹핑 정렬 키"""
        if interval == 1:
            return age

        if school_level_option and age <= 19:
            if age < 8: return 0
            if 8 <= age <= 13: return 8
            if 14 <= age <= 16: return 14
            if 17 <= age <= 19: return 17

        # [v6.23] 상위 연령대 통합 정렬값
        if upper_age_cutoff is not None and age >= upper_age_cutoff:
            return upper_age_cutoff

        # [v6.21] 18/19세 통합 정렬값
        if not school_level_option and (min_age == 18 or min_age == 19) and age <= 29:
            return min_age

        if min_age < 18 and age <= 19:
            return min_age

        if age >= 20:
            if school_level_option or min_age < 18:
                return (age // interval) * interval
            if min_age % interval != 0:
                nb = ((min_age // interval) + 1) * interval
                if age < nb + interval:
                    return min_age

        return (age // interval) * interval

    records = []
    for _, row in df.iterrows():
        # 지역명에서 코드 부분 제거 (예: '서울특별시  (1100000000)' -> '서울특별시')
        raw_reg = str(row[region_col]).strip()
        clean_reg = raw_reg.split('(')[0].strip()
        
        for gender, (g_start, g_end) in gender_sections.items():
            for age in range(min_age, min(max_age + 1, 101)):
                idx = g_start + age
                if idx >= g_end or idx >= n_cols:
                    break
                pop = safe_int(row[all_cols[idx]])
                records.append({
                    "지역": clean_reg, "성별": gender,
                    "연령": age, "연령대": age_label(age), "인구수": pop
                })

    if not records:
        return None

    result = pd.DataFrame(records)
    result["AgeSort"] = result["연령"].apply(age_sort_key)
    agg = (result.groupby(["지역", "성별", "AgeSort", "연령대"])["인구수"]
           .sum().reset_index()
           .sort_values(["지역", "성별", "AgeSort"])
           .drop(columns=["AgeSort"]))
    return agg[agg["인구수"] > 0].reset_index(drop=True)



def format_sample_pivot_table(res_df):
    """표본 배분 결과(지역·성별·연령대·final_n)를 이미지 형식 피벗으로 변환.
    열 순서: 총계 | 남 계 | 여 계 | 남(연령대 오름차순) | 여(연령대 오름차순)
    행: 17개 시도 → 총계 행 (노란색)
    """
    required = {"지역", "성별", "연령대", "final_n"}
    if not required.issubset(res_df.columns):
        return None

    # ── 연령대 정렬 키 (시작 숫자 기준) ─────────────────────────────
    def age_start(name):
        try:
            return int(str(name).split("~")[0].replace("세", "").strip())
        except Exception:
            return 999

    # 연령대 고유값을 숫자 오름차순 정렬
    age_groups = sorted(res_df["연령대"].unique(), key=age_start)
    genders = ["남", "여"]

    # ── 피벗: 지역 × (성별, 연령대) ─────────────────────────────────
    pivot = res_df.pivot_table(
        index="지역",
        columns=["성별", "연령대"],
        values="final_n",
        aggfunc="sum",
        fill_value=0
    )

    # ── 열 순서 재정렬 ────────────────────────────────────────────────
    ordered_age_cols = []
    for g in genders:
        for ag in age_groups:
            if (g, ag) in pivot.columns:
                ordered_age_cols.append((g, ag))

    # 성별 소계
    gender_totals = {}
    for g in genders:
        g_cols = [(g, ag) for ag in age_groups if (g, ag) in pivot.columns]
        if g_cols:
            gender_totals[g] = pivot[g_cols].sum(axis=1)

    # 전체 총계
    all_total = pivot.sum(axis=1)

    # 결과 데이터프레임 조립 (단일 인덱스 열명)
    frames = {"총계": all_total}
    for g in genders:
        if g in gender_totals:
            frames[f"{g} 계"] = gender_totals[g]
    for g, ag in ordered_age_cols:
        frames[f"{g} {ag}"] = pivot[(g, ag)]

    result = pd.DataFrame(frames, index=pivot.index)

    # ── 지역 순서 고정 (SIDO_LIST 순) ────────────────────────────────
    try:
        sido_order = [s for s in SIDO_LIST if s in result.index]
        extra = [s for s in result.index if s not in sido_order]
        result = result.loc[sido_order + extra]
    except Exception:
        pass

    # ── 총계 행 추가 (인덱스명 "총계") ───────────────────────────────
    total_row = result.sum(numeric_only=True).rename("총계")
    result = pd.concat([result, total_row.to_frame().T])

    return result

