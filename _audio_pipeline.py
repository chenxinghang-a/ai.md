# -*- coding: utf-8 -*-
"""
音频处理流水线：
1. 格式转换（M4A/MP3 → WAV/OGG/AAC/FLAC）
2. Whisper 语音转文字（提取歌词/语音内容）
"""
import os, json, time
import subprocess

def _fmt_time(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int((sec % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

SRC = r"C:\Users\cxx\Documents\xwechat_files\wxid_dn3b6rwdvyjd22_e1ed\msg\file\2026-03\平安其他教练学员_20240224153817.m4a..mp3"
OUT_DIR = r"c:\Users\cxx\WorkBuddy\Claw"
FFMPEG = r"C:\Users\cxx\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin\ffmpeg.exe"

base = os.path.splitext(os.path.basename(SRC))[0]
print(f"源文件: {os.path.basename(SRC)}")
print(f"大小: {os.path.getsize(SRC)/1024:.0f}KB")
print("-" * 40)

# ========== Step 1: 格式转换 ==========
print("\n[Step 1] 格式转换")

formats = {
    "wav": ["-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1"],
    "ogg": ["-c:a", "libvorbis", "-qscale:a", "5"],
    "aac": ["-c:a", "aac", "-b:a", "128k"],
    "flac": ["-c:a", "flac", "-compression_level", "5"],
}

converted = {}
for fmt, extra_args in formats.items():
    out_path = os.path.join(OUT_DIR, base + "." + fmt)
    cmd = [FFMPEG, "-y", "-i", SRC] + extra_args + [out_path]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True)
    elapsed = time.time() - t0
    if os.path.exists(out_path):
        sz = os.path.getsize(out_path) / 1024
        print(f"  OK {fmt.upper():4s} | {sz:7.0f}KB | {elapsed:.2f}s")
        converted[fmt] = out_path
    else:
        print(f"  FAIL {fmt.upper()}")

# ========== Step 2: Whisper 语音转文字 ==========
print("\n[Step 2] Whisper 语音转文字")
wav_path = converted.get("wav")

import whisper

model_name = "base"
print(f"  加载模型: whisper-{model_name}")
t_load = time.time()
model = whisper.load_model(model_name)
print(f"  模型加载: {time.time()-t_load:.1f}s")

print(f"  正在转录...")
t_transcribe = time.time()
result = model.transcribe(wav_path, language="zh", verbose=False)
elapsed_t = time.time() - t_transcribe

segments = result.get("segments", [])
text = result["text"].strip()

print(f"  转录完成! 耗时: {elapsed_t:.1f}s 文本: {len(text)}字 片段: {len(segments)}")

# ========== Step 3: 输出结果 ==========
print("\n[Step 3] 保存结果")

# 3a) 纯文本 TXT
txt_out = os.path.join(OUT_DIR, base + "_歌词.txt")
with open(txt_out, "w", encoding="utf-8") as f:
    f.write("=== 音频转录 ===\n")
    f.write(f"源文件: {os.path.basename(SRC)}\n")
    dur = result.get('duration', segments[-1]['end'] if segments else 0)
    f.write(f"时长: {dur:.1f}秒\n")
    f.write(f"模型: whisper-{model_name}\n\n")
    f.write("--- 完整文本 ---\n")
    f.write(text + "\n\n")
    f.write("--- 分段详情(带时间戳) ---\n")
    for seg in segments:
        start = seg['start']
        end = seg['end']
        txt = seg['text'].strip()
        f.write(f"[{start:.1f}s -> {end:.1f}s] {txt}\n")
print(f"  TXT: {txt_out}")

# 3b) JSON格式
json_out = os.path.join(OUT_DIR, base + "_歌词.json")
seg_list = []
for s in segments:
    d = {"start": s["start"], "end": s["end"], "text": s["text"].strip()}
    if "words" in s:
        d["words"] = [{"word": w["word"], "start": w["start"], "end": w["end"]} for w in s.get("words", [])]
    seg_list.append(d)

with open(json_out, "w", encoding="utf-8") as f:
    dur = result.get('duration', segments[-1]['end'] if segments else 0)
    json.dump({
        "source": os.path.basename(SRC),
        "duration": dur,
        "model": model_name,
        "full_text": text,
        "language": result['language'],
        "segments": seg_list
    }, f, ensure_ascii=False, indent=2)
print(f"  JSON: {json_out}")

# 3c) SRT字幕
srt_out = os.path.join(OUT_DIR, base + "_歌词.srt")
with open(srt_out, "w", encoding="utf-8") as f:
    for i, seg in enumerate(segments, 1):
        start = _fmt_time(seg['start'])
        end = _fmt_time(seg['end'])
        f.write(str(i) + "\n" + start + " --> " + end + "\n" + seg['text'].strip() + "\n\n")
print(f"  SRT: {srt_out}")

print("\n" + "=" * 40)
print("全部完成!")
print(f"\n转录预览:")
print(text[:400])
if len(text) > 400:
    print(f"...(共{len(text)}字)")
