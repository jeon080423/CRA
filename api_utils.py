import requests
import pandas as pd
import datetime
import streamlit as st

# [v6.0] 행정안전부 주민등록 인구현황 API 연동 유틸리티
# API Key: MGFhOGVmMjZmMTExNjIyODgxNTcxNDJmMGI5NTk4ZDQ=

SERVICE_KEY = "MGFhOGVmMjZmMTExNjIyODgxNTcxNDJmMGI5NTk4ZDQ="
BASE_URL = "http://apis.data.go.kr/1741000/admmSexdAgePpltn"

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
    """가장 최근의 안정적인 통계 연월 반환 (202512 에러 대응을 위해 202511 고정 권장)"""
    return "202511"

def fetch_population_data(sido_cd="", sigungu_cd="", ym=None, service_key=None):
    """
    행정안전부 API를 통해 인구 데이터 수신
    """
    if not ym:
        ym = get_latest_ym()
        
    actual_key = service_key if service_key else SERVICE_KEY
    
    params = {
        "serviceKey": actual_key,
        "pageNo": 1,
        "numOfRows": 500, 
        "dataType": "JSON",
        "searchYearMonth": ym
    }
    
    if sido_cd:
        params["sidoCd"] = sido_cd
    if sigungu_cd:
        params["sigunguCd"] = sigungu_cd
        
    try:
        response = requests.get(BASE_URL, params=params, timeout=15)
        if response.status_code != 200:
            st.error(f"주민등록 인구 API 호출 중 오류 발생: {response.status_code}\nURL: {response.url}\nResponse: {response.text}")
            return None
            
        data = response.json()
        
        if "admmSexdAgePpltn" in data:
            items = data["admmSexdAgePpltn"]["item"]
            return pd.DataFrame(items)
        else:
            st.error(f"API 응답에 데이터가 없습니다. (연월/지역 확인 필요)\nResponse: {data}")
            return None
    except Exception as e:
        st.error(f"네트워크 또는 파싱 오류 발생: {e}")
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
