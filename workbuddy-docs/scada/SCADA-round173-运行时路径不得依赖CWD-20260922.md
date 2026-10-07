# SCADA round 173 — 运行时路径不得依赖 CWD（P2-5 配置层）

> 日期：2026-09-22
> 后端仓库：`C:\Users\cxx\WorkBuddy\Claw\industrial_scada`（GitHub `chenxinghang-a/scada`）
> 前端仓库：`C:\Users\cxx\scada-app`（GitHub `chenxinghang-a/scada-app`）
> 版本：1.3.1037 → **1.3.1038**（前后端 lockstep）

---

## 0 摘要

队列里 P2-5 记的是「40 处硬编码相对路径」，但**没给口径**。本轮把它按可复现的口径
实测钉死，结论是：**修 12 处 / 6 个文件**，且**全在生产路径上**——不是死代码。

三条核心结论：

1. **打包后配置校验永远失败**（产品缺陷）。启动日志里那三行
   「配置验证失败 [devices/alarms/system]: 配置文件不存在」不是配置坏了，
   是 `Path('配置')` 相对 CWD 解析不到 `_internal/配置/`。
   于是「配置真的坏了」和「路径不对」被压成同一个信号，校验形同虚设。
2. **诊断包三段恒为空**（产品缺陷）。`DiagnosticExporter` 的配置 / 库统计 /
   日志三个收集器都走相对路径。诊断包是排障时唯一能带走的证据，
   结果最需要的三段全是空的。
3. **「清理成功但一个都没删」**（产品缺陷）。`DataCleaner.clean_old_backups` /
   `clean_log_files` 的 glob 打错目录 → 匹配 0 个 → 返回 `status: 'success'`。
   这是最坏的失败形态：调用方看到 success 就不会再查。

**同时发现并修掉两个附带缺陷**（都是本轮实证暴露出来的）：

- 两条静态守卫被**构建产物**假红（`dist-scada-1.3.1037/` 里的源码副本被当违规报出）。
  假红比漏报更危险——它会训练人「看到守卫红了就忽略」。
- `配置/system.yaml` 的污染源找到并堵住了：`test_toggle_simulation_mode`
  的 patch 打在失效符号上，测试真的在重写受版本控制的仓库配置。

---

## 1 问题实证：P2-5 的真实范围

### 1.1 队列记录 vs 实测

**先定义口径**（不定义口径的「N 处」没法核对）：

| 口径 | 含义 | 可复现命令 |
|---|---|---|
| **R1** | `Path(<裸相对目录字面量>)` —— 直接形态 | 见下方命令 |
| **R2** | `Path(<变量>)`，而该变量的**默认值**是裸相对路径 | grep 抓不到，需人读代码 |

```bash
grep -rn -E "Path\(\s*['\"](配置|data|logs|exports|模板|静态资源)['\"]\s*\)" \
  --include=*.py . | grep -v -e "\.pytest_tmp" -e "dist-" -e "\.venv"
```

实测结果：

| 项 | 队列记录 | 实测 |
|---|---|---|
| 处数 | 40（**无口径**，无法核对） | 本轮**修 12 处 / 6 个文件**（R1 + R2 合计） |
| R1 全库原始命中 | — | **34**，但其中大部分不是生产代码（见下） |
| 是否区分死代码 | 未区分 | **已区分**：`core/` 下约 **52** 个模块带 `WIRED = False`（生产零引用） |
| 是否在生产路径 | 未说明 | **是**，见 1.2 |

**R1 的 34 处原始命中拆开看**（这是「队列记 40 处」这个数字不可用的原因）：

| 来源 | 处数 | 是否要修 |
|---|---|---|
| 本轮修复的生产文件 | 12 | ✅ 已修 |
| **2 个未接线模块**（`core/startup_checker.py`、`core/config_validator_startup.py`） | 6 | ❌ 处置归 P2-1（死代码口径） |
| 测试文件里的 docstring / 示例 | 6 | ❌ 文档里举例说明坏写法是正常的 |
| **构建产物里的源码副本**（`dist/scada-backend/_internal/...`、`dist-scada-*.prev/`） | 10+ | ❌ 产物，不该进扫描集（见 §5） |

→ 修完本轮后，**生产代码里 R1 命中为 0**（剩下的全是 docstring 与未接线模块）。

> ⚠️ 这也是「**不定义口径的计数没有意义**」的实例：同一个仓库，
> 「40 处」「60 处」「34 处」三个数字都能算出来，取决于算不算 docstring、
> 算不算产物副本、算不算未接线模块。**给数字必须给口径。**

### 1.2 生产路径上的三条硬证据

**(a) 打包后的启动日志**

起 `resources/backend/scada-backend.exe`（round 172 的安装包产物），日志出现：

```
配置验证失败 [devices]: 配置文件不存在: 配置\devices.yaml
配置验证失败 [alarms]:  配置文件不存在: 配置\alarms.yaml
配置验证失败 [system]:  配置文件不存在: 配置\system.yaml
```

而三份配置**一个不少**地躺在 `_internal/配置/`。

**(b) 运行时写入落点**

`locate_writes.py`（前后快照对比文件树差异）证明 DB 落在 `_internal/data/`，
即真实数据目录是「exe 旁边」，而相对路径代码去 CWD 找。

**(c) 全局单例 import 即 mkdir**

`core/ops_tools.py` 模块尾部：

```python
ops_audit = OpsAuditLogger()      # 默认 log_dir="logs"
```

`OpsAuditLogger.__init__` 里 `self._log_dir.mkdir(parents=True, exist_ok=True)`
—— 也就是说 **`import core.ops_tools` 这一步就会在当前工作目录下建 `logs/`**。
从服务 / 计划任务 / 冻结产物启动时，运维审计日志落到别处，
与 `LogConfig.LOG_DIR`（绝对路径）指向的日志目录**分裂成两处**。

### 1.3 为什么要区分「生产路径」与「未接线模块」

`core/` 下约 52 个模块文件头带 `WIRED = False` 标注（生产零引用），
且有守卫用例 `tests/test_core_regressions.py::test_unwired_marker_matches_reality`
（AST 扫描 import）保证「标注 ⟺ 事实」。

这些模块里的相对路径**不是生产缺陷**，处置归 P2-1（死代码口径，待主人拍板）。
本轮已核实并**排除**：`backup_verifier` / `data_compressor` / `db_pool_enhanced` /
`query_analyzer` / `startup_checker` / `config_validator_startup`。

> 附带核实：`core/config_validator_startup.py` 与 `core/startup_checker.py`
> 在生产路径**零调用**——`run.py` 用的是另一个 `core/config_validator.py`。
> 名字相近，容易修错文件。

---

## 2 修复清单

统一手法：把「相对路径 → 绝对路径」交给项目自带的 `paths.resolve()`
（基准 `BASE_DIR` 由 `__file__` / `sys.executable` 推导，**与 CWD 无关**；
对绝对路径是透传）。

| 文件 | 处数 | 修复内容 | 后果（修前） |
|---|---|---|---|
| `core/config_validator.py` | 1 | `validate_all_configs` 的 `Path(config_dir)` → `paths.resolve(...)` | 打包后配置校验永远报「文件不存在」 |
| `core/ops_tools.py` | 6 | `OpsAuditLogger.__init__`、`clean_old_backups`、`clean_log_files`、`DiagnosticExporter._collect_config` / `_collect_db_stats` / `_copy_recent_logs` | 全局单例往 CWD mkdir；清理假成功；诊断包三段全空 |
| `core/structured_logging.py` | 1 | `setup_logging` 的 `Path(log_dir)` → `paths.resolve(...)` | 按默认值调用时日志目录随 CWD 漂移 |
| `tools/device_simulator.py` | 1 | 加 `sys.path` 引导 + `self.config_path = str(paths.resolve(config_path))` | 从别处运行报「配置不存在」，与文件真缺失不可区分 |
| `tools/vacuum_db.py` | 2 | `SRC` / `DST` 走 `paths.resolve(...)` | 连到 CWD 下另一个（或空的）库 → 行数全 0 → 误判「数据全丢了」 |
| `.github/scripts/emit_failure_annotation.py` | 1 | `LOG` 改为相对 `__file__` 定位仓库根 | CI 失败时唯一公开可读的诊断通道会退化成「未找到 pytest.log」 |

**为什么 `.github/scripts/emit_failure_annotation.py` 值得单独说**：
GitHub Actions 的 job log 需要管理员权限（本仓库匿名只读，取 log 是 403），
所以 **annotation API 是 CI 失败详情唯一公开可读的通道**。
一旦这个脚本自己因为「在别的目录下执行」读不到 `pytest.log`，
它就会输出「未找到 pytest.log（测试步骤可能没跑到）」——
把「通道坏了」伪装成「测试没跑」。这是**诊断能力本身的单点**。

### 2.1 顺手清掉的两个未用 import

改了上面两个文件后，`from pathlib import Path` 变成未用（`Path(` 计数归 0），
一并删除：`core/config_validator.py`、`core/structured_logging.py`。
（`pyflakes` 复核：本轮改动**零新增** lint 问题，HEAD 上既有的未用 import 原样保留、不扩大范围。）

---

## 3 新回归测试：`tests/test_cwd_independence.py`（16 例）

四层结构，从「契约」到「事实」逐层收紧：

| 层 | 类 | 例数 | 断言什么 |
|---|---|---|---|
| 1 | `TestPathResolutionContract` | 6（含 4 条参数化） | `paths.resolve` 的映射不变量（`'配置'` → `CONFIG_DIR` 等）、绝对路径透传、CWD 无关性 |
| 2 | `TestCallSitesRouteThroughResolve` | 5 | 用 `resolve_spy`（monkeypatch 记录入参）断言每个调用点**确实**经过了 `paths.resolve` |
| 3 | `TestCwdIndependence` | 2 | `monkeypatch.chdir(tmp_path)` 后端到端：配置校验仍通过、CWD 下不新建 `logs/` `data/` `配置/` |
| 4 | `TestNoBareRelativePathLiteral` | 3 | AST 静态扫描 `Path(<裸目录字面量>)`；**自动跳过带 `WIRED = False` 的文件** |

两个实现要点：

- **静态扫描必须用 AST 取 docstring 行号**。文档里举例说明坏写法（写 `Path('配置')`）
  是正常的，按「行首三引号」判断会漏掉缩进过的 docstring 正文——
  首版就是这么误报自己写的解释性 docstring 的。
- **静态扫描要有「防滥用」守卫**。`test_unwired_skip_list_is_not_silently_growing`
  断言被跳过的未接线模块数 `< 120`：跳过的数量突然变大，说明有人用
  `WIRED = False` 把问题盖掉了，而不是修掉。

> 设计上砍掉了一条过宽的测试：首版还有 `test_relative_dir_literals_are_wrapped_in_resolve`，
> 正则把 `load_yaml_config('配置/alarms.yaml')`（被调方内部会 resolve）等 40+ 合法
> 调用点全算违规。**过宽的守卫等于没有守卫**（永远红 → 被忽略），故整条删除，
> 只留窄而高信号的 `Path(<裸目录字面量>)` 扫描。

---

## 4 变异验证（改了必须能变红，否则测试是摆设）

三组针对本轮修复 + 两组针对附带修复，全部按预期变红并已还原
（`grep -rn "MUTATION"` 复核干净）。

| # | 变异 | 预期 | 实测 |
|---|---|---|---|
| 1 | `config_validator` 改回 `Path(config_dir)` | 红 | **2 红**，且复现了打包环境那条日志的同一现象（`['devices','alarms','system']` 全判不存在） |
| 2 | `OpsAuditLogger` 改回 `Path(log_dir)` | 红 | **3 红**，且 CWD 下真的被建出 `logs/` |
| 3 | `_collect_config` 改回 `Path('配置')` | 红 | **2 红**（spy 与静态守卫**双重**抓到） |
| 4 | 守卫改「只扫 git 清单」后，往真实源文件塞违规 | 红 | **2 红**（`core/version.py:135` 宽异常、`:140` 裸 `isoformat()`）——证明扫描非空、机制有效 |
| 5 | `test_toggle_simulation_mode` 关掉落点重定向 | 红 | **1 红**（`assert fake_cfg.is_file()` → False）；且配置未污染，说明 conftest 兜底 fixture 同时生效 |

---

## 5 附带修复一：两条静态守卫被构建产物假红

### 5.1 现象

本地跑完 PyInstaller（输出 `dist-scada-1.3.1037/`）后，全量套件出现 2 红：

```
FAILED tests/test_silent_exception_guard.py::test_no_silently_swallowed_broad_exception
FAILED tests/test_timestamp_sql_consistency.py::test_no_bare_isoformat_in_sql_comparisons
```

报的**全是构建产物里的源码副本**：

```
dist-scada-1.3.1037/scada-backend/_internal/core/health_checker.py:548
dist-scada-1.3.1037/scada-backend/_internal/core/data_compressor.py:109
dist-scada-1.3.1037/scada-backend/_internal/core/report_generator.py:44
```

### 5.2 根因

两条守卫都按**目录名精确匹配**跳过：

```python
ALWAYS_SKIP = {..., "build", "dist", ...}
_SKIP_DIRS  = {..., 'dist', 'build', ...}
```

而本仓库的零删除构建约定产生的目录叫 `dist-scada-<版本>/` / `build-scada-<版本>/`
（名字刻意对齐 `.gitignore` 里已有的 `dist-scada-*/`、`build-scada-*/`）。
**精确匹配认不出带后缀的产物目录** → 扫到源码副本。

### 5.3 为什么这比漏报更危险

这两条守卫是「静默失效」类缺陷的**最后一道闸**。它们假红之后，
人的第一反应不是修守卫，而是：
① 把目录加进 skip 集（下次换个名字又红），② 干脆忽略这两条测试。
两条路都把闸门废掉。**假红会训练人忽略守卫。**

### 5.4 修法：只扫 git 清单

改成用 git 的文件清单（**`.gitignore` 是唯一权威**），不再靠人工维护前缀表：

```python
git ls-files -z --cached --others --exclude-standard -- "*.py"
```

- `--cached`：已跟踪文件（`legacy/`、`测试/` 仍在，是否扫由 skip 集决定）
- `--others --exclude-standard`：**新增但未被忽略**的源文件 → 新代码仍受管辖
  （只取 `--cached` 会漏掉开发者正在写的新文件 = 假绿）
- `-z`：NUL 分隔，非 ASCII 路径不被转义（`core.quotepath` 干扰不到）
- git 不可用时**退回** `os.walk` + 目录名跳过（历史行为），不因缺 git 而报错

实测：`git ls-files` 命中 335 个 `.py`，其中来自 `dist-scada` 的 **0 个**。

> 踩坑记录：第一版「读 HEAD blob 逐字节比对」判脏，被 `core.autocrlf=true` 打回——
> 工作区是 CRLF、git blob 是 LF，**每一份配置都被判成脏的**，告警永远在响。
> 改用 `git diff --quiet HEAD -- <path>`（走 git 自己的行尾归一化）。

### 5.5 每条守卫都补了「产物不得进扫描集」的回归用例

三个守卫文件各加一条 `test_scan_excludes_build_output`，
断言扫描集里不存在顶层目录段以 `dist` / `build` / `release` / `backup` 开头的路径。
注意**只看目录段**——`build.py` / `build.bat` / `release-manifest.json` 是文件，不算。

---

## 6 附带修复二：`配置/system.yaml` 的污染源

### 6.1 现象

全量套件跑完，`git status` 多出 `M 配置/system.yaml`，39 行 diff：
注释块被抹、`mqtt` 段重排、`simulation_mode: false` → **`true`**。

### 6.2 根因（不是 fixture 没跑，是 patch 打在失效符号上）

`展示层/api/api_system.py` 的 `POST /api/system/simulation-mode` **无条件**重写真实配置：

```python
config_path = paths.resolve('配置/system.yaml')   # 端点已改走 paths
...
with open(config_path, 'w', encoding='utf-8') as f:
    yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
```

而测试用的是：

```python
with patch('展示层.api.api_system.Path') as mock_path:   # ← 失效
```

`api_system.py` 里 `from pathlib import Path` 还在（所以 patch 不报错），
但**端点已经不再引用 `api_system.Path`** 来计算落点。
于是 patch 变成了空操作，测试真的把仓库配置整份重写了。

> 这正是「**patch 目标存在 ≠ patch 生效**」：`patch()` 只在属性不存在时才抛
> `AttributeError`；属性存在但已不在代码路径上，它会静默成功。

### 6.3 修法

只重定向 `配置/system.yaml` 这一个落点，其余路径解析保持原样：

```python
def _redirect(cfg):
    if str(cfg).replace('\\', '/').endswith('配置/system.yaml'):
        return fake_cfg          # tmp_path
    return _real_resolve(cfg)

with patch('展示层.api.api_system.paths.resolve', side_effect=_redirect):
    ...
assert fake_cfg.is_file()        # 落点确实被写（仍走真实持久化分支），但写的是 tmp
```

最后那条断言让测试**fail-closed**：将来若有人再把 patch 打偏，测试直接变红（变异 5 已验证）。

### 6.4 conftest 兜底 fixture 的盲区（已文档化 + 已加告警）

`tests/conftest.py` 已有 `restore_polluted_configs`（session 粒度快照 → 会话结束还原）。
但它有个**盲区**：

> 快照取自**当前工作区**。若上一次会话被中断（Ctrl-C / 超时 SIGTERM）导致
> teardown 没跑，污染会沉积下来，被下一次会话当作「原状」快照 ——
> 还原等于空操作，脏状态**永久化**。

已加「开局即脏」告警（`git diff --quiet HEAD -- <path>` 判定），
实测会响，且**不会误报**（净态下 5 个配置文件全判 `dirty=False`）。
选择告警而非自动 `git checkout` 还原——因为主人可能**故意**在本地改了配置没提交，
自动还原会无声毁掉主人的改动。

---

## 7 附带修复三：偶发失败定性（safe-delete 守卫）

### 7.1 现象

`tests/test_disaster_recovery.py::TestConfigRecovery::test_config_backup_restore`
—— 全量套件里偶发红，**单独跑必绿**。这条「偶发失败」在队列里**未定性挂了两轮**。

### 7.2 根因（本机特有，CI 上没有）

该用例只做一件事：`tmp_path` 里 `config_file.unlink()`（模拟"原文件丢失"），
然后从备份恢复。

而本机 WorkBuddy 注入了 **safe-delete 守卫**：

| 环境变量 | 值 |
|---|---|
| `CODEBUDDY_SAFE_DELETE_BULK_THRESHOLD` | `50` |
| `CODEBUDDY_SAFE_DELETE_BULK_STATE_DIR` | `%TEMP%\codebuddy-safe-delete-bulk` |
| `CODEBUDDY_SAFE_DELETE_BULK_GUARD` | `…\cli\vendor\shim\safe-delete-bulk-guard.cjs` |
| 注入方式 | `PYTHONPATH=…\cli\vendor\shim` |

守卫的计数是 **`scope=turn`——按每次工具调用累计**。
一次 `pytest tests/` 就是一轮，而**被测代码自身**删的文件也计入
（日志轮转、归档压缩、队列清理、临时库……）。跑到第 50 个删除之后，
**此后每一次删除都被拒**。pytest-randomly 会打乱用例顺序，
所以「撞在墙上」的用例每轮都不同 → 看起来像偶发。

### 7.3 铁证：守卫自己的状态文件

不用猜——守卫把拒绝记录写在自己目录里：

```json
// %TEMP%\codebuddy-safe-delete-bulk\<hash>\state.json
"requestRejections": {
  "3ec95c58...": { "rejected": true, "count": 50, "threshold": 50,
    "targets": ["…\\.pytest_tmp-30572\\test_config_backup_restore0\\config\\test.yaml"],
    "targetCount": 1 },
  "13208dcf...": { "rejected": true, "count": 50, "threshold": 50,
    "targets": ["…\\.pytest_tmp-34604\\test_config_backup_restore0\\config\\test.yaml"],
    "targetCount": 1 }
}
```

**`targetCount=1` 而 `count=50`** —— 只删 1 个文件却被拒，
说明拒的理由是**本轮累计已饱和**，不是这次删除本身可疑。这条特征一出现即可定性。

> 反证：在 `%TEMP%` 下一条命令里删 60 个文件 → **全部成功**。
> 所以计数不是「绝对文件数」，而是与工作区/调用上下文相关。

### 7.4 修法

把用例里的删除换成**改名**（零删除姿势），语义等价：

```python
# 原：config_file.unlink()
lost = config_file.with_name('test.yaml.lost')
config_file.rename(lost)
assert not config_file.exists()
```

并在 docstring 里写明**为什么不能改回 `unlink()`**，附上守卫的拒绝记录作为证据，
免得后人"顺手改回去"。

> ⚠️ 不要用「调高 `CODEBUDDY_SAFE_DELETE_BULK_THRESHOLD`」来解决 ——
> 那和 unset 守卫同性质，是绕过安全控制。
> 正解是让操作**根本不产生待删文件**（零删除姿势）。

### 7.5 同步沉淀

已把这条诊断写进 skill `safe-delete-guard-workarounds`（新增「坑二」）：
原有的「判定真失败还是被 guard 掐」一节只覆盖了**幻影失败**（无汇总行），
而本条是**真失败但根因在 guard**（**有** traceback）——症状相反，极易误判。

---

## 8 验证汇总

| 项 | 结果 |
|---|---|
| 后端全量套件 | 见 §8.1（本轮新增 18 例） |
| `tests/test_cwd_independence.py` | 16 passed |
| 三条静态守卫合跑 | 31 passed |
| 变异验证 | 5 组全部按预期变红并还原；`grep MUTATION` 干净 |
| `pyflakes`（本轮改动文件） | 零新增告警；消除 2 处未用 `Path` import |
| `配置/system.yaml` | 套件前后 md5 一致（`6a3e1ea7…`），不再被写脏 |
| 提交 / 推送 | 后端 `dbb4cba`（15 文件 641+/52−）、前端 `7a93215`；**两仓库远端 sha == 本地** |
| 后端 CI `SCADA CI` | **success**（`lint` / `build-backend` / `test` 三 job 全绿，run `35714873823`） |
| 前端 CI `SmartSCADA Frontend CI` | **success**（`7a932154`） |

### 8.1 全量套件

```
SUITE_START=17:56:54  yaml_before=6a3e1ea74220d68022f7bb9c3473e288
2474 passed, 317 warnings in 927.96s (0:15:27)
SUITE_END=18:12:26  yaml_after=6a3e1ea74220d68022f7bb9c3473e288
```

- **2474 passed / 0 failed**（= round 172 的 2456 + 本轮新增 18 例）
- **`yaml_before == yaml_after`** → `配置/system.yaml` 零污染，
  说明污染源已堵住（conftest 的兜底 fixture 这次无事可做）
- 前一轮（本轮修复前）是 `1 failed, 2473 passed`，那 1 红即 §6 之外的第 4 个附带修复
  （`test_config_backup_restore` 的 safe-delete 守卫假红，见 §7 与 errors.log）

---

## 9 遗留 / 待主人确认

- **构建垃圾**：本轮又发现 `~250 个 .pytest_tmp-* 目录 / 7380 个文件`（全部被 gitignore，
  但占盘）。连同 round 172 记录的 `release*/`、`dist-scada-*/`、`build-scada-*/`、
  `backend.stale-*/`，**总量已超 3 GB**。清理需主人拍板（批量删除会触发本机
  safe-delete 保护，且这些目录里有 pytest 临时产物）。
- **`release2/smartscada-Setup-1.3.1033.exe`**（带缺陷的旧包）是否删除。
- **P2-4**：968 行未接线实现 —— (A) 做完迁移 / (B) 归档。
- **P2-1 / P2-2 / P2-8**：死代码统一口径（本轮再次确认 `WIRED = False` 有 52 个模块）。
- **`dist/scada-backend/` 陈旧**（9 月 19 日）→ 发布清单如实标 `stale: true`。
  **这不是缺陷**：提交后 HEAD 时间必然晚于任何产物 mtime，`stale` 是设计常态。
  真正要出包时按 round 172 的流程重出。
- 前端 `package-lock.json` 的 `version` 字段仍漂在 `1.3.1010`。
- 后端 CI 的 `build-backend` job **只验证 exe 存在、从不验证它能跑起来**
  （PyInstaller 缺 hiddenimport 只在运行时暴露）—— round 172 发现的候选缺口，未动手。
- CI 上 `dbstat` 不可用 → `size_to_data_ratio` 永不被校验（已知覆盖缺口）。
- P2-6（God object 1385/1194/1104 行）未动。

---

## 10 方法论收获

1. **「patch 目标存在 ≠ patch 生效」。** `patch()` 只在属性不存在时抛异常；
   属性还在但已不在代码路径上，它会**静默成功**——测试就变成了真写。
   凡是 patch 内部实现细节的测试，都要问一句「被 patch 的符号现在还参与计算吗」，
   并加一条 fail-closed 断言（本例的 `assert fake_cfg.is_file()`）。
2. **守卫的假红比漏报更危险。** 漏报是「没抓到」，假红是「训练人忽略」。
   所以守卫的排除规则**必须挂在唯一权威上**（`.gitignore` / git 清单），
   而不是人工维护的前缀/名字表——后者一定会随目录改名而失配。
3. **「先证明扫描器在扫东西」和「先证明扫描器扫得准」是两条不同的守卫。**
   前者防「排除了全部 → 假绿」（已有），后者防「扫到不该扫的 → 假红」（本轮补）。
   两者都要有。
4. **诊断能力本身是单点，要按单点对待。** `emit_failure_annotation.py` 读不到日志时，
   会把「通道坏了」报告成「测试没跑」。凡是「失败时唯一可读的通道」，
   它自己的健壮性优先级等同于被测代码。
5. **过宽的守卫等于没有守卫。** 静态扫描宁可窄而准（`Path(<裸目录字面量>)`），
   不要宽而糊（把 40+ 个合法调用点全算违规）——后者必然被忽略。
6. **给数字必须给口径。** 队列里那句「P2-5 有 40 处硬编码相对路径」没有口径，
   于是**没法核对**——本轮同一个仓库，「40 处」「60 处」「34 处」都能算出来，
   取决于算不算 docstring、算不算构建产物副本、算不算未接线模块。
   **凡是要进队列/报告的数字，都必须附上「怎么算出来的」**，
   否则它既不能验收也不能推翻，只会被反复抄下去（这个 40 就抄了好几轮）。
