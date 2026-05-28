# MEMORY.md

## 🔥 执行铁律（5.7新增）
**能干的不用等指示，直接干，干完报结果。不要问"要继续吗"、"先干哪个"——有任务就执行，没任务才问。**

---

## ⚠️ 已知平台限制（5.7记录，用户已知）

### WorkBuddy ACP模式（5.7新增 - 大坑！）
- **症状**：ACP模式拦所有原生进程执行（git/python/cmd/Start-Process全部被拦）
- **只允许**：PowerShell内置cmdlet（`Invoke-RestMethod`/`Get-Content`等）、文件读写工具
- **git push绕过**：主人手动跑git命令，先设代理 `git config http.proxy [PROXY_REDACTED]`
- **git路径**：`[USER_HOME]\WorkBuddy\Claw\tools\mingit\cmd\git.exe`，不在PATH里
- **教训**：ACP模式下不要反复试原生进程，直接让主人在终端跑

### WorkBuddy content_policy问题
- **症状**：上下文压缩后，AI变"新人"，之前的任务意图全丢，导致安全策略误判
- **根因**：content_policy是平台级硬注入，无用户可配置开关（查过文档+config全确认）
- **影响**：测试下载器/搜索等基础操作被当成"下载盗版内容"拒绝
- **主人态度**：极度不满，认为基础能力不该被限制，要求只保留"不危害人类"底线
- **待办**：反馈WorkBuddy团队，要求增加safetyLevel配置或workspace级覆盖

### 上下文压缩恢复铁律
- 压缩后如果用户说"继续"或"测试X"，先查MEMORY恢复任务意图
- 不要假设当前请求是独立的，90%的情况是延续之前的任务

---

## 🔥 操作铁律（5.6强制更新 - 犯过错的必须记住）

### 下载准则
1. **GitHub/外网资源** → 第一反应 `aria2c --all-proxy`，不试直连！
2. **所有Python代码** → 写 `.py` 文件执行，**绝对禁止inline `-c` 写复杂逻辑**（PowerShell会吃掉 `<>` `'` `"` 导致语法错误）
3. **web_fetch** 只有国内站能用，超过15秒无响应就放弃 → 切Python `requests.get(timeout=15)`
4. **代理SSL报错** → 试直连 / 试aria2c走代理 / 试 `verify=False`
5. **`_downloader.py`** 封装了 `download()` / `github_raw()`，自动代理+进度条+重试，优先用

### 搜索/爬取准则（核心能力！）
1. **多渠道并行**：别吊死一棵树。国内(百度/B站/知乎/CSDN) + 国外(YouTube/GitHub/Fandom) + 镜像站同时试
2. **来源优先级**：B站/国内CDN(直连) > YouTube/GitHub(代理) > Fandom/论坛(需Cookie)
3. **同一来源最多试3次** → 不通马上换，不等不拖
4. **有用skill先用**：`download-anything`里有现成的脚本和来源参考
5. **连续5次全部失败** → 告诉用户真实原因(具体哪个站什么错)，请求用户提供资源
6. **记录成功来源**：哪个站什么方法成功了，写到MEMORY"成功来源"区

### TTS准则（5.6新增）
1. voicedesign不能写IP角色名（"派蒙""孙悟空"）
2. 音频响应是dict，取 `data["data"]` 才是base64
3. 标准TTS文本支持标签 `(开心)` `[停顿]`，效果比voicedesign好
4. **voiceclone不能保存音色ID**，每次要传原文件，效果有限

### 音频处理准则（5.6新增）
1. **禁止加任何滤波/增益**（highpass/lowpass/volume），只做格式转换
2. **禁止乱猜时间戳裁剪** → 不确定就整段保留或问主人
3. 格式统一：`pcm_s16le` + `24000Hz` + `mono`

### 任务流（5.6新增）
1. 接到任务 → 先跑 `_preflight.py` 确认网络工具正常
2. 列来源优先级 → 一次不通秒换，不等不拖
3. 执行完 → 验证输出质量 → 清理中间文件
4. 搞不定的 → 直接告诉主人真实原因，不硬撑

### Python执行准则
1. 任何超过3行的Python代码 → 写 `.py` 文件再执行
2. 任何含正则 `re.findall(r"...")` 或有特殊字符的代码 → 必须写文件
3. 任何含 f-string 且内部有引号的代码 → 必须写文件
4. 测试脚本放工作区根目录，用完不删（可能复用）

### 文件清理准则
1. **`C:\workbuddy`** 是专用回收站/暂存目录，清理工作区文件移到这里，不要用系统回收站
2. 移动用 `Move-Item $_.FullName "C:\workbuddy\"`，不要 `Remove-Item`

### 文件编码准则
1. .bat脚本用ASCII字符，不要用 `╔═╗║╝` 等特殊框线（cmd/chcp兼容性问题）
2. 文件输出统一 `utf-8-sig`（Windows中文不乱码）

### 成功资源来源记录
| 资源类型 | 来源 | 方法 | 状态 |
|---------|------|------|------|
| GitHub raw代码 | github.com | aria2c + 代理 | ✅ |
| YouTube音频 | youtube.com | yt-dlp + 代理 | ✅ |
| 百度网页 | baidu.com | requests直连 | ✅ |
| B站API | bilibili.com | 需Cookie(反爬) | ❌ |
| Fandom | fandom.com | 403反爬 | ❌ |
| Ambr数据站 | ambr.top | DNS不通/代理SSL错 | ❌ |

---

## 环境
- 用户路径: `[USER_HOME]`
- Python: 系统3.12 (`[USER_HOME]\AppData\Local\Programs\Python\Python312\python.exe`) + managed 3.13.12 / 3.14.3
- Node.js: v24.14.1 (`C:\Program Files\nodejs\node.exe`)
- 工作区: `[USER_HOME]\WorkBuddy\Claw`
- 城市: [CITY]
- GPU: RTX 5060 Laptop, Driver 581.57, CUDA 13.0
- **当前代理**：HTTPS代理，100GB流量/30元，不限设备/使用时间
- **WorkBuddy**: v4.22.5（2026-05-07更新）

## 已安装工具
### Python包
| 包名 | 用途 | 安装日期 |
|------|------|----------|
| rapidocr-onnxruntime | **本地OCR引擎** | 4.10 |
| openai-whisper / faster-whisper | **语音转文字** | 4.09 |
| reportlab, python-pptx, python-docx | 文档生成 | 4.09 |
| pydub, imageio, imageio-ffmpeg | **音频处理** | 4.09 |
| pymodbus | Modbus通信 | 4.29 |
| pypsa | 电力系统潮流计算 | 4.29 |
| paho-mqtt | MQTT通信 | 4.29 |
| PyJWT, bcrypt | 用户认证 | 4.29 |

### 关键可执行文件
- `ffmpeg` — `[USER_HOME]\AppData\Local\Microsoft\WinGet\...\ffmpeg.exe`
- `aria2c` v1.37.0 — `tools\aria2c.exe`
- `git` 2.47.1 — `tools\mingit\cmd\git.exe`

## 已安装Skills（资源获取增强，5.7新增）
| Skill | 用途 | 来源 |
|-------|------|------|
| `download-anything` | **核心下载器**：yt-dlp(1800+站)/aria2/gallery-dl/spotdl/种子 | marketplace |
| `multi-search-engine` | 16引擎搜索（7国内+9国际），无需API key | marketplace |
| `web-scraper` | 5阶段网页抓取管道（HTTP→Playwright→清洗→元数据→LLM） | marketplace |
| `deep-research` | 结构化深度调研（大纲→并行搜索→报告） | marketplace |
| `stealth-browser` | 4层反检测浏览器（Cloudflare绕过+验证码+持久会话） | marketplace |
| `baidu-drive` | 百度网盘文件管理（上传/下载/转存/搜索） | marketplace |
| `web-access` | CDP直连Chrome（登录态+并行批量操作） | marketplace |
| `playwright-scraper-skill` | Playwright隐身抓取（反爬绕过+验证码处理） | marketplace |

## 自编工具脚本
- `_downloader.py` — 下载器(aria2c+代理+进度条+SSL处理)
- `_preflight.py` — 执行前检查清单
- `_audio_pipeline.py` — 音频格式转换
- `_tts_tool.py` — MiMo TTS桌面工具(v4)
- `auto_ops.py` — 屏幕自动化工具集(screenshot/ocr/find/click_text/tpl_match/status)
- `image_finder.py` (pyautogui skill) — OCR文字定位，用法：`text "文字"` 全屏搜索坐标

## 桌面自动化要点（合并自旧MEMORY）
- 学习通是桌面Electron应用，非浏览器
- **OCR定位文字坐标是最可靠的方法**
- **边栏 x=0~169（深色RGB 49,62,89），内容区 x≥170（白色背景）**
- **不要瞎猜坐标！不要编造界面文字！用OCR定位后再点击**
- 先截图→OCR找坐标→激活窗口→点击→截图验证

## AI通道
- **Gemini Key**: `[REDACTED]
- **DeepSeek**: `[REDACTED]`（直连无需代理，可用）
- **MiMo [REDACTED] `[REDACTED]
  - OpenAI端点: `https://api.xiaomimimo.com/v1` ✅（chat+tools）
  - Anthropic端点: `https://api.xiaomimimo.com/anthropic` ⚠️（chat only, no tool_use）
  - 鉴权: `Authorization: Bearer`(OpenAI) / `x-api-key`(Anthropic)
- **MiMo [REDACTED] `[REDACTED]
  - 端点: `https://token-plan-cn.xiaomimimo.com/v1`
  - 有Anthropic兼容端点 ✅
- **MiMo TTS**: `[REDACTED]`
- **MiMo Credits**: 7亿（2026-05-07充值）
- 代理: `[PROXY_REDACTED]`

## TTS关键信息
- 端点: `POST https://api.xiaomimimo.com/v1/chat/completions`，鉴头 `api-key`
- 中文音色: 冰糖/茉莉/苏打/白桦
- voicedesign: model=`mimo-v2.5-tts-voicedesign`, audio=`{"format":"wav"}`
- voiceclone: model=`mimo-v2.5-tts-voiceclone`, audio.voice=`data:audio/wav;base64,<b64>`
- 标准TTS文本支持标签：(开心)(俏皮)[停顿][小声][叹气](兴奋)(得意)
