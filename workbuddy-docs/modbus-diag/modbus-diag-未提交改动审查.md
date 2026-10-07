# modbus-diag 未提交改动审查报告

- 仓库：`C:\Users\cxx\modbus-diag`（ESP-IDF 项目，目标 `esp32s3`）
- 基线提交：`a2ce79f`（2026-05-27 23:28，"feat: ESP32-S3 Modbus diagnostic instrument - full build pass"）
- 审查时间：2026-09-15
- 本地 IDF 版本：**ESP-IDF v5.4.0**（`C:/Users/cxx/esp-idf`，由 `build/compile_commands.json` 中的 `-IC:/Users/cxx/esp-idf/components/...` 与 `components/esp_common/include/esp_idf_version.h` 确认）
- 远端状态：`origin/main`，`git rev-list --left-right --count origin/main...HEAD` = `0 0`，无 tag
- 审查方式：只读（`git status` / `git diff` / `git show` / 读源文件），未做任何 `add` / `commit` / `push`，未修改任何代码

> **与任务描述的一处出入**：任务描述称"12 个已修改 + 1 个已删除"。实际 `git diff --stat` 为 **14 个已修改 + 1 个已删除 = 15 个文件**（多出 `main/main.c` 与 `sdkconfig.defaults`）。本报告按实际的 15 个文件逐一审查。

---

## 一句话结论

**不能直接提交。** `components/waveform/adc_sampler.c` 存在 3 处与 ESP-IDF v5.4 实际 API 不符的符号（函数名 2 处、结构体字段名 1 处），**编译必然失败**；且工作区自 2026-05-29 改动后**从未编译过**（`build/` 下最新产物为 2026-05-27 23:15，早于全部源码修改时间）。另有 1 处 P1 逻辑缺陷（`log_storage.c` SPIFFS 分区名不匹配，会永久禁用日志存储）和 2 处 P2 缺陷（UART 占用后未释放、buffer 竞态）必须先修。其余 12 个文件的改动质量良好，修完阻断项后可按下方 6 条 commit 分组提交。

---

## 逐文件改动表

| 文件 | 性质 | 关键改动 | 风险等级 |
|---|---|---|---|
| `components/common_config/app_config.h` | 新功能（基础设施） | 新增 `uart_mode_t` 枚举（`UART_MODE_IDLE` / `UART_MODE_MODBUS` / `UART_MODE_CAPTURE`），供 Modbus master 与 packet capture 共享 | 低 |
| `components/diag_report/health_metrics.c` | 并发加固 | 新增 `static SemaphoreHandle_t s_mutex`；`health_metrics_init` / `health_metrics_update` / `health_metrics_get_report` 加锁 | 低 |
| `components/display/gui_manager.c` | bug 修复 | 页面栈（深度 8）满时不再静默丢弃 push，改为左移丢最旧条目后再压栈。逻辑与 `s_page_stack[8]` 边界一致，**无越界** | 低 |
| `components/modbus_core/modbus_master.h` | 新功能 | 引入 `#include "app_config.h"`，声明 `modbus_master_get_uart_mode()` / `modbus_master_set_uart_mode()` | 低 |
| `components/modbus_core/modbus_master.c` | 新功能 + 半成品 | 新增 `static volatile uart_mode_t s_uart_mode`；`modbus_master_send_recv()` 在 `UART_MODE_CAPTURE` 时拒绝执行并返回 `MODBUS_ERR_IO`，执行期间置 `UART_MODE_MODBUS`，各退出路径恢复 `UART_MODE_IDLE`；`modbus_master_process()` 改为占位实现，`vTaskDelay` 10ms → 100ms | 中 |
| `components/modbus_core/modbus_rtu.c` | bug 修复 | `modbus_rtu_parse_response()` 各 function-code 分支补 `frame_len` 下界校验（读保持寄存器 `3+data_len+2`、写单个/多个 `>=8`、诊断 `>=6`、default `>=4`） | 低 |
| `components/modbus_core/modbus_tcp.c` | 并发加固 | 新增 `s_sock_mutex`（`xSemaphoreCreateMutex`），`modbus_tcp_connect` / `modbus_tcp_disconnect` / `modbus_tcp_send_recv` 全路径加锁 | 中 |
| `components/protocol_analyzer/packet_capture.c` | 新功能 | `packet_capture_start()` 先查 UART 是否被 Modbus 占用，再置 `UART_MODE_CAPTURE`；`packet_capture_stop()` 恢复 `UART_MODE_IDLE` | 中 |
| `components/protocol_analyzer/traffic_stats.c` | 并发加固 | 新增 `s_mutex`；`traffic_stats_add_frame` / `traffic_stats_get` / `traffic_stats_tick` 加锁；注释由 "Running average" 更正为 "Exponential moving average (alpha=0.125)" | 低 |
| `components/storage/log_storage.c` | bug 修复（**本身有缺陷**） | 新增 `spiffs_is_mounted()`，在 `log_storage_init` / `log_storage_append` 前置校验。**但校验方式错误，见 P1-1** | **高** |
| `components/waveform/adc_sampler.c` | 重写（**未完成**） | `adc_oneshot` 轮询 → `adc_continuous` DMA + `IRAM_ATTR` ISR 回调；`s_buf_mutex` 新增但未使用。**3 处编译错误，见 P0** | **阻断** |
| `components/wifi_service/web_server.c` | bug 修复 | `report_handler` 由一次性 `fread` + `httpd_resp_send` 改为 `httpd_resp_send_chunk` 循环分块发送，`buf` 1024 → 512；`fclose` 移到循环后；`httpd_resp_set_type` 仍在发送前调用（顺序正确） | 低 |
| `main/app_event.h` | 删除（去重） | 与 `components/common_config/app_event.h` **逐字节完全一致**（已用 `diff` 验证），删除后所有 include 均可解析 | 低 |
| `main/main.c` | 代码清理 / 行为变更 | `modbus_task` 优先级由 `TASK_PRIO_MODBUS`(=6) 改为硬编码 `1`，注释标明为占位 | 中 |
| `sdkconfig.defaults` | 配置（配套改动） | 新增 `CONFIG_ADC_CONTINUOUS_ISR_IRAM_SAFE=y` 与 `CONFIG_ADC_CONTINUOUS_CTRL_FUNC_IN_IRAM=y`，与 `adc_sampler.c` 的 `IRAM_ATTR` 回调配套（方向正确） | 低 |

### `main/app_event.h` 删除的安全性验证（任务第 3 点）

**结论：删除是安全的。**

1. 内容一致性：`diff <(git show HEAD:main/app_event.h) components/common_config/app_event.h` → 无差异，两文件完全相同。
2. 全仓库仅剩一份 `app_event.h`：`find . -name "app_event*"` 仅返回 `./components/common_config/app_event.h`。
3. include 路径可解析：所有 `#include "app_event.h"` 的调用方所在组件均已在 `CMakeLists.txt` 的 `REQUIRES` 中声明 `common_config`，而 `components/common_config/CMakeLists.txt` 为 `idf_component_register(INCLUDE_DIRS ".")`：
   - `main/main.c:15` → `main/CMakeLists.txt` REQUIRES 含 `common_config` ✔
   - `components/display/gui_manager.c:4` → `display/CMakeLists.txt` REQUIRES 含 `common_config` ✔
   - `components/display/pages/page_home.c:5`、`pages/page_rtu_scan.c:5` → 同属 display 组件 ✔
   - `components/input/key_scan.c:3` → `input/CMakeLists.txt` REQUIRES 含 `common_config` ✔
4. `app_event_*` 的实现仍完整保留在 `main/main.c`（`app_event_register` / `app_event_unregister` / `app_event_post` / `app_event_post_from_isr` / `app_event_process`），删除的只是重复的**声明**头文件，不涉及实现。

---

## 风险清单（按严重度排序）

### P0 — 阻断提交（编译失败）

> 判据：以下符号在 ESP-IDF v5.4.0 的 `components/esp_adc/` 下经 `grep` 全量检索**确认不存在**（`grep -rn` 退出码 1，无任何匹配），而实际 API 名已由 `components/esp_adc/include/esp_adc/adc_continuous.h` 与 `components/hal/include/hal/adc_types.h` 逐一核对。

**P0-1 `components/waveform/adc_sampler.c:53` — 函数名不存在**
```c
esp_err_t ret = adc_continuous_new_unit(&handle_cfg, &s_adc_handle);
```
IDF 5.4 实际签名为 `adc_continuous_new_handle(const adc_continuous_handle_cfg_t *hdl_config, adc_continuous_handle_t *ret_handle)`（`adc_continuous.h:115`）。
**建议**：改为 `adc_continuous_new_handle(&handle_cfg, &s_adc_handle);`

**P0-2 `components/waveform/adc_sampler.c:77` — 函数名不存在**
```c
adc_continuous_del_unit(s_adc_handle);
```
IDF 5.4 实际签名为 `adc_continuous_deinit(adc_continuous_handle_t handle)`（`adc_continuous.h:198`）。注意 `adc_continuous.h` 中**不存在**任何 `*_del_unit` / `*_del_handle` 符号。
**建议**：改为 `adc_continuous_deinit(s_adc_handle);`

**P0-3 `components/waveform/adc_sampler.c:25` — 结构体字段名不存在**
```c
uint32_t len = edata->conv_frame_size;
```
`adc_continuous_evt_data_t` 的字段为 `conv_frame_buffer` 与 **`size`**（`adc_continuous.h:76-77`），`conv_frame_size` 是 `adc_continuous_handle_cfg_t` 的字段（第 54 行），不是事件数据的字段。
**建议**：改为 `uint32_t len = edata->size;`

**P0-4 工作区从未编译验证**
- 全部被改文件的 mtime 为 2026-05-29 20:53–20:58；
- `build/esp-idf/waveform/CMakeFiles/__idf_waveform.dir/adc_sampler.c.obj` 的 mtime 为 **2026-05-27 23:15**；
- `find build -name "*.obj" -newermt "2026-05-28"` 返回**空**，即 05-28 之后没有任何编译产物。

**建议**：修复 P0-1~P0-3 后，必须在本机执行一次完整 `idf.py build` 并通过，再谈提交。当前没有任何证据表明这 15 个文件能编译。

---

### P1 — 必须先修的逻辑缺陷

**P1-1 `components/storage/log_storage.c:13` — SPIFFS 分区名不匹配，日志存储被永久禁用**

```c
static bool spiffs_is_mounted(void)
{
    size_t total = 0, used = 0;
    return esp_spiffs_info(NULL, &total, &used) == ESP_OK;
}
```

事实链（均已核对 IDF 源码 `components/spiffs/esp_spiffs.c`）：
1. `main/main.c:96-105` 的 `spiffs_init()` 使用 `.partition_label = "storage"`；`partitions.csv` 中该分区为 `storage, data, spiffs, 0x1F0000, 0x10000`。
2. `esp_vfs_spiffs_register()` 内部（`esp_spiffs.c:221`）设置 `efs->by_label = conf->partition_label != NULL;`。传入 `"storage"` → `by_label = true`。
3. `esp_spiffs_info()`（`esp_spiffs.c:302-310`）调用 `esp_spiffs_by_label(partition_label, &index)`。
4. `esp_spiffs_by_label()`（`esp_spiffs.c:105-122`）对 `label == NULL` 只匹配 `!p->by_label` 的挂载项：
   ```c
   if (!label && !p->by_label) { *index = i; return ESP_OK; }
   ```
   而本项目的挂载项 `by_label == true`，因此 `NULL` 匹配不到，函数返回 `ESP_ERR_NOT_FOUND`。
5. 于是 `esp_spiffs_info(NULL, ...)` 恒返回 `ESP_ERR_INVALID_STATE` → `spiffs_is_mounted()` 恒为 `false` → `log_storage_init()` 恒返回 `ESP_ERR_INVALID_STATE`，`log_storage_append()` 恒在写文件前 return。

**影响**：日志存储功能被**完全禁用**（且 `log_storage_init` 的失败在 `main.c` 中未被调用、也未被检查）。
**建议**：改用与注册时一致的分区名，即 `return esp_spiffs_mounted("storage");`（`esp_spiffs.h:62` 声明 `bool esp_spiffs_mounted(const char* partition_label);`），或 `esp_spiffs_info("storage", &total, &used) == ESP_OK`。
**当前缓解**：`log_storage_init` / `log_storage_append` / `log_storage_read` / `log_storage_clear` 在全仓库**无任何调用点**（仅 `.c` 定义与 `.h` 声明），故暂无运行时影响；但一旦接线即失效，属于"埋雷"。

---

### P2 — 建议提交前一并修复

**P2-1 `components/protocol_analyzer/packet_capture.c:76-86` — 占用 UART 后创建任务失败未释放**

```c
modbus_master_set_uart_mode(UART_MODE_CAPTURE);   /* :76 */
packet_capture_clear();
s_running = true;
BaseType_t ret = xTaskCreatePinnedToCore(capture_task, "capture", ...);  /* :81 */
if (ret != pdPASS) {
    s_running = false;
    return ESP_FAIL;                              /* :85 —— 未恢复 UART 模式 */
}
```
一旦任务创建失败（内存不足等），`s_uart_mode` 永久停留在 `UART_MODE_CAPTURE`，此后 `modbus_master_send_recv()` 会在 `modbus_master.c:121` 恒返回 `MODBUS_ERR_IO`，Modbus 功能被永久拒绝且无自愈路径。
**建议**：在 `return ESP_FAIL;` 前补 `modbus_master_set_uart_mode(UART_MODE_IDLE);`。

**P2-2 `components/modbus_core/modbus_master.c:121-125` + `components/protocol_analyzer/packet_capture.c:70-76` — UART 占用判定为 check-then-set，非原子**

```c
/* modbus_master.c */
if (s_uart_mode == UART_MODE_CAPTURE) { ... return MODBUS_ERR_IO; }
s_uart_mode = UART_MODE_MODBUS;
```
```c
/* packet_capture.c */
if (modbus_master_get_uart_mode() == UART_MODE_MODBUS) { ... return ESP_ERR_INVALID_STATE; }
modbus_master_set_uart_mode(UART_MODE_CAPTURE);
```
`volatile` 只保证可见性、不提供互斥。两个任务可同时通过检查后各自写入，导致 Modbus 事务与 capture 同时操作同一 UART。`modbus_master_send_recv` 由 UI 任务（`page_rtu_scan` 等）调用，`packet_capture_start` 亦由 UI 任务调用，当前实际并发面较小，但该保护本身不成立。
**建议**：改用 `xSemaphoreCreateMutex` 或 `atomic_compare_exchange` 实现原子的 "尝试获取 UART 所有权"。

**P2-3 `components/waveform/adc_sampler.c:16,44-46,30` — `s_buf_mutex` 创建后从未使用，采样缓冲无同步（半成品）**

```c
static SemaphoreHandle_t s_buf_mutex = NULL;   /* :16 */
...
if (!s_buf_mutex) { s_buf_mutex = xSemaphoreCreateMutex(); }  /* :44-46 —— 全文件再无 take/give */
```
而 ISR 在 `:30` 无保护地写 `s_sample_buf[s_write_idx]`，`adc_sampler_get_buffer()`（`:127`）直接把 `s_sample_buf` 指针交给 UI 任务，`components/display/pages/page_waveform.c:37` 立即对其做 `signal_filter_sma(raw, filtered, depth, 3)`。ISR 与任务并发读写同一缓冲 → **撕裂读**（一帧内混入两个时刻的样本）。
**建议**：这是典型的"加了一半"。要么补全双缓冲/乒乓切换（ISR 写备用缓冲，任务原子取指针），要么明确注释说明接受撕裂并删除未使用的 `s_buf_mutex`。当前状态不应提交。

**P2-4 `main/main.c:169` — Modbus 任务优先级 6 → 1，`TASK_PRIO_MODBUS` 变为死代码**

```c
xTaskCreatePinnedToCore(modbus_task, "modbus_task", TASK_STACK_MODBUS, NULL,
                        1, NULL, 0);  /* Low priority: placeholder for future request queue */
```
- 优先级由 `TASK_PRIO_MODBUS`(=6，`app_config.h:57`) 降为硬编码 `1`；
- `grep -rn "TASK_PRIO_MODBUS"` 现仅剩 `app_config.h:57` 的定义处，**该宏已无任何引用**。
- 功能影响可忽略（`modbus_master_process()` 现在只做 `vTaskDelay(100)`），但属于行为变更，且硬编码魔数绕过了集中配置。
**建议**：若确实要降优先级，应在 `app_config.h` 中定义 `TASK_PRIO_MODBUS_IDLE 1` 并引用，而不是留一个死宏 + 魔数。同时确认这是有意为之（提交信息中说明）。

---

### P3 — 低风险 / 可选优化

| 编号 | 位置 | 问题 | 建议 |
|---|---|---|---|
| P3-1 | `adc_sampler.c:27` | 循环边界 `for (uint32_t i = 0; i + 1 < len; i += SOC_ADC_DIGI_RESULT_BYTES)`，当 `len` 不是 `SOC_ADC_DIGI_RESULT_BYTES`(4) 的整数倍时会越界读 `p[i..i+3]` | 改为 `i + SOC_ADC_DIGI_RESULT_BYTES <= len` |
| P3-2 | `adc_sampler.c:50` | `.max_store_buf_size = WAVE_SAMPLE_DEPTH * 2 * 2` 注释为 `/* double buffer */`，但 `WAVE_SAMPLE_DEPTH * 2 * 2` = `WAVE_SAMPLE_DEPTH * 4`，恰好等于下一行 `.conv_frame_size = WAVE_SAMPLE_DEPTH * SOC_ADC_DIGI_RESULT_BYTES`（`SOC_ADC_DIGI_RESULT_BYTES` 在 esp32s3 上为 4）。即两者相等，并未实现"双缓冲" | 若需双缓冲应显式写 `WAVE_SAMPLE_DEPTH * SOC_ADC_DIGI_RESULT_BYTES * 2`；否则修正注释 |
| P3-3 | `modbus_tcp.c` `modbus_tcp_is_connected()` | 读取 `s_sock` 未加 `s_sock_mutex`，与 `disconnect` 存在竞态；另 `send_recv` 持锁跨阻塞 `recv()`（`SO_RCVTIMEO` 为 2s，见 `modbus_tcp.c:57`），最坏持锁 2s，期间 `disconnect` 会阻塞 | 至少让 `is_connected` 读一次局部快照 |
| P3-4 | `adc_sampler.c:15` | `static int s_write_idx` 非 `volatile`，却被 ISR（`:31`）与任务（`:95` 置 0）共享；`s_running` 已正确加 `volatile`，此处不一致 | 加 `volatile` |
| P3-5 | `adc_sampler.c:102` | `adc_continuous_register_event_callbacks(...)` 返回值未检查，注册失败将导致采样缓冲永不更新却仍返回 ESP_OK | 检查返回值并在失败时回滚 |
| P3-6 | `traffic_stats.c:64-68` | `traffic_stats_get()` 在 `!s_mutex` 时直接 `return`，`*out` 保持调用方未初始化状态（对比 `health_metrics_get_report` 同样行为） | 至少在早退前 `memset(out, 0, sizeof(*out))` |
| P3-7 | `modbus_tcp.c:29`、`health_metrics.c:19-22` | `xSemaphoreCreateMutex()` 返回 NULL（内存不足）时未处理：`modbus_tcp_connect` 会执行 `xSemaphoreTake(NULL, portMAX_DELAY)`，触发 FreeRTOS 断言 | 创建失败时返回 `ESP_ERR_NO_MEM` |

---

## 提交分组方案

共 **6 条** commit。前提：**P0-1~P0-4 必须先行修复并编译通过**，P1-1 建议同批修掉。

> 说明：`components/modbus_core/modbus_master.c` 的 diff 同时包含"UART 模式 API"与"`modbus_master_process()` 占位改造"两件事，`main/main.c` 的优先级改动与后者同主题，故一并归入 Commit 2，避免使用 `git add -p` 做行级拆分。

### Commit 1 — 删除重复头文件

```
refactor: remove duplicate main/app_event.h

main/app_event.h was byte-identical to components/common_config/app_event.h.
Every includer (main, display, input) already lists common_config in REQUIRES,
so "app_event.h" still resolves through the component include path. The
app_event_* implementations in main.c are untouched.

Files:
  main/app_event.h (deleted)
```

### Commit 2 — UART 所有权仲裁 + Modbus 任务占位

```
feat(modbus): arbitrate UART ownership between Modbus master and packet capture

Add uart_mode_t (IDLE/MODBUS/CAPTURE) to app_config.h and expose
modbus_master_get_uart_mode()/modbus_master_set_uart_mode(). A Modbus
transaction now refuses to start while capture owns the UART and marks the
UART busy for its duration, restoring IDLE on every exit path.
packet_capture_start()/stop() acquire and release it symmetrically.

Also park the Modbus task: modbus_master_process() is now an explicit
placeholder (vTaskDelay 10ms -> 100ms) and main.c starts it at priority 1
instead of TASK_PRIO_MODBUS.

Files:
  components/common_config/app_config.h
  components/modbus_core/modbus_master.h
  components/modbus_core/modbus_master.c
  components/protocol_analyzer/packet_capture.c
  main/main.c
```

### Commit 3 — 共享状态加锁

```
fix(concurrency): serialize shared state in Modbus TCP, health metrics and traffic stats

modbus_tcp_connect()/disconnect()/send_recv() now share s_sock_mutex so the
socket handle cannot be closed underneath an in-flight transaction.
health_metrics and traffic_stats guard their accumulators with a mutex so the
UI task cannot observe a half-updated report. Also correct the traffic_stats
average comment to describe the exponential moving average it actually is.

Files:
  components/modbus_core/modbus_tcp.c
  components/diag_report/health_metrics.c
  components/protocol_analyzer/traffic_stats.c
```

### Commit 4 — 边界与健壮性修复

```
fix: add bounds checks for Modbus RTU frames and harden page stack and report serving

- modbus_rtu_parse_response(): validate frame_len before reading the payload
  in every function-code branch (read regs, write single/multi, diagnostics,
  default)
- gui_manager_goto(): drop the oldest entry instead of silently skipping the
  push when the 8-deep page stack is full
- web_server report_handler(): stream the report with chunked transfer
  instead of a single 1 KB read

Files:
  components/modbus_core/modbus_rtu.c
  components/display/gui_manager.c
  components/wifi_service/web_server.c
```

### Commit 5 — SPIFFS 挂载校验（**必须先修 P1-1**）

```
fix(storage): validate SPIFFS mount before log I/O

log_storage_init() and log_storage_append() now fail fast when SPIFFS is not
mounted instead of returning success and silently dropping writes.

Files:
  components/storage/log_storage.c
```

> 若按现状提交，此 commit 会引入"日志存储永久失效"的缺陷（见 P1-1），**必须先把 `esp_spiffs_info(NULL, ...)` 改为 `esp_spiffs_mounted("storage")`** 再提交。

### Commit 6 — ADC 采样重写（**必须先修 P0-1~P0-3**）

```
feat(waveform): migrate ADC sampler from oneshot polling to continuous DMA

Replace the 1 ms oneshot polling task with adc_continuous DMA mode and an
IRAM conversion-done callback that fills the sample buffer, which is what the
100 KSPS WAVE_SAMPLE_RATE actually requires. Enable
CONFIG_ADC_CONTINUOUS_ISR_IRAM_SAFE and CONFIG_ADC_CONTINUOUS_CTRL_FUNC_IN_IRAM
so the callback can run from IRAM.

Files:
  components/waveform/adc_sampler.c
  sdkconfig.defaults
```

> 当前 `adc_sampler.c` **无法编译**（P0-1/P0-2/P0-3），此 commit 必须等修复 + 完整 `idf.py build` 通过后再提交。若时间紧张，可先提交 Commit 1–5，把 ADC 重写留到单独一个分支。

### 是否应该合成单条 commit？

**不建议。** 理由：
1. 这批改动跨 4 个语义域（UART 仲裁 / 并发加固 / 边界校验 / ADC 重写），合成单条会使 `git bisect` 无法定位问题——尤其是 ADC 重写一旦引入采样异常，与其余"加锁/加边界检查"的改动混在一起将很难二分。
2. Commit 2 引入的 `uart_mode_t` 是 Commit 6 之外唯一的新增公共 API，单独成条便于回溯。
3. Commit 1 是纯删除、零行为变更，单独成条风险最低，也最容易被 review 通过。
4. 唯一"同批补完"的合理合并是把 Commit 5 并入 Commit 3（都属于"并发/健壮性加固"），但 Commit 5 当前含 P1-1 缺陷，独立成条反而更容易在 review 时被拦下。

---

## 未决问题

1. **`adc_sampler.c` 是否曾在本机编译过？** 从时间戳看没有：全部改动文件 mtime 为 2026-05-29 20:53–20:58，而 `build/` 下最新 `.obj` 为 2026-05-27 23:15，`find build -newermt "2026-05-28"` 为空。3 处 API 名错误（P0-1~P0-3）也印证了"写完没编译"。请确认当初是否在别的机器/目录试过。
2. **`health_metrics_update()` 与 `traffic_stats_tick()` 全仓库无调用点。** 前者只在 `health_metrics.c:33` 定义、`health_metrics.h:29` 声明；后者只在 `traffic_stats.c:75` 定义、`traffic_stats.h:23` 声明。也就是说本次为它们新加的互斥锁目前是空转，且诊断页的响应时间统计、抓包页的 `frames_per_sec` 速率都拿不到数据。这是**既有问题**（非本次 diff 引入），但会影响对本次改动价值的判断——是否本轮就该把调用点接上？
3. **`log_storage_init` / `log_storage_append` / `log_storage_read` / `log_storage_clear` 全仓库无调用点。** 同上，本次加的挂载校验当前无运行时效果。是否计划接线？
4. **`main.c:169` 把 Modbus 任务优先级从 6 降到 1 是否为有意决策？** 当前 `modbus_master_process()` 只 sleep 100ms，影响可忽略；但若后续接入请求队列，需重新评估该优先级。
5. **`论文/` 未跟踪目录**（8 个文件：`generate_docx.py`、4 个 `.md`、1 个 `.docx` 等）按指示未做任何处理。是否需要加入 `.gitignore` 或单独提交？本次审查不涉及。
6. **提交前是否必须跑完整 `idf.py build`？** 建议：必须。同时建议确认 `CONFIG_ADC_CONTINUOUS_ISR_IRAM_SAFE` 在 `sdkconfig.defaults` 中生效（`build/config/sdkconfig.h` 需在重新构建后包含该配置）。
7. **CRLF 警告**：`git diff` 对全部 13 个文本文件输出 `LF will be replaced by CRLF the next time Git touches it`，说明仓库未配置 `.gitattributes`。当前 diff 未显示整文件行尾变更（统计为 262 insertions / 116 deletions，非整文件重写），故不影响本次提交，但建议后续补 `.gitattributes` 以避免跨平台噪音。

---

## 附：本次审查执行的只读命令清单

```
git -C C:/Users/cxx/modbus-diag status --porcelain
git log --oneline -5
git remote -v
git rev-list --left-right --count origin/main...HEAD
git diff --stat
git diff --cached --stat
git diff -- <15 files>
git show HEAD:main/app_event.h
diff <(git show HEAD:main/app_event.h) components/common_config/app_event.h
find . -name "app_event*"
grep -rn "app_event|log_storage_*|health_metrics_*|traffic_stats_*|modbus_tcp_*|adc_sampler_*|TASK_PRIO_*|TODO|FIXME"
cat 各组件 CMakeLists.txt / partitions.csv / sdkconfig.defaults
grep -n ... C:/Users/cxx/esp-idf/components/spiffs/esp_spiffs.c
grep -n ... C:/Users/cxx/esp-idf/components/esp_adc/include/esp_adc/adc_continuous.h
grep -n ... C:/Users/cxx/esp-idf/components/hal/include/hal/adc_types.h
stat -c '%y %n' 源码与 build 产物
```

未执行任何写操作；工作区状态与审查前一致（14 modified + 1 deleted + 1 untracked dir）。
