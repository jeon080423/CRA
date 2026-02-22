import requests
import pandas as pd
import datetime
import streamlit as st

# [v6.0] 행정안전부 주민등록 인구현황 API 연동 유틸리티
# [v6.15] stdgSexdAgePpltn (법정동별 통반단위 성/연령별) 엔드포인트 추가

# 사용자 발급 인증키 (공공데이터포털 stdgSexdAgePpltn 승인)
SERVICE_KEY = "6be75af37c6693a24417c2ed2930e4bd4dd01dddf289552260ce8ce1daf43414"

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


# ─────────────────────────────────────────────────────────────────
# [v6.14] MOIS 연령별 인구현황 엑셀 자동 파싱
# ─────────────────────────────────────────────────────────────────

def detect_and_load_mois_excel(uploaded_file):
    """행정안전부 연령별 인구현황 Excel 자동 감지 후 로드.
    Returns: (df, is_mois)  — MOIS 포맷이면 skiprows=3 적용"""
    try:
        df_peek = pd.read_excel(uploaded_file, header=None, nrows=5)
        is_mois = (
            len(df_peek.columns) >= 100 or
            any(any(kw in str(v) for kw in ["행정", "인구현황", "연령별"])
                for v in df_peek.iloc[:3, 0].values)
        )
        uploaded_file.seek(0)
        df = pd.read_excel(uploaded_file, skiprows=3, header=0) if is_mois \
             else pd.read_excel(uploaded_file)
        return df, is_mois
    except Exception:
        uploaded_file.seek(0)
        return pd.read_excel(uploaded_file), False


def parse_mois_excel_with_gender(df, regions=None, min_age=0, max_age=100,
                                  interval=10, include_sejong_in_chungnam=False,
                                  school_level_option=False):
    """MOIS 와이드 포맷 → 지역·성별·연령대 롱 포맷 변환.
    컬럼 구조 (311개):
      [0]코드 [1]지역 [2~3]계 총/등록 [4~104]계 0~100세
      [105~106]남 총/등록 [107~207]남 0~100세
      [208~209]여 총/등록 [210~310]여 0~100세
    """
    region_col_idx = 1

    # 세종 → 충남 합산
    if include_sejong_in_chungnam:
        df = df.copy()
        df.iloc[:, region_col_idx] = (
            df.iloc[:, region_col_idx].astype(str)
            .replace("세종특별자치시", "충청남도")
        )
        num_cols = df.columns[2:]
        df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
        df = df.groupby(df.columns[region_col_idx], as_index=False)[list(df.columns[2:])].sum()
        region_col_idx = 0

    region_col = df.columns[region_col_idx]
    rvals = df[region_col].astype(str)
    df = df[~rvals.isin(["전", "전국", "nan"]) & ~rvals.str.startswith("0000")]

    if regions:
        # MOIS 엑셀의 지역명은 보통 '서울특별시  (1100000000)' 형식이므로 시작 문자열로 매칭
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
            if 8 <= age <= 10: return "8~10세(초등 저학년)"
            if 11 <= age <= 13: return "11~13세(초등 고학년)"
            if 14 <= age <= 16: return "14~16세(중등)"
            if 17 <= age <= 19: return "17~19세(고등)"
            if age < 8: return f"{min_age}~7세"

        # [v6.16] 18세 미만 시작 시 19세 이하 "10대" 통합
        if min_age < 18 and age <= 19:
            return "10대"

        # 20세 이상 그룹핑
        if age >= 20:
             # 19세 이하가 특수 처리된 경우 20세부터 정규 구간(20, 30...)으로 시작
             if school_level_option or min_age < 18:
                 s = (age // interval) * interval
                 e = min(s + interval - 1, max_age, 100)
                 return "100세이상" if s >= 100 else f"{s}~{e}세"

             # 기존 로직 (min_age >= 18 이고 특수 옵션 없을 때)
             if min_age % interval != 0:
                 next_boundary = ((min_age // interval) + 1) * interval
                 if age < next_boundary + interval:
                     first_end = min(next_boundary + interval - 1, max_age, 100)
                     return "100세이상" if min_age >= 100 else f"{min_age}~{first_end}세"

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
            if 8 <= age <= 10: return 8
            if 11 <= age <= 13: return 11
            if 14 <= age <= 16: return 14
            if 17 <= age <= 19: return 17

        if min_age < 18 and age <= 19:
            return min_age

        if age >= 20:
            if school_level_option or min_age < 18:
                return (age // interval) * interval
            if min_age % interval != 0:
                next_boundary = ((min_age // interval) + 1) * interval
                if age < next_boundary + interval:
                    return min_age

        return (age // interval) * interval

    records = []
    for _, row in df.iterrows():
        region = str(row[region_col]).strip()
        for gender, (g_start, g_end) in gender_sections.items():
            for age in range(min_age, min(max_age + 1, 101)):
                idx = g_start + age
                if idx >= g_end or idx >= n_cols:
                    break
                pop = safe_int(row[all_cols[idx]])
                records.append({
                    "지역": region, "성별": gender,
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

