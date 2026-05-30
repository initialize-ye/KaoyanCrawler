"""Try the polling API: submit task then poll for results."""
import requests
import json
import time

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
})

# Visit the detail page to get cookies
session.get("https://yz.chsi.com.cn/zsml/zydetail.do", timeout=10)
session.headers.update({
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
    "Referer": "https://yz.chsi.com.cn/zsml/zydetail.do",
})

# Step 1: Submit task via ajaxRs.do
# The form data from the zydetail.do page
task_data = {
    "schId": "367880",  # 清华大学
    "zydm": "081200",   # 计算机科学与技术
    "xxfs": "",
    "curPage": 1,
    "pageSize": 20,
}
print("Submitting task...")
try:
    r = session.post("https://yz.chsi.com.cn/zsml/ajaxRs.do", data=task_data, timeout=10)
    print(f"Status: {r.status_code}")
    result = r.json()
    print(f"Response: {json.dumps(result, ensure_ascii=False, indent=2)[:2000]}")

    task_id = result.get("taskId")
    if task_id:
        print(f"\nTask ID: {task_id}")

        # Step 2: Poll for results
        for i in range(5):
            time.sleep(1)
            print(f"\nPolling attempt {i+1}...")
            poll_r = session.get(
                "https://yz.chsi.com.cn/zsml/asynProgress.do",
                params={"taskId": task_id},
                timeout=10,
            )
            print(f"Status: {poll_r.status_code}")
            poll_result = poll_r.json()
            print(f"Response: {json.dumps(poll_result, ensure_ascii=False, indent=2)[:2000]}")

            if poll_result.get("state") == "SUCCESS":
                # Get the actual results from taskUrl
                task_r = session.get(
                    "https://yz.chsi.com.cn/zsml/ajaxRs.do",
                    params={"taskId": task_id},
                    timeout=10,
                )
                print(f"\nFinal result: {task_r.status_code}")
                print(json.dumps(task_r.json(), ensure_ascii=False, indent=2)[:3000])
                break
except Exception as e:
    print(f"Error: {e}")
