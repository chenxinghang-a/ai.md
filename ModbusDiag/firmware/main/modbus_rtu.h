/**
 * ModbusDiag - Modbus RTU主站驱动
 */
#ifndef MODBUS_RTU_H
#define MODBUS_RTU_H

#include <stdint.h>
#include <stdbool.h>
#include "driver/uart.h"

#ifdef __cplusplus
extern "C" {
#endif

// 操作结果
typedef enum {
    MB_RESULT_OK,
    MB_RESULT_TIMEOUT,
    MB_RESULT_CRC_ERROR,
    MB_RESULT_EXCEPTION,
    MB_RESULT_BUSY,
    MB_RESULT_ERROR,
} mb_result_t;

// Modbus异常码
typedef enum {
    MB_EX_ILLEGAL_FUNCTION   = 0x01,
    MB_EX_ILLEGAL_ADDRESS    = 0x02,
    MB_EX_ILLEGAL_VALUE      = 0x03,
    MB_EX_DEVICE_FAILURE     = 0x04,
    MB_EX_ACKNOWLEDGE        = 0x05,
    MB_EX_DEVICE_BUSY        = 0x06,
    MB_EX_NEGATIVE_ACK       = 0x07,
    MB_EX_MEMORY_PARITY      = 0x08,
    MB_EX_GATEWAY_PATH       = 0x0A,
    MB_EX_GATEWAY_TARGET     = 0x0B,
} mb_exception_t;

// 功能码
typedef enum {
    MB_FC_READ_COILS          = 0x01,
    MB_FC_READ_DISCRETE_INPUTS = 0x02,
    MB_FC_READ_HOLDING_REGS   = 0x03,
    MB_FC_READ_INPUT_REGS     = 0x04,
    MB_FC_WRITE_SINGLE_COIL   = 0x05,
    MB_FC_WRITE_SINGLE_REG    = 0x06,
    MB_FC_WRITE_MULTIPLE_COILS = 0x0F,
    MB_FC_WRITE_MULTIPLE_REGS = 0x10,
} mb_function_code_t;

// 帧类型（用于抓包分析）
typedef enum {
    FRAME_TYPE_QUERY,
    FRAME_TYPE_RESPONSE_OK,
    FRAME_TYPE_RESPONSE_ERROR,
    FRAME_TYPE_BROADCAST,
    FRAME_TYPE_UNKNOWN,
} frame_type_t;

// 一帧原始数据
typedef struct {
    frame_type_t type;
    uint8_t data[256];
    uint16_t len;
    int64_t timestamp_us;
    uint16_t crc_calc;
    uint16_t crc_recv;
    bool crc_ok;
} mb_frame_t;

// 寄存器读取结果
typedef struct {
    mb_result_t result;
    uint16_t *regs;
    uint16_t count;
    uint8_t exception_code;
    uint32_t duration_ms;
} mb_read_result_t;

// 句柄
typedef struct modbus_rtu_ctx* modbus_rtu_handle_t;

// ---------- API ----------

// 初始化Modbus RTU
modbus_rtu_handle_t modbus_rtu_init(void);

// 设置波特率
void modbus_rtu_set_baud(modbus_rtu_handle_t h, int baud);

// 获取当前波特率
int modbus_rtu_get_baud(modbus_rtu_handle_t h);

// 读取保持寄存器
mb_result_t modbus_rtu_read_holding_regs(modbus_rtu_handle_t h,
    uint8_t slave_addr, uint16_t start_addr, uint16_t count,
    uint16_t *out_buf, uint32_t timeout_ms);

// 读取输入寄存器
mb_result_t modbus_rtu_read_input_regs(modbus_rtu_handle_t h,
    uint8_t slave_addr, uint16_t start_addr, uint16_t count,
    uint16_t *out_buf, uint32_t timeout_ms);

// 读取线圈
mb_result_t modbus_rtu_read_coils(modbus_rtu_handle_t h,
    uint8_t slave_addr, uint16_t start_addr, uint16_t count,
    bool *out_buf, uint32_t timeout_ms);

// 读取离散输入
mb_result_t modbus_rtu_read_discrete_inputs(modbus_rtu_handle_t h,
    uint8_t slave_addr, uint16_t start_addr, uint16_t count,
    bool *out_buf, uint32_t timeout_ms);

// 写单个线圈
mb_result_t modbus_rtu_write_single_coil(modbus_rtu_handle_t h,
    uint8_t slave_addr, uint16_t addr, bool value, uint32_t timeout_ms);

// 写单个寄存器
mb_result_t modbus_rtu_write_single_reg(modbus_rtu_handle_t h,
    uint8_t slave_addr, uint16_t addr, uint16_t value, uint32_t timeout_ms);

// 写多个寄存器
mb_result_t modbus_rtu_write_multiple_regs(modbus_rtu_handle_t h,
    uint8_t slave_addr, uint16_t start_addr, uint16_t *values,
    uint16_t count, uint32_t timeout_ms);

// CRC16计算
uint16_t modbus_crc16(const uint8_t *data, uint16_t len);

// 进入监听模式（抓包，不发送）
void modbus_rtu_set_monitor_mode(modbus_rtu_handle_t h, bool enable);

// 获取抓包帧
int modbus_rtu_get_frames(modbus_rtu_handle_t h, mb_frame_t *frames, int max_count);

// 清空抓包缓冲区
void modbus_rtu_clear_frames(modbus_rtu_handle_t h);

// 销毁
void modbus_rtu_deinit(modbus_rtu_handle_t h);

#ifdef __cplusplus
}
#endif

#endif // MODBUS_RTU_H
