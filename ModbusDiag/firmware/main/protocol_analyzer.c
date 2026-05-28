/**
 * ModbusDiag - 协议分析器实现
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "protocol_analyzer.h"
#include "modbus_rtu.h"
#include "config.h"

static const char *TAG = "ANALYZER";

struct analyzer_ctx {
    modbus_rtu_handle_t mb;
    bool running;
    analyzer_stats_t stats;
    mb_frame_t frames[ANALYZER_WIN_SIZE];
    int frame_count;
    int frame_write_idx;
    TaskHandle_t task;
};

analyzer_handle_t analyzer_init(modbus_rtu_handle_t mb)
{
    analyzer_handle_t h = calloc(1, sizeof(struct analyzer_ctx));
    if (!h) return NULL;
    h->mb = mb;
    h->running = false;
    h->frame_count = 0;
    h->frame_write_idx = 0;
    memset(&h->stats, 0, sizeof(analyzer_stats_t));
    return h;
}

static void analyzer_task(void *arg)
{
    analyzer_handle_t h = (analyzer_handle_t)arg;
    mb_frame_t frame;
    int64_t last_frame_time = 0;

    // 开启监听模式
    modbus_rtu_set_monitor_mode(h->mb, true);
    modbus_rtu_clear_frames(h->mb);

    while (h->running) {
        // 轮询获取帧
        int count = modbus_rtu_get_frames(h->mb, &frame, 1);
        if (count > 0) {
            // 更新统计
            h->stats.total_frames++;
            if (!frame.crc_ok) {
                h->stats.crc_errors++;
                h->stats.error_frames++;
            }

            // 判断查询/响应
            if (frame.data[1] <= 0x10) {
                h->stats.query_frames++;
                frame.type = FRAME_TYPE_QUERY;
            } else {
                h->stats.response_frames++;
                frame.type = (frame.data[1] & 0x80) ?
                             FRAME_TYPE_RESPONSE_ERROR : FRAME_TYPE_RESPONSE_OK;
                if (frame.data[1] & 0x80) {
                    h->stats.exception_frames++;
                }
            }

            // 记录活跃从站
            uint8_t slave = frame.data[0];
            if (slave >= 1 && slave <= 247) {
                if (!h->stats.active_slaves[slave]) {
                    h->stats.active_slaves[slave] = 1;
                    h->stats.active_slave_count++;
                }
            }

            // 响应时间
            if (last_frame_time > 0 && frame.type == FRAME_TYPE_RESPONSE_OK) {
                uint32_t dt = (uint32_t)(frame.timestamp_us - last_frame_time);
                if (dt < h->stats.min_response_time_us || h->stats.min_response_time_us == 0)
                    h->stats.min_response_time_us = dt;
                if (dt > h->stats.max_response_time_us)
                    h->stats.max_response_time_us = dt;
                // 移动平均
                if (h->stats.avg_response_time_us == 0)
                    h->stats.avg_response_time_us = dt;
                else
                    h->stats.avg_response_time_us = (h->stats.avg_response_time_us + dt) / 2;
            }
            last_frame_time = frame.timestamp_us;

            // 存入循环缓冲区
            h->frames[h->frame_write_idx] = frame;
            h->frame_write_idx = (h->frame_write_idx + 1) % ANALYZER_WIN_SIZE;
            if (h->frame_count < ANALYZER_WIN_SIZE) h->frame_count++;
        }

        vTaskDelay(pdMS_TO_TICKS(10));
    }

    modbus_rtu_set_monitor_mode(h->mb, false);
    h->task = NULL;
    vTaskDelete(NULL);
}

void analyzer_start(analyzer_handle_t h)
{
    if (!h || h->running) return;
    h->running = true;
    xTaskCreate(analyzer_task, "analyzer", 4096, h, 5, &h->task);
    ESP_LOGI(TAG, "Analyzer started");
}

void analyzer_stop(analyzer_handle_t h)
{
    if (h) h->running = false;
}

bool analyzer_is_running(analyzer_handle_t h)
{
    return h ? h->running : false;
}

void analyzer_get_stats(analyzer_handle_t h, analyzer_stats_t *stats)
{
    if (h && stats) memcpy(stats, &h->stats, sizeof(analyzer_stats_t));
}

mb_frame_t* analyzer_get_frames(analyzer_handle_t h, int *count)
{
    if (!h || !count) return NULL;
    *count = h->frame_count;
    return h->frames;
}

void analyzer_clear(analyzer_handle_t h)
{
    if (!h) return;
    memset(&h->stats, 0, sizeof(analyzer_stats_t));
    h->frame_count = 0;
    h->frame_write_idx = 0;
    modbus_rtu_clear_frames(h->mb);
}

const char* analyzer_frame_type_str(frame_type_t t)
{
    switch (t) {
    case FRAME_TYPE_QUERY:           return "QUERY";
    case FRAME_TYPE_RESPONSE_OK:     return "RESP_OK";
    case FRAME_TYPE_RESPONSE_ERROR:  return "RESP_ERR";
    case FRAME_TYPE_BROADCAST:       return "BCAST";
    default:                         return "UNKNOWN";
    }
}

const char* analyzer_func_code_str(uint8_t fc)
{
    switch (fc) {
    case 0x01: return "Read Coils";
    case 0x02: return "Read Discrete";
    case 0x03: return "Read Holding Regs";
    case 0x04: return "Read Input Regs";
    case 0x05: return "Write Coil";
    case 0x06: return "Write Reg";
    case 0x0F: return "Write Coils";
    case 0x10: return "Write Regs";
    default:   return "Unknown FC";
    }
}
