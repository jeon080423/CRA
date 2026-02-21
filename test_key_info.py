import requests
import sys

def test_api_key(api_key):
    urls = [
        f"https://www.googleapis.com/oauth2/v1/userinfo?key={api_key}",
        f"https://www.googleapis.com/oauth2/v2/userinfo?key={api_key}",
        f"https://www.googleapis.com/oauth2/v3/userinfo?key={api_key}",
        f"https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={api_key}", # Unlikely but test
        f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    ]
    
    for url in urls:
        print(f"Testing URL: {url.replace(api_key, 'REDACTED')}")
        try:
            resp = requests.get(url, timeout=5)
            print(f"Status: {resp.status_code}")
            print(f"Response: {resp.text[:200]}")
            print("-" * 20)
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_api_key(sys.argv[1])
    else:
        print("Usage: python test_key.py <API_KEY>")
