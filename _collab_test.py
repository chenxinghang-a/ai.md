"""
AI-Staff V4 协同测试 — 实际跑一轮CollaborationLoop
"""
import os, sys, time
os.environ["PYTHONIOENCODING"] = "utf-8"

# 设置环境变量
os.environ["GEMINI_API_KEY"] = "AIzaSyC0MMf6fQkQsG5kMj9mDeGSKn0i2imhfik"
os.environ["AI_STAFF_PROXY"] = "http://127.0.0.1:7890"

sys.path.insert(0, os.path.dirname(__file__))

from ai_staff_v4.backends.client import LLMClient
from ai_staff_v4.backends.smart_init import SmartInit
from ai_staff_v4.agents.collab_loop import CollaborationLoop, RouteContext
from ai_staff_v4.experts.registry import ExpertRegistry, ExpertConfig

# 🔧 Bug #1: ExpertRegistry 需要先 load_all()
ExpertRegistry.load_all()
print(f"[ExpertRegistry] Loaded: {[e.id for e in ExpertRegistry.list_all()]}")

print("=" * 60)
print("  AI-Staff Collab Live Test")
print("=" * 60)

# Step 1: SmartInit
print("\n[Step 1] SmartInit scan...")
registry = SmartInit.auto_configure(proxy_hint="http://127.0.0.1:7890")

print(f"  Usable: {len(registry.usable_models)}")
for m in registry.usable_models:
    print(f"    - {m.name} ({m.provider}, tier={m.tier}, {m.latency_ms}ms)")

if not registry.usable_models:
    print("  No usable models!")
    sys.exit(1)

# Step 2: Create clients
print("\n[Step 2] Create LLMClients...")
proxy = registry.proxy or "http://127.0.0.1:7890"

clients = {}
for m in registry.usable_models:
    key = m.name.replace('-', '_').replace('.', '')
    api_key = ""
    for p in registry.providers.values():
        if p.provider == m.provider:
            api_key = p.api_key
            break
    if api_key:
        clients[key] = LLMClient(
            base_url=m.base_url,
            api_key=api_key,
            model=m.name,
            proxy=proxy,
        )
        print(f"    OK: {key} -> {m.name}")

if not clients:
    print("  No clients created!")
    sys.exit(1)

# Step 3: Create CollabLoop
print("\n[Step 3] Create CollabLoop...")
collab = CollaborationLoop(clients, registry)

# Step 4: Run test task
test_task = "写一个Python快速排序函数，要求：1)支持自定义比较函数 2)处理边界情况 3)有完整的docstring和类型注解 4)包含3个以上测试用例"

print(f"\n[Step 4] Running collab task...")
print(f"  Task: {test_task}")
print("-" * 60)

t0 = time.time()
output, stats = collab.run(test_task)
elapsed = time.time() - t0

print("\n" + "=" * 60)
print("  RESULTS")
print("=" * 60)
print(f"  Status: {stats.get('status', 'unknown')}")
print(f"  Iterations: {stats.get('iterations', 0)}")
print(f"  Final Score: {stats.get('final_score', 'N/A')}")
print(f"  Time: {elapsed:.1f}s")
print(f"  Writer: {stats.get('writer_model', 'N/A')}")
print(f"  Reviewer: {stats.get('reviewer_model', 'N/A')}")

print("\n-- Output (first 1500 chars) --")
print(output[:1500])
if len(output) > 1500:
    print(f"\n... ({len(output)} chars total)")

# Trace
print("\n-- Trace --")
for entry in collab.get_trace():
    print(f"  [{entry['phase']}] iter={entry['iteration']} model={entry['model']} "
          f"score={entry['feedback_score']}")

print("\nDone!")
