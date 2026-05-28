"""MiMo TTS 桌面工具 v4 - 标准合成 + 音色设计 + 音色克隆"""
import requests, base64, json, os, threading, time, tkinter as tk
from pathlib import Path
from tkinter import ttk, scrolledtext, messagebox

API_KEY = 'sk-c5v87e5atqiq0eaasn9lv0qff6gt5ivqak9hilep6yf4ahs4'
API_URL = 'https://api.xiaomimimo.com/v1/chat/completions'
OUT_DIR = Path.home() / 'Desktop' / 'MiMo语音'
OUT_DIR.mkdir(exist_ok=True)
VOICE_DIR = OUT_DIR / '音色库'
VOICE_DIR.mkdir(exist_ok=True)

VOICES = ['冰糖', '茉莉', '苏打', '白桦']
STYLES = ['活泼可爱，元气满满，像动漫角色', '俏皮少女，语速轻快，带撒娇感',
          '温柔亲切，语速适中', '沉稳专业，正式播报', '慵懒随意，像朋友聊天']
TEXT_TPL = {
    '派蒙-开心': '（开心）哇！好厉害！（兴奋）旅行者你太棒啦！[停顿]嘿嘿，派蒙早就知道你能行！',
    '派蒙-俏皮': '（俏皮）诶嘿~被你发现啦！（得意）派蒙可是很厉害的向导哦！[小声]虽然有时候也会迷路啦…',
    '派蒙-发现': '（开心）快看快看！前面有宝箱！（兴奋）我们快去打开吧！[碎碎念]不知道里面会有什么好东西呢~',
    '普通-问候': '你好，今天天气真不错，适合出去走走。',
}

MODES = ['标准合成', '音色设计', '音色克隆']

class TTSApp:
    def __init__(self):
        self.win = tk.Tk()
        self.win.title('MiMo 语音合成 v4')
        self.win.geometry('660x700')
        self.win.resizable(False, False)
        main = ttk.Frame(self.win, padding=16)
        main.pack(fill=tk.BOTH, expand=True)
        ttk.Label(main, text='小米 MiMo 语音合成', font=('微软雅黑', 16, 'bold')).pack(pady=(0, 8))

        # 模式
        fm = ttk.Frame(main)
        fm.pack(fill=tk.X, pady=4)
        ttk.Label(fm, text='模式:', width=6).pack(side=tk.LEFT)
        self.mode_var = tk.StringVar(value='标准合成')
        self.mode_cb = ttk.Combobox(fm, textvariable=self.mode_var, values=MODES, state='readonly', width=16)
        self.mode_cb.pack(side=tk.LEFT, padx=4)
        self.mode_cb.bind('<<ComboboxSelected>>', self.on_mode_change)

        # 选择器 (音色/样本/描述)
        self.sel_frame = ttk.Frame(main)
        self.sel_frame.pack(fill=tk.X, pady=4)
        self.sel_label = ttk.Label(self.sel_frame, text='音色:', width=8)
        self.sel_label.pack(side=tk.LEFT)
        self.sel_var = tk.StringVar(value='冰糖')
        self.sel_cb = ttk.Combobox(self.sel_frame, textvariable=self.sel_var, state='readonly', width=42)
        self.sel_cb.pack(side=tk.LEFT, padx=4)

        # 台词模板
        ft = ttk.Frame(main)
        ft.pack(fill=tk.X, pady=4)
        ttk.Label(ft, text='台词模板:', width=8).pack(side=tk.LEFT)
        self.tpl_var = tk.StringVar(value='(无)')
        ttk.Combobox(ft, textvariable=self.tpl_var, values=['(无)'] + list(TEXT_TPL.keys()), state='readonly', width=40).pack(side=tk.LEFT, padx=4)
        self.tpl_var.trace_add('write', self.on_template)

        # 风格
        ttk.Label(main, text='说话风格:').pack(anchor=tk.W)
        self.style_var = tk.StringVar(value='活泼可爱，元气满满，像动漫角色')
        ttk.Combobox(main, textvariable=self.style_var, values=STYLES, state='normal', width=60).pack(fill=tk.X, pady=(0, 6))

        # 文本
        ttk.Label(main, text='台词文本:').pack(anchor=tk.W)
        self.text_box = scrolledtext.ScrolledText(main, height=9, font=('微软雅黑', 11))
        self.text_box.pack(fill=tk.BOTH, expand=True, pady=4)
        self.text_box.insert('1.0', '（开心）哇！好厉害！旅行者你太棒啦！')

        # 按钮
        f2 = ttk.Frame(main)
        f2.pack(fill=tk.X, pady=6)
        self.status = ttk.Label(f2, text='就绪', foreground='gray')
        self.status.pack(side=tk.LEFT)
        self.btn = ttk.Button(f2, text='生成语音', command=self.generate, width=14)
        self.btn.pack(side=tk.RIGHT)

        # 初始化选择器
        self.on_mode_change()
        self.win.protocol('WM_DELETE_WINDOW', self.win.destroy)

    def on_mode_change(self, event=None):
        mode = self.mode_var.get()
        if mode == '标准合成':
            self.sel_label.config(text='音色:')
            self.sel_cb.config(values=VOICES)
            self.sel_var.set('冰糖')
        elif mode == '音色设计':
            self.sel_label.config(text='音色描述:')
            self.sel_cb.config(state='normal')
            self.sel_cb.config(values=['可爱的少女音色，声音尖细高亢，元气满满'])
            self.sel_var.set('可爱的少女音色，声音尖细高亢，元气满满')
        else:
            self.sel_label.config(text='样本文件:')
            files = list(VOICE_DIR.glob('*.wav')) + list(VOICE_DIR.glob('*.mp3'))
            names = [f.name for f in files]
            if not names:
                names = ['(音色库为空，请先放入.wav样本)']
            self.sel_cb.config(values=names)
            self.sel_var.set(names[0] if names else '(音色库为空)')

    def on_template(self, *args):
        name = self.tpl_var.get()
        if name in TEXT_TPL:
            self.text_box.delete('1.0', tk.END)
            self.text_box.insert('1.0', TEXT_TPL[name])

    def generate(self):
        text = self.text_box.get('1.0', tk.END).strip()
        if not text:
            messagebox.showwarning('提示', '请输入文字')
            return
        self.btn.config(state=tk.DISABLED, text='生成中...')
        self.status.config(text='正在请求API...')
        threading.Thread(target=self._do_tts, args=(text,), daemon=True).start()

    def _do_tts(self, text):
        try:
            mode = self.mode_var.get()
            style = self.style_var.get()
            model = {'标准合成': 'mimo-v2.5-tts', '音色设计': 'mimo-v2.5-tts-voicedesign',
                     '音色克隆': 'mimo-v2.5-tts-voiceclone'}[mode]
            audio_param = {'format': 'wav'}

            if mode == '标准合成':
                audio_param['voice'] = self.sel_var.get()
            elif mode == '音色设计':
                style = self.sel_var.get()
            else:
                fname = self.sel_var.get()
                fpath = VOICE_DIR / fname
                if not fpath.exists():
                    self.win.after(0, self._show_error, f'找不到样本: {fname}')
                    return
                with open(fpath, 'rb') as f:
                    b64 = base64.b64encode(f.read()).decode()
                ext = 'wav' if fname.endswith('.wav') else 'mpeg'
                audio_param['voice'] = f'data:audio/{ext};base64,{b64}'

            r = requests.post(API_URL, headers={'api-key': API_KEY, 'Content-Type': 'application/json'},
                              json={'model': model,
                                    'messages': [{'role': 'user', 'content': style},
                                                 {'role': 'assistant', 'content': text}],
                                    'audio': audio_param}, timeout=60)
            if r.status_code != 200:
                err = r.json().get('error', {}).get('message', r.text[:100])
                self.win.after(0, self._show_error, f'API: {err}')
                return
            d = r.json().get('choices', [{}])[0].get('message', {}).get('audio', {})
            if not isinstance(d, dict) or 'data' not in d:
                self.win.after(0, self._show_error, '响应异常')
                return
            audio = base64.b64decode(d['data'])
            ts = time.strftime('%Y%m%d_%H%M%S')
            fname = f'语音_{mode}_{ts}.wav'
            fpath = OUT_DIR / fname
            fpath.write_bytes(audio)
            self.win.after(0, self._show_success, fname, len(audio))
        except Exception as e:
            self.win.after(0, self._show_error, str(e))

    def _show_success(self, fname, size):
        self.btn.config(state=tk.NORMAL, text='生成语音')
        self.status.config(text=f'已保存: {fname} ({size//1024}KB)', foreground='green')
        messagebox.showinfo('完成', f'语音已保存到桌面 MiMo语音 文件夹')

    def _show_error(self, msg):
        self.btn.config(state=tk.NORMAL, text='生成语音')
        self.status.config(text='失败', foreground='red')
        messagebox.showerror('错误', msg)

    def run(self):
        self.win.mainloop()

if __name__ == '__main__':
    TTSApp().run()
