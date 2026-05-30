"""Check zydetail.do and code endpoints."""
import requests
import json

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
})

session.get("https://yz.chsi.com.cn/zsml/index.do", timeout=10)
session.headers.update({
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
    "Referer": "https://yz.chsi.com.cn/zsml/index.do",
})

# Try zydetail.do
print("=== zydetail.do ===")
for method in ["GET", "POST"]:
    params = {"zydm": "081200", "schId": "367880"}
    try:
        if method == "GET":
            r = session.get("https://yz.chsi.com.cn/zsml/zydetail.do", params=params, timeout=10)
        else:
            r = session.post("https://yz.chsi.com.cn/zsml/zydetail.do", data=params, timeout=10)
        print(f"{method}: {r.status_code} ({len(r.text)} bytes)")
        if r.status_code == 200:
            content = r.text
            if '考试科目' in content:
                print("  HAS exam subjects!")
                idx = content.find('考试科目')
                print(content[idx:idx+2000])
            else:
                print(content[:1000])
    except Exception as e:
        print(f"{method}: {e}")

# Try code endpoints
print("\n=== code/autozy.do ===")
try:
    r = session.get("https://yz.chsi.com.cn/zsml/code/autozy.do", params={"q": "计算机"}, timeout=10)
    print(f"Status: {r.status_code}")
    print(r.text[:1000])
except Exception as e:
    print(f"Error: {e}")

print("\n=== code/yjxk/ ===")
try:
    r = session.get("https://yz.chsi.com.cn/zsml/code/yjxk/", timeout=10)
    print(f"Status: {r.status_code}")
    print(r.text[:1000])
except Exception as e:
    print(f"Error: {e}")

print("\n=== code/ml.json ===")
try:
    r = session.get("https://yz.chsi.com.cn/zsml/code/ml.json", timeout=10)
    print(f"Status: {r.status_code}")
    data = r.json()
    for item in data[:5]:
        print(f"  {item}")
except Exception as e:
    print(f"Error: {e}")

# Try searching programs with exam subject filter
print("\n=== Search programs with kmdm (考试科目代码) ===")
data = {
    "zydm": "",
    "zymc": "",
    "mldm": "",
    "yjxkdm": "0812",
    "kmdm": "408",
    "xxfs": "",
    "start": 0,
    "pageSize": 20,
    "curPage": 1,
}
try:
    r = session.post("https://yz.chsi.com.cn/zsml/rs/zys.do", data=data, timeout=10)
    result = r.json()
    print(f"Flag: {result.get('flag')}")
    if result.get("flag"):
        msg = result["msg"]
        print(f"Total: {msg.get('totalCount')}")
        for item in msg.get("list", [])[:5]:
            print(f"  {item.get('zydm')} {item.get('zymc')} | {item.get('yjxkdm')} {item.get('yjxkmc')}")
    else:
        print(f"Msg: {result.get('msg')}")
except Exception as e:
    print(f"Error: {e}")
