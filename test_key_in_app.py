import streamlit as st
import requests
from analyzer import get_api_keys

def test():
    keys = get_api_keys()
    if not keys:
        st.error("No keys found")
        return
    
    key = keys[0]
    st.write(f"Testing Key: {key[:8]}...")
    
    urls = [
        f"https://www.googleapis.com/oauth2/v1/userinfo?key={key}",
        f"https://www.googleapis.com/oauth2/v3/userinfo?key={key}",
        f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
    ]
    
    for url in urls:
        st.write(f"URL: {url}")
        try:
            resp = requests.get(url)
            st.write(f"Status: {resp.status_code}")
            st.write(f"JSON: {resp.json() if resp.status_code == 200 else resp.text}")
        except Exception as e:
            st.write(f"Error: {e}")

if __name__ == "__main__":
    test()
