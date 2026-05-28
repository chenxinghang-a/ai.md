"""
定时关机小工具 - Shutdown Timer
支持：定时关机、倒计时关机、立即关机、取消关机
"""
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import datetime
import time
import os
import sys

class ShutdownTimer:
    def __init__(self, root):
        self.root = root
        self.root.title("定时关机")
        self.root.geometry("400x320")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        # 图标
        try:
            self.root.iconbitmap(default=self.resource_path("shutdown.ico"))
        except:
            pass

        self.timer_running = False
        self.remaining_seconds = 0
        self.countdown_id = None

        self._build_ui()
        self._update_status()

    def resource_path(self, relative_path):
        try:
            base_path = sys._MEIPASS
        except:
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, relative_path)

    def _build_ui(self):
        # 标题
        title = tk.Label(self.root, text="定时关机", font=("微软雅黑", 18, "bold"), fg="#333")
        title.pack(pady=(15, 5))

        # 当前时间
        self.time_label = tk.Label(self.root, text="", font=("微软雅黑", 11), fg="#666")
        self.time_label.pack()

        # 状态
        self.status_label = tk.Label(self.root, text="当前状态: 无定时任务", font=("微软雅黑", 10), fg="#0066cc")
        self.status_label.pack(pady=(5, 10))

        # ===== 模式1: 指定时间关机 =====
        frame1 = tk.LabelFrame(self.root, text="指定时间关机", font=("微软雅黑", 9), padx=10, pady=8)
        frame1.pack(fill="x", padx=20, pady=5)

        tk.Label(frame1, text="时:", font=("微软雅黑", 9)).grid(row=0, column=0, padx=2)
        self.hour_combo = ttk.Combobox(frame1, values=[f"{i:02d}" for i in range(24)], width=5, state="readonly")
        self.hour_combo.set(datetime.datetime.now().strftime("%H"))
        self.hour_combo.grid(row=0, column=1, padx=2)

        tk.Label(frame1, text="分:", font=("微软雅黑", 9)).grid(row=0, column=2, padx=2)
        self.min_combo = ttk.Combobox(frame1, values=[f"{i:02d}" for i in range(60)], width=5, state="readonly")
        self.min_combo.set("00")
        self.min_combo.grid(row=0, column=3, padx=2)

        ttk.Button(frame1, text="设定定时关机", command=self._schedule_shutdown).grid(row=0, column=4, padx=(10, 0))

        # ===== 模式2: 倒计时关机 =====
        frame2 = tk.LabelFrame(self.root, text="倒计时关机", font=("微软雅黑", 9), padx=10, pady=8)
        frame2.pack(fill="x", padx=20, pady=5)

        tk.Label(frame2, text="分钟后关机:", font=("微软雅黑", 9)).grid(row=0, column=0, padx=2)
        self.minutes_combo = ttk.Combobox(frame2, values=[1, 5, 10, 15, 30, 45, 60, 90, 120], width=8, state="readonly")
        self.minutes_combo.set(30)
        self.minutes_combo.grid(row=0, column=1, padx=2)

        ttk.Button(frame2, text="开始倒计时", command=self._countdown_shutdown).grid(row=0, column=2, padx=(10, 0))

        # ===== 底部按钮 =====
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill="x", padx=20, pady=(10, 15))

        ttk.Button(btn_frame, text="立即关机", command=self._shutdown_now).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="取消关机", command=self._cancel_shutdown).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="刷新状态", command=self._update_status).pack(side="right", padx=5)

        # 倒计时显示
        self.countdown_label = tk.Label(self.root, text="", font=("微软雅黑", 12, "bold"), fg="#cc3300")
        self.countdown_label.pack(pady=(0, 10))

    def _run_cmd(self, cmd):
        """静默执行命令"""
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        try:
            subprocess.run(cmd, startupinfo=startupinfo, capture_output=True, timeout=5)
        except:
            pass

    def _shutdown_now(self):
        if messagebox.askyesno("确认", "确定要立即关机吗？"):
            self._run_cmd(["shutdown", "/s", "/t", "10", "/c", "定时关机：10秒后关机"])
            self.status_label.config(text="即将关机... 10秒倒计时")
            self.countdown_label.config(text="正在关机...")

    def _cancel_shutdown(self):
        self._run_cmd(["shutdown", "/a"])
        self.timer_running = False
        self.remaining_seconds = 0
        if self.countdown_id:
            self.root.after_cancel(self.countdown_id)
            self.countdown_id = None
        self.status_label.config(text="当前状态: 已取消关机")
        self.countdown_label.config(text="")

    def _schedule_shutdown(self):
        hour = int(self.hour_combo.get())
        minute = int(self.min_combo.get())
        now = datetime.datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0)

        if target <= now:
            target += datetime.timedelta(days=1)

        delta = (target - now).total_seconds()
        self.remaining_seconds = int(delta)
        self.timer_running = True

        self._run_cmd(["shutdown", "/s", "/t", str(int(delta)), "/c", f"定时关机：将于 {target.strftime('%H:%M')} 关机"])

        self.status_label.config(text=f"已设定: {target.strftime('%H:%M')} 关机")
        self._start_countdown_display()

    def _countdown_shutdown(self):
        minutes = int(self.minutes_combo.get())
        self.remaining_seconds = minutes * 60
        self.timer_running = True

        self._run_cmd(["shutdown", "/s", "/t", str(self.remaining_seconds), "/c", f"定时关机：{minutes}分钟后关机"])

        self.status_label.config(text=f"已设定: {minutes}分钟后关机")
        self._start_countdown_display()

    def _start_countdown_display(self):
        def update():
            if not self.timer_running or self.remaining_seconds <= 0:
                return

            m, s = divmod(self.remaining_seconds, 60)
            h, m = divmod(m, 60)
            if h > 0:
                text = f"剩余 {h}小时 {m}分钟 {s}秒"
            else:
                text = f"剩余 {m}分钟 {s}秒"
            self.countdown_label.config(text=text)
            self.remaining_seconds -= 1
            self.countdown_id = self.root.after(1000, update)

        update()

    def _update_status(self):
        """查询系统当前关机状态"""
        try:
            result = subprocess.run(
                ["shutdown", "/a"],
                capture_output=True, text=True, timeout=5,
                startupinfo=subprocess.STARTUPINFO()
            )
            output = result.stdout + result.stderr
            if "没有任何" in output or "No such" in output:
                self.status_label.config(text="当前状态: 无定时任务")
                self.countdown_label.config(text="")
                self.timer_running = False
            else:
                self.status_label.config(text="当前状态: ⏰ 有关机任务进行中")
        except:
            pass

        self.root.after(5000, self._update_status)

    def on_close(self):
        if self.timer_running:
            if messagebox.askyesno("提示", "有关机任务进行中，确定要关闭吗？\n（不会取消关机任务）"):
                self.root.destroy()
        else:
            self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ShutdownTimer(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
