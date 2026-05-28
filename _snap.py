"""快速截屏看桌面"""
import mss
import mss.tools

with mss.mss() as sct:
    mon = sct.monitors[1]  # 主显示器
    img = sct.grab(mon)
    output = r"C:\Users\cxx\WorkBuddy\Claw\desktop_now.png"
    mss.tools.to_png(img.rgb, img.size, output=output)
    print(f"Desktop saved: {img.width}x{img.height} -> {output}")
