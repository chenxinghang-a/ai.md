/**
 * ModbusDiag - 电池管理实现
 */
#include <stdio.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "driver/adc.h"
#include "driver/gpio.h"
#include "battery.h"
#include "config.h"

static const char *TAG = "BATTERY";

// 电池电压 = ADC值 / 4096 * 3.3 * (R1+R2)/R2
// = ADC / 4096 * 3.3 * (100+10)/10
// = ADC / 4096 * 3.3 * 11

struct battery_ctx {
    int adc_pin;
    adc1_channel_t adc_channel;
    QueueHandle_t evt_queue;
    int evt_type;
    TaskHandle_t task;
};

static void battery_monitor_task(void *arg)
{
    battery_handle_t h = (battery_handle_t)arg;
    int low_count = 0;

    while (1) {
        int raw = adc1_get_raw(h->adc_channel);
        float voltage = (float)raw / 4096.0f * 3.3f * 11.0f;

        ESP_LOGD(TAG, "ADC=%d, Battery=%.2fV", raw, voltage);

        if (voltage < BAT_WARN_VOLTAGE) {
            low_count++;
            if (low_count >= 3 && h->evt_queue) {
                // 连续3次低电才报警（防误报）
                // 发送事件
                low_count = 0;
            }
        } else {
            low_count = 0;
        }

        vTaskDelay(pdMS_TO_TICKS(5000)); // 每5秒检测一次
    }
}

battery_handle_t battery_init(int adc_pin)
{
    battery_handle_t h = calloc(1, sizeof(struct battery_ctx));
    if (!h) return NULL;

    h->adc_pin = adc_pin;
    h->evt_type = 0;
    h->evt_queue = NULL;

    // 配置ADC
    adc1_config_width(ADC_WIDTH_BIT_12);
    adc1_config_channel_atten(ADC1_CHANNEL_0, ADC_ATTEN_DB_11); // GPIO20 = ADC1_CH0

    // 启动监控任务
    xTaskCreate(battery_monitor_task, "battery", 2048, h, 5, &h->task);

    ESP_LOGI(TAG, "Battery monitor started");
    return h;
}

void battery_set_callback(battery_handle_t h, int event_type, QueueHandle_t queue)
{
    if (h) {
        h->evt_type = event_type;
        h->evt_queue = queue;
    }
}

float battery_get_voltage(battery_handle_t h)
{
    if (!h) return 0;
    int raw = adc1_get_raw(h->adc_channel);
    return (float)raw / 4096.0f * 3.3f * 11.0f;
}

int battery_get_percent(battery_handle_t h)
{
    float v = battery_get_voltage(h);
    if (v >= BAT_FULL_VOLTAGE) return 100;
    if (v <= BAT_EMPTY_VOLTAGE) return 0;
    return (int)((v - BAT_EMPTY_VOLTAGE) / (BAT_FULL_VOLTAGE - BAT_EMPTY_VOLTAGE) * 100);
}

bool battery_is_low(battery_handle_t h)
{
    return battery_get_voltage(h) < BAT_WARN_VOLTAGE;
}

void battery_deinit(battery_handle_t h)
{
    if (!h) return;
    if (h->task) vTaskDelete(h->task);
    free(h);
}
