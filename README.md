# WorkBuddy 工作流 & AI 工具集

个人AI工作台配置、自编工具脚本和工作流记录。

## 工具脚本

| 脚本 | 用途 |
|------|------|
| `_downloader.py` | 下载器（aria2c+代理+进度条+SSL处理） |
| `_preflight.py` | 执行前环境检查 |
| `_audio_pipeline.py` | 音频格式转换（pydub） |
| `_tts_tool.py` | MiMo TTS 桌面工具 |
| `_backup_memory.py` | MEMORY脱敏备份脚本 |
| `auto_ops.py` | 屏幕自动化（screenshot/ocr/click） |
| `_gemini_arena.py` | Gemini多模型横评 |
| `_deep_research.py` | 深度调研工具 |
| `_local_agent.py` | 本地Agent实现 |

## 工作流铁律

详见 `MEMORY_backup.md`，包含：
- 下载/搜索/爬取准则（多渠道并行、代理优先）
- Python执行准则（写文件不写inline）
- 音频处理准则（不加滤波，只做格式转换）
- 桌面自动化要点（OCR定位>瞎猜坐标）

## Skills

已安装的WorkBuddy Skills：
- `download-anything` — yt-dlp/aria2/gallery-dl 多站下载
- `multi-search-engine` — 16引擎搜索
- `web-scraper` — 多策略网页抓取
- `deep-research` — 结构化深度调研
- `stealth-browser` — 反检测浏览器
- `baidu-drive` — 百度网盘管理
- `web-access` — CDP直连Chrome

## 环境

- Python 3.12/3.13/3.14
- Node.js 24.x
- GPU: RTX 5060 Laptop
- 工具: ffmpeg / aria2c / git (mingit)

## 备份说明

- `MEMORY_backup.md` — 脱敏版长期记忆，API key已移除
- `.workbuddy/memory/` — 日志记忆（gitignore，不上传）
