# -*- coding: utf-8 -*-
"""
Gemini深度诊断V2 — Round 2: 具体改造方案
基于Round1的尖锐诊断，追问具体实现方案
"""
import sys, os, io, json, time

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import httpx

GEMINI_KEY = "AIzaSyC0MMf6fQkQsG5kMj9mDeGSKn0i2imhfik"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
PROXY = "http://127.0.0.1:7890"

def ask(prompt, temp=0.8):
    client = httpx.Client(proxy=PROXY, timeout=120)
    resp = client.post(GEMINI_URL,
        headers={"Authorization": f"Bearer {GEMINI_KEY}", "Content-Type": "application/json"},
        json={"model": "gemini-2.5-flash", "messages": [{"role": "user", "content": prompt}],
              "temperature": temp, "max_tokens": 4096})
    data = resp.json()
    if isinstance(data, list): return str(data[0])[:5000]
    choices = data.get("choices", [])
    if isinstance(choices, list) and len(choices) > 0:
        msg = choices[0].get("message", {})
        if isinstance(msg, dict):
            return msg.get("content", str(data))
        return str(choices[0])
    return json.dumps(data, ensure_ascii=False)[:5000]

print("=" * 70)
print("  AI-Staff V2.3 深度诊断 — Round 2: 改造方案")
print("=" * 70)

PROMPT_R2 = """基于上一轮的诊断，我需要你给出**具体的、可落地的改造方案**。

## Round 1 核心结论（你的原话）
> "你的AI专家不是在'协作'，而是在'排队朗读自己的台词'"
> "缺乏真正的Agentic Behavior和动态问题解决能力"
> "将信息共享等同于智能协作"
> "目标导向性弱：输出只是过程，不应该是结果"

## 我的约束条件
- 纯Python项目，依赖尽量少（只用httpx/pyyaml）
- 用户可能只有1个API（比如只有Gemini免费API）
- 不能搞太复杂（不能变成另一个CrewAI）
- 要有"自由感"和"可玩性" — 用户拿到手觉得有意思
- 必须能直接复用，配置简单

## 请回答以下具体问题：

### A. 圆桌讨论改造（最重要！）
当前: for round in rounds → for expert in experts → LLM调用 → append到记录

请给出**新的交互协议设计**：
1. 专家之间应该有哪些"互动动作"？(提问/反驳/补充/修正/投票/委托...)
2. 如何让LLM自己决定下一个动作？（而不是固定for循环）
3. 给出伪代码级别的流程设计

### B. 任务→最优提示词映射
用户输入任意任务，框架应该自动：
1. 判断任务类型（代码/写作/分析/创意/翻译...）
2. 选择最合适的专家组合和提示词策略
3. 设计一个TaskClassifier + PromptStrategyRegistry

### C. 自由度与可玩性
1. 给我3个"用户会觉得很酷"的功能创意
2. 如何让非程序员也能用？
3. 有什么"一键体验"可以设计的？

### D. 输出价值提升
现在只输出txt聊天记录。还应该输出什么？
- 结构化报告？JSON？可视化？

### E. P0优先级改造清单（不超过5项，按重要性排序）
每一项要包含：改什么 / 怎么改 / 预期效果 / 复杂度(低中高)

请直接、具体、给代码级方案。不要泛泛而谈。"""

print("\n🔍 Round 2: 追问具体改造方案...")
start = time.time()
response = ask(PROMPT_R2, temp=0.7)
elapsed = time.time() - start

outpath = r"c:\Users\cxx\WorkBuddy\Claw\_gemini_diag_v23.md"

# Append round 2 to existing report
with open(outpath, 'a', encoding='utf-8') as f:
    f.write(f"\n\n---\n\n## Round 2: 具体改造方案\n\n")
    f.write(f"*时间: {time.strftime('%Y-%m-%d %H:%M')} | 耗时: {elapsed:.1f}s*\n\n---\n\n")
    f.write(response)

print(f"\n{'='*70}")
print(f"  Round 2 完成! ({elapsed:.1f}s)")
print(f"  已追加到: {outpath}")
print(f"{'='*70}")
print(f"\n{response}")
