"""用ai_staff_v4 + Gemini API聊技术方向 - 简化版"""
import os, httpx, json

KEY = "AIzaSyC0MMf6fQkQsG5kMj9mDeGSKn0i2imhfik"
PROXY = "http://127.0.0.1:7890"
MODEL = "gemini-3.1-flash-lite-preview"
BASE = "https://generativelanguage.googleapis.com/v1beta/openai"

prompt = """你是一个AI框架架构师。我有一个开源AI协作框架ai_staff_v4，核心卖点：

1. **自动调配API** — SmartInit自动扫描环境变量/key文件，零配置启动
2. **自动集合多AI** — 10个Provider(Gemini/OpenAI/DeepSeek/Moonshot/通义千问/智谱GLM/硅基流动/Groq/Anthropic/Ollama)
3. **多AI协同** — V5闭环：Writer(快模型)->Reviewer(强模型)->Rebuttal(辩论)->Rejudge->Revise
4. **7种模式** — auto/direct/code/research/decision/creative/collab
5. **8个内置专家** — 自动分类任务+分配专家

当前状态：P0 bug全修，10个provider定义好，代码能import和运行。

问题：
1. 接下来最应该先做什么？推GitHub？多Provider实测？写example？
2. 开源发布策略怎么定？
3. 有什么低成本高价值的改进？
4. 相比LangChain/CrewAI/AutoGen，差异化在哪？

请给出具体、可执行的建议。中文回答。"""

client = httpx.Client(proxy=PROXY, timeout=60, follow_redirects=True)
headers = {
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json"
}
payload = {
    "model": MODEL,
    "messages": [
        {"role": "system", "content": "你是资深AI框架架构师，擅长产品策略和技术方向规划。请给出具体可执行的建议。"},
        {"role": "user", "content": prompt}
    ],
    "temperature": 0.7,
    "max_tokens": 4096
}

print(f"[Call] {MODEL} via proxy...")
try:
    resp = client.post(f"{BASE}/chat/completions", headers=headers, json=payload)
    data = resp.json()
    # Debug: save raw response
    with open("_v4_raw_resp.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[Status] {resp.status_code}")
    print(f"[Keys] {list(data.keys())}")
    if "error" in data:
        print(f"[API Error] {data['error']}")
        raise RuntimeError(str(data['error']))
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_v4_tech_chat_result.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# ai_staff_v4 技术方向讨论\n\n")
        f.write(f"Model: {MODEL} | Tokens: {usage.get('total_tokens', '?')}\n\n")
        f.write(content)
    
    print(f"[OK] Saved to {out_path}")
    print(f"[Tokens] {usage}")
except Exception as e:
    print(f"[ERROR] {e}")
    if hasattr(e, 'response'):
        print(f"[Status] {e.response.status_code}")
        print(f"[Body] {e.response.text[:500]}")
