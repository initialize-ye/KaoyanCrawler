"""Explore dwzy.do page to find program detail API."""
import requests
import re

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
})

# Visit dwzy.do page
r = session.get("https://yz.chsi.com.cn/zsml/dwzy.do", timeout=10)
content = r.text

# Find all script src
js_urls = re.findall(r'src="([^"]+\.js[^"]*)"', content)
print("JS files:")
for u in js_urls:
    print(f"  {u}")

# Find all inline scripts with meaningful content
scripts = re.findall(r'<script[^>]*>([\s\S]{50,}?)</script>', content)
print(f"\nInline scripts: {len(scripts)}")
for i, s in enumerate(scripts):
    # Skip analytics
    if 'baidu' in s.lower() or 'google' in s.lower() or 'gtag' in s.lower():
        continue
    print(f"\n--- Script {i} ({len(s)} chars) ---")
    print(s[:2000])

# Also check the page for any Vue component references
# The dwzy.do page might load a component that has the API call
component_refs = re.findall(r'(?:component|mixins|extends)\s*:\s*[a-zA-Z_]+', content)
print(f"\nComponent refs: {component_refs}")

# Look for any data loading in mounted/created hooks
mounted = re.findall(r'(?:mounted|created|beforeMount)\s*:\s*function', content)
print(f"Mounted hooks: {mounted}")
