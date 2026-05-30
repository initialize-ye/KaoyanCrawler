"""Test script: find exam subject details (考试科目) endpoint."""
import requests
import json

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
})

session.get("https://yz.chsi.com.cn/zsml/dw.do", timeout=10)
session.headers.update({
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
    "Referer": "https://yz.chsi.com.cn/zsml/dw.do",
})

# Step 1: Get school
data = {"dwmc": "北京师范大学", "ssdm": "", "xxfs": "", "dwlxs": ["all"], "start": 0, "pageSize": 20, "curPage": 1}
r = session.post("https://yz.chsi.com.cn/zsml/rs/dws.do", data=data, timeout=10)
school = r.json()["msg"]["list"][0]
sch_id = school["schId"]
sign = school["sign"]
print(f"School: {sch_id}, sign: {sign}")

# Step 2: Get programs with yjxkdm=0812 (计算机科学与技术)
data2 = {
    "schId": sch_id, "sign": sign, "xxfs": "",
    "yjxkdm": "0812", "start": 0, "pageSize": 100, "curPage": 1,
}
r2 = session.post("https://yz.chsi.com.cn/zsml/rs/zys.do", data=data2, timeout=10)
result2 = r2.json()
programs = result2["msg"]["list"]
print(f"\nFound {len(programs)} programs under 0812:")
for p in programs:
    print(f"  {p['zydm']} {p['zymc']} | {p.get('yjxkdm','')} {p.get('yjxkmc','')} | xwlx={p.get('xwlx','')}")

# Step 3: Try to get exam subjects for a specific program
# The program page URL is typically: /zsml/zyfx_search.jsp?zydm=081200&...
# Let's try different endpoints for exam details
prog = programs[0] if programs else None
if prog:
    print(f"\nTrying to get exam details for {prog['zydm']} {prog['zymc']}...")

    # Try endpoints with program code
    endpoints = [
        f"/zsml/rs/zyfxs.do",
        f"/zsml/rs/kskms.do",
        f"/zsml/rs/detail.do",
    ]

    for ep in endpoints:
        try:
            params = {
                "schId": sch_id,
                "sign": sign,
                "zydm": prog["zydm"],
                "xxfs": "",
                "start": 0,
                "pageSize": 20,
                "curPage": 1,
            }
            r3 = session.post(f"https://yz.chsi.com.cn{ep}", data=params, timeout=10)
            print(f"\n{ep}: {r3.status_code}")
            print(r3.text[:1500])
        except Exception as e:
            print(f"\n{ep}: {e}")

# Step 4: Try the querySchAction endpoint (known from web search)
try:
    params = {
        "ssdm": "11",
        "yjxkdm": "0812",
        "xxfs": "",
        "pageno": "1",
    }
    r4 = session.post("https://yz.chsi.com.cn/zsml/querySchAction.do", data=params, timeout=10)
    print(f"\nquerySchAction: {r4.status_code}")
    print(r4.text[:1500])
except Exception as e:
    print(f"\nquerySchAction: {e}")

# Step 5: Try the zyfx_search.jsp
try:
    r5 = session.get(f"https://yz.chsi.com.cn/zsml/zyfx_search.jsp?zydm=081200&schId={sch_id}", timeout=10)
    print(f"\nzyfx_search.jsp: {r5.status_code}")
    print(r5.text[:2000])
except Exception as e:
    print(f"\nzyfx_search.jsp: {e}")
