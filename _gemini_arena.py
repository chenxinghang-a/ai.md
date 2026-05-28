# -*- coding: utf-8 -*-
"""
Gemini 3 Arena — 多模型横评
测试所有可用的Gemini 3.x模型，多维度对比
"""
import sys, os, json, time, httpx, io

# Fix Windows GBK console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

API_KEY = "AIzaSyC0MMf6fQkQsG5kMj9mDeGSKn0i2imhfik"
PROXY = "http://127.0.0.1:7890"
BASE = "https://generativelanguage.googleapis.com/v1beta/openai"

# 候选模型列表（按推测能力排序）
MODELS = [
    ("gemini-2.5-pro",           "Pro级·推理强"),
    ("gemini-2.5-flash",         "Flash·均衡"),
    ("gemini-2.5-flash-preview", "Flash预览版"),
    ("gemini-3-flash-live",      "G3 Live·流式"),
    ("gemini-3.1-flash-lite-preview", "G3.1 Lite·轻量(已知可用)"),
]

# 测试问题集
QUESTIONS = [
    {
        "tag": "自我介绍",
        "q": "你好！请用一句话介绍你自己：你是什么模型、什么版本、擅长什么？",
        "max_tok": 300,
    },
    {
        "tag": "代码能力",
        "q": "用Python写一个函数：给定桌面截图路径和目标文字，用OpenCV模板匹配找到该文字在图中的位置坐标(x,y)。要求支持模糊匹配。",
        "max_tok": 1500,
    },
    {
        "tag": "推理能力",
        "q": "一个房间里有3个开关，对应隔壁房间的3个灯泡。你只能在每个房间里各进一次。怎么确定哪个开关控制哪个灯泡？请给出完整的逻辑推理过程。",
        "max_tok": 800,
    },
    {
        "tag": "创意写作",
        "q": "用50字以内写一段关于「深夜写代码的程序员」的微型小说，要有反转结局。",
        "max_tok": 400,
    },
    {
        "tag": "技术建议",
        "q": "我在做Windows桌面自动化Agent（截图→YOLO检测→LLM决策→pyautogui执行）。当前用Flash Lite但空间推理不够好。请推荐最适合这个场景的模型组合，考虑准确率、速度、成本三个维度。给出具体建议。",
        "max_tok": 1200,
    },
]

client = httpx.Client(proxy=PROXY, timeout=180)

def ask(model, prompt, max_tok=1000, msgs=None):
    """单次提问"""
    if msgs is None:
        msgs = []
    msgs.append({"role": "user", "content": prompt})
    
    for retry in range(3):
        try:
            r = client.post(BASE + "/chat/completions",
                headers={"Authorization": "Bearer " + API_KEY, "Content-Type": "application/json"},
                json={"model": model, "messages": msgs, "max_tokens": max_tok, "temperature": 0.7})
            data = r.json()
            
            # 错误处理
            if isinstance(data, dict) and "error" in data:
                err = data["error"]
                code = err.get("code", "?")
                msg = str(err.get("message", ""))[:120]
                print(f"    [ERR {code}] {msg}")
                if code in (429, 503):
                    time.sleep(8 * (retry + 1))
                    continue
                return f"[ERROR] {code}: {msg}"
            
            # 成功响应 - 兼容多种格式
            content = ""
            if isinstance(data, dict):
                if "choices" in data:
                    content = data["choices"][0].get("message", {}).get("content", "")
                elif "candidates" in data:
                    content = data["candidates"][0].get("content", {}).get("parts", [{}])[0].get("text", "")
            elif isinstance(data, list) and data:
                content = str(data[0])[:500]
            
            if content:
                msgs.append({"role": "assistant", "content": content})
            return content or "[EMPTY_RESPONSE]"
            
        except Exception as e:
            print(f"    [EXC] {e}")
            time.sleep(5)
    return "[FAILED_AFTER_RETRIES]"

def test_model(name, label):
    """完整测试一个模型的所有问题"""
    results = []
    total_chars = 0
    start = time.time()
    
    print(f"\n{'='*60}")
    print(f"  🤖 {label}")
    print(f"     Model ID: {name}")
    print(f"{'='*60}")
    
    for i, q in enumerate(QUESTIONS):
        print(f"\n  --- Q{i+1}: {q['tag']} ({q['max_tok']}tok) ---")
        t0 = time.time()
        
        resp = ask(name, q["q"], q["max_tok"])
        elapsed = time.time() - t0
        
        if resp and not resp.startswith("[ERROR") and not resp.startswith("[FAILED"):
            chars = len(resp)
            total_chars += chars
            status = f"✅ {chars}ch/{elapsed:.1f}s"
            preview = resp.replace("\n", " ")[:200]
            print(f"    [{status}]")
            print(f"    {preview}...")
        else:
            status = f"❌ {resp[:80] if resp else 'None'}"
            print(f"    [{status}]")
            resp = None
        
        results.append({
            "tag": q["tag"],
            "status": status,
            "response": (resp or "")[:500],
            "elapsed": round(elapsed, 2),
        })
        time.sleep(2)  # 礼貌间隔
    
    total_time = time.time() - start
    success = sum(1 for r in results if r["response"] and not r["response"].startswith("["))
    
    print(f"\n  📊 汇总: {success}/{len(QUESTIONS)}题通过 | {total_chars}字符 | {total_time:.1f}s总耗时")
    
    return {
        "name": name,
        "label": label,
        "success": success,
        "total": len(QUESTIONS),
        "chars": total_chars,
        "time": round(total_time, 1),
        "results": results,
    }

# ═══════ 主流程 ══════
print("=" * 60)
print("  🏟️  GEMINI 3 ARENA — 多模型横评")
print(f"  时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"  模型数: {len(MODELS)} | 问题数: {len(QUESTIONS)}")
print("=" * 60)

all_results = []
for name, label in MODELS:
    result = test_model(name, label)
    all_results.append(result)

# ═══════ 排行榜 ══════
print("\n\n" + "=" * 60)
print("  🏆 最终排行榜")
print("=" * 60)
print(f"\n{'排名':<4} {'模型':<30} {'通过':>4} {'字符':>7} {'耗时':>7}")
print("-" * 56)

sorted_results = sorted(all_results, key=lambda x: (-x["success"], -x["chars"]))
for i, r in enumerate(sorted_results):
    medal = ["🥇","🥈","🥉"][i] if i < 3 else f"{i+1}."
    print(f"{medal:<4} {r['label']:<28} {r['success']:>2}/{r['total']:<2} {r['chars']:>6,} {r['time']:>6.1f}s")

# ═══════ 保存报告 ══════
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_gemini_arena_report.md")
with open(out, "w", encoding="utf-8") as f:
    f.write("# Gemini 3 Arena — 多模型横评报告\n\n")
    f.write(f"> 测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"> 模型数: {len(MODELS)} | 问题数: {len(QUESTIONS)}\n\n")
    
    f.write("## 📊 排行榜\n\n")
    f.write("| 排名 | 模型 | 通过率 | 总字符 | 耗时 |\n|------|------|--------|--------|------|\n")
    for i, r in enumerate(sorted_results):
        m = ["🥇","🥈","🥉"][i] if i < 3 else str(i+1)
        f.write(f"| {m} | {r['label']} | {r['success']}/{r['total']} | {r['chars'],} | {r['time']}s |\n")
    
    for r in sorted_results:
        f.write(f"\n## 🤖 {r['label']} (`{r['name']}`)\n\n")
        f.write("**总体**: {}/{} 通过 | {} 字符 | {:.1f}s\n\n".format(
            r['success'], r['total'], r['chars'], r['time']))
        for res in r['results']:
            f.write(f"### Q: {res['tag']} {res['status']}\n\n")
            f.write(f"{res['response']}\n\n")

print(f"\n📄 报告已保存: _gemini_arena_report.md")

client.close()
print("\n✅ Arena 结束！感谢观看 👋")
