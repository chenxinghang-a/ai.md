# 启动项审查报告（2026-08-19）

机器：cxx 的 Win11（七彩虹 P15，RTX5060）。采集范围：HKCU/HKLM Run、启动文件夹、计划任务、第三方自启服务。

> 评级说明：**可关**=基本无副作用，放心禁；**看情况**=取决于你是否用得到；**保留**=系统/安全/常用，别动。

---

## 一、HKCU Run（当前用户登录启动，最影响开机速度和托盘整洁）

| 项 | 来源 | 建议 | 说明 |
|---|---|---|---|
| Thunder | 迅雷 | **可关** | `-silent` 自启，不用迅雷时纯占内存 |
| IDMan | Internet Download Manager | **可关** | `/onboot`，IDM 按需启动即可 |
| EpicGamesLauncher | Epic 游戏启动器 | **可关** | `-silent` 自启，用时再开 |
| BaiduYunDetect | 百度网盘 | **可关** | 后台探测服务，不用百度网盘就禁 |
| electron.app.学习通 | 学习通(cxstudy) | **可关** | 上课才用，无需开机自启 |
| Marvis | 腾讯 Marvis | **可关** | 腾讯 AI 应用，非必需 |
| MicrosoftEdgeAutoLaunch_xxx | Edge 后台预载 | **可关** | `--no-startup-window`，Edge 常驻后台，可禁 |
| OllamaServe | 自写脚本 | 看情况 | 你 AI 工作要常驻 Ollama 就留（见下方重复说明） |
| OneDrive | 微软 | 看情况 | 用 OneDrive 同步就留 |
| Steam | Steam | 看情况 | 游戏党通常留 |
| WallpaperEngine | 壁纸引擎 | 看情况 | 吃显存/内存，不要壁纸就关 |
| LGHUB | 罗技 | 保留 | 鼠标键盘驱动托盘 |
| GameViewer | 网易UU远程 | 保留 | 刚帮你设的自启 |

## 二、HKLM Run（所有用户，需管理员权限改）

| 项 | 来源 | 建议 | 说明 |
|---|---|---|---|
| Autodesk Access | Autodesk Access 应用UI | **可关** | 更新/商城启动器，AutoCAD 用不到它 |
| Autodesk Access Service | Autodesk 更新服务 | **可关** | 自动更新器，非必需 |
| SecurityHealth | Windows 安全中心 | 保留 | 托盘图标 |
| RtkAudUService | Realtek 音频 | 保留 | 声卡服务 |

## 三、启动文件夹（Startup）

| 项 | 指向 | 建议 | 说明 |
|---|---|---|---|
| Ollama.lnk | ollama app.exe (GUI) | **可关** | 与 Run 里的 OllamaServe **重复**，留 Run 那个后台服务版即可 |
| 发送至 OneNote.lnk | ONENOTEM.EXE | 看情况 | OneNote 发送到，不用就删 |

## 四、第三方自启服务（AUTO_START，影响后台资源）

| 服务 | 来源 | 建议 | 说明 |
|---|---|---|---|
| AiXiaobaoSvr / AndrowsSvr | 腾讯 Androws（安卓模拟器） | **可关** | 不玩手游模拟器就禁 |
| MarvisSvr | 腾讯 Marvis | **可关** | 同上 |
| Autodesk Access Service Host | Autodesk | **可关** | 更新宿主 |
| Autodesk CER Service | Autodesk | **可关** | 错误上报，纯垃圾 |
| OfficePLUS Service | Office 插件 | **可关** | 模板插件，不用就禁 |
| NetMsmqActivator / NetPipeActivator / NetTcpActivator | .NET WCF | **可关** | 基本用不到，除非你 Host WCF 服务 |
| Creative.VADMonitorService / CTAudSvcService | Creative 声卡 | 看情况 | 没装 Creative 声卡就关 |
| Everything | Everything 搜索 | 看情况 | 你用 Everything 搜文件就留（很轻量） |
| vivoesService / vivoSyncService | vivo 手机套件 | 看情况 | 你有用 vivo Pad，可能要同步；不用就关 |
| SangforPWEx / SangforSP | 深信服 SSL VPN | 看情况 | 学校/公司 VPN，要连就留 |
| HKClipSvc | 控制中心热键 | 看情况 | 笔记本快捷键驱动，留着稳妥 |
| PCManager Service | 微软电脑管家 | 看情况 | 用就留 |

**务必保留（安全/驱动/常用，别动）：**
- WinDefend / MDCoreSvc（Defender 杀毒）
- NvContainerLocalSystem（NVIDIA 设置）
- ClickToRunSvc（Office）
- AdskLicensingService（AutoCAD 授权，装机必留）
- GameViewerService（UU远控）
- IntelGraphicsSoftwareService、edgeupdate、GoogleUpdater、LGHUBUpdaterService

---

## 重复项提醒
Ollama 在**两处**都设了自启：Run 的 `OllamaServe`（跑 `D:\AI\scripts\start-ollama.ps1` 后台服务）+ 启动文件夹的 `Ollama.lnk`（GUI）。二选一即可，建议留 Run 的后台服务版、删启动文件夹的 .lnk。

## 下一步
要我帮你禁用哪些？可以指定上面的项，或说「关掉明确多余的」我一次性处理（只动「可关」那一档 + 重复 Ollama.lnk，不动服务和「看情况」项，避免误伤）。
