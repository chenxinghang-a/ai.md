"""调用 Gemini 3 获取 AI 协作架构改进建议"""
import httpx, json, os, time

API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyC0MMf6fQkQsG5kMj9mDeGSKn0i2imhfik")
PROXY = "http://127.0.0.1:7890"

prompt = """你是AI系统架构师。请分析以下AI协作框架的问题，并给出具体可执行的改进方案。

当前架构核心问题：
1. AI协作是假的 - expert_collab只是顺序发言+历史注入，没有真正交互
2. 路由和执行断裂 - AIRouter选了模型但auto_run不用它
3. Review不闭环 - ReviewAgent打分但不回馈给Executor重新执行
4. SelfImprove只改prompt - 不改路由策略和分类规则
5. 多模型浪费 - MultiLLMClient只做fallback，没做模型间协作
6. staff.py太臃肿 - 2053行所有逻辑堆一起

目标：让AI和AI真正协作，一个写初稿->另一个审查指出问题->第一个根据反馈修正->循环到质量达标。多模型分工（强模型决策/审查，快模型执行），整个过程自动闭环可观测。

请给出：
1. 核心架构改进（哪些模块重写/合并/删除）
2. AI协作流具体设计（消息协议、状态机、反馈闭环）
3. 多模型分工策略
4. staff.py拆分方向
5. 前3个最值得立即做的改进"""

client = httpx.Client(proxy=PROXY, timeout=120, follow_redirects=True)
t0 = time.time()
r = client.post(
    "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
    headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    json={
        "model": "gemini-3-flash-preview",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 8192,
    }
)
elapsed = time.time() - t0
print(f"Status: {r.status_code} | Time: {elapsed:.1f}s")
if r.status_code == 200:
    data = r.json()
    content = data["choices"][0]["message"]["content"]
    print(content)
else:
    print(f"Error: {r.text[:500]}")
