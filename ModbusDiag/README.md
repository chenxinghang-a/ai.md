# ModbusDiag - 便携式Modbus诊断仪

**ESP32-S3 手持式 Modbus RTU/TCP 诊断工具**

## 功能

- ✅ **设备自动发现** — 遍历1-247地址x8种波特率，自动识别在线设备
- ✅ **Modbus RTU主站** — 读写保持寄存器、输入寄存器、线圈、离散输入
- ✅ **Modbus TCP** — 通过WiFi连接远程PLC/网关
- ✅ **寄存器查看/编辑** — 任意地址读写，int16/32/float显示
- ✅ **协议抓包分析** — 监听总线，CRC校验，帧解析，统计
- ✅ **诊断报告** — 一键生成设备通讯健康报告
- ✅ **数据导出** — 通过WiFi导出CSV/JSON到手机或PC
- ✅ **3.5寸TFT彩屏** — LVGL图形界面，480x320分辨率
- ✅ **锂电池供电** — 18650电池，Type-C充电，续航>8小时

## 项目结构

```
ModbusDiag/
├── hardware/               # 硬件设计
│   ├── schematic/          # 原理图 (KiCad)
│   │   ├── SCHEMATIC.md    # 电路设计文档
│   │   └── ModbusDiag.kicad_pro
│   ├── pcb/                # PCB
│   │   └── PCB_GUIDE.md    # PCB设计指南
│   └── gerber/             # 生产文件 (待输出)
├── firmware/               # 固件 (ESP-IDF)
│   ├── main/               # 源代码
│   │   ├── main.c          # 入口
│   │   ├── app_main.c      # 应用初始化
│   │   ├── config.h        # 全局配置
│   │   ├── modbus_rtu.c/h  # Modbus RTU驱动
│   │   ├── modbus_tcp.c/h  # Modbus TCP驱动
│   │   ├── device_scanner.c/h # 设备自动发现
│   │   ├── protocol_analyzer.c/h # 协议分析
│   │   ├── ui.c/h          # LVGL UI
│   │   ├── ui_screens.c/h  # 屏幕页面
│   │   ├── battery.c/h     # 电池管理
│   │   └── data_logger.c/h # 数据记录
│   ├── components/         # 组件库
│   ├── CMakeLists.txt
│   └── sdkconfig.defaults
└── docs/                   # 文档
    ├── ARCHITECTURE.md     # 系统架构
    ├── BOM.md              # 物料清单
    └── references/         # 参考文档
```

## 快速开始

### 硬件

1. 按BOM清单采购元件
2. 使用KiCad打开原理图
3. 按PCB设计指南布局
4. 打样PCB（推荐嘉立创）
5. 焊接元件
6. 3D打印外壳

### 固件

```bash
# 安装ESP-IDF
git clone --recursive https://github.com/espressif/esp-idf.git
cd esp-idf
./install.sh esp32s3
source export.sh

# 编译固件
cd ModbusDiag/firmware
idf.py set-target esp32s3
idf.py menuconfig
idf.py build

# 烧录
idf.py -p /dev/ttyUSB0 flash monitor
```

## 专利方向

| 专利点 | 类型 | 说明 |
|--------|------|------|
| 基于ESP32的便携式多协议Modbus诊断装置 | 实用新型 | 结构+电路 |
| Modbus设备自动发现与寄存器类型推断方法 | 发明 | 算法 |
| 手持诊断仪一键通讯质量评估方法 | 发明 | 方法+算法 |

## 技术规格

| 参数 | 值 |
|------|------|
| 主控 | ESP32-S3 (双核240MHz, WiFi+BLE) |
| 屏幕 | 3.5寸 TFT 480x320 (ILI9488) |
| 触摸 | 电容触摸 (FT6236) |
| RS485 | MAX13487E 隔离型, 1200-115200bps |
| 网络 | WiFi 2.4G (AP/STA), Modbus TCP |
| 电池 | 18650 2600mAh, Type-C充电 |
| 续航 | >8小时 (连续扫描) |
| 尺寸 | 100 x 65 x 25mm |
| PCB | 2层 FR4 1.6mm |
| 固件 | ESP-IDF v5.x + LVGL v8.x |

## License

MIT
