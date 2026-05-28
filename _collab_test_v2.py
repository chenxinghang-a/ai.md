"""
AI-Staff V4 协同测试2 — 测试多种任务类型 + 跨模型协同
"""
import os, sys, time
os.environ["PYTHONIOENCODING"] = "utf-8"

os.environ["GEMINI_API_KEY"] = "AIzaSyC0MMf6fQkQsG5kMj9mDeGSKn0i2imhfik"
os.environ["AI_STAFF_PROXY"] = "http://127.0.0.1:7890"

sys.path.insert(0, os.path.dirname(__file__))

from ai_staff_v4.backends.client import LLMClient
from ai_staff_v4.backends.smart_init import SmartInit
from ai_staff_v4.agents.collab_loop import CollaborationLoop, RouteContext
from ai_staff_v4.experts.registry import ExpertRegistry, ExpertConfig

ExpertRegistry.load_all()

print("=" * 60)
print("  AI-Staff Collab Test V2 - Multi-Task")
print("=" * 60)

# SmartInit
registry = SmartInit.auto_configure(proxy_hint="http://127.0.0.1:7890")
print(f"  Usable: {len(registry.usable_models)}")
for m in registry.usable_models:
    print(f"    - {m.name} ({m.tier}, {m.latency_ms}ms)")

# Create clients
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
        clients[key] = LLMClient(base_url=m.base_url, api_key=api_key, model=m.name, proxy=proxy)

if not clients:
    print("  No clients!")
    sys.exit(1)

collab = CollaborationLoop(clients, registry)

# 多任务测试
tasks = [
    ("Code", "写一个Python装饰器，实现函数执行计时、重试（最多3次）、和结果缓存的组合功能。要求有类型注解和使用示例。"),
    ("Research", "分析2025年AI Agent技术趋势：从AutoGPT到LangGraph到MCP，关键突破点和瓶颈是什么？"),
    ("Direct", "什么是Rust语言的所有权系统？简单解释。"),
]

results = []
for task_type, task in tasks:
    print(f"\n{'='*60}")
    print(f"  [{task_type}] {task[:60]}...")
    print("-" * 60)
    
    t0 = time.time()
    output, stats = collab.run(task)
    elapsed = time.time() - t0
    
    result_line = f"  [{task_type}] status={stats.get('status','?')} score={stats.get('final_score','?')} iter={stats.get('iterations',0)} time={elapsed:.1f}s"
    print(result_line)
    print(f"  Output: {len(output)}ch")
    results.append((task_type, stats, elapsed))

# 汇总
print(f"\n{'='*60}")
print("  SUMMARY")
print("=" * 60)
for task_type, stats, elapsed in results:
    print(f"  {task_type:10s} | {stats.get('status','?'):20s} | score={stats.get('final_score','?')!s:>5s} | {elapsed:.1f}s")
