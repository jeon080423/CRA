import sys
import os
sys.path.append(os.getcwd())

from api.fss_api import search_corp_by_name
from api.dart_api import get_dart_corp_info
from api.constants import DATA_GO_KR_SERVICE_KEY, OPEN_DART_API_KEY

def test_company(name):
    print(f"\n=== Testing: {name} ===")
    
    # 1. FSS
    print("--- FSS API ---")
    fss_res = search_corp_by_name(name, DATA_GO_KR_SERVICE_KEY)
    if "_error" in fss_res:
        print(f"FSS Error: {fss_res['_error']}")
    else:
        print(f"FSS Found: {fss_res.get('corpNm')} (BRN: {fss_res.get('bzno')}, CRNO: {fss_res.get('crno')})")

    # 2. DART
    print("--- DART API ---")
    dart_res = get_dart_corp_info(name, OPEN_DART_API_KEY)
    if not dart_res:
        print("DART: Not Found")
    else:
        print(f"DART Found: {dart_res.get('corp_name')} (BRN: {dart_res.get('brn')}, CEO: {dart_res.get('ceo_nm')})")

if __name__ == "__main__":
    test_company("LG화학")
    test_company("(주)LG화학")
    test_company("LIG넥스원")
    test_company("LIG넥스원(주)")
