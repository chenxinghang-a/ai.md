# YouTube 双语字幕 · 本地 AI 翻译系统（已部署）

> 目标：YouTube 双语字幕，本地 LLM 翻译，**精准 + 不卡 + 白嫖 + 隐私零泄漏**。
> 适用环境：Windows 11 + NVIDIA RTX 5060 Laptop 8GB 显存。

---

## ✅ 当前部署状态（2026-08-16 修正）

> **✅ 可用方案（需本地 CORS 桥，端口 11437）**：浏览器扩展**不能直接直连 11434**，必须过本地 CORS 桥 `127.0.0.1:11437`。
> 原因：沉浸式翻译的 OpenAI 客户端会带自定义头（authorization / openai-beta / x-stainless-* 等）并以凭据模式请求，触发浏览器 CORS 预检(OPTIONS)；
> Ollama 即便设了 `OLLAMA_ORIGINS=*`，其预检响应 `Access-Control-Allow-Headers` 也不是 `*`，预检不过 → 浏览器拦掉请求 → 扩展报「网络连接失败」。
> 极简 CORS 桥（`D:\AI\ollama-cors-bridge.py`，回 `Allow-Headers: *` 并反射 Origin）放行即可。**api_key 必填但不校验**（填 `ollama` 即可）。
> 之前搭的 `127.0.0.1:11436` 代理已停用；现在的 `11437` 桥是**真实所需**，不是多余。日常用桌面「唤醒翻译.bat」一键拉起。

| 项目 | 状态 | 位置 |
|---|---|---|
| Ollama 程序二进制 | ✅ 已装（C 盘） | `C:\Users\cxx\AppData\Local\Programs\Ollama\ollama.exe` |
| Ollama 完整 portable 版 | ✅ 已装（含 llama-server + CUDA） | `D:\AI\Ollama\ollama.exe` |
| 模型 `qwen2.5:3b`（**主用·3B·q5量化·无思考·不漏句**） | ✅ 已封装并验证（2.4GB，30句长段0漏句，3.4s/段） | `D:\AI\models\` |
| 模型 `qwen2.5:1.5b`（**轻量备用·最快·无思考**） | ✅ 已拉取并验证（986MB，0.5s/句） | `D:\AI\models\` |
| 模型 `translategemma:4b`（翻译专精备用） | ✅ 已拉取并验证（3.3GB，1.4s/句） | `D:\AI\models\` |
| Ollama 服务 | ✅ 运行中 `http://localhost:11434` | OpenAI 兼容端点（`/v1`） |
| **CORS 桥** `ollama-cors-bridge.py` | ✅ 监听 `127.0.0.1:11437`（回宽松 CORS，转发 11434） | `D:\AI\ollama-cors-bridge.py` |
| **唤醒启动器**（手动·不开机自启） | ✅ 双击起 Ollama(若没跑)+重启桥+开 YouTube | `D:\AI\wake-translate.bat` / 桌面 `唤醒翻译.bat` |
| CORS 放行 | ⚠️ `OLLAMA_ORIGINS=*` 已设，但**扩展仍直连不过**→必须走 11437 桥 | 见「CORS 桥」行 |
| Ollama 开机自启 | ⚠️ 已配（HKCU Run + 启动文件夹），开机即起 Ollama；**桥不自动起**，需手动唤醒 | — |
| 手写 Edge 扩展（备用） | ⚠️ 已降级为备用 | `D:\AI\yt-bilingual-ext\` |
| 手写油猴脚本（备用） | ⚠️ 已降级为备用 | `yt-bilingual-subtitle.user.js` |

> **服务端已全就绪**：Ollama 跨域已开、OpenAI 兼容端点已验证可直连翻译。你只需装一个插件 + 填 3 个字段，详见「使用」。

---

## 📁 目录结构（文件分清楚）

```
C:\Users\cxx\AppData\Local\Programs\Ollama\   ← Ollama 程序（C 盘，系统注册）
D:\AI\
├── ollama-cors-bridge.py  ← 本地 CORS 桥（11437→11434，放行扩展 CORS 预检）
├── wake-translate.bat      ← 唤醒启动器（起 Ollama+桥+开 YouTube，不自动开机）
├── Ollama\          ← 完整 portable 版（ollama.exe + lib/llama-server.exe + CUDA 库）
├── models\          ← 所有 LLM 模型（OLLAMA_MODELS 环境变量指向这里）
├── logs\            ← 服务日志 / 拉取日志 / 代理日志
├── scripts\         ← 管理脚本：
│   ├── start-ollama.ps1         一键起服务（幂等）
│   ├── register-autostart.ps1   注册任务计划（需管理员，已改用注册表方案）
│   └── socks5-to-http-proxy.py  SOCKS5→HTTP 代理（仅拉模型时用）
└── yt-bilingual-ext\ ← Edge 扩展（免 Tampermonkey 一键装）：
    ├── manifest.json            MV3 清单
    ├── background.js            后台 worker：跨域翻译（Ollama/百度/谷歌）
    ├── content.js               字幕渲染 + SPA 导航 + 设置面板
    ├── page-inject.js           页面注入：读 player 字幕轨道
    └── launch-youtube.bat       一键启动器
```

---

## 🚀 使用（日常）—— 推荐：现成插件接本地 qwen3

> 手写扩展/脚本已降级备用。翻译请用成熟插件，稳定省心。

### 推荐方案：装一个插件，填 3 个字段（服务端已就绪）
任选其一（都支持自定义 OpenAI 兼容端点 / 本地 Ollama）：
- **沉浸式翻译 Immersive Translate**（功能最全：网页+字幕+输入框；自带 YouTube 双语字幕）
- **YouTube 字幕翻译**（Chrome 商店，最轻量：原生读 YouTube 字幕 + 双语叠加 + 缓存）
- **yt-subtitle-translator**（GitHub，自定义端点原生支持 Ollama，带 API 测试按钮）

**通用配置（填进插件的「自定义 OpenAI / 自定义端点」）——先用桌面「唤醒翻译.bat」把桥拉起来**：
```
API 地址 : http://127.0.0.1:11437/v1/chat/completions
模型名   : qwen2.5:3b            （3B·q5量化·无思考·不漏句；或 qwen2.5:1.5b 更轻、translategemma:4b 翻译更专精）
API Key  : ollama                （Ollama 的 OpenAI 端点必填但**不校验**，填任意值均可）
目标语言 : 简体中文
System Prompt（若可填）: 你是专业英译中翻译。只输出中文译文，不解释，不输出思考过程。
```
> ⚠️ **必须填 11437（CORS 桥），不要直接填 11434**：沉浸式翻译的 OpenAI 客户端会带自定义头（authorization / openai-beta / x-stainless-* 等），触发浏览器 CORS 预检；Ollama 即便设了 `OLLAMA_ORIGINS=*`，预检响应 `Access-Control-Allow-Headers` 也不是 `*`，预检不过→浏览器拦请求→扩展报「网络连接失败」。本地 CORS 桥（`D:\AI\ollama-cors-bridge.py`，端口 11437，回 `Allow-Headers: *` 并反射 Origin）正是为解决这个而存在。若系统代理（如 V2RayN）把 localhost 也拐走，在代理设置里把 `127.0.0.1;localhost` 加入「绕过代理」例外。

- **沉浸式翻译**：设置 → 翻译服务 → 选 **OpenAI** → 自定义模型填 `qwen2.5:3b`、自定义 URL 填上面地址、Key 填 `ollama` → 点「测试服务」应返回成功 → 基本服务选它 → 打开 YouTube 视频开「自动双语字幕」。
- 装好后打开有字幕的英文视频，自动出双语字幕。本地 RTX 5060 跑，热身後 **~0.5–1.4 秒/句**，**零额度、零云端延迟**（重看靠插件缓存）。

### 备用方案：手写扩展 / 油猴脚本（仅当插件不满足时）
- **Edge 扩展**：双击 `D:\AI\yt-bilingual-ext\launch-youtube.bat`（需该启动器开的 Edge 实例才加载）。
- **油猴脚本**：装 Tampermonkey → 粘贴 `yt-bilingual-subtitle.user.js`。
- 这两者默认仍走本地，但稳定性不如现成插件，已不再主推。

---

## 🔧 换模型 / 拉新模型

服务本身不需要联网。只有**新拉模型**时才需要代理（走 ollama.com registry）：

```powershell
# 1) 先起本地代理（把你的 SOCKS5 梯子转成 HTTP，Ollama 只吃 HTTP 代理）
python D:\AI\scripts\socks5-to-http-proxy.py

# 2) 设代理环境变量后拉模型（默认 SOCKS5 在 127.0.0.1:10808，可按需改脚本）
$env:HTTPS_PROXY='http://127.0.0.1:18080'; $env:HTTP_PROXY='http://127.0.0.1:18080'
& 'D:\AI\Ollama\ollama.exe' pull qwen3:4b        # 备选对比
& 'D:\AI\Ollama\ollama.exe' pull translategemma:12b  # 极致质量(8.1GB, 显存边缘)
```

油猴里换模型：YouTube 页面 → Tampermonkey 图标 → `🎯 设置 Chat 引擎模型` 改成目标名（如 `qwen3:4b`）。以 `translategemma` 开头的模型会自动用 Google 官方翻译 prompt。

---

## 🧠 引擎降级链

```
tlang (YouTube 内置翻译)    ← 命中则零延迟零额度（但多数视频无中文翻译）
    ↓ 失败
本地 LLM (qwen3:4b)        ← 主路径，已默认，精准且快
    ↓ 服务没起 / 失败
DeepSeek 云端               ← 备用，要 key
    ↓ 没配
百度翻译 (AppID+Key)        ← 国内直连
    ↓ 没配
谷歌翻译免费接口            ← 兜底，批量
```

---

## 📊 性能（RTX 5060 Laptop + TranslateGemma 4B）

| 指标 | 实测/预估 |
|---|---|
| 首次翻译 200 条字幕 | 30–60 秒（GPU 加速） |
| 缓存命中（重看） | **0 秒、0 请求** |
| 显存占用 | 3.3GB / 8GB（剩 4.7GB） |
| 翻译质量 | COMET22 80.1（接近商业翻译，超通用 gemma4b 的 77.2） |

---

## 🐛 调试

F12 控制台过滤 `YT双语`：
```
[YT双语] 引擎链 tlang → chat → baidu → gt
[YT双语] [Chat:translategemma:4b] 0/230
...
[YT双语] Chat 完成 230 条
```
本地服务没起时：`[YT双语] 引擎 chat 失败: network error → 切下一个`（自动降级）。

---

## 备选模型对比

| 模型 | 大小 | 说明 | 推荐度 |
|---|---|---|---|
| **qwen2.5:1.5b** | 986MB | **轻量备用**：无思考、热身後 0.5s/句、最快最轻（漏句风险高，已降级） | ⭐⭐⭐ 轻量备用 |
| translategemma:4b | 3.3GB | 翻译专用、质量高，热身後 1.4s/句（首字 18.9s 是冷启动加载，非常态） | ⭐⭐⭐⭐ 纯翻译备用 |
| qwen3:4b | 2.5GB | ⚠️ 有 thinking 特性，翻译会疯狂思考→首字极慢+可能污染，**不推荐** | ⭐ 不推荐 |
| translategemma:12b | 8.1GB | 极致翻译质量（显存边缘） | ⭐⭐⭐ 极致 |

> 注：Qwen2.5 官方**没有 2B** 档（尺寸为 0.5/1.5/3/7/14/32/72B），主人说的"2b"对应最小的 **qwen2.5:1.5b**。
| qwen2.5:7b | 4.7GB | 翻译更稳（无 thinking 特性），如需更准可拉 | ⭐⭐⭐⭐ 备选 |
| qwen2.5:3b | 1.9GB | 最轻 | ⭐⭐⭐ 最轻 |
| **qwen2.5:3b** | 2.4GB | **当前主用**：q5 量化封装（非官方 Q4）、无思考、不漏句（num_predict 放开到 1024）、实测 30 句长段完整、质量明显好于 1.5b | ⭐⭐⭐⭐⭐ 主用 |
