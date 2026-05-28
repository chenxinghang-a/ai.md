"""E2E验证：优化后的ai_staff_v4"""
import os, sys, time, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("="*60)
print("  ai_staff_v4 优化后 E2E 验证")
print("="*60)

errors = []

# 1. 导入测试
print("\n[1] 导入测试...")
try:
    from ai_staff_v4.main_mod.staff import AIStaff
    from ai_staff_v4.agents.collab_loop import CollaborationLoop, RouteContext, StructuredFeedback, CollabPhase
    from ai_staff_v4.experts.classifier import TaskClassifier
    from ai_staff_v4.agents.types import TaskState, CollaborationResult
    from ai_staff_v4.main_mod.startup import PROVIDER_TEMPLATES, from_env, quick_start
    print("  ✅ 所有模块导入成功")
except Exception as e:
    print(f"  ❌ 导入失败: {e}")
    errors.append(f"import: {e}")

# 2. TaskState 正确参数
print("\n[2] TaskState 参数测试...")
try:
    ts = TaskState(task_id="test_123")
    assert ts.task_id == "test_123", f"task_id should be 'test_123', got '{ts.task_id}'"
    print("  ✅ TaskState(task_id=...) 正确")
except Exception as e:
    print(f"  ❌ {e}")
    errors.append(f"TaskState: {e}")

# 3. TaskClassifier 统一路由
print("\n[3] 路由统一测试...")
try:
    classifier = TaskClassifier()
    s1 = classifier.classify("1+1等于几")
    assert s1.mode == "direct", f"1+1 should be direct, got {s1.mode}"
    s2 = classifier.classify("用Python写一个快速排序函数")
    assert s2.mode == "code", f"code task should be code, got {s2.mode}"
    s3 = classifier.classify("分析一下量子计算的发展趋势")
    assert s3.mode == "research", f"research should be research, got {s3.mode}"
    print(f"  ✅ 分类: direct={s1.mode}, code={s2.mode}, research={s3.mode}")
except Exception as e:
    print(f"  ❌ {e}")
    errors.append(f"Classifier: {e}")

# 4. CollabLoop 复用 TaskClassifier
print("\n[4] CollabLoop 路由统一测试...")
try:
    loop = CollaborationLoop({}, None)
    ctx1 = loop._auto_route("1+1等于几")
    assert ctx1.task_type == "direct", f"should be direct, got {ctx1.task_type}"
    assert ctx1.needs_review == False, f"direct should not need review"
    ctx2 = loop._auto_route("用Python写一个快速排序函数")
    assert ctx2.task_type == "code", f"should be code, got {ctx2.task_type}"
    assert ctx2.needs_review == True, f"code should need review"
    print(f"  ✅ CollabLoop路由: direct→{ctx1.task_type}(review={ctx1.needs_review}), code→{ctx2.task_type}(review={ctx2.needs_review})")
except Exception as e:
    print(f"  ❌ {e}")
    errors.append(f"CollabLoop route: {e}")

# 5. StructuredFeedback fallback
print("\n[5] StructuredFeedback fallback测试...")
try:
    fb = StructuredFeedback(score=50, passed=False, issues=["测试问题"], suggestions=[], strengths=[])
    prompt = fb.to_revision_prompt()
    assert "测试问题" in prompt, "feedback should contain issue"
    assert "50/100" in prompt, "feedback should contain score"
    print("  ✅ to_revision_prompt() 正常工作")
except Exception as e:
    print(f"  ❌ {e}")
    errors.append(f"StructuredFeedback: {e}")

# 6. Path import in staff.py
print("\n[6] Path导入测试...")
try:
    from ai_staff_v4.main_mod.staff import Path as StaffPath
    print("  ✅ Path 已在 staff.py 中正确导入")
except ImportError:
    # Path是通过 from pathlib import Path 导入的，不能直接from staff import
    # 换种方式验证
    import importlib
    mod = importlib.import_module('ai_staff_v4.main_mod.staff')
    assert hasattr(mod, 'Path'), "staff module should have Path"
    print("  ✅ Path 已在 staff.py 中正确导入")

# 7. startup模块
print("\n[7] startup模块测试...")
try:
    from ai_staff_v4.main_mod.startup import PROVIDER_TEMPLATES
    assert "gemini" in PROVIDER_TEMPLATES, "should have gemini template"
    assert "ollama" in PROVIDER_TEMPLATES, "should have ollama template"
    print(f"  ✅ PROVIDER_TEMPLATES: {list(PROVIDER_TEMPLATES.keys())}")
except Exception as e:
    print(f"  ❌ {e}")
    errors.append(f"startup: {e}")

# 8. router.py bus import
print("\n[8] router.py bus导入测试...")
try:
    from ai_staff_v4.backends.router import ModelRouter
    # 如果bus导入失败，这里会在创建实例时出错
    from ai_staff_v4.backends.profile import BackendProfile
    p = BackendProfile(name="test", base_url="http://test", api_key="k", model="m")
    router = ModelRouter({"test": p})
    print("  ✅ ModelRouter + bus 导入正常")
except Exception as e:
    print(f"  ❌ {e}")
    errors.append(f"Router: {e}")

# 汇总
print("\n" + "="*60)
if errors:
    print(f"  ❌ {len(errors)} 个测试失败:")
    for e in errors:
        print(f"    - {e}")
else:
    print("  ✅ 全部8项测试通过！")
print("="*60)
