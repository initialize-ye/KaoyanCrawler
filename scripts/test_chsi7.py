"""Try to find the actual search page with exam subjects."""
import requests
import re

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
})

# Try different page URLs
pages = [
    "https://yz.chsi.com.cn/zsml/queryAction.do",
    "https://yz.chsi.com.cn/zsml/query.do",
    "https://yz.chsi.com.cn/zsml/search.do",
    "https://yz.chsi.com.cn/zsml/zyfx.do",
    "https://yz.chsi.com.cn/zsml/index.do",
]

for url in pages:
    try:
        r = session.get(url, timeout=10, allow_redirects=False)
        print(f"{url.split('/')[-1]}: {r.status_code}")
        if r.status_code == 200:
            content = r.text
            if '考试科目' in content or 'kmdm' in content.lower():
                print("  HAS exam subject info!")
            # Look for form fields
            forms = re.findall(r'v-model="form\.([^"]+)"', content)
            if forms:
                print(f"  Form fields: {forms}")
    except Exception as e:
        print(f"{url}: {e}")

# Try the actual working page - maybe it's a different path
# Let me check if there's a page that shows exam subjects for a program
# by looking at the JavaScript bundle
print("\n--- Checking JS bundle for API endpoints ---")
r = session.get("https://t2.chei.com.cn/yz/zsml/assets/pc/js/app.js", timeout=10)
# This is a small loader, but let's check for any additional JS files
content = r.text
# Look for chunk files
chunks = re.findall(r'["\']([^"\']+\.js)["\']', content)
print(f"Chunks: {chunks}")

# Try to find the actual Vue app code
# The dwzy.do page loads the same app.js but might have different inline code
# Let me look at the dwzy.do page more carefully for the getData function
print("\n--- Looking for getData in dwzy.do page ---")
r = session.get("https://yz.chsi.com.cn/zsml/dwzy.do", timeout=10)
content = r.text

# Find ALL function definitions
funcs = re.findall(r'(\w+)\s*:\s*function\s*\(', content)
print(f"Functions found: {funcs}")

# Find any reference to zys.do or dws.do
api_calls = re.findall(r'/zsml/rs/\w+\.do', content)
print(f"API calls: {api_calls}")

# The getData might be in a separate component file
# Let's check if there are any lazy-loaded components
lazy = re.findall(r'import\s*\([^)]+\)', content)
print(f"Lazy imports: {lazy}")

# Check for any data URL patterns
data_urls = re.findall(r'["\']([^"\']*(?:query|search|list|data)[^"\']*)["\']', content)
print(f"Data URLs: {data_urls}")
