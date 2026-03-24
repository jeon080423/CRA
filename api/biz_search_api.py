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
    g2b_data = get_g2b_corp_info(brn, service_key)
    
    # 2. NPS 정보 (BRN 앞 6자리로 검색 유도)
    nps_results = search_nps_by_name(g2b_data.get("corp_name") or "", service_key, brn[:6])
    nps_data = {}
    if nps_results:
        # 가장 유사한 것 선택 (이름 매칭)
        best_match = nps_results[0]
        # NPS V2 상세조회는 seq(순번)를 사용함
        seq = best_match.get("seq")
        if seq:
            nps_detail = get_nps_detail(seq, service_key)
            if nps_detail:
                nps_data = nps_detail
            
    # 3. NHIS 정보
    nhis_count = get_nhis_subscriber_count(brn, nhis_df=nhis_df)
    
    # 데이터 통합 (우선순위: NPS > G2B)
    unified = {
        "brn": brn,
        "corp_name": nps_data.get("wkplNm") or g2b_data.get("corp_name") or "정보없음",
        "address": nps_data.get("wkplRoadNmDtlAddr") or g2b_data.get("addr") or "정보없음",
        "nps_subscriber": nps_data.get("jnngpCnt", 0),
        "nhis_subscriber": nhis_count if nhis_count else 0,
        "industry": nps_data.get("vldtVlKrnNm") or g2b_data.get("bizType") or "정보없음",
        "tel": g2b_data.get("telno") or "정보없음",
        "corp_size": g2b_data.get("corpSizeNm") or "정보없음",
        "source": []
    }
    
    if nps_data: unified["source"].append("NPS")
    if g2b_data: unified["source"].append("G2B")
    if nhis_count: unified["source"].append("NHIS")
    
    return unified

def batch_search_and_consolidate(sido: str, sigg: str, keyword: str, industry: str, service_key: str, nhis_df: pd.DataFrame = None) -> list[dict]:
    """전체 검색 및 통합 프로세스 실행"""
    all_brns = set()
    
    # 키워드와 다중 업종명(콤마 기준) 통합 검색
    search_terms = []
    if keyword:
        search_terms.append(keyword.strip())
    if industry:
        search_terms.extend([x.strip() for x in industry.split(",") if x.strip()])
        
    for term in search_terms:
        if not term: continue
        # 1. G2B 계약 이력으로 BRN 추출
        g2b_brns = search_g2b_contracts_by_keyword(term, service_key)
        all_brns.update(g2b_brns)
        
        # 2. NPS 업종 검색으로 후보군 추출
        nps_candidates = search_nps_companies_by_keyword(term, service_key)
        # NPS V2는 전체 BRN을 주지 않으므로 이름으로 DART 검색하여 BRN 추출 (가능한 경우)
        from api.constants import OPEN_DART_API_KEY
        from api.dart_api import get_unmasked_brn
        for cand in (nps_candidates or [])[:5]: # 상위 5개만 샘플링
            c_name = cand.get("wkplNm")
            if c_name:
                cand_brn = get_unmasked_brn(c_name, OPEN_DART_API_KEY)
                if cand_brn:
                    all_brns.add(cand_brn.replace("-", ""))
                    
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
