# -*- coding: utf-8 -*-
"""
Gemini深度诊断V2 — ai-staff V2.3 圆桌讨论功能差距分析
"""
import sys, os, io, json, time, re

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import httpx

GEMINI_KEY = "AIzaSyC0MMf6fQkQsG5kMj9mDeGSKn0i2imhfik"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
PROXY = "http://127.0.0.1:7890"

def ask_gemini(prompt, temperature=0.7):
    client = httpx.Client(proxy=PROXY, timeout=120)
    resp = client.post(
        GEMINI_URL,
        headers={"Authorization": f"Bearer {GEMINI_KEY}", "Content-Type": "application/json"},
        json={
            "model": "gemini-2.5-flash",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": 4096
        }
    )
    data = resp.json()
    # Debug: print actual response type
    if isinstance(data, list):
        return str(data[0])[:5000] if data else "empty list"
    # Gemini OpenAI-compatible API
    choices = data.get("choices", [])
    if isinstance(choices, list) and len(choices) > 0:
        msg = choices[0].get("message", {})
        if isinstance(msg, dict):
            return msg.get("content", str(data))
        return str(choices[0])
    if "content" in data:
        c = data["content"]
        if isinstance(c, list):
            return c[0].get("text", str(c))
        return str(c)
    return json.dumps(data, ensure_ascii=False)[:5000]

# ─── 读取当前源码关键部分作为上下文 ───
STAFF_PATH = r"C:\Users\cxx\.workbuddy\skills\ai-staff\scripts\ai_staff.py"
with open(STAFF_PATH, 'r', encoding='utf-8') as f:
    source_code = f.read()

# 提取expert_collab方法
collab_start = source_code.find("def expert_collab(")
collab_end = source_code.find("def _format_arena_report", collab_start)
collab_source = source_code[collab_start:collab_end]

# 提取内置专家prompts
experts_start = source_code.find("_load_builtin(cls)")
experts_end = source_code.find("for exp in builtin_experts:", experts_start) + len("for exp in builtin_experts:")
experts_section = source_code[experts_start:experts_end+500]

print("=" * 70)
print("  AI-Staff V2.3 深度诊断 — Gemini Round 1")
print("=" * 70)

PROMPT_DIAG1 = f"""你是一个顶级产品架构师+AI交互设计专家。请对以下AI多专家协作框架进行**毫不留情的深度诊断**。

## 项目背景
- 项目名: ai-staff V2.3 (Python)
- 定位: 多后端多模型LLM调度框架 + AI专家协作系统
- 核心卖点: "自由用LLM才是优势，切换模型、多模型多API同时调用"
- 目标用户: 开发者、AI工程师、想要搭建AI Agent团队的人

## 当前功能清单
1. ExpertRegistry: YAML/内置专家角色管理(6个内置专家: generalist/researcher/coder/writer/critic/planner)
2. Agent Framework: CoT规划→执行→审查→记忆 4个子Agent流水线
3. Multi-Backend Engine: BackendProfile/MultiLLMClient/ModelRouter/FallbackManager
4. Arena模式: 单API多模型对比 / Cross-Arena跨API对比
5. Expert Collab(圆桌讨论): V2.3新增，多专家轮流发言+互相引用

## 关键代码: expert_collab 方法
```python
{collab_source[:3000]}
```

## 内置专家定义
{experts_section[:2000]}

## 我的自检发现的问题
1. 太工具化/模板化 — 固定pipeline，不像"一群AI在自由协作"
2. 互动链浅 — A→B→C→D顺序发言，无真正辩论/反驳/碰撞
3. 提示词硬编码 — 专家system_prompt质量一般且难以定制
4. 缺少任务类型→最优策略映射
5. 输出格式单一
6. 即插即用体验差 — 需要手动配API写脚本

## 请你从以下维度给出诊断:

### 1. 核心差距分析（最重要！）
- 和市面上最好的AI Agent协作框架(CrewAI/AutoGen/LangGraph/MetaGPT等)比，**最致命的差距**是什么？
- 为什么说"差点意思"？具体差在哪里？

### 2. 交互设计缺陷
- 当前的圆桌讨论(expert_collab)有什么根本性设计缺陷？
- 如何让它从"轮流发言"变成"真正有价值的AI协作"？

### 3. 自由度与可玩性
- 用户拿到手后能怎么"玩"？现在够自由吗？
- 缺什么能让用户觉得"这个好玩/有用/我想试试"？

### 4. 复用性与开箱即用
- 新用户上手成本太高？如何降到最低？
- 有没有什么"一键体验"的设计缺失？

### 5. 具体改进建议（按优先级排序）
- P0: 不做就不能发布的东西
- P1: 做了会显著提升体验
- P2: 锦上添花

请尽量详细、具体、直接。不要客套话。"""

print("\n🔍 发送诊断请求给Gemini...")
start = time.time()
response1 = ask_gemini(PROMPT_DIAG1, temperature=0.8)
elapsed = time.time() - start

# 保存结果
output_path = r"c:\Users\cxx\WorkBuddy\Claw\_gemini_diag_v23.md"
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(f"# AI-Staff V2.3 Gemini 深度诊断报告\n\n")
    f.write(f"*时间: {time.strftime('%Y-%m-%d %H:%M')} | 耗时: {elapsed:.1f}s*\n\n---\n\n")
    f.write(response1)

print(f"\n{'='*70}")
print(f"  诊断完成! ({elapsed:.1f}s)")
print(f"  已保存到: {output_path}")
print(f"{'='*70}")
print(f"\n{response1}")
