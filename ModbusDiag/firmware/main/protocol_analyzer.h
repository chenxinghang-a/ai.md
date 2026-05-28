/**
 * ModbusDiag - 协议分析器
 * 监听总线数据，解析Modbus帧，统计错误
 */
#ifndef PROTOCOL_ANALYZER_H
#define PROTOCOL_ANALYZER_H

#include <stdint.h>
#include "modbus_rtu.h"

typedef struct analyzer_ctx* analyzer_handle_t;

// 统计信息
typedef struct {
    uint32_t total_frames;
    uint32_t error_frames;
    uint32_t crc_errors;
    uint32_t exception_frames;
    uint32_t query_frames;
    uint32_t response_frames;
    uint32_t min_response_time_us;
    uint32_t max_response_time_us;
    uint32_t avg_response_time_us;
    uint8_t active_slaves[256];
    uint8_t active_slave_count;
} analyzer_stats_t;

analyzer_handle_t analyzer_init(modbus_rtu_handle_t mb);
void analyzer_start(analyzer_handle_t h);
void analyzer_stop(analyzer_handle_t h);
bool analyzer_is_running(analyzer_handle_t h);
void analyzer_get_stats(analyzer_handle_t h, analyzer_stats_t *stats);
mb_frame_t* analyzer_get_frames(analyzer_handle_t h, int *count);
void analyzer_clear(analyzer_handle_t h);
const char* analyzer_frame_type_str(frame_type_t t);
const char* analyzer_func_code_str(uint8_t fc);

#endif
