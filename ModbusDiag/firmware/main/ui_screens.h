/**
 * ModbusDiag - 各页面定义
 */
#ifndef UI_SCREENS_H
#define UI_SCREENS_H

#include <stdint.h>

// 各页面创建函数
void ui_screen_main_menu_create(void);
void ui_screen_device_scan_create(void);
void ui_screen_device_list_create(void);
void ui_screen_register_view_create(void);
void ui_screen_analyzer_create(void);
void ui_screen_settings_create(void);
void ui_screen_about_create(void);

// 按键路由
void ui_screen_handle_button(int btn_id);

// 更新接口
void ui_screen_show_battery_warning(int mv);
void ui_screen_add_device(int addr, const char *model);
void ui_screen_scan_complete(int count);
void ui_screen_show_error(const char *msg);

#endif
