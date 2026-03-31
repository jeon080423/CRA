import requests
import json
import concurrent.futures
import pandas as pd
from .nps_api import search_nps_by_name, get_nps_detail, NPS_FIELD_LABELS
from .g2b_api import get_g2b_corp_info, G2B_FIELD_LABELS
from .nhis_api import get_nhis_subscriber_count
from analyzer import run_analysis
import streamlit as st

# G2B Contract API Endpoints
G2B_CONTRACT_SERVICE_URL = "http://apis.data.go.kr/1230000/CntrtcInfoService02/getServcContractInfoListByStndrd10"
G2B_CONTRACT_GOODS_URL   = "http://apis.data.go.kr/1230000/CntrtcInfoService02/getThngContractInfoListByStndrd10"

SIDO_LIST = ["전체", "서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시", "대전광역시", "울산광역시", "세종특별자치시", "경기도", "강원특별자치도", "충청북도", "충청남도", "전북특별자치도", "전라남도", "경상북도", "경상남도", "제주특별자치도"]

def get_ai_industry_suggestions(keyword: str) -> list[str]:
    """Gemini를 사용하여 키워드와 관련된 공식 업종명 제안"""
    prompt = f"""
    사용자가 입력한 검색 키워드: "{keyword}"
    이 키워드와 관련하여 한국표준산업분류(KSIC) 또는 나라장터에서 주로 사용되는 공식 업종명 5개를 제안해줘.
    결과는 반드시 JSON 리스트 형식으로만 출력해. 예: ["업종명1", "업종명2", ...]
    """
    res, err = run_analysis("{report_text}", prompt, auto_mode=True)
    if err:
        return []
    
    try:
        # JSON 부분만 추출
        start = res.find("[")
        end = res.rfind("]") + 1
        if start != -1 and end != -1:
            return json.loads(res[start:end])
    except:
        pass
    return []

def search_g2b_contracts_by_keyword(keyword: str, service_key: str) -> list[str]:
    """나라장터 계약 정보를 검색하여 관련 업체의 사업자번호(BRN) 리스트 반환"""
    brns = set()
    
    # 최근 2년 데이터 검색 (간략화를 위해 최근 100건만 샘플링)
    params = {
        "ServiceKey": service_key,
        "type": "json",
        "numOfRows": 50,
        "pageNo": 1,
        "cntrctNm": keyword # 계약명 검색
    }
    
    for url in [G2B_CONTRACT_SERVICE_URL, G2B_CONTRACT_GOODS_URL]:
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("response", {}).get("body", {}).get("items", [])
                if isinstance(items, dict): items = [items]
                for item in items:
                    # 업체 사업자번호 추출 (mainEntrpsBizno 또는 유사 필드)
                    bizno = item.get("mainEntrpsBizno") or item.get("bizno")
                    if bizno:
                        brns.add(bizno.replace("-", ""))
        except:
            continue
            
    return list(brns)

def search_nps_companies_by_keyword(keyword: str, service_key: str) -> list[dict]:
    """NPS에서 키워드/업종명으로 업체 검색"""
    # NPS Search V2 API를 활용하여 이름으로 검색
    results = search_nps_by_name(keyword, service_key)
    return results

def get_unified_corp_info(brn: str, service_key: str, nhis_df: pd.DataFrame = None) -> dict:
    """여러 기관의 정보를 통합하여 하나의 딕셔너리로 반환"""
    # 1. G2B 정보
    from api.g2b_api import get_g2b_corp_info
    g2b_data = get_g2b_corp_info(brn, service_key)
    
    # 2. NPS 정보 (BRN 앞 6자리로 검색 유도 및 본사 우선 탐색)
    from api.nps_api import search_and_match_nps
    nps_data = search_and_match_nps(g2b_data.get("corp_name") or "", brn, service_key)
            
    # 3. NHIS 정보
    nhis_count = get_nhis_subscriber_count(brn, nhis_df=nhis_df)
    
    corp_name_raw = nps_data.get("wkplNm") or g2b_data.get("corp_name") or "정보없음"
    clean_corp_name = corp_name_raw.split("/")[0].strip() if corp_name_raw != "정보없음" else "정보없음"
    
    # 기본 데이터 통합
    tel = g2b_data.get("telno") or g2b_data.get("telNo") or ""
    sources = []
    
    if nps_data: sources.append("NPS")
    if g2b_data: sources.append("G2B")
    if nhis_count: sources.append("NHIS")
    
    # 전화번호 보완 (DART)
    if not tel or tel == "정보없음":
        from api.constants import OPEN_DART_API_KEY
        from api.dart_api import get_dart_corp_info
        if clean_corp_name != "정보없음":
            dart_data = get_dart_corp_info(clean_corp_name, OPEN_DART_API_KEY, brn=brn)
            tel = dart_data.get("phn_no") or "정보없음"
            if tel != "정보없음":
                sources.append("DART")
        else:
            tel = "정보없음"
            
    # 웹크롤링 보완 (혁신적인 방법 - Naver 검색결과 등에서 추출)
    if not tel or tel == "정보없음":
        if clean_corp_name != "정보없음":
            crawled_tel = scrap_phone_from_web(clean_corp_name)
            if crawled_tel:
                tel = crawled_tel
                sources.append("WebCrawling")
            
    unified = {
        "brn": brn,
        "corp_name": clean_corp_name,
        "address": nps_data.get("wkplRoadNmDtlAddr") or g2b_data.get("addr") or "정보없음",
        "nps_subscriber": nps_data.get("jnngpCnt", 0),
        "nhis_subscriber": nhis_count if nhis_count else 0,
        "industry": nps_data.get("vldtVlKrnNm") or g2b_data.get("bizType") or "정보없음",
        "tel": tel,
        "corp_size": g2b_data.get("corpSizeNm") or "정보없음",
        "source": ", ".join(sources) if sources else "정보없음"
    }
    
    return unified

def scrap_phone_from_web(company_name: str) -> str:
    """네이버 검색을 통해 중소기업의 전화번호를 동적으로 크롤링하여 추출"""
    import urllib.parse
    import re
    from bs4 import BeautifulSoup
    
    query = urllib.parse.quote(f"{company_name} 전화번호")
    url = f"https://search.naver.com/search.naver?query={query}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # 플레이스 (지도) 영역 혹은 네이버 지식스니펫의 전화번호 탐색
            # 클래스명은 네이버 검색결과 구조에 따라 자주 변하지만, 일반적으로 span이나 div 텍스트에 들어있음
            # 정규표현식으로 전화번호 패턴 추출 (대표번호, 지역번호 등)
            phone_pattern = re.compile(r'(\d{2,3}-\d{3,4}-\d{4})')
            
            # 먼저 강조된 전화번호 텍스트 (플레이스 영역 등) 탐색 시도
            texts = soup.get_text()
            matches = phone_pattern.findall(texts)
            if matches:
                # 너무 많은 매치가 있을 수 있으니 가장 먼저 노출된 혹은 빈도수 높은 번호를 선정
                # 간단히 첫 번째 매칭 반환
                for match in matches:
                    # 렌덤한 날짜 정보 제외
                    if not match.startswith("202"):
                        return match
                        
    except Exception as e:
        print(f"Web scraping error for {company_name}: {e}")
        pass
        
    return ""

def batch_search_and_consolidate(sido: str, sigg: str, keyword: str, industry: str, service_key: str, nhis_df: pd.DataFrame = None) -> list[dict]:
    """전체 검색 및 통합 프로세스 실행"""
    all_brns = set()
    
    # 키워드와 다중 업종명(콤마 기준) 통합 검색
    search_terms = []
    if keyword:
        search_terms.append(keyword.strip())
    if industry:
        search_terms.extend([x.strip() for x in industry.split(",") if x.strip()])
        
    # 0. NHIS 캐시(건강보험공단업체) 기반 지역 우선 검색
    if nhis_df is not None and not nhis_df.empty and "_brn" in nhis_df.columns:
        regional_df = nhis_df.copy()
        
        # 1-1. 주소 기반 필터링 (주소 관련 컬럼 자동 탐지)
        addr_cols = [c for c in regional_df.columns if "주소" in c or "addr" in c.lower()]
        addr_col = addr_cols[0] if addr_cols else None
        
        if addr_col:
            if sido != "전체":
                regional_df = regional_df[regional_df[addr_col].str.contains(sido, na=False)]
            if sigg != "전체":
                regional_df = regional_df[regional_df[addr_col].str.contains(sigg, na=False)]
        
        # 1-2. 키워드/업종 기반 추가 필터링
        for term in search_terms:
            if not term: continue
            # 사업장명 검색
            mask = regional_df["사업장명"].str.contains(term, na=False, case=False)
            
            # 업종 관련 컬럼 검색 (있을 경우)
            ind_cols = [c for c in regional_df.columns if "업종" in c]
            for ic in ind_cols:
                mask = mask | regional_df[ic].astype(str).str.contains(term, na=False, case=False)
                
            matches = regional_df[mask]
            for b in matches["_brn"].dropna().tolist():
                all_brns.add(str(b).zfill(10))
    
    # 2. 결과가 부족하거나 캐시가 없을 경우 기동하는 Fallback (NPS, G2B API)
    if len(all_brns) < 10 or not (nhis_df is not None and not nhis_df.empty):
        for term in search_terms:
            if not term: continue
            
            # NPS 업종 검색으로 후보군 추출
            nps_candidates = search_nps_companies_by_keyword(term, service_key)
            from api.constants import OPEN_DART_API_KEY
            from api.dart_api import get_unmasked_brn
            
            for cand in (nps_candidates or [])[:10]:
                c_name = cand.get("wkplNm")
                # NPS 결과가 사용자가 선택한 지역과 너무 동떨어졌다면 스킵 (가벼운 필터링)
                cand_addr = cand.get("wkplRoadNmDtlAddr") or cand.get("wkplRoadNmAddr") or ""
                if sido != "전체" and sido not in cand_addr:
                    continue
                    
                if c_name:
                    clean_name = c_name.split("/")[0].strip()
                    cand_brn = get_unmasked_brn(clean_name, OPEN_DART_API_KEY)
                    if cand_brn:
                        all_brns.add(cand_brn.replace("-", ""))
                        
            # G2B 계약 이력으로 BRN 추출
            g2b_brns = search_g2b_contracts_by_keyword(term, service_key)
            all_brns.update(g2b_brns)
                    
    # 3. 통합 정보 수집 (병렬 처리)
    # 실무적으로는 모든 BRN에 대해 다 하는 것보다 상위 N개만 처리
    brn_list = list(all_brns)[:50] # 샘플링 증가
    
    final_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(get_unified_corp_info, brn, service_key, nhis_df) for brn in brn_list]
        for f in concurrent.futures.as_completed(futures):
            try:
                info = f.result()
                # 시도 및 시군구 필터링
                addr = info.get("address", "")
                sido_match = (sido == "전체" or sido in addr)
                sigg_match = (sigg == "전체" or sigg in addr)
                if sido_match and sigg_match:
                    final_results.append(info)
            except:
                continue
                
    return final_results
