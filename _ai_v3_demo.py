# -*- coding: utf-8 -*-
"""
AI-Staff V3.0 Demo — auto_run 智能路由实测
验证: 不同任务类型 → 自动选择最优策略
"""
import sys, os

SKILL_DIR = r"C:\Users\cxx\.workbuddy\skills\ai-staff"
sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))

from ai_staff import AIStaff, TaskClassifier

GEMINI_KEY = "AIzaSyC0MMf6fQkQsG5kMj9mDeGSKn0i2imhfik"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
PROXY = "http://127.0.0.1:7890"

print("=" * 70)
print("  AI-Staff V3.0 Demo — 智能路由 (auto_run)")
print("  核心卖点: 不是什么都需要圆桌会议")
print("=" * 70)

staff = AIStaff(
    base_url=GEMINI_URL,
    api_key=GEMINI_KEY,
    model="gemini-2.5-flash",
    proxy=PROXY,
)

# ─── Test 1: 先展示TaskClassifier的分类能力 ───
print("\n" + "─" * 70)
print("  📊 Phase 0: TaskClassifier 分类测试（不调API）")
print("─" * 70)

classifier = TaskClassifier()

test_inputs = [
    ("什么是量子纠缠？", "简单问答 → 应该用direct模式，1个调用搞定"),
    ("帮我写一个Python快速排序算法", "代码任务 → 应该走coder+critic"),
    ("React和Vue该选哪个？给出详细对比分析", "决策辅助 → 应该多专家分析"),
    ("深度分析一下AI Agent的未来发展趋势", "研究任务 → 应该researcher迭代追问"),
]

for inp, expected in test_inputs:
    strategy = classifier.classify(inp)
    print(f"\n  输入: {inp}")
    print(f"  → {classifier.explain(inp, strategy)}")
    print(f"  ✅ 预期: {expected}")

# ─── Test 1: DIRECT模式 — 简单问答 ───
print("\n\n" + "=" * 70)
print("  🧪 Test 1: DIRECT模式 — 简单问答 (应该只调1次API)")
print("=" * 70)

try:
    result1 = staff.auto_run(
        user_input="用一句话解释：什么是递归？给一个生活中的例子。",
        output_dir=os.path.join(os.path.dirname(__file__), "v3_test_direct")
    )
    print(f"\n  状态: {result1.status} | 模式: {result1.strategy_mode} | "
          f"质量: {result1.quality_score}/10 | 耗时: {result1.total_time_sec:.1f}s")
    print(f"  交付物: {list(result1.deliverables.keys())}")
except Exception as e:
    print(f"  [ERROR] {e}")

# ─── Test 2: CODE模式 ───  
print("\n\n" + "=" * 70)
print("  🧪 Test 2: CODE模式 — 写代码+审查 (应该coder→critic两步)")
print("=" * 70)

try:
    result2 = staff.auto_run(
        user_input="写一个Python函数，输入一个列表，返回去重后的列表，保持原始顺序。",
        output_dir=os.path.join(os.path.dirname(__file__), "v3_test_code")
    )
    print(f"\n  状态: {result2.status} | 模式: {result2.strategy_mode} | "
          f"质量: {result2.quality_score}/10 | 耗时: {result2.total_time_sec:.1f}s")
    print(f"  交付物: {list(result2.deliverables.keys())}")
except Exception as e:
    print(f"  [ERROR] {e}")

# ─── Test 3: DECISION模式 ───
print("\n\n" + "=" * 70)
print("  🧪 Test 3: DECISION模式 — 决策辅助 (多专家视角)")
print("=" * 70)

try:
    result3 = staff.auto_run(
        user_input="我想学一门新的编程语言，Python还是Go更值得投入？请从就业、学习曲线、应用场景分析。",
        output_dir=os.path.join(os.path.dirname(__file__), "v3_test_decision")
    )
    print(f"\n  状态: {result3.status} | 模式: {result3.strategy_mode} | "
          f"质量: {result3.quality_score}/10 | 耗时: {result3.total_time_sec:.1f}s")
    print(f"  交付物: {list(result3.deliverables.keys())}")
except Exception as e:
    print(f"  [ERROR] {e}")

print("\n\n" + "=" * 70)
print("  ✅ V3 Demo 完成！检查各输出文件夹查看结构化产出")
print("=" * 70)
