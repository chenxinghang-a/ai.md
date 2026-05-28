"""测试LoomLLM正确用法 — 不改代码，直接用"""
import os
os.environ["GEMINI_API_KEY"] = "AIzaSyC0MMf6fQkQsG5kMj9mDeGSKn0i2imhfik"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7890"
os.environ["HTTP_PROXY"] = "http://127.0.0.1:7890"

from ai_staff_v4 import AIStaff

print("=== LoomLLM from_env ===")
staff = AIStaff.from_env()

print(f"\nMode: {'multi-backend' if staff._multi_mode else 'single-backend'}")
if staff._multi_mode and staff.multi_llm:
    print(f"Backends: {len(staff.backends)}")
    for name, bp in staff.backends.items():
        print(f"  - {name}: {bp.model} ({bp.tier})")

print("\n=== chat test ===")
result = staff.chat("1+1等于几？只回答数字")
print(f"Answer: {result}")
