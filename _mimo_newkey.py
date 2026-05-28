import urllib.request, json, sys, ssl

sys.stdout.reconfigure(line_buffering=True)

ctx = ssl.create_default_context()
api_key = "tp-cbbwbpvooukq1scxluw8qzm04ddrd8kgtebvfd6naz7x24pq"

# Test: POST chat completions with new key
print("Testing new key...", flush=True)
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
    data = json.loads(resp.read().decode())
    with open("c:/Users/cxx/WorkBuddy/Claw/_mimo_result.json", "w", encoding="utf-8") as f:
        json.dump({"status": "ok", "code": resp.status, "data": data}, f, ensure_ascii=False, indent=2)
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")
    with open("c:/Users/cxx/WorkBuddy/Claw/_mimo_result.json", "w", encoding="utf-8") as f:
        json.dump({"status": "error", "code": e.code, "body": body[:500]}, f, ensure_ascii=False, indent=2)
except Exception as e:
    with open("c:/Users/cxx/WorkBuddy/Claw/_mimo_result.json", "w", encoding="utf-8") as f:
        json.dump({"status": "exception", "error": str(e)}, f, ensure_ascii=False, indent=2)
