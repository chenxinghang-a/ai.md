#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "esp_log.h"
#include "lwip/sockets.h"
#include "modbus_tcp.h"

static const char *TAG = "MB_TCP";
#define MB_TCP_PORT 502

struct modbus_tcp_ctx {
    int sock;
    uint16_t trans_id;
    SemaphoreHandle_t lock;
    bool connected;
};

// Modbus TCP ADU头
typedef struct __attribute__((packed)) {
    uint16_t trans_id;
    uint16_t proto_id;  // 0 for Modbus
    uint16_t len;
    uint8_t unit_id;
} mb_tcp_header_t;

modbus_tcp_handle_t modbus_tcp_init(void)
{
    modbus_tcp_handle_t h = calloc(1, sizeof(struct modbus_tcp_ctx));
    if (!h) return NULL;
    h->sock = -1;
    h->trans_id = 0;
    h->lock = xSemaphoreCreateMutex();
    h->connected = false;
    return h;
}

mb_result_t modbus_tcp_connect(modbus_tcp_handle_t h, const char *ip, uint16_t port)
{
    if (!h) return MB_RESULT_ERROR;
    if (port == 0) port = MB_TCP_PORT;

    h->sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (h->sock < 0) {
        ESP_LOGE(TAG, "Socket create failed");
        return MB_RESULT_ERROR;
    }

    struct sockaddr_in addr = {
        .sin_family = AF_INET,
        .sin_port = htons(port),
    };
    inet_pton(AF_INET, ip, &addr.sin_addr);

    struct timeval timeout = { .tv_sec = 5, .tv_usec = 0 };
    setsockopt(h->sock, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
    setsockopt(h->sock, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));

    int ret = connect(h->sock, (struct sockaddr *)&addr, sizeof(addr));
    if (ret < 0) {
        ESP_LOGE(TAG, "Connect to %s:%d failed", ip, port);
        close(h->sock);
        h->sock = -1;
        return MB_RESULT_TIMEOUT;
    }

    h->connected = true;
    ESP_LOGI(TAG, "Connected to %s:%d", ip, port);
    return MB_RESULT_OK;
}

void modbus_tcp_disconnect(modbus_tcp_handle_t h)
{
    if (!h) return;
    if (h->sock >= 0) {
        close(h->sock);
        h->sock = -1;
    }
    h->connected = false;
}

bool modbus_tcp_is_connected(modbus_tcp_handle_t h)
{
    return h && h->connected;
}

mb_result_t modbus_tcp_read_holding_regs(modbus_tcp_handle_t h,
    uint8_t unit_id, uint16_t start_addr, uint16_t count,
    uint16_t *out_buf, uint32_t timeout_ms)
{
    if (!h || !h->connected || !out_buf) return MB_RESULT_ERROR;
    xSemaphoreTake(h->lock, portMAX_DELAY);

    // 构建MBAP头 + PDU
    uint8_t pdu[12];
    h->trans_id++;
    mb_tcp_header_t *hdr = (mb_tcp_header_t *)pdu;
    hdr->trans_id = htons(h->trans_id);
    hdr->proto_id = 0;
    hdr->len = htons(6); // 剩余长度: unit_id(1) + pdu(5)
    hdr->unit_id = unit_id;
    pdu[7] = 0x03; // 读保持寄存器
    pdu[8] = (start_addr >> 8) & 0xFF;
    pdu[9] = start_addr & 0xFF;
    pdu[10] = (count >> 8) & 0xFF;
    pdu[11] = count & 0xFF;

    int sent = send(h->sock, (char *)pdu, 12, 0);
    if (sent < 12) {
        ESP_LOGE(TAG, "Send failed");
        h->connected = false;
        xSemaphoreGive(h->lock);
        return MB_RESULT_ERROR;
    }

    // 接收MBAP头
    uint8_t resp[256];
    int recvd = recv(h->sock, (char *)resp, 9, 0);
    if (recvd < 9) {
        ESP_LOGE(TAG, "Receive header failed");
        h->connected = false;
        xSemaphoreGive(h->lock);
        return MB_RESULT_TIMEOUT;
    }

    // 获取数据长度
    uint16_t resp_len = ntohs(*(uint16_t *)&resp[4]) - 1;
    uint8_t fc = resp[7];

    // 检查异常
    if (fc & 0x80) {
        xSemaphoreGive(h->lock);
        return MB_RESULT_EXCEPTION;
    }

    // 读取数据体
    int remaining = resp_len - 1; // 减去function code
    int pos = 0;
    while (pos < remaining) {
        recvd = recv(h->sock, (char *)&resp[9 + pos], remaining - pos, 0);
        if (recvd <= 0) break;
        pos += recvd;
    }

    // 解析寄存器值
    uint8_t byte_count = resp[8];
    uint16_t reg_count = byte_count / 2;
    for (uint16_t i = 0; i < reg_count && i < count; i++) {
        out_buf[i] = (resp[9 + i * 2] << 8) | resp[10 + i * 2];
    }

    xSemaphoreGive(h->lock);
    return MB_RESULT_OK;
}

void modbus_tcp_deinit(modbus_tcp_handle_t h)
{
    if (!h) return;
    modbus_tcp_disconnect(h);
    if (h->lock) vSemaphoreDelete(h->lock);
    free(h);
}
