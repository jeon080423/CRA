"""
DART(오픈다트) API 연동 모듈
- 회사명으로 corp_code(고유번호) 검색
- corp_code로 기업개황(사업자등록번호 포함) 조회
"""
import requests
import xml.etree.ElementTree as ET
import zipfile
import io
import os

DART_LIST_URL = "https://opendart.fss.or.kr/api/corpCode.xml"
DART_INFO_URL = "https://opendart.fss.or.kr/api/company.json"

# 고유번호 캐시 (메모리 내 저장)
_CORP_CODE_CACHE = {}

def update_corp_code_cache(api_key: str):
    """DART 전체 고유번호 리스트를 다운로드하여 캐시 업데이트 (ZIP형태 XML)"""
    global _CORP_CODE_CACHE
    if _CORP_CODE_CACHE:
        return True

    params = {"crtfc_key": api_key}
    try:
        resp = requests.get(DART_LIST_URL, params=params, timeout=30)
        resp.raise_for_status()
        
        # ZIP 파일 압축 해제
        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            xml_data = z.read("CORPCODE.xml")
            root = ET.fromstring(xml_data)
            for list_node in root.findall("list"):
                corp_nm = list_node.findtext("corp_name")
                corp_code = list_node.findtext("corp_code")
                if corp_nm and corp_code:
                    _CORP_CODE_CACHE[corp_nm] = corp_code
        return True
    except Exception as e:
        print(f"DART corpCode 캐시 업데이트 실패: {e}")
        return False

def get_dart_corp_info(company_name: str, api_key: str, brn: str = "") -> dict:
    """
    회사명으로 DART에서 기업 정보를 조회 (마스킹 없는 사업자번호, 대표자명, 주소 등 포함)
    brn: 이미 알고 있는 사업자번호 (있으면 결과 검증에 사용)
    """
    if not update_corp_code_cache(api_key):
        return {}

    def _normalize(n):
        return str(n).replace("(주)", "").replace("주식회사", "").replace(" ", "").upper()

    def _brn_clean(b):
        return str(b or "").replace("-", "").replace(" ", "").zfill(10)

    # 1) 정확히 일치하는 상호명 찾기
    corp_code = _CORP_CODE_CACHE.get(company_name)
    
    # 2) 정규화 후 재검색 (공백, (주), 주식회사 등 제거)
    if not corp_code:
        target_norm = _normalize(company_name)
        
        for name, code in _CORP_CODE_CACHE.items():
            if _normalize(name) == target_norm:
                corp_code = code
                break
        
        # 3) 별칭 처리 및 포함 관계 매칭
        if not corp_code:
            alias_norm = target_norm.replace("LIG", "엘아이지")
            for name, code in _CORP_CODE_CACHE.items():
                n_norm = _normalize(name)
                # 양방향 포함 매칭:
                #  - n_norm in target_norm : DART 등록명이 검색어의 일부 (항상 허용)
                #  - target_norm in n_norm : 검색어가 DART 등록명의 일부 (BRN이 있을 때만 허용, 이후 BRN 교차검증으로 오매칭 차단)
                safe_match = n_norm == alias_norm or n_norm in target_norm
                risky_match = brn and (target_norm in n_norm)  # BRN 있을 때만 허용 (v2.2 교차검증이 뒤에서 보호)
                if (safe_match or risky_match) and len(target_norm) >= 3:
                    corp_code = code
                    break

    if not corp_code:
        return {}

    # 4) 기업개황 조회
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code
    }
    try:
        resp = requests.get(DART_INFO_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("status") == "000":
            result = {
                "brn": data.get("bizr_no", ""),
                "crno": data.get("jurir_no", ""),
                "corp_name": data.get("corp_name", ""),
                "ceo_nm": data.get("ceo_nm", ""),
                "addr": data.get("adres", ""),
                "hm_url": data.get("hm_url", ""),
                "induty_code": data.get("induty_code", ""),
                "est_dt": data.get("est_dt", ""),
                "phn_no": data.get("phn_no", ""),
                "source": "DART"
            }
            
            # [v2.2] BRN 교차 검증 - 마스킹 부분 고려 자릿수 비교
            if brn:
                input_brn_clean = _brn_clean(brn)
                dart_brn_clean = _brn_clean(result["brn"])

                # DART BRN이 비어 있거나 전부 0이면 검증 불가 → 통과
                if dart_brn_clean and dart_brn_clean != "0000000000":
                    # 자릿수 단위 비교: 양쪽 모두 '*'가 아닌 위치에서 숫자가 달라야 불일치
                    mismatch = False
                    for ch_input, ch_dart in zip(input_brn_clean, dart_brn_clean):
                        if ch_input != "*" and ch_dart != "*" and ch_input != ch_dart:
                            mismatch = True
                            break
                    if mismatch:
                        # 공개된 자릿수가 하나라도 다르면 다른 업체 → 제외
                        return {}
            
            return result
    except Exception as e:
        print(f"DART 기업개황 조회 실패: {e}")
    
    return {}

def get_unmasked_brn(company_name: str, api_key: str) -> str:
    """하위 호환성을 위한 래퍼"""
    info = get_dart_corp_info(company_name, api_key)
    return info.get("brn", "")
