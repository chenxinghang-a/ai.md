/**
 * ModbusDiag - 设备自动发现实现
 * 核心算法：
 * 1. 遍历所有波特率(1200-115200)
 * 2. 在每个波特率下遍历地址1-247
 * 3. 发读取保持寄存器(功能码03)请求
 * 4. 有响应则记录设备
 * 5. 对发现的设备深入探测寄存器范围
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "device_scanner.h"
#include "modbus_rtu.h"
#include "config.h"

static const char *TAG = "SCANNER";

#define MAX_DEVICES     32

struct scanner_ctx {
    modbus_rtu_handle_t mb;
    bool running;
    int progress;
    int device_count;
    scanner_device_t devices[MAX_DEVICES];
    TaskHandle_t task_handle;
    QueueHandle_t evt_queue;
};

// 波特率列表
static const int baud_rates[] = SCAN_BAUD_RATES;

scanner_handle_t scanner_init(void *modbus_rtu_handle)
{
    scanner_handle_t h = calloc(1, sizeof(struct scanner_ctx));
    if (!h) return NULL;
    h->mb = (modbus_rtu_handle_t)modbus_rtu_handle;
    h->running = false;
    h->progress = 0;
    h->device_count = 0;
    h->task_handle = NULL;
    h->evt_queue = NULL;
    memset(h->devices, 0, sizeof(h->devices));
    return h;
}

void scanner_set_callback(scanner_handle_t h, QueueHandle_t event_queue)
{
    if (h) h->evt_queue = event_queue;
}

void scanner_stop(scanner_handle_t h)
{
    if (h) h->running = false;
}

void scanner_start_full(scanner_handle_t h)
{
    if (!h || h->running) return;
    h->running = true;
    h->progress = 0;
    h->device_count = 0;
    memset(h->devices, 0, sizeof(h->devices));

    // 启动扫描任务
    xTaskCreate(scanner_task, "scanner", 8192, h, 5, &h->task_handle);
    ESP_LOGI(TAG, "Scanner started");
}

void scanner_task(void *arg)
{
    scanner_handle_t h = (scanner_handle_t)arg;
    uint16_t regs[8];
    int total_steps = sizeof(baud_rates) / sizeof(baud_rates[0]) * 247;
    int step = 0;

    ESP_LOGI(TAG, "Scanning %d baud rates...", SCAN_BAUD_COUNT);

    for (int b = 0; b < SCAN_BAUD_COUNT && h->running; b++) {
        int baud = baud_rates[b];
        modbus_rtu_set_baud(h->mb, baud);
        vTaskDelay(pdMS_TO_TICKS(50)); // 等待波特率切换稳定

        ESP_LOGI(TAG, "Scanning baud=%d...", baud);

        for (int addr = SCAN_ADDR_START; addr <= SCAN_ADDR_END && h->running; addr++) {
            step++;
            h->progress = (step * 100) / total_steps;

            // 读3个寄存器看有没有设备响应
            mb_result_t res = modbus_rtu_read_holding_regs(
                h->mb, addr, 0, 3, regs, MODBUS_SCAN_TIMEOUT);

            if (res == MB_RESULT_OK) {
                // 发现设备！
                if (h->device_count < MAX_DEVICES) {
                    int idx = h->device_count++;
                    h->devices[idx].addr = addr;
                    h->devices[idx].baud = baud;
                    h->devices[idx].regs_found = 3; // 至少3个寄存器
                    h->devices[idx].response_time = 0; // TODO: 记录响应时间

                    // 尝试读取设备ID (地址0x00-0x05)
                    uint16_t id_regs[6];
                    mb_result_t id_res = modbus_rtu_read_holding_regs(
                        h->mb, addr, 0, 6, id_regs, MODBUS_SCAN_TIMEOUT);

                    if (id_res == MB_RESULT_OK) {
                        // 将寄存器值作为ASCII模型名
                        char *p = h->devices[idx].model;
                        for (int i = 0; i < 6; i++) {
                            p += sprintf(p, "%c%c",
                                (id_regs[i] >> 8) & 0xFF,
                                id_regs[i] & 0xFF);
                        }
                        h->devices[idx].model[31] = '\0';
                    } else {
                        snprintf(h->devices[idx].model, 32, "Device@%d", addr);
                    }

                    ESP_LOGI(TAG, "Found: addr=%d baud=%d model=%s",
                           addr, baud, h->devices[idx].model);

                    // 发事件通知
                    if (h->evt_queue) {
                        // 发送EVENT_DEVICE_FOUND
                    }
                }
            }

            // 每扫描10个地址让出CPU
            if (addr % 10 == 0) vTaskDelay(1);
        }
    }

    h->running = false;
    h->progress = 100;

    ESP_LOGI(TAG, "Scan complete: %d devices found", h->device_count);

    // 发事件
    if (h->evt_queue) {
        // 发送EVENT_SCAN_COMPLETE
    }

    h->task_handle = NULL;
    vTaskDelete(NULL);
}

int scanner_get_progress(scanner_handle_t h)
{
    return h ? h->progress : 0;
}

int scanner_get_device_count(scanner_handle_t h)
{
    return h ? h->device_count : 0;
}

void scanner_get_devices(scanner_handle_t h, scanner_device_t *devs, int *count)
{
    if (!h || !devs || !count) return;
    int n = (h->device_count < *count) ? h->device_count : *count;
    memcpy(devs, h->devices, n * sizeof(scanner_device_t));
    *count = n;
}
