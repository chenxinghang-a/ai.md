"""用ai_staff_v4 + Gemini API聊技术方向"""
import os
import sys

# 设置环境变量
os.environ["GEMINI_API_KEY"] = "AIzaSyC0MMf6fQkQsG5kMj9mDeGSKn0i2imhfik"
os.environ["AI_STAFF_PROXY"] = "http://127.0.0.1:7890"

from ai_staff_v4 import AIStaff

# 用quick_start启动
print("[Init] Starting ai_staff_v4 with Gemini...")
staff = AIStaff.quick_start(
    api_key="AIzaSyC0MMf6fQkQsG5kMj9mDeGSKn0i2imhfik",
    provider="gemini",
    proxy="http://127.0.0.1:7890",
    model="gemini-2.5-flash-lite",
)

print(f"[Init] Staff ready, model={staff.llm.model}")

# 聊技术方向
prompt = """你是一个AI框架架构师。我现在有一个开源AI协作框架ai_staff_v4，核心卖点：

1. **自动调配API** — SmartInit自动扫描环境变量/key文件，零配置启动
2. **自动集合多AI** — 10个Provider(Gemini/OpenAI/DeepSeek/Moonshot/通义千问/智谱GLM/硅基流动/Groq/Anthropic/Ollama)，一键切换
3. **多AI协同** — V5闭环：Writer(快模型)->Reviewer(强模型)->Rebuttal(辩论)->Rejudge->Revise，质量达标才停
4. **7种模式** — auto/direct/code/research/decision/creative/collab
5. **8个内置专家** — 自动分类任务+分配最合适的专家

当前状态：P0 bug全修，10个provider定义好了，代码能import。
我的问题：
1. 接下来最应该先做什么？推GitHub？多Provider实测？写example？
2. 开源发布策略怎么定？README/Guide/Example该做到什么程度？
3. 有什么能显著提升框架价值但成本不高的改进？
4. 竞品分析：相比LangChain/CrewAI/AutoGen，我的差异化在哪？怎么强化？

请给出具体、可执行的建议，不要泛泛而谈。用中文回答。"""

print("\n[Chat] Sending prompt to Gemini...")
print("="*60)

try:
    result = staff.chat(prompt, mode="research", return_details=True)
    
    # 输出结果到文件（避免PowerShell编码问题）
    output_text = ""
    if hasattr(result, 'deliverables'):
        for key, val in result.deliverables.items():
            output_text += f"\n{'='*60}\n"
            output_text += f"FILE: {key}\n"
            output_text += f"{'='*60}\n"
            output_text += str(val)
    
    if not output_text:
        output_text = str(result) if not isinstance(result, str) else result
    
    output_path = os.path.join(os.path.dirname(__file__), "_v4_tech_chat_result.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# ai_staff_v4 技术方向讨论\n\n")
        f.write(f"Model: {staff.llm.model}\n")
        f.write(f"Time: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(output_text)
    
    print(f"[Done] Result saved to: {output_path}")
    
    # 打印关键元数据
    if hasattr(result, 'quality_score'):
        print(f"[Meta] Quality: {result.quality_score}/10")
    if hasattr(result, 'total_tokens'):
        print(f"[Meta] Tokens: {result.total_tokens}")
    if hasattr(result, 'total_time_sec'):
        print(f"[Meta] Time: {result.total_time_sec:.1f}s")

except Exception as e:
    print(f"[ERROR] {type(e).__name__}: {e}")
    # 尝试简单模式
    print("\n[Fallback] Trying direct mode...")
    try:
        output = staff.chat("给ai_staff_v4这个AI协作框架3条最关键的下步行动建议", mode="direct")
        with open(os.path.join(os.path.dirname(__file__), "_v4_tech_chat_result.md"), "w", encoding="utf-8") as f:
            f.write(f"# ai_staff_v4 技术方向讨论(fallback)\n\n{output}")
        print(f"[Done] Fallback result saved")
    except Exception as e2:
        print(f"[FATAL] {type(e2).__name__}: {e2}")
