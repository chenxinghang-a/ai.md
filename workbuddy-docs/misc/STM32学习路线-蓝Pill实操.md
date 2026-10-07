# STM32 学习路线（蓝 Pill 实操版）

> 对象：cxx（电气工程本科 + 独立开发者）
> 硬件：蓝 Pill（STM32F103C8T6，LQFP48，64KB Flash / 20KB SRAM）+ ST-Link V2
> 主机：Win11 / RTX 5060 8GB / 16GB RAM
> 目标方向：PCB 设计、无人机飞控 → 就业目标大疆
> 每周预算：8–10 小时
> 版本：v1.0 / 2026-09-15

---

## 目录

| 章节 | 内容 | 建议阅读顺序 |
|---|---|---|
| 1 | 起点诊断（你已会 / 真空白） | 先读 |
| 2 | 工具链选型（给结论） | 先读 |
| 3 | 分阶段实操路线（阶段 0–6） | 核心，边做边读 |
| 4 | ESP32 → STM32 坑清单 | 阶段 0 之前通读一遍，之后当字典查 |
| 5 | 蓝 Pill 具体约束 | 阶段 0 之前读 |
| 6 | 与 PCB / 飞控 / 大疆的衔接 | 阶段 5 之后再读 |
| 7 | 周计划表（16 周） | 先读 |
| 附录 A | HAL 函数 / 寄存器速查 | 随时查 |
| 附录 B | 「需自行核实」清单 | 用前确认 |

---

## 1. 起点诊断

### 1.1 结论先行

你的 ESP32-S3 毕设（Modbus 诊断工具：FreeRTOS 多任务 + SPI ILI9341 + ADC 连续采样 + DMA + RS-485 + UART + WiFi + SPIFFS + ESP-IDF 组件化）**已经覆盖了 STM32 学习路线里 60% 的「概念层」内容**。

所以：

- **不要**从「点灯」开始按部就班学概念。你缺的是 **ST 生态的具体 API、工具链、和 Cortex-M3 裸机的底层细节**，不是「什么是中断」「什么是 DMA」。
- **要**把重心放在：HAL 函数怎么写、CubeMX 怎么配、NVIC 怎么分组、链接脚本怎么改、跑飞了怎么查。
- 阶段 0 只花 **2–3 小时**（不是一周）。阶段 2、4、5 可以压缩 50%。

### 1.2 你已经会的（可直接迁移）

| 能力 | ESP32-S3 上你用什么 | STM32 上对应什么 | 迁移难度 |
|---|---|---|---|
| GPIO 输出/输入 | `gpio_set_direction` / `gpio_set_level` | `HAL_GPIO_Init` / `HAL_GPIO_WritePin` | ★ 极低 |
| 外部中断 | `gpio_install_isr_service` + `gpio_isr_handler_add` | EXTI + `HAL_GPIO_EXTI_Callback` + NVIC 使能 | ★★ 低（多一层 NVIC） |
| 定时器 | `esp_timer` / GPTimer | `TIMx` + `HAL_TIM_Base_Init` | ★★ 低 |
| PWM | LEDC | `HAL_TIM_PWM_Start` + `__HAL_TIM_SET_COMPARE` | ★ 极低 |
| UART | `uart_driver_install` + `uart_read_bytes` | `HAL_UART_Init` + `HAL_UART_Receive_DMA` | ★★ 低 |
| I2C | 新版 `i2c_master_*` 驱动 | `HAL_I2C_Mem_Read/Write` | ★★ 低 |
| SPI | `spi_bus_initialize` + `spi_device_transmit` | `HAL_SPI_Transmit/Receive` | ★★ 低 |
| ADC + DMA | `adc_continuous_*` | `HAL_ADC_Start_DMA` + DMA1 | ★★ 低 |
| RTOS 多任务 | FreeRTOS（ESP-IDF 分支） | 原生 FreeRTOS 或 CMSIS-RTOS v2 | ★★★ 中 |
| 队列/信号量/互斥量 | `xQueueCreate` / `xSemaphoreTake` | 同名 API（原生）或 `osMessageQueue*` | ★★ 低 |
| 看数据手册 | 会 | 会 | — |
| C 语言 | 能写 | 能写 | — |
| 硬件设计 | 立创EDA + 焊接 | 一样 | — |
| 调试思维 | 会 | 会 | — |

### 1.3 你的真空白 / 半空白

**这些是 ESP-IDF 帮你藏起来、STM32 上必须自己面对的东西：**

| 空白项 | 为什么 ESP32 上没遇到 | 在 STM32 上什么时候会咬你 |
|---|---|---|
| **NVIC 优先级分组**（抢占/子优先级） | `esp_intr_alloc` 帮你封装了，ESP32 是固定 1 级抢占 + 3 级子优先 | 阶段 1 第一次写 EXTI；阶段 5 用 FreeRTOS 时直接死给你看 |
| **时钟树手配** | ESP32 主频基本固定 240MHz，`esp_pm` 管 | 阶段 0 配 HSE/PLL/APB 分频；APB1 超 36MHz 直接翻车 |
| **启动文件 / 链接脚本 / 内存布局** | ESP-IDF 的 CMake + 分区表完全抽象掉了 | 阶段 0 想改 stack 大小；阶段 5 发现 20KB RAM 不够 |
| **DMA 请求映射（F1 无 DMAMUX）** | ESP32 的 GDMA 通道可自由连任意外设 | 阶段 2/4 配 DMA 时：**通道和外设是硬连线的，配错就是没反应** |
| **寄存器级操作** | ESP-IDF 的 `driver` 层比较厚 | HAL 是薄封装，出错必须回 RM0008 看寄存器 |
| **单核 RTOS 的调度陷阱** | ESP32 双核，`xTaskCreatePinnedToCore` 帮你分担 | 阶段 5：所有任务抢一个核，优先级设计错了直接饿死 |
| **栈大小单位** | ESP-IDF 的 `xTaskCreate` 栈深度单位是**字节** | 原生 FreeRTOS 是**字（word）**，差 4 倍 |
| **SWD 调试与复位行为** | `idf.py monitor` 看日志就够了 | 阶段 0 之后就得学会断点、看寄存器、单步进 ISR |
| **STM32F1 的 I2C 硬件 errata** | ESP32 的 I2C 外设很干净 | 阶段 3：MPU6050 读着读着 BUSY 标志卡死 |
| **Flash 等待周期（Latency）** | 自动的 | 阶段 0：72MHz 下不设 2 个 wait state，跑起来随机崩 |

### 1.4 你**不需要**再学的东西（跳过）

- 什么是中断 / 什么是 DMA / 什么是 RTOS 任务 —— 你已经懂了
- 什么是 SPI 时序 / I2C 时序 —— 你驱动过 ILI9341 和 RS-485，懂了
- 怎么读数据手册 —— 你会
- 什么是环形缓冲 / 双缓冲 —— 你做过 ADC 连续采样

**唯一需要重新学的**：这些概念在 **ST 的 HAL + CubeMX + 裸机 Cortex-M3** 里的**具体写法**。

---

## 2. 工具链选型

### 2.1 四选一对比

| 维度 | STM32CubeIDE（已装） | Keil MDK | PlatformIO | 纯 Makefile + arm-gcc |
|---|---|---|---|---|
| **授权** | 免费，无代码大小限制，ST 官方 | MDK-Community Edition 非商业免费（**需自行核实当前条款**）；商业版按年订阅；旧版 MDK-Lite 限 32KB | 免费开源 | 免费开源 |
| **Win11 体验** | 好（基于 Eclipse，略重，1.5–2GB 内存） | 最好（原生 Windows，启动快，编辑器老） | 好（VS Code） | 中（要自己配） |
| **跨平台** | Win / Linux / macOS | **仅 Windows** | Win / Linux / macOS | 全平台 |
| **编译器** | arm-none-eabi-gcc（GCC） | ARM Compiler 6（Clang 派生）或 AC5 | arm-none-eabi-gcc | arm-none-eabi-gcc |
| **代码生成** | **CubeMX 集成**，图形配引脚/时钟/中间件 | 需装 CubeMX 单独生成，或手动 | 需手动写 CubeMX 或依赖社区框架 | 全手写 |
| **调试** | GDB + ST-Link，体验好，有寄存器视图 | **业界最好**的调试器（uVision），逻辑分析仪/Event Recorder | GDB + OpenOCD，可用，但配置麻烦 | GDB 命令行，最灵活最痛苦 |
| **代码可移植性** | **高**（标准 GCC + HAL + Makefile/CMake） | **低**（ARMCC 特有语法、`__weak` 行为差异、pack 依赖） | 高 | 最高 |
| **国内教程/资料** | 极多（正点原子/野火都主推） | 极多（老牌教程基本都是 Keil） | 中等 | 少 |
| **CI/自动化** | 支持 headless build（`headless-build.bat`，**路径与版本相关，需自行核实**） | 命令行构建可用（`UV4.exe -b`） | `pio run` 一行搞定 | `make` |
| **坑** | Eclipse 偶尔卡；索引重建慢；`.ioc` 与代码同步冲突 | 授权复杂；ARMCC 与 GCC 不兼容；32KB 限制（旧 Lite 版）；Windows only；工程文件是二进制 `.uvprojx`，Git diff 难看 | STM32 支持是社区维护（`platform = ststm32`），HAL 版本更新滞后；CubeMX 生成的 `.ioc` 和 PIO 的 `platformio.ini` 会打架 | 上手成本高；要自己维护启动文件、链接脚本、CMSIS |
| **大疆/飞控圈实际用什么** | 开源飞控（Betaflight/ArduPilot/PX4）**全部用 GCC + Makefile/CMake** | RoboMaster 官方例程同时提供 Keil 和 CubeIDE 工程 | 少 | **开源飞控主流** |

### 2.2 结论（给你的推荐）

**主用：STM32CubeIDE（你已装）**
**辅用：PlatformIO（VS Code 里跑同一套 HAL 代码，做 CI 和快速试验）**
**备用：纯 Makefile + arm-gcc（第 6 阶段做飞控时再上）**
**Keil：只用来读别人的老工程，不新建工程**

理由（按重要性排序）：

1. **CubeMX 集成是决定性的。** STM32 的学习成本有 70% 在「配时钟树 + 配引脚复用 + 配 NVIC + 配 DMA 请求映射」。CubeMX 把这些做成可视化，你出错时能立刻看到冲突（比如 PA13 被占导致 SWD 挂了）。Keil 没有这个。
2. **你已经有 GCC 生态的习惯。** ESP-IDF 是 CMake + GCC，CubeIDE 是 Makefile + GCC。从 IDF 过来，GCC 的工具链行为（`-specs=nano.specs`、`-mcpu=cortex-m3`、链接脚本语法）是通的。换 Keil 的 ARMCC 等于重新学一套编译器怪癖。
3. **跨平台 + 可移植。** 你以后要在 Linux 上跑 CI、要给别人分享工程、要上 GitHub，Keil 的二进制 `.uvprojx` 是灾难。
4. **飞控方向最终一定是 GCC。** 大疆 RoboMaster 开发板 A 型主控是 **STM32F427IIH6**（已核实），官方 SDK 提供 Keil 与 CubeIDE 两套工程。而 Betaflight / ArduPilot / PX4 全部是 GCC。早点在 GCC 上扎根。

**明确不建议**：把 Keil 当主力。除非你以后进的公司强制用 Keil，否则学它纯属浪费时间。

### 2.3 Win11 环境配置清单

| 步骤 | 具体操作 | 验证 |
|---|---|---|
| 1 | CubeIDE 里 `Help > Manage embedded software packages`，安装 **STM32Cube MCU Package for STM32F1 Series**（CubeF1） | 列表里 F1 显示已安装版本号 |
| 2 | 装 ST-Link 驱动（CubeIDE 自带，或单独装 `ST-Link_V2_USBdriver`） | 设备管理器出现 `STMicroelectronics STLink dongle` |
| 3 | 检查 ST-Link 固件：运行 `ST-LinkUpgrade.exe`（在 CubeIDE 安装目录的 `STM32Cube/Repository/...` 或独立下载） | 显示固件版本，能升级到最新 |
| 4 | 准备 USB-TTL 串口模块（CH340 / CP2102），接蓝 Pill 的 PA9(TX)/PA10(RX)/GND | 用串口助手能看到 115200 打印 |
| 5 | （可选）VS Code + PlatformIO 插件，`board = bluepill_f103c8`，`debug_tool = stlink` | `pio run` 能编译 |
| 6 | （可选）独立安装 `arm-none-eabi-gcc` 与 `make`（用 MSYS2 或 xPack），为阶段 6 的纯 Makefile 做准备 | `arm-none-eabi-gcc --version` |

**CubeIDE 关键设置（一定要改）：**

| 位置 | 改成什么 | 为什么 |
|---|---|---|
| `Project > Properties > C/C++ Build > Settings > MCU Post build outputs` | 勾选 **Convert to Intel Hex file** | 方便用 STM32CubeProgrammer 烧录 |
| 同上 > `MCU G++/GCC Compiler > Optimization` | Debug 用 `-O0`，Release 用 `-Og` 或 `-Os` | `-O2` 下断点会跳，单步会乱 |
| `Run > Debug Configurations > Debugger` | Interface: **SWD**，Frequency: 4MHz，勾选 **Reset behaviour: Connect under reset** | 防止程序进入低功耗或跑飞后连不上 |
| `Window > Preferences > C/C++ > Indexer` | 关掉 "Index source files not included in the build" | 大幅降低卡顿 |
| `Project > Properties > C/C++ Build > Settings > Tool Settings` | 若用 `printf("%f")`，加链接参数 `-u _printf_float` | nano.specs 默认禁用浮点 printf |

---

## 3. 分阶段实操路线

> **通用约定**：每个阶段的「新建工程」流程统一为
> `File > New > STM32 Project > 搜索 "STM32F103C8Tx" > 选 STM32F103C8Tx > 工程名 > 语言选 C > Finish`
> 生成后立刻做三件事：① 在 `Project Manager > Code Generator` 勾选 **"Generate peripheral initialization as a pair of .c/.h files per peripheral"**；② 勾选 **"Keep User Code when re-generating"**；③ 时钟配置页把 `SYS > Debug` 设为 **Serial Wire**（否则 PA13/PA14 被当 GPIO，SWD 失联）。

---

### 阶段 0：环境跑通（预计 2–3 小时，**不可跳过但可极速通过**）

#### 目标

确认「CubeMX 配 → CubeIDE 编译 → ST-Link 下载 → LED 闪 + 串口打印」这条链路完全打通。

#### 硬件连接

| 蓝 Pill 引脚 | 接到 |
|---|---|
| 3.3V | ST-Link 3.3V |
| GND | ST-Link GND |
| PA13 (SWDIO) | ST-Link SWDIO |
| PA14 (SWCLK) | ST-Link SWCLK |
| PA9 (USART1_TX) | USB-TTL 的 **RX** |
| PA10 (USART1_RX) | USB-TTL 的 **TX** |
| GND | USB-TTL GND（**必须共地**） |

> 蓝 Pill 板载 LED 在 **PC13**，**低电平点亮**（LED 阳极接 3.3V，阴极经电阻到 PC13）。

#### CubeMX 配置

| 配置项 | 值 | 说明 |
|---|---|---|
| `System Core > RCC > High Speed Clock (HSE)` | **Crystal/Ceramic Resonator** | 蓝 Pill 有 8MHz 晶振 |
| `System Core > SYS > Debug` | **Serial Wire** | 关键！否则 SWD 失联 |
| `System Core > SYS > Timebase Source` | **SysTick**（裸机阶段） | 阶段 5 上 FreeRTOS 时可改成 TIM2 |
| `Connectivity > USART1 > Mode` | **Asynchronous** | PA9/PA10 自动分配 |
| `USART1 > Parameter Settings` | Baud 115200，8 bits，No parity，1 stop | 常见串口助手默认 |
| `GPIO > PC13` | **GPIO_Output**，Output Push Pull，No pull，Low speed，Initial: **High** | 初始 High = LED 灭 |
| `Clock Configuration` 页 | HSE 8MHz → **PLL Mul x9** → SYSCLK **72MHz** → AHB /1 → APB1 /2 (36MHz) → APB2 /1 (72MHz) → ADC /6 (12MHz) → USB /1.5 (48MHz) | 见下方「时钟树」 |
| `Clock Configuration > Flash Latency` | 选 **2 WS**（CubeMX 通常自动，但要自己确认） | 48–72MHz 必须 2 个等待周期 |

**时钟树路径（CubeMX 里从右往左点）：**

```
HSE 8MHz
  → PLL Source: HSE
  → PLLMUL: x9
  → PLLCLK = 72MHz
  → SYSCLK Source: PLLCLK  = 72MHz
  → AHB Prescaler: /1       = HCLK 72MHz
  → APB1 Prescaler: /2      = PCLK1 36MHz   (F103 APB1 上限 36MHz)
  → APB2 Prescaler: /1      = PCLK2 72MHz   (F103 APB2 上限 72MHz)
  → ADC Prescaler: /6       = ADCCLK 12MHz  (上限 14MHz)
  → USB Prescaler: /1.5     = 48MHz
  → Flash Latency: 2 WS
```

#### 要写的代码

**① LED 闪烁（`main.c` 的 `while (1)` 里）：**

```c
/* USER CODE BEGIN WHILE */
while (1)
{
    HAL_GPIO_TogglePin(GPIOC, GPIO_PIN_13);
    HAL_Delay(500);   /* SysTick 提供，1ms 基准 */
    /* USER CODE END WHILE */
    /* USER CODE BEGIN 3 */
}
/* USER CODE END 3 */
```

**② printf 重定向到 USART1**（放在 `main.c` 的 `/* USER CODE BEGIN 4 */` 区域）：

```c
/* USER CODE BEGIN 4 */
#include <stdio.h>

/* CubeIDE 的 syscalls.c 里 _write() 会调用 __io_putchar()，
   所以只要实现这个弱符号即可让 printf 走串口。 */
int __io_putchar(int ch)
{
    uint8_t c = (uint8_t)ch;
    HAL_UART_Transmit(&huart1, &c, 1, HAL_MAX_DELAY);
    return ch;
}

/* 备用方案：如果 __io_putchar 没生效，直接实现 _write（注释掉上面那个再启用） */
/*
int _write(int file, char *ptr, int len)
{
    (void)file;
    HAL_UART_Transmit(&huart1, (uint8_t *)ptr, (uint16_t)len, HAL_MAX_DELAY);
    return len;
}
*/
/* USER CODE END 4 */
```

**③ 关掉 stdout 缓冲**（否则 printf 不带 `\n` 时不输出，在 `main()` 开头 `MX_USART1_UART_Init()` 之后调用）：

```c
/* USER CODE BEGIN 2 */
setvbuf(stdout, NULL, _IONBF, 0);   /* 需要 #include <stdio.h> */
printf("SYSCLK = %lu Hz\r\n", (unsigned long)HAL_RCC_GetSysClockFreq());
/* USER CODE END 2 */
```

#### 验证方法（看到什么算成功）

| 现象 | 说明 |
|---|---|
| CubeIDE Console 里 `Build Finished. 0 errors, 0 warnings` | 编译链 OK |
| Debug 能连上，能停在 `main()` 第一行 | ST-Link + SWD OK |
| 点 Run，PC13 上的蓝灯以 1Hz 闪烁 | GPIO + SysTick + 时钟树 OK |
| 串口助手（115200）收到 `SYSCLK = 72000000 Hz` | 时钟树配置正确 + UART + printf 重定向 OK |

> 打印出来的必须是 **72000000**。如果是 8000000，说明 PLL 没生效 —— 90% 是 HSE 没启振。

#### 常见坑

| 坑 | 现象 | 原因 / 解法 |
|---|---|---|
| **SWD 失联** | CubeIDE 报 `No STM32 target found` 或 `Target not responding` | ① SYS Debug 没设成 Serial Wire，PA13/PA14 被复用成 GPIO → 用 **BOOT0=1** 启动进入 System memory bootloader 后重烧，或按住 NRST 点 Debug（Connect under reset）② 蓝 Pill 的 3.3V 没供上（ST-Link 的 3.3V 输出电流有限，USB 口供电更稳） |
| **HSE 起振失败** | `HAL_RCC_OscConfig()` 返回错误，程序卡在 `Error_Handler()` 的 `while(1)` | 蓝 Pill 部分批次的 8MHz 晶振负载电容不对；或 HSE_VALUE 不是 8000000。检查 `stm32f1xx_hal_conf.h` 里的 `HSE_VALUE`，以及 `system_stm32f1xx.c` 的 `HSE_VALUE` |
| **串口乱码** | 收到 `烫烫烫` 之类 | ① 波特率不匹配 ② 系统时钟不是 72MHz 导致 UART 分频算错 ③ USB-TTL 的 GND 没接 |
| **printf 无输出** | 灯闪但串口没东西 | ① stdout 行缓冲（用 `setvbuf` 关掉，或每次都加 `\r\n`）② 没有 `#include <stdio.h>` ③ 链接时 `_write` 被 nano.specs 的弱定义抢走（改用 `__io_putchar`） |
| **PC13 驱动能力** | 接了大电流负载后 MCU 异常 | PC13/PC14/PC15 属于 **VBAT 供电域**，datasheet 规定单脚输出电流 **最大 3mA**。只接 LED，别驱动蜂鸣器/继电器 |
| **BOOT0 跳线** | 烧完程序不跑 | 蓝 Pill 的 BOOT0 跳线帽要在 **0 位**（靠 0 的那侧）才是从 Flash 启动 |

---

### 阶段 1：GPIO / EXTI 中断 / 定时器（预计 8–12 小时）

#### 1.1 GPIO 进阶

**目标**：理解 HAL 的 GPIO 初始化结构体，掌握上拉/下拉/开漏的适用场景。

**核心代码：**

```c
/* 手动初始化一个 GPIO（不用 CubeMX 生成的那套） */
static void gpio_manual_init(void)
{
    GPIO_InitTypeDef gi = {0};

    __HAL_RCC_GPIOB_CLK_ENABLE();      /* 必须先开时钟！否则写寄存器无效 */

    gi.Pin   = GPIO_PIN_12;            /* PB12 */
    gi.Mode  = GPIO_MODE_OUTPUT_PP;    /* 推挽输出 */
    gi.Pull  = GPIO_NOPULL;
    gi.Speed = GPIO_SPEED_FREQ_LOW;    /* F1 有 LOW / MEDIUM / HIGH 三档 */
    HAL_GPIO_Init(GPIOB, &gi);

    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, GPIO_PIN_SET);   /* 输出高 */
}
```

**F1 的 GPIO Mode 枚举**（`GPIO_MODE_*`，`stm32f1xx_hal_gpio.h`）：

| 宏 | 用途 |
|---|---|
| `GPIO_MODE_INPUT` | 浮空/上拉/下拉输入（由 `Pull` 决定） |
| `GPIO_MODE_OUTPUT_PP` | 推挽输出 |
| `GPIO_MODE_OUTPUT_OD` | 开漏输出（**I2C 软件模拟、多机共享总线**必须用这个） |
| `GPIO_MODE_AF_PP` | 复用推挽（SPI SCK/MOSI、USART TX、TIM PWM 输出） |
| `GPIO_MODE_AF_OD` | 复用开漏（I2C 硬件外设的 SCL/SDA、CAN） |
| `GPIO_MODE_ANALOG` | 模拟输入（ADC 通道、低功耗） |
| `GPIO_MODE_IT_RISING` / `_FALLING` / `_RISING_FALLING` | 外部中断 |
| `GPIO_MODE_EVT_*` | 事件模式（不产生中断，只唤醒） |

**验证**：PB12 输出方波，示波器/逻辑分析仪看到电平翻转；或 PB12 接 LED 闪烁。

**常见坑**：
- **忘开外设时钟**（`__HAL_RCC_GPIOx_CLK_ENABLE()`）—— 最常见，写寄存器毫无反应且不报错。
- F1 的 `GPIO_SPEED_FREQ_LOW` 对应 2MHz，`MEDIUM` = 10MHz，`HIGH` = 50MHz。做 SPI/I2C 高速时必须给 `HIGH`。

#### 1.2 EXTI 外部中断

**CubeMX 配置**：

| 配置项 | 值 |
|---|---|
| 选一个按键引脚（比如 PB0） | `GPIO_Input`，Pull: **Pull-up**（按键另一端接 GND） |
| `GPIO > PB0 > GPIO mode` | **External Interrupt Mode with Falling edge trigger detection** |
| `NVIC > EXTI line0 interrupt` | **Enabled**，Preemption Priority 填 **2**，Sub Priority 填 0 |
| `NVIC > Code generation` | 勾选 **"Generate IRQ handler"**（否则要自己写 `EXTI0_IRQHandler`） |

**代码：**

```c
/* main.c 的 USER CODE BEGIN 4 */
volatile uint32_t g_btn_count = 0;
volatile uint32_t g_last_tick = 0;

void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
    if (GPIO_Pin == GPIO_PIN_0)   /* 注意是 GPIO_PIN_0，不是 Pin 编号 */
    {
        uint32_t now = HAL_GetTick();

        /* 软件消抖：20ms 内的抖动丢弃。注意 HAL_GetTick 在中断里可用，
           但它依赖 SysTick 中断，且 SysTick 优先级通常高于 EXTI，
           所以这个值是可用的。 */
        if ((now - g_last_tick) > 20U)
        {
            g_last_tick = now;
            g_btn_count++;
        }
    }
}
```

**CubeMX 自动生成的 `stm32f1xx_it.c` 长这样（你要知道它做了什么）：**

```c
void EXTI0_IRQHandler(void)
{
    HAL_GPIO_EXTI_IRQHandler(GPIO_PIN_0);   /* 清标志 + 回调 HAL_GPIO_EXTI_Callback */
}
```

**验证**：按一下按键，`g_btn_count` 加 1。在 Debug 的 Expressions 里加 `g_btn_count`，用 Live Expressions（CubeIDE 有）实时看。

**常见坑**：

| 坑 | 说明 |
|---|---|
| **回调里用 `HAL_Delay()`** | **绝对禁止**。`HAL_Delay` 靠 SysTick 中断，而 SysTick 优先级可能低于 EXTI，会造成死锁。中断里只能做「置标志 / 给信号量 / 存数据」 |
| **回调里 `printf`** | `HAL_UART_Transmit` 是阻塞的，在中断里跑几十微秒到几毫秒，会拖垮系统。要么在中断里塞进环形缓冲、主循环里发；要么用 DMA |
| **回调函数名写错** | `HAL_GPIO_EXTI_Callback` 是 `__weak` 的，你在 `main.c` 里重写一个**同名同签名**的函数就行。写成 `HAL_GPIO_EXTI_Callback(uint16_t)` 漏了 `void` 参数列表在某些编译器下不报错但不覆盖 |
| **F1 的 EXTI 线共享** | PA0/PB0/PC0… 共享 **EXTI0**。同一时刻只能有一根引脚用 EXTI0。CubeMX 会在你同时选 PA0 和 PB0 时报警告 |
| **F1 的中断向量名** | 不像 F4 有 `EXTI0_IRQHandler` 统一，F1 是分开的：`EXTI0_IRQHandler`、`EXTI1_IRQHandler`、`EXTI2_IRQHandler`、`EXTI3_IRQHandler`、`EXTI4_IRQHandler`、**`EXTI9_5_IRQHandler`**（5–9 共用）、**`EXTI15_10_IRQHandler`**（10–15 共用） |
| **中断优先级没使能** | 光在 CubeMX 里选模式不够，必须 `NVIC > Enable`。或者手动 `HAL_NVIC_SetPriority(EXTI0_IRQn, 2, 0); HAL_NVIC_EnableIRQ(EXTI0_IRQn);` |

#### 1.3 定时器

**蓝 Pill 上可用的定时器（这是重点，F103C8 是 medium-density）**：

| 定时器 | 类型 | 位宽 | 主要用途 | 蓝 Pill 上有吗 |
|---|---|---|---|---|
| TIM1 | 高级控制 | 16-bit | 互补 PWM、死区、刹车（电机/无刷驱动） | ✅ |
| TIM2 | 通用 | 16-bit | PWM、输入捕获、编码器、定时中断 | ✅ |
| TIM3 | 通用 | 16-bit | 同上 | ✅ |
| TIM4 | 通用 | 16-bit | 同上 | ✅ |
| TIM5/6/7/8 | 通用/基本 | 16-bit | — | ❌ **F103C8 没有**（high-density 才有） |
| SysTick | 内核 | 24-bit | HAL 的 1ms 基准 | ✅ |
| IWDG / WWDG | 看门狗 | 12/7-bit | 独立/窗口看门狗 | ✅ |

**TIM2 的引脚映射（F103C8）**：

| 通道 | 引脚 |
|---|---|
| TIM2_CH1 | PA0 |
| TIM2_CH2 | PA1 |
| TIM2_CH3 | PA2 |
| TIM2_CH4 | PA3 |

**TIM3**：CH1=PA6, CH2=PA7, CH3=PB0, CH4=PB1
**TIM4**：CH1=PB6, CH2=PB7, CH3=PB8, CH4=PB9
**TIM1**：CH1=PA8, CH1N=PB13, CH2=PA9, CH2N=PB14, CH3=PA10, CH3N=PB15, CH4=PA11

> ⚠️ **注意冲突**：TIM1_CH2 是 PA9，而 PA9 是 USART1_TX。同一个工程里不能同时用。CubeMX 会提示。

**① 定时中断（1kHz）**

CubeMX：`Timers > TIM2 > Clock Source: Internal Clock`，`Parameter Settings`：
- `Prescaler (PSC - 16 bits value)` = **71**（72MHz / 72 = 1MHz 计数频率）
- `Counter Period (AutoReload Register - 16 bits value)` = **999**（1MHz / 1000 = 1kHz）
- `NVIC Settings > TIM2 global interrupt` = Enabled，Preemption Priority = **3**

```c
/* USER CODE BEGIN 2 */
HAL_TIM_Base_Start_IT(&htim2);   /* 注意是 _IT，不是 HAL_TIM_Base_Start */
/* USER CODE END 2 */

/* USER CODE BEGIN 4 */
volatile uint32_t g_tim2_tick = 0;

void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
{
    if (htim->Instance == TIM2)
    {
        g_tim2_tick++;
    }
}
/* USER CODE END 4 */
```

**验证**：`g_tim2_tick` 每秒增加 1000。用 `HAL_GetTick()` 做基准测：`if (g_tim2_tick - t0 >= 1000) { t0 = g_tim2_tick; HAL_GPIO_TogglePin(...); }`，LED 应该 1Hz 闪。

**② PWM 输出（呼吸灯）**

CubeMX：`Timers > TIM3 > Channel3: PWM Generation CH3`（对应 PB0）
- `PSC` = 71 → 1MHz
- `ARR` = 999 → **1kHz PWM**
- `Pulse` = 0（初始占空比）
- `CH Polarity` = High

```c
/* USER CODE BEGIN 2 */
HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_3);
/* USER CODE END 2 */

/* USER CODE BEGIN WHILE */
uint16_t duty = 0;
int8_t   dir  = 1;
while (1)
{
    duty = (uint16_t)(duty + dir * 5);
    if (duty >= 1000U) { duty = 1000U; dir = -1; }
    if (duty == 0U)    { dir = 1; }

    __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_3, duty);
    HAL_Delay(5);
    /* USER CODE END WHILE */
}
```

**验证**：PB0 接 LED（串 1kΩ 电阻），LED 呼吸。示波器看到 1kHz 方波，占空比线性变化。

**③ 输入捕获（测脉冲宽度）**

CubeMX：`TIM3 > Channel1: Input Capture direct mode`（PA6），`PSC` = 71，`ARR` = 0xFFFF，`IC1 > Polarity Selection: Rising Edge`，`NVIC` 使能。

```c
volatile uint32_t g_pulse_us = 0;
static uint32_t  s_rise = 0;

void HAL_TIM_IC_CaptureCallback(TIM_HandleTypeDef *htim)
{
    if (htim->Instance == TIM3)
    {
        if (htim->Channel == HAL_TIM_ACTIVE_CHANNEL_1)
        {
            uint32_t now = HAL_TIM_ReadCapturedValue(htim, TIM_CHANNEL_1);

            /* 先读上升沿时间，再翻转极性等下降沿 */
            if (s_rise == 0U)
            {
                s_rise = now;
                __HAL_TIM_SET_CAPTUREPOLARITY(htim, TIM_CHANNEL_1, TIM_INPUTCHANNELPOLARITY_FALLING);
            }
            else
            {
                g_pulse_us = (now >= s_rise) ? (now - s_rise)
                                             : (0x10000U - s_rise + now);
                s_rise = 0U;
                __HAL_TIM_SET_CAPTUREPOLARITY(htim, TIM_CHANNEL_1, TIM_INPUTCHANNELPOLARITY_RISING);
            }
        }
    }
}
```

> ⚠️ `__HAL_TIM_SET_CAPTUREPOLARITY` 会同时改 `CCER` 的 CC1P 和 CC1NP 位，必须**在中断里、且关掉该通道的捕获中断之后**调用更安全。更稳妥的写法是用两个通道（CH1 上升沿 + CH2 下降沿，接同一根线）分别捕获。**这个细节建议自己实测验证。**

**④ 编码器模式（阶段 6 会用到）**

CubeMX：`TIM2 > Combined Channels: Encoder Mode`，PA0/PA1 接编码器 A/B 相，`PSC` = 0，`ARR` = 0xFFFF（或 65535）。

```c
HAL_TIM_Encoder_Start(&htim2, TIM_CHANNEL_ALL);
int32_t cnt = (int32_t)__HAL_TIM_GET_COUNTER(&htim2);
/* 注意：16 位计数器会溢出/下溢，需要自己处理成 32 位增量 */
```

**验证**：手转编码器，计数器跟着变。

**常见坑**：

| 坑 | 说明 |
|---|---|
| **PSC/ARR 搞反** | `f_pwm = f_clk / (PSC+1) / (ARR+1)`。PSC 是「分频到计数频率」，ARR 是「一个周期的计数个数」。注意 **PSC 和 ARR 都是 16 位**，ARR 最大 65535 |
| **忘开 PWM 的 GPIO 时钟** | CubeMX 会自动开，手写时别忘 |
| **高级定时器 TIM1 需要额外开主输出** | TIM1/TIM8 的互补输出需要 `__HAL_TIM_MOE_ENABLE(&htim1)`（Main Output Enable），否则 PWM 出不来。TIM2/3/4 不需要 |
| **`HAL_TIM_PeriodElapsedCallback` 里判断 `Instance`** | 多个定时器共用这一个回调，必须判断 `htim->Instance`，否则逻辑串台 |
| **ARR 改了但计数器不重置** | 运行中改 ARR，要配合 `__HAL_TIM_SET_AUTORELOAD` 并在下一个更新事件才生效 |
| **`HAL_TIM_Base_Start_IT` vs `HAL_TIM_Base_Start`** | 前者开中断，后者不开。忘了 `_IT` 就是「回调永远不触发」 |

---

### 阶段 2：串口 + DMA + 环形缓冲（预计 4–8 小时，**可压缩**）

> **你已会**：UART 收发、DMA、环形缓冲、不定长帧解析（Modbus RTU 你做过）。
> **本阶段唯一目标**：学会 **STM32 HAL 的具体写法**，尤其是 **F1 的 DMA 通道硬连线** 和 **IDLE 空闲中断**。

#### 2.1 为什么要用「DMA + IDLE 中断」

| 方案 | 问题 |
|---|---|
| `HAL_UART_Receive`（阻塞轮询） | 占满 CPU，只能收固定长度 |
| `HAL_UART_Receive_IT`（单字节中断） | 每收 1 字节进一次中断。115200bps 下约 87μs 一次中断，Modbus 帧长了就丢字节 |
| **`HAL_UART_Receive_DMA` + IDLE 中断** | DMA 后台搬运，一帧结束（总线空闲）触发一次 IDLE 中断，CPU 只在帧边界被唤醒。**这是工业通信的标准做法** |

#### 2.2 CubeMX 配置（关键：DMA 通道是硬连线的）

| 配置项 | 值 |
|---|---|
| `USART1 > Mode` | Asynchronous |
| `USART1 > Parameter Settings` | 115200 / 8 / N / 1 |
| `USART1 > DMA Settings > Add` | **USART1_RX**，Mode: **Circular**，Data Width: Byte/Byte，Priority: High |
| `USART1 > DMA Settings > Add` | **USART1_TX**，Mode: **Normal**，Data Width: Byte/Byte，Priority: Medium |
| `USART1 > NVIC Settings` | **USART1 global interrupt = Enabled**（IDLE 中断靠它） |

**F1 的 DMA 请求映射（RM0008 的 "DMA1 requests" 表，**这是必须记住的**）：**

| DMA1 通道 | 可服务的外设（部分） |
|---|---|
| Channel1 | **ADC1**、TIM2_CH3、TIM4_CH1 |
| Channel2 | **SPI1_RX**、USART3_TX、TIM1_CH1、TIM2_UP、TIM3_CH3 |
| Channel3 | **SPI1_TX**、USART3_RX、TIM1_CH2、TIM3_CH4、TIM3_UP |
| Channel4 | **USART1_TX**、SPI2_RX、I2C2_TX、TIM1_CH4、TIM4_CH2 |
| Channel5 | **USART1_RX**、SPI2_TX、I2C2_RX、TIM1_UP、TIM2_CH1、TIM4_CH3 |
| Channel6 | **USART2_RX**、I2C1_TX、TIM1_CH3、TIM3_CH1 |
| Channel7 | **USART2_TX**、I2C1_RX、TIM2_CH2、TIM2_CH4、TIM4_UP |

> ⚠️ **F1 没有 DMAMUX**（那是 F0/G0/G4/H7 才有的）。每个 DMA 通道能服务哪些外设是**芯片内部硬连线固定的**，改不了。
> 后果：**如果你同时要用 ADC1 + USART1_RX + SPI1_RX，会撞车**（ADC1 和 TIM2_CH3 抢 Channel1，SPI1_RX 独占 Channel2，USART1_RX 独占 Channel5 —— 这个组合是 OK 的）。
> 真正会撞的典型：**同时用 USART2_TX 和 I2C1_RX**（都抢 Channel7），或者 **同时用 TIM2_CH3 和 ADC1**（都抢 Channel1）。CubeMX 会在 DMA 配置页给你红字警告。
> **蓝 Pill 只有 DMA1**（7 个通道）。DMA2 是 high-density F103 才有的。

#### 2.3 代码：DMA + IDLE + 环形缓冲（可直接编译）

新建 `uart_rx.c` / `uart_rx.h`：

```c
/* ==================== uart_rx.h ==================== */
#ifndef UART_RX_H
#define UART_RX_H

#include "main.h"
#include <stdint.h>

void     uart_rx_init(void);          /* 启动 DMA 接收 + 使能 IDLE 中断 */
void     uart_rx_idle_isr(void);      /* 在 USART1_IRQHandler 里调用 */
int      uart_rx_get(uint8_t *out);   /* 主循环取 1 字节，返回 1 表示取到 */
uint32_t uart_rx_overflow_count(void);

#endif /* UART_RX_H */
```

```c
/* ==================== uart_rx.c ==================== */
#include "uart_rx.h"
#include <string.h>

extern UART_HandleTypeDef huart1;
extern DMA_HandleTypeDef  hdma_usart1_rx;

#define RX_DMA_BUF_SIZE  128u          /* DMA 搬运的临时区 */
#define RB_SIZE          1024u         /* 环形缓冲，必须是 2 的幂 */
#define RB_MASK          (RB_SIZE - 1u)

static uint8_t  s_dma_buf[RX_DMA_BUF_SIZE];
static uint16_t s_dma_last_pos = 0;    /* 上次处理到的位置 */

static volatile uint8_t  s_rb[RB_SIZE];
static volatile uint16_t s_rb_head = 0;   /* 写指针：只在 ISR 改 */
static volatile uint16_t s_rb_tail = 0;   /* 读指针：只在主循环改 */
static volatile uint32_t s_rb_ovf  = 0;

static inline void rb_put(uint8_t b)
{
    uint16_t next = (uint16_t)((s_rb_head + 1u) & RB_MASK);
    if (next == s_rb_tail)          /* 满：丢弃最旧策略会让 head/tail 复杂化，这里选丢新 */
    {
        s_rb_ovf++;
        return;
    }
    s_rb[s_rb_head] = b;
    s_rb_head = next;
}

int uart_rx_get(uint8_t *out)
{
    if (s_rb_tail == s_rb_head)     /* 空 */
    {
        return 0;
    }
    *out = s_rb[s_rb_tail];
    s_rb_tail = (uint16_t)((s_rb_tail + 1u) & RB_MASK);
    return 1;
}

uint32_t uart_rx_overflow_count(void)
{
    return s_rb_ovf;
}

void uart_rx_init(void)
{
    s_dma_last_pos = 0;
    s_rb_head = 0;
    s_rb_tail = 0;
    s_rb_ovf  = 0;

    __HAL_UART_ENABLE_IT(&huart1, UART_IT_IDLE);   /* 使能 IDLE 中断 */
    HAL_UART_Receive_DMA(&huart1, s_dma_buf, RX_DMA_BUF_SIZE);
}

/* 在 USART1_IRQHandler 中、HAL_UART_IRQHandler 之前调用 */
void uart_rx_idle_isr(void)
{
    if (__HAL_UART_GET_FLAG(&huart1, UART_FLAG_IDLE) == RESET)
    {
        return;
    }
    __HAL_UART_CLEAR_IDLEFLAG(&huart1);            /* 读 SR 再读 DR 清标志 */

    /* CNDTR 是"剩余未搬运字节数"，反向算出 DMA 已经写到哪 */
    uint16_t pos = (uint16_t)(RX_DMA_BUF_SIZE - __HAL_DMA_GET_COUNTER(&hdma_usart1_rx));

    while (s_dma_last_pos != pos)
    {
        rb_put(s_dma_buf[s_dma_last_pos]);
        s_dma_last_pos = (uint16_t)((s_dma_last_pos + 1u) % RX_DMA_BUF_SIZE);
    }
}
```

在 `stm32f1xx_it.c` 里改 `USART1_IRQHandler`（**放在 `/* USER CODE BEGIN USART1_IRQn 0 */` 区域**，否则重新生成代码会被覆盖）：

```c
void USART1_IRQHandler(void)
{
    /* USER CODE BEGIN USART1_IRQn 0 */
    uart_rx_idle_isr();               /* 先处理 IDLE：把 DMA 数据搬进环形缓冲 */
    /* USER CODE END USART1_IRQn 0 */
    HAL_UART_IRQHandler(&huart1);     /* 再交给 HAL 处理 RXNE / TC / 错误 */
    /* USER CODE BEGIN USART1_IRQn 1 */
    /* USER CODE END USART1_IRQn 1 */
}
```

在 `main.c` 里用：

```c
/* USER CODE BEGIN 2 */
uart_rx_init();
/* USER CODE END 2 */

/* USER CODE BEGIN WHILE */
uint8_t b;
while (1)
{
    if (uart_rx_get(&b))
    {
        HAL_UART_Transmit(&huart1, &b, 1, 10);   /* 回显 */
    }
    /* USER CODE END WHILE */
}
```

#### 2.4 另一种写法：`HAL_UARTEx_ReceiveToIdle_DMA`

CubeF1 的 HAL 提供这个扩展函数，它把「DMA + IDLE」封装成一次调用，回调是 `HAL_UARTEx_RxEventCallback`：

```c
/* 启动 */
HAL_UARTEx_ReceiveToIdle_DMA(&huart1, rx_buf, sizeof(rx_buf));
__HAL_DMA_DISABLE_IT(&hdma_usart1_rx, DMA_IT_HT);   /* 关半满中断，避免一次帧触发两次回调 */

/* 回调：Size = 本次收到的字节数 */
void HAL_UARTEx_RxEventCallback(UART_HandleTypeDef *huart, uint16_t Size)
{
    if (huart->Instance == USART1)
    {
        /* 在这里处理 rx_buf[0..Size-1] */
        HAL_UARTEx_ReceiveToIdle_DMA(&huart1, rx_buf, sizeof(rx_buf));  /* 重新武装 */
    }
}
```

| 对比 | 手动 DMA+IDLE（2.3） | `HAL_UARTEx_ReceiveToIdle_DMA`（2.4） |
|---|---|---|
| 代码量 | 多，要自己写环形缓冲 | 少 |
| 灵活性 | 高，可以做零拷贝、多缓冲 | 低，回调里必须尽快处理完并重新武装 |
| 高波特率/长帧 | 更好 | 回调处理慢会丢数据 |
| 可用性 | 任何 HAL 版本 | **需要 CubeF1 HAL ≥ 1.1.9**（在 `stm32f1xx_hal_uart_ex.h` 里搜 `ReceiveToIdle_DMA` 确认） |

**建议**：先按 2.3 手写一遍（理解原理），再用 2.4 做对比。

#### 2.5 DMA 发送

```c
/* 注意：pData 指向的缓冲区在 DMA 传输完成前不能被改写 */
static uint8_t s_tx_buf[64];

void uart_send_dma(const uint8_t *data, uint16_t len)
{
    if (len > sizeof(s_tx_buf)) return;
    memcpy(s_tx_buf, data, len);                       /* 拷进常驻缓冲 */
    HAL_UART_Transmit_DMA(&huart1, s_tx_buf, len);     /* 立刻返回，后台发送 */
}

void HAL_UART_TxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART1)
    {
        /* 发送完成，可以发下一帧了 */
    }
}
```

#### 验证方法

| 测试 | 期望现象 |
|---|---|
| 用串口助手以 115200 连续发 1000 字节 | 全部回显，`uart_rx_overflow_count()` 保持 0 |
| 把 `RB_SIZE` 改成 16，再发 1000 字节 | `uart_rx_overflow_count()` 增加 —— 说明溢出检测生效 |
| 发一帧后停顿 5ms 再发下一帧 | 每次 IDLE 中断搬走整帧，不丢首字节 |
| 用逻辑分析仪测回显延迟 | 单字节回显延迟 < 100μs |

#### 常见坑

| 坑 | 现象 | 原因 |
|---|---|---|
| **DMA 通道选错** | 完全没反应，`CNDTR` 不减少 | F1 通道是硬连线的，必须用 USART1_RX → Channel5 |
| **DMA 模式选了 Normal** | 收满 128 字节后就停了，之后再也收不到 | 接收必须用 **Circular** |
| **忘使能 USART1 全局中断** | IDLE 中断不触发 | NVIC 里要 Enable |
| **`__HAL_UART_CLEAR_IDLEFLAG` 漏掉** | IDLE 中断只进一次 | 这个标志必须「读 SR + 读 DR」才能清，用宏最稳 |
| **`HAL_UART_Receive_DMA` 长度和缓冲区大小不一致** | 越界 / 数据错位 | 传 `sizeof(buf)` 别手写数字 |
| **`HAL_UART_Transmit_DMA` 传了局部变量地址** | 发出去乱码 / 死机 | DMA 是异步的，函数返回后局部变量栈已失效。必须用 `static` 或全局缓冲 |
| **ORE（溢出错误）没清** | 串口彻底死了，`HAL_UART_ErrorCallback` 一直进 | 在 `HAL_UART_ErrorCallback` 里 `__HAL_UART_CLEAR_OREFLAG(huart)` 并重启 DMA 接收 |
| **中断里调用 `printf`** | 系统变慢、优先级反转 | 用环形缓冲 + 主循环发 |
| **`__HAL_DMA_GET_COUNTER` 的单位** | 算出长度不对 | F1 上 CNDTR 是按 **Data Width** 计的，Byte 模式下就是字节数 |

---

### 阶段 3：I2C（MPU6050）/ SPI（Flash 或屏）（预计 12–16 小时）

#### 3.1 I2C 读 MPU6050

**硬件**：MPU6050 模块（GY-521）接 I2C1

| 蓝 Pill | GY-521 |
|---|---|
| PB6 (I2C1_SCL) | SCL |
| PB7 (I2C1_SDA) | SDA |
| 3.3V | VCC |
| GND | GND |
| — | AD0 接 GND（地址 = 0x68） |

> GY-521 模块上自带 4.7kΩ 上拉电阻，所以蓝 Pill 这边不用再加。**如果自己画板子（阶段 6 之后）必须自己加 4.7kΩ 上拉到 3.3V。**

**CubeMX 配置**：

| 配置项 | 值 |
|---|---|
| `Connectivity > I2C1 > I2C` | **I2C**（不是 SMBus） |
| `Speed Mode` | **Fast Mode**，`Clock Speed` = 400000 |
| `GPIO Settings` | 自动设为 PB6/PB7，**AF Open Drain**（CubeMX 会自动配，自己手写别忘 `GPIO_MODE_AF_OD`） |
| `NVIC` | 可以不开（用阻塞模式），也可开 `I2C1 event interrupt` |

**代码（可直接编译）：**

```c
/* ==================== mpu6050.h ==================== */
#ifndef MPU6050_H
#define MPU6050_H

#include "main.h"
#include <stdint.h>

/* HAL 需要 8 位地址：7 位地址左移 1 位 */
#define MPU6050_ADDR          (0x68u << 1)

#define MPU6050_REG_SMPLRT_DIV   0x19u
#define MPU6050_REG_CONFIG       0x1Au
#define MPU6050_REG_GYRO_CONFIG  0x1Bu
#define MPU6050_REG_ACCEL_CONFIG 0x1Cu
#define MPU6050_REG_ACCEL_XOUT_H 0x3Bu
#define MPU6050_REG_PWR_MGMT_1   0x6Bu
#define MPU6050_REG_WHO_AM_I     0x75u

typedef struct {
    int16_t ax, ay, az;   /* 原始值 */
    int16_t temp;
    int16_t gx, gy, gz;
} mpu6050_raw_t;

HAL_StatusTypeDef mpu6050_init(I2C_HandleTypeDef *hi2c);
HAL_StatusTypeDef mpu6050_read_raw(I2C_HandleTypeDef *hi2c, mpu6050_raw_t *out);
float             mpu6050_temp_c(int16_t raw_temp);

#endif /* MPU6050_H */
```

```c
/* ==================== mpu6050.c ==================== */
#include "mpu6050.h"

#define I2C_TIMEOUT_MS   100u

static HAL_StatusTypeDef mpu_write_u8(I2C_HandleTypeDef *hi2c, uint8_t reg, uint8_t val)
{
    return HAL_I2C_Mem_Write(hi2c, MPU6050_ADDR, reg,
                             I2C_MEMADD_SIZE_8BIT, &val, 1u, I2C_TIMEOUT_MS);
}

HAL_StatusTypeDef mpu6050_init(I2C_HandleTypeDef *hi2c)
{
    uint8_t who = 0u;

    /* 0. 确认器件在总线上：会发地址 + 等 ACK */
    if (HAL_I2C_IsDeviceReady(hi2c, MPU6050_ADDR, 3u, I2C_TIMEOUT_MS) != HAL_OK)
    {
        return HAL_ERROR;
    }

    /* 1. 读 WHO_AM_I，应该是 0x68 */
    if (HAL_I2C_Mem_Read(hi2c, MPU6050_ADDR, MPU6050_REG_WHO_AM_I,
                         I2C_MEMADD_SIZE_8BIT, &who, 1u, I2C_TIMEOUT_MS) != HAL_OK)
    {
        return HAL_ERROR;
    }
    if (who != 0x68u)
    {
        return HAL_ERROR;
    }

    /* 2. 软复位 */
    if (mpu_write_u8(hi2c, MPU6050_REG_PWR_MGMT_1, 0x80u) != HAL_OK) return HAL_ERROR;
    HAL_Delay(100u);

    /* 3. 唤醒 + 时钟源选 PLL with X gyro reference（比内部 RC 稳） */
    if (mpu_write_u8(hi2c, MPU6050_REG_PWR_MGMT_1, 0x01u) != HAL_OK) return HAL_ERROR;
    HAL_Delay(10u);

    /* 4. 数字低通滤波 DLPF_CFG = 3：加速度 44Hz / 陀螺 42Hz，延迟 4.9ms */
    if (mpu_write_u8(hi2c, MPU6050_REG_CONFIG, 0x03u) != HAL_OK) return HAL_ERROR;

    /* 5. 采样率 1kHz / (1 + 9) = 100Hz */
    if (mpu_write_u8(hi2c, MPU6050_REG_SMPLRT_DIV, 0x09u) != HAL_OK) return HAL_ERROR;

    /* 6. 陀螺量程 ±250 dps → 灵敏度 131 LSB/(°/s) */
    if (mpu_write_u8(hi2c, MPU6050_REG_GYRO_CONFIG, 0x00u) != HAL_OK) return HAL_ERROR;

    /* 7. 加速度量程 ±2g → 灵敏度 16384 LSB/g */
    if (mpu_write_u8(hi2c, MPU6050_REG_ACCEL_CONFIG, 0x00u) != HAL_OK) return HAL_ERROR;

    return HAL_OK;
}

HAL_StatusTypeDef mpu6050_read_raw(I2C_HandleTypeDef *hi2c, mpu6050_raw_t *out)
{
    uint8_t b[14];

    if (out == NULL)
    {
        return HAL_ERROR;
    }

    /* 从 ACCEL_XOUT_H(0x3B) 开始连续读 14 字节：
       AX AY AZ TEMP GX GY GZ，每项高字节在前（big-endian） */
    if (HAL_I2C_Mem_Read(hi2c, MPU6050_ADDR, MPU6050_REG_ACCEL_XOUT_H,
                         I2C_MEMADD_SIZE_8BIT, b, 14u, I2C_TIMEOUT_MS) != HAL_OK)
    {
        return HAL_ERROR;
    }

    out->ax   = (int16_t)(((uint16_t)b[0]  << 8) | (uint16_t)b[1]);
    out->ay   = (int16_t)(((uint16_t)b[2]  << 8) | (uint16_t)b[3]);
    out->az   = (int16_t)(((uint16_t)b[4]  << 8) | (uint16_t)b[5]);
    out->temp = (int16_t)(((uint16_t)b[6]  << 8) | (uint16_t)b[7]);
    out->gx   = (int16_t)(((uint16_t)b[8]  << 8) | (uint16_t)b[9]);
    out->gy   = (int16_t)(((uint16_t)b[10] << 8) | (uint16_t)b[11]);
    out->gz   = (int16_t)(((uint16_t)b[12] << 8) | (uint16_t)b[13]);

    return HAL_OK;
}

float mpu6050_temp_c(int16_t raw_temp)
{
    return ((float)raw_temp / 340.0f) + 36.53f;
}
```

**验证方法**：

| 步骤 | 期望现象 |
|---|---|
| `HAL_I2C_IsDeviceReady` | 返回 `HAL_OK`（没接模块返回 `HAL_ERROR`） |
| 读 `WHO_AM_I` (0x75) | 返回 **0x68** |
| 静止平放读原始值 | `az` ≈ **+16384**（±2g 量程，1g 重力），`ax`/`ay` ≈ 0（±500 内正常） |
| 读温度 | 25°C 左右，手捏芯片会上升 |
| 绕 Z 轴快速转 | `gz` 明显变化（±250dps 量程） |

**换算公式**：

```
加速度(g)  = raw / 16384.0     (±2g)    / 8192.0 (±4g) / 4096.0 (±8g) / 2048.0 (±16g)
角速度(dps)= raw / 131.0       (±250)   / 65.5 (±500)  / 32.8 (±1000) / 16.4 (±2000)
温度(°C)   = raw / 340.0 + 36.53
```

**常见坑（这一节是重点，STM32F1 的 I2C 是出了名的坑）**：

| 坑 | 现象 | 原因 / 解法 |
|---|---|---|
| **BUSY 标志卡死** | `HAL_I2C_Mem_Read` 一直返回 `HAL_BUSY` 或超时，重启才好 | **STM32F1 的 I2C 硬件 errata**：从机在传输中途掉电/复位，SDA 被拉低，总线死锁。**解法**：① 把 SCL 配成 GPIO 推挽，手动打 9 个以上时钟脉冲，再产生 STOP 条件释放总线；② 严重的话改用 **软件 I2C**（两个 GPIO 位翻转），彻底避开硬件 I2C |
| **地址忘了左移** | 一直 NACK | HAL 的 `HAL_I2C_Mem_Read` 要的是 **8 位地址**（7 位左移 1 位）。MPU6050 是 `0x68 << 1 = 0xD0` |
| **AD0 引脚悬空** | 地址在 0x68/0x69 之间随机 | AD0 必须明确接 GND 或 3.3V |
| **忘清 SLEEP 位** | 读出来全是 0 或固定值 | `PWR_MGMT_1` (0x6B) 的 bit6 是 SLEEP，上电默认 **1（睡眠）**，必须写 0 唤醒 |
| **上拉电阻缺失** | 波形上升沿很缓，高速下 NACK | 自画板必须加 4.7kΩ 上拉到 3.3V（模块板已带） |
| **`I2C_MEMADD_SIZE_8BIT` 写成 `_16BIT`** | 数据错位 | MPU6050 是 8 位寄存器地址 |
| **多字节读的 endianness** | 数据乱七八糟 | MPU6050 是 **big-endian**，必须先读高字节 |

#### 3.2 SPI 读 W25Q64 Flash（推荐先做这个，比屏简单）

**硬件**：W25Q64 模块接 SPI1

| 蓝 Pill | W25Q64 |
|---|---|
| PA5 (SPI1_SCK) | CLK |
| PA6 (SPI1_MISO) | DO |
| PA7 (SPI1_MOSI) | DI |
| PA4 (GPIO 输出) | CS |
| 3.3V / GND | VCC / GND |

**CubeMX 配置**：

| 配置项 | 值 |
|---|---|
| `Connectivity > SPI1 > Mode` | **Full-Duplex Master**（Disable Half-Duplex / Hardware NSS） |
| `Hardware NSS Signal` | **Disable**（用软件控制 CS） |
| `Frame Format` | Motorola |
| `Data Size` | 8 Bits |
| `First Bit` | MSB First |
| `Prescaler` | **8**（72MHz / 8 = 9MHz，保守；W25Q64 最高支持 104MHz，可试 /4 = 18MHz） |
| `Clock Polarity (CPOL)` | **Low** |
| `Clock Phase (CPHA)` | **1 Edge** |
| `CRC Calculation` | Disabled |
| PA4 | 手动设为 `GPIO_Output`，Initial: **High**，Speed: **High** |

**代码（可直接编译）：**

```c
/* ==================== w25q.h ==================== */
#ifndef W25Q_H
#define W25Q_H

#include "main.h"
#include <stdint.h>

#define W25Q_CMD_JEDEC_ID      0x9Fu
#define W25Q_CMD_READ_STATUS1  0x05u
#define W25Q_CMD_WRITE_ENABLE  0x06u
#define W25Q_CMD_READ_DATA     0x03u
#define W25Q_CMD_PAGE_PROGRAM  0x02u
#define W25Q_CMD_SECTOR_ERASE  0x20u   /* 4KB */
#define W25Q_CMD_CHIP_ERASE    0xC7u

uint32_t w25q_read_jedec_id(SPI_HandleTypeDef *hspi);
uint8_t  w25q_read_status1(SPI_HandleTypeDef *hspi);
void     w25q_write_enable(SPI_HandleTypeDef *hspi);
void     w25q_wait_busy(SPI_HandleTypeDef *hspi);
void     w25q_read(SPI_HandleTypeDef *hspi, uint32_t addr, uint8_t *buf, uint32_t len);
void     w25q_page_program(SPI_HandleTypeDef *hspi, uint32_t addr, const uint8_t *buf, uint32_t len);
void     w25q_sector_erase(SPI_HandleTypeDef *hspi, uint32_t addr);

#endif /* W25Q_H */
```

```c
/* ==================== w25q.c ==================== */
#include "w25q.h"

extern SPI_HandleTypeDef hspi1;

#define W25Q_CS_LOW()   HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_RESET)
#define W25Q_CS_HIGH()  HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_SET)

#define SPI_TIMEOUT_MS  1000u

static void w25q_send_cmd(uint8_t cmd)
{
    HAL_SPI_Transmit(&hspi1, &cmd, 1u, SPI_TIMEOUT_MS);
}

uint32_t w25q_read_jedec_id(SPI_HandleTypeDef *hspi)
{
    uint8_t cmd = W25Q_CMD_JEDEC_ID;
    uint8_t id[3] = { 0u, 0u, 0u };

    W25Q_CS_LOW();
    HAL_SPI_Transmit(hspi, &cmd, 1u, SPI_TIMEOUT_MS);
    /* 全双工 Master 下 Receive 会自动发 0xFF 作为时钟 */
    HAL_SPI_Receive(hspi, id, 3u, SPI_TIMEOUT_MS);
    W25Q_CS_HIGH();

    return ((uint32_t)id[0] << 16) | ((uint32_t)id[1] << 8) | (uint32_t)id[2];
}

uint8_t w25q_read_status1(SPI_HandleTypeDef *hspi)
{
    uint8_t cmd = W25Q_CMD_READ_STATUS1;
    uint8_t st  = 0u;

    W25Q_CS_LOW();
    HAL_SPI_Transmit(hspi, &cmd, 1u, SPI_TIMEOUT_MS);
    HAL_SPI_Receive(hspi, &st, 1u, SPI_TIMEOUT_MS);
    W25Q_CS_HIGH();

    return st;
}

void w25q_write_enable(SPI_HandleTypeDef *hspi)
{
    W25Q_CS_LOW();
    w25q_send_cmd(W25Q_CMD_WRITE_ENABLE);
    W25Q_CS_HIGH();
}

void w25q_wait_busy(SPI_HandleTypeDef *hspi)
{
    uint32_t guard = 0u;
    /* STATUS1 的 bit0 = BUSY */
    while ((w25q_read_status1(hspi) & 0x01u) != 0u)
    {
        if (++guard > 100000u) { break; }   /* 超时保护，防止死等 */
    }
}

void w25q_read(SPI_HandleTypeDef *hspi, uint32_t addr, uint8_t *buf, uint32_t len)
{
    uint8_t cmd[4];
    cmd[0] = W25Q_CMD_READ_DATA;
    cmd[1] = (uint8_t)(addr >> 16);
    cmd[2] = (uint8_t)(addr >> 8);
    cmd[3] = (uint8_t)(addr);

    W25Q_CS_LOW();
    HAL_SPI_Transmit(hspi, cmd, 4u, SPI_TIMEOUT_MS);
    HAL_SPI_Receive(hspi, buf, (uint16_t)len, SPI_TIMEOUT_MS);
    W25Q_CS_HIGH();
}

void w25q_page_program(SPI_HandleTypeDef *hspi, uint32_t addr, const uint8_t *buf, uint32_t len)
{
    uint8_t cmd[4];

    /* 一页 256 字节，不能跨页，调用者必须自己保证 */
    if (len > 256u) { len = 256u; }

    w25q_write_enable(hspi);

    cmd[0] = W25Q_CMD_PAGE_PROGRAM;
    cmd[1] = (uint8_t)(addr >> 16);
    cmd[2] = (uint8_t)(addr >> 8);
    cmd[3] = (uint8_t)(addr);

    W25Q_CS_LOW();
    HAL_SPI_Transmit(hspi, cmd, 4u, SPI_TIMEOUT_MS);
    HAL_SPI_Transmit(hspi, (uint8_t *)buf, (uint16_t)len, SPI_TIMEOUT_MS);
    W25Q_CS_HIGH();

    w25q_wait_busy(hspi);
}

void w25q_sector_erase(SPI_HandleTypeDef *hspi, uint32_t addr)
{
    uint8_t cmd[4];

    w25q_write_enable(hspi);

    cmd[0] = W25Q_CMD_SECTOR_ERASE;
    cmd[1] = (uint8_t)(addr >> 16);
    cmd[2] = (uint8_t)(addr >> 8);
    cmd[3] = (uint8_t)(addr);

    W25Q_CS_LOW();
    HAL_SPI_Transmit(hspi, cmd, 4u, SPI_TIMEOUT_MS);
    W25Q_CS_HIGH();

    w25q_wait_busy(hspi);   /* 擦除一个 4KB 扇区约 45ms */
}
```

**验证方法**：

| 测试 | 期望值 |
|---|---|
| `w25q_read_jedec_id()` | **W25Q64 → 0xEF4017**；W25Q128 → 0xEF4018；W25Q32 → 0xEF4016 |
| 擦除 + 写入 + 读回 | 读回数据与写入一致 |
| 未擦除直接写 | 读回是旧数据 AND 新数据（NOR Flash 只能 1→0） |

**常见坑**：

| 坑 | 现象 | 原因 |
|---|---|---|
| **CS 没拉低** | 读 ID 返回 0x000000 或 0xFFFFFF | CS 时序错误 |
| **CS 拉低后没拉高** | 第二次操作全乱 | 每个命令必须完整包在 CS 低-高之间 |
| **SPI 模式不对** | 读 ID 全 0xFF | W25Q 支持 Mode 0 (CPOL=0,CPHA=0) 和 Mode 3 (CPOL=1,CPHA=1)。CubeMX 的 `CPOL Low + CPHA 1Edge` = Mode 0 |
| **写入前没 Write Enable** | 写不进去 | 每次 Program/Erase 前必须发 0x06 |
| **跨页写** | 数据绕回到页首 | 256 字节页边界，必须拆分 |
| **写前没擦除** | 数据是 AND 结果 | NOR Flash 只能 1→0，写前必须 Erase |
| **MISO/MOSI 接反** | 完全没反应 | 检查接线（这是最常见的接线错误） |

#### 3.3 SPI 驱动 ILI9341 屏

**你已经在 ESP32 上驱动过 ILI9341 了**，所以本节的「新知识」只有一点：**把 ESP-IDF 的 `spi_device_transmit` 换成 `HAL_SPI_Transmit`，把 GPIO 操作换成 `HAL_GPIO_WritePin`**。

**引脚映射（蓝 Pill）**：

| ILI9341 | 蓝 Pill | 说明 |
|---|---|---|
| SCK | PA5 | SPI1_SCK |
| SDO (MISO) | PA6 | 可只接 MOSI，不用读 |
| SDI (MOSI) | PA7 | SPI1_MOSI |
| CS | PA4 | 软件控制 |
| DC (RS) | PB0 | 数据/命令选择 |
| RESET | PB1 | 复位 |
| LED/BL | 3.3V（或 PB10 做 PWM 调光） | 背光 |

**CubeMX**：SPI1 配置同 W25Q，但 `Prescaler` 用 **8**（9MHz，ILI9341 写操作上限约 10MHz，保守）。PB0/PB1 设为 `GPIO_Output`，Speed 设 **High**。

**代码骨架（可直接编译，底层原语）：**

```c
/* ==================== lcd_ili9341.h ==================== */
#ifndef LCD_ILI9341_H
#define LCD_ILI9341_H

#include "main.h"
#include <stdint.h>

#define LCD_W  240u
#define LCD_H  320u

void lcd_init(void);
void lcd_set_window(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1);
void lcd_fill(uint16_t color);
void lcd_draw_pixel(uint16_t x, uint16_t y, uint16_t color);

#endif
```

```c
/* ==================== lcd_ili9341.c ==================== */
#include "lcd_ili9341.h"

extern SPI_HandleTypeDef hspi1;

#define LCD_CS_LOW()    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_RESET)
#define LCD_CS_HIGH()   HAL_GPIO_WritePin(GPIOA, GPIO_PIN_4, GPIO_PIN_SET)
#define LCD_DC_CMD()    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_0, GPIO_PIN_RESET)
#define LCD_DC_DATA()   HAL_GPIO_WritePin(GPIOB, GPIO_PIN_0, GPIO_PIN_SET)
#define LCD_RST_LOW()   HAL_GPIO_WritePin(GPIOB, GPIO_PIN_1, GPIO_PIN_RESET)
#define LCD_RST_HIGH()  HAL_GPIO_WritePin(GPIOB, GPIO_PIN_1, GPIO_PIN_SET)

#define LCD_SPI_TO  1000u

static void lcd_write_cmd(uint8_t cmd)
{
    LCD_DC_CMD();
    LCD_CS_LOW();
    HAL_SPI_Transmit(&hspi1, &cmd, 1u, LCD_SPI_TO);
    LCD_CS_HIGH();
}

static void lcd_write_data(const uint8_t *data, uint32_t len)
{
    LCD_DC_DATA();
    LCD_CS_LOW();
    HAL_SPI_Transmit(&hspi1, (uint8_t *)data, (uint16_t)len, LCD_SPI_TO);
    LCD_CS_HIGH();
}

static void lcd_write_data_u8(uint8_t v)
{
    lcd_write_data(&v, 1u);
}

void lcd_set_window(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1)
{
    uint8_t b[4];

    lcd_write_cmd(0x2Au);                 /* Column Address Set */
    b[0] = (uint8_t)(x0 >> 8); b[1] = (uint8_t)x0;
    b[2] = (uint8_t)(x1 >> 8); b[3] = (uint8_t)x1;
    lcd_write_data(b, 4u);

    lcd_write_cmd(0x2Bu);                 /* Page Address Set */
    b[0] = (uint8_t)(y0 >> 8); b[1] = (uint8_t)y0;
    b[2] = (uint8_t)(y1 >> 8); b[3] = (uint8_t)y1;
    lcd_write_data(b, 4u);

    lcd_write_cmd(0x2Cu);                 /* Memory Write */
}

void lcd_fill(uint16_t color)
{
    uint8_t line[LCD_W * 2u];
    uint32_t i;

    for (i = 0u; i < LCD_W; i++)
    {
        line[i * 2u]      = (uint8_t)(color >> 8);
        line[i * 2u + 1u] = (uint8_t)(color & 0xFFu);
    }

    lcd_set_window(0u, 0u, LCD_W - 1u, LCD_H - 1u);
    LCD_DC_DATA();
    LCD_CS_LOW();
    for (i = 0u; i < LCD_H; i++)
    {
        HAL_SPI_Transmit(&hspi1, line, (uint16_t)sizeof(line), LCD_SPI_TO);
    }
    LCD_CS_HIGH();
}

void lcd_draw_pixel(uint16_t x, uint16_t y, uint16_t color)
{
    uint8_t b[2];
    b[0] = (uint8_t)(color >> 8);
    b[1] = (uint8_t)(color & 0xFFu);
    lcd_set_window(x, y, x, y);
    lcd_write_data(b, 2u);
}

void lcd_init(void)
{
    /* 硬件复位 */
    LCD_RST_HIGH();
    HAL_Delay(5u);
    LCD_RST_LOW();
    HAL_Delay(20u);
    LCD_RST_HIGH();
    HAL_Delay(150u);

    /* --- 以下只列关键命令，完整的 ILI9341 上电序列请照抄你自己
           ESP32 工程里那份初始化表（Power Control A/B、VCOM、Gamma 等），
           把底层 spi_device_transmit 换成 lcd_write_data 即可 --- */

    lcd_write_cmd(0x01u);                 /* Software Reset */
    HAL_Delay(120u);

    lcd_write_cmd(0x11u);                 /* Sleep Out */
    HAL_Delay(120u);

    lcd_write_cmd(0x3Au);                 /* Pixel Format Set */
    lcd_write_data_u8(0x55u);             /* 16 bit/pixel (RGB565) */
    HAL_Delay(10u);

    lcd_write_cmd(0x36u);                 /* Memory Access Control */
    lcd_write_data_u8(0x48u);             /* MY=0 MX=1 MV=1 → 横屏；竖屏用 0x08 */
    HAL_Delay(10u);

    lcd_write_cmd(0x29u);                 /* Display ON */
    HAL_Delay(20u);
}
```

> ⚠️ **说明**：上面只包含复位、像素格式、显示开这几个**关键命令**。完整的 ILI9341 初始化需要大约 25–30 条命令（Power Control A/B、VCOM Control、Gamma 曲线等）。
> **推荐做法**：直接复用你 ESP32 工程里的初始化表 —— 把 `spi_device_transmit()` 换成 `lcd_write_data()`、`gpio_set_level()` 换成 `HAL_GPIO_WritePin()`，初始化表的命令字节**完全不用改**（ILI9341 是同一颗芯片）。

**验证方法**：

| 测试 | 期望现象 |
|---|---|
| `lcd_fill(0xF800)` | 整屏变红（RGB565 的纯红） |
| `lcd_fill(0x07E0)` | 整屏变绿 |
| `lcd_fill(0x001F)` | 整屏变蓝 |
| `lcd_draw_pixel(0, 0, 0xFFFF)` | 左上角一个白点 |
| 刷屏速度 | 240×320 全屏（150KB）@9MHz ≈ 140ms/帧 ≈ 7fps（够画 UI，不够播视频） |

**常见坑**：

| 坑 | 现象 | 原因 |
|---|---|---|
| **DC 脚时序错了** | 花屏 / 完全不亮 | DC 必须在 CS 拉低**之前或同时**设好，不能夹在 SPI 传输中间 |
| **RGB565 字节序反了** | 颜色不对（红变蓝） | 有些屏要 `color` 高低字节交换。先试 `0xF800` 看是不是红 |
| **MADCTL 方向不对** | 画面镜像/旋转 | 0x36 参数不同屏不同，试 0x08/0x48/0x88/0xC8 |
| **背光没接** | 全黑但 SPI 有波形 | LED/BL 脚要接 3.3V 或 PWM |
| **用 `HAL_SPI_Transmit` 逐像素** | 慢到 1fps | 必须批量发（见 `lcd_fill` 的整行缓冲做法），或用 **DMA** |
| **`line[]` 数组太大** | 栈溢出 | `uint8_t line[480]` 放函数栈里，配合 FreeRTOS 的小栈会溢出。改成 `static` |

---

### 阶段 4：ADC + DMA 采样（预计 4–6 小时，**可压缩**）

> **你已会**：ESP32 的 `adc_continuous` + DMA 连续采样。
> **本阶段新知识**：F1 的 ADC 时钟约束、通道映射、`HAL_ADC_Start_DMA` 的 `uint32_t*` 要求、定时器触发。

#### 4.1 F1 ADC 关键参数

| 参数 | 值 | 说明 |
|---|---|---|
| 分辨率 | 12 位 | 0–4095 |
| ADCCLK | **最高 14MHz** | 由 PCLK2 分频得到，72MHz/6 = 12MHz（CubeMX 的 `/6` 档） |
| 转换时间 | `(采样周期 + 12.5) / ADCCLK` | 12MHz + 55.5 周期 → `68/12M ≈ 5.67μs` |
| 参考电压 | VDDA = 3.3V | 蓝 Pill 的 VDDA 直接接 3.3V，没有独立滤波 |
| 通道数 | ADC1/ADC2 各 10 个外部通道 | 见下表 |

**蓝 Pill 可用的 ADC 通道**：

| 通道 | 引脚 | 通道 | 引脚 |
|---|---|---|---|
| ADC_IN0 | PA0 | ADC_IN8 | PB0 |
| ADC_IN1 | PA1 | ADC_IN9 | PB1 |
| ADC_IN2 | PA2 | ADC_IN16 | 内部温度传感器 |
| ADC_IN3 | PA3 | ADC_IN17 | 内部 Vrefint（约 1.20V） |
| ADC_IN4 | PA4 | | |
| ADC_IN5 | PA5 | | |
| ADC_IN6 | PA6 | | |
| ADC_IN7 | PA7 | | |

> ⚠️ **引脚冲突**：PA5/PA6/PA7 是 SPI1，PB0/PB1 是 TIM3_CH3/CH4 和你的 LCD 控制脚。**做多外设综合项目时，ADC 通道要提前规划**。推荐用 **PA0 / PA1 / PA4**（相对空闲）。

#### 4.2 CubeMX 配置（多通道扫描 + 循环 DMA）

以 PA0(IN0) 和 PA1(IN1) 两路为例：

| 配置项 | 值 |
|---|---|
| `Analog > ADC1 > IN0` | **IN0**（勾选） |
| `Analog > ADC1 > IN1` | **IN1**（勾选） |
| `ADC1 > Parameter Settings > Mode > Scan Conversion Mode` | **Enabled** |
| `ADC1 > Parameter Settings > Mode > Continuous Conversion Mode` | **Enabled** |
| `ADC1 > Parameter Settings > Mode > DMA Continuous Requests` | **Enabled** |
| `ADC1 > Parameter Settings > Mode > Discontinuous Conversion Mode` | Disabled |
| `ADC1 > Parameter Settings > Rank` | Rank 1: Channel 0, Sampling Time **55.5 Cycles**；Rank 2: Channel 1, Sampling Time **55.5 Cycles** |
| `ADC1 > Parameter Settings > Data Alignment` | Right alignment |
| `ADC1 > Parameter Settings > Number Of Conversion` | **2** |
| `ADC1 > DMA Settings > Add` | **ADC1**，Mode: **Circular**，Data Width: **Word / Word** |
| `ADC1 > NVIC Settings` | `ADC1 and ADC2 global interrupt` = Enabled（用 DMA 回调就需要） |

**采样时间怎么选**：源阻抗越高，需要的采样周期越长。

| 源阻抗 | 推荐采样周期 |
|---|---|
| < 1kΩ | 7.5 或 13.5 cycles |
| 1k–10kΩ | 28.5 或 41.5 cycles |
| 10k–50kΩ | **55.5 cycles**（保守起点） |
| > 50kΩ | 239.5 cycles，或加电压跟随器 |

#### 4.3 代码（可直接编译）

```c
/* ==================== adc_dma.h ==================== */
#ifndef ADC_DMA_H
#define ADC_DMA_H

#include "main.h"
#include <stdint.h>

#define ADC_CH_NUM        2u            /* 扫描的通道数 */
#define ADC_BUF_LEN       128u          /* 必须是 ADC_CH_NUM 的整数倍 */
#define ADC_FRAME_LEN     (ADC_BUF_LEN / ADC_CH_NUM)

extern volatile uint16_t g_adc_avg[ADC_CH_NUM];
extern volatile uint32_t g_adc_frames;

void adc_dma_start(void);

#endif
```

```c
/* ==================== adc_dma.c ==================== */
#include "adc_dma.h"

extern ADC_HandleTypeDef hadc1;

/* ⚠️ F1 的 HAL_ADC_Start_DMA 要的是 uint32_t*，不是 uint16_t* */
static uint32_t s_adc_buf[ADC_BUF_LEN];

volatile uint16_t g_adc_avg[ADC_CH_NUM] = { 0u, 0u };
volatile uint32_t g_adc_frames = 0u;

static void adc_accumulate(const uint32_t *p, uint32_t frames)
{
    uint32_t sum[ADC_CH_NUM] = { 0u };
    uint32_t i, c;

    for (i = 0u; i < frames; i++)
    {
        for (c = 0u; c < ADC_CH_NUM; c++)
        {
            /* 右对齐 12 位，取低 12 位即可（高 4 位为 0） */
            sum[c] += (p[i * ADC_CH_NUM + c] & 0x0FFFu);
        }
    }
    for (c = 0u; c < ADC_CH_NUM; c++)
    {
        g_adc_avg[c] = (uint16_t)(sum[c] / frames);
    }
    g_adc_frames++;
}

void adc_dma_start(void)
{
    /* 校准：F1 的 HAL 只有一个参数（F4/F7 是双参数，多一个 ADC_SINGLE_ENDED） */
    if (HAL_ADCEx_Calibration_Start(&hadc1) != HAL_OK)
    {
        Error_Handler();
    }

    if (HAL_ADC_Start_DMA(&hadc1, s_adc_buf, ADC_BUF_LEN) != HAL_OK)
    {
        Error_Handler();
    }
}

/* DMA 搬完前半缓冲（128 个 uint32 = 64 帧） */
void HAL_ADC_ConvHalfCpltCallback(ADC_HandleTypeDef *hadc)
{
    if (hadc->Instance == ADC1)
    {
        adc_accumulate(&s_adc_buf[0], ADC_FRAME_LEN / 2u);
    }
}

/* DMA 搬完整个缓冲 */
void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef *hadc)
{
    if (hadc->Instance == ADC1)
    {
        adc_accumulate(&s_adc_buf[ADC_BUF_LEN / 2u], ADC_FRAME_LEN / 2u);
    }
}
```

```c
/* main.c USER CODE BEGIN 2 */
adc_dma_start();
/* USER CODE END 2 */

/* main.c USER CODE BEGIN WHILE */
while (1)
{
    /* 电压换算： V = raw / 4095.0 * 3.3 */
    printf("CH0=%4u (%.3fV)  CH1=%4u (%.3fV)  frames=%lu\r\n",
           (unsigned)g_adc_avg[0], (double)g_adc_avg[0] * 3.3 / 4095.0,
           (unsigned)g_adc_avg[1], (double)g_adc_avg[1] * 3.3 / 4095.0,
           (unsigned long)g_adc_frames);
    HAL_Delay(200);
    /* USER CODE END WHILE */
}
```

> ⚠️ `printf("%.3f")` 需要浮点 printf 支持。CubeIDE 里加链接参数 `-u _printf_float`（`Project > Properties > C/C++ Build > Settings > MCU/MPU GCC Linker > Miscellaneous > Linker flags`）。不加的话会打印空白或 `0.000`。

#### 4.4 定时器触发 ADC（工业级做法）

如果要**精确等间隔采样**（比如飞控的 1kHz 姿态采样），不能用「Continuous Conversion」自由跑，要用 **TIM 触发**：

| CubeMX 配置 | 值 |
|---|---|
| `ADC1 > Parameter Settings > External Trigger Conversion Source` | **Timer 2 Trigger Out event** |
| `ADC1 > Parameter Settings > Continuous Conversion Mode` | **Disabled**（改成单次，靠触发驱动） |
| `TIM2 > Parameter Settings` | `PSC=71`, `ARR=999` → 1kHz 更新事件 |
| `TIM2 > Trigger Output (TRGO) Parameters > Trigger Event Selection` | **Update Event** |
| `TIM2` | 不需要开 NVIC（只要 TRGO） |
| `ADC1 > DMA Settings` | Mode: **Circular**（必须，否则触发一次就停） |

这样：TIM2 每 1ms 产生一次 TRGO → ADC 转换一次 → DMA 搬到缓冲区 → 半满/全满回调处理。**采样率误差 = 晶振误差，和 CPU 负载无关**。

#### 验证方法

| 测试 | 期望现象 |
|---|---|
| PA0 接 GND | 读数 ≈ 0（噪声下 0–10） |
| PA0 接 3.3V | 读数 ≈ 4095 |
| PA0 接 1.65V（分压 3.3V/2） | 读数 ≈ 2047 ± 20 |
| 手指碰 PA0 | 读数乱跳（人体工频干扰，说明 ADC 在工作） |
| 测 Vrefint (ADC_IN17) | 读数 ≈ `1.20 / 3.3 * 4095 ≈ 1489`。**如果偏差大，说明 VDDA 不是 3.3V** |
| `g_adc_frames` 增长速率 | Continuous 模式 ≈ 采样率/(缓冲帧数)；定时器触发模式精确等于 1kHz/(帧数) |

#### 常见坑

| 坑 | 现象 | 原因 |
|---|---|---|
| **缓冲区类型写成 `uint16_t`** | 编译报错或数据错乱 | F1 的 `HAL_ADC_Start_DMA` 签名是 `(ADC_HandleTypeDef*, uint32_t*, uint32_t)`，必须 `uint32_t` 数组 |
| **忘调 `HAL_ADCEx_Calibration_Start`** | 读数有固定偏差（几十 LSB） | F1 必须校准，且要在 `HAL_ADC_Start` **之前** |
| **DMA 选了 Normal 模式** | 采满一轮就停 | 必须 Circular |
| **`Number Of Conversion` 和 DMA 长度不匹配** | 通道错位 | `DMA长度` 必须是 `通道数` 的整数倍 |
| **ADCCLK 超过 14MHz** | 读数不稳、随温度漂 | 检查 ADC Prescaler，72MHz 下必须 ≥ /6 |
| **`HAL_ADC_Start_DMA` 在 `MX_ADC1_Init` 之前调** | HardFault | 初始化顺序 |
| **采样时间太短 + 高阻抗源** | 读数偏低且不稳定 | 加长采样周期，或加电压跟随器 |
| **PA0 同时配了别的复用** | 读数恒为 0 | 检查 CubeMX 的引脚冲突警告 |
| **`HAL_ADC_ConvHalfCpltCallback` 里做耗时操作** | 数据覆盖 | 回调里只做「算平均值/塞队列」，重活交给任务 |

---

### 阶段 5：FreeRTOS 移植（预计 4–8 小时，**可压缩**）

> **你已会**：FreeRTOS 任务、队列、信号量、互斥量、任务优先级。
> **本阶段新知识**：① CubeMX 里的 FreeRTOS 配置项；② **CMSIS-RTOS v2 的 `os*` API vs 原生 API**；③ **栈大小单位从字节变字**；④ **NVIC 优先级和 FreeRTOS 的 `configMAX_SYSCALL_INTERRUPT_PRIORITY` 的关系**（这是最容易死的地方）；⑤ **单核 vs 双核**。

#### 5.1 CubeMX 配置

| 配置项 | 值 | 说明 |
|---|---|---|
| `Middleware and Software Packs > FREERTOS > Interface` | **CMSIS_V2** | 现代写法；也可以用 `CMSIS_V1`（更接近原生） |
| `FREERTOS > Config parameters > USE_PREEMPTION` | Enabled | 抢占式调度 |
| `FREERTOS > Config parameters > TICK_RATE_HZ` | **1000** | 1ms 一个 tick（默认 1000，改小省电） |
| `FREERTOS > Config parameters > MAX_PRIORITIES` | **7** | 优先级 0（最低）– 6（最高） |
| `FREERTOS > Config parameters > MINIMAL_STACK_SIZE` | **128**（单位：**字**，= 512 字节） | 空闲任务用的栈 |
| `FREERTOS > Config parameters > TOTAL_HEAP_SIZE` | **10240** | ⚠️ **默认只有 3072 字节，20KB RAM 里根本不够用** |
| `FREERTOS > Config parameters > Memory Allocation` | **heap_4** | 支持释放和碎片合并，CubeMX 默认 |
| `FREERTOS > Config parameters > CHECK_FOR_STACK_OVERFLOW` | **Option2** | 栈溢出钩子，调试期必开 |
| `FREERTOS > Config parameters > USE_MUTEXES` | Enabled | |
| `FREERTOS > Config parameters > USE_COUNTING_SEMAPHORES` | Enabled | |
| `FREERTOS > Config parameters > USE_TIMERS` | 按需 | 用软件定时器才开，会多占 RAM |
| `FREERTOS > Config parameters > USE_TRACE_FACILITY` | Enabled（调试期） | 可以看任务状态 |
| `FREERTOS > Advanced settings > Timebase Source` | **TIM2**（或 TIM3/TIM4） | 见下方说明 |
| `SYS > Timebase Source` | **TIM2** | 同上，两者要一致 |

> **为什么要把 HAL 的时基从 SysTick 挪到 TIM2？**
> FreeRTOS 也要用 SysTick 做调度心跳。如果 HAL 和 FreeRTOS 抢 SysTick，`HAL_GetTick()` 会不准、`HAL_Delay()` 会阻塞调度器。
> **规则**：用 FreeRTOS 时，HAL 时基（`SYS > Timebase Source`）必须改成 **非 SysTick 的定时器**（TIM2/TIM3/TIM4）。CubeMX 会弹出提示让你改。

#### 5.2 任务栈大小的坑（**最容易踩**）

| 环境 | `xTaskCreate` 的 `usStackDepth` 单位 | `osThreadNew` 的 `stack_size` 单位 |
|---|---|---|
| **ESP-IDF** | **字节**（乐鑫改过） | 字节 |
| **原生 FreeRTOS / CubeMX CMSIS_V2** | **字（word）= 4 字节**（`StackType_t` 在 Cortex-M3 上是 `uint32_t`） | **字节** |

**后果**：你在 ESP32 上写 `xTaskCreate(fn, "t", 4096, ...)` 是 4KB 栈。搬到 STM32 用原生 `xTaskCreate` 写 `4096`，那是 **16KB** —— 蓝 Pill 总共只有 20KB RAM，直接分配失败。

**建议栈大小（蓝 Pill，原生 `xTaskCreate` 的「字」单位）**：

| 任务类型 | 推荐栈（字） | 折合字节 |
|---|---|---|
| 纯 GPIO 翻转 / 状态机 | 64–128 | 256–512 B |
| 有 `printf` | **256–384** | 1–1.5 KB |
| I2C/SPI 外设驱动 | 128–256 | 512 B–1 KB |
| 有浮点运算（PID） | 256–384 | 1–1.5 KB |
| 有 `sprintf`/`sscanf` | **384–512** | 1.5–2 KB |

**怎么量出真实使用量**：

```c
UBaseType_t hw = uxTaskGetStackHighWaterMark(NULL);   /* 返回"历史最小剩余"，单位：字 */
```

在任务里定期打印，**剩 < 32 字就该加栈**。

#### 5.3 代码（原生 FreeRTOS API 版，可直接编译）

```c
/* ==================== app_tasks.c ==================== */
#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"
#include "semphr.h"
#include "main.h"
#include <stdio.h>

extern UART_HandleTypeDef huart1;
extern volatile uint16_t  g_adc_avg[2];
extern volatile uint32_t  g_adc_frames;

/* ---- 任务间通信对象 ---- */
static QueueHandle_t     s_adc_q   = NULL;
static SemaphoreHandle_t s_btn_sem = NULL;

typedef struct {
    uint16_t ch0;
    uint16_t ch1;
    uint32_t seq;
} adc_msg_t;

/* ---- 任务 1：LED 心跳（最低优先级） ---- */
static void vTaskLed(void *arg)
{
    (void)arg;
    const TickType_t period = pdMS_TO_TICKS(500);

    for (;;)
    {
        HAL_GPIO_TogglePin(GPIOC, GPIO_PIN_13);
        vTaskDelay(period);            /* 让出 CPU 500ms */
    }
}

/* ---- 任务 2：ADC 数据处理 ---- */
static void vTaskAdc(void *arg)
{
    (void)arg;
    adc_msg_t msg;
    uint32_t  last_seq = 0u;

    for (;;)
    {
        /* 阻塞等队列，最多等 200ms */
        if (xQueueReceive(s_adc_q, &msg, pdMS_TO_TICKS(200)) == pdPASS)
        {
            last_seq = msg.seq;
            /* 这里可以做滤波、PID、上报…… */
            (void)last_seq;
        }
        else
        {
            /* 超时：没数据，做点别的（比如检查栈水位） */
            (void)uxTaskGetStackHighWaterMark(NULL);
        }
    }
}

/* ---- 任务 3：串口上报（优先级低于 ADC） ---- */
static void vTaskReport(void *arg)
{
    (void)arg;

    for (;;)
    {
        printf("ADC CH0=%4u CH1=%4u frames=%lu\r\n",
               (unsigned)g_adc_avg[0],
               (unsigned)g_adc_avg[1],
               (unsigned long)g_adc_frames);
        vTaskDelay(pdMS_TO_TICKS(500));
    }
}

/* ---- 中断给队列塞数据（DMA 回调里调用） ---- */
void app_push_adc_isr(void)
{
    BaseType_t hpw = pdFALSE;
    adc_msg_t  msg;

    if (s_adc_q == NULL) { return; }

    msg.ch0 = g_adc_avg[0];
    msg.ch1 = g_adc_avg[1];
    msg.seq = g_adc_frames;

    /* 注意：必须用 FromISR 版本！ */
    (void)xQueueSendFromISR(s_adc_q, &msg, &hpw);

    if (hpw == pdTRUE)
    {
        portYIELD_FROM_ISR(hpw);       /* 若唤醒了更高优先级任务，立刻切 */
    }
}

/* ---- 启动 ---- */
void app_tasks_start(void)
{
    s_adc_q   = xQueueCreate(8u, sizeof(adc_msg_t));
    s_btn_sem = xSemaphoreCreateBinary();

    if ((s_adc_q == NULL) || (s_btn_sem == NULL))
    {
        Error_Handler();
    }

    /* ⚠️ 这里的 128/256 单位是【字】，不是字节！ */
    (void)xTaskCreate(vTaskLed,    "led",    128u, NULL, 1u, NULL);
    (void)xTaskCreate(vTaskReport, "report", 384u, NULL, 2u, NULL);  /* 有 printf，给大点 */
    (void)xTaskCreate(vTaskAdc,    "adc",    256u, NULL, 3u, NULL);

    vTaskStartScheduler();      /* 正常情况不会返回 */

    /* 只有堆不够 / 调度器启动失败才会走到这里 */
    for (;;) { }
}
```

在 `main.c` 里：

```c
/* USER CODE BEGIN 2 */
adc_dma_start();
app_tasks_start();     /* 这里面会调用 vTaskStartScheduler()，不返回 */
/* USER CODE END 2 */
```

**栈溢出钩子（必加，调试期救命）：**

```c
/* USER CODE BEGIN 4 */
void vApplicationStackOverflowHook(TaskHandle_t xTask, char *pcTaskName)
{
    (void)xTask;
    (void)pcTaskName;

    taskDISABLE_INTERRUPTS();
    /* 在这里打断点，然后看 pcTaskName 是哪个任务溢出的 */
    for (;;) { }
}

void vApplicationMallocFailedHook(void)
{
    taskDISABLE_INTERRUPTS();
    /* 堆不够了。加大 configTOTAL_HEAP_SIZE，或减小任务栈 */
    for (;;) { }
}
/* USER CODE END 4 */
```

> `vApplicationStackOverflowHook` / `vApplicationMallocFailedHook` 要生效，必须：
> ① `FreeRTOSConfig.h` 里 `#define configCHECK_FOR_STACK_OVERFLOW 2`
> ② `#define configUSE_MALLOC_FAILED_HOOK 1`
> ③ 钩子函数名**完全一致**（原生 API 用 `TaskHandle_t`，CMSIS_V1 用 `xTaskHandle`，**需自行核实**你的 CubeMX 生成版本用哪个类型）

#### 5.4 与 ESP-IDF FreeRTOS 的差异（**这是你最需要的部分**）

| 维度 | ESP-IDF（你熟悉的） | STM32 原生 FreeRTOS | 坑 |
|---|---|---|---|
| **内核** | 乐鑫的 FreeRTOS 分支，带 SMP | 上游 FreeRTOS 单核 | — |
| **核数** | ESP32-S3 双核，`xTaskCreatePinnedToCore` | **单核**，没有 `PinnedToCore` | 移植时删掉所有 `PinnedToCore` 调用 |
| **优先级范围** | `configMAX_PRIORITIES` = 25（0–24，数字大 = 高） | 默认 7（0–6，**数字大 = 高，规则一样**） | 你在 ESP32 上用优先级 10 的任务，搬到 STM32 会创建失败（>6） |
| **栈单位** | `xTaskCreate` 的深度是**字节** | 原生是**字**；`osThreadNew` 是**字节** | **差 4 倍，最致命的坑** |
| **idle 任务栈** | `CONFIG_FREERTOS_IDLE_TASK_STACKSIZE` | `configMINIMAL_STACK_SIZE`（字） | 蓝 Pill 默认 128 字 = 512 B |
| **中断分配** | `esp_intr_alloc()`，自动处理优先级 | 手动 `HAL_NVIC_SetPriority` + `EnableIRQ` | STM32 要自己算优先级 |
| **ISR 里能调 API 的优先级限制** | ESP-IDF 内部处理 | **`configMAX_SYSCALL_INTERRUPT_PRIORITY` 限制** | **见 5.5，最容易 HardFault 的地方** |
| **软件定时器** | `esp_timer`（独立于 FreeRTOS） | `xTimerCreate`（FreeRTOS 软件定时器，跑在 timer task 里） | ESP-IDF 的 `esp_timer_get_time()` 没对应，用 `xTaskGetTickCount()` |
| **堆** | `heap_caps_malloc(MALLOC_CAP_DMA)` 等多区域堆 | 单一堆（`heap_1..heap_5`） | STM32 没有 DMA 专用堆概念 |
| **看门狗** | Task WDT + Interrupt WDT，自动 | 需手动喂 IWDG，或用 `esp_task_wdt` 的替代（自己实现） | STM32 上没东西帮你检测「任务卡死」 |
| **日志** | `ESP_LOGI/W/E`，有等级、时间戳、颜色 | 无，要自己 `printf` + 环形缓冲 | 建议自己写一个 `LOG_xxx` 宏 |
| **事件循环** | `esp_event_loop` | 无对应，用队列自己搭 | — |
| **组件化** | `idf_component_register()` + CMake | 无，靠 `.c/.h` 手动加进工程 | **见第 4 章** |
| **API 前缀** | `esp_*` / `xTask*` 混用 | 原生 `xTask*`/`vTask*` 或 CMSIS `os*` | 别在一个工程里混用两套（会重定义） |

#### 5.5 ⚠️ NVIC 优先级 vs FreeRTOS（**这一节是 HardFault 重灾区**）

**规则**：任何**调用了 `xxxFromISR()` API 的中断**，它的**抢占优先级数值必须 ≥ `configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY`**。

**为什么**：FreeRTOS 靠 `BASEPRI` 寄存器屏蔽中断来保护临界区。`BASEPRI` 只能屏蔽「优先级数值 ≥ 某个值」的中断。如果你把一个用 FreeRTOS API 的中断设成优先级 0（最高），`BASEPRI` 屏蔽不了它，它就会在 FreeRTOS 的临界区里插进来操作内核链表 → **链表损坏 / HardFault / 随机死机**。

**CubeMX 生成的默认值（`FreeRTOSConfig.h`）**：

```c
#define configPRIO_BITS                          4      /* STM32 实现了 4 位优先级 */
#define configLIBRARY_LOWEST_INTERRUPT_PRIORITY  15
#define configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY  5  /* ← 关键数字 */

#define configKERNEL_INTERRUPT_PRIORITY \
    (configLIBRARY_LOWEST_INTERRUPT_PRIORITY << (8 - configPRIO_BITS))
#define configMAX_SYSCALL_INTERRUPT_PRIORITY \
    (configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY << (8 - configPRIO_BITS))
```

**换算表（`configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY = 5` 时）**：

| 你想要的抢占优先级 | 允许在 ISR 里调 FreeRTOS API？ | 说明 |
|---|---|---|
| 0（最高） | ❌ **绝对禁止** | 只能用于不调用任何 FreeRTOS API 的极紧急中断 |
| 1–4 | ❌ **禁止** | 同上 |
| **5–15** | ✅ 允许 | 安全区 |
| 15（最低） | ✅ 允许 | |

**在 CubeMX 里配**：`NVIC Settings` 里每个中断的 `Preemption Priority` 填 **≥ 5**，只要你打算在它的 ISR 里用 `xQueueSendFromISR` / `xSemaphoreGiveFromISR`。

**FreeRTOS 自带断言会抓这个**（如果 `configASSERT` 已定义）：

```c
/* port.c 里 */
configASSERT( ucCurrentPriority >= ucMaxSysCallPriority );
```

CubeIDE 里默认 `configASSERT` 定义在 `FreeRTOSConfig.h`，触发时会进 `vAssertCalled()` 并死循环 —— **调试时把断点打在这里，能立刻发现优先级配错了**。

**NVIC 分组的坑（F1 特有）**：

| 概念 | 说明 |
|---|---|
| **优先级分组** | STM32 把 4 位优先级拆成「抢占位 + 子优先级位」。分组决定怎么拆 |
| `NVIC_PRIORITYGROUP_4` | 4 位抢占 / 0 位子优先级。**HAL_Init() 的默认值，也是 FreeRTOS 要求的配置** |
| `NVIC_PRIORITYGROUP_3` | 3 位抢占 / 1 位子优先级 |
| … | … |
| `NVIC_PRIORITYGROUP_0` | 0 位抢占 / 4 位子优先级 |
| **陷阱 1** | 只有**抢占优先级**决定「能否打断」，**子优先级只在同时挂起时决定谁先跑**，不能抢占 |
| **陷阱 2** | 用 FreeRTOS 时必须用 `NVIC_PRIORITYGROUP_4`。如果你中途改成 `GROUP_2`，`configMAX_SYSCALL_INTERRUPT_PRIORITY` 的换算就错了 |
| **陷阱 3** | `HAL_NVIC_SetPriority(IRQn, PreemptPriority, SubPriority)` 的两个参数是**未移位的原始值（0–15）**；而 CMSIS 的 `NVIC_SetPriority(IRQn, priority)` 要的是**已移位到高 4 位的值**。两者不通用！ |
| **陷阱 4** | `HAL_NVIC_SetPriority` 的 `SubPriority` 参数在 `GROUP_4` 下**被完全忽略**。很多人填了子优先级却发现没效果 |

> `HAL_Init()` 里默认设成哪一组，**以你工程的 `stm32f1xx_hal.c` 实际代码为准**（`HAL_Init()` 里有 `HAL_NVIC_SetPriorityGrouping(...)` 这一行，去读一眼确认）。

#### 5.6 单核调度的坑

| 坑 | 现象 | 解法 |
|---|---|---|
| **高优先级任务不阻塞** | 低优先级任务永远不跑（饿死） | 高优先级任务必须有 `vTaskDelay` / 队列阻塞 / 信号量等待。`taskYIELD()` 只能让给**同优先级**任务 |
| **任务里 `HAL_Delay()`** | 调度器被阻塞，其他任务卡住 | `HAL_Delay` 是忙等（轮询 `uwTick`），**必须换成 `vTaskDelay(pdMS_TO_TICKS(ms))`** |
| **优先级反转** | 高优先级任务等低优先级任务释放锁 | 用 **互斥量**（`xSemaphoreCreateMutex`，FreeRTOS 有优先级继承），不要用二值信号量当锁 |
| **ISR 里调非 FromISR 版本** | HardFault / 断言失败 | 所有 `xQueueSend` / `xSemaphoreGive` / `xTaskNotifyGive` 在 ISR 里都要加 `FromISR` 后缀 |
| **在 ISR 里 `vTaskDelay`** | 死机 | ISR 里不能阻塞 |
| **任务栈溢出** | 随机 HardFault，改代码位置就"好了" | 开 `configCHECK_FOR_STACK_OVERFLOW 2` + `uxTaskGetStackHighWaterMark` |
| **堆耗尽** | `xTaskCreate` 返回 `errCOULD_NOT_ALLOCATE_REQUIRED_MEMORY` | 加大 `configTOTAL_HEAP_SIZE`，但 20KB RAM 是硬上限 |
| **`printf` 无锁** | 多任务打印时串口输出乱码交错 | 用互斥量包住 `printf`，或自己写带锁的 `log_printf` |
| **空闲任务被喂狗** | 用 IWDG 时低优先级空闲任务跑不到 | 别在空闲任务里喂狗，改用专门的中优先级任务 |

---

### 阶段 6：综合项目（预计 24–40 小时）

#### 6.1 三个候选方案（按对「飞控方向」的价值排序）

| 方案 | 覆盖的技术点 | 对飞控的价值 | 难度 |
|---|---|---|---|
| **A. 自平衡小车** | MPU6050 + PID + PWM + 编码器 + FreeRTOS + 串口调参 | ★★★★★ 直接对应飞控的姿态环 | 中 |
| **B. 单轴无刷云台** | MPU6050 + 互补滤波/卡尔曼 + SimpleFOC + TIM1 互补PWM + 电流采样 | ★★★★★ 对应飞控的电机控制 | 高 |
| **C. 便携式数据记录仪** | ADC+DMA + SPI Flash + FatFS + FreeRTOS + 低功耗 | ★★☆ 对应你的 Modbus 工具思路，但对飞控帮助小 | 中 |

**推荐：先做 A（自平衡小车），有余力再做 B。**

> 理由：方案 A 用到的 **姿态解算 + 串级 PID + 电机 PWM + 编码器测速**，是飞控的「单轴简化版」。做完 A，你已经理解了飞控 80% 的控制逻辑，剩下的只是 3 轴 + 混控矩阵 + 传感器融合。

#### 6.2 方案 A：自平衡小车 —— 详细拆解

**硬件清单（蓝 Pill 版）**：

| 元件 | 型号/规格 | 数量 | 备注 |
|---|---|---|---|
| 主控 | STM32F103C8T6 蓝 Pill | 1 | 已有 |
| 姿态传感器 | MPU6050 (GY-521) | 1 | I2C1，PB6/PB7 |
| 电机驱动 | TB6612FNG 或 DRV8833 模块 | 1 | 双路 H 桥 |
| 电机 | N20 减速电机（带霍尔编码器） | 2 | 6V/12V，减速比 1:30 左右 |
| 编码器 | 电机自带霍尔编码器（A/B 相） | 2 | 接 TIM2/TIM4 编码器模式 |
| 电源 | 2S 锂电（7.4V）+ 降压到 5V/3.3V | 1 | 或 4×AA 电池盒 |
| 车体 | 亚克力/3D 打印底板 + 轮子 | 1 套 | — |
| 调试 | USB-TTL | 1 | 已有 |
| 屏幕 | ILI9341（可选，显示姿态） | 1 | 已有 |
| 蜂鸣器 | 有源蜂鸣器 | 1 | 报警/提示 |

**软件架构（FreeRTOS 任务划分）**：

| 任务 | 优先级 | 栈（字） | 周期 | 职责 |
|---|---|---|---|---|
| `vTaskAttitude` | **5**（最高） | 384 | 5ms（200Hz） | 读 MPU6050、互补滤波、算 pitch/pitch_rate |
| `vTaskControl` | **4** | 256 | 5ms（200Hz） | 串级 PID：外环角度 → 内环角速度 → PWM |
| `vTaskEncoder` | 3 | 128 | 10ms（100Hz） | 读编码器、算速度 |
| `vTaskComm` | 2 | 384 | 事件驱动 | 串口收调参命令、上报数据 |
| `vTaskDisplay` | 1 | 384 | 100ms | ILI9341 刷姿态数据 |
| `vTaskLed` | 1 | 64 | 500ms | 心跳灯 |

**任务间通信**：

```
vTaskAttitude --[队列 q_att]--> vTaskControl
vTaskEncoder  --[队列 q_spd]--> vTaskControl
vTaskControl  --[队列 q_dbg]--> vTaskComm / vTaskDisplay
vTaskComm     --[队列 q_cfg]--> vTaskControl  (调参)
```

**串级 PID 骨架（可直接编译）：**

```c
/* ==================== pid.h ==================== */
#ifndef PID_H
#define PID_H

typedef struct {
    float kp, ki, kd;
    float integral;
    float i_limit;      /* 积分限幅 */
    float out_limit;    /* 输出限幅 */
    float prev_meas;
    float prev_out;
    float d_lpf_alpha;  /* 微分低通系数 0~1，越小越平滑 */
} pid_t;

void  pid_init(pid_t *p, float kp, float ki, float kd,
               float i_limit, float out_limit, float d_lpf_alpha);
void  pid_reset(pid_t *p);
float pid_step(pid_t *p, float setpoint, float meas, float dt);

#endif
```

```c
/* ==================== pid.c ==================== */
#include "pid.h"

void pid_init(pid_t *p, float kp, float ki, float kd,
              float i_limit, float out_limit, float d_lpf_alpha)
{
    p->kp = kp; p->ki = ki; p->kd = kd;
    p->i_limit = i_limit;
    p->out_limit = out_limit;
    p->d_lpf_alpha = d_lpf_alpha;
    pid_reset(p);
}

void pid_reset(pid_t *p)
{
    p->integral  = 0.0f;
    p->prev_meas = 0.0f;
    p->prev_out  = 0.0f;
}

float pid_step(pid_t *p, float setpoint, float meas, float dt)
{
    float err, deriv, out;

    if (dt <= 0.0f) { return p->prev_out; }

    err = setpoint - meas;

    /* 积分（带限幅，防积分饱和） */
    p->integral += p->ki * err * dt;
    if (p->integral >  p->i_limit) { p->integral =  p->i_limit; }
    if (p->integral < -p->i_limit) { p->integral = -p->i_limit; }

    /* 微分（对测量值微分，避免 setpoint 突变产生微分尖峰）+ 低通 */
    deriv = -p->kd * (meas - p->prev_meas) / dt;
    deriv = p->d_lpf_alpha * deriv + (1.0f - p->d_lpf_alpha) * p->prev_out;
    p->prev_meas = meas;

    out = p->kp * err + p->integral + deriv;

    if (out >  p->out_limit) { out =  p->out_limit; }
    if (out < -p->out_limit) { out = -p->out_limit; }

    p->prev_out = out;
    return out;
}
```

```c
/* ==================== balance.c 控制任务核心 ==================== */
#include "FreeRTOS.h"
#include "task.h"
#include "pid.h"
#include "mpu6050.h"
#include "main.h"

extern I2C_HandleTypeDef hi2c1;
extern TIM_HandleTypeDef htim3;    /* PWM: PB0 = 左电机, PB1 = 右电机 */
extern TIM_HandleTypeDef htim2;    /* 编码器 */
extern TIM_HandleTypeDef htim4;    /* 编码器 */

#define CTRL_DT_S      0.005f       /* 5ms */
#define PWM_ARR        999.0f
#define PITCH_TARGET   0.0f         /* 目标角度：直立 */

static pid_t s_pid_angle;           /* 外环：角度 → 角速度目标 */
static pid_t s_pid_rate;            /* 内环：角速度 → PWM */
static pid_t s_pid_speed;           /* 速度环（可选，叠加到角度目标） */

void control_init(void)
{
    /* 先用保守参数，靠串口在线调 */
    pid_init(&s_pid_angle, 8.0f,  0.0f,  0.0f,  200.0f, 300.0f, 1.0f);
    pid_init(&s_pid_rate,  1.2f,  0.0f,  0.02f, 300.0f, 900.0f, 0.3f);
    pid_init(&s_pid_speed, 0.5f,  0.02f, 0.0f,  100.0f,  15.0f, 1.0f);

    HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_3);
    HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_4);
    HAL_TIM_Encoder_Start(&htim2, TIM_CHANNEL_ALL);
    HAL_TIM_Encoder_Start(&htim4, TIM_CHANNEL_ALL);
}

static void motor_set(float left, float right)
{
    /* left/right 范围 -1000 ~ +1000，对应 PWM 占空比 */
    uint32_t l, r;
    float    a;

    /* 左电机：PB0 (TIM3_CH3) 调占空比，方向靠另一路 GPIO 或 H 桥 IN1/IN2 */
    a = (left < 0.0f) ? -left : left;
    if (a > PWM_ARR) { a = PWM_ARR; }
    l = (uint32_t)a;

    a = (right < 0.0f) ? -right : right;
    if (a > PWM_ARR) { a = PWM_ARR; }
    r = (uint32_t)a;

    __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_3, l);
    __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_4, r);

    /* 方向控制：TB6612 的 AIN1/AIN2、BIN1/BIN2 用 GPIO 控制，这里略 */
    /* HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, (left  >= 0.0f) ? GPIO_PIN_SET : GPIO_PIN_RESET); */
    /* HAL_GPIO_WritePin(GPIOB, GPIO_PIN_13, (right >= 0.0f) ? GPIO_PIN_SET : GPIO_PIN_RESET); */
}

void vTaskControl(void *arg)
{
    (void)arg;

    TickType_t last_wake = xTaskGetTickCount();
    const TickType_t period = pdMS_TO_TICKS(5u);

    float pitch = 0.0f;         /* 来自姿态任务（这里简化成局部变量） */
    float gyro_y = 0.0f;
    float rate_sp, out;

    for (;;)
    {
        /* 1. 外环：角度 PID，输出角速度目标 */
        rate_sp = pid_step(&s_pid_angle, PITCH_TARGET, pitch, CTRL_DT_S);

        /* 2. 内环：角速度 PID，输出 PWM */
        out = pid_step(&s_pid_rate, rate_sp, gyro_y, CTRL_DT_S);

        /* 3. 差速输出（原地平衡，暂不转向） */
        motor_set(out, out);

        /* 4. 严格周期调度：不会累积漂移 */
        vTaskDelayUntil(&last_wake, period);
    }
}
```

**调试顺序（不要跳步）**：

| 步骤 | 做什么 | 成功标准 |
|---|---|---|
| 1 | 单独测 MPU6050，静止读角度 | pitch 漂移 < 0.5°/s |
| 2 | 单独测电机：给固定 PWM | 轮子转，正负号正确 |
| 3 | 单独测编码器 | 手转轮子，计数正负对应方向 |
| 4 | 闭环只开内环（角速度环） | 手推车体，轮子「反抗」 |
| 5 | 加上外环（角度环），Kp 从小往大调 | 车能站住几秒 |
| 6 | 加微分 Kd | 站得稳，不振荡 |
| 7 | 加速度环 | 车不跑偏 |
| 8 | 用串口在线调参 | 能实时改 Kp/Ki/Kd |

**验证方法（看到什么算成功）**：
- 手扶车体倾斜，轮子朝倾斜方向加速（负反馈正确）
- 松手后能自主站立 **≥ 10 秒**
- 轻推一下能恢复平衡
- 串口助手里能看到 200Hz 的姿态数据流，无丢帧

**常见坑**：

| 坑 | 现象 | 原因 |
|---|---|---|
| **反馈极性反了** | 一上电就全速冲向一边 | 电机方向 / 陀螺仪方向 / PID 符号，三者要一致。先把 Kp 设 0，手推车体确认轮子「反向」加速 |
| **MPU6050 安装方向** | 角度符号反 | 传感器轴和车体轴要对齐，记录安装朝向 |
| **控制频率不稳** | PID 抖动 | 必须用 `vTaskDelayUntil`，不能用 `vTaskDelay` |
| **积分饱和** | 车"充电"后突然暴走 | 积分限幅 + 输出限幅 |
| **姿态任务被抢占** | 角度数据延迟，控制不稳 | 姿态任务给最高优先级 |
| **I2C 读 MPU6050 阻塞太久** | 200Hz 跑不到 | 一次读 14 字节（一次事务），不要分 7 次读 |
| **PWM 频率太低** | 电机啸叫刺耳 | 用 20kHz 以上（`PSC=0, ARR=3599` @72MHz → 20kHz） |
| **电源噪声干扰 MPU6050** | 角度数据跳变 | 电机电源和 MCU 电源分开走线，加 LC 滤波；MPU6050 的 VDD 加 100nF + 10μF |
| **共用调试串口和控制** | 调参时控制卡顿 | 上报数据降频（比如 50Hz），或单独一路 UART |

#### 6.3 方案 B：单轴无刷云台（进阶，对飞控价值更高）

**核心技术点**：

| 技术 | 说明 |
|---|---|
| **TIM1 互补 PWM** | TIM1_CH1(PA8) / CH1N(PB13) 驱动半桥，需要 `__HAL_TIM_MOE_ENABLE()` 开主输出 |
| **死区时间** | `sBreakDeadTimeConfig.DeadTime` 配置，防止上下桥直通 |
| **三相电流采样** | 用 ADC + 注入通道（`HAL_ADCEx_InjectedStart`），和 PWM 同步采样 |
| **无感/有感换相** | 有霍尔用霍尔，无感用反电动势过零检测 |
| **SimpleFOC** | 开源 FOC 库，支持 STM32，可直接用。**需自行核实其对 STM32F1 的支持程度**（F1 无 FPU，FOC 运算会吃力） |
| **卡尔曼滤波** | 比互补滤波更好的姿态解算 |

> ⚠️ **现实建议**：**F103C8 做 FOC 会非常吃力**（72MHz 无 FPU，浮点全靠软件模拟）。做方案 B 建议直接上 **STM32F405 / G431**（见第 5 章换板建议）。

---

## 4. 从 ESP32 迁移到 STM32 的坑清单

> **用法**：阶段 0 之前通读一遍建立印象，之后遇到问题回来查。

### 4.1 工程组织：ESP-IDF 组件化 vs STM32 HAL 库

| 维度 | ESP-IDF | STM32CubeIDE |
|---|---|---|
| **构建系统** | CMake（`idf.py build`） | Eclipse CDT managed build（底层生成 `Debug/makefile` + `Debug/sources.mk`），新版也支持 CMake |
| **模块化** | `idf_component_register(SRCS ... INCLUDE_DIRS ... REQUIRES ...)` 一行搞定，组件自动发现 | **没有组件概念**。新加 `.c` 文件要手动放到 `Core/Src/`，或右键 `Refresh` 让 Eclipse 索引到（Eclipse 会自动编译工程目录下的所有 `.c`） |
| **头文件路径** | `INCLUDE_DIRS` 自动传递 | `Project > Properties > C/C++ Build > Settings > GCC Compiler > Includes` 手动加，或用 `Core/Inc` |
| **依赖管理** | `idf_component.yml` 从组件仓库拉 | 手动拷源码进来 |
| **代码生成** | 无 | **CubeMX 会覆盖 `main.c` / `xxx_it.c` / `stm32f1xx_hal_msp.c`**，所以必须写在 `/* USER CODE BEGIN xxx */` 里 |
| **工程文件** | `CMakeLists.txt`（纯文本，Git 友好） | `.cproject` / `.project`（XML，Git diff 难看但能用） |
| **配置** | `sdkconfig` / `menuconfig` | `.ioc` 文件（XML） |
| **多目标** | `idf.py set-target esp32s3` | 换芯片要新建工程（或改 `.ioc` 后重新生成） |

**关键规则**：

> **CubeMX 生成的文件，只能改 `/* USER CODE BEGIN xxx */` 到 `/* USER CODE END xxx */` 之间的内容。**
> 这 5 个文件是「生成文件」：`main.c`、`stm32f1xx_it.c`、`stm32f1xx_hal_msp.c`、`stm32f1xx_hal_conf.h`、`system_stm32f1xx.c`。
> **自己的代码放新文件**（`app_xxx.c/h`），不要塞进 `main.c`。这样重新生成代码时不会丢。

**从 IDF 迁移的正确姿势**：

```
ESP-IDF 工程                     STM32 工程
─────────────────────────────    ─────────────────────────────
components/
  modbus_diag/
    CMakeLists.txt
    modbus_diag.c          →     Core/Src/modbus_diag.c
    include/modbus_diag.h  →     Core/Inc/modbus_diag.h
  ili9341/
    ili9341.c              →     Core/Src/ili9341.c
    include/ili9341.h      →     Core/Inc/ili9341.h
main/
  main.c                   →     Core/Src/main.c  (只用 USER CODE 区)
```

### 4.2 FreeRTOS：ESP-IDF 封装 vs 原生 API

**已在 5.4 详述，这里给速查表：**

| 你可能习惯写（ESP-IDF） | STM32 原生 FreeRTOS | STM32 CMSIS-RTOS v2 |
|---|---|---|
| `xTaskCreate(fn, "n", 4096, NULL, 5, NULL)` （4096 **字节**） | `xTaskCreate(fn, "n", 1024, NULL, 5, NULL)` （1024 **字**） | `osThreadNew(fn, NULL, &attr)` （attr 里 4096 **字节**） |
| `xTaskCreatePinnedToCore(fn, "n", 4096, NULL, 5, NULL, 1)` | 删掉，只留 6 个参数 | 不存在 |
| `vTaskDelay(pdMS_TO_TICKS(100))` | 一样 | `osDelay(100)` |
| `xQueueCreate(8, sizeof(msg))` | 一样 | `osMessageQueueNew(8, sizeof(msg), NULL)` |
| `xQueueSend(q, &m, portMAX_DELAY)` | 一样 | `osMessageQueuePut(q, &m, 0, osWaitForever)` |
| `xQueueSendFromISR(q, &m, &hpw)` | 一样 | `osMessageQueuePut(q, &m, 0, 0)`（CMSIS 自动判断上下文） |
| `xSemaphoreCreateBinary()` | 一样 | `osSemaphoreNew(1, 0, NULL)` |
| `xSemaphoreCreateMutex()` | 一样 | `osMutexNew(NULL)` |
| `xSemaphoreGiveFromISR(s, &hpw)` | 一样 | `osSemaphoreRelease(s)` |
| `vTaskStartScheduler()` | 一样 | `osKernelStart()` |
| `esp_timer_get_time()` | `xTaskGetTickCount()` | `osKernelGetTickCount()` |
| `ESP_LOGI(TAG, "x=%d", x)` | `printf("x=%d\r\n", x)` | 同左 |
| `esp_task_wdt_reset()` | 无对应（自己喂 IWDG） | 无对应 |
| `heap_caps_malloc(n, MALLOC_CAP_DMA)` | `pvPortMalloc(n)` | `osMemoryPoolAlloc` 或 `pvPortMalloc` |
| `configMAX_PRIORITIES` = 25 | 默认 **7** | 默认 7 |
| `CONFIG_FREERTOS_HZ` = 1000 | `configTICK_RATE_HZ` = 1000 | 同左 |
| `xPortGetFreeHeapSize()` | 一样 | 一样 |
| `uxTaskGetStackHighWaterMark(NULL)` | 一样（单位：**字**） | 一样（单位：**字**） |
| **双核** | **单核** | **单核** |

**双核 vs 单核的实际影响**：

| 场景 | ESP32-S3（双核） | STM32F103（单核） |
|---|---|---|
| 一个任务死循环 | 另一个核的任务还能跑 | **整个系统卡死** |
| 高负载任务 | 可以 pin 到另一个核分担 | 只能靠优先级 + 时间片 |
| 中断处理 | 可以分配给不同核 | 全在同一个核 |
| 优先级设计 | 宽松，错了也还能跑 | **必须严格**，一个高优先级不阻塞的任务就能饿死整个系统 |
| 调试 | 要看两个核的调用栈 | 一个调用栈，简单 |

### 4.3 NVIC 中断优先级分组

**已在 5.5 详述。核心三条：**

1. **用 FreeRTOS 就用 `NVIC_PRIORITYGROUP_4`**（4 位抢占 / 0 位子优先级）。
2. **调 `xxxFromISR()` 的中断，抢占优先级必须 ≥ `configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY`**（CubeMX 默认 5）。
3. **`HAL_NVIC_SetPriority` 传原始值（0–15），`NVIC_SetPriority`（CMSIS）传已移位值**。别混用。

**一个实用优先级规划模板（FreeRTOS 工程）：**

| 中断 | 抢占优先级 | 能在 ISR 里用 FreeRTOS API 吗 |
|---|---|---|
| 电机 PWM 故障 / 刹车 | 0–2 | ❌ 不能（只置硬件标志） |
| SysTick（FreeRTOS tick） | `configKERNEL_INTERRUPT_PRIORITY` | 内核自己管，别动 |
| PendSV | 最低 | 内核自己管，别动 |
| EXTI 按键 / 传感器中断 | 6 | ✅ |
| UART IDLE / DMA 完成 | 6 | ✅ |
| ADC DMA 完成 | 6 | ✅ |
| TIM 周期中断（用于触发任务） | 7 | ✅ |

> 注意：**数值越大优先级越低**。上表 0 最高，7 最低。

### 4.4 时钟树：CubeMX 生成 vs 手写

| 维度 | ESP32 | STM32F103 |
|---|---|---|
| 主频 | 240MHz（S3 双核） | 72MHz 单核 |
| 配置方式 | `esp_pm_configure()` / menuconfig | CubeMX 图形化，或手写 `SystemClock_Config()` |
| 时钟源 | 内部 PLL（40MHz 晶振） | HSE 8MHz 晶振 + PLL x9 |
| 关键约束 | — | **APB1 ≤ 36MHz**、**APB2 ≤ 72MHz**、**ADCCLK ≤ 14MHz**、**USB = 48MHz**、**Flash 等待周期要匹配主频** |
| 改主频 | 简单 | 改 PLL 后要同步改 APB 分频 + Flash latency + 所有外设的波特率/定时器计算 |
| 时钟准确性 | 内部 RC 有偏差 | **HSE 晶振精度决定 UART/CAN/USB 能否工作** |

**CubeMX 生成的 `SystemClock_Config()` 长这样（你要能读懂）：**

```c
void SystemClock_Config(void)
{
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

    /* 1. 开 HSE，配 PLL */
    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    RCC_OscInitStruct.HSEState       = RCC_HSE_ON;
    RCC_OscInitStruct.HSEPredivValue = RCC_HSE_PREDIV_DIV1;
    RCC_OscInitStruct.HSIState       = RCC_HSI_ON;
    RCC_OscInitStruct.PLL.PLLState   = RCC_PLL_ON;
    RCC_OscInitStruct.PLL.PLLSource  = RCC_PLLSOURCE_HSE;
    RCC_OscInitStruct.PLL.PLLMUL     = RCC_PLL_MUL9;      /* 8MHz x 9 = 72MHz */
    if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
    {
        Error_Handler();
    }

    /* 2. 切系统时钟 + 配总线分频 */
    RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK
                                | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    RCC_ClkInitStruct.SYSCLKSource   = RCC_SYSCLKSOURCE_PLLCLK;
    RCC_ClkInitStruct.AHBCLKDivider  = RCC_SYSCLK_DIV1;    /* HCLK  = 72MHz */
    RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;      /* PCLK1 = 36MHz */
    RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;      /* PCLK2 = 72MHz */

    /* 3. 第二个参数是 Flash 等待周期：72MHz 需要 2 */
    if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK)
    {
        Error_Handler();
    }
}
```

**陷阱**：

| 陷阱 | 后果 |
|---|---|
| **HSE 起振失败没处理** | `HAL_RCC_OscConfig` 返回 `HAL_ERROR`，CubeMX 生成的代码进 `Error_Handler()` 死循环。蓝 Pill 上常见（晶振批次问题） |
| **改了主频没改 `HSE_VALUE`** | `HAL_RCC_GetSysClockFreq()` 返回值不对，所有基于它算波特率的代码全错 |
| **APB1 超 36MHz** | 定时器、I2C、USART2/3 全部工作异常。**注意：APB1 分频 ≠ 1 时，TIM2/3/4 的时钟会被自动 x2**（36MHz×2 = 72MHz），这是 F1 的特性，算 PWM 频率时别搞错 |
| **Flash latency 少了** | 高主频下随机取指错误 → 随机 HardFault。**这是"跑飞"的头号原因之一** |
| **没开 `__HAL_RCC_AFIO_CLK_ENABLE()`** | EXTI 的 AFIO 映射不生效（F1 特有，F4 没有 AFIO） |

### 4.5 链接脚本 / 启动文件 / 内存布局

**ESP32 上你完全看不到这些东西**（IDF 帮你隐藏了分区表、内存映射）。STM32 上必须面对。

**CubeIDE 工程里的关键文件**：

| 文件 | 作用 | 能改吗 |
|---|---|---|
| `STM32F103C8Tx_FLASH.ld` | 链接脚本，定义 Flash/RAM 地址、各段位置、栈堆大小 | ✅ 能改（比如改栈大小） |
| `startup_stm32f103xb.s` | 启动文件，定义中断向量表 + 复位后初始化（拷贝 .data、清零 .bss、调 `main`） | ⚠️ 谨慎，改中断向量表要小心 |
| `system_stm32f1xx.c` | `SystemInit()`，时钟树的一部分 | ⚠️ 一般不改 |

**链接脚本的核心内容（CubeIDE 生成的）：**

```ld
/* STM32F103C8Tx_FLASH.ld 关键片段 */
_estack = 0x20005000;       /* 栈顶 = RAM 起始 0x20000000 + 20KB */
_Min_Heap_Size  = 0x200;    /* 堆至少 512 字节（给 malloc 用） */
_Min_Stack_Size = 0x400;    /* 主栈至少 1KB（给中断和 main 用） */

MEMORY
{
  RAM   (xrw) : ORIGIN = 0x20000000, LENGTH = 20K    /* ← 20KB SRAM */
  FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 64K    /* ← 64KB Flash */
}

SECTIONS
{
  .isr_vector : { ... } >FLASH     /* 中断向量表，必须在 Flash 开头 */
  .text       : { ... } >FLASH     /* 代码 */
  .rodata     : { ... } >FLASH     /* 常量 */
  .data       : { ... } >RAM AT> FLASH   /* 已初始化全局变量：存在 Flash，启动时拷到 RAM */
  .bss        : { ... } >RAM       /* 未初始化全局变量：启动时清零，不占 Flash */
  ...
}
```

**关键概念对照表**：

| 概念 | 在 ESP32 上 | 在 STM32 上 |
|---|---|---|
| 代码放哪 | Flash（通过 cache 映射到地址空间） | Flash @ 0x08000000，通过总线直接取指 |
| 已初始化全局变量 | 自动 | 存在 Flash 里，**启动时由启动文件拷到 RAM**（`.data` 段） |
| 未初始化全局变量 | 自动清零 | 启动文件清零（`.bss` 段） |
| `const` 全局变量 | 放 Flash | 放 `.rodata`（Flash），不占 RAM |
| 栈 | 每个任务独立栈，IDF 自动分配 | 主栈（MSP）在链接脚本里，任务栈自己 `xTaskCreate` 分配 |
| 堆 | `heap_caps` 多区域 | `_Min_Heap_Size`（给 `malloc`）+ FreeRTOS 的 `configTOTAL_HEAP_SIZE`（给 `pvPortMalloc`），**两个独立** |

**常见改动（你一定会遇到）**：

| 想做什么 | 怎么改 |
|---|---|
| 加大主栈（ISR 太深导致溢出） | `STM32F103C8Tx_FLASH.ld` 里把 `_Min_Stack_Size = 0x400` 改成 `0x800`（2KB） |
| 加大 FreeRTOS 堆 | CubeMX 里改 `TOTAL_HEAP_SIZE`，或直接改 `FreeRTOSConfig.h` 的 `configTOTAL_HEAP_SIZE` |
| Flash 用到 128KB（部分 C8 芯片实际有） | 改 `.ld` 里的 `LENGTH = 64K` → `128K`。**但这是超规格使用，不可靠，别在正经产品里这么干** |
| 看 RAM 用了多少 | 编译后看 `Debug/*.map` 文件，搜 `.bss` / `.data` 段大小；或 CubeIDE 的 `Build Analyzer`（`Project > Build Analyzer`） |
| 看 Flash 用了多少 | 同上，看 `.text` + `.rodata` 之和 |

**「跑飞」和内存的关系**：

- 栈溢出会**静默地覆盖相邻的全局变量**（不会立刻崩），症状是「某个全局变量莫名其妙变了」。
- **20KB RAM 下，栈溢出是头号疑难杂症**。用 `uxTaskGetStackHighWaterMark` 和 `-fstack-usage` 编译选项量化。

### 4.6 调试手段差异

| 维度 | ESP32-S3（你熟悉的） | STM32F103 蓝 Pill |
|---|---|---|
| **调试接口** | 内置 USB-JTAG（S3 有）/ 外接 JTAG | **SWD**（SWDIO=PA13, SWCLK=PA14），只需 2 根线 |
| **调试器** | ESP32-S3 内置 USB，或 ESP-Prog | **ST-Link V2**（克隆版十几块） |
| **软件** | `idf.py openocd` + `idf.py gdb` | CubeIDE 内置 GDB，或 OpenOCD + `arm-none-eabi-gdb` |
| **日志** | `ESP_LOGx` + `idf.py monitor`，有等级/时间戳/颜色 | **没有**。要自己 `printf` 重定向，或 SEGGER RTT |
| **SWO / ITM 单线跟踪** | 不适用 | ⚠️ **STM32F1 的 SWO/ITM 基本不可用**（PB3 虽复用为 TRACESWO，但官方未支持，社区普遍反馈无法使用 —— **需自行核实**） |
| **SEGGER RTT** | 可用（`esp-idf` 有支持） | 可用（J-Link 官方支持；OpenOCD 也有 RTT 支持） |
| **单步 / 断点** | 可以，但双核要选核 | **体验好得多**，可以单步进中断，看寄存器、外设寄存器 |
| **寄存器视图** | 有限 | **很强**。CubeIDE 的 `SVD` 视图能看到所有外设寄存器实时值 |
| **复位行为** | 复位后可能被 ROM bootloader 接管 | 干净，`monitor reset halt` 后直接停在 `Reset_Handler` |
| **实时变量监视** | 一般 | CubeIDE 的 **Live Expressions** 可以不停机看变量（靠 SWD 后台读取，会拖慢一点） |

**CubeIDE 调试配置（必做）**：

| 位置 | 设置 |
|---|---|
| `Run > Debug Configurations > Debugger` | Interface: **SWD**，Frequency: **4MHz**（连不上就降到 1MHz） |
| 同上 | `Reset behaviour`: **Connect under reset**（程序跑飞/进低功耗时救命） |
| 同上 | 勾选 `Enable live expressions`（如果要用） |
| `Window > Show View > Registers` | 打开寄存器视图 |
| `Run > Debug Configurations > SVD` | 加载 `STM32F103xx.svd`，之后能在 `Peripherals` 视图看外设寄存器 |

**OpenOCD + GDB 命令行调试（阶段 6 会用到）**：

```bash
# 终端 1：启动 OpenOCD
openocd -f interface/stlink.cfg -f target/stm32f1x.cfg

# 终端 2：启动 GDB
arm-none-eabi-gdb Debug/MyProject.elf
(gdb) target extended-remote localhost:3333
(gdb) monitor reset halt
(gdb) load
(gdb) monitor reset init
(gdb) break main
(gdb) continue
```

> ⚠️ 具体的 `.cfg` 文件名和路径随 OpenOCD 版本变化（可能是 `interface/stlink-v2.cfg`），**需自行核实**自己安装的 OpenOCD 的 `scripts/` 目录内容。

**printf 调试 vs 断点调试的选择**：

| 场景 | 用什么 |
|---|---|
| 看周期性数据流 | printf + 环形缓冲（不阻塞） |
| 看某个变量在崩之前的最后值 | 断点 + Live Expressions |
| 看时序问题（谁先谁后） | **逻辑分析仪**（几十块的 8 通道，配 PulseView）或 GPIO 翻转 + 示波器 |
| 看 HardFault 原因 | 断在 `HardFault_Handler`，读 CFSR/HFSR/BFAR |
| 看 RTOS 任务状态 | `vTaskList()` / `uxTaskGetSystemState()` 打印到串口 |
| 看不出来的偶发问题 | SEGGER RTT（不占串口，速度快） |

### 4.7 常见「程序跑飞」排查路径

**按这个顺序排查，90% 的问题能定位：**

```
程序跑飞 / HardFault / 随机死机
│
├─ 1. 先看是不是【时钟问题】
│    ├─ Flash latency 对不对？（72MHz 必须 2 WS）
│    ├─ HSE 起振了吗？（跑 HAL_RCC_OscConfig 的返回值）
│    ├─ APB1 有没有超 36MHz？
│    └─ 症状：跑起来后随机崩、改个无关代码就好了/坏了
│
├─ 2. 再看是不是【栈溢出】
│    ├─ 主栈（MSP）：加大 .ld 里的 _Min_Stack_Size
│    ├─ 任务栈：uxTaskGetStackHighWaterMark(NULL) 看剩余
│    ├─ 局部大数组：uint8_t buf[1024] 放栈上 = 直接爆
│    └─ 症状：某个全局变量莫名变了、函数返回地址错乱、改栈大小就好了
│
├─ 3. 再看是不是【NVIC 优先级配错】
│    ├─ 调了 xxxFromISR() 的中断，抢占优先级 < 5？
│    ├─ NVIC 分组不是 GROUP_4？
│    ├─ 在 ISR 里调了非 FromISR 版本？
│    └─ 症状：一进中断就死、configASSERT 触发、vAssertCalled 死循环
│
├─ 4. 再看是不是【在中断里做了不该做的事】
│    ├─ HAL_Delay() 在 ISR 里 → 死锁
│    ├─ printf/HAL_UART_Transmit（阻塞）在 ISR 里 → 拖慢或死锁
│    ├─ 大循环 / 浮点运算在 ISR 里 → 拖慢
│    └─ 症状：中断频率一高就卡死
│
├─ 5. 再看是不是【指针 / 数组越界】
│    ├─ NULL 指针解引用
│    ├─ 数组越界写（尤其是 DMA 缓冲区）
│    ├─ 释放后使用 / 重复释放
│    └─ 症状：HardFault，CFSR 的 IMPRECISERR 或 PRECISERR 置位
│
├─ 6. 再看是不是【DMA 配置错】
│    ├─ F1 通道和外设不匹配？（硬连线）
│    ├─ 缓冲区在栈上（函数返回后失效）？
│    ├─ 缓冲区太小 / 长度参数写错？
│    └─ 症状：数据错乱、DMA 传输完成中断不触发
│
└─ 7. 最后看【硬件】
     ├─ 供电不足（USB 口带不动电机）
     ├─ 晶振/复位脚受干扰
     ├─ SWD 线太长（> 15cm 容易连不上）
     └─ 症状：手碰一下就复位、加负载就崩
```

**HardFault 定位代码（可直接编译，**强烈建议现在就加到你的工程里**）：**

```c
/* ==================== fault_dump.c ==================== */
#include <stdint.h>

/* 这些地址来自 ARM Cortex-M3 的 SCB（System Control Block） */
#define SCB_CFSR_ADDR   (0xE000ED28UL)   /* Configurable Fault Status Register */
#define SCB_HFSR_ADDR   (0xE000ED2CUL)   /* HardFault Status Register */
#define SCB_MMFAR_ADDR  (0xE000ED34UL)   /* MemManage Fault Address */
#define SCB_BFAR_ADDR   (0xE000ED38UL)   /* BusFault Address */

/* 故障时压栈的 8 个寄存器 + 可能扩展的 18 个 */
typedef struct {
    uint32_t r0;
    uint32_t r1;
    uint32_t r2;
    uint32_t r3;
    uint32_t r12;
    uint32_t lr;
    uint32_t pc;
    uint32_t xpsr;
} stack_frame_t;

/* 定义在下面，供汇编跳转 */
void hard_fault_report(uint32_t *sf) __attribute__((noinline, used));

/* 这些变量在调试器的 Watch 窗口里看 */
volatile uint32_t g_cfsr  = 0u;
volatile uint32_t g_hfsr  = 0u;
volatile uint32_t g_mmfar = 0u;
volatile uint32_t g_bfar  = 0u;
volatile uint32_t g_fault_pc = 0u;
volatile uint32_t g_fault_lr = 0u;

void hard_fault_report(uint32_t *sf)
{
    stack_frame_t *p = (stack_frame_t *)sf;

    g_cfsr     = *(volatile uint32_t *)SCB_CFSR_ADDR;
    g_hfsr     = *(volatile uint32_t *)SCB_HFSR_ADDR;
    g_mmfar    = *(volatile uint32_t *)SCB_MMFAR_ADDR;
    g_bfar     = *(volatile uint32_t *)SCB_BFAR_ADDR;
    g_fault_pc = p->pc;
    g_fault_lr = p->lr;

    /* 在这里打断点。然后在 Watch 窗口看上面 6 个变量：
       - g_fault_pc 就是出错的那条指令地址（在 .map 里搜 / 或反汇编）
       - g_cfsr 的位含义：
           bit  0  IACCVIOL   取指访问违例
           bit  1  DACCVIOL   数据访问违例
           bit  8  IBUSERR    取指总线错误
           bit  9  PRECISERR  精确数据总线错误（BFAR 有效）
           bit 10  IMPRECISERR 非精确总线错误（写操作延迟报错，常见于野指针写）
           bit 16 UNDEFINSTR  未定义指令（常见于跳到了数据区）
           bit 17 INVSTATE    非法状态（Thumb 位丢失，常见于函数指针错）
           bit 18 INVPC       非法 PC 装载
           bit 24 UNALIGNED   非对齐访问
           bit 25 DIVBYZERO   除零
       - g_hfsr bit30 = FORCED，表示有可配置故障升级成了 HardFault
    */
    for (;;) { }
}

/* 用汇编取出正确的栈指针（MSP 还是 PSP），再跳进 C 函数 */
__attribute__((naked)) void HardFault_Handler(void)
{
    __asm volatile (
        "tst lr, #4         \n"   /* 看 EXC_RETURN 的 bit2 */
        "ite eq             \n"
        "mrseq r0, msp      \n"   /* bit2=0 → 用的是 MSP */
        "mrsne r0, psp      \n"   /* bit2=1 → 用的是 PSP（任务上下文） */
        "b hard_fault_report\n"
    );
}
```

**用法**：
1. 把这个文件加进工程。
2. 在 `hard_fault_report()` 的 `for (;;)` 那行打断点。
3. 跑飞时程序会停在这里，Watch 窗口看 `g_fault_pc` 和 `g_cfsr`。
4. 用 `g_fault_pc` 去 `Debug/*.map` 里搜，或者在 CubeIDE 的反汇编视图里跳过去，就能看到是哪一行代码。

> ⚠️ `__attribute__((naked))` 的函数里**不能有任何 C 代码**，只能写汇编。这是 GCC 的要求。上面的写法符合。
> 如果你同时用了 FreeRTOS，`HardFault_Handler` 不会被 FreeRTOS 覆盖（FreeRTOS 只改 SVC/PendSV/SysTick），可以直接用。

### 4.8 其他零散但会咬人的坑

| 坑 | 说明 |
|---|---|
| **`__weak` 函数覆盖** | HAL 的回调函数（`HAL_GPIO_EXTI_Callback`、`HAL_UART_RxCpltCallback` 等）都是 `__weak` 的，你在别处定义同名同签名的函数就能覆盖。**签名必须完全一致**，否则链接器不会报错，你的函数就是个死函数 |
| **`Error_Handler()` 是死循环** | CubeMX 生成的 `Error_Handler()` 里有 `__disable_irq(); while(1){}`。程序卡死在这里很常见，**在 `while(1)` 上打断点，往回看调用栈**就能知道是哪个初始化失败了 |
| **F1 的 AFIO** | F1 有独立的 AFIO 时钟（`__HAL_RCC_AFIO_CLK_ENABLE()`），F4 没有。用 EXTI 重映射、TIM 重映射时必须开 |
| **复用功能重映射** | F1 支持把 USART1 从 PA9/PA10 重映射到 PB6/PB7。要用 `__HAL_AFIO_REMAP_USART1_ENABLE()`，且必须先开 AFIO 时钟 |
| **SWJ 引脚复用** | PA13/PA14/PA15/PB3/PB4 默认是 SWD/JTAG。如果你想用它们做 GPIO，必须 `__HAL_AFIO_REMAP_SWJ_NOJTAG()` 或 `..._DISABLE()` 释放。**一旦禁用了 SWD 就再也连不上了，除非用 BOOT0 或 NRST** |
| **VBAT 域的引脚** | PC13/PC14/PC15 在 VBAT 供电域，输出电流上限 **3mA**，且翻转速度慢。不要用它们驱动需要速度或电流的东西 |
| **F1 的 GPIO 没有 `Alternate` 参数** | F1 的 GPIO 初始化结构体里没有 `Alternate` 字段（F4 有）。F1 靠 `Mode = GPIO_MODE_AF_PP` 就够了 |
| **`HAL_Delay()` 的最小分辨率** | 依赖 SysTick 的 1ms 中断。要微秒级延时用 DWT 的 CYCCNT 计数器 |
| **DWT 微秒延时（F1 可用）** | `CoreDebug->DEMCR \|= CoreDebug_DEMCR_TRCENA_Msk; DWT->CYCCNT = 0; DWT->CTRL \|= DWT_CTRL_CYCCNTENA_Msk;` 然后读 `DWT->CYCCNT` 算微秒。**需自行核实**在 F1 上是否稳定可用（有些资料说 F1 的 DWT 计数器有缺陷） |

**DWT 微秒延时实现（可直接编译，调试期很有用）：**

```c
/* ==================== dwt_delay.h ==================== */
#ifndef DWT_DELAY_H
#define DWT_DELAY_H
#include <stdint.h>

void     dwt_init(void);
void     dwt_delay_us(uint32_t us);
uint32_t dwt_get_cycles(void);

#endif
```

```c
/* ==================== dwt_delay.c ==================== */
#include "dwt_delay.h"
#include "stm32f1xx.h"

static uint32_t s_cycles_per_us = 72u;

void dwt_init(void)
{
    /* 使能跟踪与调试模块 */
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;

    /* 清零并启动周期计数器 */
    DWT->CYCCNT = 0u;
    DWT->CTRL  |= DWT_CTRL_CYCCNTENA_Msk;

    s_cycles_per_us = SystemCoreClock / 1000000u;   /* 72MHz → 72 */
}

void dwt_delay_us(uint32_t us)
{
    uint32_t start = DWT->CYCCNT;
    uint32_t ticks = us * s_cycles_per_us;

    while ((DWT->CYCCNT - start) < ticks)
    {
        /* 忙等 */
    }
}

uint32_t dwt_get_cycles(void)
{
    return DWT->CYCCNT;
}
```

> ⚠️ `DWT->CYCCNT` 是 32 位，72MHz 下约 **59.6 秒**溢出一次。单次延时不要超过几秒。
> ⚠️ 有些资料反馈 STM32F1 的 DWT CYCCNT 不可靠，**建议自己实测验证**（用 `dwt_delay_us(1000)` 配合示波器测 GPIO 翻转）。

---

## 5. 蓝 Pill（STM32F103C8T6）的具体约束

### 5.1 资源清单

| 资源 | 蓝 Pill 有 | 说明 |
|---|---|---|
| 内核 | **Cortex-M3 @ 72MHz** | 单核，1.25 DMIPS/MHz |
| **FPU** | ❌ **没有** | 浮点靠软件模拟。一次 `float` 乘法约 20–50 周期（vs 硬件 1 周期）。**做 PID/FOC 时要考虑** |
| Flash | **64KB**（官方标称） | 部分 C8 芯片实际有 128KB 可用，但**超规格，不可靠** |
| SRAM | **20KB** | 真正的瓶颈。FreeRTOS 堆 + 任务栈 + DMA 缓冲 + 全局变量，全在这里 |
| GPIO | 37 个 | 5V 容忍（大部分引脚） |
| 定时器 | TIM1（高级）+ TIM2/3/4（通用） | **没有 TIM5/6/7/8** |
| ADC | 2 个（ADC1/ADC2），12 位，10 通道 | 最高 14MHz ADCCLK |
| **DAC** | ❌ **F1 全系没有 DAC** | 要模拟输出只能用 PWM + RC 滤波 |
| DMA | **仅 DMA1，7 个通道** | 通道↔外设硬连线，无 DMAMUX |
| I2C | 2（I2C1/I2C2） | **有硬件 errata** |
| SPI | 2（SPI1/SPI2） | SPI1 最高 36MHz |
| USART | 3（USART1/2/3） | USART1 挂 APB2（72MHz），USART2/3 挂 APB1（36MHz） |
| USB | 1（全速 12Mbps 设备） | **需要外部 1.5kΩ 上拉到 DP** |
| CAN | 1（bxCAN） | **需要外部 CAN 收发器**（如 TJA1050） |
| 比较器 | ❌ 没有 | F3/G4 才有 |
| 运放 | ❌ 没有 | F3/G4 才有 |
| RTC | 1 | 需要 32.768kHz 晶振（蓝 Pill 板上有） |
| 看门狗 | IWDG + WWDG | |
| **唯一 ID** | ✅ 96 位 | 可用于设备序列号 |

### 5.2 20KB RAM 的实际影响（**这是最硬的约束**）

**做个算术**：

| 项目 | 占用 |
|---|---|
| 主栈（`_Min_Stack_Size`） | 1KB |
| 主堆（`_Min_Heap_Size`） | 0.5KB |
| 全局变量 + 静态变量（`.data` + `.bss`） | 2–4KB（用 HAL 库 + 一些缓冲） |
| **剩下给 FreeRTOS 的** | **约 14–16KB** |
| FreeRTOS 内核对象（TCB、队列、信号量） | 1–2KB |
| **实际可分配给任务栈的** | **约 12–14KB** |
| 一个带 `printf` 的任务（384 字 = 1.5KB） | 1.5KB |
| 一个姿态任务（384 字） | 1.5KB |
| 一个控制任务（256 字） | 1KB |
| 一个显示任务（384 字） | 1.5KB |
| 一个通信任务（384 字） | 1.5KB |
| 空闲任务 + 定时器任务 | 0.5 + 1 KB |
| **小计** | **约 8.5KB** |

**结论**：**20KB 下最多跑 5–6 个任务，且不能有大的静态缓冲区。**

**必须遵守的规则**：

| 规则 | 原因 |
|---|---|
| **不要开 `USE_TIMERS`**（除非真要用） | 软件定时器任务要额外 1KB 栈 |
| **不要在栈上放 > 256 字节的数组** | 用 `static` |
| **`configTOTAL_HEAP_SIZE` 不要超过 12KB** | 要留余量给 `.bss` 和栈 |
| **不要用 `sprintf`**，用 `snprintf` 且缓冲区 ≤ 128 字节 | `sprintf` 内部可能用几百字节栈 |
| **不要开 `-u _printf_float`**（除非真需要） | 浮点 printf 会多占约 1.5KB Flash + 大量栈 |
| **DMA 缓冲用 `static`** | 必须是常驻内存 |
| **LCD 的行缓冲用 `static`** | `uint8_t line[480]` 放栈上会爆 |
| **编完看 Build Analyzer** | 实时监控 RAM 使用率，别等到跑飞才发现 |

### 5.3 蓝 Pill **不能**做什么

| 不能做 | 原因 | 替代方案 |
|---|---|---|
| **跑大型 RTOS 应用（10+ 任务）** | 20KB RAM 不够 | 换 F405（192KB RAM） |
| **做浮点密集运算（FOC、卡尔曼、FFT）** | 无 FPU，软件浮点慢 20–50 倍 | 换 F405/F411（有 FPU）/ H743 |
| **跑 MicroPython / 大型文件系统** | 64KB Flash + 20KB RAM | 换 F405/F407（1MB Flash） |
| **跑 Linux** | 无 MMU | 换 F7/H7 也不行，要 A 系列（如 Allwinner） |
| **高速 USB（480Mbps）** | 只有全速 USB（12Mbps） | 换 F405/F407（有 USB OTG HS） |
| **以太网** | 无 MAC | 换 F407/F427 |
| **驱动大屏幕（>320×240 全彩 + 高帧率）** | SPI 只有 36MHz，RAM 不够做帧缓冲 | 换 F4 + FSMC/FMC 并口屏 |
| **同时用多路 DMA 外设** | 只有 DMA1 的 7 个通道，且硬连线 | 换 F4（DMA1+DMA2，16 通道） |
| **做高精度模拟输出** | 无 DAC | 换 F4（有 DAC），或 PWM + 滤波 |
| **做电机 FOC** | 无 FPU + 无高级定时器的完整功能 + 无运放/比较器 | 换 G431（专为电机控制设计，有 CORDIC/FMAC/运放/比较器） |
| **做音频处理** | 无 I2S + 无 FPU + RAM 不够 | 换 F411/F407（有 I2S） |
| **做图像处理** | 无 DCMI + RAM 不够 | 换 F429/F767（有 DCMI + 大 RAM） |
| **长期稳定运行的工业产品** | 部分批次的晶振/电源设计有隐患（克隆板尤其） | 自己画板（见 6.1），或换官方 Nucleo 板 |

### 5.4 什么时候该换板

| 场景 | 推荐芯片 | 理由 | 开发板推荐 |
|---|---|---|---|
| **学完蓝 Pill，要做飞控** | **STM32F405RGT6 / F411CEU6** | 有 FPU、168MHz、192/128KB RAM、1MB Flash，**Betaflight/ArduPilot 的主流选择** | 自制 F405 飞控板 / MatekF405 / 官方 STM32F411 Nucleo |
| **要做 ArduPilot / PX4** | **STM32H743VIT6** | 480MHz、双精度 FPU、1MB RAM、2MB Flash，**PX4 官方主控** | Pixhawk 6X / 自制 H743 板 |
| **要做电机 FOC / ESC** | **STM32G431CBU6** | 170MHz、FPU、CORDIC/FMAC 硬件加速、内置运放+比较器、专为电机控制 | 官方 NUCLEO-G431RB / SimpleFOC 社区板 |
| **要学 RoboMaster（大疆生态）** | **STM32F427IIH6** | RoboMaster 开发板 A 型的主控（**已核实**） | 买官方 RoboMaster 开发板 A 型 |
| **要做高端 DSP/音频** | **STM32F411 / F407** | FPU + I2S + 大 RAM | 官方 STM32F411E-DISCO |
| **要做低成本量产** | **STM32G030 / G071** | 便宜、够用、生态好 | 自制 |

**换板建议（给你）**：

> **蓝 Pill 学完阶段 0–5 就够本了。阶段 6 的自平衡小车可以用蓝 Pill 做完（验证你的控制逻辑），但一旦要碰「3 轴姿态解算 + 无刷电机 FOC + 高速日志」，立刻换 F405。**
>
> **不要用蓝 Pill 硬撑飞控项目。** 你会把 80% 的时间花在「RAM 又不够了」「浮点太慢了」上，而不是学飞控本身。

**换板的信号（出现任意一条就该换）**：

- `configTOTAL_HEAP_SIZE` 已经调到 14KB，还有任务创建失败
- 一个 PID 循环跑不到 1kHz（想跑到 4kHz 做内环）
- 想用 `float` 做矩阵运算 / 卡尔曼滤波
- 需要同时用 3 路以上 DMA 外设
- 需要 USB 和 CAN 同时用
- Flash 已经用到 90%（64KB 里 58KB）

### 5.5 蓝 Pill 的硬件坑（克隆板特有）

| 坑 | 说明 |
|---|---|
| **USB 上拉电阻不对** | 部分克隆板把 DP 的 1.5kΩ 上拉画成了 10kΩ，导致 USB 设备无法被主机识别 |
| **晶振质量差** | 便宜的 8MHz 晶振 + 不匹配的负载电容 → HSE 起振失败或频率偏差。**UART 会乱码，USB 会枚举失败** |
| **BOOT0 跳线设计** | 有些板子的 BOOT0 跳线帽默认位置不对，烧完不跑 |
| **PC13 LED 亮度** | 蓝 Pill 的 LED 串的是 470Ω 或 1kΩ，很暗，正常 |
| **SWD 排针顺序** | 不同克隆板的 4 针 SWD 顺序可能不同（有的把 3.3V 和 GND 调换）。**接线前用万用表确认** |
| **3.3V 稳压器** | 部分板子用 RT9193 或 AMS1117，输出电流 300mA–800mA。**带不动电机**，电机要独立供电 |
| **VDDA 没有滤波** | 蓝 Pill 的 VDDA 直接接 3.3V，ADC 精度受数字噪声影响。要更高精度需自己加 LC 滤波 |
| **无源晶振负载电容** | 蓝 Pill 板上是 20pF 或 22pF。如果换晶振要重算 |

---

## 6. 与目标方向的衔接

### 6.1 做 PCB：从蓝 Pill 最小系统板开始

**目标**：自己画一块「蓝 Pill 等价」的 STM32F103C8T6 最小系统板，打样、焊接、烧录、跑通。

> 你已经有立创EDA + 焊接能力，所以这部分的「新知识」只有：**MCU 最小系统的电源/晶振/复位/去耦设计规范**。

#### 元件清单（BOM）

| 序号 | 元件 | 规格 | 数量 | 封装 | 备注 |
|---|---|---|---|---|---|
| 1 | MCU | **STM32F103C8T6** | 1 | LQFP-48 | |
| 2 | LDO | **AMS1117-3.3** | 1 | SOT-223 | 5V→3.3V，输出 800mA（会发热） |
| 3 | 输入电容 | 10μF / 16V | 1 | 0805 | LDO 输入 |
| 4 | 输出电容 | 22μF / 10V | 1 | 0805 | LDO 输出（AMS1117 需要 ≥ 22μF 才稳） |
| 5 | 去耦电容 | 100nF / 50V | 6 | 0402/0603 | 每个 VDD 脚一个，紧贴引脚 |
| 6 | 体电容 | 4.7μF / 10V | 1 | 0805 | VDD 总线上一个 |
| 7 | VDDA 滤波 | 铁氧体磁珠 600Ω@100MHz | 1 | 0603 | 3.3V → VDDA |
| 8 | VDDA 电容 | 100nF + 1μF | 各 1 | 0402/0603 | VDDA 到 GND |
| 9 | HSE 晶振 | **8MHz**，负载电容 20pF | 1 | 5032 或 HC-49SMD | |
| 10 | HSE 负载电容 | 20pF（或按晶振 CL 计算） | 2 | 0402 | |
| 11 | LSE 晶振 | 32.768kHz | 1 | 3215 | 可选（用 RTC 才需要） |
| 12 | LSE 负载电容 | 12pF | 2 | 0402 | |
| 13 | 复位电阻 | 10kΩ 上拉到 3.3V | 1 | 0402 | NRST 有内部上拉，外部加更稳 |
| 14 | 复位电容 | 100nF | 1 | 0402 | NRST 到 GND |
| 15 | 复位按键 | 轻触开关 3×4mm | 1 | — | |
| 16 | BOOT0 跳线 | 2.54mm 排针 1×3 | 1 | — | 或焊盘跳线 |
| 17 | BOOT0 电阻 | 10kΩ 下拉 | 1 | 0402 | 默认从 Flash 启动 |
| 18 | 用户 LED | 0805 贴片 LED | 1 | 0805 | 接 PC13 |
| 19 | LED 限流电阻 | 1kΩ | 1 | 0402 | PC13 限流 3mA，1kΩ 合适 |
| 20 | 电源 LED | 0805 贴片 LED | 1 | 0805 | 电源指示 |
| 21 | 电源 LED 电阻 | 1kΩ | 1 | 0402 | |
| 22 | USB 接口 | **Type-C 16P**（或 Micro-USB） | 1 | — | |
| 23 | USB 匹配电阻 | 22Ω | 2 | 0402 | D+/D- 串联 |
| 24 | **USB DP 上拉** | **1.5kΩ** 到 3.3V | 1 | 0402 | ⚠️ **STM32F103 无内部上拉，必须外置** |
| 25 | USB ESD 保护 | USBLC6-2SC6 | 1 | SOT-23-6 | 可选但推荐 |
| 26 | SWD 排针 | 2.54mm 排针 1×4 | 1 | — | 3.3V / SWDIO / SWCLK / GND |
| 27 | 排针 | 2.54mm 排针 2×20 | 2 | — | 引出所有 IO |
| 28 | 电源开关 | 拨动开关 | 1 | — | 可选 |
| 29 | 5V 输入 | Type-C 或 DC 座 | 1 | — | |

**总成本估算**：约 15–25 元（PCB 打样 5 片约 5 元 + 元件 10–20 元）

#### 关键设计规则（**这几条决定你的板子能不能跑起来**）

| 规则 | 具体要求 | 违反的后果 |
|---|---|---|
| **去耦电容** | 每个 VDD 引脚（VDD1/2/3/4）旁放一个 100nF，走线 **< 3mm**，先过电容再进引脚 | 随机复位、跑飞 |
| **VDDA 滤波** | 3.3V → 铁氧体磁珠 → VDDA，VDDA 到 GND 加 100nF + 1μF | ADC 噪声大，读 MPU6050 时干扰 |
| **晶振布局** | 晶振**紧贴** MCU 的 OSC_IN/OSC_OUT 引脚（< 10mm），负载电容靠近晶振并接地，**晶振下方和周围不走任何其他信号线**，加接地保护环 | HSE 起振失败、频率偏差、UART 乱码 |
| **复位电路** | NRST 上 10kΩ 到 3.3V + 100nF 到 GND，走线短 | 上电不稳定复位 |
| **USB 差分对** | D+/D- 走线等长，差分阻抗约 **90Ω**，尽量短，避免过孔 | USB 枚举失败（全速 USB 容忍度较高，但别乱走） |
| **DP 上拉** | 1.5kΩ 从 PA12 到 3.3V，**必须在 MCU 侧** | USB 设备完全不被识别 |
| **地平面** | 2 层板：顶层走线 + 底层整块 GND。4 层板：信号/GND/电源/信号 | 噪声、EMC 不过 |
| **电源走线宽度** | 3.3V 主回路 ≥ 0.5mm（1oz 铜，1A 电流约需 1mm） | 压降、发热 |
| **SWD 排针** | 引出 3.3V / SWDIO(PA13) / SWCLK(PA14) / GND / NRST | 调试不了 |
| **BOOT0** | 通过 10kΩ 下拉到 GND，跳线可拉到 3.3V | 烧完不跑 |

#### 设计步骤（用立创EDA）

| 步骤 | 做什么 | 检查点 |
|---|---|---|
| 1 | 新建工程，画原理图 | 用官方/社区的原理图做参考，**逐条核对**（尤其去耦电容和 USB 上拉） |
| 2 | 元件选型 + 立创商城匹配 | 确认所有元件有货、有封装库 |
| 3 | 分配 PCB 封装，检查每个封装的引脚编号 | **LQFP-48 的引脚编号容易搞错，对着 datasheet 数一遍** |
| 4 | 布局：先放 MCU（居中），再放晶振、LDO、USB、连接器 | 晶振靠近 MCU；LDO 靠近电源输入；USB 靠板边 |
| 5 | 布线：先走电源，再走差分对，最后走信号 | 晶振走线最短；去耦电容先过再进引脚 |
| 6 | 铺铜：底层整块 GND，顶层也铺 GND 并用多个过孔缝合 | 检查有无孤岛铜皮 |
| 7 | DRC 检查 | 修正所有错误 |
| 8 | 导出 Gerber + BOM + 坐标文件 | 在立创 EDA 的 3D 预览里看一遍 |
| 9 | 打样（嘉立创 5 片约 5 元，2 层，1.6mm，1oz） | |
| 10 | 焊接（先焊 LDO 和 MCU，测 3.3V 正常后再焊其他） | **上电前先用万用表测 3.3V 对 GND 有没有短路** |
| 11 | 烧录测试程序（LED 闪 + 串口打印） | 和蓝 Pill 一样的效果 |

#### 验证清单

- [ ] 上电后 3.3V 电压在 3.25–3.35V 之间
- [ ] 复位按键按下时 NRST 电压为 0V
- [ ] SWD 能连上，能读到芯片 ID
- [ ] 下载程序后 LED 闪烁
- [ ] 串口 115200 打印正常（说明 HSE 起振、时钟准确）
- [ ] USB 插上电脑能被识别为设备（如果是 USB 应用）
- [ ] ADC 读 Vrefint ≈ 1489

#### 进阶：把这个板子改造成飞控底板

在最小系统板基础上加：

| 模块 | 器件 | 接口 |
|---|---|---|
| IMU | ICM-42688-P 或 MPU6000 | SPI1 |
| 气压计 | BMP388 / DPS310 | I2C1 |
| 磁力计 | QMC5883L / IST8310 | I2C1 |
| 黑匣子 | W25Q128 | SPI2 |
| 电机输出 | 4 路 PWM（TIM1/TIM4） | 排针 |
| RC 输入 | SBUS（UART 反相） | USART2 |
| 图传/OSD | UART | USART3 |
| 电源 | 5V BEC + 3.3V LDO + 电流/电压检测 | ADC |

> **参考开源飞控硬件**：Betaflight 的 target 定义、Holybro/Matek 的飞控原理图（公开）。**这些是最直接的学习材料**。

### 6.2 做飞控：STM32 学完哪些阶段才够

#### 能力映射表

| 飞控需要的能力 | 对应本路线阶段 | 够不够 |
|---|---|---|
| GPIO / 定时器 / PWM | 阶段 1 | ✅ |
| 串口通信（RC 输入、GPS、图传） | 阶段 2 | ✅ |
| IMU 驱动（SPI/I2C） | 阶段 3 | ✅ |
| 传感器采样 + DMA | 阶段 4 | ✅ |
| RTOS 多任务调度 | 阶段 5 | ✅ |
| **姿态解算（互补滤波 / 卡尔曼）** | 阶段 6 方案 A | ⚠️ 只学了入门 |
| **串级 PID 控制** | 阶段 6 方案 A | ✅ |
| **无刷电机 FOC / DShot** | 阶段 6 方案 B | ⚠️ 蓝 Pill 做不动 |
| **传感器融合（IMU + 气压 + 磁 + GPS）** | ❌ 未覆盖 | ❌ 需另外学 |
| **混控矩阵（4 轴/6 轴）** | ❌ 未覆盖 | ❌ 需另外学 |
| **失控保护 / 故障检测** | ❌ 未覆盖 | ❌ 需另外学 |
| **MAVLink / MSP 协议** | ❌ 未覆盖 | ❌ 需另外学 |
| **PCB 设计（飞控板）** | 6.1 | ✅ 入门 |
| **C++（大疆 SDK 是 C++）** | ❌ 未覆盖 | ❌ **需补** |

#### 下一步路线（蓝 Pill 学完之后）

```
【你现在的位置】蓝 Pill 学完阶段 0–5
        │
        ├── 并行推进 ──────────────────────────────┐
        │                                          │
        ▼                                          ▼
  【硬件线】                                【软件线】
  阶段 6.1 画最小系统板                      阶段 6 方案 A 自平衡小车
  → 打样焊接调试                            → 姿态解算 + 串级 PID
  → 加 IMU/气压计/黑匣子                     → 串口在线调参
        │                                          │
        └──────────────┬───────────────────────────┘
                       ▼
              【换板：STM32F405】
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   【路线 A】      【路线 B】      【路线 C】
   用开源飞控      自己写飞控       走大疆生态
   Betaflight      (从零实现)      RoboMaster
   ├ 刷固件        ├ 移植 FreeRTOS  ├ 买 A 型开发板(F427)
   ├ 读源码        ├ 写 IMU 驱动    ├ 学官方 SDK (C++)
   ├ 改配置        ├ 姿态解算       ├ 做步兵/英雄机器人
   ├ 自己设计板子  ├ 串级 PID       ├ 参加 RoboMaster 比赛
   └ 调参          ├ 混控          └ 简历上写"大疆生态开发经验"
                   ├ DShot 输出
                   ├ MSP/MAVLink
                   └ 黑匣子日志
                       │
                       ▼
              【终极：ArduPilot / PX4】
              STM32H743 + ChibiOS/NuttX
```

**建议路径（给你的具体情况）**：

> **走「路线 B（自己写飞控）+ 路线 C（RoboMaster）双线」。**
>
> - 路线 B 让你真正理解飞控的每一行代码 —— 这是面试时能讲出东西的关键。
> - 路线 C 让你有大疆生态的实战经验 —— 这是**直接对口大疆招聘**的加分项（RoboMaster 参赛经历是大疆校招的强偏好）。
> - 路线 A（改 Betaflight）作为调剂，用它验证你对飞控概念的理解。

#### 飞控方向需要补的知识（不在本路线范围内，但要提前知道）

| 知识 | 为什么需要 | 怎么学 |
|---|---|---|
| **控制理论** | PID 只是入门，飞控要用到 LQR、ADRC、模型预测控制 | 自动控制原理教材 + MATLAB/Simulink 仿真 |
| **姿态表示** | 欧拉角有万向锁，飞控用四元数 | 《Quaternion kinematics for the error-state Kalman filter》 |
| **传感器融合** | 单一 IMU 不够，要融合气压/磁/GPS | Mahony / Madgwick 算法，EKF |
| **C++** | 大疆 RoboMaster SDK、PX4 都是 C++ | 《Effective C++》+ 读 PX4 源码 |
| **通信协议** | MAVLink / MSP / DShot / SBUS / CRSF | 协议文档 + 抓包分析 |
| **嵌入式 Linux** | 高端飞控用 Linux 跑感知算法 | 树莓派 + ROS |
| **电机与电调** | 无刷电机、FOC、DShot | SimpleFOC 项目 + 电调拆解 |
| **PCB 高速设计** | 飞控板的 IMU 走线、电源完整性 | 从 6.1 的最小系统板开始积累 |

### 6.3 简历上怎么写这段学习经历

#### 模板 1：STM32 学习经历（放在「项目经历」或「技能」栏）

**❌ 不要这样写**（没有信息量）：

> 学习了 STM32 单片机，掌握了 GPIO、定时器、串口、I2C、SPI、ADC、FreeRTOS 等外设。

**✅ 应该这样写**：

> **STM32F103 裸机 + RTOS 底层驱动实践**（个人项目 / 2026.09–2026.12）
>
> - 基于 STM32F103C8T6（Cortex-M3 @72MHz，64KB Flash / 20KB SRAM），独立完成从 CubeMX 时钟树配置到外设驱动的全流程开发
> - 实现 **UART + DMA + IDLE 空闲中断**的不定长帧接收，配合自研环形缓冲（1KB），在 115200bps 下连续收包零丢帧，CPU 占用从轮询方案的 ~100% 降至 <5%
> - 驱动 **MPU6050**（I2C1 @400kHz），实现 14 字节单事务读取 + 互补滤波姿态解算，200Hz 姿态输出；针对 STM32F1 I2C 总线死锁 errata 实现 GPIO 位翻转恢复机制
> - 设计 **ADC 双通道 + DMA1 循环采样**，配合定时器 TRGO 触发实现等间隔 1kHz 采样，采样率误差仅取决于晶振精度
> - 移植 **FreeRTOS**（heap_4），按 5 级优先级划分姿态/控制/通信/显示/心跳任务，用队列解耦数据流；通过 `uxTaskGetStackHighWaterMark` 把总 RAM 占用控制在 14KB 以内
> - 编写 **HardFault 现场转储机制**（读取 CFSR/HFSR/BFAR + 解析压栈 PC），将偶发死机问题的定位时间从数小时缩短至分钟级

#### 模板 2：自平衡小车（放「项目经历」首位）

> **基于 STM32 + FreeRTOS 的两轮自平衡机器人**（个人项目 / 2026.11–2026.12）
>
> - 硬件：STM32F103C8T6 + MPU6050 + TB6612 双路 H 桥 + 带霍尔编码器 N20 减速电机，自制亚克力车体
> - 软件：FreeRTOS 五任务架构，姿态任务 200Hz 最高优先级，串级 PID（外环角度 200Hz / 内环角速度 200Hz），采用 `vTaskDelayUntil` 保证严格周期调度
> - 关键实现：微分项对测量值求导 + 一阶低通（抑制设定值突变尖峰）；积分分离 + 抗积分饱和；互斥量保护串口调参
> - 结果：**静态自主平衡 > 60 秒**，受扰后 0.5 秒内恢复；支持串口在线调参（Kp/Ki/Kd 实时下发，无需重新烧录）
> - 该项目是**四旋翼飞控的单轴简化模型**，姿态解算与串级 PID 架构可直接迁移至多旋翼

#### 模板 3：PCB 设计经历

> **STM32F103C8T6 最小系统板设计与验证**（个人项目 / 2026.12）
>
> - 基于立创EDA 完成原理图与 2 层 PCB 设计（40×60mm），含 LDO 电源、8MHz HSE 晶振、USB Type-C（含 1.5kΩ DP 上拉）、SWD 调试口、复位与 BOOT0 电路
> - 遵循 MCU 最小系统设计规范：每 VDD 引脚 100nF 去耦（走线 <3mm）、VDDA 经铁氧体磁珠隔离滤波、晶振区域接地保护环、USB 差分对 90Ω 阻抗控制
> - 完成打样、贴片焊接、上电测试全流程；板子通过 SWD 下载程序，串口 115200 通信正常，ADC 读 Vrefint 误差 <1%
> - 在此基础上扩展设计 **STM32F405 飞控底板**（IMU 走 SPI1、气压计走 I2C1、黑匣子走 SPI2、4 路 DShot 输出）

#### 模板 4：技能栏写法

> **嵌入式开发**
> - MCU：STM32F1/F4（HAL 库、CubeMX）、ESP32-S3（ESP-IDF）；熟悉 Cortex-M 架构、NVIC 优先级管理、启动流程与链接脚本
> - RTOS：FreeRTOS（原生 API 与 CMSIS-RTOS v2）、ESP-IDF FreeRTOS；任务优先级设计、栈水位分析、队列/信号量/互斥量应用
> - 外设驱动：GPIO/EXTI、TIM（PWM/输入捕获/编码器）、UART（DMA+IDLE）、I2C、SPI、ADC（DMA+定时器触发）、CAN、USB
> - 通信协议：Modbus RTU、RS-485、UART、SPI、I2C、CAN
> - 调试：SWD/JTAG、GDB + OpenOCD、逻辑分析仪、HardFault 现场分析、内存/栈水位量化
> - 硬件：立创EDA 原理图与 PCB 设计、SMT 焊接、示波器/万用表使用
> - 语言：C（熟练）、C++（在读）、Python（脚本与上位机）

#### 面试时怎么讲这段经历（大疆嵌入式岗）

面试官大概率会问的 3 个问题 + 你应该怎么答：

| 问题 | 你应该答什么（要点） |
|---|---|
| **「讲一个你遇到的 bug 和你怎么解决的」** | 讲 **STM32F1 的 I2C BUSY 死锁**：现象（跑几小时后 I2C 全部超时）、排查（用逻辑分析仪抓波形，发现 SDA 被从机拉低）、根因（F1 I2C errata：传输中从机复位导致总线死锁）、解法（实现 GPIO 位翻转恢复：把 SCL/SDA 切成普通 GPIO，手动发 9 个 SCL 脉冲 + STOP 条件，再切回 AF 模式）、验证（连续跑 72 小时无复现） |
| **「你怎么保证系统的实时性」** | 讲 **三个层次**：① 硬件层：ADC 用定时器 TRGO 触发，采样间隔只取决于晶振；② 驱动层：UART 用 DMA + IDLE 中断，CPU 只在帧边界被唤醒；③ 系统层：FreeRTOS 用 `vTaskDelayUntil` 保证严格周期，姿态任务给最高优先级，用 `uxTaskGetStackHighWaterMark` 验证栈余量。**给具体数字**（200Hz、抖动 < 50μs） |
| **「你怎么定位偶发死机」** | 讲 **HardFault 现场转储**：在 `HardFault_Handler` 里用 `tst lr, #4` 判断用的是 MSP 还是 PSP，取出压栈的 PC，读 CFSR/HFSR/BFAR 定位故障类型。举一个实际案例（比如 IMPRECISERR 位 = 野指针写，最后定位到 DMA 缓冲区传了局部变量地址）。**展示你有系统化方法，而不是"print 大法"** |

---

## 7. 时间预算（每周 8–10 小时）

### 7.1 16 周主计划

| 周 | 阶段 | 内容 | 预计时长 | 可压缩 | 交付物 |
|---|---|---|---|---|---|
| **W1** | 阶段 0 | 环境跑通：CubeMX 配时钟树、LED 闪烁、串口 printf | **3h** | ⬇️ **可压到 2h** | 能编译能下载能打印的工程 |
| **W2–W3** | 阶段 1 | GPIO 进阶、EXTI 中断 + 消抖、TIM 定时/PWM/输入捕获/编码器 | **16h** | 部分可压 | 4 个独立 demo |
| **W4** | 阶段 2 | UART + DMA + IDLE + 环形缓冲 | **8h** | ⬇️ **可压到 4h**（你熟 UART/DMA） | 不定长帧接收模块 |
| **W5–W6** | 阶段 3 | I2C 读 MPU6050（含 errata 处理）、SPI 读 W25Q64、SPI 驱动 ILI9341 | **16h** | ⬇️ 屏驱动可压到 2h（复用 ESP32 代码） | 3 个驱动模块 |
| **W7** | 阶段 4 | ADC + DMA 采样、定时器触发、Vrefint 校准 | **6h** | ⬇️ **可压到 3h** | 等间隔采样模块 |
| **W8** | 阶段 5 | FreeRTOS 移植、NVIC 优先级、任务划分、栈水位 | **8h** | ⬇️ **可压到 4h**（你熟 FreeRTOS） | 多任务框架 |
| **W9–W12** | 阶段 6 | 自平衡小车：硬件组装 → 单模块调试 → 闭环调参 | **32h** | ❌ 不建议压 | 能自主平衡的小车 |
| **W13–W14** | 6.1 | PCB 最小系统板：原理图 → 布局布线 → 打样 → 焊接 → 验证 | **16h** | ❌ 不建议压 | 自制开发板 |
| **W15** | 6.2 | 简历整理、项目文档、面试问题准备 | **8h** | 可压到 4h | 简历 + 项目 README |
| **W16** | 6.2 | 飞控预备：读 Betaflight 源码 / 买 RoboMaster 开发板 / 学 C++ | **8h** | — | 下一步计划 |
| | | **合计** | **约 121h（16 周 × 8h）** | | |

### 7.2 压缩版（每周 8h，12 周完成）

**如果你按本路线的压缩建议执行：**

| 周 | 内容 | 时长 | 说明 |
|---|---|---|---|
| W1 | 阶段 0 + 阶段 1 前半（GPIO + EXTI） | 8h | 环境只需 2h，剩下 6h 做 GPIO/EXTI |
| W2 | 阶段 1 后半（TIM 全部） | 8h | PWM/输入捕获/编码器 |
| W3 | 阶段 2（UART+DMA+环形缓冲） | 4h | **跳过 ESP32 已掌握的概念讲解** |
| W3 | 阶段 3 前半（I2C MPU6050） | 4h | 含 F1 I2C errata 处理 |
| W4 | 阶段 3 后半（SPI W25Q64 + ILI9341） | 8h | **直接移植 ESP32 的 ILI9341 初始化表** |
| W5 | 阶段 4（ADC+DMA） | 4h | **跳过 DMA 概念，只学 F1 的 HAL 差异** |
| W5 | 阶段 5（FreeRTOS） | 4h | **跳过 RTOS 概念，只学 CubeMX 配置 + NVIC 陷阱** |
| W6–W9 | 阶段 6（自平衡小车） | 32h | 不压缩 |
| W10–W11 | PCB 最小系统板 | 16h | 不压缩 |
| W12 | 简历 + 飞控预备 | 8h | |
| | **合计** | **约 96h** | 比主计划省 25h |

### 7.3 各阶段「必做 vs 可跳过」清单

| 阶段 | **必做**（不做会踩坑） | **可跳过/压缩**（你已有基础） |
|---|---|---|
| 0 | ① SYS Debug 设 Serial Wire ② 时钟树 72MHz + Flash latency 2WS ③ 串口 printf 重定向 | 点灯本身（你 5 分钟就会） |
| 1 | ① EXTI + NVIC 使能 ② 中断里不能 HAL_Delay ③ TIM 的 PSC/ARR 计算 | GPIO 基础概念（你会） |
| 2 | ① F1 的 DMA 通道硬连线表（**必须背**）② IDLE 中断清标志 ③ DMA 缓冲必须 static | UART 协议、DMA 原理（你会） |
| 3 | ① F1 的 I2C errata 处理（**必做，否则一定踩**）② MPU6050 的 SLEEP 位 ③ SPI 模式 CPOL/CPHA | ② SPI/I2C 时序（你会）③ ILI9341 初始化表（直接抄 ESP32 的） |
| 4 | ① ADCCLK ≤ 14MHz ② `HAL_ADCEx_Calibration_Start` ③ DMA 缓冲是 `uint32_t*` | ADC 原理、DMA 双缓冲（你会） |
| 5 | ① **栈单位是「字」不是字节** ② **NVIC 优先级 ≥ 5** ③ HAL 时基改 TIM2 ④ `HAL_Delay` → `vTaskDelay` | RTOS 概念、队列/信号量用法（你会） |
| 6 | ① 严格周期调度用 `vTaskDelayUntil` ② 反馈极性验证 ③ 串口在线调参 | 传感器驱动（阶段 3 已做） |

### 7.4 每周节奏建议（8–10h 怎么分配）

| 时段 | 时长 | 做什么 |
|---|---|---|
| 工作日晚上（2–3 天） | 每次 1.5h | 读文档 + 写代码 + 编译下载 |
| 周末半天 | 4h | **集中做硬件调试 + 排查问题**（问题通常在硬件侧） |
| 周末另半天 | 2h | 写笔记 / 整理工程 / 更新 README |

**关键建议**：

> **每周留出至少 2 小时做「写文档」**。不是为了交作业，而是为了：
> ① 面试时你有一份可展示的项目 README
> ② 三个月后你自己看得懂当时的代码
> ③ 排查问题时有个「上次是怎么解决的」的记录本

### 7.5 里程碑检查点

| 里程碑 | 时间点 | 达成标准 |
|---|---|---|
| **M1** | W1 末 | 能独立用 CubeMX 建工程、配时钟、写串口打印 |
| **M2** | W4 末 | 能写一个「UART + DMA + IDLE + 环形缓冲」的完整模块，连续收包不丢 |
| **M3** | W7 末 | 能独立驱动 I2C/SPI 传感器，并能处理 F1 的 I2C errata |
| **M4** | W8 末 | 能把裸机程序改造成 FreeRTOS 多任务，且不踩 NVIC/栈的坑 |
| **M5** | W12 末 | 自平衡小车能自主站立 > 60 秒 |
| **M6** | W14 末 | 自制的 PCB 板能跑通程序 |
| **M7** | W16 末 | 简历上有 3 个可讲的项目；明确下一步（飞控/PCB）方向 |

---

## 附录 A：HAL 函数 / 寄存器速查

### A.1 GPIO

| 函数/宏 | 说明 |
|---|---|
| `__HAL_RCC_GPIOA_CLK_ENABLE()` | 开 GPIOA 时钟（同理 GPIOB/...） |
| `HAL_GPIO_Init(GPIO_TypeDef *GPIOx, GPIO_InitTypeDef *GPIO_Init)` | 初始化 |
| `HAL_GPIO_WritePin(GPIOx, GPIO_Pin, GPIO_PinState)` | 写引脚 |
| `HAL_GPIO_ReadPin(GPIOx, GPIO_Pin)` | 读引脚 |
| `HAL_GPIO_TogglePin(GPIOx, GPIO_Pin)` | 翻转 |
| `GPIO_PinState` 取值 | `GPIO_PIN_SET` / `GPIO_PIN_RESET` |
| 寄存器 | `GPIOx->BSRR`（置位/复位）、`GPIOx->ODR`、`GPIOx->IDR`、`GPIOx->CRL`/`CRH`（F1 特有，配置寄存器） |

### A.2 EXTI / NVIC

| 函数/宏 | 说明 |
|---|---|
| `HAL_NVIC_SetPriorityGrouping(NVIC_PRIORITYGROUP_4)` | 设优先级分组 |
| `HAL_NVIC_SetPriority(IRQn_Type, PreemptPriority, SubPriority)` | 设优先级（原始值 0–15） |
| `HAL_NVIC_EnableIRQ(IRQn_Type)` | 使能中断 |
| `HAL_NVIC_DisableIRQ(IRQn_Type)` | 关闭中断 |
| `__HAL_GPIO_EXTI_CLEAR_IT(GPIO_Pin)` | 清 EXTI 挂起标志 |
| `HAL_GPIO_EXTI_IRQHandler(GPIO_Pin)` | 在 `EXTIx_IRQHandler` 里调用 |
| `HAL_GPIO_EXTI_Callback(GPIO_Pin)` | 用户重写的回调（`__weak`） |
| F1 中断向量名 | `EXTI0_IRQHandler` … `EXTI4_IRQHandler`、`EXTI9_5_IRQHandler`、`EXTI15_10_IRQHandler` |
| 寄存器 | `EXTI->IMR`、`EXTI->EMR`、`EXTI->RTSR`、`EXTI->FTSR`、`EXTI->PR`（挂起） |

### A.3 TIM

| 函数/宏 | 说明 |
|---|---|
| `HAL_TIM_Base_Init(&htim)` | 基本定时器初始化 |
| `HAL_TIM_Base_Start(&htim)` | 启动（无中断） |
| `HAL_TIM_Base_Start_IT(&htim)` | 启动 + 开更新中断 |
| `HAL_TIM_PWM_Start(&htim, TIM_CHANNEL_x)` | 启动 PWM |
| `HAL_TIM_IC_Start_IT(&htim, TIM_CHANNEL_x)` | 启动输入捕获 + 中断 |
| `HAL_TIM_Encoder_Start(&htim, TIM_CHANNEL_ALL)` | 启动编码器模式 |
| `__HAL_TIM_SET_COMPARE(&htim, TIM_CHANNEL_x, val)` | 设占空比 |
| `__HAL_TIM_GET_COUNTER(&htim)` | 读计数 |
| `__HAL_TIM_SET_COUNTER(&htim, val)` | 写计数 |
| `__HAL_TIM_SET_AUTORELOAD(&htim, val)` | 设 ARR |
| `HAL_TIM_ReadCapturedValue(&htim, TIM_CHANNEL_x)` | 读捕获值 |
| `__HAL_TIM_SET_CAPTUREPOLARITY(&htim, TIM_CHANNEL_x, pol)` | 设捕获极性 |
| `__HAL_TIM_MOE_ENABLE(&htim1)` | TIM1/TIM8 开主输出（互补 PWM 必须） |
| `HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef*)` | 更新中断回调 |
| `HAL_TIM_PWM_PulseFinishedCallback(...)` | PWM 脉冲完成回调 |
| `HAL_TIM_IC_CaptureCallback(...)` | 输入捕获回调 |
| 关键寄存器 | `TIMx->PSC`、`TIMx->ARR`、`TIMx->CNT`、`TIMx->CCR1..4`、`TIMx->CCMR1/2`、`TIMx->CCER`、`TIMx->BDTR`（TIM1 专有） |

### A.4 UART

| 函数/宏 | 说明 |
|---|---|
| `HAL_UART_Init(&huart)` | 初始化 |
| `HAL_UART_Transmit(&huart, pData, Size, Timeout)` | 阻塞发送 |
| `HAL_UART_Receive(&huart, pData, Size, Timeout)` | 阻塞接收 |
| `HAL_UART_Transmit_IT` / `HAL_UART_Receive_IT` | 中断方式 |
| `HAL_UART_Transmit_DMA` / `HAL_UART_Receive_DMA` | DMA 方式 |
| `HAL_UARTEx_ReceiveToIdle_DMA(&huart, pData, Size)` | DMA + IDLE 一体（CubeF1 HAL ≥1.1.9） |
| `__HAL_UART_ENABLE_IT(&huart, UART_IT_IDLE)` | 使能 IDLE 中断 |
| `__HAL_UART_GET_FLAG(&huart, UART_FLAG_IDLE)` | 读 IDLE 标志 |
| `__HAL_UART_CLEAR_IDLEFLAG(&huart)` | 清 IDLE 标志 |
| `__HAL_UART_CLEAR_OREFLAG(&huart)` | 清溢出错误标志 |
| `HAL_UART_RxCpltCallback` / `TxCpltCallback` / `ErrorCallback` | 回调 |
| `HAL_UARTEx_RxEventCallback(huart, Size)` | IDLE 事件回调 |
| 寄存器 | `USARTx->SR`、`USARTx->DR`、`USARTx->BRR`、`USARTx->CR1/2/3` |

### A.5 I2C

| 函数/宏 | 说明 |
|---|---|
| `HAL_I2C_Init(&hi2c)` | 初始化 |
| `HAL_I2C_IsDeviceReady(&hi2c, DevAddr, Trials, Timeout)` | 探测器件（发地址等 ACK） |
| `HAL_I2C_Master_Transmit(&hi2c, DevAddr, pData, Size, Timeout)` | 主发 |
| `HAL_I2C_Master_Receive(...)` | 主收 |
| `HAL_I2C_Mem_Write(&hi2c, DevAddr, MemAddr, MemAddSize, pData, Size, Timeout)` | 写寄存器 |
| `HAL_I2C_Mem_Read(&hi2c, DevAddr, MemAddr, MemAddSize, pData, Size, Timeout)` | 读寄存器 |
| `I2C_MEMADD_SIZE_8BIT` / `I2C_MEMADD_SIZE_16BIT` | 寄存器地址宽度 |
| `HAL_I2C_Master_Transmit_DMA` / `..._IT` | DMA / 中断方式 |
| `HAL_I2C_ErrorCallback` | 错误回调 |
| 寄存器 | `I2Cx->CR1`、`I2Cx->CR2`、`I2Cx->SR1`、`I2Cx->SR2`、`I2Cx->CCR`、`I2Cx->TRISE`、`I2Cx->DR` |

### A.6 SPI

| 函数/宏 | 说明 |
|---|---|
| `HAL_SPI_Init(&hspi)` | 初始化 |
| `HAL_SPI_Transmit(&hspi, pData, Size, Timeout)` | 只发 |
| `HAL_SPI_Receive(&hspi, pData, Size, Timeout)` | 只收（全双工时自动发 0xFF） |
| `HAL_SPI_TransmitReceive(&hspi, pTx, pRx, Size, Timeout)` | 全双工收发 |
| `HAL_SPI_Transmit_DMA` / `..._IT` | DMA / 中断方式 |
| `HAL_SPI_TxCpltCallback` / `RxCpltCallback` / `TxRxCpltCallback` | 回调 |
| 寄存器 | `SPIx->CR1`、`SPIx->CR2`、`SPIx->SR`、`SPIx->DR` |

### A.7 ADC

| 函数/宏 | 说明 |
|---|---|
| `HAL_ADC_Init(&hadc)` | 初始化 |
| `HAL_ADCEx_Calibration_Start(&hadc)` | **F1 单参数**（F4/F7 双参数，多一个 `ADC_SINGLE_ENDED` / `ADC_CALIB_OFFSET`） |
| `HAL_ADC_Start(&hadc)` | 启动（单次） |
| `HAL_ADC_Start_DMA(&hadc, pData, Length)` | 启动 DMA（**F1 要求 `uint32_t*`**） |
| `HAL_ADC_PollForConversion(&hadc, Timeout)` | 轮询等转换完成 |
| `HAL_ADC_GetValue(&hadc)` | 读结果 |
| `HAL_ADC_ConfigChannel(&hadc, &sConfig)` | 改通道配置 |
| `HAL_ADCEx_InjectedStart(&hadc)` | 启动注入组 |
| `HAL_ADC_ConvCpltCallback` / `ConvHalfCpltCallback` | 转换完成 / 半完成回调 |
| 寄存器 | `ADCx->SR`、`ADCx->CR1`、`ADCx->CR2`、`ADCx->SQR1/2/3`、`ADCx->SMPR1/2`、`ADCx->DR`、`ADCx->JSQR` |

### A.8 DMA

| 函数/宏 | 说明 |
|---|---|
| `HAL_DMA_Init(&hdma)` | 初始化 |
| `HAL_DMA_Start(&hdma, SrcAddress, DstAddress, DataLength)` | 启动（阻塞） |
| `HAL_DMA_Start_IT(&hdma, Src, Dst, Len)` | 启动 + 中断 |
| `HAL_DMA_Abort(&hdma)` | 中止 |
| `HAL_DMA_Abort_IT(&hdma)` | 中止 + 回调 |
| `__HAL_DMA_GET_COUNTER(&hdma)` | 读剩余传输数（F1 上即 `CNDTR`） |
| `__HAL_DMA_ENABLE_IT(&hdma, DMA_IT_HT)` | 开半满中断 |
| `__HAL_DMA_DISABLE_IT(&hdma, DMA_IT_HT)` | 关半满中断 |
| `HAL_DMA_XferCpltCallback` / `XferHalfCpltCallback` / `XferErrorCallback` | 回调 |
| F1 寄存器 | `DMA1_Channelx->CCR`、`CNDTR`、`CPAR`、`CMAR` |
| F1 请求映射 | 见 2.2 表格（**必须记住**） |

### A.9 FreeRTOS（原生 API）

| 函数/宏 | 说明 |
|---|---|
| `xTaskCreate(fn, name, usStackDepth, arg, prio, handle)` | 创建任务，**`usStackDepth` 单位是字** |
| `vTaskDelete(handle)` | 删除任务 |
| `vTaskDelay(ticks)` | 相对延时（可被唤醒提前返回） |
| `vTaskDelayUntil(&lastWake, period)` | **绝对**周期延时（严格周期） |
| `vTaskStartScheduler()` | 启动调度器（不返回） |
| `xQueueCreate(len, itemSize)` | 建队列 |
| `xQueueSend` / `xQueueSendFromISR` | 发送 |
| `xQueueReceive` | 接收 |
| `xSemaphoreCreateBinary` / `xSemaphoreCreateMutex` / `xSemaphoreCreateCounting` | 建信号量/互斥量 |
| `xSemaphoreTake` / `xSemaphoreGive` | 获取/释放 |
| `xSemaphoreGiveFromISR` | ISR 里释放 |
| `xTaskNotifyGive` / `ulTaskNotifyTake` | 轻量级任务通知（比信号量快） |
| `vTaskSuspend` / `vTaskResume` | 挂起/恢复 |
| `uxTaskGetStackHighWaterMark(NULL)` | 当前任务栈最小剩余（**单位：字**） |
| `xPortGetFreeHeapSize()` | 剩余堆 |
| `xTaskGetTickCount()` | 当前 tick |
| `pdMS_TO_TICKS(ms)` | 毫秒 → tick |
| `portYIELD_FROM_ISR(hpw)` | ISR 里触发切换 |
| `taskENTER_CRITICAL()` / `taskEXIT_CRITICAL()` | 临界区（会操作 BASEPRI） |
| `vTaskStartScheduler` 相关钩子 | `vApplicationStackOverflowHook`、`vApplicationMallocFailedHook`、`vApplicationIdleHook`、`vApplicationTickHook` |
| 关键宏（`FreeRTOSConfig.h`） | `configTOTAL_HEAP_SIZE`、`configMINIMAL_STACK_SIZE`、`configMAX_PRIORITIES`、`configTICK_RATE_HZ`、`configCHECK_FOR_STACK_OVERFLOW`、`configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY`、`configUSE_PREEMPTION`、`configUSE_TIME_SLICING` |

### A.10 Cortex-M3 系统寄存器

| 寄存器 | 地址 | 用途 |
|---|---|---|
| `SCB->CFSR` | `0xE000ED28` | 可配置故障状态 |
| `SCB->HFSR` | `0xE000ED2C` | HardFault 状态 |
| `SCB->MMFAR` | `0xE000ED34` | MemManage 故障地址 |
| `SCB->BFAR` | `0xE000ED38` | BusFault 故障地址 |
| `SCB->AIRCR` | `0xE000ED0C` | 优先级分组（`PRIGROUP` 位） |
| `SCB->VTOR` | `0xE000ED08` | 中断向量表偏移（做 Bootloader 必用） |
| `SysTick->CTRL` / `LOAD` / `VAL` / `CALIB` | `0xE000E010` 起 | 系统节拍 |
| `NVIC->ISER[n]` | `0xE000E100` 起 | 中断使能 |
| `NVIC->IP[n]` | `0xE000E400` 起 | 中断优先级 |
| `DWT->CYCCNT` | `0xE0001004` | 周期计数器（做微秒延时） |
| `CoreDebug->DEMCR` | `0xE000EDFC` | 调试控制（bit24 = TRCENA） |

### A.11 常用计算速查

```
PWM 频率   = f_tim_clk / (PSC + 1) / (ARR + 1)
UART 波特率误差 = |实际波特率 - 目标| / 目标 × 100%     (< 2% 可接受，< 1% 更稳)
ADC 转换时间 = (采样周期数 + 12.5) / ADCCLK
ADC 电压     = raw / 4095 × VDDA
STM32F1 的 APB1 分频 ≠ 1 时，TIM2/3/4 时钟 = PCLK1 × 2
STM32F1 的 APB2 分频 ≠ 1 时，TIM1 时钟   = PCLK2 × 2
MPU6050 加速度(g) = raw / 16384   (±2g)
MPU6050 角速度(dps) = raw / 131   (±250dps)
MPU6050 温度(°C) = raw / 340 + 36.53
```

---

## 附录 B：「需自行核实」清单

> 以下内容我在文档里已尽力准确，但**存在版本/批次/具体工程差异**。用之前请自己确认一遍。

| 编号 | 项目 | 位置 | 怎么核实 |
|---|---|---|---|
| B1 | `HAL_Init()` 里默认设的 NVIC 优先级分组 | 5.5 / 4.3 | 打开 `Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal.c`，搜 `HAL_NVIC_SetPriorityGrouping` |
| B2 | CubeF1 HAL 版本是否支持 `HAL_UARTEx_ReceiveToIdle_DMA` | 2.4 | 搜 `Drivers/STM32F1xx_HAL_Driver/Inc/stm32f1xx_hal_uart_ex.h` 里的 `ReceiveToIdle_DMA` |
| B3 | CubeMX 生成的 `FreeRTOSConfig.h` 里 `configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY` 的具体值 | 5.5 | 打开工程的 `Core/Inc/FreeRTOSConfig.h` 直接看 |
| B4 | CubeMX 生成的 `vApplicationStackOverflowHook` 的参数类型（`TaskHandle_t` vs `xTaskHandle`） | 5.3 | 看生成的 `FreeRTOSConfig.h` 里 `configCHECK_FOR_STACK_OVERFLOW` 附近，或看 `portable/.../portmacro.h` 的类型定义 |
| B5 | Keil MDK Community Edition 的免费条款与限制 | 2.1 | 访问 https://www.keil.arm.com/mdk-community/ 看最新条款 |
| B6 | CubeIDE headless build 的具体命令与路径 | 2.1 | 在 CubeIDE 安装目录找 `headless-build.bat`，或看 ST 官方文档 |
| B7 | STM32F1 的 SWO/ITM 是否可用 | 4.6 | 用 ST-Link 试 `SWO` 输出，或用 J-Link 试；社区普遍反馈不可用 |
| B8 | STM32F1 的 DWT->CYCCNT 是否稳定 | 4.8 | 用 `dwt_delay_us(1000)` + 示波器测 GPIO 翻转，看误差 |
| B9 | `__HAL_TIM_SET_CAPTUREPOLARITY` 在中断里调用是否安全 | 1.3 | 实测；或改用双通道捕获（CH1 上升沿 + CH2 下降沿） |
| B10 | OpenOCD 的 `interface/stlink.cfg` 具体文件名 | 4.6 | 看你自己 OpenOCD 安装的 `scripts/interface/` 目录 |
| B11 | RoboMaster 开发板 C 型的主控型号 | 2.2 / 6.2 | 查 RoboMaster 官方产品页；A 型已核实为 STM32F427IIH6 |
| B12 | 部分蓝 Pill 的 STM32F103C8 是否真有 128KB Flash | 5.1 | 用 STM32CubeProgrammer 读 Flash 大小寄存器，或试着往 0x08010000 写数据再读回 |
| B13 | 蓝 Pill 克隆板的 SWD 排针引脚顺序 | 5.5 | 用万用表量一下，确认 3.3V / GND / SWDIO / SWCLK 的位置 |
| B14 | 具体蓝 Pill 板的 HSE 晶振负载电容值 | 6.1 | 看板子上的丝印或测电容；或查你的板子型号的原理图 |
| B15 | SimpleFOC 对 STM32F1 的支持程度 | 6.3 | 查 SimpleFOC 官方文档的 MCU 支持列表 |

---

## 附录 C：推荐学习资源

### 官方文档（**必读，优先级最高**）

| 文档 | 编号 | 用途 |
|---|---|---|
| **STM32F103xx Reference Manual** | **RM0008** | 寄存器级手册。**遇到任何 HAL 搞不定的问题都来这里** |
| **STM32F103x8/xB Datasheet** | **DS5319** | 电气特性、引脚定义、封装、绝对最大额定值 |
| **Cortex-M3 Technical Reference Manual** | DDI 0337 | NVIC、SCB、SysTick、异常模型 |
| **STM32F10xxx Flash Programming Manual** | PM0075 | Flash 编程（做 Bootloader 时用） |
| **AN2586** | — | STM32F10xxx 硬件设计指南（**画 PCB 必读**） |
| **AN4013** | — | STM32 定时器概览 |
| **FreeRTOS 官方文档** | — | https://www.freertos.org/Documentation |

### 中文资源

| 资源 | 说明 |
|---|---|
| 正点原子 STM32F103 教程 | 最全的中文教程，寄存器版 + HAL 库版 |
| 野火 STM32 教程 | 文档质量高，配套视频 |
| 硬汉嵌入式论坛 | STM32 疑难问题 |
| 稚晖君 / 硬件工程师练成之路 | B 站，PCB 和嵌入式 |

### 开源飞控（**阶段 6 之后读**）

| 项目 | 主控 | 语言 | 说明 |
|---|---|---|---|
| **Betaflight** | STM32F4/F7/H7 | C | 穿越机飞控，代码结构清晰，**最好的入门阅读材料** |
| **INAV** | STM32F4/F7 | C | Betaflight 分支，加 GPS 导航 |
| **ArduPilot** | STM32F4/F7/H7 | C++ | 最完整，支持多旋翼/固定翼/车/船/潜艇 |
| **PX4** | STM32F4/F7/H7 | C++ | 学术圈主流，模块化好 |
| **SimpleFOC** | 多平台 | C++ | 无刷电机 FOC 库 |
| **Cleanflight** | — | C | Betaflight 的前身 |

---

## 附录 D：开工检查清单（打印出来贴在桌上）

**硬件**

- [ ] 蓝 Pill × 1
- [ ] ST-Link V2（含 4 根杜邦线）
- [ ] USB-TTL 模块（CH340/CP2102）
- [ ] MPU6050 模块（GY-521）
- [ ] W25Q64 SPI Flash 模块
- [ ] ILI9341 SPI 屏（2.4" 或 2.8"）
- [ ] 面包板 + 杜邦线若干
- [ ] LED × 4 + 1kΩ 电阻 × 4
- [ ] 按键 × 2 + 10kΩ 电阻 × 2
- [ ] 万用表
- [ ] （强烈推荐）逻辑分析仪（8 通道，几十块，配 PulseView）

**软件**

- [ ] STM32CubeIDE（已装）
- [ ] STM32Cube MCU Package for STM32F1（CubeF1）
- [ ] ST-Link 驱动 + 固件升级
- [ ] 串口助手（SSCOM / XCOM / PuTTY / VS Code 串口插件）
- [ ] PulseView（配逻辑分析仪）
- [ ] （可选）VS Code + PlatformIO
- [ ] （可选）arm-none-eabi-gcc + make + OpenOCD

**文档**

- [ ] RM0008（STM32F103 参考手册）—— **下载到本地**
- [ ] DS5319（STM32F103x8/xB 数据手册）
- [ ] AN2586（硬件设计指南）
- [ ] MPU6050 数据手册 + 寄存器手册
- [ ] W25Q64 数据手册
- [ ] ILI9341 数据手册

**代码模板（建议先建好，后面直接抄）**

- [ ] `fault_dump.c/h`（HardFault 转储）
- [ ] `uart_rx.c/h`（DMA + IDLE + 环形缓冲）
- [ ] `ringbuf.c/h`（通用环形缓冲）
- [ ] `dwt_delay.c/h`（微秒延时）
- [ ] `log.c/h`（带互斥锁的日志）
- [ ] `pid.c/h`（PID 控制器）
- [ ] `app_tasks.c/h`（FreeRTOS 任务框架）

---

**文档结束。**

> **最后一句建议**：
> 你的 ESP32 基础让你**跳过了 STM32 学习中最费时间的部分**（概念建立）。你真正要花时间的只有两件事：
> ① **ST 生态的具体 API 和工具链**（2–3 周能过）
> ② **Cortex-M3 裸机的底层细节**（NVIC、时钟、内存布局、跑飞排查）—— **这部分才是从「会用单片机」到「能做飞控」的分水岭**。
>
> 别贪快。阶段 4/5 压缩没问题，但**阶段 1（中断 + 定时器）和阶段 6（综合项目）不要跳**。这两个阶段决定了你在面试时能不能讲出深度。
