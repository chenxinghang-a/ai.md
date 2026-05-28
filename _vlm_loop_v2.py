# -*- coding: utf-8 -*-
"""
VLM Loop Agent v2 — Screenshot → YOLO Detect → OCR Enhance → Route → Decide → Execute
完整闭环桌面自动化（修复v1所有已知问题）

Improvements over v1:
- P0: SystemLauncher — Win+搜索启动应用（不靠视觉猜图标）
- P3: IntentRouter — launch/Close/screenshot等硬编码拦截
- P1: OCREnhancer — RapidOCR给每个box加文字标签
- P2: ActionHistory — 去重+死循环检测
- Better LLM prompt — 带OCR文字+历史+死循环警告

Usage:
  python _vlm_loop_v2.py "打开学习通上课去"
  python _vlm_loop_v2.py --dry "点击登录按钮"
  python _vlm_loop_v2.py --interactive
"""

import argparse
import sys
import os
import time
import json
import re
import base64

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
from PIL import ImageGrab, Image
from ultralytics import YOLO
import pyautogui

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "_ref", "vlm-yolo-agent", "models")
YOLO_MODEL = os.path.join(MODEL_DIR, "yolov8_ui_model.pt")
YOLO_CONF = 0.35

GEMINI_API_KEY = "AIzaSyC0MMf6fQkQsG5kMj9mDeGSKn0i2imhfik"
GEMINI_MODEL = "gemini-3.1-flash-lite-preview"
PROXY = "http://127.0.0.1:7890"

MAX_TURNS = 15
SCREENSHOT_QUALITY = 85


def get_device():
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda:" + str(torch.cuda.current_device())
    except:
        pass
    return "cpu"


DEVICE = get_device()


def image_to_base64(image_np, max_size=1600):
    h, w = image_np.shape[:2]
    if max(h, w) > max_size:
        scale = max_size / max(h, w)
        image_np = cv2.resize(image_np, (int(w * scale), int(h * scale)))
    buf = __import__("io").BytesIO()
    Image.fromarray(image_np).save(buf, format='JPEG', quality=SCREENSHOT_QUALITY)
    return base64.b64encode(buf.getvalue()).decode('utf-8')


# ═══════════════════════════════════════
# Module 1: SystemLauncher (P0)
# ═══════════════════════════════════════
class SystemLauncher:
    """通过Windows系统搜索启动应用，不依赖视觉"""

    APP_ALIASES = {
        "学习通": "超星学习通", "超星": "超星学习通", "chaoxing": "超星学习通",
        "微信": "微信", "wechat": "WeChat",
        "edge": "Microsoft Edge", "浏览器": "Microsoft Edge",
        "chrome": "Google Chrome", "记事本": "Notepad",
        "b站": "哔哩哔哩", "bilibili": "哔哩哔哩",
        "抖音": "抖音", "qq": "QQ", "钉钉": "钉钉",
        "word": "Word", "excel": "Excel", "ppt": "PowerPoint",
        "vscode": "Visual Studio Code", "steam": "Steam",
    }

    def resolve_app_name(self, name):
        return self.APP_ALIASES.get(name.lower().strip(), name)

    def find_on_desktop(self, app_name):
        """Use Windows API to find app icon on desktop (Gemini R2 recommendation)"""
        try:
            from pywinauto.desktop import Desktop
            from pywinauto import Desktop as PyDesktop
            desktop = PyDesktop(backend="uia")
            try:
                list_view = desktop.window(class_name="Progman").child_window(control_type="List")
                for item in list_view.children():
                    name = item.window_text().strip()
                    if app_name in name or name in app_name:
                        rect = item.rectangle()
                        return {
                            "name": name,
                            "center": ((rect.left + rect.right) // 2,
                                      (rect.top + rect.bottom) // 2),
                            "rect": (rect.left, rect.top, rect.right, rect.bottom),
                        }
            except:
                pass  # Fallback to Win+search
        except ImportError:
            print("       [INFO] pywinauto not installed, using Win+search")
        except Exception as e:
            print("       [INFO] Desktop API failed: {}".format(str(e)[:50]))
        return None

    def launch(self, app_name):
        target = self.resolve_app_name(app_name)
        print("[LAUNCH] Starting: {} -> {}".format(app_name, target))

        # Strategy 1: Try to find and click icon on desktop via Windows API
        found = self.find_on_desktop(target)
        if found:
            print("[LAUNCH] Found on desktop: \"{}\" @ ({},{})".format(
                found["name"], found["center"][0], found["center"][1]))
            try:
                pyautogui.doubleClick(found["center"][0], found["center"][1])
                time.sleep(3.0)
                print("       [OK] Double-clicked desktop icon")
                return True
            except Exception as e:
                print("       [Click failed: {}, fallback to search]".format(e))

        # Strategy 2: Win key + type + enter (universal fallback)
        
        try:
            # Step 1: Win键打开开始菜单/搜索
            pyautogui.press('win')
            time.sleep(0.8)
            
            # Step 2: 输入应用名
            # 用剪贴板输入中文（pyautogui.write不支持中文）
            import subprocess
            subprocess.run(['clip'], input=target.encode('gbk'), check=True, 
                          creationflags=subprocess.CREATE_NO_WINDOW)
            time.sleep(0.2)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(2.0)  # 等待搜索结果出现
            
            # Step 3: 回车启动
            pyautogui.press('enter')
            print("       Pressed Enter, waiting for app...")
            time.sleep(4.0)  # 等待应用启动
            
            print("       [OK] Launch command sent")
            return True
            
        except Exception as e:
            print("       [FAIL] {}".format(e))
            return False


# ═══════════════════════════════════════
# Module 2: IntentRouter (P3)
# ═══════════════════════════════════════
class IntentRouter:
    """意图预路由 — 能硬编码解决的就不麻烦LLM"""

    LAUNCH_PATTERNS = [
        r'^打开\s*(.+)$', r'^启动\s*(.+)$', r'^运行\s+(.+)$',
        r'^launch\s+(.+)$', r'^open\s+(.+)$', r'^run\s+(.+)$',
        r'^去(.+)上课$', r'去(.+)看看$',
    ]
    
    CLOSE_PATTERNS = [
        r'^关闭\s*(.+)$', r'^退出\s*(.+)$', r'^关掉\s+(.+)$',
        r'^close\s+(.+)$', r'^quit\s+(.+)$',
    ]

    def route(self, user_cmd):
        """
        Returns: ("intent_type", param) or None (交给LLM)
        intent_types: launch | close | screenshot | minimize | maximize | scroll
        """
        cmd = user_cmd.strip()
        cmd_lower = cmd.lower()

        # Launch patterns
        for p in self.LAUNCH_PATTERNS:
            m = re.match(p, cmd, re.IGNORECASE)
            if m:
                app = m.group(1).strip()
                if app:
                    return ("launch", app)

        # Close patterns
        for p in self.CLOSE_PATTERNS:
            m = re.match(p, cmd, re.IGNORECASE)
            if m:
                app = m.group(1).strip()
                if app:
                    return ("close", app)

        # Simple commands
        if re.search(r'截[图屏]|screenshot|截个屏', cmd_lower):
            return ("screenshot", None)
        if re.search(r'最小化|minimize', cmd_lower):
            return ("minimize", None)
        if re.search(r'最大化|maximize', cmd_lower):
            return ("maximize", None)
        if re.search(r'(向下|往下|page.?down).*滚|scroll down', cmd_lower):
            return ("scroll_down", None)
        if re.search(r'(向上|往上|page.?up).*滚|scroll up', cmd_lower):
            return ("scroll_up", None)

        return None  # Let LLM handle it


# ═══════════════════════════════════════
# Module 3: OCREnhancer (P1)
# ═══════════════════════════════════════
class OCREnhancer:
    """给YOLO检测框加上OCR文字识别"""

    def __init__(self):
        try:
            from rapidocr_onnxruntime import RapidOCR
            self.engine = RapidOCR()
            print("[OCR] RapidOCR initialized")
        except ImportError:
            print("[OCR] RapidOCR not found, OCR disabled")
            self.engine = None

    def enhance(self, screenshot, detections):
        """给每个detection加上text字段"""
        if not self.engine or not detections:
            return detections

        total = len(detections)
        for i, det in enumerate(detections):
            x1, y1, x2, y2 = map(int, det['box'])
            w, h = x2 - x1, y2 - y1

            if w < 20 or h < 20:
                det['text'] = ''
                continue

            crop_img = screenshot[y1:y2, x1:x2]
            if crop_img.size == 0:
                det['text'] = ''
                continue

            try:
                # RapidOCR returns: [[[x1,y1],[x2,y2],[x3,y3],[x4,y4]], text_string, confidence_float]
                # NOT: [[...], (text, conf)]  ← this was the BUG!
                result, _ = self.engine(crop_img)
                text = ""
                if result and isinstance(result, list):
                    # Upscale small icons before OCR for better recognition
                    if w < 60 or h < 60:
                        crop_img = cv2.resize(crop_img, None, fx=2.0, fy=2.0,
                                              interpolation=cv2.INTER_CUBIC)
                        result2, _ = self.engine(crop_img)
                        if result2 and isinstance(result2, list):
                            result = result2
                    
                    texts = [line[1] for line in result 
                             if isinstance(line, (list,tuple)) and len(line) >= 2]
                    text = "".join(texts).strip()

                det['text'] = text

                # Type refinement based on OCR text
                if text:
                    if re.search(r'https?://|www\.', text):
                        det['type'] = 'link_text'
                    elif len(text) <= 6 and det['type'] == 'image':
                        det['type'] = 'app_icon'
                    elif len(text) <= 15 and det['type'] in ('button', 'image'):
                        det['type'] = 'button_label'

                label = text[:12] if text else "(empty)"
                print("       [OCR {}/{}] {} -> \"{}\"".format(i+1, total, det['type'], label))

            except Exception as e:
                det['text'] = ''

        return detections


# ═══════════════════════════════════════
# Module 4: ActionHistory (P2)
# ═══════════════════════════════════════
class ActionHistory:
    """动作历史管理 + 去重 + 死循环检测"""

    def __init__(self, max_history=10, dup_threshold=25):
        self.history = []      # [(action_str, coord), ...]
        self.max_h = max_history
        self.dup_thresh = dup_threshold  # 像素容差

    def push(self, action_json, coord=None):
        entry = {"action": action_json, "coord": coord, "time": time.time()}
        self.history.append(entry)
        if len(self.history) > self.max_h:
            self.history.pop(0)

    def is_duplicate(self, new_coord):
        """新坐标是否与最近动作重复"""
        if not new_coord or not self.history:
            return False, 0
        
        last = self.history[-1]
        last_coord = last.get("coord")
        if not last_coord:
            return False, 0
        
        dist = abs(new_coord[0] - last_coord[0]) + abs(new_coord[1] - last_coord[1])
        is_dup = dist < self.dup_thresh
        return is_dup, dist

    def stuck_count(self, ref_coord=None):
        """计算与ref_coord重复的连续次数"""
        if not ref_coord or not self.history:
            return 0
        
        count = 0
        for h in reversed(self.history):
            c = h.get("coord")
            if c and abs(c[0] - ref_coord[0]) + abs(c[1] - ref_coord[1]) < self.dup_thresh:
                count += 1
            else:
                break
        return count

    def recent_actions(self, n=3):
        """最近n步摘要"""
        recent = self.history[-n:] if len(self.history) >= n else self.history
        return [h["action"] for h in recent]

    def get_stuck_warning(self, coord=None):
        """如果检测到死循环，返回警告文字"""
        if coord:
            stuck = self.stuck_count(coord)
            if stuck >= 2:
                return "WARNING: You have clicked near ({},{}) {} times in a row! This coordinate is NOT responding. Try a different element or action.".format(
                    coord[0], coord[1], stuck + 1)
        return None


# ═══════════════════════════════════════
# Module 5: VLMLoopAgent (Main)
# ═══════════════════════════════════════
class VLMLoopAgent:
    def __init__(self, model=None):
        self.llm_model = model or GEMINI_MODEL
        
        # Init subsystems
        print("[INIT] Loading YOLO: " + YOLO_MODEL)
        self.yolo = YOLO(YOLO_MODEL)
        if DEVICE != "cpu":
            self.yolo.to(DEVICE)
        self.yolo_classes = self.yolo.names
        print("       Device: {} | Classes: {}".format(DEVICE, len(self.yolo_classes)))

        self.launcher = SystemLauncher()
        self.router = IntentRouter()
        self.ocr = OCREnhancer()
        self.history = ActionHistory()
        
        self._init_llm()

    def _init_llm(self):
        from openai import OpenAI
        import httpx as hx
        http_client = hx.Client(proxy=PROXY, timeout=60)
        self.client = OpenAI(
            api_key=GEMINI_API_KEY,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            http_client=http_client,
        )
        print("[LLM] Connected | Model: {}".format(self.llm_model))

    def capture_and_detect(self):
        img = np.array(ImageGrab.grab(all_screens=True))
        t = time.time()
        results = self.yolo.predict(img, save=False, verbose=False, device=DEVICE)[0]
        dt = time.time() - t

        detections = []
        for i, box in enumerate(results.boxes):
            conf = float(box.conf[0])
            if conf < YOLO_CONF:
                continue
            cls_id = int(box.cls[0])
            cls_name = self.yolo_classes[cls_id]
            x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
            detections.append({
                "id": len(detections) + 1,
                "type": cls_name,
                "conf": round(conf, 2),
                "box": [x1, y1, x2, y2],
                "center": [(x1 + x2) // 2, (y1 + y2) // 2],
                "size": [x2 - x1, y2 - y1],
                "text": "",  # Will be filled by OCR
            })

        detections.sort(key=lambda d: d["conf"], reverse=True)
        return img, detections, dt * 1000

    def format_elements_for_llm(self, detections):
        """带OCR文字的元素列表，给LLM看"""
        if not detections:
            return "No UI elements detected."
        lines = ["Detected UI elements (with OCR text):"]
        for d in detections[:30]:
            cx, cy = d["center"]
            txt = d.get("text", "")
            txt_display = " text=\"{}\"".format(txt.replace('"', "'")[:20]) if txt else ""
            lines.append("  #{} {}{} conf={}% @({},{}) size={}x{}".format(
                d["id"], d["type"], txt_display,
                int(d["conf"]*100), cx, cy, d["size"][0], d["size"][1]))
        if len(detections) > 30:
            lines.append("  ... +{} more".format(len(detections) - 30))
        return "\n".join(lines)

    def ask_llm(self, goal, detections, screenshot_b64, turn_num, prev_actions=None, stuck_warning=None):
        """Ask LLM to decide next action"""
        elem_text = self.format_elements_for_llm(detections)

        system_prompt = """You control a Windows PC via mouse and keyboard automation.
You receive a screenshot and detected UI element list WITH TEXT LABELS (from OCR).

CRITICAL RULES:
1. ALWAYS reply with valid JSON only. No markdown, no explanation outside JSON.
2. When elements have text labels (e.g., #5 button_label "登录"), USE THE TEXT to identify targets.
3. NEVER click the same coordinates repeatedly. If previous actions show repeats, pick a DIFFERENT element.
4. If you see a stuck warning, you MUST change strategy immediately.
5. For typing: click field first, then type.
6. Screen: 2560x1440, origin (0,0)=top-left, Y increases downward.

Actions:
- click: {"action":"click","element_id":N}
- type: {"action":"type","element_id":N,"text":"..."}
- key: {"action":"key","key":"enter|tab|escape|win..."}
- hotkey: {"action":"hotkey","keys":["ctrl","a"]}
- scroll: {"action":"scroll","direction":"up|down"}
- wait: {"action":"wait","seconds":N}
- done: {"action":"done","message":"..."}"""

        user_parts = [
            "Goal: {}".format(goal),
            "Turn {}/{}".format(turn_num, MAX_TURNS),
            "",
            elem_text,
        ]
        if prev_actions:
            user_parts.insert(1, "Recent actions: " + "; ".join(prev_actions))
        if stuck_warning:
            user_parts.append("\n" + stuck_warning)

        response = self.client.chat.completions.create(
            model=self.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": [
                    {"type": "image_url", "image_url": {
                        "url": "data:image/jpeg;base64,{}".format(screenshot_b64),
                        "detail": "low"
                    }},
                    {"type": "text", "text": "\n".join(user_parts)}
                ]}
            ],
            max_tokens=300,
            temperature=0.1,
        )
        
        raw = response.choices[0].message.content.strip()
        jm = re.search(r'\{.*\}', raw, re.DOTALL)
        if jm:
            return json.loads(jm.group())
        return {"action": "error", "message": "No JSON in response: " + raw[:100]}

    def execute_action(self, action, detections):
        act = action.get("action", "?")

        if act in ("done",):
            print("\n[DONE] {}".format(action.get("message", "")))
            return "done"
        if act == "error":
            print("[ERR] {}".format(action.get("message", "")))
            return "error"

        coord = None
        target = None

        if act == "wait":
            sec = action.get("seconds", 1)
            print("[WAIT] {}s".format(sec))
            time.sleep(sec)
            return "ok"

        if act == "key":
            k = action.get("key", "")
            print("[KEY] {}".format(k))
            pyautogui.press(k); time.sleep(0.3)
            return "ok"

        if act == "hotkey":
            keys = action.get("keys", [])
            print("[HOTKEY] {}".format("+".join(keys)))
            pyautogui.hotkey(*keys); time.sleep(0.3)
            return "ok"

        if act == "scroll":
            d = action.get("direction", "down")
            pyautogui.scroll(-300 if d == "up" else 300)
            time.sleep(0.5)
            return "ok"

        if act in ("click", "type"):
            eid = action.get("element_id")
            target = next((d for d in detections if d["id"] == eid), None)
            if not target:
                print("[ERR] Element #{} not found!".format(eid))
                return "not_found"
            coord = target["center"]

        if act == "click" and target:
            cx, cy = coord
            print("[CLICK] #{} \"{}\" @ ({},{})".format(target["id"], target.get("text","?"), cx, cy))
            pyautogui.click(cx, cy)
            time.sleep(0.5)
            self.history.push(json.dumps(action), coord)
            return "clicked"

        if act == "type":
            text = action.get("text", "")
            if target:
                cx, cy = coord
                print("[TYPE] #{} then: {}".format(target["id"], repr(text[:30])))
                pyautogui.click(cx, cy); time.sleep(0.4)
            # Clipboard for Chinese text
            import subprocess
            subprocess.run(['clip'], input=text.encode('utf-8'), check=True,
                          creationflags=subprocess.CREATE_NO_WINDOW)
            time.sleep(0.15)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.3)
            self.history.push(json.dumps(action), coord)
            return "typed"

        print("[?] Unknown: {}".format(act))
        return "unknown"

    def run(self, user_cmd, dry_run=False, confirm=False):
        """Main loop"""
        print("\n" + "=" * 60)
        print("  VLM Loop v2 | Goal: {}".format(user_cmd))
        print("  Device: {} | Dry:{} Confirm:{}".format(DEVICE, dry_run, confirm))
        print("=" * 60)

        # Step 0: Intent routing
        intent = self.router.route(user_cmd)
        if intent:
            itype, param = intent
            print("\n[ROUTE] Hard-coded intent: {}({})".format(itype, str(param)[:30]))

            if itype == "launch" and not dry_run:
                self.launcher.launch(param)
                print("\n[DONE] Launched: {}".format(param))
                return
            elif itype == "screenshot":
                img = np.array(ImageGrab.grab(all_screens=True))
                p = os.path.join(BASE_DIR, "_screenshot_{}.png".format(int(time.time())))
                Image.fromarray(img).save(p)
                print("[SAVED] {}".format(p))
                return
            elif itype in ("minimize", "maximize"):
                if not dry_run:
                    pyautogui.hotkey('win', 'd') if itype == "minimize" else None
                print("[WINDOW] {}".format(ityte))
                return
            # Fall through to LLM for other intents

        # Main loop
        for turn in range(1, MAX_TURNS + 1):
            print("\n--- Turn {}/{} ---".format(turn, MAX_TURNS))

            # 1) Capture + Detect
            print("[1/4] Screenshot + YOLO...")
            img, detections, dt_ms = self.capture_and_detect()
            print("     {} elements | {:.0f}ms".format(len(detections), dt_ms))

            # Show top elements
            for d in detections[:8]:
                t = d.get("text", "")
                tl = " \"{}\"".format(t[:10]) if t else ""
                print("     #{} {:<14} {:>3}% @({:>4},{:>4}){}".format(
                    d["id"], d["type"], int(d["conf"]*100), d["center"][0], d["center"][1], tl))
            if len(detections) > 8:
                print("     ... +{} more".format(len(detections) - 8))

            # 2) OCR Enhancement
            print("[2/4] OCR enhancing...")
            t_ocr = time.time()
            detections = self.ocr.enhance(img, detections)
            print("     {:.0f}ms".format((time.time() - t_ocr) * 1000))

            # 3) LLM Decision
            print("[3/4] Asking LLM...")
            b64img = image_to_base64(img)
            recent = self.history.recent_actions(3)

            # Check stuck BEFORE asking LLM
            # Use last coord as reference
            last_coord = self.history.history[-1]["coord"] if self.history.history else None
            stuck_warn = self.history.get_stuck_warning(last_coord)

            action = self.ask_llm(user_cmd, detections, b64img, turn,
                                   prev_actions=recent, stuck_warning=stuck_warn)

            if action.get("action") in ("done",):
                break

            # 4) Execute
            print("[4/4] Execute: {}".format(json.dumps(action, ensure_ascii=False)))
            if dry_run:
                print("[DRY] Skipped execution")
                continue

            if confirm:
                try:
                    c = input("     [y/n/s]? ").strip().lower()
                    if c.startswith('n'): break
                    if c.startswith('s'): continue
                except: break

            result = self.execute_action(action, detections)
            if result == "done":
                break

            time.sleep(0.5)

        print("\n[DONE] Ended after {} turns".format(turn))


def main():
    parser = argparse.ArgumentParser(description="VLM Loop v2 — Enhanced desktop automation")
    parser.add_argument("command", nargs="?", default=None, help="Natural language command")
    parser.add_argument("--dry", "-d", action="store_true", help="Dry run")
    parser.add_argument("--yes", "-y", action="store_true", help="Auto-confirm")
    parser.add_argument("-i", "--interactive", action="store_true", help="Interactive mode")
    args = parser.parse_args()

    agent = VLMLoopAgent()

    if args.interactive or not args.command:
        print("\n=== VLM Loop v2 Interactive ===")
        while True:
            try:
                cmd = input("\n> ").strip()
            except: break
            if not cmd: continue
            if cmd.lower() in ('quit','q','exit'):
                print("Bye!"); break
            d = cmd.startswith("dry:")
            if d: cmd = cmd[4:].strip()
            agent.run(cmd, dry_run=d, confirm=not args.yes and not d)
    else:
        agent.run(args.command, dry_run=args.dry, confirm=not args.yes)


if __name__ == "__main__":
    main()
