"""Check index.do page for exam subject info and find the program detail endpoint."""
import requests
import re

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
})

# Check index.do page
r = session.get("https://yz.chsi.com.cn/zsml/index.do", timeout=10)
content = r.text

# Find form fields
forms = re.findall(r'v-model="([^"]+)"', content)
print(f"Form fields: {forms}")

# Find API endpoints
apis = re.findall(r'/zsml/[a-zA-Z/.]+', content)
print(f"API refs: {set(apis)}")

# Find getData function
idx = content.find("getData: function")
if idx > 0:
    print(f"\ngetData found:")
    print(content[idx:idx+2000])

# Find any reference to exam subjects (考试科目, kskm, kmdm)
if '考试科目' in content:
    idx = content.find('考试科目')
    print(f"\n考试科目 found at {idx}:")
    print(content[max(0,idx-500):idx+1000])

# Find any reference to 408
if '408' in content:
    idx = content.find('408')
    print(f"\n408 found at {idx}:")
    print(content[max(0,idx-200):idx+200])
