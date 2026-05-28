"""AI-Staff V4 快速验证测试 — 验证本次修复的所有改动"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_import():
    """1. 基础导入"""
    from ai_staff_v4 import AIStaff
    from ai_staff_v4.agents.types import CollaborationResult
    from ai_staff_v4.agents.collab_loop import CollaborationLoop
    print("[OK] import")

def test_chat_signature():
    """2. chat()签名含return_details参数"""
    from ai_staff_v4 import AIStaff
    import inspect
    sig = inspect.signature(AIStaff.chat)
    params = list(sig.parameters.keys())
    assert "return_details" in params, f"return_details not in {params}"
    assert sig.parameters["return_details"].default == False
    print("[OK] chat(return_details=False) param exists")

def test_collaboration_result_fields():
    """3. CollaborationResult含total_tokens和trace_id"""
    from ai_staff_v4.agents.types import CollaborationResult
    r = CollaborationResult(
        goal="test", status="success", strategy_mode="direct",
        trace_id="abc123", total_tokens=500,
    )
    assert r.total_tokens == 500
    assert r.trace_id == "abc123"
    assert hasattr(r, 'deliverables')
    assert hasattr(r, 'quality_score')
    print("[OK] CollaborationResult fields complete")

def test_call_with_fallback_returns_3tuple():
    """4. _call_with_fallback返回3元组(content, model, tokens)"""
    from ai_staff_v4.agents.collab_loop import CollaborationLoop
    import inspect
    # 检查返回值注解
    src = inspect.getsource(CollaborationLoop._call_with_fallback)
    assert "tuple[str, str, int]" in src, "Return type should be tuple[str, str, int]"
    print("[OK] _call_with_fallback returns 3-tuple")

def test_collab_loop_run_stats_has_tokens():
    """5. collab_loop.run()返回的stats含total_tokens"""
    from ai_staff_v4.agents.collab_loop import CollaborationLoop
    import inspect
    src = inspect.getsource(CollaborationLoop.run)
    assert '"total_tokens"' in src, "run() stats should include total_tokens"
    print("[OK] collab_loop.run() stats include total_tokens")

def test_auto_run_v5_sets_tokens():
    """6. auto_run_v5()填充total_tokens从collab_stats"""
    from ai_staff_v4 import AIStaff
    import inspect
    src = inspect.getsource(AIStaff.auto_run_v5)
    assert 'collab_stats.get("total_tokens"' in src, "auto_run_v5 should read total_tokens from collab_stats"
    print("[OK] auto_run_v5 reads total_tokens from collab_stats")

def test_extract_text():
    """7. _extract_text方法存在"""
    from ai_staff_v4 import AIStaff
    assert hasattr(AIStaff, '_extract_text'), "_extract_text method missing"
    print("[OK] _extract_text method exists")

def test_chat_simple_task_fast_path():
    """8. chat()对direct任务走快速路径（不进V5闭环）"""
    from ai_staff_v4 import AIStaff
    import inspect
    src = inspect.getsource(AIStaff.chat)
    # 检查快速路径逻辑
    assert "strategy.mode == \"direct\"" in src, "Should have fast path for direct tasks"
    assert "chat_single" in src, "Should call chat_single for fast path"
    print("[OK] chat() has fast path for simple tasks")

def test_chat_updates_messages():
    """9. chat()主路径更新self.messages"""
    from ai_staff_v4 import AIStaff
    import inspect
    src = inspect.getsource(AIStaff.chat)
    assert 'self.messages.append({"role": "user"' in src, "Should append user message"
    assert 'self.messages.append({"role": "assistant"' in src, "Should append assistant message"
    print("[OK] chat() updates self.messages")

def test_chat_single_returns_tokens():
    """10. chat_single()的stats含total_tokens"""
    from ai_staff_v4 import AIStaff
    import inspect
    src = inspect.getsource(AIStaff.chat_single)
    assert '"total_tokens"' in src, "chat_single stats should include total_tokens"
    print("[OK] chat_single() stats include total_tokens")

def test_rest_api_chat_returns_details():
    """11. REST API /chat返回trace_id和total_tokens"""
    from ai_staff_v4.endpoints.rest_api import RestAPIHandler
    import inspect
    src = inspect.getsource(RestAPIHandler._handle_chat)
    assert "trace_id" in src, "/chat should return trace_id"
    assert "total_tokens" in src, "/chat should return total_tokens"
    assert "quality_score" in src, "/chat should return quality_score"
    assert "return_details=True" in src, "/chat should call with return_details=True"
    print("[OK] REST API /chat returns full details")

def test_rest_api_run_returns_trace():
    """12. REST API /run返回trace_id和total_tokens"""
    from ai_staff_v4.endpoints.rest_api import RestAPIHandler
    import inspect
    src = inspect.getsource(RestAPIHandler._handle_run)
    assert "trace_id" in src, "/run should return trace_id"
    assert "total_tokens" in src, "/run should return total_tokens"
    print("[OK] REST API /run returns trace_id and total_tokens")

def test_forced_mode_returns_collab_result():
    """13. _chat_forced_mode返回CollaborationResult"""
    from ai_staff_v4 import AIStaff
    import inspect
    src = inspect.getsource(AIStaff._chat_forced_mode)
    assert "return collab_result" in src, "Should return CollaborationResult for collab mode"
    assert "result.total_time_sec" in src, "Should set total_time_sec"
    print("[OK] _chat_forced_mode returns CollaborationResult")

def test_budget_summary():
    """14. budget.summary()可用"""
    from ai_staff_v4.core.budget import TokenBudgetManager, BudgetConfig
    bm = TokenBudgetManager(BudgetConfig())
    summary = bm.summary()
    assert isinstance(summary, dict)
    print("[OK] budget.summary() works")

if __name__ == "__main__":
    tests = [
        test_import,
        test_chat_signature,
        test_collaboration_result_fields,
        test_call_with_fallback_returns_3tuple,
        test_collab_loop_run_stats_has_tokens,
        test_auto_run_v5_sets_tokens,
        test_extract_text,
        test_chat_simple_task_fast_path,
        test_chat_updates_messages,
        test_chat_single_returns_tokens,
        test_rest_api_chat_returns_details,
        test_rest_api_run_returns_trace,
        test_forced_mode_returns_collab_result,
        test_budget_summary,
    ]
    
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {t.__name__}: {e}")
            failed += 1
    
    print(f"\n{'='*40}")
    print(f"  {passed}/{len(tests)} passed, {failed} failed")
    if failed == 0:
        print("  ALL GREEN!")
    print(f"{'='*40}")
