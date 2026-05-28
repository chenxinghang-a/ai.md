/**
 * ModbusDiag - LVGL UI框架
 */
#ifndef UI_H
#define UI_H

#include <stdint.h>
#include <stdbool.h>

// 屏幕ID
typedef enum {
    SCREEN_MAIN_MENU,
    SCREEN_DEVICE_SCAN,
    SCREEN_DEVICE_LIST,
    SCREEN_REGISTER_VIEW,
    SCREEN_REGISTER_EDIT,
    SCREEN_PROTOCOL_ANALYZER,
    SCREEN_OSCILLOSCOPE,
    SCREEN_DIAG_REPORT,
    SCREEN_SETTINGS,
    SCREEN_ABOUT,
    SCREEN_COUNT
} screen_id_t;

// 初始化LVGL和硬件
void ui_init(void);

// 切换屏幕
void ui_switch_screen(screen_id_t screen);

// 按键处理
void ui_handle_button(int btn_id);

// 更新接口
void ui_show_battery_warning(int voltage_x100);
void ui_add_device(int addr, const char *model);
void ui_scan_complete(int count);
void ui_show_error(const char *msg);

#endif
