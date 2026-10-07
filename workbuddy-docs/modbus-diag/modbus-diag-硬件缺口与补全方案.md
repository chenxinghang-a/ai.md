# modbus-diag 硬件资产盘点 · 缺口分析 · 补全方案

> 盘点对象：`C:\Users\cxx\modbus-diag`（ESP-IDF v5.4 工程，目标 esp32s3）
> 盘点方式：**只读**。未修改仓库内任何文件，未执行任何 git 操作。
> 依据来源：`components/` `main/` 源码、`sdkconfig.defaults`、`dependencies.lock`、`partitions.csv`、各 `CMakeLists.txt`、`hardware/` 目录、`论文/` 目录。
> 凡论文与代码均未写明的，一律标注「**论文与代码均未明确**」，不做型号/引脚推测填充。

---

## 0. 结论速览（先看这一段）

| 项 | 状态 |
|---|---|
| 原理图 `.kicad_sch` | **缺失**（`hardware/` 下不存在） |
| PCB `.kicad_pcb` | **缺失** |
| BOM | **缺失**（论文与代码中均无 BOM/成本章节） |
| `hardware/modbus-diag.kicad_pro` | 存在，但为**空工程**（`sheets: []`，无原理图页；仅有设计规则与网络类） |
| `hardware/modbus-diag.pretty` | 存在，但为**空目录**（无任何 `.kicad_mod` 封装） |
| 引脚分配唯一权威来源 | `components/common_config/app_config.h`（1~44 行），全工程引脚均由此头文件定义 |
| 发现**致命级**问题 | **2 项**（GPIO4 双重占用；按键上拉方案自相矛盾） |
| 发现**严重级**问题 | **11 项**（见 §4.B） |
| 发现**中等级**问题 | **14 项**（见 §4.C） |

**一句话结论**：软件侧的硬件需求已经收敛得很清楚（引脚集中在 `app_config.h`，外设清单完整），但**硬件侧交付物为零**；且论文第 4 章与代码之间存在 1 个会让板子直接不工作的 GPIO4 冲突，必须在画原理图之前解决。

---

## 1. 硬件资产盘点

### 1.1 现有硬件资产（全部）

```
hardware/
├── modbus-diag.kicad_pro     ← 724 B，空工程（无 sheets、无原理图、无 PCB）
└── modbus-diag.pretty/       ← 空目录，0 个 .kicad_mod
```

`hardware/modbus-diag.kicad_pro` 是**唯一**的硬件文件，其内容已确认：

| 字段 | 值 | 说明 |
|---|---|---|
| `sheets` | `[]` | **无原理图页** → 原理图从未开始 |
| `board.layer_presets` / `boards` | `[]` | **无 PCB** |
| `libraries.pinned_footprint_libs` | `[]` | **未绑定任何封装库** |
| `net_settings.classes` | `Default` / `Power` / `RS485` | 已预设 3 个网络类（有设计意图，但无内容） |
| `Default` | clearance 0.2 / track 0.25 / via 0.6 / drill 0.3 | 单位 mm |
| `Power` | clearance 0.3 / track 0.5 / via 0.8 / drill 0.4 | 单位 mm |
| `RS485` | clearance 0.2 / track **0.3** / via 0.6 / drill 0.3 | 单位 mm |
| `design_settings.rules` | min_clearance 0.2 / min_track_width 0.25 | 单位 mm |

> **注**：`RS485` 网络类设定的线宽是 **0.3mm**，而论文 4.7.2（`第4章_硬件设计.md:145`）写的是「RS-485 差分信号线（A、B）…线宽 0.2mm」。二者不一致，详见 §4.C8。

### 1.2 其他可能含硬件信息的资料（已排查）

| 位置 | 是否含硬件信息 | 结论 |
|---|---|---|
| `README` / `docs/` | — | **项目根目录无 README、无 docs 目录** |
| `web/`（`app.js` `index.html` `style.css`） | 否 | 纯 Web 前端（HTML 报告页），无硬件信息 |
| `managed_components/` | 否 | 仅为 `espressif__mdns` 依赖库（构建产物），无硬件信息 |
| `build/` | 否 | 构建产物 |
| `论文/` | **是** | 硬件规格主来源，见 §3 |
| `hardware/*.pretty` | 否 | **空目录** |
| `sdkconfig` / `sdkconfig.defaults` | **是** | Flash 容量、PSRAM 模式、外设开关，见 §2.3 |

**结论：项目内除论文外，不存在任何原理图、封装、网表、Gerber 或其他硬件资料。**

### 1.3 代码规模核对

| 组件 | 源文件数 | 是否涉及硬件 |
|---|---|---|
| `display`（含 `pages/`） | 13 | **是**：SPI 驱动 ILI9341 |
| `input` | 2 | **是**：4 路 GPIO 按键 |
| `modbus_core` | 4 | **是**：UART1 + DE/RE 方向控制 |
| `waveform` | 4 | **是**：ADC 连续采样 |
| `storage` | 3 | 否（NVS + SPIFFS，片内） |
| `wifi_service` | 5 | 否（片内射频） |
| `protocol_analyzer` | 3 | 复用 UART1 |
| `modbus_scanner` | 3 | 复用 UART1 |
| `diag_report` | 3 | 否 |
| `common_config` | 2 | **是**：`app_config.h` 为引脚唯一来源 |
| `main` | 1 | **是**：初始化顺序 |

---

## 2. 代码反推硬件需求

### 2.1 引脚分配总表（权威来源：`components/common_config/app_config.h`）

所有引脚均在 `app_config.h` 中以宏定义，全工程无第二处引脚硬编码（已用 `GPIO_NUM_*` / `gpio_set_direction` / `adc_oneshot_channel` / `uart_set_pin` 全量 grep 确认）。

| # | GPIO | 信号 | 方向 | 代码依据（文件:行号） | 论文依据（`第4章_硬件设计.md`） | 一致性 |
|---|---|---|---|---|---|---|
| 1 | **GPIO0** | BOOT 下载模式选择 | 输入（上拉） | 无 | :83 | 仅论文 |
| 2 | **GPIO1** | BTN_UP 按键 | 输入（内部上拉） | `app_config.h:30`；`key_scan.c:13-15, 65-66` | :30, :113 | ✅ 一致 |
| 3 | **GPIO2** | BTN_DOWN 按键 | 输入（内部上拉） | `app_config.h:31`；`key_scan.c:13-15, 65-66` | :31, :113 | ✅ 一致 |
| 4 | **GPIO3** | TOUCH_IRQ（XPT2046） | 输入（中断） | `app_config.h:18`（**未被任何 .c 引用**） | :109 | ⚠️ 论文写了、代码未实现 |
| 5 | **GPIO4** | RS485_DE / RE | 输出 | `app_config.h:25`；`modbus_master.c:30, 35, 68-75` | :89 | ✅ 一致 |
| 6 | **GPIO4** | ADC1_CH3 波形采集 | 模拟输入 | `app_config.h:38`；`adc_sampler.c:67` | :121（另见 `毕业论文_完整版.md:343`） | ❌ **与 #5 冲突** |
| 7 | **GPIO7** | TFT_BL 背光 | 输出 | `app_config.h:10`；`tft_driver.c:145, 153` | :101, :105 | ✅ 一致 |
| 8 | **GPIO8** | TFT_RST | 输出 | `app_config.h:9`；`tft_driver.c:145, 156-158` | :101 | ✅ 一致 |
| 9 | **GPIO9** | TFT_DC | 输出 | `app_config.h:8`；`tft_driver.c:145, 93-94` | :101 | ✅ 一致 |
| 10 | **GPIO10** | TFT_CS | SPI 片选 | `app_config.h:7`；`tft_driver.c:179` | :101 | ✅ 一致 |
| 11 | **GPIO11** | TFT_MOSI | SPI 数据 | `app_config.h:5`；`tft_driver.c:163` | :101 | ✅ 一致 |
| 12 | **GPIO12** | TFT_SCK | SPI 时钟 | `app_config.h:6`；`tft_driver.c:165` | :101 | ✅ 一致 |
| 13 | **GPIO17** | RS485 TX → MAX3485 DI | UART1 TX | `app_config.h:23`；`modbus_master.c:86` | :89 | ✅ 一致 |
| 14 | **GPIO18** | RS485 RX ← MAX3485 RO | UART1 RX | `app_config.h:24`；`modbus_master.c:86` | :89 | ✅ 一致 |
| 15 | **GPIO41** | BTN_BACK 按键 | 输入（内部上拉） | `app_config.h:33`；`key_scan.c:13-15` | :31, :113 | ✅ 一致 |
| 16 | **GPIO42** | BTN_OK 按键 | 输入（内部上拉） | `app_config.h:32`；`key_scan.c:13-15` | :30, :113 | ✅ 一致 |
| 17 | **GPIO43** | UART0 TX → CH340G | UART0 | 无 | :83 | 仅论文 |
| 18 | **GPIO44** | UART0 RX ← CH340G | UART0 | 无 | :83 | 仅论文 |
| 19 | **GPIO46** | TOUCH_CS（XPT2046） | SPI 片选 | `app_config.h:17`（**未被任何 .c 引用**） | :109 | ⚠️ 论文写了、代码未实现 |
| 20 | **GPIO48** | 状态 LED | 输出 | `app_config.h:44`（**未被任何 .c 引用**） | :34-35（框图） | ⚠️ 论文写了、代码未实现 |
| 21 | GPIO19 / GPIO20 | USB-OTG D- / D+ | USB | 无 | 无 | **论文与代码均未明确** |

**占用统计**：GPIO0/1/2/3/4/7/8/9/10/11/12/17/18/41/42/43/44/46/48，共 19 个；ESP32-S3 可用 GPIO 约 36 个（WROOM-1 引出），**引脚资源充裕**。

**已确认「定义了但代码从未使用」的引脚**（grep `LED_PIN` / `TOUCH_PIN_CS` / `TOUCH_PIN_IRQ` / `TOUCH_SPI_HOST` 在所有 `.c` 中零命中）：
- `TOUCH_PIN_CS`（GPIO46）、`TOUCH_PIN_IRQ`（GPIO3）、`TOUCH_SPI_HOST`（SPI2_HOST）
- `LED_PIN`（GPIO48）

→ 触摸功能与状态 LED **只有硬件需求声明，没有驱动实现**。`components/input/input_event.c:3` 自述为 `/* This file exists as placeholder for future touch input integration */`，与此吻合。

### 2.2 外设清单（代码反推）

| 外设 | 型号 / 规格 | 接口 | 关键参数 | 代码依据 |
|---|---|---|---|---|
| 主控模组 | ESP32-S3，双核 LX7，240MHz | — | 8MB Flash（QIO/80MHz）、PSRAM（QUAD/80MHz） | `sdkconfig.defaults:4, 7-9, 16-18` |
| TFT 显示屏 | **ILI9341** | **4 线 SPI，SPI2_HOST（HSPI）** | 320×240，RGB565，**40MHz**，DMA 自动通道 | `app_config.h:3-13`；`tft_driver.c:162-182` |
| TFT 背光 | GPIO7 直驱（代码为纯 GPIO 开关） | GPIO 输出 | 代码中**无 LEDC/PWM**，仅 `gpio_set_level` | `app_config.h:10`；`tft_driver.c:145, 153` |
| 触摸控制器 | **XPT2046** | SPI2_HOST（与 TFT 共享总线），独立 CS | 2MHz（代码常量，未使用） | `app_config.h:15-19`（未被引用） |
| RS-485 收发器 | 代码仅见 UART，**芯片型号来自论文** | **UART1** | 默认 **9600** 8N1，超时 100ms，重试 2 次，缓冲区 512B | `app_config.h:22-27, 52-53`；`modbus_master.c:15-22, 79-91` |
| RS-485 方向控制 | DE 与 RE 并联，单 GPIO 控制 | GPIO 输出（推挽） | 高=发送，低=接收 | `app_config.h:25`；`modbus_master.c:28-36, 76` |
| ADC 采样 | ESP32-S3 内置 ADC，**ADC_UNIT_1** | 连续（DMA）模式 | **100 000 Hz**，深度 **1024** 点，12dB 衰减 | `app_config.h:38-41`；`adc_sampler.c:49-72, 104` |
| 按键 | 4 个独立按键 | GPIO 输入，**内部上拉**，低有效 | 轮询周期 30ms，长按 800ms | `app_config.h:30-35`；`key_scan.c:31-59, 64-72` |
| 存储 | **无 SD 卡**。NVS + SPIFFS（片内 Flash） | — | SPIFFS 分区 64KB，挂载点 `/spiffs` | `partitions.csv:2-5`；`main.c:96-109`；`log_storage.c:8` |
| WiFi 天线 | 片内（无外置天线代码） | — | AP 模式 SSID `ModbusDiag` / 密码 `12345678`，Web 端口 80 | `app_config.h:46-49`；`wifi_manager.c:70` |
| 电源 | 代码无涉及 | — | — | — |

**明确不存在的外设**（已全量 grep 确认）：
- **无 SD / TF 卡**（`sdmmc` / `sdspi` / `SD卡` 在代码与论文中零命中）
- **无 I²C 外设**（`i2c` 零命中）
- **无 LEDC/PWM**（`ledc` 零命中；论文 4.4.2 称「预留 PWM 调光能力」与代码一致，属预留未实现）
- **无 RTC 芯片**（32.768kHz 晶振仅论文提及）
- **无 LVGL、无 esp_lcd**（`lvgl` / `esp_lcd` 零命中）→ 显示驱动为**完全自研**，与论文「自研轻量级 GUI 框架」表述一致

### 2.3 配置层面的硬件约束

| 配置项 | 值 | 文件:行号 |
|---|---|---|
| 目标芯片 | `esp32s3` | `sdkconfig.defaults:4` |
| Flash 容量 | **8MB**，QIO，80MHz | `sdkconfig.defaults:7-9` |
| PSRAM | **启用**，QUAD 模式，80MHz | `sdkconfig.defaults:16-18` |
| 分区表 | 自定义 `partitions.csv` | `sdkconfig.defaults:12-13` |
| 分区布局 | nvs 0x6000 / phy 0x1000 / factory 0x1E0000 / storage(spiffs) 0x10000 | `partitions.csv:2-5` |
| 双核 | `CONFIG_FREERTOS_UNICORE=n` | `sdkconfig.defaults:22` |
| ADC | `CONFIG_ADC_DISABLE_DAC=y`，连续模式 ISR 置于 IRAM | `sdkconfig.defaults:36-38` |
| 控制台 | UART0 默认引脚 | `sdkconfig.defaults:25` |
| 外部依赖 | 仅 `espressif/mdns` 1.11.1（IDF 5.4.0） | `dependencies.lock:1-20` |

> **PSRAM 关键发现**：`sdkconfig.defaults` 启用了 8MB PSRAM，但全工程 grep `SPIRAM` / `MALLOC_CAP_SPIRAM` / `heap_caps` **零命中**——PSRAM 配置了但代码从未使用。详见 §4.C2。

### 2.4 任务与核心分配（用于核对论文 5.1.3）

| 任务 | 核心 | 优先级 | 依据 |
|---|---|---|---|
| `ui_task` | Core **1** | `TASK_PRIO_UI` = 5 | `main.c:165-166` |
| `modbus_task` | Core **0** | 1（硬编码，注释说明为占位） | `main.c:168-169` |
| `key_scan` | Core **1** | 3（硬编码） | `key_scan.c:78` |
| `capture` | 见 `packet_capture.c:81` | `TASK_PRIO_CAPTURE` = 4 | `packet_capture.c:81` |

---

## 3. 论文已写明的硬件规格（提取）

来源：`论文/第4章_硬件设计.md`（15842 B）。已逐行 diff 验证 `毕业论文_完整版.md:553-707` 与本章**内容完全一致**（仅差末尾分隔符），因此两处引用等价。

### 3.1 选型结论（`第4章_硬件设计.md:49-59`）

| 部件 | 论文选定型号 | 论文给出的关键参数 |
|---|---|---|
| 主控 | **ESP32-S3-WROOM-1** | 双核 LX7 @240MHz；512KB SRAM；**8MB Flash + 8MB PSRAM**；2×SPI、2×UART、多通道 12 位 ADC、原生 USB-OTG；内置 2.4GHz WiFi（AP/STA） |
| RS-485 收发器 | **MAX3485** | 3.3V 半双工；最高 10Mbps；±15kV ESD；54Ω 负载下 ≥±1.5V；1/8 单位负载，最多 256 节点；静态 300μA；−40~+125℃ |
| 显示驱动 | **ILI9341** | 262K 色；240×320；内置 172800 B 显存；4 线 SPI @40MHz；20ms 全屏刷新 |
| 触摸控制器 | **XPT2046** | 4 线电阻式；内置 12 位 SAR ADC；与主控共享 SPI，独立片选 |
| LDO | **AMS1117-3.3** | 输入 4.5~12V；输出 3.3V/1A；压差典型 1.1V |

### 3.2 各电路模块参数

| 模块 | 论文给出的参数 | 依据 |
|---|---|---|
| 电源输入 | USB Type-C 输入 5V | :65 |
| LDO 输入滤波 | 10μF 钽 + 100nF 陶瓷 | :65 |
| LDO 输出滤波 | 22μF 钽（ESR 0.5Ω）+ 100nF 陶瓷 | :65 |
| 去耦电容 | 100nF，**0402 封装**，距引脚 ≤3mm；VDD3P3 与 VDD_SDIO 各一 | :67 |
| 总电流估算 | ESP32-S3 约 240mA + ILI9341 约 80mA + MAX3485 约 2mA + 其他 30mA = **约 352mA** | :67 |
| 主晶振 | 40MHz 无源 + **22pF** ×2 负载电容 | :73 |
| RTC 晶振 | 32.768kHz 无源 ±20ppm + **12.5pF** ×2 负载电容 | :75 |
| 复位 | EN 上拉 **10KΩ** + **100nF** 到地（τ=1ms） + 手动复位按键 | :79 |
| 下载 | **CH340G**；UART0 TX=GPIO43 / RX=GPIO44；BOOT=GPIO0，10KΩ 上拉 | :83 |
| RS-485 连接 | RO→GPIO18；DI→GPIO17；RE+DE 并联→GPIO4；VCC 就近 100nF | :89 |
| 终端电阻 | **120Ω**，预留焊盘 + 跳线帽或 0Ω 电阻可选接入 | :93 |
| ESD 保护 | A/B 线各并联 **SMBJ6.5CA**，钳位约 10.5V，响应 <1ns | :95 |
| 失效安全偏置 | A/B 间 **15KΩ** 偏置网络（A 上拉 3.3V，B 下拉 GND） | :95 |
| TFT 连接 | SCK=GPIO12、MOSI=GPIO11、CS=GPIO10、DC=GPIO9、RST=GPIO8、BL=GPIO7；40MHz | :101 |
| 上电时序 | 先供 VCC/IOVCC → 延时 ≥10ms → 释放 RST → 延时 120ms → 发初始化序列 | :101 |
| 背光驱动 | GPIO7 → **2N7002** MOS 管；白光 LED 串联；限流电阻 **100Ω** = (5V−3.0V)/20mA；预留 PWM 调光 | :105 |
| 触摸接口 | TCS=GPIO46、IRQ=GPIO3；与 ILI9341 共享 MOSI/SCK | :109 |
| 按键 | 4 个独立按键 → GPIO1/GPIO2/GPIO42/GPIO41；**外部 10KΩ 上拉**；并联 **100nF** 消抖（τ=1ms）；软件 30ms 消抖；长按 800ms | :113, :115 |
| ADC 通道 | **ADC1_CH3（GPIO4）**，12 位 SAR，满量程 0~3.1V（11dB 衰减） | :121 |
| ADC 分压 | R1=10KΩ、R2=10KΩ，衰减 1/2，最大可测 6.2V | :123 |
| ADC 缓冲 | **LM358** 电压跟随器（输入阻抗约 1MΩ，输出阻抗约 100Ω） | :125 |
| ADC 滤波 | R3=1KΩ + C1=10nF，fc≈**15.9kHz** | :129 |
| ADC 钳位 | **BAT54S** 双向钳位（Vf≈0.3V，Cj≈10pF） | :131 |
| PCB | **4 层板**：顶层信号 / 内层1 GND / 内层2 3.3V / 底层信号；尺寸 **80mm×60mm** | :137 |
| 高速走线 | SPI 目标 50Ω 单端，线宽约 0.15mm，长度匹配 ±5mm，3W 原则 | :143 |
| RS-485 走线 | 差分对，**线宽 0.2mm、线距 0.2mm**，差分阻抗 100Ω±10% | :145 |
| 电源分区 | 数字/模拟 3.3V 平面经 **磁珠 100Ω@100MHz** 单点连接 | :149 |
| 天线净空 | 模组端部 10mm×5mm 净空；板框外延 ≥2mm；天线正下方各层挖空 | :151 |

### 3.3 论文其他章节的硬件相关表述（需一并核对）

| 位置 | 表述 |
|---|---|
| `毕业论文_完整版.md:337-343`（3.2.1 硬件架构） | RS-485 走 **UART1，115200bps**；TFT 用 **HSPI(SPI2)** @40MHz；按键**采用内部上拉电阻**、**通过定时器中断实现按键消抖**；ADC 采样 100kHz / 1024 点 / 约 10ms |
| `毕业论文_完整版.md:343` | 「RS-485 总线的 **A 线信号**经过分压和滤波电路后连接至 ESP32-S3 的 GPIO4（ADC1 通道 3）」 |
| `毕业论文_完整版.md:411` | waveform 组件「对原始数据进行**中值滤波**去噪」 |
| `毕业论文_完整版.md:415` | input 组件「通过**定时器中断以 10ms 周期**扫描按键…连续 **3 次**采样一致即判定有效…长按**超过 1 秒**」 |
| `毕业论文_完整版.md:858` | 「采样任务…循环调用 **`adc_oneshot_read`** 函数进行单次 ADC 转换…目标 100KSPS，实际约 **20-50KSPS**」 |
| `毕业论文_完整版.md:864` | 「系统采用**简单移动平均（SMA）**滤波器进行平滑处理」 |
| `毕业论文_完整版.md:1342` | 「**后续可通过引入 DMA 连续采样模式**提升采样速率」（列为未来改进方向） |
| `毕业论文_完整版.md:15`（摘要） | 「波形采样率可达 **20-50KSPS**」 |
| `毕业论文_完整版.md:1033` | 测试用逻辑分析仪 Saleae Logic Pro 8（**非本机硬件**，仅测试仪器） |
| `毕业论文_完整版.md:1037` | 测试用 USB 转 RS-485 适配器 CH340G（**非本机硬件**，仅测试仪器） |

---

## 4. 代码 ↔ 论文 交叉核对：矛盾点清单

> 分级标准：
> **A 致命** = 按现状画板会直接不工作或烧器件
> **B 严重** = 功能可用但有隐患，答辩大概率被追问
> **C 中等** = 描述/配置不一致，影响论文严谨性

### A. 致命级（2 项）

#### A1. GPIO4 被同时分配给 RS-485 方向控制和 ADC 采样 ⚠️ 最高优先级

| 侧 | 证据 |
|---|---|
| 代码（RS-485 DE） | `app_config.h:25` → `#define RS485_PIN_DE 4`；`modbus_master.c:30` `gpio_set_level(RS485_PIN_DE, 1)`；`modbus_master.c:69` 将其配为 `GPIO_MODE_OUTPUT` |
| 代码（ADC 输入） | `app_config.h:38` → `#define WAVE_ADC_CHANNEL ADC_CHANNEL_3 /* GPIO4 */`；`adc_sampler.c:67` `.channel = WAVE_ADC_CHANNEL` |
| 论文（RS-485 DE） | `第4章_硬件设计.md:89`「RE 和 DE 引脚并联后由 **GPIO4** 统一控制」 |
| 论文（ADC 输入） | `第4章_硬件设计.md:121`「模拟信号采集通道连接 ESP32-S3 的 **ADC1_CH3（GPIO4）**」；另见 `毕业论文_完整版.md:343` |

**技术事实**：ESP32-S3 的 ADC1 通道映射为 CH0=GPIO1 … **CH3=GPIO4** … CH9=GPIO10。因此 `ADC_CHANNEL_3` 与 GPIO4 是同一个物理引脚。

**后果**：
1. 同一引脚既被配成**推挽输出**（DE 驱动 MAX3485 的 DE/RE），又被配成**模拟输入**（ADC）。二者在硅片内部直接冲突，ADC 读到的实际是 DE 输出电平或悬空值，**波形采集功能必然失效**。
2. 论文 3.2.1 明确 ADC 测的是「**RS-485 总线的 A 线信号**」。A 线共模范围约 −7V~+12V，若真接到该脚，会通过 GPIO4 的推挽输出级灌入大电流，**有损坏芯片的风险**。
3. 这不是代码 bug 也不是论文笔误，而是**同一处错误在两侧一致存在**——说明设计阶段就没发现。

**修法（三选一，需在画原理图前定稿）**：
- **方案 1（推荐）**：ADC 换到空闲引脚，如 **GPIO5（ADC1_CH4）** 或 **GPIO6（ADC1_CH5）**，同步改 `app_config.h:38` 与论文 `:121`。改动最小。
- **方案 2**：RS-485 DE 换到空闲 GPIO（如 GPIO13/14），保留 GPIO4 作 ADC。但 DE 走线变长，影响方向切换时序。
- **方案 3**：若坚持共用，需加模拟开关做时分复用——复杂且 ADC 采样时会打断 Modbus 通信，**不推荐**。

#### A2. 按键上拉方案：代码/论文 3.2.1 用内部上拉，论文 4.5 用外部 10KΩ

| 侧 | 证据 |
|---|---|
| 代码 | `key_scan.c:68` `.pull_up_en = GPIO_PULLUP_ENABLE`（**内部上拉**，无外部上拉代码） |
| 论文 3.2.1 | `毕业论文_完整版.md:341`「4 个独立按键…**采用内部上拉电阻**」 |
| 论文 4.5 | `第4章_硬件设计.md:113`「GPIO 引脚**通过 10KΩ 电阻上拉至 3.3V**」 |

**后果**：
- 论文**自身两处矛盾**（3.2.1 vs 4.5），答辩必被问。
- 若照论文 4.5 加外部 10KΩ 上拉：功能正常，但与内部上拉并联（约 8.7KΩ），且浪费 4 个电阻。
- 若照代码只用内部上拉：ESP32-S3 内部上拉典型值约 **45KΩ**，则论文 4.5 的 RC 消抖计算 τ = 10KΩ×100nF = 1ms **不成立**（实际 τ ≈ 45KΩ×100nF = 4.5ms），硬件消抖时间常数与论文描述不符。

**修法**：**统一为外部 10KΩ 上拉 + 100nF 消抖电容**（论文 4.5 方案），并把代码 `key_scan.c:68` 的 `pull_up_en` 改为 `GPIO_PULLUP_DISABLE`；同时删掉论文 3.2.1 的「采用内部上拉电阻」表述。

---

### B. 严重级（11 项）

#### B1. ADC 采样方式：论文说单次软件循环，代码是 DMA 连续模式
- 论文 `毕业论文_完整版.md:858`：循环调用 **`adc_oneshot_read`**，实际 20-50KSPS。
- 代码 `adc_sampler.c:3` 引入 `esp_adc/adc_continuous.h`，`:53` `adc_continuous_new_unit()`，`:104` `adc_continuous_start()`，采样率 `:61` 配 100000 Hz，DMA 双缓冲 `:50-51`。
- **加强矛盾**：论文 `毕业论文_完整版.md:1342` 把「引入 DMA 连续采样模式」列为**未来改进方向**，但代码**已经实现**了 DMA 连续采样。
- 影响：论文第 5 章与第 7 章结论落后于代码，答辩若演示 DMA 采集会被质疑。
- **修法**：论文 5.x 与 7.x 按 `adc_sampler.c` 的实际实现改写（连续模式 + `adc_continuous_evt_cbs_t` 回调）；摘要的「20-50KSPS」需重新实测后修正。

#### B2. 滤波算法：论文说中值滤波，代码是滑动平均
- 论文 `毕业论文_完整版.md:411`：「对原始数据进行**中值滤波**去噪」。
- 代码 `signal_process.h:4` `void signal_filter_sma(...)`，`:7` 注释 `/* Apply simple moving average filter */`。
- 论文 `毕业论文_完整版.md:864` 自己也写的是 **SMA**，且摘要 `:13` 也写「滑动平均滤波」。
- 结论：`:411` 是论文内部的孤立笔误。
- **修法**：把 `:411` 的「中值滤波」改为「滑动平均滤波」。

#### B3. 背光「LED 串联」与限流电阻计算自相矛盾
- 论文 `第4章_硬件设计.md:105`：「TFT 背光采用白光 LED **串联**方案」；随后 `R = (5V − 3.0V) / 20mA = 100Ω`。
- 该公式只对**单颗** LED（或并联）成立。若真为 2 颗串联，Vf 合计 6.0V > 5V，**根本无法点亮**。
- **修法**：二选一——(a) 改为「单颗高亮白光 LED 或多颗并联」，保留 100Ω；(b) 保留串联但背光供电改用 12V 或升压，重算限流电阻。

#### B4. 「裸屏」与「显示模组」两种设计口径混用
- 论文 `第4章_硬件设计.md:105` 按**裸屏**设计背光：LED 串 + 限流电阻 + 2N7002 MOS 管。
- 论文 `:101` 和 `:109` 又按**集成模组**描述：单一 BL 脚、与 XPT2046 共享 SPI、40MHz。
- 市售 ILI9341 2.4"/2.8" 模组通常**自带背光升压/限流电路和 MOS 管**，只引出 VCC/GND/BL；若用模组，4.4.2 的 100Ω 和 2N7002 就是多余的；若用裸屏，则 XPT2046 需另行外挂（裸屏不含触摸控制器）。
- **修法**：明确 BOM 选「**含 XPT2046 的 ILI9341 SPI 模组**」（推荐，与代码 4 线 SPI + 独立 CS 一致），4.4.2 改写为「模组 BL 脚经 2N7002 或直接由 GPIO7 控制」。

#### B5. 40MHz 晶振与模组内置晶振冗余
- 论文 `第4章_硬件设计.md:73`：设计外部 **40MHz 无源晶振 + 22pF ×2**。
- 事实：**ESP32-S3-WROOM-1 模组内部已集成 40MHz 晶振**。原理图上再画一颗不仅冗余，还会与模组内部电路冲突（模组未引出 XTAL 引脚）。
- 论文 `:73` 自己也写「40MHz 时钟经内部 PLL 倍频至 240MHz」——既然靠内部 PLL，就不需要外部晶振。
- **修法**：删除外部 40MHz 晶振及 2×22pF。**32.768kHz RTC 晶振需要保留**（WROOM-1 默认不含，若用 RTC/深睡唤醒才需要；本工程代码中无 RTC 使用，可标注为「预留」）。

#### B6. RS-485 失效安全偏置 15KΩ 严重偏弱
- 论文 `第4章_硬件设计.md:95`：「A、B 信号线之间并联一个 **15KΩ** 偏置电阻网络（A 线上拉至 3.3V，B 线下拉至地），确保总线空闲时 A>B，处于逻辑『1』」。
- 计算（含 120Ω 终端电阻）：回路总阻 = 15000 + 120 + 15000 = 30120Ω；电流 ≈ 3.3/30120 ≈ 109.6µA；**V_AB ≈ 109.6µA × 120Ω ≈ 13.1mV**。
- RS-485 接收器判定逻辑「1」的门限是 **≥200mV**（差分输入阈值 ±200mV）。**13mV 只有门限的 6.5%**，无法保证失效安全，总线空闲时输出电平不确定，会产生随机误帧。
- **修法**：偏置电阻改为 **390Ω~680Ω**（例如上拉 680Ω、下拉 680Ω → V_AB ≈ 3.3×120/(680+120+680) ≈ 267mV，满足门限）。若选带真正失效安全（true fail-safe）的收发器（如 MAX3485E 系列中带 F 后缀型号）可降低对偏置的依赖，但本设计已选 MAX3485，建议仍加合理偏置。

#### B7. RS-485 A 线电压超出 ADC 量程，BAT54S 会长期钳位
- 论文 `第4章_硬件设计.md:121-123`：ADC 满量程 0~3.1V，R1/R2 各 10KΩ 分压 1/2，「最大可测输入电压扩展至 **6.2V**」。
- 事实：RS-485 总线 A 线的**共模电压范围是 −7V ~ +12V**（TIA/EIA-485-A 规定）。经 1/2 分压后为 **−3.5V ~ +6V**，远超 ADC 的 0~3.1V 输入范围。
- 后果：论文 `:131` 的 BAT54S 会在大部分工作时间内处于**导通钳位**状态，导致：(a) 波形读数严重失真（顶部/底部被削平）；(b) 分压电阻上有持续电流；(c) 长期钳位影响可靠性。
- **修法**：提高分压比（如 R1=30KΩ / R2=10KΩ，衰减 1/4 → 可测 ±12V 且 3.1V 对应 12.4V），或在前级加**差分/隔离放大器**（如 AMC1200）后再进 ADC。若只测 A 线相对 GND 的低压信号，应在论文中明确「仅适用于共模正常的低压测试场景」。

#### B8. CH340G 缺少必需的 12MHz 晶振
- 论文 `第4章_硬件设计.md:83`：下载电路采用 **CH340G**。
- 事实：**CH340G 无内置振荡器，必须外接 12MHz 晶体（或 12MHz 陶瓷谐振器）+ 2 个负载电容**。论文 4.2 全文未提及该晶振。
- 后果：按论文画板，CH340G 不工作，USB 下载/调试失效。
- **修法**：二选一——(a) 补上 12MHz 晶振 + 2×22pF（约 0.5 元）；(b) **改用 CH340C / CH340N**（内置振荡器，无需外部晶振，且 CH340N 为 SOP-8 更省面积）。推荐 (b)，并同步修改论文 `:83`。

#### B9. USB Type-C 缺少 CC 下拉电阻
- 论文 `第4章_硬件设计.md:65`：USB Type-C 接口输入 5V。
- 事实：Type-C 作为**受电端（Sink）**时，必须在 CC1、CC2 上各接一个 **5.1kΩ 下拉电阻到 GND**，否则标准 Type-C 电源（含 PD 充电器）**不会输出电压**。
- 论文未提及该电阻。
- **修法**：补 2×5.1kΩ（0402）。若改用 6P 简易 Type-C 母座（仅 2 个 CC 焊盘合并处理），仍需 1 个 5.1kΩ 到 CC。

#### B10. 触摸 IRQ(GPIO3) 与 CS(GPIO46) 落在 strapping 引脚上
- 论文 `第4章_硬件设计.md:109`：TCS=**GPIO46**、IRQ=**GPIO3**；代码 `app_config.h:17-18` 一致。
- 事实：ESP32-S3 的 strapping 引脚为 **GPIO0、GPIO3、GPIO45、GPIO46**。
  - **GPIO3** = JTAG 信号源选择（Strapping）。
  - **GPIO46** = ROM 信息打印 / 启动模式相关（Strapping，内部默认下拉）。
- 后果：上电复位瞬间，若 XPT2046 的 IRQ（低有效、开漏）或 CS 将这两个脚拉至非预期电平，会**影响启动模式或 JTAG 选择**，导致偶发启动失败或无法下载。这类问题现场极难定位。
- **修法**：把 TOUCH_CS 与 TOUCH_IRQ 挪到普通 GPIO（如 GPIO14/GPIO21），或在两脚各加 10KΩ 上拉/下拉使上电电平确定且与 strapping 默认值一致。同时同步改论文 `:109` 与 `app_config.h:17-18`。

#### B11. 按键 GPIO41/GPIO42 是 JTAG MTDI/MTMS 默认引脚
- 论文 `第4章_硬件设计.md:113`：按键接 GPIO42（OK）、GPIO41（BACK）；代码 `app_config.h:32-33` 一致。
- 事实：ESP32-S3 默认 JTAG 引脚为 MTCK=GPIO39、MTDO=GPIO40、**MTDI=GPIO41、MTMS=GPIO42**。将 GPIO41/42 用作按键输入会**禁用默认 JTAG 调试**（除非通过 eFuse 重映射）。
- 佐证：`main/CMakeLists.txt:17` 引入了 `efuse` 组件，`main.c:10` 包含 `esp_efuse.h`，但 `main.c:141` **仅调用了 `esp_efuse_get_pkg_ver()` 打印版本**，**并未做 JTAG 重映射**。
- 后果：功能可用（按键正常工作），但若需在线调试则需 eFuse 重映射（一次性烧写，不可逆）。
- **修法**：论文中补一句说明「GPIO41/42 用作按键，放弃默认 JTAG，如需调试通过 eFuse 将 JTAG 重映射至其他 GPIO」；或改用 GPIO13/14 等空闲脚。

---

### C. 中等级（14 项）

| # | 矛盾/缺口 | 代码侧 | 论文侧 | 建议 |
|---|---|---|---|---|
| C1 | RS-485 默认波特率 | `app_config.h:26` **9600** | `毕业论文_完整版.md:323` 框图写 UART1 **115200bps** | 统一为「默认 9600，可配 1200~115200」（论文 `:255` 的 FR1 表述才是对的） |
| C2 | PSRAM 配了但没用 | `sdkconfig.defaults:16-18` 启用 8MB PSRAM；全工程 `heap_caps`/`MALLOC_CAP_SPIRAM` **零命中** | `第4章_硬件设计.md:51` 强调 8MB PSRAM 满足「波形数据缓存、图形渲染」需求 | 二选一：在代码中显式用 PSRAM（如给波形缓冲/帧缓冲分配 `MALLOC_CAP_SPIRAM`），或删掉 sdkconfig 中的 PSRAM 配置并修改论文表述 |
| C3 | Flash 容量与分区表不匹配 | `sdkconfig.defaults:7` 8MB Flash；`partitions.csv` 仅用到 0x200000（**2MB**），6MB 闲置 | 论文未讨论分区 | 扩大 SPIFFS（现仅 **64KB**，`partitions.csv:5`），报告/日志/报文导出容易写满 |
| C4 | 触摸功能论文详述、代码未实现 | `app_config.h:15-19` 定义引脚但**零引用**；`input_event.c:3` 自述为占位符 | `第4章_硬件设计.md:107-109` 完整描述 XPT2046 电路 | 明确取舍：要么在 BOM 中保留 XPT2046 并在论文标注「预留未实现」，要么从论文 4.4.3 中删除 |
| C5 | 状态 LED 论文有、代码无 | `app_config.h:44` `LED_PIN 48` **零引用** | `第4章_硬件设计.md:34-35` 框图标注「GPIO48 LED指示灯」 | 补 LED 驱动（3 行代码）或从论文中删除 |
| C6 | 按键消抖实现方式 | `key_scan.c:31-59` **30ms 轮询任务**，基于时间阈值；`BTN_DEBOUNCE_MS=30`（`app_config.h:34`） | `毕业论文_完整版.md:341, 415`：**定时器中断**、**10ms 周期**、**连续 3 次采样一致** | 论文按代码改写，或代码改用 esp_timer；三处参数（10/30ms、3 次采样）需对齐 |
| C7 | 长按阈值 | `app_config.h:35` `BTN_LONG_PRESS_MS` **800ms** | `毕业论文_完整版.md:415` 长按**超过 1 秒** | 统一为 800ms 或 1000ms |
| C8 | RS-485 差分线宽 | `hardware/modbus-diag.kicad_pro` 中 `RS485` 网络类 `track_width` = **0.3mm** | `第4章_硬件设计.md:145` 线宽 **0.2mm**、线距 0.2mm | 统一（0.2mm 更贴近 100Ω 差分目标阻抗，建议改 KiCad 网络类） |
| C9 | MAX3485 的 ±15kV ESD 规格 | 代码不涉及 | `第4章_硬件设计.md:53` 称 MAX3485 具备 ±15kV ESD | ±15kV ESD 通常是 **MAX3485E** 的规格；建议 BOM 明确写 MAX3485 或 MAX3485E，或保留外部 SMBJ6.5CA 作为兜底（论文 `:95` 已有 TVS） |
| C10 | USB-OTG 引脚未明确 | 无 | 论文 `:51` 提到「原生 USB-OTG 接口」，但未给出引脚 | ESP32-S3 原生 USB 使用 **GPIO19 (D−) / GPIO20 (D+)**，需在原理图中明确，并考虑 USB ESD 保护 |
| C11 | 5V 输入无保护 | 无 | 论文 4.2.1 仅描述 Type-C → LDO，无保险丝/防反接/TVS | 建议增加自恢复保险丝（PTC）+ 输入 TVS；毕设虽可省，但论文可写为「预留」 |
| C12 | 无电源指示/电源开关 | 无 | 未提及 | 建议加电源指示 LED + 限流电阻，或明确不做 |
| C13 | 主控模组型号后缀未明确 | `sdkconfig.defaults:7,16-18` 仅给出 8MB Flash + QUAD PSRAM | `第4章_硬件设计.md:51` 仅说「8MB Flash 及 8MB PSRAM」 | 具体型号后缀（如 N8R8）**论文与代码均未明确**，需在 BOM 中确认；不同后缀影响天线形式（PCB 天线 / IPEX）与封装 |
| C14 | LDO 热设计未讨论 | 无 | 论文 `:67` 只算电流裕量，未算耗散 | 按 352mA、压差 1.7V 估算，AMS1117 耗散约 **0.6W**，SOT-223 需保证足够铜箔散热；论文可补一句 |

---

## 5. BOM 表

完整清单见同目录 **`modbus-diag-BOM.csv`**（UTF-8 带 BOM，Excel 直接打开不乱码）。

### 5.1 BOM 统计

| 维度 | 数量 |
|---|---|
| 物料行数 | **45 行** |
| 其中「论文与代码均未明确」的补缺项 | **3 行**（12MHz 晶振、5.1kΩ CC 下拉、状态 LED 限流电阻） |
| 封装标注为「待定」的行 | **24 行** |
| 明确给出封装的来源 | 仅论文 `:67` 明确 0402（去耦电容）；其余按行业常规标注并注明 |
| 论文/代码未给出的字段 | 封装、位号、厂商料号、单价、成本——**均无出处，不做编造** |

### 5.2 BOM 关键说明

- **封装「待定」的原因**：论文只对去耦电容指定了 0402（`第4章_硬件设计.md:67`），对模组、按键、连接器等均未指定封装；`hardware/modbus-diag.pretty` 为空目录，无封装库可参考；`modbus-diag.kicad_pro` 未绑定任何封装库（`pinned_footprint_libs: []`）。因此除论文明确项外一律标「待定」，待选定实际采购料号后回填。
- **数量标注「待定」的行**：`100nF` 去耦电容的数量取决于模组电源引脚数与布线，论文只给出「就近放置」的原则性要求（`:67`），未给具体颗数。
- **BOM 中未列入的项**（因为论文与代码均未明确，不编造）：保险丝、电源开关、电源指示 LED、ESD 保护二极管（USB 侧）、调试排针、测试点、丝印/面板、外壳结构件。
- **不属于本机 BOM 的测试仪器**（论文 `:1033-1037` 提及但非本设备硬件）：Saleae Logic Pro 8、USB 转 RS-485 适配器（CH340G）、Modbus Slave / Modbus Poll 软件、测试用 PC。

---

## 6. 缺口补全方案：三条路线对比

### 6.0 三个缺口的依赖关系

```
① 原理图 .kicad_sch ──┬──> ② PCB .kicad_pcb ──> Gerber ──> 打样/焊接
                      │
                      └──> ③ BOM（由原理图自动导出，或反向补齐原理图）
```

**关键顺序**：BOM 必须**从原理图导出**（而不是手工列），否则 BOM 与原理图必然脱节，答辩时一查就穿。所以正确顺序是 **先解决 A1/A2 两个致命冲突 → 画原理图 → 导出 BOM → 画 PCB**。

### 6.1 三条路线对比

| 维度 | **路线 A：KiCad 手绘** | **路线 B：立创EDA 绘制** | **路线 C：由网表/代码生成** |
|---|---|---|---|
| **工具** | KiCad 8/9（`hardware/modbus-diag.kicad_pro` 已存在） | 立创EDA 专业版（桌面已有快捷方式） | SKiDL / 自写 Python 生成网表 → 再导入 EDA |
| **原理图工作量** | 约 40~60 个元件符号，全手工放置+连线，约 8~15 小时 | 约 4~8 小时（元件库现成、符号封装绑定好、连线辅助强） | 网表生成约 2~4 小时，但**仍需人工画原理图供论文插图** |
| **PCB 工作量** | 4 层板 80×60mm，约 10~20 小时（需手工设层叠、阻抗、差分对） | 约 6~12 小时（4 层板模板、差分对工具、DRC 更友好） | 布局布线无法自动生成，**工作量与路线 A/B 相同** |
| **元件库/封装** | 需自行准备：`modbus-diag.pretty` **当前为空**；ESP32-S3-WROOM-1、ILI9341 模组、XPT2046 模组、Type-C 座等需手工建库或下载 | **立创商城元件库直接可用**，符号+封装+BOM 三合一，命中率高（ESP32-S3-WROOM-1、MAX3485、AMS1117、CH340C、SMBJ6.5CA、BAT54S 均为常用料） | 同路线 A，仍需外部库 |
| **BOM 导出** | 「工具→生成 BOM」导出 CSV，字段需自行映射 | **一键导出 BOM**，且直接对接嘉立创下单，字段天然齐全（型号、封装、位号、数量） | 网表本身即 BOM 雏形，但需再格式化 |
| **git 友好度（主人的硬要求：每版推 git）** | ⭐⭐⭐⭐⭐ `.kicad_sch`/`.kicad_pcb` 为纯文本 S-expression，diff 可读 | ⭐⭐⭐ 专业版工程文件为 JSON，可 diff 但有大量自动 UUID 噪音 | ⭐⭐⭐⭐ 生成脚本本身可 diff |
| **打样链路** | 需自行导出 Gerber 上传嘉立创/其他厂 | **原生对接嘉立创，一键下单**，最顺 | 同路线 A |
| **学习成本** | 中（KiCad 界面 + 建库） | **低**（主人已在用，桌面有快捷方式） | **高**（需写脚本 + 仍需学 EDA） |
| **主要风险** | 建库耗时最长，模组类元件容易画错引脚 | 4 层板层叠与阻抗控制不如 KiCad 直观；导出 KiCad 格式不完美 | 生成原理图可读性差，**不适合放进论文附录**；无法省掉 PCB 布线 |
| **适配本项目的额外优势** | `modbus-diag.kicad_pro` 已预设 `Default`/`Power`/`RS485` 三个网络类和设计规则，**可直接复用**，只需修正 C8 的 0.3mm 线宽 | 库覆盖最全，**BOM 缺口（交付物②）可顺带补齐** | 若主人的毕设要求「可复现的自动化设计流程」，这是加分项 |
| **适配本项目的额外劣势** | 需要新建 `modbus-diag.pretty` 里的全部封装 | 需把已有的 `.kicad_pro` 设计规则手工搬到立创EDA | 与「推 git 每版」要求结合时，需额外维护生成脚本与产物的一致性 |

### 6.2 路线 C 的补充说明（为什么不推荐作为主路线）

「由网表生成」听起来最省事，但实际只解决了**原理图录入**这一个环节：
- PCB 布局布线**无法自动生成**，仍要人工完成——占整个硬件工作量的 60% 以上。
- 自动生成的原理图是机器布局，**不适合作为论文插图**（第 4 章需要可读的电路图）。
- 需要额外维护「代码 → 网表」脚本与产物的一致性，反而增加 git 管理负担。
- **但它有一个有价值的用法**：可以把 `app_config.h` 的引脚宏作为**单一事实来源**，用脚本导出「引脚 ↔ 网络」对照表，作为**原理图人工连线时的检查清单**，防止 B10/B11 这类引脚选错。这是低成本、高收益的用法。

### 6.3 推荐路线

> ## 推荐：**路线 B（立创EDA）为主，辅以路线 A 的设计规则复用**
>
> ### 理由（按权重排序）
> 1. **主人已在用立创EDA**（桌面有快捷方式），学习成本最低、出错概率最小。
> 2. **直接补齐 BOM 缺口**——立创EDA 的元件库天然绑定「符号 + 封装 + 商城型号 + 价格」，画完原理图即得可下单 BOM，一举解决交付物②。
> 3. **打样链路最短**——嘉立创一键下单，4 层板 80×60mm 属常规工艺，成本与交期可控。
> 4. **元件命中率高**——本设计 90% 以上是常用料（ESP32-S3-WROOM-1、MAX3485、AMS1117-3.3、CH340C、SMBJ6.5CA、BAT54S、LM358、2N7002、XPT2046、ILI9341），立创商城均有现成符号与封装，无需自建库。
> 5. **`hardware/modbus-diag.kicad_pro` 的价值仍可保留**——把其中已预设的 `Default` / `Power` / `RS485` 三个网络类的参数（clearance / track_width / via）手工搬到立创EDA 的设计规则中，避免从零设定。
>
> ### 对「每版推 git」的落地策略
> 立创EDA 专业版工程文件是 JSON，直接入库 diff 噪音较大。建议：
> - 工程源文件（`.epro` 等）**照常入库**，作为版本基线；
> - 每次推版**同时导出并入库** 3 个产物快照：`原理图.pdf`、`PCB.pdf`、`BOM.csv`；
> - 这样 git 历史里能看到「每版」的可读差异，符合主人「原理图/PCB/代码/BOM，每版推 git」的原话要求。
>
> ### 若必须用 KiCad（备选：路线 A）
> 触发条件：学校/导师明确要求 KiCad，或主人希望 `.kicad_sch`/`.kicad_pcb` 的**纯文本 diff**（这对「每版推 git」确实是最优解）。
> 此时的工作重点是**建库**：优先从 SnapEDA / 立创商城 / Espressif 官方 KiCad 库下载 ESP32-S3-WROOM-1、ILI9341 模组、XPT2046、Type-C 座的符号与封装，放入 `hardware/modbus-diag.pretty`，可把建库时间从十余小时压缩到 2~3 小时。

### 6.4 执行顺序建议（无论选哪条路线）

| 阶段 | 任务 | 产出 | 前置依赖 |
|---|---|---|---|
| **P0** | 解决 **A1**（GPIO4 冲突）与 **A2**（按键上拉） | 修改 `app_config.h:25/38` + 论文 `:89/:113/:121` | 无——**必须先做** |
| **P1** | 解决 B8/B9/B10/B11 等会「画错就报废」的项（12MHz 晶振、CC 下拉、strapping 引脚） | 引脚与物料清单定稿 | P0 |
| **P2** | 画原理图（按 §2.1 引脚表 + §3 论文参数） | `.kicad_sch` / 立创EDA 原理图 | P1 |
| **P3** | 从原理图**导出 BOM**，与本报告 §5 的 CSV 交叉核对 | 正式 BOM | P2 |
| **P4** | 画 PCB（4 层、80×60mm、按论文 4.7 的层叠/阻抗/净空要求） | `.kicad_pcb` / 立创EDA PCB | P3 |
| **P5** | DRC + Gerber 导出 + 打样 + 焊接 | Gerber、实物 | P4 |
| **P6** | 按实物实测回填论文第 4 章与第 6/7 章（含 B1 采样率、C2 PSRAM 用途） | 论文修订 | P5 |

---

## 7. 附：本报告的证据索引

| 结论 | 主要证据 |
|---|---|
| 引脚分配 | `components/common_config/app_config.h:3-44` |
| TFT SPI 初始化 | `components/display/tft_driver.c:141-186` |
| 按键扫描 | `components/input/key_scan.c:13-82` |
| RS-485 DE 控制与 UART | `components/modbus_core/modbus_master.c:28-36, 65-95` |
| ADC 连续采样 | `components/waveform/adc_sampler.c:40-113` |
| 信号处理算法 | `components/waveform/signal_process.h:4-16` |
| 触摸未实现 | `components/input/input_event.c:3`；`app_config.h:15-19` 零引用 |
| 任务核心分配 | `main/main.c:112-172`；`components/input/key_scan.c:78` |
| Flash / PSRAM / 分区 | `sdkconfig.defaults:7-18`；`partitions.csv:2-5` |
| 外部依赖 | `dependencies.lock:1-20`；`components/wifi_service/idf_component.yml:1-2` |
| 空 KiCad 工程 | `hardware/modbus-diag.kicad_pro`（`sheets: []`）；`hardware/modbus-diag.pretty/`（空） |
| 论文硬件规格 | `论文/第4章_硬件设计.md:1-152`（与 `毕业论文_完整版.md:553-707` 内容一致） |
| 论文软件-硬件交叉描述 | `毕业论文_完整版.md:337-343, 411, 415, 858, 864, 1342` |

---

*报告生成时间：2026-09-15 · 全程只读，未修改 `modbus-diag` 仓库任何文件，未执行 git 操作。*
