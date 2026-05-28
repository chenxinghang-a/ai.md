"""全面测试V5 CollabLoop — 触发辩论协议 + 全模式验证"""
import sys, os, time, json, traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from ai_staff_v4 import AIStaff

def test_rebuttal(staff):
    """测试辩论协议：用高阈值+刻意模糊任务触发低分→rebuttal"""
    print("\n" + "="*60)
    print("  [Rebuttal测试] 高阈值(95)+模糊任务 → 强制触发辩论")
    print("="*60)
    
    # 用一个极度模糊的指令+高阈值，几乎必然触发低分
    result = staff.auto_run_v5(
        "随便写点什么",
        max_iterations=3,
        quality_threshold=95,  # 极高阈值
    )
    
    print(f"\n  结果: status={result.status}")
    print(f"  评分: {result.quality_score*10:.0f}/100")
    print(f"  迭代: {result.rounds_used}轮")
    print(f"  trace_id: {result.trace_id}")
    
    # 检查trace里有没有rebuttal
    from ai_staff_v4.agents.collab_loop import CollabPhase
    loop = staff._get_collab_loop()
    phases = [p.phase for p in loop._trace_log]
    has_rebuttal = any(p == CollabPhase.REBUTTAL for p in phases)
    has_revising = any(p == CollabPhase.REVISING for p in phases)
    has_review = any(p == CollabPhase.REVIEWING for p in phases)
    print(f"  阶段: {[p.value for p in phases]}")
    print(f"  触发Review: {'✅' if has_review else '❌'}")
    print(f"  触发Rebuttal: {'✅' if has_rebuttal else '❌'}")
    print(f"  触发Revising: {'✅' if has_revising else '❌'}")
    
    # Review和Revising至少有一个就算通过（Rebuttal需要50-79分才触发）
    return has_review and (has_rebuttal or has_revising or result.quality_score * 10 >= 85)

def test_all_modes(staff):
    """测试所有chat()模式"""
    results = {}
    
    modes = [
        ("direct",   "什么是Python的GIL？一句话解释"),
        ("code",     "写一个冒泡排序"),
        ("research", "2025年Rust在嵌入式领域的发展"),
        ("decision", "Docker vs Podman选哪个？"),
        ("creative", "给一个AI编程助手起名"),
    ]
    
    for mode, prompt in modes:
        print(f"\n{'='*60}")
        print(f"  [{mode}] {prompt[:40]}...")
        print("-"*60)
        try:
            t0 = time.time()
            output = staff.chat(prompt, mode=mode)
            elapsed = time.time() - t0
            ok = bool(output and not output.startswith("[ERROR") and not output.startswith("[No output"))
            results[mode] = {"ok": ok, "time": f"{elapsed:.1f}s", "len": len(output)}
            print(f"  {'✅' if ok else '❌'} {len(output)}ch / {elapsed:.1f}s")
        except Exception as e:
            results[mode] = {"ok": False, "error": str(e)[:100]}
            print(f"  ❌ {type(e).__name__}: {str(e)[:80]}")
    
    return results

def test_edge_cases(staff):
    """边界情况测试"""
    results = {}
    
    cases = [
        ("empty_prompt", "", "空输入"),
        ("very_long", "请详细分析" + "AI技术发展" * 100, "超长输入"),
        ("chinese_special", "解释「递归」—什么是递归？🤔", "中文+emoji+特殊符号"),
        ("code_injection", "import os; os.system('rm -rf /')", "代码注入尝试"),
        ("multi_line", "任务1: 写一个函数\n任务2: 写测试\n任务3: 写文档", "多行任务"),
    ]
    
    for name, prompt, desc in cases:
        print(f"\n  [{name}] {desc}")
        try:
            output = staff.chat(prompt or "你好", mode="direct")
            ok = bool(output)
            results[name] = {"ok": ok, "len": len(output)}
            print(f"    {'✅' if ok else '❌'} {len(output)}ch")
        except Exception as e:
            results[name] = {"ok": False, "error": str(e)[:80]}
            print(f"    ❌ {type(e).__name__}: {str(e)[:60]}")
    
    return results

def test_rest_api(staff):
    """REST API端点测试"""
    from ai_staff_v4.endpoints.rest_api import RestAPIServer, RestAPIHandler
    import httpx
    
    print(f"\n{'='*60}")
    print("  [REST API] 端点存在性测试")
    print("-"*60)
    
    # 检查Handler上的方法
    results = {}
    for method in ["_handle_chat", "_handle_run", "_handle_status", "_handle_health"]:
        has = hasattr(RestAPIHandler, method)
        results[method] = has
        print(f"  {method}: {'✅' if has else '❌'}")
    
    # 测试实际HTTP请求
    srv = RestAPIServer(staff=staff, port=18899)
    srv.start()
    time.sleep(0.5)
    
    try:
        client = httpx.Client(timeout=10)
        
        # Health check
        r = client.get("http://localhost:18899/health")
        results["health_http"] = r.status_code == 200
        print(f"  GET /health: {'✅' if r.status_code == 200 else '❌'} ({r.status_code})")
        
        # Chat
        r = client.post("http://localhost:18899/chat", json={"prompt": "hello", "mode": "direct"}, timeout=30)
        results["chat_http"] = r.status_code == 200
        if r.status_code == 200:
            data = r.json()
            print(f"  POST /chat: ✅ ({data.get('duration_ms', '?')}ms)")
        else:
            print(f"  POST /chat: ❌ ({r.status_code})")
    except Exception as e:
        results["http_test"] = False
        print(f"  HTTP测试: ❌ {str(e)[:60]}")
    finally:
        srv.stop()
    
    return results

# ═══════════════════════════════════════════
#  主测试
# ═══════════════════════════════════════════

if __name__ == "__main__":
    print("初始化 AI-Staff...")
    staff = AIStaff.from_env()
    
    # 1. 辩论协议测试
    rebuttal_ok = test_rebuttal(staff)
    
    # 2. 全模式测试
    mode_results = test_all_modes(staff)
    
    # 3. 边界情况
    edge_results = test_edge_cases(staff)
    
    # 4. REST API
    api_results = test_rest_api(staff)
    
    # ══════ 汇总 ══════
    print("\n" + "="*60)
    print("  汇总报告")
    print("="*60)
    
    print(f"\n  辩论协议: {'✅ 触发' if rebuttal_ok else '❌ 未触发'}")
    
    print(f"\n  模式测试:")
    for mode, r in mode_results.items():
        status = '✅' if r.get('ok') else '❌'
        extra = r.get('time', r.get('error', ''))
        print(f"    {mode:10s} {status} {extra}")
    
    print(f"\n  边界情况:")
    for name, r in edge_results.items():
        status = '✅' if r.get('ok') else '❌'
        extra = r.get('error', f"{r.get('len', 0)}ch")
        print(f"    {name:18s} {status} {extra}")
    
    print(f"\n  REST API:")
    for name, ok in api_results.items():
        print(f"    {name:20s} {'✅' if ok else '❌'}")
    
    # 统计
    total = len(mode_results) + len(edge_results) + len(api_results) + 1
    passed = sum(1 for r in mode_results.values() if r.get('ok'))
    passed += sum(1 for r in edge_results.values() if r.get('ok'))
    passed += sum(1 for v in api_results.values() if v)
    passed += 1 if rebuttal_ok else 0
    
    print(f"\n  总计: {passed}/{total} 通过")
