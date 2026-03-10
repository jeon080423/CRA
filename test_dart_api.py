import sys
import os

# 현재 디렉토리를 경로에 추가하여 api 패키지 임포트 가능하게 함
sys.path.append(os.getcwd())

from api.dart_api import get_unmasked_brn
from api.constants import OPEN_DART_API_KEY as DART_API_KEY

def test_dart():
    test_companies = ["삼성전자", "경현건설", "현대자동차"]
    print(f"Using DART API Key: {DART_API_KEY[:5]}...")
    
    for corp in test_companies:
        print(f"\n--- Testing: {corp} ---")
        brn = get_unmasked_brn(corp, DART_API_KEY)
        if brn:
            print(f"Result for {corp}: {brn} (Length: {len(brn)})")
        else:
            print(f"No result for {corp}")

if __name__ == "__main__":
    test_dart()
