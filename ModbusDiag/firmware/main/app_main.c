/**
 * ModbusDiag - 应用主循环
 */
#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "esp_log.h"
#include "driver/gpio.h"
#include "config.h"

#include "modbus_rtu.h"
#include "modbus_tcp.h"
#include "device_scanner.h"
#include "protocol_analyzer.h"
#include "ui.h"
#include "battery.h"
#include "data_logger.h"

static const char *TAG = "APP";

// 全局事件队列 (用于模块间通信)
static QueueHandle_t event_queue = NULL;

// 事件类型定义
typedef enum {
    EVENT_BATTERY_LOW,
    EVENT_DEVICE_FOUND,
    EVENT_DEVICE_LOST,
    EVENT_SCAN_COMPLETE,
    EVENT_READ_COMPLETE,
    EVENT_ERROR,
    EVENT_BUTTON_PRESS,
    EVENT_WIFI_CONNECTED,
    EVENT_WIFI_DISCONNECTED,
} event_type_t;

typedef struct {
    event_type_t type;
    int32_t data;
    void *ptr;
} app_event_t;

// 各模块句柄
static modbus_rtu_handle_t modbus_rtu_h = NULL;
static modbus_tcp_handle_t modbus_tcp_h = NULL;
static scanner_handle_t scanner_h = NULL;
static analyzer_handle_t analyzer_h = NULL;
static battery_handle_t battery_h = NULL;

// ------------------- 事件处理任务 -------------------
static void event_handler_task(void *arg)
{
    app_event_t evt;
    while (1) {
        if (xQueueReceive(event_queue, &evt, portMAX_DELAY)) {
            switch (evt.type) {
            case EVENT_BATTERY_LOW:
                ESP_LOGW(TAG, "Battery low: %.2fV", (float)evt.data / 100.0f);
                ui_show_battery_warning(evt.data);
                break;
            case EVENT_DEVICE_FOUND:
                ESP_LOGI(TAG, "Device found at addr %d", evt.data);
                ui_add_device(evt.data, (const char *)evt.ptr);
                break;
            case EVENT_SCAN_COMPLETE:
                ESP_LOGI(TAG, "Scan complete: %d devices found", evt.data);
                ui_scan_complete(evt.data);
                break;
            case EVENT_ERROR:
                ESP_LOGE(TAG, "Error: %s", (const char *)evt.ptr);
                ui_show_error((const char *)evt.ptr);
                break;
            case EVENT_BUTTON_PRESS:
                ui_handle_button(evt.data);
                break;
            default:
                break;
            }
        }
    }
}

// ------------------- 按键扫描任务 -------------------
static void button_scan_task(void *arg)
{
    const gpio_num_t btn_pins[] = {
        PIN_BTN_UP, PIN_BTN_DOWN, PIN_BTN_OK, PIN_BTN_BACK
    };
    const int btn_ids[] = { 1, 2, 3, 4 }; // 1=UP, 2=DOWN, 3=OK, 4=BACK
    int last_state[4] = {1, 1, 1, 1};

    // 配置按键GPIO为上拉输入
    for (int i = 0; i < 4; i++) {
        gpio_set_direction(btn_pins[i], GPIO_MODE_INPUT);
        gpio_set_pull_mode(btn_pins[i], GPIO_PULLUP_ONLY);
    }

    while (1) {
        for (int i = 0; i < 4; i++) {
            int state = gpio_get_level(btn_pins[i]);
            if (state != last_state[i] && state == 0) {
                // 下降沿（按下）
                app_event_t evt = { .type = EVENT_BUTTON_PRESS, .data = btn_ids[i] };
                xQueueSend(event_queue, &evt, 0);
                ESP_LOGD(TAG, "Button %d pressed", btn_ids[i]);
            }
            last_state[i] = state;
        }
        vTaskDelay(pdMS_TO_TICKS(20)); // 20ms消抖
    }
}

// ------------------- 初始化所有模块 -------------------
void app_main_init(void)
{
    ESP_LOGI(TAG, "Initializing subsystems...");

    // 创建事件队列
    event_queue = xQueueCreate(32, sizeof(app_event_t));

    // 初始化GPIO（LED、蜂鸣器）
    gpio_set_direction(PIN_LED_R, GPIO_MODE_OUTPUT);
    gpio_set_direction(PIN_LED_G, GPIO_MODE_OUTPUT);
    gpio_set_direction(PIN_LED_B, GPIO_MODE_OUTPUT);
    gpio_set_direction(PIN_BUZZER, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_LED_R, 1); // 启动时红灯亮
    gpio_set_level(PIN_LED_G, 0);
    gpio_set_level(PIN_LED_B, 0);

    // 初始化电池管理
    battery_h = battery_init(PIN_BAT_ADC);
    if (battery_h) {
        battery_set_callback(battery_h, EVENT_BATTERY_LOW, event_queue);
        ESP_LOGI(TAG, "Battery module OK");
    }

    // 初始化Modbus RTU
    modbus_rtu_h = modbus_rtu_init();
    if (!modbus_rtu_h) {
        ESP_LOGE(TAG, "Modbus RTU init failed!");
        app_event_t evt = { .type = EVENT_ERROR, .ptr = "Modbus RTU init failed" };
        xQueueSend(event_queue, &evt, 0);
    } else {
        ESP_LOGI(TAG, "Modbus RTU OK");
    }

    // 初始化Modbus TCP（WiFi AP模式）
    modbus_tcp_h = modbus_tcp_init();
    if (modbus_tcp_h) {
        ESP_LOGI(TAG, "Modbus TCP OK");
    }

    // 初始化设备扫描器
    scanner_h = scanner_init(modbus_rtu_h);
    scanner_set_callback(scanner_h, event_queue);

    // 初始化协议分析器
    analyzer_h = analyzer_init(modbus_rtu_h);

    // 初始化LVGL UI
    ui_init();
    ESP_LOGI(TAG, "UI initialized");

    // 启动事件处理任务
    xTaskCreate(event_handler_task, "event_handler", 4096, NULL, 5, NULL);

    // 启动按键扫描任务
    xTaskCreate(button_scan_task, "btn_scan", 2048, NULL, 5, NULL);

    // 绿灯 → 启动完成
    gpio_set_level(PIN_LED_R, 0);
    gpio_set_level(PIN_LED_G, 1);

    ESP_LOGI(TAG, "ModbusDiag ready! v" FW_VERSION_STR);
}
