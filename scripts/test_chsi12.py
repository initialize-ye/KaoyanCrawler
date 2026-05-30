"""Find the API endpoint that zydetail.do uses to load exam data."""
import requests
import re

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
})

# Get the zydetail.do page
r = session.get("https://yz.chsi.com.cn/zsml/zydetail.do", timeout=10)
content = r.text

# Find ALL inline scripts
scripts = re.findall(r'<script[^>]*>([\s\S]{30,}?)</script>', content)
print(f"Found {len(scripts)} scripts")

for i, s in enumerate(scripts):
    if 'baidu' in s.lower() or 'google' in s.lower() or 'gtag' in s.lower():
        continue
    if len(s) < 50:
        continue
    print(f"\n=== Script {i} ({len(s)} chars) ===")
    # Look for API calls
    if 'api.' in s or 'ajax' in s or 'syncAjax' in s or '/zsml/' in s:
        print("  CONTAINS API CALL!")
    print(s[:3000])

# Also look for the getData function specifically
print("\n=== Looking for getData ===")
idx = content.find("getData")
while idx >= 0:
    context = content[max(0,idx-50):idx+200]
    if 'function' in context or 'function' in content[idx:idx+100]:
        print(f"\nat {idx}:")
        print(content[idx:idx+500])
    idx = content.find("getData", idx+1)

# Look for syncAjax or api.post or api.get
print("\n=== Looking for API patterns ===")
for pattern in ['syncAjax', 'api.post', 'api.get', '/zsml/rs/', 'taskUrl']:
    indices = [m.start() for m in re.finditer(re.escape(pattern), content)]
    for idx in indices:
        print(f"\n{pattern} at {idx}:")
        print(content[max(0,idx-100):idx+300])
