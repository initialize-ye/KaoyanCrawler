"""Test script to explore 研招网 API - try different param combos."""
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
print(f"School ID: {sch_id}, sign: {sign}, sign2: {sign2}")

# Step 2: Try /zsml/rs/zys.do with different params
# Based on the dwzy.do page, it might need sign2 or mldm (门类代码)
param_sets = [
    {"schId": sch_id, "sign": sign, "xxfs": "", "start": 0, "pageSize": 20, "curPage": 1},
    {"schId": sch_id, "sign": sign, "sign2": sign2, "xxfs": "", "start": 0, "pageSize": 20, "curPage": 1},
    {"schId": sch_id, "sign": sign2, "xxfs": "", "start": 0, "pageSize": 20, "curPage": 1},
    {"dwdm": "10027", "sign": sign, "xxfs": "", "start": 0, "pageSize": 20, "curPage": 1},
    {"schId": sch_id, "sign": sign, "xxfs": "", "mldm": "08", "start": 0, "pageSize": 20, "curPage": 1},
    {"schId": sch_id, "sign": sign, "xxfs": "", "yjxkdm": "0812", "start": 0, "pageSize": 20, "curPage": 1},
]

for i, params in enumerate(param_sets):
    try:
        r2 = session.post("https://yz.chsi.com.cn/zsml/rs/zys.do", data=params, timeout=10)
        print(f"\nSet {i}: {r2.status_code}")
        resp = r2.text
        print(resp[:800])
    except Exception as e:
        print(f"\nSet {i}: {e}")
