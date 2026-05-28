import requests
import os
import time

# 清除代理
for k in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"]:
    os.environ.pop(k, None)

url = "https://token-plan-cn.xiaomimimo.com/v1/chat/completions"
headers = {
    "Authorization": "Bearer tp-cgwm1wfaag1xdvbl1q0r36bbdzu1h7sz0p21n03k73qmj6ne",
    "Content-Type": "application/json"
}
data = {
    "model": "mimo-v2.5-pro",
    "messages": [{"role": "user", "content": "say hi"}],
    "max_tokens": 10
}

for i in range(3):
    try:
        print(f"Attempt {i+1}...")
        r = requests.post(url, headers=headers, json=data, timeout=30)
        print(f"  Status: {r.status_code}")
        print(f"  Response: {r.text[:300]}")
    except Exception as e:
        print(f"  Error: {type(e).__name__}: {e}")
    time.sleep(2)
