import requests
import json
import os

# 清除代理
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("all_proxy", None)
os.environ.pop("ALL_PROXY", None)

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

try:
    r = requests.post(url, headers=headers, json=data, timeout=30)
    print(f"Status: {r.status_code}")
    print(r.text[:1000])
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
