"""
🤖 桌面AI助手 v2 — 计算机视觉驱动GUI自动化
=================================================
架构(参考AIDesktopPilot + AI-Computer-use-YOLO):
  Layer 1 截屏: mss快速截屏 → numpy BGR数组
  Layer 2 检测: YOLOv8s定位UI元素 + RapidOCR读文本
  Layer 3 决策: Gemini VLM理解上下文(可选)
  Layer 4 执行: pyautogui模拟鼠标/键盘操作
  Layer 5 工作流: tasks.json任务序列自动执行

功能:
  - detect <元素>     检测UI元素位置并返回坐标
  - click <元素>      检测+点击指定类型UI元素
  - type <文本>       键盘输入文字
  - screenshot        截屏保存
  - ocr               OCR读取屏幕文字
  - run tasks.json    执行任务工作流
  - watch <元素>      实时监控+自动操作(类外挂模式)

用法:
  python _yolo_realtime.py                    # 交互式CLI
  python _yolo_realtime.py --mode watch       # 监控模式
  python _yolo_realtime.py --task tasks.json  # 执行任务文件
"""
import os, sys, time, json, threading, argparse, re
import cv2, numpy as np
import pyautogui
from mss import mss
from ultralytics import YOLO

# ===================== 配置 =====================
CFG = {
    "model": "yolov8s.pt",          # YOLO模型
    "conf": 0.5,                     # 置信度阈值
    "screenshot_dir": r"C:\Users\cxx\WorkBuddy\Claw\hot_screenshots",
    
    # 操作安全
    "failsafe": True,                # 鼠标左上角紧急停止
    "op_pause": 0.1,                 # 每次操作后暂停秒数
    
    # VLM决策(可选,用Gemini)
    "vlm_enabled": False,
    "vlm_url": "http://127.0.0.1:8046/v1/chat/completions",
    
    # 任务默认值
    "retry": 3,                      # 检测失败重试次数
    "detect_interval": 1.0,          # 检测间隔
    
    "verbose": 1,
}

pyautogui.FAILSAFE = CFG["failsafe"]
pyautogui.PAUSE = CFG["op_pause"]


class DesktopAI:
    """桌面AI助手核心 — 基于AIDesktopPilot架构重构"""
    
    def __init__(self, config=None):
        self.cfg = config or CFG
        
        # 屏幕截屏器(mss比pyautogui快)
        self.sct = mss()
        mon = self.sct.monitors[1]
        self.screen_w = mon["width"]
        self.screen_h = mon["height"]
        
        # 加载YOLO
        print(f"⏳ 加载YOLO: {self.cfg['model']}")
        self.yolo = YOLO(self.cfg["model"])
        self.class_names = self.yolo.names
        print(f"   ✅ {len(self.class_names)}个类别")
        
        # 加载OCR
        self._init_ocr()
        
        # 统计
        self.stats = {"detections": 0, "actions": 0, "screenshots": 0}
        
        os.makedirs(self.cfg["screenshot_dir"], exist_ok=True)
        print(f"   ✅ 截图目录: {self.cfg['screenshot_dir']}")
        print(f"   🖥️ 屏幕: {self.screen_w}x{self.screen_h}")

    def _init_ocr(self):
        """初始化RapidOCR"""
        try:
            from rapidocr_onnxruntime import RapidOCR
            self.ocr = RapidOCR()
            self.has_ocr = True
            print("   ✅ OCR引擎: RapidOCR")
        except Exception as e:
            self.ocr = None
            self.has_ocr = False
            print(f"   ⚠️ OCR不可用({e})，回退到cv2")

    # ========== Layer 1: 截屏 ==========
    
    def screenshot(self, save=False, prefix="cap"):
        """
        截取全屏 → 返回numpy BGR(H,W,3)
        save=True时同时保存到文件
        """
        shot = self.sct.grab({"left": 0, "top": 0, 
                               "width": self.screen_w, 
                               "height": self.screen_h})
        frame = np.array(shot)
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        
        if save:
            path = self._save(frame_bgr, prefix)
            return frame_bgr, path
        return frame_bgr

    def _save(self, frame_bgr, prefix="cap"):
        ts = int(time.time() * 1000)
        fname = f"{prefix}_{ts}.png"
        fpath = os.path.join(self.cfg["screenshot_dir"], fname)
        cv2.imwrite(fpath, frame_bgr)
        self.stats["screenshots"] += 1
        if self.cfg["verbose"]:
            print(f"📸 {fpath}")
        return fpath

    # ========== Layer 2: 检测 ==========
    
    def detect(self, target_class=None, conf=None, frame=None):
        """
        YOLO检测UI元素
        参数:
          target_class: str|list — 只返回这些类别(如"person"/["button","link"])
                        None=返回所有
          conf: float — 置信度阈值
          frame: numpy — 已有的帧(None则自动截图)
        返回: list[dict] — [{"box":(x1,y1,x2,y2), "center":(cx,cy), 
                            "conf":0.85, "cls_name":"mouse", "cls_id":0}, ...]
        """
        if frame is None:
            frame = self.screenshot()
        
        conf = conf or self.cfg["conf"]
        results = self.yolo(frame, verbose=False, conf=conf)
        
        targets = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                c = float(box.conf[0])
                cid = int(box.cls[0])
                name = self.class_names[cid]
                
                # 类别过滤
                if target_class:
                    if isinstance(target_class, str):
                        if name.lower() != target_class.lower():
                            continue
                    elif isinstance(target_class, (list, tuple)):
                        if name.lower() not in [t.lower() for t in target_class]:
                            continue
                
                targets.append({
                    "box": (x1, y1, x2, y2),
                    "center": ((x1+x2)//2, (y1+y2)//2),
                    "conf": c,
                    "cls_name": name,
                    "cls_id": cid,
                })
        
        # 按置信度降序
        targets.sort(key=lambda t: t["conf"], reverse=True)
        self.stats["detections"] += len(targets)
        return targets

    def detect_element(self, element_type, retry=None):
        """
        检测指定类型的UI元素(参考AIDesktopPilot的detect_ui_elements)
        找到后返回最高置信度的目标dict，找不到返回None
        
        用法:
          btn = ai.detect_element("cell phone")
          if btn: ai.click_target(btn)
        """
        retry = retry or self.cfg["retry"]
        
        for attempt in range(retry):
            targets = self.detect(target_class=element_type)
            if targets:
                t = targets[0]  # 最高置信度
                if self.cfg["verbose"] >= 1:
                    print(f"  🎯 [{t['cls_name']}] @({t['center'][0]},{t['center'][1]}) "
                          f"conf={t['conf']:.0%}")
                return t
            
            if attempt < retry - 1:
                time.sleep(self.cfg["detect_interval"])
        
        if self.cfg["verbose"]:
            print(f"  ❌ '{element_type}' 未找到({retry}次尝试)")
        return None

    def ocr_screen(self, region=None, frame=None):
        """
        OCR读取屏幕文字
        region: (x1,y1,x2,y2) 只识别该区域
        返回: str — 合并后的文字
        """
        if frame is None:
            frame = self.screenshot()
        
        if region:
            x1, y1, x2, y2 = region
            frame = frame[y1:y2, x1:x2]
        
        if self.has_ocr:
            result, elapse = self.ocr(frame)
            if result:
                texts = [line[1] for line in result]
                return "\n".join(texts)
            return ""
        else:
            # 回退: 无OCR时返回空
            return "(OCR不可用)"

    # ========== Layer 3: VLM决策(可选) ==========
    
    def ask_vlm(self, question, image_path=None):
        """向Gemini VLM提问屏幕内容(需要LiteLLM在8046端口)"""
        if not self.cfg.get("vlm_enabled"):
            return "(VLM未启用)"
        
        try:
            import requests
            
            # 构造消息
            content = []
            if image_path and os.path.exists(image_path):
                import base64
                with open(image_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"}
                })
            content.append({"type": "text", "text": question})
            
            resp = requests.post(
                self.cfg["vlm_url"],
                headers={"Content-Type": "application/json"},
                json={
                    "model": "gemini/gemini-2.5-flash",
                    "messages": [{"role": "user", "content": content}],
                    "max_tokens": 500,
                },
                timeout=30,
            )
            
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"(VLM错误: {e})"

    # ========== Layer 4: 动作执行 ==========
    
    def click_point(self, x, y):
        """点击指定坐标"""
        pyautogui.click(x, y)
        self.stats["actions"] += 1
        if self.cfg["verbose"] >= 1:
            print(f"  🖱️ 点击 ({x},{y})")

    def click_target(self, target):
        """点击检测到的目标中心点"""
        cx, cy = target["center"]
        self.click_point(cx, cy)

    def double_click(self, x=None, y=None, target=None):
        """双击"""
        if target:
            x, y = target["center"]
        pyautogui.doubleClick(x, y)
        self.stats["actions"] += 1
        print(f"  🖱️🖱️ 双击 ({x},{y})")

    def right_click(self, x=None, y=None, target=None):
        """右键"""
        if target:
            x, y = target["center"]
        pyautogui.rightClick(x, y)
        self.stats["actions"] += 1
        print(f"  🖱️R 右键 ({x},{y})")

    def type_text(self, text, interval=0.02):
        """输入文字"""
        pyautogui.write(text, interval=interval)
        self.stats["actions"] += 1
        print(f"  ⌨️ 输入: {text[:50]}{'...' if len(text)>50 else ''}")

    def type_keys(self, *keys):
        """按键组合(如 type_keys('ctrl','a','del'))"""
        pyautogui.hotkey(*keys)
        self.stats["actions"] += 1
        print(f"  ⌨️ 按键: {'+'.join(keys)}")

    def drag(self, start_xy, end_xy, duration=0.5):
        """拖拽从start到end"""
        pyautogui.moveTo(start_xy[0], start_xy[1], duration=0.1)
        pyautogui.dragTo(end_xy[0], end_xy[1], duration=duration)
        self.stats["actions"] += 1
        print(f"  ↔️ 拖拽 {start_xy}→{end_xy}")

    def scroll(self, clicks=3, x=None, y=None):
        """滚动"""
        if x is None or y is None:
            x, y = pyautogui.position()
        pyautogui.scroll(clicks, x=x, y=y)

    # ========== 组合动作 ==========
    
    def detect_and_click(self, element_type, retry=None, conf=None):
        """检测+点击 一条龙(最常用)"""
        target = self.detect_element(element_type, retry=retry)
        if target:
            time.sleep(0.2)  # 短暂等待稳定
            self.click_target(target)
            return True
        return False

    def click_if_exists(self, element_type):
        """存在就点，不存在不报错"""
        target = self.detect_element(element_type, retry=1)
        if target:
            self.click_target(target)
            return True
        return False

    # ========== Layer 5: 工作流 ==========
    
    def execute_tasks(self, task_list):
        """
        执行任务列表(参考AIDesktopPilot的tasks.json格式)
        
        task_list格式:
        [
            {"action": "click", "target": "cell phone"},
            {"action": "wait", "seconds": 2},
            {"action": "type", "text": "hello"},
            {"action": "key", "keys": ["enter"]},
            {"action": "screenshot", "prefix": "step1"},
            {"action": "ocr"},
            {"action": "detect", "target": "person"},
            {"action": "drag", "from": [100,200], "to": [300,400]},
            {"action": "scroll", "clicks": -5},
            {"action": "double_click", "target": "icon"},
            {"action": "loop", "target": "button", "max_attempts": 10, "interval": 2}
        ]
        """
        results = []
        total = len(task_list)
        
        for i, task in enumerate(task_list):
            action = task.get("action", "?").lower()
            idx = i + 1
            
            try:
                if action == "click":
                    ok = self.detect_and_click(task.get("target"))
                    results.append({"step": idx, "status": "✅" if ok else "❌", 
                                   "action": f"click[{task.get('target')}]"})
                
                elif action == "double_click":
                    t = self.detect_element(task.get("target"))
                    if t:
                        self.double_click(target=t)
                        results.append({"step": idx, "status": "✅", "action": "dblclick"})
                    else:
                        results.append({"step": idx, "status": "❌", "action": "dblclick"})
                
                elif action == "right_click":
                    t = self.detect_element(task.get("target"))
                    if t:
                        self.right_click(target=t)
                        results.append({"step": idx, "status": "✅", "action": "rclick"})
                    else:
                        results.append({"step": idx, "status": "❌", "action": "rclick"})
                
                elif action == "type":
                    self.type_text(task.get("text", ""))
                    results.append({"step": idx, "status": "✅", "action": "type"})
                
                elif action == "key":
                    keys = task.get("keys", [])
                    if isinstance(keys, str):
                        keys = [keys]
                    self.type_keys(*keys)
                    results.append({"step": idx, "status": "✅", "action": f"key:{'+'.join(keys)}"})
                
                elif action == "wait":
                    sec = task.get("seconds", 1)
                    time.sleep(sec)
                    results.append({"step": idx, "status": "⏸️", "action": f"wait:{sec}s"})
                
                elif action == "screenshot":
                    _, path = self.screenshot(save=True, prefix=task.get("prefix", "task"))
                    results.append({"step": idx, "status": "📸", "action": path})
                
                elif action == "ocr":
                    text = self.ocr_screen()
                    results.append({"step": idx, "status": "📝", "action": text[:100]})
                
                elif action == "detect":
                    targets = self.detect(target_class=task.get("target"))
                    info = [(t["cls_name"], f"{t['conf']:.0%}", t["center"]) for t in targets[:5]]
                    results.append({"step": idx, "status": f"🎯({len(targets)})", "action": str(info)})
                
                elif action == "drag":
                    frm = tuple(task.get("from", [0, 0]))
                    to = tuple(task.get("to", [100, 100]))
                    dur = task.get("duration", 0.5)
                    self.drag(frm, to, dur)
                    results.append({"step": idx, "status": "✅", "action": "drag"})
                
                elif action == "scroll":
                    clicks = task.get("clicks", 3)
                    self.scroll(clicks)
                    results.append({"step": idx, "status": "✅", "action": f"scroll:{clicks}"})
                
                elif action == "loop":
                    # 循环检测直到出现或超时
                    tgt = task.get("target", "")
                    max_n = task.get("max_attempts", 10)
                    interval = task.get("interval", 2)
                    found = False
                    for n in range(max_n):
                        t = self.detect_element(tgt, retry=1)
                        if t:
                            self.click_target(t)
                            found = True
                            break
                        time.sleep(interval)
                    results.append({
                        "step": idx, 
                        "status": "✅" if found else "❌", 
                        "action": f"loop:{tgt}×{max_n}"
                    })
                
                else:
                    results.append({"step": idx, "status": "❓", "action": f"未知:{action}"})
                    
            except Exception as e:
                results.append({"step": idx, "status": "💥", "action": f"错误:{e}"})
        
        # 打印摘要
        print(f"\n{'='*50}")
        print(f"  任务完成 {sum(1 for r in results if '✅' in r['status'])}/{total}")
        print(f"{'='*50}")
        for r in results:
            print(f"  [{r['step']:>2}] {r['status']} {r['action']}")
        print(f"\n  统计: 检测={self.stats['detections']} 操作={self.stats['actions']} "
              f"截图={self.stats['screenshots']}")
        
        return results

    # ========== Watch模式(实时监控) ==========
    
    def watch(self, target_classes=None, mode="click", interval=2.0, conf=None):
        """
        实时监控模式 — 类游戏外挂/辅助瞄准
        检测到目标后自动执行动作
        
        mode: click/double_click/right_click/follow(鼠标跟随)/log(只记录)
        """
        import ctypes
        user32 = ctypes.windll.user32
        VK_ESC = 0x1B
        VK_SPACE = 0x20
        
        if target_classes is None:
            target_classes = []
        elif isinstance(target_classes, str):
            target_classes = [target_classes]
        
        print(f"\n{'='*50}")
        print(f"  🔍 监控模式启动")
        print(f"  目标: {target_classes or '(全部)'}")
        print(f"  动作: {mode} | 间隔: {interval}s | ESC退出 | Space暂停")
        print(f"{'='*50}\n")
        
        paused = False
        last_action_time = 0
        cooldown = 1.0  # 操作冷却
        
        while True:
            # ESC退出
            if user32.GetAsyncKeyState(VK_ESC) & 0x8000:
                print("\n[ESC] 停止监控")
                break
            
            # Space暂停
            if user32.GetAsyncKeyState(VK_SPACE) & 0x8000:
                paused = not paused
                print(f"[Space] {'⏸️暂停' if paused else '▶️继续'}")
                time.sleep(0.3)
                continue
            
            if paused:
                time.sleep(0.1)
                continue
            
            t0 = time.time()
            
            # 截屏+检测
            frame = self.screenshot()
            targets = self.detect(target_class=target_classes or None, 
                                 conf=conf, frame=frame)
            
            if targets:
                top = targets[0]
                now = time.time()
                elapsed = now - t0
                
                info = (f"🎯 {top['cls_name']} {top['conf']:.0%} "
                       f"@({top['center'][0]},{top['center'][1]}) "
                       f"[{len(targets)}个] {(1/elapsed):.1f}FPS")
                print(info)
                
                # 执行动作
                if mode == "click" and now - last_action_time > cooldown:
                    self.click_target(top)
                    last_action_time = now
                elif mode == "double_click" and now - last_action_time > cooldown:
                    self.double_click(target=top)
                    last_action_time = now
                elif mode == "right_click" and now - last_action_time > cooldown:
                    self.right_click(target=top)
                    last_action_time = now
                elif mode == "follow":
                    # 平滑跟随
                    mx, my = pyautogui.position()
                    nx = int(mx + (top["center"][0] - mx) * 0.3)
                    ny = int(my + (top["center"][1] - my) * 0.3)
                    pyautogui.moveTo(nx, ny, duration=0.05)
                # log模式只打印，不操作
            
            # 控制帧率
            elapsed = time.time() - t0
            sleep_time = interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)


def load_tasks(path):
    """加载tasks.json"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ==================== CLI ====================

def print_banner():
    print("""
╔═══════════════════════════════════════╗
║     🤖 桌面AI助手 v2                  ║
║     截屏→YOLO检测→LLM决策→自动化操作   ║
╚═══════════════════════════════════════╝""")


def interactive_mode(ai):
    """交互式命令行"""
    print("\n可用命令:")
    print("  detect <类别>     检测UI元素")
    print("  click <类别>      检测+点击")
    print("  dclick <类别>     双击")
    print("  screenshot / ss   截屏")
    print("  ocr               读屏幕文字")
    print("  type <文字>       输入文字")
    print("  key <按键>        按键(如'enter', 'ctrl a')")
    print("  watch <类别>      开始实时监控")
    print("  run <文件.json>   执行任务文件")
    print("  stats             统计信息")
    print("  quit / q          退出\n")
    
    while True:
        try:
            cmd = input("🦞 AI> ").strip()
            if not cmd:
                continue
            
            parts = cmd.split(maxsplit=1)
            action = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""
            
            if action in ("quit", "q", "exit"):
                break
            
            elif action == "detect":
                if arg:
                    targets = ai.detect(target_class=arg)
                else:
                    targets = ai.detect()
                for t in targets[:10]:
                    print(f"  🎯 {t['cls_name']:15s} {t['conf']:.0%}  "
                          f"box={t['box']}  center={t['center']}")
                if not targets:
                    print("  (无检测结果)")
            
            elif action == "click":
                if arg:
                    ai.detect_and_click(arg)
                else:
                    print("  用法: click <类别名>")
            
            elif action in ("dclick", "dc"):
                t = ai.detect_element(arg)
                if t:
                    ai.double_click(target=t)
            
            elif action in ("screenshot", "ss"):
                prefix = arg or "manual"
                ai.screenshot(save=True, prefix=prefix)
            
            elif action == "ocr":
                text = ai.ocr_screen()
                print(f"--- 屏幕文字 ---\n{text}\n---")
            
            elif action == "type":
                if arg:
                    ai.type_text(arg)
                else:
                    print("  用法: type <要输入的文字>")
            
            elif action == "key":
                if arg:
                    keys = arg.split()
                    ai.type_keys(*keys)
                else:
                    print("  用法: key <按键组合> (如 'ctrl a del' 或 'enter')")
            
            elif action == "watch":
                cls = arg.split()[0] if arg else None
                ai.watch(target_classes=cls, mode="click", interval=1.5)
            
            elif action == "follow":
                cls = arg.split()[0] if arg else None
                ai.watch(target_classes=cls, mode="follow", interval=0.5)
            
            elif action == "run":
                if arg.endswith(".json"):
                    tasks = load_tasks(arg)
                    ai.execute_tasks(tasks)
                else:
                    print(f"  任务文件不存在: {arg}")
            
            elif action == "stats":
                print(f"\n  统计:")
                print(f"  检测次数: {ai.stats['detections']}")
                print(f"  操作次数: {ai.stats['actions']}")
                print(f"  截图数量: {ai.stats['screenshots']}")
            
            else:
                print(f"  未知命令: {action}")
        
        except KeyboardInterrupt:
            print("\n")
            continue
        except Exception as e:
            print(f"  错误: {e}")


def main():
    parser = argparse.ArgumentParser(description="🤖 桌面AI助手 v2")
    parser.add_argument("--mode", default="interactive",
                       help="运行模式: interactive/watch/task")
    parser.add_argument("--model", default=CFG["model"])
    parser.add_argument("--conf", type=float, default=None)
    parser.add_argument("--target", default=None,
                       help="watch模式下要监控的目标类别")
    parser.add_argument("--watch-mode", default="click",
                       choices=["click","double_click","right_click","follow","log"],
                       help="watch模式的动作")
    parser.add_argument("--interval", type=float, default=1.5,
                       help="watch模式检测间隔(秒)")
    parser.add_argument("--task", default=None,
                       help="要执行的tasks.json路径")
    parser.add_argument("--vlm", action="store_true",
                       help="启用VLM(Gemini)决策层")
    args = parser.parse_args()
    
    print_banner()
    
    # 应用参数
    cfg = dict(CFG)
    cfg["model"] = args.model
    if args.conf:
        cfg["conf"] = args.conf
    cfg["vlm_enabled"] = args.vlm
    
    # 初始化
    ai = DesktopAI(cfg)
    
    # 选择模式
    if args.mode == "watch":
        ai.watch(target_classes=args.target, mode=args.watch_mode, 
                interval=args.interval, conf=args.conf)
    
    elif args.mode == "task":
        if args.task:
            tasks = load_tasks(args.task)
            ai.execute_tasks(tasks)
        else:
            print("❌ --task模式需要指定任务文件路径")
    
    else:
        interactive_mode(ai)


if __name__ == "__main__":
    main()
