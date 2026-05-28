# -*- coding: utf-8 -*-
"""
Local Rule Agent — YOLO detect + keyword matching + pyautogui execute
NO external API needed. Pure local.

Usage:
  python _local_agent.py click button
  python _local_agent.py type "hello world"
  python _local_agent.py find search
  python _local_agent.py interactive
"""

import argparse
import sys
import os
import time
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
from PIL import ImageGrab
from ultralytics import YOLO
import pyautogui

# ── Config ──────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "_ref", "vlm-yolo-agent", "models")
YOLO_MODEL = os.path.join(MODEL_DIR, "yolov8_ui_model.pt")
YOLO_CONF = 0.35


def get_device():
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda:" + str(torch.cuda.current_device())
    except:
        pass
    return "cpu"

DEVICE = get_device()


# ── Keyword→Element Type Mapping ─────────
KEYWORD_MAP = {
    # Action keywords → target element types
    "search": ["field"],
    "input": ["field"],
    "box": ["field"],
    "text box": ["field"],
    "textbox": ["field"],
    "fill": ["field"],
    "enter": ["field"],
    "button": ["button"],
    "btn": ["button"],
    "click": ["button", "link", "image"],  # generic click
    "link": ["link"],
    "url": ["link"],
    "hyperlink": ["link"],
    "image": ["image"],
    "img": ["image"],
    "pic": ["image"],
    "picture": ["image"],
    "heading": ["heading"],
    "title": ["heading"],
    "header": ["heading"],
    "label": ["label", "text"],
    "text": ["text", "label"],
    "checkbox": ["checkbox"],
    "check": ["checkbox"],
    "tick": ["checkbox"],
    "radio": ["radiobutton"],
    "option": ["radiobutton"],
    "select": ["radiobutton"],
    "any": [],  # match all
}

# Position hints in user query
POS_TOP = re.compile(r'\b(top|upper|above|header|navbar|menu bar)\b', re.I)
_POS_BOTTOM = re.compile(r'\b(bottom|lower|below|footer|status|taskbar)\b', re.I)
POS_LEFT = re.compile(r'\b(left|sidebar|side|nav)\b', re.I)
POS_RIGHT = re.compile(r'\b(right)\b', re.I)

# Ordinal words → index
ORDINAL = {
    "first": 0, "second": 1, "third": 2, "fourth": 3, "fifth": 4,
    "sixth": 5, "seventh": 6, "eighth": 7,
    "1st": 0, "2nd": 1, "3rd": 2, "4th": 3, "5th": 4,
}


class LocalAgent:
    def __init__(self):
        print("[LOAD] YOLO: " + YOLO_MODEL)
        self.model = YOLO(YOLO_MODEL)
        if DEVICE != "cpu":
            self.model.to(DEVICE)
        self.classes = self.model.names
        print("       Device: {} | Classes: {}".format(DEVICE, len(self.classes)))

    def capture_and_detect(self):
        """Return (screenshot_rgb_np, detections)"""
        img = np.array(ImageGrab.grab(all_screens=True))
        t = time.time()
        results = self.model.predict(img, save=False, verbose=False,
                                      device=DEVICE)[0]
        dt = time.time() - t

        detections = []
        for i, box in enumerate(results.boxes):
            conf = float(box.conf[0])
            if conf < YOLO_CONF:
                continue
            cls_id = int(box.cls[0])
            cls_name = self.classes[cls_id]
            x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
            detections.append({
                "id": len(detections) + 1,
                "type": cls_name,
                "conf": round(conf, 2),
                "box": [x1, y1, x2, y2],
                "center": [(x1 + x2) // 2, (y1 + y2) // 2],
                "size": [x2 - x1, y2 - y1],
                # position metadata for filtering
                "y_center": (y1 + y2) // 2,
                "x_center": (x1 + x2) // 2,
            })

        detections.sort(key=lambda d: d["conf"], reverse=True)
        return img, detections, dt * 1000

    def parse_command(self, cmd_str):
        """
        Parse natural language command into structured action.
        Returns: {action: str, target_types: list, text: str|None, ordinal: int|None}
        """
        cmd_lower = cmd_str.lower().strip()

        # Detect action type
        action = "click"
        if any(w in cmd_lower for w in ("type", "input ", "write", "enter ", "fill")):
            action = "type"
        elif any(w in cmd_lower for w in ("scroll down", "page down")):
            action = "scroll_down"
        elif any(w in cmd_lower for w in ("scroll up", "page up")):
            action = "scroll_up"
        elif any(w in cmd_lower for w in ("find", "locate", "where is", "show me")):
            action = "find"

        # Extract text to type (in quotes or after certain keywords)
        type_text = None
        if action == "type":
            # Look for quoted text
            m = re.search(r'["\u201c](.+?)["\u201d]', cmd_str)
            if m:
                type_text = m.group(1)
            else:
                # Text after the element keyword
                for kw in ("into", "to", ":"):
                    if kw in cmd_lower:
                        idx = cmd_lower.index(kw) + len(kw)
                        type_text = cmd_str[idx:].strip().strip('"').strip('\u201c').strip('\u201d')
                        break
                if not type_text and ' ' in cmd_str:
                    parts = cmd_str.split(None, 1)
                    if len(parts) > 1:
                        type_text = parts[1]

        # Determine target element types from keywords
        target_types = None  # None = all clickable
        screen_h = 1440  # default, will be updated

        for keyword, types in KEYWORD_MAP.items():
            if keyword in cmd_lower:
                if types:  # specific type mapping
                    target_types = types
                else:
                    target_types = None  # "any" -> all types
                break

        # If no keyword matched but it's a generic action, default to clickable elements
        if target_types is None and action in ("click",):
            target_types = ["button", "link", "field", "checkbox"]

        # Parse ordinal (first, second, etc.)
        ordinal = None
        for word, idx in ORDINAL.items():
            if word in cmd_lower:
                ordinal = idx
                break
        # Also check for "#N" pattern
        m_num = re.search(r'#(\d+)', cmd_str)
        if m_num:
            ordinal = int(m_num.group(1)) - 1

        return {
            "action": action,
            "target_types": target_types,
            "text": type_text,
            "ordinal": ordinal,
            "position_hint": {
                "top": bool(POS_TOP.search(cmd_lower)),
                "bottom": bool(_POS_BOTTOM.search(cmd_lower)),
                "left": bool(POS_LEFT.search(cmd_lower)),
                "right": bool(POS_RIGHT.search(cmd_lower)),
            },
            "raw": cmd_str,
        }

    def select_target(self, detections, parsed_cmd, screen_size=(2560, 1440)):
        """
        Select best target element based on parsed command.
        Returns: detection dict or None
        """
        sw, sh = screen_size
        mid_y = sh // 2
        mid_x = sw // 2

        # Filter by type
        candidates = list(detections)
        if parsed_cmd["target_types"]:
            candidates = [d for d in candidates if d["type"] in parsed_cmd["target_types"]]
            if not candidates:
                # Relax: use all detections
                candidates = list(detections)

        if not candidates:
            return None

        pos_hint = parsed_cmd["position_hint"]
        score_fn = self._make_scorer(pos_hint, sw, sh)

        # Score each candidate
        scored = [(d, score_fn(d)) for d in candidates]
        scored.sort(key=lambda x: x[1], reverse=True)

        # Apply ordinal filter
        ordinal = parsed_cmd.get("ordinal")
        if ordinal is not None and 0 <= ordinal < len(scored):
            return scored[ordinal][0]

        if not scored:
            print("[DEBUG] No candidates matched")
            return None
        return scored[0][0]

    def _make_scorer(self, pos_hint, w, h):
        """Create scoring function based on position hints"""
        mid_x, mid_y = w // 2, h // 2

        def scorer(d):
            score = d["conf"] * 100  # base: confidence
            cx, cy = d["center"][0], d["center"][1]

            # Position bonuses/penalties
            if pos_hint["top"]:
                if cy < mid_y:
                    score += 30
                else:
                    score -= 20
            if pos_hint["bottom"]:
                if cy > mid_y:
                    score += 30
                else:
                    score -= 20
            if pos_hint["left"]:
                if cx < mid_x:
                    score += 20
                else:
                    score -= 10
            if pos_hint["right"]:
                if cx > mid_x:
                    score += 20
                else:
                    score -= 10

            # Size bonus (prefer larger targets for clicking)
            area = d["size"][0] * d["size"][1]
            score += min(area / 10000, 15)

            return score

        return scorer

    def execute_action(self, parsed_cmd, target=None, detections=None):
        """Execute the action"""
        action = parsed_cmd["action"]

        if action == "find":
            if target:
                print("[FIND] Target: #{} {} @ ({},{}) size={}x{}".format(
                    target["id"], target["type"],
                    target["center"][0], target["center"][1],
                    target["size"][0], target["size"][1]))
                # Highlight on screen briefly
                cx, cy = target["center"]
                x1, y1, _, _ = target["box"]
                # Move mouse to target
                pyautogui.moveTo(cx, cy, duration=0.3)
            else:
                print("[FIND] No matching element found")
            return True

        if action == "click":
            if not target:
                print("[CLICK] No target to click!")
                return False
            cx, cy = target["center"]
            tname = target["type"]
            tid = target["id"]
            print("[CLICK] #{} {} at ({}, {})".format(tid, tname, cx, cy))
            pyautogui.click(cx, cy)
            return True

        if action == "type":
            text = parsed_cmd.get("text") or ""
            if target:
                cx, cy = target["center"]
                print("[TYPE] Click #{} {} at ({},{}) then type: {}".format(
                    target["id"], target["type"], cx, cy, repr(text)))
                pyautogui.click(cx, cy)
                time.sleep(0.3)
            print("[TYPE] Inputting: " + repr(text))
            pyautogui.typewrite(text, interval=0.02)
            return True

        if action in ("scroll_up", "scroll_down"):
            amount = 300 if action == "scroll_down" else -300
            print("[SCROLL] {}".format(action))
            pyautogui.scroll(amount)
            return True

        print("[UNKNOWN] Action: {}".format(action))
        return False

    def run(self, cmd_str, dry_run=False, show_img=False):
        """Run one full cycle"""
        print("\n" + "=" * 50)
        print("  > {}".format(cmd_str))
        print("=" * 50)

        # Step 1: Parse
        parsed = self.parse_command(cmd_str)
        print("[PARSE] action={}, types={}, text={}, ordinal={}".format(
            parsed["action"], parsed["target_types"],
            repr(parsed.get("text")), parsed["ordinal"]))

        # Step 2: Detect
        print("[DETECT] Screenshot + YOLO...")
        img, detections, dt_ms = self.capture_and_detect()
        print("       {} elements | {:.0f}ms".format(len(detections), dt_ms))

        if show_img:
            ann = self._annotate(img, detections)
            outpath = os.path.join(BASE_DIR, "_agent_output.png")
            cv2.imwrite(outpath, cv2.cvtColor(ann, cv2.COLOR_RGB2BGR))
            print("[SAVE] " + outpath)

        # Show detected elements
        for d in detections[:10]:
            print("       #{} {:<8} {:>3}% @({:>4},{:>4}) {:>4}x{:<4}".format(
                d["id"], d["type"], int(d["conf"]*100),
                d["center"][0], d["center"][1],
                d["size"][0], d["size"][1]))
        if len(detections) > 10:
            print("       ... +{}".format(len(detections) - 10))

        # Step 3: Select target
        target = self.select_target(detections, parsed,
                                     (img.shape[1], img.shape[0]))
        if target:
            print("[SELECT] #{} {} (conf={}) @ ({},{})".format(
                target["id"], target["type"], target["conf"],
                target["center"][0], target["center"][1]))
        else:
            print("[SELECT] No matching element")

        # Step 4: Execute
        if dry_run:
            print("[DRY RUN] Would: {} target=#{} text={}".format(
                parsed["action"], target["id"] if target else None,
                repr(parsed.get("text"))))
        else:
            self.execute_action(parsed, target, detections)

        total = "\n[DONE]"
        print(total)
        return target, detections

    def _annotate(self, img, detections, highlight_id=None):
        ann = img.copy()
        colors = {}
        for det in detections:
            cls = det["type"]
            if cls not in colors:
                h = sum(ord(c) for c in cls)
                colors[cls] = ((h * 37) % 256, (h * 73) % 256, (h * 131) % 256)
            color = colors[cls]
            x1, y1, x2, y2 = det["box"]
            did = det["id"]
            lw = 4 if did == highlight_id else 2
            if did == highlight_id:
                color = (0, 255, 0)
            cv2.rectangle(ann, (x1, y1), (x2, y2), color, lw)
            lbl = "#" + str(did) + " " + cls + " " + str(round(det["conf"] * 100)) + "%"
            tw, th = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)[0]
            cv2.rectangle(ann, (x1, y1 - th - 6), (x1 + tw, y1), color, -1)
            cv2.putText(ann, lbl, (x1, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255,255,255), 2)
        return ann


def interactive_mode(agent):
    """REPL loop"""
    print("\n=== Local Agent (NO API) ===")
    print("Examples:")
    print('  click button')
    print('  click search')
    print('  type "hello" into search')
    print('  click first button')
    print('  scroll down')
    print('  find search')
    print('  quit')

    while True:
        try:
            cmd = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break
        if not cmd:
            continue
        if cmd.lower() in ("quit", "q", "exit"):
            print("Bye!")
            break
        dry = cmd.startswith("dry:")
        if dry:
            cmd = cmd[4:].strip()
        agent.run(cmd, dry_run=dry)


def main():
    parser = argparse.ArgumentParser(description="Local Agent — YOLO+Rules, no API needed")
    parser.add_argument("command", nargs="?", default=None, help="Command like 'click button'")
    parser.add_argument("--dry", "-d", action="store_true", help="Dry run (no execution)")
    parser.add_argument("--show", "-s", action="store_true", help="Save annotated image")
    parser.add_argument("-i", "--interactive", action="store_true", help="Interactive mode")
    args = parser.parse_args()

    print("=" * 50)
    print("  Local Agent (Pure Offline)")
    print("  Device: " + DEVICE)
    print("=" * 50)

    agent = LocalAgent()

    if args.interactive or not args.command:
        interactive_mode(agent)
    else:
        agent.run(args.command, dry_run=args.dry, show_img=args.show)


if __name__ == "__main__":
    main()
