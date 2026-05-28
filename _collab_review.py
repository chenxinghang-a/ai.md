"""让Gemini审查代码，小龙虾改代码 — 真正的人机协同"""
import os, sys, json
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["GEMINI_API_KEY"] = "AIzaSyC0MMf6fQkQsG5kMj9mDeGSKn0i2imhfik"
os.environ["AI_STAFF_PROXY"] = "http://127.0.0.1:7890"
sys.path.insert(0, os.path.dirname(__file__))

from ai_staff_v4.backends.client import LLMClient
from ai_staff_v4.backends.smart_init import SmartInit

# Init
registry = SmartInit.auto_configure(proxy_hint="http://127.0.0.1:7890")
usable = registry.usable_models
print(f"Usable: {len(usable)}")
for m in usable:
    print(f"  {m.name} ({m.tier}, {m.latency_ms}ms)")

best = min([m for m in usable if m.is_free], key=lambda m: m.latency_ms) if [m for m in usable if m.is_free] else min(usable, key=lambda m: m.latency_ms)
print(f"Using: {best.name}")

api_key = ""
for p in registry.providers.values():
    if p.provider == best.provider:
        api_key = p.api_key
        break

client = LLMClient(base_url=best.base_url, api_key=api_key, model=best.name, proxy=registry.proxy or "http://127.0.0.1:7890")

# 读取所有核心文件
files_to_review = [
    "ai_staff_v4/agents/collab_loop.py",
    "ai_staff_v4/backends/client.py",
    "ai_staff_v4/backends/smart_init.py",
    "ai_staff_v4/experts/registry.py",
    "ai_staff_v4/experts/classifier.py",
]

all_code = {}
for f in files_to_review:
    try:
        with open(f, "r", encoding="utf-8") as fh:
            all_code[f] = fh.read()
    except FileNotFoundError:
        pass

print(f"\nReviewing {len(all_code)} files...")

# 构建审查请求
code_blocks = []
for path, code in all_code.items():
    code_blocks.append(f"### {path} ({len(code)} chars)\n```python\n{code}\n```")

prompt = (
    "你是Python代码审查专家。请审查以下AI-Staff V4核心模块代码。\n"
    "重点关注：\n"
    "1. 过度工程/复杂化的地方 — 哪些代码可以删除或大幅简化？\n"
    "2. Bug和逻辑错误\n"
    "3. 性能问题\n\n"
    + "\n\n".join(code_blocks)
    + "\n\n请用JSON格式输出审查结果：\n"
    '{"score": 0-100, "critical_issues": ["严重问题1", ...], '
    '"simplify": [{"file": "文件路径", "what": "简化什么", "how": "怎么简化"}], '
    '"bugs": ["bug1", ...], "overall": "总体评价"}'
)

content, usage = client.chat_completion(
    messages=[{"role": "user", "content": prompt}],
    temperature=0.2, max_tokens=4096,
)

print(f"\n{'='*60}")
print(f"  GEMINI CODE REVIEW")
print(f"{'='*60}")
print(content)
