import sys
import os
sys.path.append(os.getcwd())

from api.fss_api import search_corp_by_name
from api.dart_api import get_dart_corp_info
from api.constants import DATA_GO_KR_SERVICE_KEY, OPEN_DART_API_KEY

def test_enrichment(name):
    print(f"\n=== Testing Enrichment: {name} ===")
    
    # Simulate the logic in app.py
    # 1. Start with name
    res_id = {"brn": "", "crno": "", "api_name": "", "api_ceo": "", "api_addr": ""}
    
    # FSS
    print("Step 1: FSS API")
    fss_res = search_corp_by_name(name, DATA_GO_KR_SERVICE_KEY)
    if fss_res and "_error" not in fss_res:
        res_id["brn"] = fss_res.get("bzno", "")
        res_id["crno"] = fss_res.get("crno", "")
        res_id["api_name"] = fss_res.get("corpNm", "")
        res_id["api_ceo"] = fss_res.get("ceoNm", "")
        res_id["api_addr"] = fss_res.get("enpAddr", "")
        print(f"  FSS Success: {res_id['api_name']}, CEO: {res_id['api_ceo']}")
    else:
        print(f"  FSS Failed: {fss_res.get('_error') if fss_res else 'None'}")

    # DART
    print("Step 2: DART API (Always Enrich)")
    target_name = res_id["api_name"] or name
    dart_info = get_dart_corp_info(target_name, OPEN_DART_API_KEY)
    if dart_info:
        if not res_id["brn"] or "*" in res_id["brn"]:
            res_id["brn"] = dart_info.get("brn", "")
        res_id["crno"] = res_id["crno"] or dart_info.get("crno", "")
        res_id["api_ceo"] = res_id["api_ceo"] or dart_info.get("ceo_nm", "")
        res_id["api_addr"] = res_id["api_addr"] or dart_info.get("addr", "")
        print(f"  DART Success: {dart_info.get('corp_name')}, CEO: {res_id['api_ceo']}, BRN: {res_id['brn']}")
    else:
        print("  DART Failed/No Match")

    print(f"Final Result for {name}: BRN={res_id['brn']}, CEO={res_id['api_ceo']}, CRNO={res_id['crno']}")

if __name__ == "__main__":
    # Test cases reported as problematic
    test_enrichment("LG화학")
    test_enrichment("LIG넥스원")
    test_enrichment("(주)대신라이팅") # User screenshot showed this too
