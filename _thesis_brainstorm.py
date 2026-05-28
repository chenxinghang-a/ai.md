"""Gemini brainstorm for thesis direction."""
import os
os.environ['GEMINI_API_KEY'] = 'AIzaSyC0MMf6fQkQsG5kMj9mDeGSKn0i2imhfik'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'

from ai_staff_v4 import AIStaff
staff = AIStaff.from_env()

prompt = (
    "我是电气工程及其自动化专业本科生，毕业设计做了一个Python多智能体LLM框架（LoomLLM），核心功能：\n"
    "1. 智能任务路由：简单问题1次LLM调用，复杂任务自动触发多专家协作闭环\n"
    "2. 质量门控：Writer生成→Reviewer审查→不达标迭代修正，直到质量分数>=80\n"
    "3. 成本感知：根据任务复杂度自动选模型，简单问题用便宜模型，代码任务用强模型审查\n"
    "4. 6个专家角色：通用助手、研究员、工程师、创作者、审查员、规划师\n"
    "5. 支持多种LLM后端（Gemini/DeepSeek/OpenAI等）\n\n"
    "框架本身是通用的，但我想包装成跟工业自动化/电气工程相关的毕设。\n\n"
    "请帮我：\n"
    "1. 精简毕设题目（不要超过20字）\n"
    "2. 给出3-5个方向，说明怎么把框架和电气自动化结合起来\n"
    "3. 论文章节建议（6-8章）\n"
    "4. 答辩时怎么讲'为什么做这个'才不跑题"
)

result = staff.chat(prompt, mode='research', return_details=True)
text = list(result.deliverables.values())[0]
print(text)
