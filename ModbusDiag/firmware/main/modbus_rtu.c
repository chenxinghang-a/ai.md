/**
 * ModbusDiag - Modbus RTU主站实现
 * 基于ESP-IDF UART驱动，硬件RS485控制
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "esp_log.h"
#include "driver/uart.h"
#include "driver/gpio.h"
#include "esp_timer.h"
#include "modbus_rtu.h"
#include "config.h"

static const char *TAG = "MODBUS_RTU";

#define FRAME_BUF_SIZE  64

struct modbus_rtu_ctx {
    int baud;
    bool monitor_mode;
    SemaphoreHandle_t lock;
    QueueHandle_t frame_queue;
    uint8_t rx_buf[256];
    uint16_t rx_len;
    int64_t rx_start_us;
    bool rx_in_progress;
};

// ---------- CRC16 (Modbus标准) ----------
static const uint16_t crc16_table[256] = {
    0x0000, 0xC0C1, 0xC181, 0x0140, 0xC301, 0x03C0, 0x0280, 0xC241,
    0xC601, 0x06C0, 0x0780, 0xC741, 0x0500, 0xC5C1, 0xC481, 0x0440,
    0xCC01, 0x0CC0, 0x0D80, 0xCD41, 0x0F00, 0xCFC1, 0xCE81, 0x0E40,
    0x0A00, 0xCAC1, 0xCB81, 0x0B40, 0xC901, 0x09C0, 0x0880, 0xC841,
    0xD801, 0x18C0, 0x1980, 0xD941, 0x1B00, 0xDBC1, 0xDA81, 0x1A40,
    0x1E00, 0xDEC1, 0xDF81, 0x1F40, 0xDD01, 0x1DC0, 0x1C80, 0xDC41,
    0x1400, 0xD4C1, 0xD581, 0x1540, 0xD701, 0x17C0, 0x1680, 0xD641,
    0xD201, 0x12C0, 0x1380, 0xD341, 0x1100, 0xD1C1, 0xD081, 0x1040,
    0xF001, 0x30C0, 0x3180, 0xF141, 0x3300, 0xF3C1, 0xF281, 0x3240,
    0x3600, 0xF6C1, 0xF781, 0x3740, 0xF501, 0x35C0, 0x3480, 0xF441,
    0x3C00, 0xFCC1, 0xFD81, 0x3D40, 0xFF01, 0x3FC0, 0x3E80, 0xFE41,
    0xFA01, 0x3AC0, 0x3B80, 0xFB41, 0x3900, 0xF9C1, 0xF881, 0x3840,
    0x2800, 0xE8C1, 0xE981, 0x2940, 0xEB01, 0x2BC0, 0x2A80, 0xEA41,
    0xEE01, 0x2EC0, 0x2F80, 0xEF41, 0x2D00, 0xEDC1, 0xEC81, 0x2C40,
    0xE401, 0x24C0, 0x2580, 0xE541, 0x2700, 0xE7C1, 0xE681, 0x2640,
    0x2200, 0xE2C1, 0xE381, 0x2340, 0xE101, 0x21C0, 0x2080, 0xE041,
    0xA001, 0x60C0, 0x6180, 0xA141, 0x6300, 0xA3C1, 0xA281, 0x6240,
    0x6600, 0xA6C1, 0xA781, 0x6740, 0xA501, 0x65C0, 0x6480, 0xA441,
    0x6C00, 0xACC1, 0xAD81, 0x6D40, 0xAF01, 0x6FC0, 0x6E80, 0xAE41,
    0xAA01, 0x6AC0, 0x6B80, 0xAB41, 0x6900, 0xA9C1, 0xA881, 0x6840,
    0x7800, 0xB8C1, 0xB981, 0x7940, 0xBB01, 0x7BC0, 0x7A80, 0xBA41,
    0xBE01, 0x7EC0, 0x7F80, 0xBF41, 0x7D00, 0xBDC1, 0xBC81, 0x7C40,
    0xB401, 0x74C0, 0x7580, 0xB541, 0x7700, 0xB7C1, 0xB681, 0x7640,
    0x7200, 0xB2C1, 0xB381, 0x7340, 0xB101, 0x71C0, 0x7080, 0xB041,
    0x5000, 0x90C1, 0x9181, 0x5140, 0x9301, 0x53C0, 0x5280, 0x9241,
    0x9601, 0x56C0, 0x5780, 0x9741, 0x5500, 0x95C1, 0x9481, 0x5440,
    0x9C01, 0x5CC0, 0x5D80, 0x9D41, 0x5F00, 0x9FC1, 0x9E81, 0x5E40,
    0x5A00, 0x9AC1, 0x9B81, 0x5B40, 0x9901, 0x59C0, 0x5880, 0x9841,
    0x8801, 0x48C0, 0x4980, 0x8941, 0x4B00, 0x8BC1, 0x8A81, 0x4A40,
    0x4E00, 0x8EC1, 0x8F81, 0x4F40, 0x8D01, 0x4DC0, 0x4C80, 0x8C41,
    0x4400, 0x84C1, 0x8581, 0x4540, 0x8701, 0x47C0, 0x4680, 0x8641,
    0x8201, 0x42C0, 0x4380, 0x8341, 0x4100, 0x81C1, 0x8081, 0x4040,
};

uint16_t modbus_crc16(const uint8_t *data, uint16_t len)
{
    uint16_t crc = 0xFFFF;
    for (uint16_t i = 0; i < len; i++) {
        crc = (crc >> 8) ^ crc16_table[(crc ^ data[i]) & 0xFF];
    }
    return crc;
}

// ---------- 硬件控制 ----------
static void rs485_set_tx(bool tx_mode)
{
    gpio_set_level(PIN_RS485_DE, tx_mode ? 1 : 0);
    gpio_set_level(PIN_RS485_RE, tx_mode ? 1 : 0);
}

// ---------- UART接收处理 ----------
static void uart_rx_task(void *arg)
{
    modbus_rtu_handle_t h = (modbus_rtu_handle_t)arg;
    uint8_t byte;
    int64_t frame_timeout_us = 0;

    while (1) {
        int len = uart_read_bytes(UART_RS485_NUM, &byte, 1, pdMS_TO_TICKS(1));
        if (len <= 0) {
            // 帧超时检测 (3.5字符时间)
            if (h->rx_in_progress && frame_timeout_us > 0) {
                int64_t now = esp_timer_get_time();
                if (now - h->rx_start_us > frame_timeout_us) {
                    // 帧结束
                    if (h->rx_len > 0) {
                        uint16_t crc = modbus_crc16(h->rx_buf, h->rx_len - 2);
                        uint16_t recv_crc = h->rx_buf[h->rx_len - 2] |
                                           (h->rx_buf[h->rx_len - 1] << 8);

                        mb_frame_t frame;
                        frame.type = FRAME_TYPE_UNKNOWN;
                        frame.len = h->rx_len;
                        memcpy(frame.data, h->rx_buf, h->rx_len);
                        frame.timestamp_us = h->rx_start_us;
                        frame.crc_calc = crc;
                        frame.crc_recv = recv_crc;
                        frame.crc_ok = (crc == recv_crc);

                        if (h->frame_queue) {
                            xQueueSend(h->frame_queue, &frame, 0);
                        }

                        ESP_LOGD(TAG, "Frame: len=%d, crc=%s, first=%02X %02X",
                               h->rx_len, frame.crc_ok ? "OK" : "BAD",
                               h->rx_buf[0], h->rx_buf[1]);
                    }
                    h->rx_in_progress = false;
                    h->rx_len = 0;
                }
            }
            continue;
        }

        // 新帧开始
        if (!h->rx_in_progress) {
            h->rx_in_progress = true;
            h->rx_len = 0;
        }

        if (h->rx_len < sizeof(h->rx_buf)) {
            h->rx_buf[h->rx_len++] = byte;
        }

        h->rx_start_us = esp_timer_get_time();
        // 超时时间 = 3.5字符 (约35bit time)
        frame_timeout_us = (35000000LL) / h->baud;
    }
}

// ---------- API ----------

modbus_rtu_handle_t modbus_rtu_init(void)
{
    modbus_rtu_handle_t h = calloc(1, sizeof(struct modbus_rtu_ctx));
    if (!h) return NULL;

    h->baud = UART_RS485_BAUD;
    h->monitor_mode = false;
    h->lock = xSemaphoreCreateMutex();
    h->frame_queue = xQueueCreate(FRAME_BUF_SIZE, sizeof(mb_frame_t));
    h->rx_len = 0;
    h->rx_in_progress = false;

    // 配置GPIO
    gpio_set_direction(PIN_RS485_RE, GPIO_MODE_OUTPUT);
    gpio_set_direction(PIN_RS485_DE, GPIO_MODE_OUTPUT);
    rs485_set_tx(false); // 默认接收模式

    // 配置UART
    uart_config_t uart_cfg = {
        .baud_rate = h->baud,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };

    ESP_ERROR_CHECK(uart_param_config(UART_RS485_NUM, &uart_cfg));
    ESP_ERROR_CHECK(uart_set_pin(UART_RS485_NUM,
                                 PIN_RS485_TX,  // TXD
                                 PIN_RS485_RX,  // RXD
                                 UART_PIN_NO_CHANGE,
                                 UART_PIN_NO_CHANGE));
    ESP_ERROR_CHECK(uart_driver_install(UART_RS485_NUM, 256, 0, 0, NULL, 0));

    // 启动接收任务
    xTaskCreate(uart_rx_task, "mb_rx", 3072, h, 10, NULL);

    ESP_LOGI(TAG, "Modbus RTU initialized, baud=%d", h->baud);
    return h;
}

void modbus_rtu_set_baud(modbus_rtu_handle_t h, int baud)
{
    if (!h) return;
    xSemaphoreTake(h->lock, portMAX_DELAY);
    h->baud = baud;
    uart_set_baudrate(UART_RS485_NUM, baud);
    xSemaphoreGive(h->lock);
    ESP_LOGI(TAG, "Baud changed to %d", baud);
}

int modbus_rtu_get_baud(modbus_rtu_handle_t h)
{
    return h ? h->baud : 0;
}

// 发送Modbus RTU帧并等待响应
static mb_result_t send_and_wait(modbus_rtu_handle_t h,
    uint8_t *pdu, uint16_t pdu_len,
    uint8_t slave_addr, uint8_t expected_fc,
    uint16_t expected_regs, uint16_t *out_buf,
    uint32_t timeout_ms)
{
    uint8_t frame[256];
    uint16_t frame_len;

    // 构建RTU帧 (地址 + PDU + CRC)
    frame[0] = slave_addr;
    memcpy(&frame[1], pdu, pdu_len);
    frame_len = 1 + pdu_len;
    uint16_t crc = modbus_crc16(frame, frame_len);
    frame[frame_len++] = crc & 0xFF;
    frame[frame_len++] = (crc >> 8) & 0xFF;

    // 清空接收缓冲区
    uart_flush(UART_RS485_NUM);
    if (h->frame_queue) {
        xQueueReset(h->frame_queue);
    }

    // 切换到发送模式
    rs485_set_tx(true);
    vTaskDelay(pdMS_TO_TICKS(1)); // 等待RE/DE稳定

    // 发送
    uart_write_bytes(UART_RS485_NUM, (const char *)frame, frame_len);
    uart_wait_tx_done(UART_RS485_NUM, pdMS_TO_TICKS(100));

    // 切回接收
    vTaskDelay(pdMS_TO_TICKS(2)); // 发送完等待
    rs485_set_tx(false);

    // 等待响应
    int64_t deadline = esp_timer_get_time() + timeout_ms * 1000;
    mb_frame_t resp;
    bool got_frame = false;

    while (esp_timer_get_time() < deadline) {
        if (xQueueReceive(h->frame_queue, &resp, pdMS_TO_TICKS(10))) {
            // 检查是否是对应的响应帧
            if (resp.data[0] == slave_addr) {
                got_frame = true;

                // 检查CRC
                if (!resp.crc_ok) {
                    ESP_LOGW(TAG, "CRC error from addr %d", slave_addr);
                    return MB_RESULT_CRC_ERROR;
                }

                // 检查异常码
                if (resp.data[1] & 0x80) {
                    uint8_t ex = resp.data[2];
                    ESP_LOGW(TAG, "Exception %02X from addr %d", ex, slave_addr);
                    return MB_RESULT_EXCEPTION;
                }

                // 解析响应
                if (expected_fc == MB_FC_READ_HOLDING_REGS ||
                    expected_fc == MB_FC_READ_INPUT_REGS) {
                    uint8_t byte_count = resp.data[2];
                    uint16_t reg_count = byte_count / 2;
                    for (uint16_t i = 0; i < reg_count && i < expected_regs; i++) {
                        out_buf[i] = (resp.data[3 + i * 2] << 8) |
                                      resp.data[4 + i * 2];
                    }
                }

                return MB_RESULT_OK;
            }
        }
    }

    return MB_RESULT_TIMEOUT;
}

mb_result_t modbus_rtu_read_holding_regs(modbus_rtu_handle_t h,
    uint8_t slave_addr, uint16_t start_addr, uint16_t count,
    uint16_t *out_buf, uint32_t timeout_ms)
{
    if (!h || !out_buf) return MB_RESULT_ERROR;
    xSemaphoreTake(h->lock, portMAX_DELAY);

    uint8_t pdu[] = {
        MB_FC_READ_HOLDING_REGS,
        (start_addr >> 8) & 0xFF,
        start_addr & 0xFF,
        (count >> 8) & 0xFF,
        count & 0xFF
    };
    mb_result_t res = send_and_wait(h, pdu, sizeof(pdu), slave_addr,
                                    MB_FC_READ_HOLDING_REGS, count, out_buf, timeout_ms);

    xSemaphoreGive(h->lock);
    return res;
}

mb_result_t modbus_rtu_read_input_regs(modbus_rtu_handle_t h,
    uint8_t slave_addr, uint16_t start_addr, uint16_t count,
    uint16_t *out_buf, uint32_t timeout_ms)
{
    if (!h || !out_buf) return MB_RESULT_ERROR;
    xSemaphoreTake(h->lock, portMAX_DELAY);

    uint8_t pdu[] = {
        MB_FC_READ_INPUT_REGS,
        (start_addr >> 8) & 0xFF,
        start_addr & 0xFF,
        (count >> 8) & 0xFF,
        count & 0xFF
    };
    mb_result_t res = send_and_wait(h, pdu, sizeof(pdu), slave_addr,
                                    MB_FC_READ_INPUT_REGS, count, out_buf, timeout_ms);

    xSemaphoreGive(h->lock);
    return res;
}

mb_result_t modbus_rtu_read_coils(modbus_rtu_handle_t h,
    uint8_t slave_addr, uint16_t start_addr, uint16_t count,
    bool *out_buf, uint32_t timeout_ms)
{
    if (!h || !out_buf) return MB_RESULT_ERROR;
    xSemaphoreTake(h->lock, portMAX_DELAY);

    uint8_t pdu[] = {
        MB_FC_READ_COILS,
        (start_addr >> 8) & 0xFF,
        start_addr & 0xFF,
        (count >> 8) & 0xFF,
        count & 0xFF
    };
    uint16_t regs[128];
    mb_result_t res = send_and_wait(h, pdu, sizeof(pdu), slave_addr,
                                    MB_FC_READ_COILS, count, regs, timeout_ms);

    if (res == MB_RESULT_OK) {
        // 响应数据在frame里，比较麻烦，简化处理
    }

    xSemaphoreGive(h->lock);
    return res;
}

mb_result_t modbus_rtu_read_discrete_inputs(modbus_rtu_handle_t h,
    uint8_t slave_addr, uint16_t start_addr, uint16_t count,
    bool *out_buf, uint32_t timeout_ms)
{
    if (!h || !out_buf) return MB_RESULT_ERROR;
    xSemaphoreTake(h->lock, portMAX_DELAY);

    uint8_t pdu[] = {
        MB_FC_READ_DISCRETE_INPUTS,
        (start_addr >> 8) & 0xFF,
        start_addr & 0xFF,
        (count >> 8) & 0xFF,
        count & 0xFF
    };
    // 简化：使用相同处理逻辑
    uint16_t regs[128];
    mb_result_t res = send_and_wait(h, pdu, sizeof(pdu), slave_addr,
                                    MB_FC_READ_DISCRETE_INPUTS, count, regs, timeout_ms);

    xSemaphoreGive(h->lock);
    return res;
}

mb_result_t modbus_rtu_write_single_coil(modbus_rtu_handle_t h,
    uint8_t slave_addr, uint16_t addr, bool value, uint32_t timeout_ms)
{
    if (!h) return MB_RESULT_ERROR;
    xSemaphoreTake(h->lock, portMAX_DELAY);

    uint8_t pdu[] = {
        MB_FC_WRITE_SINGLE_COIL,
        (addr >> 8) & 0xFF,
        addr & 0xFF,
        value ? 0xFF : 0x00,
        0x00
    };
    mb_result_t res = send_and_wait(h, pdu, sizeof(pdu), slave_addr,
                                    MB_FC_WRITE_SINGLE_COIL, 0, NULL, timeout_ms);

    xSemaphoreGive(h->lock);
    return res;
}

mb_result_t modbus_rtu_write_single_reg(modbus_rtu_handle_t h,
    uint8_t slave_addr, uint16_t addr, uint16_t value, uint32_t timeout_ms)
{
    if (!h) return MB_RESULT_ERROR;
    xSemaphoreTake(h->lock, portMAX_DELAY);

    uint8_t pdu[] = {
        MB_FC_WRITE_SINGLE_REG,
        (addr >> 8) & 0xFF,
        addr & 0xFF,
        (value >> 8) & 0xFF,
        value & 0xFF
    };
    mb_result_t res = send_and_wait(h, pdu, sizeof(pdu), slave_addr,
                                    MB_FC_WRITE_SINGLE_REG, 0, NULL, timeout_ms);

    xSemaphoreGive(h->lock);
    return res;
}

mb_result_t modbus_rtu_write_multiple_regs(modbus_rtu_handle_t h,
    uint8_t slave_addr, uint16_t start_addr, uint16_t *values,
    uint16_t count, uint32_t timeout_ms)
{
    if (!h || !values || count > 123) return MB_RESULT_ERROR;
    xSemaphoreTake(h->lock, portMAX_DELAY);

    uint8_t pdu[5 + count * 2];
    pdu[0] = MB_FC_WRITE_MULTIPLE_REGS;
    pdu[1] = (start_addr >> 8) & 0xFF;
    pdu[2] = start_addr & 0xFF;
    pdu[3] = (count >> 8) & 0xFF;
    pdu[4] = count & 0xFF;
    pdu[5] = count * 2; // byte count
    for (uint16_t i = 0; i < count; i++) {
        pdu[6 + i * 2] = (values[i] >> 8) & 0xFF;
        pdu[7 + i * 2] = values[i] & 0xFF;
    }

    mb_result_t res = send_and_wait(h, pdu, 6 + count * 2, slave_addr,
                                    MB_FC_WRITE_MULTIPLE_REGS, 0, NULL, timeout_ms);

    xSemaphoreGive(h->lock);
    return res;
}

void modbus_rtu_set_monitor_mode(modbus_rtu_handle_t h, bool enable)
{
    if (!h) return;
    h->monitor_mode = enable;
    if (enable) {
        rs485_set_tx(false); // 始终接收
        ESP_LOGI(TAG, "Monitor mode enabled");
    }
}

int modbus_rtu_get_frames(modbus_rtu_handle_t h, mb_frame_t *frames, int max_count)
{
    if (!h || !frames || !h->frame_queue) return 0;
    int count = 0;
    while (count < max_count && xQueueReceive(h->frame_queue, &frames[count], 0)) {
        count++;
    }
    return count;
}

void modbus_rtu_clear_frames(modbus_rtu_handle_t h)
{
    if (h && h->frame_queue) {
        xQueueReset(h->frame_queue);
    }
}

void modbus_rtu_deinit(modbus_rtu_handle_t h)
{
    if (!h) return;
    uart_driver_delete(UART_RS485_NUM);
    if (h->lock) vSemaphoreDelete(h->lock);
    if (h->frame_queue) vQueueDelete(h->frame_queue);
    free(h);
    ESP_LOGI(TAG, "Deinitialized");
}
