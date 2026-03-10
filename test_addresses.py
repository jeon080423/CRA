import sys
import os

# 모듈 임포트 경로 추가
sys.path.append(os.getcwd())

from utils.matcher import split_address

test_cases = [
    ("광주광역시 북구", ("광주", "북구", "")),
    ("서울특별시 종로구", ("서울", "종로구", "")),
    ("경기도 수원 팔달", ("경기", "수원시 팔달구", "")),
    ("전라북도 전주 완산", ("전북", "전주시 완산구", "")),
    ("충청남도 천안 동남", ("충남", "천안시 동남구", "")),
    ("강원특별자치도 춘천시", ("강원", "춘천시", "")),
    ("세종특별자치시 한누리대로", ("세종", "", "한누리대로")),
    ("부산광역시 해운대", ("부산", "해운대구", "")),
]

print("--- Address Normalization Test ---")
success_count = 0
for addr, expected in test_cases:
    result = split_address(addr)
    # sido, sigungu, rest
    if result == expected:
        print(f"✅ [PASS] {addr} -> {result}")
        success_count += 1
    else:
        print(f"❌ [FAIL] {addr} -> {result} (Expected: {expected})")

print(f"\nResult: {success_count}/{len(test_cases)} passed.")
