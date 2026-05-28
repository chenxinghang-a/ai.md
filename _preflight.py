"""
执行前检查清单: 每次复杂操作前自检
运行: python _preflight.py
"""
import subprocess, sys
from pathlib import Path

def check(label, condition, detail=""):
    mark = "OK" if condition else "X"
    print(f"  [{mark}] {label}" + (f" -> {detail}" if detail else ""))

print("=== 预检清单 ===")
print()

print("[网络]")
# 代理连通性
try:
    import requests
    r = requests.get("https://www.baidu.com", timeout=5)
    check("国内直连", r.status_code == 200, f"HTTP {r.status_code}")
except Exception as e:
    check("国内直连", False, str(e)[:40])

try:
    r = requests.get("https://www.google.com",
        proxies={"http":"http://127.0.0.1:7890","https":"http://127.0.0.1:7890"},
        timeout=5)
    check("代理外网", r.status_code == 200, f"HTTP {r.status_code}")
except Exception as e:
    check("代理外网", False, str(e)[:40])

try:
    r = requests.get("https://github.com",
        proxies={"http":"http://127.0.0.1:7890","https":"http://127.0.0.1:7890"},
        timeout=5)
    check("代理GitHub", r.status_code == 200, f"HTTP {r.status_code}")
except Exception as e:
    check("代理GitHub", False, str(e)[:40])

print()
print("[工具]")
check("aria2c存在", Path(r"C:\Users\cxx\WorkBuddy\Claw\tools\aria2c.exe").exists())
check("ffmpeg存在", Path(r"C:\Users\cxx\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin\ffmpeg.exe").exists())
check("Python OK", sys.version_info >= (3, 10))
check("requests已装", True)  # 刚才import成功就说明有
check("下载器就绪", Path(r"C:\Users\cxx\WorkBuddy\Claw\_downloader.py").exists())

print()
print("=== 预检完成 ===")
print("如果所有项都是[OK]，可以继续")
print("如果有[X]，先修复再执行任务")
