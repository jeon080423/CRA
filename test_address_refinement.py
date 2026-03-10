import sys
import os
sys.path.append(os.getcwd())

from utils.matcher import clean_address, split_address

def test_addresses():
    test_cases = [
        "(03171) 서울특별시 종로구 세종대로 209",
        "03171 서울특별시 종로구 세종대로 209",
        "서울특별시 종로구 세종대로 209 (03171)",
        "경기도 수원시 팔달구 효원로 1",
        "충청남도 천안시 서북구 번영로 156",
        "부산광역시 해운대구 센텀중앙로 79 (우) 48058",
        "제주특별자치도 제주시 문연로 6",
        "세종특별자치시 도움6로 11",
    ]
    
    print("=== Address Refinement Test ===")
    for addr in test_cases:
        cleaned = clean_address(addr)
        sido, sigungu, rest = split_address(cleaned)
        print(f"\nOriginal: {addr}")
        print(f"  Cleaned: {cleaned}")
        print(f"  Split: Sido='{sido}', Sigungu='{sigungu}', Rest='{rest}'")

if __name__ == "__main__":
    test_addresses()
