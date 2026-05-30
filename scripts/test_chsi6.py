"""Find program detail page with exam subjects."""
import requests
import re

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
data = {"dwmc": "清华大学", "ssdm": "", "xxfs": "", "dwlxs": ["all"], "start": 0, "pageSize": 20, "curPage": 1}
r = session.post("https://yz.chsi.com.cn/zsml/rs/dws.do", data=data, timeout=10)
school = r.json()["msg"]["list"][0]
sch_id = school["schId"]
sign = school["sign"]
print(f"School: {sch_id}")

# Get programs
data2 = {
    "schId": sch_id, "sign": sign, "xxfs": "",
    "yjxkdm": "0812", "start": 0, "pageSize": 5, "curPage": 1,
}
r2 = session.post("https://yz.chsi.com.cn/zsml/rs/zys.do", data=data2, timeout=10)
programs = r2.json()["msg"]["list"]
prog = programs[0]
zydm = prog["zydm"]
print(f"Program: {zydm}")

# Try to find the detail page by checking the actual web page
# The detail page URL might be embedded in the list page as a link
# Let's check the dwzy.do page with the school ID
r3 = session.get(f"https://yz.chsi.com.cn/zsml/dwzy.do?schId={sch_id}&zydm={zydm}", timeout=10)
content = r3.text

# Look for any API endpoint references
api_refs = re.findall(r'/zsml/[a-zA-Z/.]+', content)
print(f"\nAPI refs in dwzy.do: {set(api_refs)}")

# Look for getData or similar function
if 'getData' in content:
    idx = content.find('getData')
    print(f"\ngetData found at {idx}")
    print(content[idx:idx+1000])

# Try the actual program detail page format
# 研招网 might use: /zsml/queryAction.do?ssdm=11&yjxkdm=0812&xxfs=
urls = [
    f"https://yz.chsi.com.cn/zsml/queryAction.do?ssdm=11&yjxkdm=0812",
    f"https://yz.chsi.com.cn/zsml/view?zydm={zydm}&schId={sch_id}",
    f"https://yz.chsi.com.cn/zsml/{zydm}.do",
]

for url in urls:
    try:
        r4 = session.get(url, timeout=10, allow_redirects=False)
        print(f"\nGET {url.split('?')[0].split('/')[-1]}: {r4.status_code}")
        if r4.status_code == 200 and '考试科目' in r4.text:
            print("  FOUND exam subjects!")
    except Exception as e:
        print(f"\nGET {url}: {e}")

# Try the known working endpoint format from dw.do page
# In dw.do, the getData uses api.syncAjax which goes through the api library
# The api library uses polling with taskId
# Let's try the /zsml/ajaxRs.do endpoint which is the task endpoint
try:
    # First submit a task
    task_data = {
        "schId": sch_id,
        "sign": sign,
        "zydm": zydm,
        "xxfs": "",
        "start": 0,
        "pageSize": 20,
        "curPage": 1,
    }
    r5 = session.post("https://yz.chsi.com.cn/zsml/ajaxRs.do", data=task_data, timeout=10)
    print(f"\najaxRs.do: {r5.status_code}")
    print(r5.text[:2000])
except Exception as e:
    print(f"\najaxRs.do: {e}")
