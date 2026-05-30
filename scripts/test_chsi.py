"""Test script to explore 研招网 API endpoints."""
import requests
import json

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
})

# Visit page first to get cookies
session.get("https://yz.chsi.com.cn/zsml/dw.do", timeout=10)

session.headers.update({
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
    "Referer": "https://yz.chsi.com.cn/zsml/dw.do",
})

# Step 1: Search for institution
data = {
    "dwmc": "北京师范大学",
    "ssdm": "",
    "xxfs": "",
    "dwlxs": ["all"],
    "start": 0,
    "pageSize": 20,
    "curPage": 1,
}
r = session.post("https://yz.chsi.com.cn/zsml/rs/dws.do", data=data, timeout=10)
result = r.json()
school = result["msg"]["list"][0]
sch_id = school["schId"]
sign = school["sign"]
sign2 = school["sign2"]
print(f"School: {school['dwmc']}, ID: {sch_id}, sign: {sign}")

# Step 2: Try different endpoints for program search
endpoints = [
    "/zsml/rs/zyfxs.do",
    "/zsml/rs/zys.do",
    "/zsml/rs/dwzy.do",
    "/zsml/rs/zyfx.do",
    "/zsml/rs/zym.do",
]

for endpoint in endpoints:
    try:
        data2 = {
            "schId": sch_id,
            "sign": sign,
            "xxfs": "",
            "start": 0,
            "pageSize": 20,
            "curPage": 1,
        }
        r2 = session.post(f"https://yz.chsi.com.cn{endpoint}", data=data2, timeout=10)
        print(f"\n{endpoint}: {r2.status_code} ({len(r2.text)} bytes)")
        if r2.status_code == 200:
            print(r2.text[:1500])
    except Exception as e:
        print(f"\n{endpoint}: {e}")
