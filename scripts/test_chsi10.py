"""Find the API that zydetail.do page uses to load exam subject data."""
import requests
import re

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
})

# Get the zydetail.do page
r = session.get("https://yz.chsi.com.cn/zsml/zydetail.do", timeout=10)
content = r.text

# Find all getData or API call functions
print("=== Functions ===")
funcs = re.findall(r'(\w+)\s*:\s*function\s*\(', content)
print(funcs)

# Find getData function
idx = content.find("getData: function")
if idx > 0:
    print("\n=== getData ===")
    print(content[idx:idx+2000])

# Find any API endpoint references
print("\n=== API endpoints ===")
apis = re.findall(r'/zsml/rs/[a-zA-Z]+\.do', content)
print(set(apis))

# Find syncAjax calls
print("\n=== syncAjax calls ===")
calls = re.findall(r"api\.syncAjax\([^)]+\)", content)
for c in calls:
    print(c)

# Find form fields
print("\n=== Form fields ===")
forms = re.findall(r'form\.(\w+)', content)
print(set(forms))

# Find any reference to exam subjects
print("\n=== Exam subject refs ===")
for keyword in ['kskm', 'kmdm', '考试科目', 'subject', 'kscj']:
    if keyword in content:
        idx = content.find(keyword)
        print(f"\n{keyword} at {idx}:")
        print(content[max(0,idx-200):idx+300])
