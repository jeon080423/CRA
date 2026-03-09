import requests

key = "6be75af37c6693a24417c2ed2930e4bd4dd01dddf289552260ce8ce1daf43414"

def test_odcloud():
    url = "https://api.odcloud.kr/api/3049051/v1/uddi:71a6826c-7c86-4b4c-8e90-b61607d40214"
    print(f"--- Testing Odcloud for NHIS (2024) ---")
    
    # 1. Parameter way
    print("Method 1: Query Parameter (serviceKey)")
    resp = requests.get(url, params={"serviceKey": key, "page": 1, "perPage": 1})
    print(f"Status: {resp.status_code}")
    print(f"Body: {resp.text[:200]}\n")
    
    # 2. Header way
    print("Method 2: Header (Authorization: Infra-Key)")
    headers = {"Authorization": f"Infra-Key {key}"}
    resp = requests.get(url, params={"page": 1, "perPage": 1}, headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Body: {resp.text[:200]}\n")

if __name__ == "__main__":
    test_odcloud()
