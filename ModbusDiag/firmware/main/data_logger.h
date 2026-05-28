/**
 * ModbusDiag - 数据记录与导出
 */
#ifndef DATA_LOGGER_H
#define DATA_LOGGER_H

#include <stdint.h>
#include <stdbool.h>

typedef struct {
    uint32_t timestamp;
    uint8_t slave_addr;
    uint16_t reg_addr;
    uint16_t reg_value;
} data_point_t;

void data_logger_init(void);

// 记录一个数据点
void data_logger_record(uint8_t addr, uint16_t reg, uint16_t value);

// 导出为CSV (保存到Flash/SPIFFS)
bool data_logger_export_csv(const char *filename);

// 导出为JSON (用于API导出到手机)
char* data_logger_export_json(int *out_len);

// 清空数据
void data_logger_clear(void);

// 获取记录数
int data_logger_count(void);

#endif
