# SCADA round 171 —— 膨胀检测 CI 红灯根因（monotonic 开机秒数）+ 发布清单 lockstep 守卫

- 日期：2026-09-21（夜间）
- 版本：后端 `1.3.1035` → **`1.3.1036`**；前端 `1.3.1034` → **`1.3.1036`**（恢复 lockstep）
- 承接：round 170（中断会话收尾 + 后端 CI 4 类红灯修掉 3 类）

---

## 0. 摘要

round 170 结束时后端 CI 还剩最后一类红灯：`TestBloatDetection` ×3，**CI 红、本机绿**，
当时刻意没有做推测性改动，只加了诊断输出等一轮 CI 循环。

本轮拿到了 CI annotation，**根因 100% 确证，而且它不是测试缺陷，是产品缺陷**：

> `time.monotonic()` 在 Windows 上返回的是**开机以来的秒数**（`GetTickCount64`），
> 不是 Unix 时间戳。`Database._last_bloat_warn_at` 初值写成 `0.0`，
> 语义等于「在开机后第 0 秒告警过」。于是在任何**开机不足 3600 秒**的机器上，
> `now - 0.0 >= 3600` 恒为假 —— **首条膨胀告警被节流吃掉**。

后果：CI runner 每次都是新开机机器（annotation 实测 `now=915`）→ 必红；
现场设备**掉电重启后同样会静默最长 1 小时**，等于「缺陷 7：膨胀无自动检测」只修了一半。

顺带查出第二个同类静默失效：`release-manifest.json` 里前端产物路径是用**后端 VERSION**
拼的，生成器从不读前端 `package.json`；且 `_resolve_frontend_root()` 的候选路径**漏掉了
CI 布局**，导致 `frontend_deps_lock_digest` 在 CI 上静默为 null。

第三个发现是收尾时冒出来的一条偶发失败（`test_write_multiple_readback`）牵出来的：
**模拟器的「写保持」机制 100% 没生效** —— `build_slave_block` 把每台寄存器的保持时长
算进 `spec['hold']` 后**从来没有人读它**，四个 `SimDataBlock` 一律用 `hold_seconds=0`
构造。后果是客户端写入活不过一个更新周期：`--simulator` 模式下用户在界面上改的
继电器/设定值 1 秒后就被模型改回去，`writable_hold_seconds: 300` 是个摆设。

三处都已修复 + 补回归用例 + 变异验证（共 7 组）。

---

## 1. 核心发现 1：`TestBloatDetection` 的 CI 红灯

### 1.1 证据链（三步，缺一不可）

**第一步：读代码，推翻自己上一轮的假设。**
上一轮我猜「`check_bloat` 的 quick 口径（`PRAGMA freelist_count`）与 dbstat 口径不一致」。
读 `存储层/database.py:1059` 后**自我否定**：

```python
free_ratio = (free_pages / page_count) if page_count else 0.0
```

`free_pages` 无论 `include_dbstats` 与否都来自 `PRAGMA freelist_count`；
`include_dbstats` 只影响 `data_bytes_mb` / `size_to_data_ratio`。**不存在口径不一致。**

同时排除了另两个猜测：
- loguru `{}` 与 `%s` 不匹配 → 否，`database.py:16` 是 `logging.getLogger(__name__)`（标准库）
- `db` fixture 是模块级导致节流生效 → 否，`tests/test_storage_regressions.py:37` 是函数级

**第二步：本地复现。**
写临时 pytest 插件，把**被测模块**的 `time.monotonic()` 伪装成「刚开机 200 秒」：

| 模拟开机时长 | 结果 |
|---|---|
| 100000s（≈本机 24.6h） | 5 passed |
| 3599s | **3 failed** |
| 200s（CI runner 量级） | **3 failed** |

失败文案与 CI annotation **逐字一致**。

**第三步：CI annotation 一锤定音。**
（CI 的 job log 需管理员权限 403，annotation 是唯一公开可读通道 —— 这正是
round 170 加 `emit_failure_annotation.py` 的价值）

```
E       AssertionError: 空闲页占比过高却没有告警日志 —— 缺陷 7 的核心就是"没有自动检测"
E           quick: free_page_ratio=0.9579 freelist=478 page_count=499 is_bloated=True
E           full : free_page_ratio=0.9579 data_bytes_mb=None size_to_data_ratio=None
E           阈值=0.3
E           logger: effective_level=WARNING propagate=True manager.disable=0
E           节流: _last_bloat_warn_at=0.0 now=915 间隔=3600
E           caplog 记录数=0
```

**`now=915`** —— CI runner 开机仅 915 秒（约 15 分钟）。本机是 `now=88999`。
`915 - 0.0 = 915 < 3600` → 告警被吞。**根因确证。**

> 这条 `now=915` 是 round 170 我加的 `_bloat_diag()` 打出来的。
> 上一轮只加诊断、不做推测性改动的决定是对的 —— 否则这一轮就是在修一个不存在的口径问题。

### 1.2 修复（两层，缺一不可）

**(a) 产品代码** `存储层/database.py:86`

```python
# 初值必须是 -inf（语义 =「从未告警」），**不能写 0.0**
self._last_bloat_warn_at = float('-inf')
```

`now - (-inf) = inf >= 3600` → 首次检测永远通过节流，与机器开机时长无关。

**(b) 测试** `tests/test_storage_regressions.py`

- 新增 `_force_warn_window(db)`：把窗口拨到「很久以前」，且**读被测模块的时钟**
  （`db_module.time.monotonic()`，不是测试模块的 `time`）
- 三处 `db._last_bloat_warn_at = 0.0` 全部替换
- 新增 `_FakeMonotonic`：把某模块的 `monotonic()` 伪装成指定开机时长，其余属性透传
- 新增回归用例 `test_fresh_boot_does_not_suppress_first_warning`：
  **刻意不重置**节流字段，直接依赖新建实例的初值 → 初值写错就**行为上**红
- 修 `_bloat_diag()`：原先打印的是**测试模块**的 `time.monotonic()`
  （上一轮我正是被这个 `now=88999` 误导过），改为打印**被测模块**实际用的时钟

> 踩到的坑：`_force_warn_window` 第一版用测试模块的 `time.monotonic()`，
> 在被测模块时钟被伪装后算出「很久以后」而不是「很久以前」，节流照样命中。
> **凡是「读取被测代码用的时钟」的地方，都必须走被测模块的引用。**

### 1.3 变异验证

| 变异 | 结果 |
|---|---|
| A：初值 `-inf` → `0.0` | 1 failed（新用例的初值断言，精准命中） |
| A2：在 A 基础上再屏蔽初值断言，只看行为 | 1 failed（**行为断言也守得住**） |
| B：`_force_warn_window` 回退成 `0.0` | **3 failed** |

A2 的意义：证明这条用例不是「只断言内部属性」，而是真能捕获行为回归。

---

## 2. 核心发现 2：发布清单的前后端版本 lockstep 静默失效

### 2.1 缺陷

`tools/gen_release_manifest.py:218`：

```python
FRONTEND_ROOT / "release" / f"SmartSCADA Setup {version}.exe"
```

`version` 是**后端 VERSION**。而安装包名实际由前端 `package.json` 的 version 决定
（electron-builder 读它）。生成器**从不读前端 package.json**。

→ 两端版本一旦不同步，清单会写出一条字段齐全、看起来正常、但**永远不可能存在**的路径。
这正是本项目一直在清的那类「静默失效」。

本轮就真实触发了：后端 `VERSION` 已到 `1.3.1035`，前端还停在 `1.3.1034`。

### 2.2 附带的第二处静默失效

`_resolve_frontend_root()` 的候选路径只有：

1. `BACKEND_ROOT.parent / "scada-app"`（开发机：与后端同级）
2. `Path("C:/Users/cxx/scada-app")`（本机历史布局）
3. `BACKEND_ROOT.parent.parent / "scada-app"`

CI 的布局是**前端 checkout 到后端工作区的子目录** `<workspace>/scada-app`
（round 170 在 ci.yml 里加的 `Checkout frontend sources`），
即 `BACKEND_ROOT / "scada-app"` —— **三条候选都匹配不到**。
于是 CI 上 `FRONTEND_ROOT` 指向不存在的路径，
`frontend_deps_lock_digest` **静默变成 null**，没有任何断言会报错。

### 2.3 修复

`tools/gen_release_manifest.py`：

- 新增 `_frontend_version()`：读前端 `package.json` 的 version（读不到返回 None）
- 新增 `_lockstep_state()`：`synced` / `skewed` / `unknown`
- 清单新增两个顶层字段：`frontend_version`、`version_lockstep`
- `_collect_artifacts(version, frontend_version)`：
  版本不同步时给**前端产物条目**加 `stale` + note，note 里写明两端各自的实际版本
- `_frontend_root_candidates()` 抽成独立函数（为了可测），补上 CI 布局候选
  `BACKEND_ROOT / "scada-app"`

`tests/test_release_manifest.py` 新增 `TestFrontendVersionLockstep`（8 条）：
- 读前端版本、前端不在场时状态为 `unknown`（不猜成 synced）
- `_lockstep_state` 三态分类
- 不同步 + 产物不存在 → note 点明「造不出来」且写出两个版本号
- 不同步 + 磁盘上**真有**同名文件 → 仍标 `stale`
- **反向对照**：同步时不得误标（否则标注会被当噪音忽略）
- 清单暴露 lockstep 字段
- 已提交清单的 lockstep 状态**自洽性**（刻意不断言等于 synced ——
  那是机器状态依赖，正是本轮修掉的那类反模式）
- 候选列表覆盖 CI 布局 + 搜索逻辑 + 兜底

变异验证：

| 变异 | 结果 |
|---|---|
| `frontend_skewed` 恒为 `False`（假装同步） | 2 failed |
| 删掉 CI 布局候选路径 | 1 failed |

### 2.4 版本对齐

前端 `package.json` `1.3.1034` → `1.3.1036`，恢复与后端 lockstep。

> 注：前端 `package-lock.json` 的 `version` 字段长期漂在 `1.3.1010`
> （历史多次抬版本都没同步），`npm ci` 容忍，故本次沿用既有做法只改 `package.json`。
> 这个漂移本身是个待清理项，已记入队列。

---

## 3. 核心发现 3：模拟器「写保持」机制完全失效

### 3.1 怎么发现的

全量套件跑完报 **2446 passed / 1 failed**：
`test_modbus_protocol_e2e.py::test_write_multiple_readback`。

我的改动（`database.py` 的 `-inf`、清单工具）与 Modbus 协议无关，所以先判 flaky：

- 单跑该用例 3 次 → 全过
- 单跑整个 e2e 文件 15 次 → 全过（135 个用例零失败）

→ 是**全量套件里的交叉干扰**，不是独立生命周期竞态。**别猜，读代码。**

### 3.2 根因

`tools/modbus_simulator.py::build_slave_block`：

```python
specs.append({..., 'hold': writable_hold if writable else read_only_hold})
...
hr = SimDataBlock(0, [0] * block_size, written={}, hold_seconds=0)   # ← 传的是 0
```

而 `SimDataBlock.setValues` 用的是 `self._hold`：

```python
self._written[start + i] = now + self._hold      # = now + 0 = now
```

模型线程的跳过条件：

```python
if any(hr._written.get(i, 0.0) > now for i in range(bi, bi + length)):
    continue                                      # now_write > now 恒为假 → 从不跳过
```

**`spec['hold']` 全仓 grep 确认：只有赋值、没有任何读取点。**

→ 写保持形同虚设，客户端写入只能撑到下一个更新 tick。

### 3.3 决定性实验

起模拟器（`--interval 1.0`）→ 写 4 个继电器 → 立即回读 → 等 1.5s 再回读：

| | 修复前 | 修复后 |
|---|---|---|
| 立即回读 | `[111, 222, 333, 444]` ✓ | `[111, 222, 333, 444]` ✓ |
| 等 1.5s 回读 | **`[1, 1, 1, 1]`** ✗ | `[111, 222, 333, 444]` ✓ |

这解释了 flaky 的机理：写与读之间恰好撞上一次更新 tick 就红。
全量套件里 2447 个用例的时序抖动让它偶发，单跑几乎不复现 —— **最难排查的那类红**。

### 3.4 对产品的意义（不只是测试）

`run.py --simulator` 模式下，用户在 SCADA 界面上改的继电器/设定值
**1 秒后就被模型改回去**，看起来「写了没用」。
配置项 `writable_hold_seconds: 300` 完全是个摆设。
`--simulator` 是演示与验收路径，这个缺陷会直接误导验收。

### 3.5 修复

`tools/modbus_simulator.py`：

1. **让保持时长真的传下去** —— `SimDataBlock` 新增 `hold_by_index`（block 索引 → 秒），
   新增 `hold_for(idx)`；`setValues` 逐地址查表算过期时刻。
   为什么不能只用一个 `hold_seconds`：同一个 hr 块里 rw（300s）与只读（5s）
   两种寄存器混在一起，单个标量表达不了。
2. **把「检查写保持」与「写模型值」关进临界区** —— `SimDataBlock` 新增 `self.lock`，
   `update_slave` 的整个 check+write 包在 `with hr.lock:` 里，`setValues` 的
   「写值+登记」也包在同一把锁里。
   理由：没有锁时，模型线程可能在「检查」（当时该地址还没被写，不跳过）之后、
   「写模型值」之前被客户端插入，把刚写进去的值静默覆盖 —— 窗口微秒级，
   但写保持的**全部意义**就是「客户端写了就别动它」。
3. 修正模块 docstring 里那句错误断言（原文写「客户端写入也落在同一个 list，
   写后读回天然成立」——只在同一更新周期内成立）。

### 3.6 回归测试

- 新增 `tests/test_modbus_simulator_hold.py`（**8 例**）：保持时长是否真的传到数据块、
  `setValues` 记的过期时刻是否用了 spec 的时长、模型是否跳过被写寄存器、
  保持期过后模型是否重新接管（防「永久冻结」）、以及两条并发不变量
  （`update_slave` 必须等待数据块锁 / 压测下客户端写入一次都不能丢）
- `tests/test_modbus_protocol_e2e.py` 新增
  `test_client_write_is_held_across_model_updates`（写 → 等 1.5s → 回读），
  **这就是本该早就存在的用例**

### 3.7 变异验证

| 变异 | 结果 |
|---|---|
| A：`hold_by_index` 不传给数据块（还原原缺陷） | **4 failed**（含那条新 E2E） |
| B：`update_slave` 去掉 `with hr.lock` | **1 failed**（确定性锁守卫） |

变异 B 的守卫是**确定性**的，不靠概率：主线程先持有锁，再看 `update_slave`
是否被挡住 —— 用了锁就阻塞，没用锁就立刻跑完。

### 3.8 同类缺陷扫描（另一套写跟踪）

`采集层/simulated_client.py` 与 `采集层/device_behavior_simulator.py` 也各自维护
写入跟踪（`_written_values` / `_written_coils`），但它们的读取路径是
**「写入字典优先」且永不过期**（`written_value = self._written_values.get(address)`
命中即返回）→ **没有同类缺陷**。

**结论：写保持失效只存在于 `tools/modbus_simulator.py` 一处。**

---

## 4. 次要发现

### 4.1 CI 与本机 SQLite 编译选项不同

CI annotation 显示 `data_bytes_mb=None`（本机是 `0.08`），
说明 **CI 的 SQLite 没编译 `SQLITE_ENABLE_DBSTAT_VTAB`**，`dbstat` 虚表不可用。

全仓扫描确认：只有 `test_storage_regressions.py` 依赖这些字段，
且已有 `if stats['data_bytes_mb'] is not None:` 守卫 → 不会红。
但**代价是 CI 上永远不校验 `size_to_data_ratio`**，属已知覆盖缺口。

### 4.2 同类缺陷全仓扫描（`monotonic` 当节流时钟）

| 位置 | 用法 | 是否有同类缺陷 |
|---|---|---|
| `存储层/database.py:1106` | 告警节流 | **有，本轮已修** |
| `core/db_pool_enhanced.py:193/226` | `deadline = monotonic() + timeout` | 无（差值相消） |
| `core/health_checker.py:70/98` | `duration = monotonic() - start` | 无 |
| `tools/modbus_simulator.py:189/255` | `_written.get(i, 0.0) > now` | 无（方向相反，`0.0 > now` 恒假 = 不保持） |

生产代码里其余时间戳判定全部用 `time.time()`（绝对时间戳），`0.0` 当「从未」是正确的。

**结论：全仓只有这一处踩 monotonic 陷阱。**

### 4.3 P2-4 调查结论（只调查，未动手）

「同一能力三套实现」的真实结构是 **「一套在用 + 一整套没接线」**：

| 能力 | 生产在用（`run.py` 装配） | 无生产引用 |
|---|---|---|
| 报警输出 | `报警层/alarm_output.py::AlarmOutput`（438 行） | `real_alarm_output.py::RealAlarmOutput`（393）<br>`simulated_alarm_output.py::SimulatedAlarmOutput`（230） |
| 语音广播 | `报警层/broadcast_system.py::BroadcastSystem`（300 行） | `real_broadcast.py::RealBroadcastSystem`（212）<br>`simulated_broadcast.py` |
| 接口 | — | `报警层/interfaces.py`（133） |

关键事实：

- 提交 `c32f1d3`（"chore: 删除废弃入口 run_new.py、run_v2.py、factory.py，保留 run.py"）
  **删掉了 `factory.py`** —— 而那是**唯一**会实例化 `RealAlarmOutput` /
  `SimulatedAlarmOutput` / `RealBroadcastSystem` 的地方。删掉之后这一整套就断了线。
- 全仓（含 yaml/json/md/txt）grep 确认：非测试引用为零；无动态 import。
- `报警层/alarm_manager.py:1236-1272` 的 `_invoke_alarm_output` / `_invoke_broadcast`
  **刻意做了两套命名兼容**（`trigger_alarm` vs `activate_alarm`、
  `speak_alarm` vs `speak`），注释明确写着「旧实现硬调 → AttributeError 被吞 → 全线静默漏报」。
  → 说明这是**半途而废的迁移**，不是纯粹的遗留垃圾。
- `SCADA系统教科书.txt:1030-1067` 还在描述那个已删除的工厂（文档过期）。
- 这 5 个文件约 **968 行**，另有 4 个测试文件（`test_real_alarm_broadcast.py`、
  `test_alarm_output_broadcast.py` 等）在**测死代码** —— 绿的测试给出虚假安全感。

**处置需要主人拍板**：是「把迁移做完（接线到接口实现）」还是「归档这 968 行」。
前者是行为变更且触及报警投递（安全相关），后者属死代码口径问题（队列待确认第 7 条）。
**本轮未做任何改动。**

---

## 5. 验证汇总

| 项 | 结果 |
|---|---|
| 后端全量 pytest | **2456 passed / 0 failed**（exit=0） |
| 存储回归（正常时钟 / 200s / 3599s / 100000s） | 46 passed ×4 |
| 发布清单测试 | 31 passed |
| 模拟器写保持单元测试 | 8 passed |
| Modbus 协议 E2E | 10 passed |
| 决定性实验（写 → 等 1.5s → 回读） | 修复前 `[1,1,1,1]` → 修复后 `[111,222,333,444]` |
| 变异验证 | **7 组**全部按预期变红，均已还原 |

### 5.1 一条未定性的本地 flake（不影响 CI）

中间一次全量跑出现过 **1 条偶发失败**：
`tests/test_disaster_recovery.py::TestConfigRecovery::test_config_backup_restore`。

事实：
- 该用例**只用 stdlib**（`mkdir` / `write_text` / `shutil.copy2` / `unlink` / `read_text`），
  全程在 `tmp_path` 内，**不碰任何产品代码**
- 隔离跑 3 次 + 整文件跑 → 全过；随后一次全量跑 → 也过（即**非确定性**）
- 台账 `errors.log`（2026-09-17）已记录过同一机制：
  **本机 safe-delete 守卫会拦截单个 `unlink()`**，当时表现为
  `test_path_resolution.py` 在 `finally: target.unlink()` 处失败

判断：**极可能与本机注入的 safe-delete 守卫有关**。
关键结论 —— **该守卫是 WorkBuddy 环境注入的，GitHub Actions 上没有**，
因此这条 flake **不会影响 CI 绿灯**，属本机开发体验问题。
未做改动（改测试去迁就环境守卫是本末倒置）。

变异验证清单：
1. `_last_bloat_warn_at` 初值回退 `0.0` → 1 红
2. 在此基础上屏蔽初值断言（只看行为）→ 1 红
3. `_force_warn_window` 回退 `0.0` → 3 红
4. 清单 `frontend_skewed` 恒为 `False` → 2 红
5. 删掉 CI 布局候选路径 → 1 红
6. `hold_by_index` 不传给数据块 → 4 红
7. `update_slave` 去掉 `with hr.lock` → 1 红

---

## 6. 遗留 / 下一步

- [ ] 本轮提交推送后看后端 CI 是否**全绿**（round 170 起后端 CI 连续红了两天）
- [ ] `release2/smartscada-Setup-1.3.1033.exe` 是带缺陷的安装包（`after-pack.js` 抹掉了
      Element Plus 全部样式 357KB）→ 需用当前 HEAD 重新构建；`npm run electron:build`
      现在会先过 `verify:dist` 闸门
- [ ] 约 790 MB 构建垃圾待清（`release2/` 743MB、`dist.corrupt-20260921/`、
      `dist.bak.1789913446/`）—— 已 gitignore，删除会触发确认弹窗，**待主人拍板**
- [ ] 前端 `package-lock.json` 的 `version` 字段漂在 `1.3.1010`（待同步）
- [ ] **P2-4 待主人拍板**：968 行未接线的报警/广播实现 —— 做完迁移还是归档
- [ ] P2-6（God object 1385/1194/1104 行）、P2-5（40 处硬编码相对路径）未动
- [ ] CI 上 `dbstat` 不可用 → `size_to_data_ratio` 在 CI 上永远不被校验（已知覆盖缺口）

---

## 7. 方法论收获

1. **「本机绿 / CI 红」优先怀疑环境量而非逻辑量。**
   这次的环境量是 `time.monotonic()` 的**起点**（开机时刻），
   不是时区、不是文件系统、不是版本 —— 这类「随时间/机器变化的隐式输入」最难查，
   因为本地永远复现不出来。**能把环境量伪装掉的测试脚手架，比多写十条断言有用。**
2. **只加诊断、不做推测性改动，是对的。**
   round 170 拒绝猜测、只把全部输入写进断言消息，本轮直接拿到 `now=915` 一锤定音。
   反过来，如果当时按错误假设改了 `check_bloat` 的口径，就会在正确的代码上引入真 bug。
3. **诊断输出必须读「被测代码用的那个时钟/对象」。**
   `_bloat_diag` 第一版打印测试模块的 `monotonic`，显示 `now=88999` ——
   一个看起来完全正常、实际上毫无意义的数字，上一轮就是被它带偏的。
4. **「清单字段齐全」不等于「清单说的是真的」。**
   本轮第二个发现（前端产物路径用后端版本拼）和 round 170 的
   「旧世代包冒充当前版本」是同一类问题：**证据撒谎**。
   凡是「用 A 的版本号去推断 B 的产物路径」的地方，都必须回读 B 的真实版本。
5. **「偶发失败」不要放过，它往往指向一个确定性的真缺陷。**
   `test_write_multiple_readback` 单跑 15 遍全过、全量套件才偶发一次 ——
   最容易被当成"环境抖动"忽略。但顺着它读代码，挖出的是
   **写保持机制 100% 未生效**这个确定性缺陷（不是概率问题，是功能根本不存在），
   影响面直达产品演示路径。**概率性失败 + 代码里有一处"算了但没人用"的字段
   = 强信号。**
6. **「算出来的值没人读」是一种独立的缺陷类别，值得专门扫。**
   本轮三个发现里有两个是同一形状：
   - `spec['hold']` 算了，从没被读 → 写保持失效
   - 前端版本可以从 `package.json` 读，但从没被读 → 清单记下永不存在的路径
   两者都是「字段齐全、看起来正常、实际是错的」。
   扫这类缺陷的方法很便宜：**对每个"算出来存起来的配置/元数据字段，
   grep 它的读取点，为 0 就是嫌疑。**
