import time
import random
import requests
from bs4 import BeautifulSoup
import urllib.parse
import streamlit as st

def scrape_saramin(region_kw: str, industry_kws: list, max_pages: int = 3) -> list:
    """
    사람인(Saramin) 웹페이지 검색결과를 크롤링하여 회사 이름 목록을 추출합니다.
    IP 차단 방지를 위해 User-Agent 랜더마이징 및 time.sleep()을 적용합니다.
    """
    
    # 1. 키워드 조합 (예: "경기 성남시 제조업")
    # 산업분류가 여러 개일 경우 첫 번째 것만 메인으로 우선 검색하거나, 공백으로 다 붙임
    ind_str = " ".join([kw[:2] for kw in industry_kws[:2]]) if industry_kws else ""
    search_query = f"{region_kw} {ind_str}".strip()
    encoded_query = urllib.parse.quote(search_query)

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    ]

    base_url = "https://www.saramin.co.kr/zf_user/search/company?searchword="

    companies_found = []
    seen_names = set()

    for page in range(1, max_pages + 1):
        url = f"{base_url}{encoded_query}&recruitPage={page}&recruitSort=relation&recruitPageCount=40"
        
        headers = {
            "User-Agent": random.choice(user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.saramin.co.kr/"
        }

        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                print(f"Saramin crawl failed: {resp.status_code}")
                break
                
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # 기업명 추출 (클래스명은 사이트 개편에 따라 달라질 수 있으므로 여러 방향으로 접근)
            # 사람인 '기업 검색' 결과의 회사명 노드들
            corp_elements = soup.select("h2.corp_name a, div.corp_name a, strong.corp_name a, .corp_name")
            
            if not corp_elements:
                # 공고 검색 결과 탭으로 폴백시
                corp_elements = soup.select("div.corp_name > a")
                
            page_found = 0
            for el in corp_elements:
                corp_name = el.get_text(strip=True).replace("(주)", "").replace("㈜", "").strip()
                if corp_name and corp_name not in seen_names and len(corp_name) > 1:
                    seen_names.add(corp_name)
                    # 크롤링한 기초 데이터 구성
                    companies_found.append({
                        "사업장명": corp_name,
                        "출처": "사람인 크롤링",
                        "검색키워드": search_query
                    })
                    page_found += 1
            
            # 검색결과가 통째로 없거나 요소가 잡히지 않으면 중단
            if page_found == 0:
                break
                
            # IP 차단 방지 (Random Sleep 1~3 seconds)
            sleep_time = random.uniform(1.5, 3.5)
            # st.toast(f"사람인 크롤링: {page}페이지 완료 ({page_found}건 발굴). 차단 방지를 위해 {sleep_time:.1f}초 대기합니다...")
            time.sleep(sleep_time)
            
        except Exception as e:
            print(f"Scraper error: {e}")
            break

    return companies_found


def scrape_naver_map(region_kw: str, industry_kw: str, max_count: int = 100) -> list:
    """
    네이버 지도 내부 검색 API를 약간 우회/활용하여 특정 지역의 업종을 크롤링합니다.
    (주의: 과도한 요청 시 차단될 수 있으므로 time.sleep 적용)
    """
    companies = []
    
    # 예: "성남시 제조업"
    query = f"{region_kw} {industry_kw[:3]}"
    encoded_query = urllib.parse.quote(query)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://map.naver.com/v5/search/",
        "Accept": "application/json, text/plain, */*",
    }
    
    page = 1
    # 네이버 지도는 한 번에 20개 내외씩 반환
    while len(companies) < max_count:
        # 네이버 플레이스 검색 API (비공식/웹용)
        url = f"https://map.naver.com/v5/api/search?caller=pc_web&query={encoded_query}&type=all&searchCoord=&page={page}&displayCount=30&isPlaceRecommendationReplace=true&lang=ko"
        
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                print(f"Naver Map Error: {resp.status_code}")
                break
                
            data = resp.json()
            # 결과 배열 경로
            items = data.get("result", {}).get("place", {}).get("list", [])
            
            if not items:
                break
                
            for it in items:
                name = it.get("name", "")
                address = it.get("address", "") or it.get("roadAddress", "")
                if name:
                    companies.append({
                        "사업장명": name,
                        "주소": address,
                        "출처": "네이버 지도 크롤링",
                        "검색키워드": query
                    })
            
            if len(companies) >= max_count:
                break
                
            page += 1
            time.sleep(random.uniform(1.2, 2.5))
            
        except Exception as e:
            print(f"Naver map scraping failed: {e}")
            break
            
    return companies[:max_count]


def scrape_kakao_map(region_kw: str, industry_kw: str, max_count: int = 100) -> list:
    """
    카카오맵(PC 웹) 검색 API를 활용하여 특정 지역의 업종을 크롤링합니다.
    공식 API 키 없이 웹 서비스용 엔드포인트를 사용합니다.
    """
    import json
    import re

    companies = []
    query = f"{region_kw} {industry_kw[:3]}"
    encoded_query = urllib.parse.quote(query)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://map.kakao.com/",
        "Accept": "*/*",
    }
    
    # 카카오맵은 한 페이지에 15개 정도씩 반환 (기본값)
    # 실제 PC웹 호출 구조: https://search.map.kakao.com/mapsearch/map.daum?q=...&msFlag=A&sort=0
    
    try:
        # 1페이지만 우선 호출 (필요시 루프 확장 가능하나 안정성을 위해 1회성 대량 확보 시도)
        url = f"https://search.map.kakao.com/mapsearch/map.daum?q={encoded_query}&msFlag=A&sort=0"
        
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return []
            
        # JSONP 대응 (괄호 제거 및 내부 JSON 추출)
        raw_text = resp.text.strip()
        # 보통 callback(...) 형태로 오거나 순수 JSON으로 올 수 있음
        json_match = re.search(r'^[^(]*\((.*)\)[^)]*$', raw_text, re.DOTALL)
        if json_match:
            json_data = json.loads(json_match.group(1))
        else:
            json_data = json.loads(raw_text)
            
        items = json_data.get("place", [])
        if not items:
            return []
            
        for it in items:
            name = it.get("name", "")
            # address 또는 new_address(도로명)
            address = it.get("address", "") or it.get("new_address", "")
            tel = it.get("tel", "")
            
            if name:
                companies.append({
                    "사업장명": name,
                    "주소": address,
                    "전화번호": tel,
                    "출처": "카카오맵 크롤링",
                    "검색키워드": query
                })
                
        return companies[:max_count]
        
    except Exception as e:
        print(f"Kakao map scraping failed: {e}")
        return []

