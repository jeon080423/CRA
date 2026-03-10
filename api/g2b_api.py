"""
조달청_나라장터 사용자정보 서비스 연동 모듈
- 사업자등록번호로 조달업체 정보(대표자, 업종, 전화번호 등) 조회
"""
import requests
import xml.etree.ElementTree as ET

G2B_USER_INFO_URL = "http://apis.data.go.kr/1230000/HrcspUserService/getBasisInfo"

def get_g2b_corp_info(brn: str, service_key: str) -> dict:
    """
    사업자등록번호(10자리)로 나라장터 조달업체 정보를 조회
    """
    if not brn or len(brn.replace("-", "")) != 10:
        return {}

    params = {
        "serviceKey": service_key,
        "bizrno": brn.replace("-", ""),
        "type": "json" # JSON 지원 여부 확인 필요 (공공데이터포털은 보통 지원)
    }
    
    try:
        # 1차 시도: JSON
        params["type"] = "json"
        resp = requests.get(G2B_USER_INFO_URL, params=params, timeout=15)
        
        if resp.status_code == 200:
            try:
                data = resp.json()
                body = data.get("response", {}).get("body", {})
                items = body.get("items", [])
                if items:
                    if isinstance(items, dict): items = [items]
                    item = items[0]
                    return _parse_g2b_item(item)
            except:
                # JSON 파싱 실패 시 XML로 fallback
                pass

        # 2차 시도: XML (확장성 대비)
        params["type"] = "xml"
        resp = requests.get(G2B_USER_INFO_URL, params=params, timeout=15)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            item_node = root.find(".//item")
            if item_node is not None:
                item_dict = {child.tag: (child.text or "").strip() for child in item_node}
                return _parse_g2b_item(item_dict)

    except Exception as e:
        print(f"G2B 사용자정보 조회 실패: {e}")
    
    return {}

def _parse_g2b_item(item: dict) -> dict:
    """G2B 응답 데이터를 공통 포맷으로 파싱"""
    return {
        "corp_name": item.get("cmpnyNm") or item.get("corpNm", ""),
        "brn": item.get("bizrno", ""),
        "ceo_nm": item.get("rprsntvNm", ""),
        "addr": item.get("adres", ""),
        "telno": item.get("telno", ""),
        "faxno": item.get("faxno", ""),
        "bizType": item.get("bizType", ""), # 등록업종
        "source": "G2B"
    }
