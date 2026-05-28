"""MiMo API 诊断 v3 - 用requests + 代理"""
import sys, os
sys.stdout.reconfigure(line_buffering=True)

try:
    import requests
except ImportError:
    # 用urllib
    print("No requests, trying urllib...")

    import urllib.request, urllib.error, json

    # 先试直连
    url = "https://api.xiaomimimo.com/v1/chat/completions"
    api_key = "sk-c5v87e5atqiq0eaasn9lv0qff6gt5ivqak9hilep6yf4ahs4"

    # 设置代理
    handler = urllib.request.ProxyHandler({
        'http': 'http://127.0.0.1:7890',
        'https': 'http://127.0.0.1:7890'
    })
    opener = urllib.request.build_opener(handler)

    payload = json.dumps({
        "model": "mimo-v2.5-pro",
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 10
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")

    print(f"URL: {url}", flush=True)
    print(f"Model: mimo-v2.5-pro", flush=True)
    print("---", flush=True)

    try:
        resp = opener.open(req, timeout=30)
        body = resp.read().decode("utf-8")
        print(f"OK {resp.status}", flush=True)
        print(body[:500], flush=True)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code}: {body[:500]}", flush=True)
    except Exception as e:
        print(f"ERR: {e}", flush=True)
