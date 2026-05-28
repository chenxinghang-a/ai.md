/**
 * ModbusDiag - LVGL UI实现
 * 基于ESP32-S3 + ILI9488 3.5寸 480x320
 */
#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "driver/spi_master.h"
#include "driver/gpio.h"
#include "driver/ledc.h"
#include "esp_timer.h"

#include "lvgl.h"
#include "ui.h"
#include "ui_screens.h"
#include "config.h"

static const char *TAG = "UI";

// ---------- 硬件驱动 ----------

// SPI句柄
static spi_device_handle_t spi_dev = NULL;

// TFT写命令
static void tft_write_cmd(uint8_t cmd)
{
    gpio_set_level(PIN_TFT_DC, 0); // 命令模式
    gpio_set_level(PIN_TFT_CS, 0);
    spi_transaction_t t = {
        .length = 8,
        .tx_buffer = &cmd,
    };
    spi_device_transmit(spi_dev, &t);
    gpio_set_level(PIN_TFT_CS, 1);
}

// TFT写数据
static void tft_write_data(const uint8_t *data, int len)
{
    gpio_set_level(PIN_TFT_DC, 1); // 数据模式
    gpio_set_level(PIN_TFT_CS, 0);
    spi_transaction_t t = {
        .length = len * 8,
        .tx_buffer = data,
    };
    spi_device_transmit(spi_dev, &t);
    gpio_set_level(PIN_TFT_CS, 1);
}

// TFT初始化序列 (ILI9488)
static void tft_init(void)
{
    // 复位
    gpio_set_level(PIN_TFT_RST, 0);
    vTaskDelay(pdMS_TO_TICKS(10));
    gpio_set_level(PIN_TFT_RST, 1);
    vTaskDelay(pdMS_TO_TICKS(120));

    // ILI9488初始化命令
    const uint8_t init_cmds[] = {
        // 软件复位
        0x01, 0x00,
        0x11, 0x00, vTaskDelay(120),

        // 电源控制
        0xC0, 0x01, 0x10,
        0xC1, 0x01, 0x10,
        0xC5, 0x02, 0x10, 0x10,

        // 帧率控制
        0xE0, 0x15,
        0x00,0x03,0x09,0x08,0x16,0x0A,0x3F,0x78,
        0x4C,0x09,0x0A,0x08,0x16,0x1A,0x0F,

        // 负向伽马
        0xE1, 0x15,
        0x00,0x16,0x19,0x03,0x0F,0x05,0x32,0x45,
        0x46,0x04,0x0E,0x0D,0x35,0x37,0x0F,

        // 显示设置
        0x36, 0x01, 0x48, // MADCTL: BGR, 数据线顺序
        0x3A, 0x01, 0x66, // 像素格式: 18bit

        // 显示开
        0x29, 0x00,
    };

    int i = 0;
    while (i < (int)sizeof(init_cmds)) {
        uint8_t cmd = init_cmds[i++];
        uint8_t param_count = init_cmds[i++];

        tft_write_cmd(cmd);
        for (int p = 0; p < param_count; p++) {
            uint8_t val = init_cmds[i++];
            tft_write_data(&val, 1);
        }

        if (cmd == 0x11 || cmd == 0x29) {
            vTaskDelay(pdMS_TO_TICKS(120));
        }
    }

    // 设置背光
    gpio_set_level(PIN_TFT_BL, 1); // 简单开关，PWM先不搞

    ESP_LOGI(TAG, "TFT initialized");
}

// LVGL显示刷新
static void lvgl_flush_cb(lv_disp_drv_t *drv, const lv_area_t *area, lv_color_t *color_map)
{
    // 设置窗口
    tft_write_cmd(0x2A); // 列地址
    uint8_t col_data[] = {
        (area->x1 >> 8) & 0xFF, area->x1 & 0xFF,
        (area->x2 >> 8) & 0xFF, area->x2 & 0xFF,
    };
    tft_write_data(col_data, 4);

    tft_write_cmd(0x2B); // 行地址
    uint8_t row_data[] = {
        (area->y1 >> 8) & 0xFF, area->y1 & 0xFF,
        (area->y2 >> 8) & 0xFF, area->y2 & 0xFF,
    };
    tft_write_data(row_data, 4);

    // 写像素
    tft_write_cmd(0x2C);
    int size = (area->x2 - area->x1 + 1) * (area->y2 - area->y1 + 1);
    tft_write_data((const uint8_t *)color_map, size * 2); // RGB565

    lv_disp_flush_ready(drv);
}

// 触摸读取
static void lvgl_touch_read(lv_indev_drv_t *drv, lv_indev_data_t *data)
{
    // 简化：目前没用触摸，用物理按键
    data->state = LV_INDEV_STATE_REL;
}

// LVGL心跳
static void lvgl_tick_task(void *arg)
{
    while (1) {
        lv_tick_inc(LVGL_TICK_PERIOD_MS);
        vTaskDelay(pdMS_TO_TICKS(LVGL_TICK_PERIOD_MS));
    }
}

// LVGL任务
static void lvgl_task(void *arg)
{
    while (1) {
        lv_task_handler();
        vTaskDelay(pdMS_TO_TICKS(LVGL_TICK_PERIOD_MS));
    }
}

// ---------- 初始化 ----------

void ui_init(void)
{
    ESP_LOGI(TAG, "Initializing UI...");

    // 初始化GPIO
    gpio_set_direction(PIN_TFT_CS, GPIO_MODE_OUTPUT);
    gpio_set_direction(PIN_TFT_DC, GPIO_MODE_OUTPUT);
    gpio_set_direction(PIN_TFT_RST, GPIO_MODE_OUTPUT);
    gpio_set_direction(PIN_TFT_BL, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_TFT_CS, 1);
    gpio_set_level(PIN_TFT_BL, 0);

    // 初始化SPI
    spi_bus_config_t bus_cfg = {
        .mosi_io_num = PIN_TFT_MOSI,
        .miso_io_num = PIN_TFT_MISO,
        .sclk_io_num = PIN_TFT_SCK,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = TFT_WIDTH * TFT_HEIGHT * 2 + 8,
    };
    ESP_ERROR_CHECK(spi_bus_initialize(SPI_TFT_HOST, &bus_cfg, SPI_DMA_CH_AUTO));

    spi_device_interface_config_t dev_cfg = {
        .clock_speed_hz = SPI_TFT_CLOCK_HZ,
        .mode = 0,
        .spics_io_num = PIN_TFT_CS,
        .queue_size = 1,
        .flags = SPI_DEVICE_NO_DUMMY,
    };
    ESP_ERROR_CHECK(spi_bus_add_device(SPI_TFT_HOST, &dev_cfg, &spi_dev));

    // 初始化TFT
    tft_init();

    // 初始化LVGL
    lv_init();

    // 显示缓冲区
    static lv_color_t buf1[TFT_WIDTH * 40];
    static lv_disp_draw_buf_t draw_buf;
    lv_disp_draw_buf_init(&draw_buf, buf1, NULL, TFT_WIDTH * 40);

    // 显示驱动
    static lv_disp_drv_t disp_drv;
    lv_disp_drv_init(&disp_drv);
    disp_drv.hor_res = TFT_WIDTH;
    disp_drv.ver_res = TFT_HEIGHT;
    disp_drv.flush_cb = lvgl_flush_cb;
    disp_drv.draw_buf = &draw_buf;
    lv_disp_drv_register(&disp_drv);

    // 触摸驱动（简化）
    static lv_indev_drv_t indev_drv;
    lv_indev_drv_init(&indev_drv);
    indev_drv.type = LV_INDEV_TYPE_POINTER;
    indev_drv.read_cb = lvgl_touch_read;
    lv_indev_drv_register(&indev_drv);

    // 启动LVGL任务
    xTaskCreate(lvgl_tick_task, "lv_tick", 2048, NULL, 5, NULL);
    xTaskCreate(lvgl_task, "lv_task", 4096, NULL, LVGL_TASK_PRIORITY, NULL);

    // 打开背光
    gpio_set_level(PIN_TFT_BL, 1);

    // 创建主菜单
    ui_screen_main_menu_create();

    ESP_LOGI(TAG, "UI ready");
}

// ---------- UI API ----------

void ui_switch_screen(screen_id_t screen)
{
    switch (screen) {
    case SCREEN_MAIN_MENU:     ui_screen_main_menu_create(); break;
    case SCREEN_DEVICE_SCAN:   ui_screen_device_scan_create(); break;
    case SCREEN_DEVICE_LIST:   ui_screen_device_list_create(); break;
    case SCREEN_REGISTER_VIEW: ui_screen_register_view_create(); break;
    case SCREEN_PROTOCOL_ANALYZER: ui_screen_analyzer_create(); break;
    case SCREEN_SETTINGS:      ui_screen_settings_create(); break;
    case SCREEN_ABOUT:         ui_screen_about_create(); break;
    default: break;
    }
}

void ui_handle_button(int btn_id)
{
    // 转发到当前活动屏幕
    ui_screen_handle_button(btn_id);
}

void ui_show_battery_warning(int voltage_x100)
{
    ui_screen_show_battery_warning(voltage_x100);
}

void ui_add_device(int addr, const char *model)
{
    ui_screen_add_device(addr, model);
}

void ui_scan_complete(int count)
{
    ui_screen_scan_complete(count);
}

void ui_show_error(const char *msg)
{
    ui_screen_show_error(msg);
}
