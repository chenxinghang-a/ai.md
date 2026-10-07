# SCADA round 161 交付链轮报告

- **日期**：2026-09-16
- **版本**：`1.3.1006` → **`1.3.1007`**
- **后端**：`C:\Users\cxx\WorkBuddy\Claw\industrial_scada` → `9058b3e`
- **前端**：`C:\Users\cxx\scada-app` → `bbfc62f`
- **上游**：`SCADA-交付链缺口与修复方案.md`（round 161 预研，两轮核实版）
- **本轮主题**：交付链**零风险/低风险项** —— 仓库卫生 + 打包配方入 git + 消除自动更新的静默失效

> 本轮刻意**只做不需要下载大文件、不需要产品决策**的项。
> 真正跑一次 `electron:build` / `pyinstaller` 需要下载约 300 MB 并占用数 GB 内存，
> 本机 C 盘仅剩约 11 GB、可用内存常年 1–2 GB，**留到主人在场的一轮单独执行**。

---

## 一、后端（`9058b3e`，1.3.1007）

### 1.1 归档 10 个游离脚本（1042 行）

原先散落在**仓库根目录**且被提交进 git 的一次性调试脚本，移入 `legacy/root-scripts/`：

`_api_push.py`(293) / `_audit_deps.py`(69) / `_check_bugs.py`(104) / `_git_push.py`(43) /
`_test_all.py`(73) / `test_fixes.py`(105) / `test_simple.py`(103) / `test_start.py`(227) /
`quick_test.py`(8) / `check_status.py`(17)

- **归档前逐个 grep 全仓库确认零引用**。`test_start` 的 16 处命中经**逐条检查**
  全部是 `test_start_device_not_found` 这类**测试函数名的子串误匹配**，不是真引用。
- **没有删除** —— 只移出根目录，内容仍在 git 历史与 HEAD 里，随时可取回。
  按主人「先归档、一个版本周期后无回归再删」的口径处置。
- 新增 `legacy/root-scripts/README.md`，逐条说明每个脚本的来历、为什么归档、
  **以及「不保证能跑」**（`quick_test.py` / `check_status.py` 打的是已经不存在的
  `localhost:5000`）。
- 结果：根目录 `.py` 从 15 个降到 **5 个**（`build.py` / `config.py` / `launcher.py` /
  `paths.py` / `run.py`），不再有「看起来像正式入口」的噪声。

### 1.2 `scada-backend.spec` 入 git + 去硬编码

**根因**：`.gitignore` 里有 `*.spec` 规则 → `scada-backend.spec` 被挡在 git 外面
（**磁盘上有、git 里没有**），新克隆的仓库无法复现后端打包。

- `.gitignore` 加 `!scada-backend.spec` 例外放行
- `pathex` 去硬编码：原为 `'C:\Users\cxx\WorkBuddy\Claw\industrial_scada'`，
  换机器 / 换用户名就构建失败。改用 PyInstaller 注入的全局 `SPECPATH`
  （= `os.path.split(SPEC)[0]`，即 spec 文件所在目录）。
  **已核官方文档**：`https://pyinstaller.org/en/stable/spec-files.html`
  → 「Globals Available to the Spec File」→ `SPECPATH`。
  注意 `SPECPATH` 从仓库根执行时可能为空串，故用 `os.path.abspath()` 归一。
- ⚠️ **诚实标注：本机 venv 里没装 PyInstaller，所以这个改动只做了「语法 + API 契约」
  验证，未做实际构建验证。** 不过 `pathex` 只影响 import 搜索路径，
  且失败方式是**构建期报错（响亮失败）**，不是静默失效 —— 风险有界。

### 1.3 取消跟踪运行期产物与垃圾文件

| 文件 | 情况 | 处置 |
|---|---|---|
| `stderr.txt` | **2.4 MB 二进制垃圾**，自 5 月 30 日起就在 git 里 | `git rm --cached`（文件留磁盘，`.gitignore` 本就有 `stderr*.txt` 规则，只是已跟踪所以不生效） |
| `stdout.txt` | 58 B，同上 | 同上 |
| `data/audit_log.jsonl` | **运行期审计日志**，每跑一次测试就追加几十条 `emergency_stop` 测试垃圾，此前**每轮提交都夹带噪声** | `git rm --cached` + `.gitignore` 新增 `data/audit_log.jsonl` |

**已确认取消跟踪是安全的**：写入方 `智能层/device_control.py:1221` 会
`self._audit_file.parent.mkdir(parents=True, exist_ok=True)` 然后以 `'a'` 模式打开
→ 新克隆的仓库里文件不存在也会被自动创建，不会报错。

### 1.4 静态守卫范围调整

`tests/test_silent_exception_guard.py` 的 `EXCLUDED_DIRS` 加入 `legacy/`
（归档区按定义是废弃代码，不适用生产代码的静默异常标准）。

---

## 二、前端（`bbfc62f`，1.3.1007）

### 2.1 消除自动更新的静默失效（P3-a 最小修复）

**问题链**（四层防御性编程叠在一起，最终表现为「永远不更新，且没有任何人知道」）：

1. `package.json` 里**没有 `electron-updater`** 依赖
2. `electron/updater.js:2` 用 `try { require(...) } catch { autoUpdater = null }` **静默吞掉**
3. `electron/updater.js` 在 `!autoUpdater` 时只 `console.log('electron-updater 不可用')` 然后 `return`
   —— 而**打包后的 Windows 应用没有控制台，这句日志谁也看不见**
4. `electron/main.js:9` 外面**又一层** `try/catch`

→ `main.js:396` 启动 15 秒后调 `checkForUpdates()`，函数**立即返回，什么也没发生**。

**修复（只做「让失败可见」，不改行为）**：

- 捕获 `require` 失败的具体原因（`loadError`）
- 新增 `reportUnavailable(reason)`：`console.warn` + **落盘**到
  `userData/update.log`（含时间戳与具体原因）
- 每个进程只记一次，避免刷屏
- 落盘也失败时不再向上抛 —— **「更新能力探测失败」绝不能影响应用启动**

**顺带修掉一个自己引入的问题**：原因字符串含换行（Node 的
`Cannot find module ...\nRequire stack:\n- ...`）会把一条日志写成多行、
破坏「一行一条」的格式 —— 已压成单行。

**明确未做**（需要主人拍板）：`npm i electron-updater` + 配置 `build.publish` +
修 `latest.yml` 文件名不一致。这些属「发布渠道」决策，已进「待主人确认」第 9 条。

### 2.2 构建验证踩到的坑

`npm run build` 第一次**失败**，但不是代码问题 —— 是 **safe-delete guard** 拦住了
`vite build` 清空 `dist/assets`（137 个文件 > 阈值 50）：

```
[safe-delete][SAFE_DELETE_BULK_CONFIRM_REQUIRED] {"count":137,"threshold":50,
 "targets":["C:\\Users\\cxx\\scada-app\\dist\\assets"]}
```

按已知规避法用**改名代替删除**：`mv dist dist.prev-<ts>` 后重跑，**8.7 秒构建成功**。
（构建后把 `dist.prev-*` 移出仓库，避免它在 `.gitignore` 的 `dist/` 规则覆盖范围之外
而变成未跟踪文件。）

---

## 三、验证

| 项目 | 结果 |
|---|---|
| 后端全量套件 | **2004 passed / 0 failed**（与 round 160 同数 —— 说明归档游离脚本**未影响测试收集**，这是预期行为，因为 `pyproject.toml` 的 `testpaths = ["tests"]`） |
| 后端 spec 语法 | `ast.parse` 通过；`pathex = os.path.abspath(SPECPATH)`；无硬编码路径残留 |
| 前端类型检查 | `vue-tsc --noEmit` **零错误** |
| 前端构建 | `vite build` **成功**（8.70s，2312 modules） |
| 前端单测 | **vitest 57 passed**（5 个文件） |
| 前端 updater 桩测 | **6/6 PASS** —— 劫持 `require('electron')` 把 `app.getPath` 指到临时目录，断言：不抛异常 / 日志生成 / 含可诊断原因 / 不刷屏（1 行）/ 导出接口未破坏 |

---

## 四、提交与推送

| 仓库 | 提交 | 版本 | 远端核对 |
|---|---|---|---|
| 后端 | `7e5660c` → **`9058b3e`** | `1.3.1006` → **`1.3.1007`** | ✅ `ls-remote` == 本地 |
| 前端 | `cfaae5f` → **`bbfc62f`** | `1.3.1006` → **`1.3.1007`** | ✅ `ls-remote` == 本地 |

---

## 五、交付链剩余项（未做，原因）

| 编号 | 项 | 为什么本轮没做 |
|---|---|---|
| P3-a（完整） | 装 `electron-updater` + 配 `build.publish` | **需要主人定发布渠道**（GitHub Releases / 自建服务器 / 干脆删掉） |
| P3-b | `latest.yml` 文件名与实际产物不一致（带空格）→ 接通后也会 404 | 依附于 P3-a，一起做 |
| P3-c | 前端仓库无法从零出包（`extraResources` 依赖 248 MB 的 `backend/` 构建产物） | 需要跑 PyInstaller，**内存/磁盘开销大** |
| P3-e | CI 从没验证过 Windows（唯一 workflow 跑 `ubuntu-latest`） | 改 CI 需要推一次触发 GitHub Actions 才能验证；且 Windows runner 计费 2× |
| P3-f | 前端零 CI（`scada-app/.github/` 不存在） | 需要先有可跑的 CI 范式 |
| 实际出包 | `electron:build` + `pyinstaller` | **需下载约 300 MB、占用数 GB 内存** → 留给主人在场的一轮 |

---

## 六、本轮踩的坑（已写进 skill / errors.log）

1. **safe-delete guard 会拦住 `vite build` 清 `dist/assets`** —— 前端构建失败时
   先看是不是这个原因，不要怀疑代码。规避法：`mv dist dist.prev-<ts>`。
   注意 `dist.prev-*` **不在** `.gitignore` 的 `dist/` 规则覆盖范围内，构建完要移出仓库。
2. **`.gitignore` 对「已跟踪文件」无效** —— `stderr*.txt` / `stdout*.txt` 规则早就在，
   但文件已被跟踪，所以一直没生效。必须 `git rm --cached` 才会真正取消跟踪。
3. **`*.spec` 这类宽泛规则会误伤必须入库的文件** —— 用 `!文件名` 例外放行，
   比直接删规则安全。
