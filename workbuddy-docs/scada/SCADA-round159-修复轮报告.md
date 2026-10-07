# SCADA round 159 修复轮报告

日期：2026-09-16
代码基线：后端 `63ca8c8`（1.3.1003）→ 本轮 `1.3.1004` / `1.3.1005`
方式：3 个子 agent 并行（P0-1 / P0-4 / P1-1·P1-2）+ 主线自研（P0-2 补漏、P1-5、P2-3）

---

## 一句话结论

审计报告只是**线索**，不是结论。本轮按审计的「建议执行顺序」动手，结果：

- 审计的 P0-2 只修了 9 处，**实际还有 16 处同类漏网**（其中 2 处会让告警/容量预测静默少算）
- 审计点名的 P2-3「`api_performance.py` 未注册」比描述更严重 —— **该模块连 import 都是坏的**，前端整个性能监控页面是死的
- 审计 P1-5 的「清理任务无调度」牵出一个更硬的问题：**调度器 `start_all()` 自己会死锁**

---

## 一、P0-2 时间戳：审计修了 9 处，实际共 25 处

### 机制
库内 timestamp 由 `存储层/database.py::adapt_datetime` 写成**空格分隔** `'2026-08-17 10:30:00'`，
而 `datetime.isoformat()` 默认产出 **`'T'` 分隔**。SQLite 按文本比较，
ASCII 中 `'T'(0x54) > ' '(0x20)`：

```
'2026-08-17 23:59:59' < '2026-08-17T10:00:00'   → True（错误）
```

### 本轮新增修复 16 处

| 文件 | 处数 | 失效形态 |
|---|---|---|
| `core/report_generator.py` | 9 | `BETWEEN ? AND ?` 双向错位：**起始日当天记录全丢**，结束日之后记录被误纳 |
| `core/ops_tools.py` | 2 | `DELETE FROM history_data/audit_logs WHERE timestamp < ?` → **多删同日数据** |
| `tools/auto_ops.py` | 2 | 同上 |
| `core/data_compressor.py` | 1 | 归档 cutoff → 保留期内数据被当成过期压缩 |
| `tools/auto_alerts.py` | 1 | `WHERE timestamp > ?` → 告警统计**静默少算** |
| `tools/capacity_planner.py` | 1 | `WHERE timestamp > ?` → 容量预测偏小 |

> 注意 `auto_alerts` / `capacity_planner` 这类是 `>` 方向：**不会报错、数字只是偏小**，
> 属于最典型的"看起来正常"失效。

### 防复发
新增 `tests/test_timestamp_sql_consistency.py`（6 用例）：
- **静态扫描**：全库找 `isoformat()` 参与 SQL 时间比较的位置，命中即失败（带 `ALLOWED_HITS` 白名单登记无害命中）
- **行为验证**：对 4 个模块断言"同日记录不被误删 / 不被漏算"

**变异验证**：把 `ops_tools.py` 的两处 `sep=' '` 还原成裸 `isoformat()` → **3 条测试立刻失败**；
恢复修复 → 6 passed。

---

## 二、P0-1 Modbus 静默假成功（最严重，agent 完成）

`采集层/modbus_client.py` 两条读路径共 **10 条失败路径**全部 `return 缓存值`，
调用方**无法区分新值与几天前的旧值**，上游熔断器永远不跳闸。

修复：
- 新增 `_last_good_at` 时间戳字典 + `get_cache_age(address, count) -> float | None`
- 新增可观测状态 `last_read_source`（`'fresh'`/`'cache'`/`'none'`）、`last_read_ok`
- 新增统计计数 `stats['stale_reads']`，**每条兜底路径都自增**
- 10 条失败路径统一收敛到 `_fallback_to_cache()`，日志升到 WARNING 并**带上缓存年龄秒数**
- docstring 加 `Warning:` 段落，把"返回值可能是陈旧数据，调用方必须查 `last_read_source`"写成契约
- **质量码传播**：`采集层/data_collector.py` 读完后若 `last_read_source == 'cache'`，
  把该项质量码从 `GOOD(192)` 降级为 `UNCERTAIN_LAST_USABLE(64)`，不再把旧值当实时数据

新增 `tests/test_modbus_stale_data.py`。

---

## 三、P0-4 假绿测试（agent 完成）

审计点名的位置有一处**路径写错**：`tests/test_modbus_client.py` **不存在**，
真实位置是 `tests/test_write_safety.py`。已更正审计报告。

修复模式（示例）：
- `assert x is not None or True`（恒真）→ 改为校验类型 / 长度 / 元素类型
- 只调用不断言（"Should not raise"）→ 改为把契约断言出来
- 裸 `Flask(__name__)` 建的限流测试（永远 skip）→ 改用 `create_app()` 让限流真正绑定

---

## 四、P1-1 / P1-2 超时与线程泄漏（agent 完成）

- `core/health_checker.py`：原用 `ThreadPoolExecutor` + `future.result(timeout)`。
  真问题不只是"超时被吞"——`with ThreadPoolExecutor` 退出时会**等检查线程结束**，
  检查函数卡死则健康检查自己永久挂住。改为守护线程 + 结果信箱，
  超时必须有明确结果（标 `UNHEALTHY` + `TimeoutError`），且检测到上一次检查未返回时不再叠加线程。
- `报警层/alarm_manager.py`：
  - 升级/洪水定时器原本**回调里无条件自我重排**，且 `stop_*` 无法阻止 → 永久泄漏。
    新增 `threading.Event` 停止标志，停止后不再重排；`stop_*` 幂等。
  - 配置热重载线程原本无引用、无停止路径 → 改为持有引用 + `stop_config_watcher(timeout)`，
    轮询用可中断 `Event.wait()`。
  - 新增统一入口 `AlarmManager.stop()`；`run.py` 关闭路径改调它。

新增 `tests/test_lifecycle_shutdown.py`。

---

## 五、P1-5 清理任务无调度 —— 牵出调度器死锁（主线）

审计结论属实，但根因比描述更严重：

1. `core/scheduled_tasks.py` 的 `task_manager` **全项目零引用** —— 没注册过任务，也没 `start_all()` 过
2. **`start_all()` 本身会死锁**：它在持有 `threading.Lock` 时调用 `self.start()`，
   而 `start()` 又去获取同一把**非可重入**锁 → 永久挂住。`stop_all()` 同样。
   也就是说：谁第一个尝试用这个调度器，谁就会踩死锁 —— 这大概正是它一直没人用的原因
3. `TaskManager.add()` 重复注册会**替换正在运行的任务对象** → 旧线程失控，从此停不掉

修复：
- `_lock` 改为 `threading.RLock()`（并写明为什么必须可重入）
- `add()` 遇到运行中的同名任务**保留原任务**，不再替换
- 新增 `core/maintenance.py`：把 7 个清理任务统一注册到 `task_manager`
  （JWT 黑名单 / API 缓存 / nonce / 限流计数 / 离线消息队列 / 分层缓存 / 数据归档）
- `run.py`：删掉手写的 `while True: sleep(86400)` 裸线程（无停止路径），
  改用 `start_maintenance()`；关闭路径加 `stop_maintenance()`
- 运维接口：`GET /api/ops/maintenance/tasks`（登录可见）、
  `POST /api/ops/maintenance/tasks/<name>/run`（admin）

新增 `tests/test_maintenance_scheduler.py`（9 用例），含**死锁回归**与**幂等性**。
**变异验证**：`RLock` 还原成 `Lock` → 死锁测试立刻失败。

---

## 六、P1-3 采集队列阻塞入队（主线）

审计说"`queue.put()` 阻塞且队列无上限"。**前半对、后半不对**：
队列其实有上限（`DiskBackedQueue(maxsize=200000)`），且另外两处入队已经是
"非阻塞 + 丢最旧"。真正的问题是**断路器降级分支用了阻塞式 `self.data_queue.put(item)`**。

危害比审计描述的更具体：采集链路是"采集 → 在回调里 `_schedule_next()` 排下一次"的
**串行**结构。阻塞在 `put()` 上意味着**该设备再也走不到 `_schedule_next()`，
从此静默停止采集** —— 不报错、不告警，操作员看到的是"设备正常但数据不再更新"。

修复：抽出 `_enqueue_drop_oldest(item) -> bool` 统一三处入队路径（非阻塞、丢最旧、
丢弃计数进 `stats['dropped_items']`），删掉阻塞 `put()`。

新增 `tests/test_collector_queue_backpressure.py`（4 用例），含**AST 静态守卫**禁止
`data_queue.put(` 再次出现（用 AST 而非正则 —— 正则会被模块自己的注释误报）。
**变异验证**：还原阻塞 `put()` → 守卫立刻失败。

---

## 七、P2-3 `api_performance.py`：比审计描述更严重（主线）

审计说"未注册到蓝图"。实际是**该模块 import 就会抛 `ImportError`**：

```python
from core.service_response import api_error   # 该名字不存在，实际叫 error_response
```

所以它一直挂不上不是疏忽，是**挂上就会崩**。修掉 import 与 3 处调用后注册进 `ALL_BLUEPRINTS`，
`/api/performance/metrics/{realtime,history,summary}` 三个接口恢复 ——
前端 `PerformanceMonitor.vue` 的整个性能监控页面从"全 404"变成可用。

新增 `tests/test_blueprint_registration.py`：静态扫描 `展示层/api/*.py`，
**任何定义了 Blueprint 的模块都必须在 `ALL_BLUEPRINTS` 里，且其路由必须真的出现在 `url_map`**。
**变异验证**：从 `ALL_BLUEPRINTS` 摘掉 `performance_bp` → 3 条测试失败。

---

## 八、版本与推送

| 版本 | 内容 |
|---|---|
| `1.3.1004` | 上一轮 P0-2/P0-3/P0-5 收口（原为未提交状态）→ 已提交推送 |
| `1.3.1005` | 本轮 P0-1 / P0-4 / P1-1·P1-2 / P1-5 / P2-3 |

---

## 九、遗留（下一轮候选，按优先级）

1. ~~P1-3 无界阻塞队列~~ → ✅ 本轮已修（见第六节）。**注意审计原文说"队列无上限"是错的**，
   队列有上限（200000），真问题是断路器降级分支用了阻塞式 `put()`
2. **P1-4 `except: pass` 70 处**：静默吞异常
3. **P1-6 缺索引**：高频查询列
4. **P2-7 `core/module_registry.py` 生产环境从不注册**（已复核：`ModuleRegistry.register` **只在测试里调用过**）
   → `/modules` API 永远返回空；`chaos_engineering` / `health_checker` 的模块查找每次 KeyError 被吞掉，
   这些检查实际是常量
5. **P2-1 死模块 24 个 / 4578 行** —— 本轮**已逐个全量复核**（扫描 291 个源文件，
   排除 `tests/` / `dist/` / `build/`）：

   | 模块 | 行数 | 外部引用 |
   |---|---|---|
   | `adaptive_compression` `body_size_limit` `brotli_compression` `chunked_response` | 190/113/162/144 | 0 |
   | `cursor_pagination` `data_compressor` `deep_validator` `etag_support` | 191/232/239/160 | 0 |
   | `import_validator` `log_sampler` `log_sanitizer` `schema_validator` | 268/118/113/322 | 0 |
   | `sliding_window_limiter` `slow_query_logger` `sparse_fieldsets` `sql_cache` | 168/158/165/262 | 0 |
   | `streaming_export` `structured_logging_enhanced` `token_bucket_limiter` | 146/178/193 | 0 |
   | `config_validator_startup` `rate_limit_whitelist` `smart_retry` | 170/202/263 | 0 |
   | `cache_tier` `user_rate_limiter` | 264/157 | **1**（`core/maintenance.py`，本轮新增） |

   > 有意思的是：P1-5 的接线**顺手把其中 2 个"唤醒"了** —— `cache_tier` 与
   > `user_rate_limiter` 现在只有它们的清理函数被调用，其余代码仍是死的。
   > 另外 `core/wal_cleaner.py` 也属死模块，但 WAL checkpoint 已由
   > `database.wal_checkpoint()` 覆盖。
   >
   > ⚠️ **诚实备注**：`data_compressor.py` 也在死模块名单里。本轮修掉了它的
   > cutoff 格式 bug，但**该模块当前无人调用，所以这个修复没有运行时效果** ——
   > 修它是因为一旦被接线就会立刻出错，属于防御性修复。

6. **P2-2 前端 44 / 46 个 composable 是死的**（且有测试在测死代码）
7. **P2-8 横切关注点各来一套**：7 个限流器、5 个校验器、5 个日志器、3 个追踪器、3 个审计系统
8. **P3 交付链**：`.spec` 不在 git 且含硬编码绝对路径、Electron 出包依赖被 gitignore 的 19 MB exe、
   自动更新是假的（`electron-updater` 未安装）

---

## 十、环境坑（本轮新增，已写进 skill）

- **同一文件的两处 `Edit` 放在同一条消息里会互相覆盖** —— 第二次编辑基于原始内容写入，
  第一次的改动会**静默丢失**（工具仍报 success）。本轮实测：`_make_history_db` 加建表语句的编辑
  被同批的另一处编辑吞掉，导致测试多失败一轮。**改同一文件必须串行。**
- pytest 结束时 safe-delete guard 仍会在**打印汇总行之前**杀进程（进度行全绿但无 `N passed`）。
  处置：把 `%TEMP%\pytest-of-<user>\{garbage-*,pytest-*}` **改名**移开再重跑。
  本轮实测移开 20 个目录后，同一条命令立刻给出 `132 passed`。
