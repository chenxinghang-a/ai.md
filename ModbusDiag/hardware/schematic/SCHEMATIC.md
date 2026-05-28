# ModbusDiag 原理图设计文档

## 1. 系统电源电路

### 1.1 锂电池充电 (TP4056)

```
                    USB 5V
                       │
                      [D1] SS34 (防反接)
                       │
                 ┌─────┴─────┐
         1kΩ    │  TP4056    │
  PROG ──[R]───┤6 PROG  BAT├─── 电池正极(+)
               │5 TEMP   VCC├─── USB 5V
   GND ────────┤4 GND    CHRG├─── LED_CHG (GPIO?)
               │3 CHRG   STDBY├─── LED_STB (GPIO?)
               │2 VCC        │
               │1 CE         │
               └─────────────┘
                    │
                   GND
```

**元件参数：**
- U1: TP4056 (SOP-8/MSOP-8)
- R_PROG: 1.2kΩ (充电电流1A)
- D1: SS34 (肖特基二极管, SMA)
- C1: 10μF/16V (输入滤波)
- C2: 10μF/16V (输出滤波)

### 1.2 5V升压 (MT3608)

```
  电池3.7V (+) ──────┬──── [L1] 4.7μH ────┬──── VOUT (+5V)
                      │                    │
                     [C3]               ┌──┤ SW   FB├──┐
                    ＿10μF             │  │  MT3608    │  │
                      │               │  │ EN      GND├──┘
                     GND              │  └────────────┘
                                      │         │
                                     GND       [R1][R2]分压
                                               10kΩ 1.2kΩ
                                                 │
                                                GND
```

**元件参数：**
- U2: MT3608 (SOT23-6)
- L1: 4.7μH (功率电感, 1.5A)
- R1: 10kΩ (1%)
- R2: 1.2kΩ (1%) → VOUT=0.6×(1+10/1.2)=5.6V (含二极管压降后约5V)
- D2: SS34 (输出整流)
- C3: 22μF/16V (输入)
- C4: 22μF/16V (输出)

### 1.3 3.3V稳压 (AMS1117-3.3)

```
  5V ──────┬──── [C5] 10μF ──────┬──── VDD33 (3.3V)
           │                      │
          GND                   ┌──┤ IN   OUT├──┐
                               │  │ AMS1117-3.3 │  │
                               │  │   SOT-223   │  │
                               └──┤ GND        │  │
                                  └────────────┘  │
                                     │        [C6] 10μF
                                    GND         │
                                               GND
```

**注意事项：**
- AMS1117-3.3最大输出800mA
- 输入输出电容必须靠近芯片引脚
- TBAT+ 通过100k+10k分压到GPIO20用于电池电压检测

## 2. ESP32-S3 最小系统

### 2.1 时钟电路

```
                 40MHz晶振
                 Y1 (±10ppm)
                ┌──┐
          ┌─────┤  ├──────┐
          │     └──┘      │
         [C7]           [C8]
         18pF           18pF
          │               │
         GND             GND
          │               │
       XTAL_P(37)     XTAL_N(36)
```

### 2.2 上电复位 (CHIP_PU)

```
  VDD33 ──────┬──── GPIO0 (上拉10kΩ)
              │
             [R3] 10kΩ
              │
     ┌────────┴────────┐
     │  CHIP_PU (Pin5) │
     │                 │
    [C9] 1μF          │
     │                 │
    GND               GND
```

### 2.3 USB-UART调试

```
  ESP32-S3              CP2102
  GPIO43(TXD) ────────── RXD
  GPIO44(RXD) ────────── TXD
  GPIO0(BOOT) ────────── DTR (通过三极管反转)
  EN(CHIP_PU) ────────── RTS (通过三极管反转)
                      │
                    USB到PC
```

## 3. RS485隔离电路 (MAX13487E)

```
  ESP32-S3              MAX13487E
  3.3V ───────────────┬─ VCC
                      │
  GPIO16(RE) ─────────┤─ RE (低电平接收)
  GPIO17(DE) ─────────┤─ DE (高电平发送)
  GPIO18(RX) ─────────┤─ RO (接收输出)
  GPIO19(TX) ─────────┤─ DI (发送输入)
                      │
                     GND
                      │
                     ─┴─
  A ─────────────────┤ A (RS485+)
  B ─────────────────┤ B (RS485-)
                     ─┬─
                      │
                    GND
```

**保护电路：**
```
  RS485 A ──┬── [TVS1] ── GND
            └── [R5] 10Ω ── MAX13487 A
  RS485 B ──┬── [TVS2] ── GND
            └── [R6] 10Ω ── MAX13487 B
  A ──── [R7] 100kΩ ──── B
```

**元件参数：**
- U3: MAX13487EESA (SOIC-8)
- TVS1, TVS2: SM712 (双向TVS, 针对RS485)
- R5, R6: 10Ω (限流)
- R7: 120Ω (终端匹配电阻, 仅在总线端焊接)

## 4. TFT液晶显示 (ILI9488 3.5寸 480x320)

### 4.1 连接方式 (SPI 4线)

| TFT引脚 | 连接 | ESP32-S3 GPIO |
|---------|------|---------------|
| LCD_CS | SPI片选 | GPIO3 |
| LCD_DC | 数据/命令 | GPIO4 |
| LCD_RST | 复位 | GPIO9 |
| LCD_BL | 背光PWM | GPIO10 |
| MOSI | SPI数据 | GPIO7 (SPI2_MOSI) |
| SCK | SPI时钟 | GPIO6 (SPI2_SCK) |
| MISO | SPI(可选读) | GPIO8 (SPI2_MISO) |
| VCC | 3.3V | VDD33 |
| GND | GND | GND |

### 4.2 触摸 (FT6236, I2C)

| 触摸引脚 | 连接 | ESP32-S3 GPIO |
|---------|------|---------------|
| T_SDA | I2C数据 | GPIO14 (I2C_SDA) |
| T_SCL | I2C时钟 | GPIO15 (I2C_SCL) |
| T_INT | 中断 | GPIO5 (可选) |
| T_RST | 复位 | GPIO13 (可选) |
| VCC | 3.3V | VDD33 |
| GND | GND | GND |

**上拉电阻：** I2C总线需要4.7kΩ上拉到3.3V

## 5. 按键与指示灯

### 5.1 物理按键 (4个)

```
  VDD33 ── [R8] 10kΩ ──┬── GPIO
                        │
                       [SW] 按键
                        │
                       GND
```

| 按键 | GPIO | 功能 |
|------|------|------|
| SW_UP | GPIO25 | 上/增加 |
| SW_DOWN | GPIO26 | 下/减少 |
| SW_OK | GPIO27 | 确认/进入 |
| SW_BACK | GPIO28 | 返回/取消 |

### 5.2 RGB指示灯

```
  GPIO21 ── [R9] 220Ω ──┬── Red阳极(LED_R)
  GPIO22 ── [R10] 220Ω ──┼── Green阳极(LED_G)
  GPIO23 ── [R11] 220Ω ──┼── Blue阳极(LED_B)
                        │
                      RGB共阴 ── GND
```

### 5.3 蜂鸣器

```
  GPIO24 ── [R12] 100Ω ──┬── Buzzer正极
                         │
                       Buzzer负极 ── GND
```

(有源蜂鸣器，PWM控制频率/音量)

## 6. 完整接线汇总

```
┌─────────────────────────────────────────────────────┐
│ ESP32-S3  GPIO 分配表                                 │
├───────┬─────────┬───────────┬────────────────────────┤
│ GPIO  │ 功能    │ 连接对象  │ 备注                    │
├───────┼─────────┼───────────┼────────────────────────┤
│ 3     │ SPI_CS  │ TFT_CS    │ 显示屏片选              │
│ 4     │ DC      │ TFT_DC    │ 数据/命令               │
│ 5     │ INT     │ FT_INT    │ 触摸中断(可选)          │
│ 6     │ SPI_CLK │ TFT_SCK   │ SPI时钟                │
│ 7     │ SPI_MOSI│ TFT_MOSI  │ SPI数据                │
│ 8     │ SPI_MISO│ TFT_MISO  │ SPI(可选读)            │
│ 9     │ RST     │ TFT_RST   │ 显示复位                │
│ 10    │ BL_PWM  │ TFT_BL    │ 背光PWM                │
│ 13    │ RST_T   │ TFT_RST   │ 触摸复位(可选)          │
│ 14    │ I2C_SDA │ FT_SDA    │ 触摸I2C数据             │
│ 15    │ I2C_SCL │ FT_SCL    │ 触摸I2C时钟             │
│ 16    │ RS485_RE│ MAX13487  │ 接收使能                │
│ 17    │ RS485_DE│ MAX13487  │ 发送使能                │
│ 18    │ RS485_RX│ MAX13487  │ UART1接收              │
│ 19    │ RS485_TX│ MAX13487  │ UART1发送              │
│ 20    │ ADC     │ BAT分压   │ 电池电压检测            │
│ 21-23 │ RGB_LED │ LED_R/G/B│ 三色指示灯              │
│ 24    │ PWM     │ Buzzer    │ 蜂鸣器                  │
│ 25-28 │ KEY     │ SW_UP/DN  │ 4个物理按键             │
│       │         │ _OK/_BACK │                        │
│ 43    │ U0TXD   │ CP2102_RX│ 调试串口TX              │
│ 44    │ U0RXD   │ CP2102_TX│ 调试串口RX              │
└───────┴─────────┴───────────┴────────────────────────┘
```

## Netlist (CSV格式)

```csv
Net,From_Pin,To_Pin
VDD33,AMS1117-3.3 OUT,ESP32-S3 VDD3P3(2,3,20,46),MAX13487 VCC,TFT VCC,FT6236 VCC,10k上拉
GND,TP4056 GND,MT3608 GND,AMS1117 GND,ESP32 GND(epad),MAX13487 GND,TFT GND,FT6236 GND,CP2102 GND
5V,MT3608 OUT,AMS1117 IN
BAT+,TP4056 BAT,MT3608 IN
SPI_CLK,GPIO6,TFT_SCK
SPI_MOSI,GPIO7,TFT_MOSI
SPI_MISO,GPIO8,TFT_MISO
TFT_CS,GPIO3,TFT_CS
TFT_DC,GPIO4,TFT_DC
TFT_RST,GPIO9,TFT_RST
TFT_BL,GPIO10,TFT_BL
I2C_SDA,GPIO14,FT_SDA
I2C_SCL,GPIO15,FT_SCL
U1TXD,GPIO19,MAX13487 DI
U1RXD,GPIO18,MAX13487 RO
RS485_RE,GPIO16,MAX13487 RE
RS485_DE,GPIO17,MAX13487 DE
BAT_ADC,GPIO20,分压电阻中点
BTN_UP,GPIO25,按键SW_UP
BTN_DOWN,GPIO26,按键SW_DOWN
BTN_OK,GPIO27,按键SW_OK
BTN_BACK,GPIO28,按键SW_BACK
LED_R,GPIO21,RGB_R
LED_G,GPIO22,RGB_G
LED_B,GPIO23,RGB_B
BUZZER,GPIO24,蜂鸣器
U0TXD,GPIO43,CP2102 RXD
U0RXD,GPIO44,CP2102 TXD
```
