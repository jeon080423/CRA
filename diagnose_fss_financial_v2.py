import sys
import os
import requests

# Add relevant paths
sys.path.append(r"k:\app\1.보고서 분석기")

from api.fss_api import FINA_SUMM_URL, FINA_BS_URL, FINA_IS_URL, search_financial_by_crno

def diagnose_fina_url(name, url, crno, year):
    print(f"--- Diagnosing {name} ---")
    print(f"URL: {url}")
    params = {
        "serviceKey": "DUMMY_KEY", 
        "crno": crno,
        "bizYear": year,
        "numOfRows": 1,
        "resultType": "json"
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        print(f"Status Code: {resp.status_code}")
        if resp.status_code == 200:
            print("Response text (truncated):", resp.text[:200])
        else:
            print("Response error:", resp.text[:200])
    except Exception as e:
        print(f"Error: {e}")

test_crno = "1101111848914" # 가이드북 예제 CRNO
test_year = "2018"

diagnose_fina_url("FSC_FINA_SUMM", FINA_SUMM_URL, test_crno, test_year)
diagnose_fina_url("FSC_FINA_BS", FINA_BS_URL, test_crno, test_year)
diagnose_fina_url("FSC_FINA_IS", FINA_IS_URL, test_crno, test_year)

print("\n--- Testing search_financial_by_crno (with fallback) ---")
res = search_financial_by_crno(test_crno, test_year, "DUMMY_KEY")
print("Result:", res)
