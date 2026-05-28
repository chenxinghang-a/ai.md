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

# 测试我用的key（MEMORY里记录的）
url = "https://token-plan-cn.xiaomimimo.com/v1/chat/completions"
headers = {
    "Authorization": "Bearer tp-cuvo8bhyg042lw6s0z7kehbkf5fwvtosx8795tk7aw38njlt",
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
