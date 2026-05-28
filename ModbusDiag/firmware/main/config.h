#ifndef CONFIG_H
#define CONFIG_H

// ============================================================
// ModbusDiag - 全局配置
// ============================================================

// ---------- 版本 ----------
#define FW_VERSION_MAJOR    1
#define FW_VERSION_MINOR    0
#define FW_VERSION_PATCH    0
#define FW_VERSION_STR      "1.0.0"

// ---------- GPIO分配 ----------
// TFT屏幕 (ILI9488 SPI)
#define PIN_TFT_CS          3
#define PIN_TFT_DC          4
#define PIN_TFT_SCK         6
#define PIN_TFT_MOSI        7
#define PIN_TFT_MISO        8
#define PIN_TFT_RST         9
#define PIN_TFT_BL          10

// 触摸 (FT6236 I2C)
#define PIN_TOUCH_SDA       14
#define PIN_TOUCH_SCL       15
#define PIN_TOUCH_INT       5
#define PIN_TOUCH_RST       13

// RS485 (MAX13487)
#define PIN_RS485_RE        16
#define PIN_RS485_DE        17
#define PIN_RS485_RX        18
#define PIN_RS485_TX        19

// 电池检测
#define PIN_BAT_ADC         20

// RGB LED
#define PIN_LED_R           21
#define PIN_LED_G           22
#define PIN_LED_B           23

// 蜂鸣器
#define PIN_BUZZER          24

// 按键
#define PIN_BTN_UP          25
#define PIN_BTN_DOWN        26
#define PIN_BTN_OK          27
#define PIN_BTN_BACK        28

// ---------- UART配置 ----------
#define UART_DEBUG_NUM      UART_NUM_0
#define UART_DEBUG_BAUD     115200
#define UART_DEBUG_TXD      GPIO_NUM_43
#define UART_DEBUG_RXD      GPIO_NUM_44

#define UART_RS485_NUM      UART_NUM_1
#define UART_RS485_BAUD     9600    // 默认9600，自动扫描时会遍历
#define UART_RS485_TXD      GPIO_NUM_19
#define UART_RS485_RXD      GPIO_NUM_18

// ---------- SPI配置 ----------
#define SPI_TFT_HOST        SPI2_HOST
#define SPI_TFT_CLOCK_HZ    40 * 1000 * 1000  // 40MHz (最大)
#define SPI_TFT_DMA_CHAN    SPI_DMA_CH_AUTO

// ---------- I2C配置 ----------
#define I2C_TOUCH_HOST      I2C_NUM_0
#define I2C_TOUCH_CLOCK_HZ  400000

// ---------- TFT参数 ----------
#define TFT_WIDTH           480
#define TFT_HEIGHT          320
#define TFT_BL_PWM_FREQ     5000
#define TFT_BL_PWM_RES      8     // 8位PWM (0-255)
#define TFT_BL_DEFAULT      128   // 默认50%亮度

// ---------- LVGL配置 ----------
#define LVGL_TICK_PERIOD_MS 5
#define LVGL_TASK_PRIORITY  5
#define LVGL_TASK_STACK     4096

// ---------- Modbus配置 ----------
#define MODBUS_DEFAULT_TIMEOUT  1000  // ms
#define MODBUS_RETRY_COUNT      3
#define MODBUS_SCAN_TIMEOUT     200   // ms per device

// 设备扫描参数
#define SCAN_ADDR_START     1
#define SCAN_ADDR_END       247
#define SCAN_BAUD_RATES     { 1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200 }
#define SCAN_BAUD_COUNT     8

// ---------- 电池阈值 ----------
#define BAT_ADC_R1          100000  // 分压上拉电阻 100kΩ
#define BAT_ADC_R2          10000   // 分压下拉电阻  10kΩ
#define BAT_ADC_REF         3.3f    // ADC参考电压
#define BAT_ADC_RES         4096    // 12位ADC

#define BAT_FULL_VOLTAGE    4.2f    // 满电电压
#define BAT_EMPTY_VOLTAGE   3.3f    // 关机电压
#define BAT_WARN_VOLTAGE    3.5f    // 低电报警

// ---------- WiFi AP模式 ----------
#define WIFI_AP_SSID        "ModbusDiag"
#define WIFI_AP_PASS        "12345678"
#define WIFI_AP_CHANNEL     6
#define WIFI_AP_MAX_CONN    4

// ---------- 协议分析缓冲区 ----------
#define ANALYZER_BUF_SIZE   4096    // 抓包缓冲区字节
#define ANALYZER_WIN_SIZE   200     // 显示窗口(帧数)

// ---------- 日志 ----------
// 注释掉不需要的日志级别
// #define LOG_LOCAL_LEVEL    ESP_LOG_VERBOSE
#define LOG_LOCAL_LEVEL      ESP_LOG_INFO

#endif // CONFIG_H
