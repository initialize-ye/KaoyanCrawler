"""Search all schools for CS programs and find exam subject details."""
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

# Search programs by yjxkdm (计算机科学与技术) without school filter
# This is the index.do page search, not the dw.do page
data = {
    "zydm": "",
    "zymc": "",
    "mldm": "",
    "yjxkdm": "0812",
    "xxfs": "",
    "start": 0,
    "pageSize": 20,
    "curPage": 1,
}
r = session.post("https://yz.chsi.com.cn/zsml/rs/zys.do", data=data, timeout=10)
result = r.json()
print(f"Flag: {result.get('flag')}")
if result.get("flag"):
    msg = result["msg"]
    print(f"Total: {msg.get('totalCount')}")
    print(f"Total pages: {msg.get('totalPage')}")
    for item in msg.get("list", [])[:10]:
        # Print all keys to understand the data structure
        print(f"\n  Keys: {list(item.keys())}")
        print(f"  zydm={item.get('zydm')} zymc={item.get('zymc')}")
        print(f"  dwmc={item.get('dwmc')} dwdm={item.get('dwdm')}")
        print(f"  yjxkdm={item.get('yjxkdm')} yjxkmc={item.get('yjxkmc')}")
        print(f"  xwlx={item.get('xwlx')} xxfs={item.get('xxfs')}")
        # Check for exam subject fields
        for k in item.keys():
            if 'km' in k.lower() or 'subject' in k.lower() or 'ks' in k.lower():
                print(f"  {k}={item.get(k)}")
else:
    print(f"Error: {result.get('msg')}")
