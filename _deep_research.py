# -*- coding: utf-8 -*-
"""Deep research session with Gemini — multi-turn, learn from each response"""
import sys, os, json, time, httpx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

API_KEY = "AIzaSyC0MMf6fQkQsG5kMj9mDeGSKn0i2imhfik"
PROXY = "http://127.0.0.1:7890"
MODEL = "gemini-3.1-flash-lite-preview"
BASE = "https://generativelanguage.googleapis.com/v1beta/openai"

client = httpx.Client(proxy=PROXY, timeout=180)

def ask(prompt, msgs=None, max_tok=6000):
    """Send to Gemini, return raw content or error string"""
    if msgs is None:
        msgs = []
    # Add user message
    msgs.append({"role": "user", "content": prompt})
    
    for retry in range(3):
        try:
            r = client.post(BASE + "/chat/completions",
                headers={"Authorization": "Bearer " + API_KEY, "Content-Type": "application/json"},
                json={"model": MODEL, "messages": msgs, "max_tokens": max_tok, "temperature": 0.2})
            data = r.json()
            if isinstance(data, list):
                if data and "error" in str(data[0]): 
                    print("  [503?] {}".format(str(data[0])[:100]))
                    time.sleep(5); continue
            if isinstance(data, dict):
                if "error" in data:
                    err = data["error"]
                    code = err.get("code", "?")
                    msg = str(err.get("message",""))[:80]
                    print("  [ERR {}] {}".format(code, msg))
                    if code == 429 or code == 503:
                        time.sleep(10 * (retry + 1)); continue
                    return None
                if "choices" in data:
                    reply = data["choices"][0].get("message", {}).get("content", "")
                    msgs.append({"role": "assistant", "content": reply})
                    return reply
            return "[UNKNOWN] " + str(data)[:200]
        except Exception as e:
            print("  [EXC] {}".format(e))
            time.sleep(5)
    return None

print("=" * 60)
print("  Gemini Deep Research Session")
print("  Model:", MODEL)
print("=" * 60)

# ═══════ Round 1: 验证RapidOCR正确用法 ══════
print("\n=== R1: RapidOCR API验证 ===")

r1 = ask("""我在开发桌面自动化Agent，用RapidOCR做UI元素文字识别。
我刚测试了RapidOCR的真实返回格式，请确认我的理解是否正确：

测试代码和结果：
```python
from rapidocr_onnxruntime import RapidOCR
import numpy as np
from PIL import Image, ImageDraw

img = Image.new('RGB', (300, 80), 'white')
d = ImageDraw.Draw(img)  
d.text((10,20), '学习通登录', fill='black', font=ImageFont.truetype('msyh.ttc',28))
arr = np.array(img)

e = RapidOCR()
result, elapse = e(arr)
```

返回结果：
```
result = [
    [
        [[3.0, 19.0], [157.0, 20.0], [157.0, 61.0], [3.0, 60.0]],   # 四边形坐标(4个点)
        '学习通登录',                                                    # 文字字符串
        0.9993806481361389                                               # 置信度float
    ]
]
elapse = [1.28, 0.001, 0.201]  # [det_time, cls_time, rec_time]

空白图返回: result=None, elapse=None
```

问题：
1. 返回格式是 list[list[polygon_4pts, str_text, float_conf]] 对吗？
2. 我之前的代码写的是 line[1][0] 假设line[1]是tuple(text,conf)，这明显错了。正确取法应该是 line[1] 就是文字？
3. 对于桌面图标（小图48x48或更小），OCR能识别出应用名吗？有没有什么预处理技巧提升小图标识别率？
4. 有没有参数可以调优（比如det/rec模型精度）？

请给出正确的RapidOCR封装函数代码。""")

if r1:
    print("[Gemini R1] ({} chars)\n".format(len(r1)))
    print(r1[:3000])
    if len(r1) > 3000: print("... truncated ({})".format(len(r1)))
else:
    print("R1 failed, skipping..."); r1 = ""

# ═══════ Round 2: 桌面图标OCR策略 ══════
print("\n=== R2: 桌面图标识别策略 ===")

r2 = ask("""继续。现在讨论桌面图标场景。

背景：Windows桌面2560x1440，YOLO检测到36个image类型元素（都是桌面图标）。
每个icon大约 40~70像素宽高。
目标：通过OCR知道每个图标是什么应用（学习通、Chrome、微信等...）

问题：
1. 直接对YOLO的box裁剪后送OCR效果如何？会不会因为太小而识别不出？
2. 如果直接裁剪不行，有什么替代方案？比如：
   - 放大裁剪区域后再OCR？（插值放大）
   - 用图标周围的文字标签（桌面shortcut的文件名）来识别？
   - Windows shell API获取桌面图标列表（非视觉方法）？
3. 你推荐的最佳方案是什么？给出具体实现思路。

注意：我已经安装了rapidocr-onnxruntime，不想再装新东西了。""")

if r2:
    print("[Gemini R2] ({} chars)\n".format(len(r2)))
    print(r2[:3000])
    if len(r2) > 3000: print("... truncated")
else:
    print("R2 failed..."); r2 = ""

# ═══════ Round 3: VLM Agent整体优化建议 ══════
print("\n=== R3: 整体架构优化 ===")  

r3 = ask("""继续。现在从更高层面讨论VLM Agent怎么做得更好。

当前架构v2：
截图→YOLO检测(8类UI元素)→RapidOCR增强(给每个box加文字)→IntentRouter(硬编码拦截launch/close等)→LLM决策(Gemini Flash Lite)→pyautogui执行→ActionHistory(去重防死循环)

实测结果v1（无OCR版）："打开学习通上课去" → 10轮全部失败，LLM反复点击同一位置

已知的改进方向：
- P0 SystemLauncher ✅ (Win+搜索启动应用)
- P1 OCR融合 (正在修复API用法bug)  
- P2 ActionHistory ✅ (去重)
- P3 IntentRouter ✅ (硬编码拦截)

我想问更深的问题：

1. **LLM模型选择**：Flash Lite够用吗？对于"看截图找按钮并点击"这种任务，什么级别的模型能稳定做到90%+准确率？要不要考虑本地小模型？

2. **多模态理解**：当前发给LLM的是低质量JPEG(detail="low") + 元素列表文字。如果改成高质量图片+详细元素信息，决策准确度能提升多少？token成本呢？

3. **反馈闭环**：执行动作后再截图对比前后状态变化，判断操作是否成功。这个思路可行吗？怎么做最简单有效？

4. **竞品参考**：你知道哪些开源桌面自动化项目做得比较好的？它们的核心技术栈是什么？

5. **如果让你从头设计一个最强的桌面自动化Agent**（不限制现有代码），你会怎么设计？给我一个理想架构蓝图。

请深入分析每个问题，给出你的判断和建议。""")

if r3:
    print("[Gemini R3] ({} chars)\n".format(len(r3)))
    print(r3[:4000])
    if len(r3) > 4000: print("... truncated ({})".format(len(r3)))
else:
    print("R3 failed..."); r3 = ""

# ═══════ Save all results ══════
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_gemini_research.md")
with open(out, "w", encoding="utf-8") as f:
    f.write("# Gemini Deep Research Results\n\n")
    f.write("## R1: RapidOCR API验证\n\n{}\n\n".format(r1 or "(failed)"))
    f.write("## R2: 桌面图标识别策略\n\n{}\n\n".format(r2 or "(failed)"))
    f.write("## R3: 架构优化\n\n{}\n\n".format(r3 or "(failed)"))

total = sum(len(x) for x in [r1,r2,r3] if x)
print("\n" + "=" * 60)
print("  Research complete | {} total chars | Saved: _gemini_research.md".format(total))
print("=" * 60)

client.close()
