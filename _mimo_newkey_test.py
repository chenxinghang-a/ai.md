import urllib.request, json, sys, ssl

sys.stdout.reconfigure(line_buffering=True)

ctx = ssl.create_default_context()

# Test with new key
api_key = "tp-cbbwbpvooukq1scxluw8qzm04ddrd8kgtebvfd6naz7x24pq"

# Test 1: GET /v1/models
print("=== Test 1: GET /v1/models (new key) ===", flush=True)
try:
    req = urllib.request.Request(
        "https://api.xiaomimimo.com/v1/models",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    resp = urllib.request.urlopen(req, timeout=15, context=ctx)
    print(f"Status: {resp.status}", flush=True)
    print(resp.read().decode()[:800], flush=True)
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")
    print(f"HTTP {e.code}: {body[:500]}", flush=True)
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}", flush=True)

# Test 2: POST chat completions
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
            "Authorization": f"Bearer {api_key}"
        }
    )
    resp = urllib.request.urlopen(req, timeout=30, context=ctx)
    print(f"Status: {resp.status}", flush=True)
    print(resp.read().decode()[:800], flush=True)
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")
    print(f"HTTP {e.code}: {body[:500]}", flush=True)
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}", flush=True)

# Test 3: old key
print("\n=== Test 3: GET /v1/models (old key) ===", flush=True)
old_key = "sk-c5v87e5atqiq0eaasn9lv0qff6gt5ivqak9hilep6yf4ahs4"
try:
    req = urllib.request.Request(
        "https://api.xiaomimimo.com/v1/models",
        headers={"Authorization": f"Bearer {old_key}"}
    )
    resp = urllib.request.urlopen(req, timeout=15, context=ctx)
    print(f"Status: {resp.status}", flush=True)
    print(resp.read().decode()[:800], flush=True)
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")
    print(f"HTTP {e.code}: {body[:500]}", flush=True)
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}", flush=True)
