/**
 * ModbusDiag - 设备自动发现
 */
#ifndef DEVICE_SCANNER_H
#define DEVICE_SCANNER_H

#include <stdint.h>
#include <stdbool.h>
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"

typedef struct scanner_ctx* scanner_handle_t;

typedef struct {
    int addr;
    int baud;
    int16_t regs_found;     // -1 = error
    uint32_t response_time; // us
    char model[32];
} scanner_device_t;

scanner_handle_t scanner_init(void *modbus_rtu_handle);
void scanner_set_callback(scanner_handle_t h, QueueHandle_t event_queue);

// 启动全自动扫描（遍历1-247地址 x 8种波特率）
void scanner_start_full(scanner_handle_t h);

// 停止扫描
void scanner_stop(scanner_handle_t h);

// 获取扫描进度 (0-100)
int scanner_get_progress(scanner_handle_t h);

// 获取发现的设备数
int scanner_get_device_count(scanner_handle_t h);

// 获取设备列表
void scanner_get_devices(scanner_handle_t h, scanner_device_t *devs, int *count);

// 扫描任务（在独立线程运行）
void scanner_task(void *arg);

#endif
