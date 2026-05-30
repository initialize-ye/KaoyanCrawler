"""Find the exact form data format for zydetail.do page."""
import requests
import re

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
})

# Get the zydetail.do page
r = session.get("https://yz.chsi.com.cn/zsml/zydetail.do", timeout=10)
content = r.text

# Find the Vue data/form object
# Look for 'form:' or 'data:' in the Vue instance
print("=== Vue instance data ===")
idx = content.find("data: function ()")
if idx > 0:
    print(content[idx:idx+2000])

# Find all form.xxx references
print("\n=== form.xxx references ===")
form_refs = re.findall(r'form\.(\w+)', content)
print(set(form_refs))

# Find the template section to understand what data is displayed
print("\n=== Template section ===")
template_match = re.search(r'<div[^>]*id="app"[^>]*>([\s\S]*?)<script', content)
if template_match:
    template = template_match.group(1)
    # Find v-model and v-for references
    v_models = re.findall(r'v-model="([^"]+)"', template)
    print(f"v-models: {v_models}")

    # Find table or list references
    tables = re.findall(r'<table[^>]*>([\s\S]*?)</table>', template)
    print(f"Tables found: {len(tables)}")

    # Find any data binding
    bindings = re.findall(r'\{\{([^}]+)\}\}', template)
    print(f"Bindings: {bindings[:20]}")

# The zydetail.do might need specific URL params
# Let's try with query params
print("\n=== Try with query params ===")
urls = [
    "https://yz.chsi.com.cn/zsml/zydetail.do?schId=367880&zydm=081200",
    "https://yz.chsi.com.cn/zsml/zydetail.do?zydm=081200&schId=367880&xxfs=",
]
for url in urls:
    r = session.get(url, timeout=10)
    content = r.text
    # Check if there's different content
    if 'form.' in content:
        form_refs = re.findall(r'form\.(\w+)', content)
        print(f"\n{url.split('?')[1]}: form fields = {set(form_refs)}")

# The key insight: zydetail.do might use the SAME API as index.do
# but with different form data. Let's try the /zsml/rs/zys.do endpoint
# with the exact form fields from the zydetail page
print("\n=== Try /zsml/rs/zys.do with full form data ===")
session.headers.update({
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
    "Referer": "https://yz.chsi.com.cn/zsml/zydetail.do",
})

# Try different form data combinations
test_forms = [
    {"schId": "367880", "zydm": "081200", "xxfs": "", "start": 0, "pageSize": 20, "curPage": 1},
    {"schId": "367880", "zydm": "081200", "xxfs": ""},
    {"dwdm": "10003", "zydm": "081200", "xxfs": ""},
]

for i, form in enumerate(test_forms):
    r = session.post("https://yz.chsi.com.cn/zsml/rs/zys.do", data=form, timeout=10)
    print(f"\nForm {i}: {r.status_code}")
    try:
        result = r.json()
        print(f"  Flag: {result.get('flag')}")
        if result.get("flag"):
            msg = result["msg"]
            print(f"  Total: {msg.get('totalCount')}")
            if msg.get("list"):
                item = msg["list"][0]
                print(f"  Keys: {list(item.keys())}")
                # Look for exam subject fields
                for k, v in item.items():
                    if v is not None and v != "":
                        print(f"  {k}={v}")
    except:
        print(f"  Response: {r.text[:500]}")
