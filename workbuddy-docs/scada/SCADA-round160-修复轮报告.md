# SCADA round 160 修复轮报告

- **日期**：2026-09-16
- **版本**：`1.3.1005` → **`1.3.1006`**
- **仓库**：后端 `C:\Users\cxx\WorkBuddy\Claw\industrial_scada`；前端 `C:\Users\cxx\scada-app`
- **上游**：round 159 修复轮（`06a489c` / `f970317`）+ 5 路代码质量审计报告
- **本轮主题**：P1-4 静默吞异常治理 · P1-6 数据库索引引导落地 · P2-7 模块注册表接线

---

## 一、取项与编排

队列最高优先级未阻塞项为 **round 160**，含三条：

| 编号 | 主题 | 分工 |
|---|---|---|
| P1-4 | 静默吞异常（`except Exception: pass`） | 4 路并行子 agent：`core` / 数据链路 / 外围 / 主线写静态守卫 |
| P1-6 | 缺索引（`index_advisor` 从未接线） | 主线 |
| P2-7 | `module_registry` 生产环境从不注册 | 主线 |

上一轮结束时这四项的改动**已落盘但未提交、未验证**（工作区 48 个文件 dirty）。本轮工作是**收口**：独立复核 → 全量验证 → 补测试 → 提交推送。

---

## 二、P1-4 静默吞异常治理

### 口径修正（重要）

队列原记「70 处」，那是**正则口径**。改用 AST「`ExceptHandler` 且块体仅一条 `Pass`/`Continue`」后为准，全库共 **89 处**。

分布：`core` 33 / 采集层 15 / gateway 10 / 存储层 10 / 展示层 4 / 报警层 4 / 用户层 4 / timeseries 3 / 智能层 3 / `config.py` 2。

### 结果

全库 AST 实测对比（同一扫描器跑 `HEAD=06a489c` 的归档副本 vs 本轮工作区）：

| 口径 | 治理前 | 治理后 |
|---|---|---|
| **宽异常被静默丢弃**（`except Exception/BaseException: pass\|continue`） | **82** | **13** |
| 窄异常被静默忽略 | 23 | 16 |
| 合计 | 105 | 29 |

**关键结论：生产服务代码里的宽异常静默丢弃已归零。** 剩余 13 处宽异常**全部**落在守卫扫描范围之外：

- `tools/` 运维脚本 **11 处**（`security_scan.py` 7 / `auto_metrics.py` / `deploy.py` / `diagnostics.py` / `performance_baseline.py`）
- `测试/` 旧中文名测试目录 **2 处**（裸 `except:`，已被 `pyproject` 排除出收集范围）

生产侧剩余的 16 处窄异常属明确的、可枚举的预期分支，**刻意保留**：`queue.Empty`（轮询取空 → `continue`）、`socket.timeout`（超时 → 重试下一轮）、`RuntimeError` / `(ValueError, TypeError)`。

### 关键修复（不只是「把 pass 换成 logger」）

本轮真正有价值的是**把「静默放行」改成「fail-closed」**，而非补日志：

1. **`用户层/auth.py::_blacklist_user_tokens()`** —— 原实现把「取令牌」和「落库」包在**同一个** `try` 里，`except Exception: pass`。后果：撤销令牌**落库失败**时函数静默返回，调用方以为撤销成功，**而已撤销的令牌仍可继续使用**。
   - 现改为：拆成两步，落库失败返回 `False`；`change_password()` 收到 `False` 时记 `logger.error` 并在返回值里带 `warning` 字段提示用户重新登录。
2. **`用户层/auth.py::refresh_token()`** —— 原代码把 `password_changed_at` 的时间戳解析**和**比对一起包在 `try` 里，解析失败 `except (ValueError, TypeError): pass` → **等于假定密码没改过**，已改密用户的旧刷新令牌可继续续期。
   - 现改为 fail-closed：解析失败直接 `return None` 拒绝续期，并记 `logger.error` 要求人工核查数据。
3. **`报警层/alarm_manager.py`** —— 损坏配置的备份逻辑、撤销失败路径等 5 处（见变异验证脚本）。

### 静态守卫（防回归）

新增 `tests/test_silent_exception_guard.py`，AST 扫描（**不是正则** —— 正则会被注释和 docstring 误伤）锁死两类退化：

- **裸 `except:`** 一律禁止（会连 `KeyboardInterrupt` / `SystemExit` 一起吞掉，导致 Ctrl-C 杀不掉进程）
- **`except Exception/BaseException: pass|continue`** 一律禁止

守卫自带**反向验证**：`test_narrow_silent_except_is_tolerated` / `test_broad_detection_catches_tuple_and_bare` 证明「宽 / 窄」判别逻辑本身是对的，不会误伤窄异常（否则守卫会把所有窄异常都报成违规，那就没人会认真修）。另有 `test_scan_covers_real_files` 断言扫描到 >100 个文件且抽查 5 个核心模块，**防止 `EXCLUDED_DIRS` 写错导致「扫了 0 个文件」的假绿**。

**独立变异验证**（我本人执行，非 agent 自述）：向 `core/` 注入一个含裸 `except:` + `except Exception: pass` 的临时文件 → 守卫测试 **2 failed**；删除临时文件后恢复绿。守卫确实有效。

---

## 三、P1-6 数据库索引引导

`core/index_advisor.py` 此前只「提建议」，从未被任何启动流程调用，建议从未落地。

新增 `core/index_bootstrap.py`，在 `run.py:84` **建库之后、开始采集之前**调用 `ensure_indexes(database)`：

- 索引清单**显式固化**为 7 条 `CREATE INDEX IF NOT EXISTS`，每条 DDL 上方写明「为谁建 / 为什么缺 / 预期收益」，并**引用具体调用点行号**
- 幂等：已有索引原样跳过；单条失败记 `logger.warning` 并继续，不中断其它索引
- 支持 `Database` 实例（走其线程本地连接池，`get_connection()` 上下文管理器负责 commit）与裸 `sqlite3.Connection` 两种入参

### 独立实测验证（我本人执行）

在**全新临时库**上实跑，并用 `EXPLAIN QUERY PLAN` 证明索引真的被查询计划用上：

```
PASS  全新库：无失败索引  -- failed=[]          ← 无列名/表名笔误
PASS  全新库：确实新建了索引  -- created=4 already=3
PASS  二次调用：全部命中已存在（幂等）  -- created=[]
PASS  清单里每个索引名都真实存在于 sqlite_master
PASS  查询计划用上 idx_history_timestamp   SEARCH history_data USING COVERING INDEX idx_history_timestamp (timestamp>?)
PASS  查询计划用上 idx_alarm_timestamp     SEARCH alarm_records USING COVERING INDEX idx_alarm_timestamp (timestamp>? AND timestamp<?)
PASS  查询计划用上 idx_device_status_device_time  SEARCH device_status USING INDEX idx_device_status_device_time (device_id=?)
PASS  查询计划用上 idx_alarm_device_level_time    SEARCH alarm_records USING INDEX idx_alarm_device_level_time (device_id=? AND alarm_level=?)
```

**这一步是必须的**：`_apply()` 刻意把单条 DDL 失败吞成 warning（容错设计），所以「索引名写错」这种错误**不会让测试变红**，只会在生产静默地什么都不建 —— 正是本项目最怕的失效模式。因此验证必须**直接检查 `result['failed']` 是否为空**，而不能只看「函数没抛异常」。

复现脚本：`verify_index_bootstrap.py`（本工作区）。

---

## 四、P2-7 模块注册表接线

**问题**：`core/module_registry.py` 是完整实现的模块注册表，但**生产环境从未注册过任何模块** → `/modules` API 恒返回空；`chaos_engineering` / `health_checker` 里 `get_instance('alarm_manager' | 'database' | 'data_collector')` 每次抛 `KeyError` **并被 `except: pass` 吞掉** → 这些检查实际上退化成常量。

**修复**：

1. 新增 `ModuleRegistry.register_instance(name, instance)` —— 直接登记**已有对象**，保留对象身份，不重复构造（`register()` 是「登记类 + 懒构造」，语义不同，不能混用）。
2. `get_instance()` 放宽为接受 `INITIALIZED / RUNNING / PAUSED`。此前只允许 `INITIALIZED` → **模块一旦 `start()` 就再也取不到实例**，对「运行期才查依赖」的调用方致命。仍拒绝 `REGISTERED`（还没构造实例）与 `ERROR` / `DISABLED`。
3. `run.py:266-269` 注册 4 个核心模块（`database` / `device_manager` / `alarm_manager` / `data_collector`）。

**注册顺序已核对**：注册位于 `run.py:266`，而四个变量分别在 `77`（database）、`95-97`（device_manager）、`140`（alarm_manager）、`219`（data_collector）赋值 —— **不存在「赋值前注册」**。

新增 `tests/test_module_registry_wiring.py`（14 用例）：4 个稳态检查 + 静态守卫（断言 `run.py` 里确实调用了 `register_instance`）+ 并发注册线程安全。

---

## 五、验证

| 项目 | 结果 |
|---|---|
| 后端全量套件 | **2004 passed / 0 failed / 0 skipped**（基线 1945，本轮 **+59** 条） |
| 耗时 | 382.44s（6分22秒） |
| 新增测试文件 | 5 个：`test_silent_exception_guard.py` / `test_module_registry_wiring.py` / `test_index_bootstrap.py` / `test_silent_failure_fixes.py` / `test_silent_success_fixes.py` |
| 独立变异验证 | 静默异常守卫：注入违规 → 2 failed → 清理后恢复绿 ✅ |
| 独立实测验证 | 索引引导：全新库 `failed=[]` + 4 条查询计划 SCAN→SEARCH ✅ |

---

## 六、提交与推送

| 仓库 | 提交 | 版本 | 远端核对 |
|---|---|---|---|
| 后端 | `06a489c` → **`7e5660c`**（54 文件，+2132/−181） | `1.3.1005` → **`1.3.1006`** | ✅ `ls-remote` == 本地 |
| 前端 | `f970317` → **`cfaae5f`** | `1.3.1005` → **`1.3.1006`** | ✅ `ls-remote` == 本地 |

- 推送方式：内置 mingit + 显式代理 `127.0.0.1:10808`（已先 `netstat` 确认端口在听）
- 前端本轮无代码改动，仅版本号 lockstep 对齐（`package.json` + `package-lock.json`）
- **提交前做了清场**：`data/audit_log.jsonl` 被还原到 HEAD，**未把测试垃圾带进提交**（见 §7.1）

---

## 七、本轮新发现（已登记进队列）

1. **`data/audit_log.jsonl` 是运行期产物，却被 git 跟踪** —— 每跑一次测试就往里追加几十条 `emergency_stop` / `estop_reset` 之类的**测试垃圾**（本轮 +91 行），导致每轮提交都夹带噪声。根因是测试写进了生产审计日志路径。
   - 建议：测试改用临时目录；该文件从 git 移除并 gitignore。**本轮已把它从提交中剔除**（工作区保留）。
2. **仓库根目录 `stderr.txt` 是一个 2.4 MB 的已跟踪二进制垃圾文件**（`stdout.txt` 58 B），自 5 月 30 日起就躺在 git 里。
3. `_mutate2.py`（变异验证脚本）被遗留在仓库根目录 —— 已移出到 `~/.workbuddy-ai/queue/quarantine/`。

---

## 八、待主人拍板（不阻塞，继续下一项）

沿用队列「待主人确认」区，本轮新增/强化：

- **第 7 条**（死代码处置口径）现在覆盖**四处**：P2-1 后端死模块 24 个 / 4578 行、P2-2 前端死 composable 45 个 / 6598 行（占前端 `src/` 42%）、P2-9 后端根目录 10 个游离脚本 1042 行、以及本轮新发现的 `stderr.txt` 2.4 MB + `data/audit_log.jsonl`。**建议统一口径：先归档不删。**
- **第 8 条**（横切关注点收敛保哪个）—— 需要产品口径。
- **第 1 条**（「验证通过」是轻档还是重档）—— 直接决定下一轮是做 P3 交付链（出安装包）还是继续清技术债。
