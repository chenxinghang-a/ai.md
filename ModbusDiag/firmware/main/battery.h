/**
 * ModbusDiag - 电池管理
 */
#ifndef BATTERY_H
#define BATTERY_H

#include <stdint.h>
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"

typedef struct battery_ctx* battery_handle_t;

battery_handle_t battery_init(int adc_pin);
void battery_set_callback(battery_handle_t h, int event_type, QueueHandle_t queue);
float battery_get_voltage(battery_handle_t h);
int battery_get_percent(battery_handle_t h);
bool battery_is_low(battery_handle_t h);
void battery_deinit(battery_handle_t h);

#endif
