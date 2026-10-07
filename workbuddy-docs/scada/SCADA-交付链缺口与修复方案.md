# SCADA 交付链缺口与修复方案（round 161 预研）

- **日期**：2026-09-16
- **调研范围**：后端 `C:\Users\cxx\WorkBuddy\Claw\industrial_scada` + 前端 `C:\Users\cxx\scada-app`
- **方法**：只读探查 + 实际执行 `npm run build`（未执行 `electron:build`，见 §4 说明）
- **性质**：P3 交付链预研，**为 round 161 提供可执行清单**

> ⚠️ **本文档经过两轮核实。** 第一轮由子 agent 产出，其中**多条结论与实测不符**（见 §5「被推翻的结论」）。本文档只保留**我本人复验过**的事实，每条都附证据。

---

## 一、结论摘要

| 待核问题 | 实测结论 |
|---|---|
| `electron:build` 从未成功 | ❌ **不成立** —— 2026-06-01 成功出过包，`release/` 里有 **146 MB 的 `SmartSCADA Setup 1.0.0.exe`** |
| `.spec` 不在 git | ✅ **成立** —— `scada-backend.spec`（1516 B）存在于磁盘，但 `git ls-files` 返回空 |
| 依赖被 gitignore 的 19 MB exe | ✅ **成立但说法不准** —— 前端 `extraResources` 依赖 `backend/` 目录，而该目录**整体 248 MB**，其中 `backend/_internal/` 与 `backend/*.exe` 被 gitignore |
| 自动更新是假的 | ✅ **成立，且是最严重的一条** —— 装了调用方、**没装 `electron-updater` 依赖**，`updater.js:2` 用 try/catch 把 require 失败吞掉 → 整个更新链是 **no-op** |
| CI 测试范围与本地不一致 | ✅ **成立**，但不是「3 个坏 YAML」 —— 后端只有 1 个 `ci.yml`，**YAML 语法正确**；真问题是**平台不一致**（CI 跑 ubuntu，产物是 Windows 桌面应用） |
| 后端根目录 10 个游离脚本 | ✅ **成立，1042 行，实测零引用**，删除风险为零 |

**最高优先级三件事**：
1. **自动更新是 no-op** —— 装出来的 exe 永远不更新，且**用户无任何提示**（静默失效，与本项目 round 159/160 修的是同一类病）。
2. **前端仓库无法从零出包** —— `extraResources` 指向的 `backend/` 是 248 MB 的 PyInstaller 产物，且其关键部分被 gitignore。新克隆的仓库**跑不出安装包**。
3. **CI 从没验证过 Windows** —— 这是个 Windows 桌面应用，CI 却在 ubuntu 上跑。

---

## 二、后端核实

### 2.1 CI（`.github/workflows/ci.yml`，唯一一个）

`yaml.safe_load()` **解析通过**。内容：

```yaml
jobs:
  test:   runs-on: ubuntu-latest, matrix python 3.12/3.13
          → pip install -r requirements.txt && pip install pytest pytest-cov
          → pytest tests/ -q --cov=. --cov-report=xml --cov-report=term-missing
  lint:   runs-on: ubuntu-latest → ruff check（continue-on-error，advisory）
```

**真实问题**（不是「坏 YAML」）：

| 问题 | 证据 |
|---|---|
| **平台不匹配** | CI 跑 `ubuntu-latest`；产品是 Windows Electron 应用。本机是 Win11 + Python 3.13.14，**CI 从未在 Windows 上跑过任何测试** |
| **CI 带 `--cov=.`，本地不带** | 本地命令 `pytest tests/ -q -p no:cacheprovider`（`pyproject.toml:46` `testpaths = ["tests"]`）。CI 的 `--cov=.` 覆盖整个仓库（含 `tools/`、`dist/`），**覆盖率口径完全不同** |
| **CI 没有 `-p no:cacheprovider`** | 本机因为 safe-delete guard 必须加这个参数，CI 不需要；但意味着**两条命令的收集行为不一致** |
| 未验证 | CI 是否真的跑起来过（需要看 GitHub Actions 记录，本地查不到） |

### 2.2 后端打包

- `scada-backend.spec`：**磁盘上有（1516 B，6 月 4 日），但未纳入 git** → 新克隆仓库无法复现打包
- `requirements.txt` 存在（827 B）
- `.gitignore` 排除整个 `dist/` → PyInstaller 产物不进 git（**合理**）

---

## 三、前端核实

### 3.1 `package.json` 实况

```json
"name": "smartscada",  "version": "1.3.1005",
"build": { "appId": "com.smartscada.app", "productName": "SmartSCADA",
           "directories": { "output": "release" },
           "files": ["dist/**/*", "electron/**/*", "resources/**/*"],
           "extraResources": [{ "from": "backend/", "to": "backend/", ... }],
           "win": { "target": ["nsis"], "signAndEditExecutable": false } }
```

**配置本身是完整的** —— `appId` 与 `name` 命名一致（`smartscada` / `com.smartscada.app`），`files` 白名单存在，`extraResources` 存在。

### 3.2 自动更新为什么是 no-op（**本轮最严重发现**）

证据链：

1. `package.json` 的 `dependencies` / `devDependencies` 里 **没有 `electron-updater`**（只有 `electron` / `electron-builder`）
2. `electron/updater.js:2`：
   ```js
   try { autoUpdater = require('electron-updater').autoUpdater } catch { autoUpdater = null }
   ```
   → 依赖缺失被 **try/catch 静默吞掉**
3. `electron/updater.js:15`：`if (!autoUpdater) { console.log('electron-updater 不可用'); return }`
   → 函数**直接 return，什么都不做**。而且只有 `console.log`，**用户界面完全无感知**
4. `electron/main.js:9`：`try { const u = require('./updater'); ... } catch {}`
   → 又一层 try/catch

**结果**：更新链路四层防御性编程叠在一起，最终表现为「**永远不更新，且没有任何人知道**」。这与 round 159/160 修的「静默假成功」是**同一种病**，只不过发生在 JS 侧。

### 3.3 出包产物与分发

- `release/` 里有 **2026-06-01 成功构建的完整产物**：
  - `SmartSCADA Setup 1.0.0.exe`（**146 MB**）
  - `smartscada-1.0.0-x64.nsis.7z`（139 MB）
  - `latest.yml`（electron-builder 生成的更新清单，指向 `SmartSCADA-Setup-1.0.0.exe`）
  - `win-unpacked/`
- `.gitignore` 排除了 `release/` → **产物不进 git**（这是对的），但**也没有任何其他分发渠道**（无 GitHub Releases 配置、无 `build.publish`）
- **注意**：`latest.yml` 里的文件名 `SmartSCADA-Setup-1.0.0.exe` 与实际文件名 `SmartSCADA Setup 1.0.0.exe`（**带空格**）**不一致** → 即使接通了 `electron-updater`，下载也会 404。这是个隐藏的第二层 bug。

### 3.4 前端没有 CI

`scada-app/.github/` **不存在** → 前端**零 CI**。

### 3.5 `backend/` 目录（`extraResources` 的来源）

- 体积 **248 MB**（`_internal/` + `data/` + `logs/` + `exports/` + `build_entry.py`）
- `.gitignore` 排除了 `backend/*.exe`、`backend/_internal/`、`backend/logs/`、`backend/data/`
- → **新克隆的 scada-app 仓库里 `backend/` 是空的**，`electron:build` 即使跑起来也会打出一个**没有后端的空壳安装包**

---

## 四、可执行修复清单（按投入产出比排序）

### P0-1 · 让自动更新要么真通、要么明确报错（**最高优先**）

- **问题**：四层 try/catch 让「更新不可用」变成无声的
- **最小改动（推荐先做这步）**：把 `updater.js:15` 的 `console.log` 改成**可见的降级提示**（主进程日志 + 首次启动时在 UI 上提示一次「当前版本不支持自动更新」），消除「静默失效」
- **完整修复**：`npm i electron-updater` + `package.json` 加 `build.publish` + 修 §3.3 的文件名不一致
- **风险**：完整修复会改变发布流程，需要发布渠道口径（GitHub Releases / 自建服务器）
- **验证**：装旧版 → 启动 → 看是否弹出更新提示
- **需主人拍板**：发布渠道走哪个

### P0-2 · 让前端仓库能从零出包

- **问题**：`extraResources` 依赖 248 MB 的构建产物，且关键部分被 gitignore
- **改什么**：在前端仓库加一个 `scripts/build-backend.mjs`，从**后端仓库**（或 git submodule）跑 PyInstaller 产出 `backend/`；并在 README 写清依赖顺序
- **风险**：低（新增脚本，不动现有链路）
- **验证**：在一个干净克隆里跑 `npm run electron:build` 能出包
- **注意**：需要下载 PyInstaller + 构建，**占用内存大**（见 §5）

### P1-1 · 把 `scada-backend.spec` 纳入 git

- **改什么**：`git add scada-backend.spec`（当前未跟踪）
- **风险**：零
- **验证**：`git ls-files scada-backend.spec` 有输出

### P1-2 · 修 CI 平台不匹配

- **改什么**：`.github/workflows/ci.yml` 的 `runs-on` 增加 `windows-latest` 维度，或改为 Windows 单平台（因为产品只出 Windows 包）
- **风险**：低；**验证**：推一次看 Actions 是否绿
- **注意**：Windows runner 消耗 GitHub Actions 额度更快（Windows 按 2× 计费）

### P2-1 · 删后端根目录 10 个游离脚本（1042 行）

- **已实测确认零引用**（逐个 grep，`test_start` 的 16 处命中经逐条检查**全是 `test_start_device_not_found` 这类测试函数名的子串误匹配**）
- **风险：零**；**验证**：删完跑全量套件仍 `2004 passed`
- **注意**：这些是**已跟踪文件**，删除要走 commit

### P2-2 · 统一 CI 与本地测试命令口径

- **改什么**：让 CI 与本地用同一条命令（去掉 `--cov=.` 或本地也加上），把 `testpaths` 作为唯一真源
- **风险**：零

### P3-1 · 根目录垃圾文件

- `stderr.txt`（**2.4 MB 已跟踪二进制**）+ `stdout.txt`（58 B），自 5 月 30 日起就在 git 里
- `data/audit_log.jsonl`（**运行期产物被跟踪**，每跑一次测试追加几十条测试垃圾）
- **风险**：零；**验证**：`git rm` 后仓库体积下降

---

## 五、被推翻的结论（子 agent 首轮报告的错误）

**记这一节是因为：本项目 round 159 已经踩过一次「审计报告是线索不是结论」的坑，这次又踩了一次。**

| 子 agent 的结论 | 实测 | 证据 |
|---|---|---|
| 「CI 有 3 个 workflow 全是坏 YAML，含一个生产部署 workflow」 | ❌ **完全错误**。后端只有 1 个 `ci.yml`，`yaml.safe_load()` **解析通过**；前端根本没有 `.github/` | `ls .github/workflows/` 只有 `ci.yml`；`yaml.safe_load` → OK |
| 「`.spec` 已提交进 git」（与原审计相反） | ❌ **错误**。`git ls-files scada-backend.spec` **返回空** | 原审计是对的 |
| 「`updater.cjs` 零引用，是死代码」 | ❌ **错误**。文件名是 `updater.js`，且 `main.js:9` **确实 require 了它** | `grep -rn updater electron/` |
| 「`appId` 与 `name` 不一致会导致数据目录不匹配」 | ❌ **错误**。`name=smartscada` / `appId=com.smartscada.app`，命名一致 | `package.json:2,43` |
| 「没有 `build.files` 白名单」 | ❌ **错误**。`files` 字段存在（`package.json:48`） | 同上 |

**保留的结论**（我复验后成立）：`electron-updater` 未安装 → 自动更新 no-op；`release/` 被 gitignore；`backend/` 是 248 MB 构建产物；10 个游离脚本零引用；`electron:build` 历史上成功过。

**教训**：子 agent 的报告必须**逐条回源码复核**才能采信。本轮我实际推翻了它 5 条结论中的 5 条（**全部关键结论都有错**）。

---

## 六、资源类操作（需主人拍板，不建议无人值守）

本机 **C 盘已用 90%（剩余约 11 GB）**，可用内存常年 1–2 GB。

| 操作 | 预估占用 | 说明 |
|---|---|---|
| `electron-builder --win`（若缓存已存在） | 复用 `%LOCALAPPDATA%\electron-builder\Cache`，但仍需数 GB 内存 | 6 月出包成功过，缓存可能还在 |
| `pyinstaller scada-backend.spec` | 产物 248 MB，构建峰值内存 1–2 GB | **不能与 pytest 同时跑** |
| 完整出包（前后端） | 磁盘 +3~4 GB | 建议**单独一轮、主人确认机器空闲时**执行 |

**建议**：先做 §4 里全部**零风险/低风险且不需要下载大文件**的项（P0-1 最小改动 / P1-1 / P1-2 / P2-1 / P2-2 / P3-1），把出包链路的配置性缺陷修完；**把真正跑一次完整出包单独留给主人在场的一轮**。

---

## 七、与队列「待主人确认」的对应

- **第 1 条**（「验证通过」是轻档还是重档）：重档含「出安装包」。本报告 §6 说明为何建议**分层执行** —— 配置修复可无人值守，实际出包需主人确认机器空闲。
- **第 7 条**（死代码处置口径）：§4 的 P2-1 / P3-1 属同一口径。其中 P2-1 那 10 个脚本经**逐条 grep 实测零引用**，删除风险为零。
- **新增待拍板**：自动更新的发布渠道（GitHub Releases / 自建服务器 / 干脆删掉 `updater.js`）。
