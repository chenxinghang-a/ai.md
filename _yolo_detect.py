# -*- coding: utf-8 -*-
"""
YOLO UI Detector — Route B core
Screenshot -> YOLOv8 detect -> coordinates -> click

Usage:
  python _yolo_detect.py              # screenshot + detect + show
  python _yolo_detect.py --click 3    # click element #3
  python _yolo_detect.py --model ui   # use Web UI model (default)
  python _yolo_detect.py --list       # list only, no window
"""

import argparse
import sys
import time
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
from PIL import ImageGrab
from ultralytics import YOLO

# Auto-detect GPU
def get_device():
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda:" + str(torch.cuda.current_device())
    except:
        pass
    return "cpu"

DEVICE = get_device()
if DEVICE != "cpu":
    import torch
    print("[GPU] Device: {} ({})".format(DEVICE, torch.cuda.get_device_name(0)))
else:
    print("[GPU] CPU mode (no CUDA PyTorch)")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "_ref", "vlm-yolo-agent", "models")

MODELS = {
    "ui": "yolov8_ui_model.pt",
    "ui100": "yolov8_ui_100.pt",
    "mobile": "chunk02_best.pt",
    "mobile1": "chunk01_best.pt",
    "yolov8s": "yolov8s.pt",
}

ALIASES = {
    "button": ["button"],
    "link": ["link"],
    "input": ["field", "edittext"],
    "text": ["text", "heading", "label"],
    "image": ["image"],
    "checkbox": ["checkbox"],
    "radio": ["radiobutton"],
    "clickable": ["button", "link", "checkbox", "radiobutton", "togglebutton"],
}


class YOLOUIDetector:
    def __init__(self, model_name="ui", conf=0.5):
        model_path = os.path.join(MODEL_DIR, MODELS.get(model_name, MODELS["ui"]))
        if not os.path.exists(model_path):
            raise FileNotFoundError("Model not found: " + model_path)
        print("[LOAD] Model: " + model_path)
        self.model = YOLO(model_path)
        if DEVICE != "cpu":
            self.model.to(DEVICE)
        self.conf = conf
        self.class_names = self.model.names
        print("       Classes(" + str(len(self.class_names)) + "): " + str(self.class_names))

    def screenshot(self):
        img = ImageGrab.grab(all_screens=True)
        return np.array(img)

    def detect(self, image=None, filter_classes=None):
        if image is None:
            image = self.screenshot()

        results = self.model.predict(image, save=False, verbose=False,
                                      device=DEVICE)[0]

        detections = []
        for i, box in enumerate(results.boxes):
            conf = float(box.conf[0])
            if conf < self.conf:
                continue

            cls_id = int(box.cls[0])
            cls_name = self.class_names[cls_id]
            x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())

            if filter_classes:
                fcls = [c.lower() for c in filter_classes]
                if cls_name.lower() not in fcls and "all" not in fcls:
                    continue

            detections.append({
                "id": i + 1,
                "class_name": cls_name,
                "confidence": round(conf, 3),
                "box": (x1, y1, x2, y2),
                "center": ((x1 + x2) // 2, (y1 + y2) // 2),
                "size": (x2 - x1, y2 - y1),
            })

        detections.sort(key=lambda d: d["confidence"], reverse=True)
        return detections

    def annotate(self, image, detections, highlight_id=None):
        ann = image.copy()
        colors = {}

        for det in detections:
            cls = det["class_name"]
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

            lbl = "#" + str(did) + " " + cls + " " + str(round(det["confidence"] * 100)) + "%"
            tw, th = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)[0]
            cv2.rectangle(ann, (x1, y1 - th - 6), (x1 + tw, y1), color, -1)
            cv2.putText(ann, lbl, (x1, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

        return ann

    def format_detections(self, detections):
        if not detections:
            return "[!] No UI elements detected"

        hdr = "{:>3} {:<12} {:<7} {:<16} {:<10}".format("#", "Type", "Conf", "Coord(L,T)", "Size(W*H)")
        lines = [hdr]
        lines.append("-" * 55)

        for d in detections:
            x1, y1 = d["box"][0], d["box"][1]
            w, h = d["size"]
            line = "{:>3} {:<12} {:.1%} ({:>4},{:>4})   {:>3}*{:>3}".format(
                d["id"], d["class_name"], d["confidence"], x1, y1, w, h
            )
            lines.append(line)

        lines.append("-" * 55)
        from collections import Counter
        counts = Counter(d["class_name"] for d in detections)
        summary = ", ".join("{}:{}".format(k, v) for k, v in counts.items())
        lines.append("Total: {} elements | {}".format(len(detections), summary))

        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="YOLO UI Element Detector")
    parser.add_argument("--model", "-m", default="ui", choices=list(MODELS.keys()))
    parser.add_argument("--conf", "-c", type=float, default=0.5)
    parser.add_argument("--filter", "-f", default=None)
    parser.add_argument("--list", "-l", action="store_true")
    parser.add_argument("--click", type=int, default=None)
    parser.add_argument("--save", "-s", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    detector = YOLOUIDetector(model_name=args.model, conf=args.conf)

    print("[CAP] Screenshotting...")
    screenshot = detector.screenshot()
    print("      Resolution: {}x{}".format(screenshot.shape[1], screenshot.shape[0]))

    filter_cls = None
    if args.filter:
        if args.filter in ALIASES:
            filter_cls = ALIASES[args.filter]
        else:
            filter_cls = [f.strip() for f in args.filter.split(",")]
        print("[FLT] Filter: " + str(filter_cls))

    print("[DET] Detecting... (threshold={})".format(args.conf))
    t0 = time.time()
    detections = detector.detect(screenshot, filter_classes=filter_cls)
    dt = time.time() - t0
    print("[TIM] Inference: {:.0f}ms ({})".format(dt * 1000, DEVICE))

    info_text = detector.format_detections(detections)
    print("\n" + info_text)

    if args.json:
        json_out = json.dumps(detections, ensure_ascii=False, indent=2)
        if args.save:
            jpath = args.save.rsplit(".", 1)[0] + ".json"
            with open(jpath, "w", encoding="utf-8") as fp:
                fp.write(json_out)
            print("[SAV] JSON saved: " + jpath)
        else:
            print("\n--- JSON ---\n" + json_out)

    if args.click is not None:
        if args.click < 1 or args.click > len(detections):
            print("[ERR] Invalid ID: {} (range 1-{})".format(args.click, len(detections)))
            return

        target = detections[args.click - 1]
        cx, cy = target["center"]
        import pyautogui
        print("[CLK] Click #{}: {} @ ({}, {})".format(args.click, target["class_name"], cx, cy))
        pyautogui.click(cx, cy)
        return

    annotated = detector.annotate(screenshot, detections, highlight_id=args.click)

    if args.save:
        cv2.imwrite(args.save, cv2.cvtColor(annotated, cv2.COLOR_RGB2BGR))
        print("[SAV] Saved: " + args.save)
    elif not args.list:
        win_name = "YOLO UI Detection (model={}, found={})".format(args.model, len(detections))
        display_img = cv2.cvtColor(annotated, cv2.COLOR_RGB2BGR)

        h, w = display_img.shape[:2]
        max_h = 900
        if h > max_h:
            scale = max_h / h
            display_img = cv2.resize(display_img, (int(w * scale), max_h))

        cv2.imshow(win_name, display_img)
        print("\nPress Q to close | Press S to save")
        while True:
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == ord('Q'):
                break
            elif key == ord('s') or key == ord('S'):
                outpath = os.path.join(BASE_DIR, "_yolo_output_" + str(int(time.time())) + ".png")
                cv2.imwrite(outpath, display_img)
                print("[SAV] Saved: " + outpath)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
