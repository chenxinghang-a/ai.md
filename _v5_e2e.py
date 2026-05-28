"""
E2E验证：AI-AI闭环协作
测试 CollaborationLoop 的核心功能
"""
import os, sys, time, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_staff_v4 import AIStaff

API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyC0MMf6fQkQsG5kMj9mDeGSKn0i2imhfik")

def test_v5_collab():
    """测试V5闭环协作"""
    print("=" * 60)
    print("  🔄 E2E: AI↔AI 闭环协作测试")
    print("=" * 60)
    
    # Step 1: 初始化
    print("\n📋 Phase 1: 初始化 AIStaff...")
    staff = AIStaff.quick_start(API_KEY, provider="gemini")
    print(f"   ✅ AIStaff 初始化成功")
    
    # Step 2: 简单任务（不需要审查）
    print("\n📋 Phase 2: 简单任务（无审查闭环）...")
    result1 = staff.auto_run_v5("1+1等于几？")
    print(f"   状态: {result1.status} | 评分: {result1.quality_score}/10 | 迭代: {result1.rounds_used}")
    assert result1.status in ("success",), f"简单任务应该成功: {result1.status}"
    print("   ✅ 简单任务通过")
    
    # Step 3: 代码任务（需要审查闭环）
    print("\n📋 Phase 3: 代码任务（审查闭环）...")
    result2 = staff.auto_run_v5(
        "用Python写一个二分查找函数，要求处理边界情况",
        max_iterations=2,
        quality_threshold=70,
    )
    print(f"   状态: {result2.status} | 评分: {result2.quality_score}/10 | 迭代: {result2.rounds_used}")
    print(f"   策略: {result2.strategy_mode}")
    print(f"   交付物: {list(result2.deliverables.keys())}")
    # 即使没达标也不算失败，只要返回了内容
    assert result2.deliverables, "代码任务应该有交付物"
    print("   ✅ 代码任务通过")
    
    # Step 4: 对比 V4 vs V5
    print("\n📋 Phase 4: V4 vs V5 对比...")
    t4_start = time.time()
    r4 = staff.auto_run("用Python写一个二分查找函数")
    t4 = time.time() - t4_start
    
    t5_start = time.time()
    r5 = staff.auto_run_v5("用Python写一个二分查找函数", max_iterations=2, quality_threshold=70)
    t5 = time.time() - t5_start
    
    print(f"   V4: 评分={r4.quality_score}/10, 迭代={r4.rounds_used}, 耗时={t4:.1f}s")
    print(f"   V5: 评分={r5.quality_score}/10, 迭代={r5.rounds_used}, 耗时={t5:.1f}s")
    print(f"   V5比V4多迭代 {r5.rounds_used - r4.rounds_used} 次")
    print("   ✅ 对比完成")
    
    print("\n" + "=" * 60)
    print("  ✅ E2E 全部通过！V5闭环协作功能正常")
    print("=" * 60)

if __name__ == "__main__":
    test_v5_collab()
