"""MiMo API 诊断测试"""
import json
try:
    import urllib.request
    import urllib.error

    url = "https://api.xiaomimimo.com/v1/chat/completions"
    api_key = "sk-c5v87e5atqiq0eaasn9lv0qff6gt5ivqak9hilep6yf4ahs4"

    payload = json.dumps({
        "model": "mimo-v2.5-pro",
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 10
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")

    print(f"Testing: {url}")
    print(f"Model: mimo-v2.5-pro")
    print(f"Key: {api_key[:10]}...{api_key[-6:]}")
    print("---")

    resp = urllib.request.urlopen(req, timeout=30)
    data = json.loads(resp.read().decode("utf-8"))
    print(f"Status: {resp.status} OK")
    print(f"Response: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")

except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")
    print(f"HTTP Error: {e.code} {e.reason}")
    print(f"Body: {body[:1000]}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
