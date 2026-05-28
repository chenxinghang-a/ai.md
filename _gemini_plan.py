"""Ask Gemini how to fix ai_staff_v4 to be truly plug-and-play"""
import sys, os, json
sys.path.insert(0, r"c:\Users\cxx\WorkBuddy\Claw")

from ai_staff_v4.backends.client import LLMClient

KEY = "AIzaSyC0MMf6fQkQsG5kMj9mDeGSKn0i2imhfik"
PROXY = "http://127.0.0.1:7890"
BASE = "https://generativelanguage.googleapis.com/v1beta/openai"

client = LLMClient(base_url=BASE, api_key=KEY, model="gemini-2.5-flash-lite", proxy=PROXY, timeout=60)

PROMPT = """你是AI框架架构师。我有一个Python包 ai_staff_v4（AI员工调度系统），现在有这些痛点导致用户体验极差，请给出具体的代码级解决方案：

## 当前问题
1. 用户必须手动填config.yaml，填错就全挂（Key/Proxy/Model三个字段）
2. 模型名经常过期，用户不知道哪些能用
3. 国内必须代理，但没开代理时没有任何友好提示
4. 429/503/404错误全部裸抛，普通用户看不懂
5. Windows下GBK编码问题频繁炸
6. 每次都要手动传proxy/key/model，不能一键启动

## 技术约束
- Python 3.12+, Windows环境
- 用httpx做HTTP请求
- 已有 LLMClient 类（OpenAI兼容格式）
- 配置文件是YAML格式
- 需要支持多模型fallback

## 请输出：
1. 具体的代码改动清单（哪个文件改什么）
2. 新增的"智能初始化"逻辑：自动检测代理→自动查模型列表→选最优模型→缓存结果
3. 错误处理的统一层：把所有API错误翻译成中文提示
4. 一行启动的API设计：from ai_staff_v4 import AIStaff; s = AIStaff(); s.chat("你好")
5. 完整的关键代码片段（可直接复制使用）

不要废话，给可执行的方案。输出JSON格式方便解析。"""

print("Asking Gemini for improvement plan...")
content, usage = client.chat_completion(
    messages=[{"role": "user", "content": PROMPT}],
    temperature=0.3,
    max_tokens=4000
)

print(f"\n=== Gemini Response ({usage}) ===\n")
print(content)

# Save
with open(r"c:\Users\cxx\WorkBuddy\Claw\_gemini_plan_result.txt", "w", encoding="utf-8") as f:
    f.write(content)
print("\nSaved to _gemini_plan_result.txt")
