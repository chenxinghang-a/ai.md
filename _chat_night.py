# -*- coding: utf-8 -*-
"""Gemini 3.1 Flash Lite 深度技术夜聊 15轮"""
import sys,os,json,time,httpx,io
if sys.platform=="win32":
    sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8",errors="replace")
    sys.stderr=io.TextIOWrapper(sys.stderr.buffer,encoding="utf-8",errors="replace")

KEY="AIzaSyC0MMf6fQkQsG5kMj9mDeGSKn0i2imhfik"
PX="http://127.0.0.1:7890"
MD="gemini-3.1-flash-lite-preview"
BS="https://generativelanguage.googleapis.com/v1beta/openai"
C=httpx.Client(proxy=PX,timeout=180)
MS=[]; LOG=[]

def ask(q,mx=4000):
    global MS
    MS.append({"role":"user","content":q})
    for r in range(4):
        try:
            x=C.post(BS+"/chat/completions",
                headers={"Authorization":"Bearer "+KEY,"Content-Type":"application/json"},
                json={"model":MD,"messages":MS,"max_tokens":mx,"temperature":0.8})
            d=x.json()
            if isinstance(d,dict) and "error" in d:
                e=d["error"];c=e.get("code","?")
                print(f"    [ERR{c}] {str(e.get('message',''))[:100]}")
                if c in(429,503):time.sleep(12*(r+1));continue
                return f"[ERR{c}] {e.get('message','')[:150]}"
            if isinstance(d,dict) and "choices" in d:
                t=d["choices"][0].get("message",{}).get("content","")
                MS.append({"role":"assistant","content":t});return t
            return "[?]"+str(d)[:200]
        except Exception as e:
            print(f"    [EXC]{e}");time.sleep(6)
    return "[FAIL]"

def log(u,a,n):
    LOG.append(f"\n{'='*60}\n[Round {n}]\n\n>>> 用户:\n{u}\n\n<<< Gemini 3.1 Flash Lite:\n{a or '(无响应)'}")
    c=len(a)if a else 0;print(f"  R{n}: OK {c}ch");return a

print("="*60);print("  Gemini 3.1 Flash Lite - 技术夜聊 15轮");print("="*60)

R=0
R+=1;log(ask("你好！先自我介绍一下——你是什么模型版本？训练数据截止时间？强项和短板？"),"",R)

R+=1;log(ask(f"我在做Windows桌面自动化Agent。架构：截图→YOLOv8检测UI元素→OCR增强→LLM决策(Gemini)→pyautogui执行。实测发现LLM空间推理很差，经常输出错误坐标。核心瓶颈在哪？如果让你重新设计你会怎么改？给出完整方案。",3000),"",R)

R+=1;log(ask("YOLO用的通用coco预训练模型，桌面图标全标成'image'没语义区分。针对学习通/微信/Chrome这几个目标应用做微调可行吗？需要多少标注数据？有没有零样本或少样本的替代方案？",2500),"",R)

R+=1;log(ask("LLM空间坐标问题具体怎么解？坐标归一化、锚点参考、相对坐标系——哪个最靠谱？有没有工业界验证过的方案？请给代码示例。",2000),"",R)

R+=1;log(ask("设计一个完整的反馈闭环：执行动作后截图对比前后状态→判断成功失败→失败重试→多次失败走降级策略。请写出完整的伪代码或Python框架。",2500),"",R)

R+=1;log(ask("Windows UI Automation API（UIA）vs 纯视觉识别 vs OCR，三者在桌面自动化场景下的优劣对比？pywinauto/uiautomation/win32gui你推荐哪个？Electron/WebView应用的控件树特别乱怎么处理？",2000),"",R)

R+=1;log(ask("本地跑视觉小模型替代云端Gemini？Qwen2-VL-7B / MiniCPM-V-2.6 / Phi-3-Vision 在RTX 5060 Laptop(8GB显存)上能跑吗？速度和准确率够不够做UI元素决策？对比Gemini API差距多大？",2000),"",R)

R+=1;log(ask("Agent的记忆方案：纯prompt塞历史？向量数据库？JSON状态文件？我的是单次任务场景（不是长期运行），哪种最简单有效？给我具体的数据结构设计。",1500),"",R)

R+=1;log(ask("桌面自动化的错误分类体系：弹窗遮挡、页面未加载完、元素位置变化、应用崩溃、网络超时——每种错误的检测方法和应对策略？写成代码框架。",2500),"",R)

R+=1;log(ask("竞品分析：UFO微软 / OmniParser微软 / OS-Copilot港大 / Computer Use Anthropic —— 各自技术路线是什么？谁最强为什么？它们的开源代码哪个值得参考？",2500),"",R)

R+=1;log(ask("pyautogui这个库实际生产能用吗？还是只是玩具级别？和Windows原生API（SendInput/PostMessage/UIAutomation）比差在哪？什么场景下必须放弃pyautogui换原生方案？",2000),"",R)

R+=1;log(ask("多模态输入方案：当前我只发JPEG(detail=low)+文字列表给LLM。如果改发高质量PNG+详细的边界框坐标+OCR文字，决策准确率能提升多少？token成本增加多少？性价比如何？有没有中间路线？",2000),"",R)

R+=1;log(ask("假设我要把这个Agent做成产品卖给大学生用（比如自动刷课、抢课、填表）。技术上还需要补哪些短板？商业化最大风险是什么？合规方面有什么要注意的？",2000),"",R)

R+=1;log(ask("最后问个有趣的：你觉得AI桌面自动化最终形态是什么样的？5年后我们还需要鼠标键盘吗？你眼中的'完美Agent'应该具备什么能力？畅想一下，不用太严谨。",1500),"",R)

R+=1;log(ask("总结一下今晚聊的所有要点，按优先级排个P0-P3清单，每项一句话说清楚。另外给我一个下一步行动建议——明天我应该先做什么改进收益最大？",2000),"",R)

out=os.path.join(os.path.dirname(os.path.abspath(__file__)),"_gemini_chat.txt")
with open(out,"w",encoding="utf-8") as f:
    f.write("Gemini 3.1 Flash Lite 技术夜聊记录\n")
    f.write(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"模型: {MD}\n")
    f.write(f"总轮数: {R}\n")
    f.write("".join(LOG))
total=sum(len(l)for l in LOG)
print(f"\n{'='*60}")
print(f"Done! {R} rounds | {total} chars | Saved: _gemini_chat.txt")
C.close()
