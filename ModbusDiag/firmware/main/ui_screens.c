/**
 * ModbusDiag - LVGL屏幕定义
 */
#include <stdio.h>
#include <string.h>
#include "esp_log.h"
#include "lvgl.h"
#include "ui_screens.h"
#include "config.h"

static const char *TAG = "UI_SCREEN";

// 当前屏幕ID
static int current_screen = 0;

// 全局对象
static lv_obj_t *battery_label = NULL;
static lv_obj_t *status_bar_label = NULL;

// ============ 状态栏 ============
static void create_status_bar(lv_obj_t *parent)
{
    static lv_style_t style;
    lv_style_init(&style);
    lv_style_set_bg_color(&style, lv_color_hex(0x1a1a2e));
    lv_style_set_text_color(&style, lv_color_white());
    lv_style_set_pad_all(&style, 4);

    lv_obj_t *bar = lv_obj_create(parent);
    lv_obj_set_size(bar, TFT_WIDTH, 24);
    lv_obj_set_pos(bar, 0, 0);
    lv_obj_add_style(bar, &style, 0);
    lv_obj_set_scrollbar_mode(bar, LV_SCROLLBAR_MODE_OFF);

    battery_label = lv_label_create(bar);
    lv_label_set_text(battery_label, "BAT: 100%");
    lv_obj_align(battery_label, LV_ALIGN_LEFT_MID, 5, 0);

    status_bar_label = lv_label_create(bar);
    lv_label_set_text(status_bar_label, "ModbusDiag");
    lv_obj_align(status_bar_label, LV_ALIGN_RIGHT_MID, -5, 0);
}

// ============ 主菜单 ============
static lv_obj_t *main_menu = NULL;

void ui_screen_main_menu_create(void)
{
    if (main_menu) {
        lv_scr_load(main_menu);
        return;
    }

    main_menu = lv_obj_create(NULL);
    lv_obj_set_size(main_menu, TFT_WIDTH, TFT_HEIGHT);
    lv_obj_set_style_bg_color(main_menu, lv_color_hex(0x16213e), 0);

    create_status_bar(main_menu);

    // 标题
    lv_obj_t *title = lv_label_create(main_menu);
    lv_label_set_text(title, "ModbusDiag");
    lv_obj_set_style_text_color(title, lv_color_hex(0x00d2ff), 0);
    lv_obj_set_style_text_font(title, &lv_font_montserrat_20, 0);
    lv_obj_align(title, LV_ALIGN_TOP_MID, 0, 30);

    lv_obj_t *subtitle = lv_label_create(main_menu);
    lv_label_set_text(subtitle, "便携式Modbus诊断仪 v" FW_VERSION_STR);
    lv_obj_set_style_text_color(subtitle, lv_color_hex(0x888888), 0);
    lv_obj_align(subtitle, LV_ALIGN_TOP_MID, 0, 55);

    // 菜单项
    const char *items[] = {
        "1. 设备扫描",
        "2. 设备列表",
        "3. 寄存器读写",
        "4. 协议分析",
        "5. 诊断报告",
        "6. 设置",
    };

    for (int i = 0; i < 6; i++) {
        lv_obj_t *btn = lv_btn_create(main_menu);
        lv_obj_set_size(btn, TFT_WIDTH - 40, 32);
        lv_obj_set_pos(btn, 20, 85 + i * 37);
        lv_obj_set_style_bg_color(btn, lv_color_hex(0x0f3460), 0);
        lv_obj_set_style_bg_color(btn, lv_color_hex(0x1a5276), LV_STATE_PRESSED);

        lv_obj_t *label = lv_label_create(btn);
        lv_label_set_text(label, items[i]);
        lv_obj_set_style_text_color(label, lv_color_hex(0xeeeeee), 0);
        lv_obj_center(label);
    }

    lv_scr_load(main_menu);
    current_screen = 0;
    ESP_LOGI(TAG, "Main menu created");
}

// ============ 设备扫描页 ============
static lv_obj_t *scan_screen = NULL;
static lv_obj_t *scan_progress_bar = NULL;
static lv_obj_t *scan_progress_label = NULL;
static lv_obj_t *scan_status_label = NULL;
static lv_obj_t *scan_device_list = NULL;

void ui_screen_device_scan_create(void)
{
    if (scan_screen) {
        lv_scr_load(scan_screen);
        return;
    }

    scan_screen = lv_obj_create(NULL);
    lv_obj_set_size(scan_screen, TFT_WIDTH, TFT_HEIGHT);
    lv_obj_set_style_bg_color(scan_screen, lv_color_hex(0x16213e), 0);

    create_status_bar(scan_screen);

    lv_obj_t *title = lv_label_create(scan_screen);
    lv_label_set_text(title, "设备扫描");
    lv_obj_set_style_text_color(title, lv_color_hex(0x00d2ff), 0);
    lv_obj_align(title, LV_ALIGN_TOP_MID, 0, 30);

    // 进度条
    scan_progress_bar = lv_bar_create(scan_screen);
    lv_obj_set_size(scan_progress_bar, TFT_WIDTH - 40, 20);
    lv_obj_align(scan_progress_bar, LV_ALIGN_TOP_MID, 0, 60);
    lv_obj_set_style_bg_color(scan_progress_bar, lv_color_hex(0x333333), LV_PART_MAIN);
    lv_obj_set_style_bg_color(scan_progress_bar, lv_color_hex(0x00d2ff), LV_PART_INDICATOR);
    lv_bar_set_range(scan_progress_bar, 0, 100);
    lv_bar_set_value(scan_progress_bar, 0, LV_ANIM_OFF);

    scan_progress_label = lv_label_create(scan_screen);
    lv_label_set_text(scan_progress_label, "0%");
    lv_obj_align(scan_progress_label, LV_ALIGN_TOP_MID, 0, 85);
    lv_obj_set_style_text_color(scan_progress_label, lv_color_hex(0xaaaaaa), 0);

    scan_status_label = lv_label_create(scan_screen);
    lv_label_set_text(scan_status_label, "按 OK 开始扫描");
    lv_obj_align(scan_status_label, LV_ALIGN_TOP_MID, 0, 110);
    lv_obj_set_style_text_color(scan_status_label, lv_color_hex(0x888888), 0);

    // 设备结果列表
    scan_device_list = lv_list_create(scan_screen);
    lv_obj_set_size(scan_device_list, TFT_WIDTH - 40, 160);
    lv_obj_align(scan_device_list, LV_ALIGN_TOP_MID, 0, 140);
    lv_obj_set_style_bg_color(scan_device_list, lv_color_hex(0x0f3460), 0);
    lv_obj_set_style_text_color(scan_device_list, lv_color_hex(0xcccccc), 0);

    lv_scr_load(scan_screen);
    current_screen = 1;
}

// ============ 设备列表页 ============
static lv_obj_t *devlist_screen = NULL;
static lv_obj_t *devlist_list = NULL;
static int devlist_count = 0;

void ui_screen_device_list_create(void)
{
    if (devlist_screen) {
        lv_scr_load(devlist_screen);
        return;
    }

    devlist_screen = lv_obj_create(NULL);
    lv_obj_set_size(devlist_screen, TFT_WIDTH, TFT_HEIGHT);
    lv_obj_set_style_bg_color(devlist_screen, lv_color_hex(0x16213e), 0);

    create_status_bar(devlist_screen);

    lv_obj_t *title = lv_label_create(devlist_screen);
    lv_label_set_text(title, "设备列表");
    lv_obj_set_style_text_color(title, lv_color_hex(0x00d2ff), 0);
    lv_obj_align(title, LV_ALIGN_TOP_MID, 0, 30);

    lv_obj_t *info = lv_label_create(devlist_screen);
    lv_label_set_text_fmt(info, "已发现 %d 台设备", devlist_count);
    lv_obj_set_style_text_color(info, lv_color_hex(0xaaaaaa), 0);
    lv_obj_align(info, LV_ALIGN_TOP_MID, 0, 55);

    devlist_list = lv_list_create(devlist_screen);
    lv_obj_set_size(devlist_list, TFT_WIDTH - 40, 220);
    lv_obj_align(devlist_list, LV_ALIGN_TOP_MID, 0, 80);
    lv_obj_set_style_bg_color(devlist_list, lv_color_hex(0x0f3460), 0);

    // 提示
    lv_obj_t *hint = lv_label_create(devlist_screen);
    lv_label_set_text(hint, "按OK选择设备，BACK返回");
    lv_obj_set_style_text_color(hint, lv_color_hex(0x666666), 0);
    lv_obj_align(hint, LV_ALIGN_BOTTOM_MID, 0, -10);

    lv_scr_load(devlist_screen);
    current_screen = 2;
}

// ============ 寄存器读写页 ============
static lv_obj_t *reg_screen = NULL;

void ui_screen_register_view_create(void)
{
    if (reg_screen) {
        lv_scr_load(reg_screen);
        return;
    }

    reg_screen = lv_obj_create(NULL);
    lv_obj_set_size(reg_screen, TFT_WIDTH, TFT_HEIGHT);
    lv_obj_set_style_bg_color(reg_screen, lv_color_hex(0x16213e), 0);

    create_status_bar(reg_screen);

    lv_obj_t *title = lv_label_create(reg_screen);
    lv_label_set_text(title, "寄存器读写");
    lv_obj_set_style_text_color(title, lv_color_hex(0x00d2ff), 0);
    lv_obj_align(title, LV_ALIGN_TOP_MID, 0, 30);

    lv_obj_t *info = lv_label_create(reg_screen);
    lv_label_set_text(info, "请在设备列表中选择设备");
    lv_obj_set_style_text_color(info, lv_color_hex(0x888888), 0);
    lv_obj_align(info, LV_ALIGN_TOP_MID, 0, 60);

    lv_scr_load(reg_screen);
    current_screen = 3;
}

// ============ 协议分析页 ============
static lv_obj_t *analyzer_screen = NULL;

void ui_screen_analyzer_create(void)
{
    if (analyzer_screen) {
        lv_scr_load(analyzer_screen);
        return;
    }

    analyzer_screen = lv_obj_create(NULL);
    lv_obj_set_size(analyzer_screen, TFT_WIDTH, TFT_HEIGHT);
    lv_obj_set_style_bg_color(analyzer_screen, lv_color_hex(0x16213e), 0);

    create_status_bar(analyzer_screen);

    lv_obj_t *title = lv_label_create(analyzer_screen);
    lv_label_set_text(title, "协议分析");
    lv_obj_set_style_text_color(title, lv_color_hex(0x00d2ff), 0);
    lv_obj_align(title, LV_ALIGN_TOP_MID, 0, 30);

    lv_obj_t *info = lv_label_create(analyzer_screen);
    lv_label_set_text(info, "监听Modbus总线数据...\nOK=开始/停止");
    lv_obj_set_style_text_color(info, lv_color_hex(0x888888), 0);
    lv_obj_align(info, LV_ALIGN_TOP_MID, 0, 60);

    lv_scr_load(analyzer_screen);
    current_screen = 4;
}

// ============ 设置页 ============
static lv_obj_t *settings_screen = NULL;

void ui_screen_settings_create(void)
{
    if (settings_screen) {
        lv_scr_load(settings_screen);
        return;
    }

    settings_screen = lv_obj_create(NULL);
    lv_obj_set_size(settings_screen, TFT_WIDTH, TFT_HEIGHT);
    lv_obj_set_style_bg_color(settings_screen, lv_color_hex(0x16213e), 0);

    create_status_bar(settings_screen);

    lv_obj_t *title = lv_label_create(settings_screen);
    lv_label_set_text(title, "设置");
    lv_obj_set_style_text_color(title, lv_color_hex(0x00d2ff), 0);
    lv_obj_align(title, LV_ALIGN_TOP_MID, 0, 30);

    const char *settings[] = {
        "波特率: 9600",
        "超时: 1000ms",
        "背光: 50%",
        "WiFi AP: On",
        "关于",
    };

    for (int i = 0; i < 5; i++) {
        lv_obj_t *btn = lv_btn_create(settings_screen);
        lv_obj_set_size(btn, TFT_WIDTH - 40, 32);
        lv_obj_set_pos(btn, 20, 60 + i * 37);
        lv_obj_set_style_bg_color(btn, lv_color_hex(0x0f3460), 0);

        lv_obj_t *label = lv_label_create(btn);
        lv_label_set_text(label, settings[i]);
        lv_obj_set_style_text_color(label, lv_color_hex(0xeeeeee), 0);
        lv_obj_center(label);
    }

    lv_scr_load(settings_screen);
    current_screen = 5;
}

// ============ 关于页 ============
void ui_screen_about_create(void)
{
    lv_obj_t *scr = lv_obj_create(NULL);
    lv_obj_set_size(scr, TFT_WIDTH, TFT_HEIGHT);
    lv_obj_set_style_bg_color(scr, lv_color_hex(0x16213e), 0);

    create_status_bar(scr);

    lv_obj_t *title = lv_label_create(scr);
    lv_label_set_text(title, "关于");
    lv_obj_set_style_text_color(title, lv_color_hex(0x00d2ff), 0);
    lv_obj_align(title, LV_ALIGN_TOP_MID, 0, 30);

    lv_obj_t *info = lv_label_create(scr);
    lv_label_set_text(info,
        "ModbusDiag v" FW_VERSION_STR "\n\n"
        "便携式Modbus诊断仪\n"
        "基于ESP32-S3\n\n"
        "功能:\n"
        " - 设备自动发现\n"
        " - Modbus RTU/TCP\n"
        " - 寄存器读写\n"
        " - 协议抓包分析\n"
        " - 诊断报告\n\n"
        "BACK 返回主菜单");
    lv_obj_set_style_text_color(info, lv_color_hex(0xcccccc), 0);
    lv_obj_align(info, LV_ALIGN_TOP_MID, 0, 60);

    lv_scr_load(scr);
    current_screen = 6;
}

// ============ 按键路由 ============
void ui_screen_handle_button(int btn_id)
{
    switch (current_screen) {
    case 0: // 主菜单
        if (btn_id == 1/*UP*/) { /* 向上滚动 */ }
        else if (btn_id == 2/*DOWN*/) { /* 向下滚动 */ }
        else if (btn_id == 3/*OK*/) { ui_switch_screen(SCREEN_DEVICE_SCAN); }
        else if (btn_id == 4/*BACK*/) { /* 无操作 */ }
        break;
    case 1: // 扫描
        if (btn_id == 3/*OK*/) { /* 开始扫描 */ }
        else if (btn_id == 4/*BACK*/) { ui_switch_screen(SCREEN_MAIN_MENU); }
        break;
    default:
        if (btn_id == 4) { ui_switch_screen(SCREEN_MAIN_MENU); }
        break;
    }
}

// ============ 更新接口 ============
void ui_screen_show_battery_warning(int mv)
{
    if (battery_label) {
        float v = mv / 100.0f;
        int pct = (int)((v - 3.3f) / (4.2f - 3.3f) * 100);
        if (pct < 0) pct = 0;
        if (pct > 100) pct = 100;
        lv_label_set_text_fmt(battery_label, "BAT: %d%%", pct);
    }
}

void ui_screen_add_device(int addr, const char *model)
{
    if (scan_device_list) {
        lv_obj_t *btn = lv_btn_create(scan_device_list);
        lv_obj_set_size(btn, lv_pct(100), 30);
        lv_obj_set_style_bg_color(btn, lv_color_hex(0x1a5276), 0);

        lv_obj_t *label = lv_label_create(btn);
        lv_label_set_text_fmt(label, "Addr %d: %s", addr, model ? model : "Unknown");
        lv_obj_center(label);
    }

    if (devlist_list) {
        lv_obj_t *btn = lv_btn_create(devlist_list);
        lv_obj_t *label = lv_label_create(btn);
        lv_label_set_text_fmt(label, "Addr %d: %s", addr, model ? model : "Unknown");
        lv_obj_center(label);
    }
}

void ui_screen_scan_complete(int count)
{
    if (scan_status_label) {
        lv_label_set_text_fmt(scan_status_label, "扫描完成: 发现 %d 台设备", count);
    }
}

void ui_screen_show_error(const char *msg)
{
    if (scan_status_label) {
        lv_label_set_text(scan_status_label, msg);
        lv_obj_set_style_text_color(scan_status_label, lv_color_hex(0xff4444), 0);
    }
}
