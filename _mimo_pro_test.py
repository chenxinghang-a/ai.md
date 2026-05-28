"""Test MiMo Pro API with token-plan endpoint"""
import requests
import json

BASE_URL = "https://token-plan-cn.xiaomimimo.com/v1"
API_KEY = "tp-cuvo8bhyg042lw6s0z7kehbkf5fwvtosx8795tk7aw38njlt"

# Test 1: List models
print("=" * 50)
print("Test 1: List models")
try:
    r = requests.get(
        f"{BASE_URL}/models",
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=15
    )
    print(f"Status: {r.status_code}")
    print(f"Body: {r.text[:1000]}")
except Exception as e:
    print(f"Error: {e}")

# Test 2: Chat completion with MiMo-V2.5-Pro
print("\n" + "=" * 50)
print("Test 2: Chat completion")
try:
    r = requests.post(
        f"{BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "MiMo-V2.5-Pro",
            "messages": [{"role": "user", "content": "说一个字"}],
            "max_tokens": 10
        },
        timeout=30
    )
    print(f"Status: {r.status_code}")
    print(f"Body: {r.text[:1000]}")
except Exception as e:
    print(f"Error: {e}")

# Test 3: Try lowercase model name
print("\n" + "=" * 50)
print("Test 3: Lowercase model name")
try:
    r = requests.post(
        f"{BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "mimo-v2.5-pro",
            "messages": [{"role": "user", "content": "说一个字"}],
            "max_tokens": 10
        },
        timeout=30
    )
    print(f"Status: {r.status_code}")
    print(f"Body: {r.text[:1000]}")
except Exception as e:
    print(f"Error: {e}")
