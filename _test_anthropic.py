import requests
import os

# 清除代理
for k in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "all_proxy", "ALL_PROXY"]:
    os.environ.pop(k, None)

# 测试Anthropic端点
url = "https://token-plan-cn.xiaomimimo.com/anthropic/v1/messages"
headers = {
    "x-api-key": "tp-cgwm1wfaag1xdvbl1q0r36bbdzu1h7sz0p21n03k73qmj6ne",
    "anthropic-version": "2023-06-01",
    "Content-Type": "application/json"
}
data = {
    "model": "mimo-v2.5-pro",
    "max_tokens": 10,
    "messages": [{"role": "user", "content": "hi"}]
}

try:
    r = requests.post(url, headers=headers, json=data, timeout=30)
    print(f"Status: {r.status_code}")
    print(r.text[:1000])
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")

print("\n---\n")

# 测试OpenAI端点（同样的key）
url2 = "https://token-plan-cn.xiaomimimo.com/v1/chat/completions"
headers2 = {
    "Authorization": "Bearer tp-cgwm1wfaag1xdvbl1q0r36bbdzu1h7sz0p21n03k73qmj6ne",
    "Content-Type": "application/json"
}
data2 = {
    "model": "mimo-v2.5-pro",
    "messages": [{"role": "user", "content": "hi"}],
    "max_tokens": 10
}

try:
    r2 = requests.post(url2, headers=headers2, json=data2, timeout=30)
    print(f"Status: {r2.status_code}")
    print(r2.text[:1000])
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
