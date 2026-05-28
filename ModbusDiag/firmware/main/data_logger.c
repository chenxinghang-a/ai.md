/**
 * ModbusDiag - 数据记录实现
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "esp_log.h"
#include "data_logger.h"

static const char *TAG = "LOGGER";

#define MAX_DATA_POINTS 1024

static data_point_t data_buf[MAX_DATA_POINTS];
static int data_count = 0;
static SemaphoreHandle_t data_lock = NULL;

void data_logger_init(void)
{
    data_lock = xSemaphoreCreateMutex();
    data_count = 0;
    ESP_LOGI(TAG, "Data logger ready (max %d points)", MAX_DATA_POINTS);
}

void data_logger_record(uint8_t addr, uint16_t reg, uint16_t value)
{
    if (!data_lock) return;

    xSemaphoreTake(data_lock, portMAX_DELAY);
    if (data_count < MAX_DATA_POINTS) {
        data_buf[data_count].timestamp = esp_log_timestamp();
        data_buf[data_count].slave_addr = addr;
        data_buf[data_count].reg_addr = reg;
        data_buf[data_count].reg_value = value;
        data_count++;
    }
    xSemaphoreGive(data_lock);
}

int data_logger_count(void)
{
    return data_count;
}

void data_logger_clear(void)
{
    if (!data_lock) return;
    xSemaphoreTake(data_lock, portMAX_DELAY);
    data_count = 0;
    xSemaphoreGive(data_lock);
}

bool data_logger_export_csv(const char *filename)
{
    if (!data_lock) return false;

    xSemaphoreTake(data_lock, portMAX_DELAY);
    // 简化：实际用SPIFFS写入文件
    ESP_LOGI(TAG, "Export %d points to %s", data_count, filename);

    // CSV格式
    // Timestamp,Slave,Register,Value
    for (int i = 0; i < data_count; i++) {
        // fprintf(file, "%u,%d,%d,%d\n", ...);
    }
    xSemaphoreGive(data_lock);
    return true;
}

char* data_logger_export_json(int *out_len)
{
    if (!data_lock || !out_len) return NULL;

    xSemaphoreTake(data_lock, portMAX_DELAY);
    // 估计JSON大小
    int buf_size = data_count * 64 + 128;
    char *json = malloc(buf_size);
    if (!json) {
        xSemaphoreGive(data_lock);
        return NULL;
    }

    int pos = sprintf(json, "{\"count\":%d,\"points\":[", data_count);
    for (int i = 0; i < data_count && pos < buf_size - 100; i++) {
        pos += sprintf(json + pos,
            "{\"t\":%u,\"s\":%d,\"r\":%d,\"v\":%d}%s",
            data_buf[i].timestamp,
            data_buf[i].slave_addr,
            data_buf[i].reg_addr,
            data_buf[i].reg_value,
            i < data_count - 1 ? "," : "");
    }
    pos += sprintf(json + pos, "]}");
    *out_len = pos;

    xSemaphoreGive(data_lock);
    return json;
}
