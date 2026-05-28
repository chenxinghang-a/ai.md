"""调用Gemini获取ai_staff_v4代码优化方案"""
import httpx, json, os, time, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

API_KEY = os.environ.get('GEMINI_API_KEY', 'AIzaSyC0MMf6fQkQsG5kMj9mDeGSKn0i2imhfik')
PROXY = 'http://127.0.0.1:7890'

prompt = '''你是Python架构师。以下代码库有严重问题，请给出具体修复方案（只给关键代码片段，不要废话）。

## 代码库: ai_staff_v4 (2190行主文件 staff.py)

### P0 运行时崩溃（必须立即修）
1. staff.py L771: `Path(output_path)` 但没 `from pathlib import Path` → NameError
2. staff.py L349: `TaskState(task=...)` 应为 `TaskState(task_id=...)` → TypeError
3. rest_api.py L230-236: 调用 `staff.chat()`, `staff.code()`, `staff.decision()` 但AIStaff没有这些方法 → 500
4. router.py L105: `bus.publish(...)` 但没导入 `bus` → NameError

### P1 逻辑Bug
5. staff.py L1194: `_stats or {}` — 当critic分支不执行时 `_stats` 未定义 → UnboundLocalError
6. engine.py L374: 普通字符串中的 {self._reflection_interval} 不会被替换
7. staff.py L1150: `quality_score = min(9.0, 7.0 + len(all_deliverables) * 0.3)` — 按文件数评分，3个文件就满分

### 架构问题
8. 三套路由关键词表：classifier.py / ai_router.py / collab_loop.py 各维护一套，内容不一致
9. AIRouter从未被主执行流程使用（幽灵功能）
10. staff.py 2190行，需要拆分
11. collab_loop.py _auto_route() 与 TaskClassifier 功能重复
12. review失败时continue但last_feedback可能为None → to_revision_prompt() 报错

### 请给出：
1. P0修复的具体代码（5行以内每处）
2. 三套路由统一方案：如何合并，保留哪个文件
3. staff.py拆分建议：拆成哪几个文件，每个负责什么
4. collab_loop的review失败fallback策略
'''

client = httpx.Client(proxy=PROXY, timeout=60, follow_redirects=True)

# 尝试多个模型
models = ['gemini-2.5-flash-lite', 'gemini-2.5-flash', 'gemini-3-flash-preview']
for model in models:
    t0 = time.time()
    try:
        r = client.post(
            'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions',
            headers={'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'},
            json={
                'model': model,
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.7,
                'max_tokens': 4096,
            }
        )
        elapsed = time.time() - t0
        print(f'Model: {model} | Status: {r.status_code} | Time: {elapsed:.1f}s')
        if r.status_code == 200:
            data = r.json()
            content = data['choices'][0]['message']['content']
            print(content)
            break
        else:
            print(f'  Error: {r.text[:200]}')
    except Exception as e:
        print(f'Model: {model} | Exception: {e}')
