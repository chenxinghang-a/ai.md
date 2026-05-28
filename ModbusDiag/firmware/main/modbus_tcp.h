/**
 * ModbusDiag - Modbus TCP客户端
 */
#ifndef MODBUS_TCP_H
#define MODBUS_TCP_H

#include <stdint.h>
#include <stdbool.h>
#include "modbus_rtu.h" // 复用结果码

typedef struct modbus_tcp_ctx* modbus_tcp_handle_t;

modbus_tcp_handle_t modbus_tcp_init(void);
mb_result_t modbus_tcp_connect(modbus_tcp_handle_t h, const char *ip, uint16_t port);
void modbus_tcp_disconnect(modbus_tcp_handle_t h);
bool modbus_tcp_is_connected(modbus_tcp_handle_t h);

mb_result_t modbus_tcp_read_holding_regs(modbus_tcp_handle_t h,
    uint8_t unit_id, uint16_t start_addr, uint16_t count,
    uint16_t *out_buf, uint32_t timeout_ms);

void modbus_tcp_deinit(modbus_tcp_handle_t h);

#endif
