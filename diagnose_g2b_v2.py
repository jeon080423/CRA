import sys
import os
import requests

# Add relevant paths
sys.path.append(r"k:\app\1.보고서 분석기")

from api.g2b_api import G2B_CORP_INFO_URL, G2B_INST_INFO_URL, G2B_CORP_INDST_URL, G2B_CORP_PRDCT_URL, get_g2b_corp_info

def diagnose_g2b_url(name, url, bizno):
    print(f"--- Diagnosing {name} ---")
    print(f"URL: {url}")
    params = {
        "serviceKey": "DUMMY_KEY", # 실 사용 시 환경변수/설정에서 가져옴
        "bizno": bizno,
        "inqryDiv": "3",
        "type": "json",
        "numOfRows": 1,
        "pageNo": 1
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

test_brn = "6128306057" # 가이드북 예제 BRN

diagnose_g2b_url("PPS_CORP_BASIC", G2B_CORP_INFO_URL, test_brn)
diagnose_g2b_url("PPS_CORP_INDST", G2B_CORP_INDST_URL, test_brn)
diagnose_g2b_url("PPS_CORP_PRDCT", G2B_CORP_PRDCT_URL, test_brn)
diagnose_g2b_url("PPS_INST_INFO", G2B_INST_INFO_URL, test_brn)
