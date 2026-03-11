import sys
import os
sys.path.append(os.getcwd())

from api.nts_api import get_nts_business_status
from api.constants import DATA_GO_KR_SERVICE_KEY

def test_nts():
    # Test with some well-known BRNs (public info)
    # LIG Nex1: 215-86-35051
    # LG Chem: 107-81-98139
    test_brns = ["2158635051", "1078198139"]
    
    print(f"Testing NTS API with BRNs: {test_brns}")
    results = get_nts_business_status(test_brns, DATA_GO_KR_SERVICE_KEY)
    
    if not results:
        print("❌ No results returned. Check API key or network.")
        return

    for brn, data in results.items():
        print(f"\nBRN: {brn}")
        print(f"  Status: {data.get('status')}")
        print(f"  Tax Type: {data.get('tax_type')}")
        print(f"  Status Code: {data.get('status_cd')}")

if __name__ == "__main__":
    test_nts()
