"""让Gemini审查v4代码并给出落地改进建议"""
import httpx, json, os, time, sys

API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyC0MMf6fQkQsG5kMj9mDeGSKn0i2imhfik")
PROXY = "http://127.0.0.1:7890"
MODEL = sys.argv[1] if len(sys.argv) > 1 else "gemini-3.1-flash-lite-preview"

# 收集关键文件
files_to_review = {
    "staff.py": "ai_staff_v4/main_mod/staff.py",
    "collab_loop.py": "ai_staff_v4/agents/collab_loop.py",
    "startup.py": "ai_staff_v4/main_mod/startup.py",
    "rest_api.py": "ai_staff_v4/endpoints/rest_api.py",
}

code_snippets = {}
for name, path in files_to_review.items():
    full = os.path.join(os.path.dirname(__file__), path)
    if os.path.exists(full):
        with open(full, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # 取前100行 + 最后30行（避免太长）
            if len(lines) > 130:
                code_snippets[name] = (
                    f"[{len(lines)}行, 只展示前100+后30行]\n"
                    + "".join(lines[:100])
                    + "\n... [中间省略] ...\n"
                    + "".join(lines[-30:])
                )
            else:
                code_snippets[name] = "".join(lines)
    else:
        code_snippets[name] = "[文件不存在]"

prompt = f"""你是AI系统架构师，请审查以下ai-staff V4项目的关键代码，从「产品落地」角度给出具体改进建议。

## 当前架构概览
- staff.py: 主控类，~1900行，统一入口chat()刚加，7种模式路由
- collab_loop.py: V5闭环协作引擎，Writer→Reviewer→Revise循环
- startup.py: 启动逻辑，from_env/quick_start
- rest_api.py: HTTP API端点

## 已完成优化
1. 统一chat()入口（auto/direct/code/research/decision/creative/collab/arena）
2. 线程安全（expert参数传递，不污染self.expert）
3. CollabLoop讨论模式（复杂任务Reviewer参与讨论）
4. Gemini3做Reviewer（_pick_model优先3.x）
5. REST API接入chat()

## 核心代码

### staff.py
```
{code_snippets.get('staff.py', '')}
```

### collab_loop.py
```
{code_snippets.get('collab_loop.py', '')}
```

### rest_api.py
```
{code_snippets.get('rest_api.py', '')}
```

## 请回答以下问题（具体、可执行、不要泛泛而谈）

1. **代码质量**: 有哪些明显的代码坏味道？前3个最该修的是什么？
2. **产品落地**: 如果要让真实用户使用，还缺什么？优先级排序
3. **AI互动性**: 当前Writer→Reviewer→Revise的闭环够不够？怎么让AI之间真正"讨论"而不是轮流发言？
4. **部署问题**: 要部署到GitHub让其他人能用，需要什么（文档、配置、CI、示例）？
5. **架构风险**: 有什么技术债会越积越大？现在就该处理的
6. **下一步**: 如果只有1小时，最该做的3件事是什么？
"""

client = httpx.Client(proxy=PROXY, timeout=120, follow_redirects=True)
t0 = time.time()

# 保存prompt到临时文件供debug
with open(os.path.join(os.path.dirname(__file__), "_gemini_review_prompt.txt"), "w", encoding="utf-8") as f:
    f.write(prompt)

r = client.post(
    "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
    headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    json={
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 8192,
    }
)
elapsed = time.time() - t0
print(f"[{MODEL}] Status: {r.status_code} | Time: {elapsed:.1f}s")

if r.status_code == 200:
    data = r.json()
    content = data["choices"][0]["message"]["content"]
    print(content)
    # 保存回复
    with open(os.path.join(os.path.dirname(__file__), "_gemini_review_response.md"), "w", encoding="utf-8") as f:
        f.write(f"# Gemini Review ({MODEL}, {elapsed:.1f}s)\n\n{content}")
else:
    print(f"Error: {r.text[:500]}")
