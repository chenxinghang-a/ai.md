import urllib.request, json, sys
sys.stdout.reconfigure(line_buffering=True)

# Test 1: GET /v1/models
print("=== Test 1: GET /v1/models ===", flush=True)
try:
    req = urllib.request.Request(
        "https://api.xiaomimimo.com/v1/models",
        headers={"Authorization": "Bearer sk-c5v87e5atqiq0eaasn9lv0qff6gt5ivqak9hilep6yf4ahs4"}
    )
    resp = urllib.request.urlopen(req, timeout=15)
    print(f"Status: {resp.status}", flush=True)
    print(resp.read().decode()[:800], flush=True)
except Exception as e:
    print(f"Error: {e}", flush=True)

# Test 2: POST /v1/chat/completions
print("\n=== Test 2: POST chat completions ===", flush=True)
try:
    payload = json.dumps({
        "model": "mimo-v2.5-pro",
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 10
    }).encode()
    req = urllib.request.Request(
        "https://api.xiaomimimo.com/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer sk-c5v87e5atqiq0eaasn9lv0qff6gt5ivqak9hilep6yf4ahs4"
        }
    )
    resp = urllib.request.urlopen(req, timeout=30)
    print(f"Status: {resp.status}", flush=True)
    print(resp.read().decode()[:800], flush=True)
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}: {e.read().decode()[:500]}", flush=True)
except Exception as e:
    print(f"Error: {e}", flush=True)
