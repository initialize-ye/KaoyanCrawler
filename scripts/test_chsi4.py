"""Find exam subject details for a program."""
import requests

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

# Get school
data = {"dwmc": "北京师范大学", "ssdm": "", "xxfs": "", "dwlxs": ["all"], "start": 0, "pageSize": 20, "curPage": 1}
r = session.post("https://yz.chsi.com.cn/zsml/rs/dws.do", data=data, timeout=10)
school = r.json()["msg"]["list"][0]
sch_id = school["schId"]
sign = school["sign"]

# Get programs with yjxkdm=0812
data2 = {
    "schId": sch_id, "sign": sign, "xxfs": "",
    "yjxkdm": "0812", "start": 0, "pageSize": 10, "curPage": 1,
}
r2 = session.post("https://yz.chsi.com.cn/zsml/rs/zys.do", data=data2, timeout=10)
result2 = r2.json()
prog = result2["msg"]["list"][0]

# Now try to find the detail page
# The 研招网 typically uses /zsml/viewAction.do or similar
# Let's try fetching the program detail page directly
zydm = prog["zydm"]
print(f"Program: {zydm}")

# Try different detail URLs
urls_to_try = [
    f"https://yz.chsi.com.cn/zsml/zyfx_search.jsp?zydm={zydm}&schId={sch_id}",
    f"https://yz.chsi.com.cn/zsml/queryAction.do?zydm={zydm}&schId={sch_id}",
    f"https://yz.chsi.com.cn/zsml/viewAction.do?zydm={zydm}&schId={sch_id}",
]

# Also try POST endpoints for detail
post_endpoints = [
    ("/zsml/rs/zyfxs.do", {"schId": sch_id, "sign": sign, "zydm": zydm, "xxfs": "", "start": 0, "pageSize": 20, "curPage": 1}),
    ("/zsml/rs/zyfx.do", {"schId": sch_id, "sign": sign, "zydm": zydm, "xxfs": "", "start": 0, "pageSize": 20, "curPage": 1}),
    ("/zsml/rs/detail.do", {"schId": sch_id, "sign": sign, "zydm": zydm}),
    ("/zsml/rs/kskm.do", {"schId": sch_id, "sign": sign, "zydm": zydm}),
]

for url in urls_to_try:
    try:
        r3 = session.get(url, timeout=10, allow_redirects=False)
        print(f"\nGET {url}: {r3.status_code}")
        if r3.status_code == 200:
            # Look for exam subject info in the page
            content = r3.text
            if "考试科目" in content or "kskm" in content.lower() or "kmdm" in content.lower():
                print("  FOUND exam subject info!")
                # Find relevant section
                idx = content.find("考试科目")
                if idx > 0:
                    print(content[max(0,idx-200):idx+500])
            else:
                print(f"  Content length: {len(content)}")
        elif r3.status_code in (301, 302):
            print(f"  Redirect: {r3.headers.get('Location', '')}")
    except Exception as e:
        print(f"\nGET {url}: {e}")

for ep, params in post_endpoints:
    try:
        r4 = session.post(f"https://yz.chsi.com.cn{ep}", data=params, timeout=10)
        print(f"\nPOST {ep}: {r4.status_code}")
        if r4.status_code == 200:
            text = r4.text
            print(text[:1000])
    except Exception as e:
        print(f"\nPOST {ep}: {e}")
