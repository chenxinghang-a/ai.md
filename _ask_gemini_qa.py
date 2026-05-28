"""让Gemini做QA审查"""
import httpx, os, time

API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyC0MMf6fQkQsG5kMj9mDeGSKn0i2imhfik")
PROXY = "http://127.0.0.1:7890"

prompt = """你是QA工程师。以下是我们刚修的bug列表，请检查是否还有遗漏的问题：

已修bug:
1. BaseAgent缺bus属性 -> 加了全局EventBus
2. from_env()找不到keys.json -> discover_and_start()增加keys.json扫描
3. chat() forced mode全挂 -> 是bug1导致的
4. REST API handler方法在Handler类上不在Server上 -> 修了测试
5. keys.json格式不匹配 -> 统一为{"gemini": "key"}格式

请回答：
1. 这些修复是否完整？有没有引入新bug？
2. 从用户角度，还有什么地方会卡住？
3. 代码里还有哪些明显的bug或隐患？
4. 测试16/17通过，唯一失败是辩论协议没触发（因为Gemini评分太高直接过了阈值）——这算bug吗？
5. 如果要发布v1.0，还差什么？"""

client = httpx.Client(proxy=PROXY, timeout=120, follow_redirects=True)
t0 = time.time()
r = client.post(
    "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
    headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    json={
        "model": "gemini-3.1-flash-lite-preview",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5,
        "max_tokens": 2048,
    }
)
elapsed = time.time() - t0
if r.status_code == 200:
    print(r.json()["choices"][0]["message"]["content"])
else:
    print(f"Error: {r.status_code} {r.text[:300]}")
