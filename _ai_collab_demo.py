# -*- coding: utf-8 -*-
"""
AI-Staff V2.3 Demo — Expert Roundtable (圆桌讨论) 实测
单API（Gemini）多专家协作，自动输出聊天记录txt
"""
import sys, os

# Add skill scripts to path
SKILL_DIR = r"C:\Users\cxx\.workbuddy\skills\ai-staff"
sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))

from ai_staff import AIStaff, ExpertRegistry

# ─── 配置：只用Gemini一个API ───
GEMINI_KEY = "AIzaSyC0MMf6fQkQsG5kMj9mDeGSKn0i2imhfik"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
PROXY = "http://127.0.0.1:7890"

print("=" * 60)
print("  AI-Staff V2.3 圆桌讨论 Demo")
print("  API: Gemini 2.5 Flash (唯一后端)")
print("=" * 60)

# 初始化 AI-Staff（单后端模式）
staff = AIStaff(
    base_url=GEMINI_URL,
    api_key=GEMINI_KEY,
    model="gemini-2.5-flash",
    proxy=PROXY,
    expert_id="generalist",
)

# ─── 运行圆桌讨论 ───
TOPIC = "如何设计一个能替代传统操作系统的AI原生操作系统？它应该有哪些核心特性？"

print(f"\n🎯 讨论话题: {TOPIC}")
print(f"👥 专家阵容: 规划师 → 研究员 → 工程师 → 审查员")
print(f"🔄 讨论轮次: 2轮")
print(f"\n{'─'*60}\n")

transcript = staff.expert_collab(
    topic=TOPIC,
    expert_ids=["planner", "researcher", "coder", "critic"],
    rounds=2,
    output_path=os.path.join(os.path.dirname(__file__), "ai_collab_demo.txt"),
)

print(f"\n{'═'*60}")
print(transcript)
print(f"{'═'*60}")

print("\n✅ Demo完成！聊天记录已保存到 ai_collab_demo.txt")
