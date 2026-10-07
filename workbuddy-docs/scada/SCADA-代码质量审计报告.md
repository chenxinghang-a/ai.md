# SCADA 代码质量审计报告

审计日期：2026-09-16
审计方式：5 路并行 agent（只读）+ 主线逐条复核
代码基线：后端 `63ca8c8`（1.3.1003）/ 前端 `7425dea`（1.3.1003）

---

## 一句话结论

**这不是「代码写得丑」的问题，是「每轮只新增、从不删除、也从不验证旧的是否还在用」的累积问题。**

三个最硬的证据：

| 证据 | 数字 |
|---|---|
| `core/` 下零引用的死模块 | **24 个 / 4551 行**（已复核） |
| 前端 `src/composables/` 零引用的死代码 | **44 个 / 共 46 个**（已复核） |
| 后端 `except: pass` 静默吞异常 | **70 处** |

外加一个更严重的：**这套系统的失效模式不是「报错」，而是「静默假死」** —— 设备挂了系统显示一切正常。

---

## P0 · 立即修（正确性 / 数据丢失 / 安全）

### P0-1　Modbus 读失败静默返回旧缓存 ✅ **最严重**

`采集层/modbus_client.py` 的 `read_holding_registers` / `read_input_registers`，
在**全部 5 条失败路径**上都返回 `self._last_good_values.get(cache_key)`：

| 失败原因 | 行号 |
|---|---|
| 地址校验失败 | 320 |
| 设备未连接 | 323 |
| Modbus 错误响应 | 349 |
| 连接异常 | 375 |
| 其他异常 | 383 |

（`read_input_registers` 同构，407 / 410 / 430 / 454 / 460）

**后果**：
- 调用方**无法区分「刚读到的新值」和「几天前的旧值」**，操作员看到的是看起来正常的数据
- 上游熔断器因为「每次都算成功」**永远不跳闸** —— 设备真挂了系统显示一切正常

**修复方向**：失败必须可观测。保留缓存但加显式信号（`last_read_ok` / `last_good_at`），
或失败返回 `None` 并把缓存值通过独立 API 暴露。数据采集侧应据此把质量标记为
`STALE`（项目已有 `DataQualityAssessor` 的质量码机制可复用）。

---

### P0-2　时间戳格式不一致 → 清理多删数据 ✅ **已修**

库内 timestamp 由 sqlite3 适配器写成**空格分隔** `'2026-08-17 10:30:00'`，
但清理/归档/范围查询用 `datetime.isoformat()` 生成 **'T' 分隔** 的 cutoff。
SQLite 按文本比较，ASCII 中 `'T'`(0x54) > `' '`(0x20)，
于是 `'2026-08-17 23:59:59' < '2026-08-17T10:00:00'` 成立 ——
**同一天里比 cutoff 更晚的记录也被判为「过旧」删掉**。

已修 9 处：`data_lifecycle.py:155/164`、`data_archive.py:121/494/498`、
`data_consistency.py:212`、`auth.py:258/428/586`。

其中 `auth.py:428` 的黑名单清理尤其值得注意 —— **每次多删近一天的令牌黑名单，等于削弱令牌撤销时效**。

回归测试 `tests/test_retention_timestamp.py`（3 个用例），
**已验证有效**：还原 bug 时以准确错误信息失败，修复后通过。

> ⚠️ **2026-09-16 补记：这 9 处只是冰山一角。** 后续用静态扫描全库复查，
> 又找出 **16 处**同类漏网（`ops_tools.py` 2 处、`report_generator.py` 9 处、
> `data_compressor.py` 1 处、`auto_alerts.py` 1 处、`auto_ops.py` 2 处、
> `capacity_planner.py` 1 处）。其中 `report_generator.py` 是 `BETWEEN ? AND ?`
> 双向错位（起始日当天记录全丢、结束日之后记录被误纳），`auto_alerts.py` /
> `capacity_planner.py` 是 `WHERE timestamp > ?` 静默漏算 —— 告警统计和容量
> 预测"看起来正常但数字偏小"。修复与验证见文末「round 159 修复轮」。

---

### P0-3　`data_archive.py:503-513` 聚合条件失效

`params` 构造后未传给 `execute()`，导致 WHERE 条件形同虚设，聚合结果**静默错误**。

---

### P0-4　假绿测试

| 位置 | 问题 |
|---|---|
| `test_security_penetration.py::test_rate_limit_login` | 用裸 Flask app（不经过 `create_app`），限流从未绑定 → **永远 skip** |
| `test_write_safety.py::test_negative_address_rejected` | 无断言，只调用了函数 |
| 多处 | `assert x or True`、断言恒真、只断言 `is not None` |
| 多处 | 把 **404 当作通过**（接口不存在也算过） |

> 📌 **更正**：本表原写 `test_modbus_client.py::test_negative_address_rejected`，
> 但 `tests/test_modbus_client.py` **这个文件不存在**。真实位置是
> `tests/test_write_safety.py`。审计报告中引用的文件路径请以实际为准。

**已修 1 处**：`test_auth_enhanced.py::test_force_change_password` 原先把「不带旧密码就能改密」
这个漏洞当成预期行为，已改为安全断言并补回归测试。

---

### P0-5　`pyproject.toml` 的 `testpaths` 指向错误目录

`testpaths = ["测试"]`（中文目录，不存在）→ 直接跑 `pytest` 只收集到 **13 个测试**，
而不是 1881 个。**任何人执行裸 `pytest` 都会得到「测试很少但全绿」的假象。**

---

## P1 · 短期（健壮性 / 可观测性）

### P1-1　超时配置了但不生效

- `core/health_checker.py:58-60`：`executor.wait(timeout=...)` 的超时被吞，
  健康检查自己可能挂死
- 多处外部调用（Modbus / OPCUA / MQTT / HTTP）缺 `timeout` 参数 → 可能永久挂起

### P1-2　线程与定时器泄漏

| 位置 | 问题 |
|---|---|
| `采集层/data_collector.py:253/341` | 线程创建后无 join / 无停止路径 |
| `报警层/alarm_manager.py:135` | 同上 |
| `报警层/alarm_manager.py:360-366` | 定时器**会自我复活**且无 `cancel()` → 永久泄漏 |

### P1-3　无界阻塞队列

`采集层/data_collector.py:128`：`queue.put()` 阻塞且队列无上限 →
消费端卡住时采集线程**永久挂起**（且无告警）。

### P1-4　`except: pass` 共 70 处

静默吞异常，故障被完全掩盖。审计已列出全部位置。

### P1-5　清理任务无调度

`jwt_blacklist` / `operation_logs` 有清理函数但**没有任何调度器调用** → 无界增长。
`core/wal_cleaner.py` 同理。

### P1-6　缺索引

高频查询列缺索引（审计已列具体表/列）。

---

## P2 · 中期（架构 / 死代码）

### P2-1　24 个死模块（4551 行）—— 已复核

```
adaptive_compression 189  body_size_limit 112  brotli_compression 161
cache_tier 263  chunked_response 143  cursor_pagination 190
data_compressor 228  deep_validator 238  etag_support 159
import_validator 267  log_sampler 117  log_sanitizer 112
schema_validator 321  sliding_window_limiter 167  slow_query_logger 157
sparse_fieldsets 164  sql_cache 261  streaming_export 145
structured_logging_enhanced 177  token_bucket_limiter 192  user_rate_limiter 156
config_validator_startup 169  rate_limit_whitelist 201  smart_retry 262
```

注意 `smart_retry`（262 行）是死的，而另外 **4 处手写了退避重试**。

### P2-2　前端 44 / 46 个 composable 是死的 —— 已复核

只有 `useErrorLogger` 真正被应用引用；`useSystemTheme` 仅被另外两个死 composable 引用。
**且有测试在测死代码**（`useCache.test.ts`、`useDebounce.test.ts`）。

### P2-3　`api_performance.py` 未注册到蓝图

243 行、不在 `ALL_BLUEPRINTS` → **前端 `PerformanceMonitor.vue` 调的接口根本不存在**。

### P2-4　同一能力三套并行实现

`AlarmOutput` ×3、`Broadcast` ×3、simulated client ×2；
`decode_float32/64` 在 3 处逐字重复。

### P2-5　配置层

- **8 / 14 个配置类零引用**
- **40 处硬编码相对路径**（如 `'配置/alarms.yaml'`）而非用 `core/paths.py`

### P2-6　God object

1385 行 / 1194 行 / 1104 行的文件；单函数 341 行。

### P2-7　`core/module_registry.py`（535 行）生产环境从不注册

但被 `chaos_engineering` / `health_checker` 调用 → 每次 `KeyError` 被吞掉 →
**这些检查实际是常量**；`/modules` API **永远返回空**。

### P2-8　横切关注点各来一套

7 个限流器、5 个校验器、5 个日志器、3 个追踪器、3 个审计系统。

### P2-9　错误处理两种风格并存

装饰器模式 vs `api_industry40.py:88-560` 里 20+ 处复制粘贴的 try/except。

---

## P3 · 工程化与交付链

| # | 问题 | 影响 |
|---|---|---|
| P3-1 | 打包配置（`.spec`）不在 git，且含**硬编码绝对路径** | 换台机器就废 |
| P3-2 | Electron 安装包依赖被 gitignore 的 **19 MB exe** | 别人 clone 后无法出包 |
| P3-3 | 自动更新是**假的**（`electron-updater` 未安装） | 用户永远收不到更新 |
| P3-4 | **5 处版本号不一致** | 无法追溯 |
| P3-5 | Release 元数据与实际产物不符 | 交付不可信 |
| P3-6 | CI 测试范围与本地不一致 | 「CI 通过」不代表真通过 |

---

## 建议执行顺序

1. **P0-1 Modbus 静默假成功**（安全关键，工控系统不能显示假数据）
2. **P0-5 + P0-4 测试可信度**（不然后面所有验证都不可信）
3. **P1-1~P1-3 超时/线程/队列**（长期运行必炸）
4. **P2-1 + P2-2 死代码清理**（一次性删掉约 4500 行 + 44 个文件，立刻降复杂度）
5. **P0-3 + P1-4 静默错误**（聚合错误 + 70 处吞异常）
6. **P2-3~P2-9 架构收敛**（需要设计决策，分批做）
7. **P3 交付链**（需要重新验证打包）

---

## 本轮已完成

- ✅ P0-2 时间戳格式（9 处 + 回归测试，已验证有效）
- ✅ 令牌类型校验 / 强制改密闸门 / 静默改密漏洞（`63ca8c8`）
- ✅ 13 处越权修复，保护率 150/167 → 157/167
- ✅ 登录限流从失效变可用（实测 429）
- ✅ 前端运行时依赖漏洞清零（npm audit 32 → 17）
- ✅ 新增 `tests/test_api_authorization.py` 静态鉴权矩阵回归测试
