import requests
import json

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
    r = requests.post(url, headers=headers, json=data, timeout=15, verify=False)
    print(f"Status: {r.status_code}")
    print(r.text[:500])
except Exception as e:
    print(f"Error: {e}")
