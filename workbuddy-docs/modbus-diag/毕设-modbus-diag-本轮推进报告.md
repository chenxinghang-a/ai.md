# 毕设 modbus-diag — 本轮推进报告

时间：2026-09-15 01:30–01:50  
执行：常驻任务循环（automation `c7971699`）第 2 轮  
仓库：`C:\Users\cxx\modbus-diag` → `github.com/chenxinghang-a/modbus-diag`

---

## 一句话结论

**积压 3 个半月的 15 个未提交文件里藏着 5 处编译阻断，已全部修复；完整 ESP-IDF v5.4.0 构建通过；拆成 6 条 commit 提交并打 tag `v0.1.0-untested`。未推送（等主人一句话）。**

---

## 一、本轮做了什么

| # | 动作                 | 结果                                                       |
| - | ------------------ | -------------------------------------------------------- |
| 1 | 盘点未提交改动            | 14 个已修改 + 1 个已删除（不是队列里写的 12 个）                           |
| 2 | 静态审查 + 实机构建双重验证    | 静态审查报 3 处 P0；**实机构建又抓出 1 处静态审查漏掉的 P0**                   |
| 3 | 修复 5 处编译阻断         | 见下表                                                      |
| 4 | 完整 `cmake --build` | ✅ 通过，`modbus-diag.bin` 306352 B（旧 306224 B），976 个 obj 重建 |
| 5 | 分 6 条 commit 提交    | 全部落在 `main`，未建分支                                         |
| 6 | 打 tag              | `v0.1.0-untested`（无后缀才是已验证可用）                            |

### 修掉的 5 处编译阻断

| # | 位置                            | 问题                                      | 修法                                                      |
| - | ----------------------------- | --------------------------------------- | ------------------------------------------------------- |
| 1 | `adc_sampler.c:25`            | `edata->conv_frame_size` 不存在            | → `edata->size`（`conv_frame_size` 是 handle 配置字段，不是事件字段） |
| 2 | `adc_sampler.c:53`            | `adc_continuous_new_unit()` 不存在         | → `adc_continuous_new_handle()`                         |
| 3 | `adc_sampler.c:77`            | `adc_continuous_del_unit()` 不存在         | → `adc_continuous_deinit()`                             |
| 4 | `modbus_master.c:106/111/121` | **`uart_mode_t` 与 ESP-IDF 撞名**          | 项目侧改名 `app_uart_mode_t` / `APP_UART_MODE_*`（19 处，4 个文件） |
| 5 | `log_storage.c:13`            | `esp_spiffs_info(NULL,…)` 恒失败，日志存储被永久禁用 | → `esp_spiffs_mounted("storage")`                       |

**第 4 条是本轮最有价值的发现。** 根因：ESP-IDF 的 `hal/uart_types.h:51` 自己就有一个 `uart_mode_t`（枚举值 `UART_MODE_UART` / `UART_MODE_RS485_HALF_DUPLEX` …）。项目在 `app_config.h` 里重名，而 `driver/uart.h` 会把它带进每一个翻译单元 → `modbus_master.c` 直接编译失败。

**静态代码审查没看出来，只有真跑编译器才能抓到。** 这条已写进代码注释防复发。

### 顺手修掉的 3 个逻辑缺陷

| 位置                    | 问题                                        | 修法                                       |
| --------------------- | ----------------------------------------- | ---------------------------------------- |
| `adc_sampler.c:27`    | 循环上界 `i + 1 < len`，`len` 非 4 的倍数时越界读 4 字节 | → `i + SOC_ADC_DIGI_RESULT_BYTES <= len` |
| `adc_sampler.c:15`    | `s_write_idx` 被 ISR 与任务共享却非 `volatile`    | → `volatile`                             |
| `packet_capture.c:84` | 抓包任务创建失败时未归还 UART → Modbus 被永久拒绝且无自愈      | → 补 `set_uart_mode(IDLE)` 回滚             |



---

## 二、6 条提交

```
c5f4d91 feat(waveform): migrate ADC sampler from oneshot polling to continuous DMA
dc3af7a fix(storage): validate SPIFFS mount before log I/O
34867ff fix: add bounds checks for Modbus RTU frames and harden page stack and report serving
90e8c1a fix(concurrency): serialize shared state in Modbus TCP, health metrics and traffic stats
4d9f679 feat(modbus): arbitrate UART ownership between Modbus master and packet capture
4d91fb1 refactor: remove duplicate main/app_event.h
```

基线：`a2ce79f`（2026-05-27）。tag：`v0.1.0-untested`。  
工作区现在干净，只剩 `论文/` 未跟踪（见第四节）。  
`git rev-list --left-right --count origin/main...HEAD` = **0 / 6**（本地领先 6，未推）。

---

## 三、过程中的环境坑（已解决，供复用）

| 坑                | 现象                                                                        | 解法                                                                                       |
| ---------------- | ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| ESP-IDF 工具链缺件    | `export.bat` 报 `esp-rom-elfs has no installed versions`，`idf.py` 完全起不来    | `idf_tools.py install esp-rom-elfs`（走代理 10808），已装好                                       |
| Git Bash 跑 IDF   | `export.sh` 把 `/c/...` 转成 `C:\c\...`，activate.py 找不到                      | **用 `export.bat`**，别用 `export.sh`                                                        |
| `cmd.exe` 被安全策略拦 | Bash 里调 `cmd.exe` 直接被拒                                                    | 改走 PowerShell 调 `.bat`                                                                   |
| **GCC 内部段错误**    | `esp_lcd_panel_rgb.c:686` → `internal compiler error: Segmentation fault` | **不是代码问题**：当时可用内存只剩 1.4 GB，12 核默认并行度把内存打爆。用 `cmake --build build --parallel 2` 降到 2 路即通过 |
| `idf.py -j1` 无效  | `Error: No such option: -j`                                               | 改用 `cmake --build build --parallel N`                                                    |

---

## 四、没做的事（明确列出）

| 项                                                                 | 状态    | 原因                                                                                                                   |
| ----------------------------------------------------------------- | ----- | -------------------------------------------------------------------------------------------------------------------- |
| **推送 6 个提交**                                                      | ❌ 未推  | 推公开仓库属对外动作，按规矩先确认。**默认建议：推**                                                                                         |
| `论文/` 纳入版本控制                                                      | ❌ 未纳入 | 里面是完整毕业论文（`毕业论文_完整版.md` 112 KB + 排版版 docx + 生成脚本），共 8 个文件。是否进固件仓库需要主人定                                               |
| `adc_sampler.c` 的 buffer 竞态                                       | ❌ 未修  | `s_buf_mutex` 建了却从未 take/give，ISR 与 `page_waveform.c` 无同步读同一 buffer。**要改成双缓冲乒乓切换，属设计决策**，不擅自动手。已在 commit message 里写明 |
| `log_storage` / `health_metrics_update` / `traffic_stats_tick` 接线 | ❌ 未接  | 这三个函数全仓库无调用点，本轮加的锁与校验目前是空转。属既有问题                                                                                     |
| 原理图 / PCB / BOM                                                   | ❌ 未画  | 见第五节                                                                                                                 |

---

## 五、硬件侧：交付物为零，且有一个致命冲突

`hardware/` 目录**只有**一个空 KiCad 工程（`sheets: []`）和一个空 `.pretty` 目录 —— **无原理图、无 PCB、无 BOM**。

**画板之前必须先解决 GPIO4 冲突**（详细分析见 `modbus-diag-硬件缺口与补全方案.md` §4.A）：

`app_config.h:25` 把 GPIO4 定义为 RS-485 的 DE/RE 方向控制（`modbus_master.c:69` 配成推挽输出），  
`app_config.h:38` 又把 GPIO4 定义为 `ADC_CHANNEL_3`（ESP32-S3 上 ADC1_CH3 就是 GPIO4）。  
论文 `第4章_硬件设计.md:89` 和 `:121` 犯了同一个错。

同一引脚既推挽输出又模拟输入 → 波形功能必然失效；且论文说 ADC 测的是 RS-485 的 A 线（共模 −7 V~+12 V），真接上去有烧片风险。  
**推荐改法：ADC 挪到 GPIO5（ADC1_CH4）或 GPIO6（ADC1_CH5）**，代码和论文同步改。

BOM 已产出 45 行（`modbus-diag-BOM.csv`），其中 3 行是论文与代码都没写、按必要性补的缺项。

---

## 六、下一步建议

1. **主人拍板：推不推？** 一句话即可，我立刻执行。
2. 画原理图前先定 GPIO4 归属（改 ADC 到 GPIO5/6）。
3. 按硬件报告修正论文与代码的 27 处矛盾（2 致命 + 11 严重 + 14 中等）—— 答辩会被问。
4. `adc_sampler.c` 双缓冲改造（要设计决策）。
5. 接上 `log_storage` / `health_metrics_update` / `traffic_stats_tick` 的调用点。
