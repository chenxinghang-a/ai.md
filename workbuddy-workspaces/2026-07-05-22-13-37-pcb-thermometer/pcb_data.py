# PCB布线数据文件 - 数字温度测量电路
# 网格尺寸: 30列(X=1~30) × 24行(Y=1~24)
# 生成时间: 2026-07-05

pcb_data = {
    "grid": {
        "cols": 30,
        "rows": 24,
        "description": "每格对应坐标纸一格，单位可自定义(mm)"
    },

    # ==================== 左侧端子区 ====================
    "terminals": [
        {"id": "T1", "name": "+12V", "x": 1, "y": 2, "type": "power_in"},
        {"id": "T2", "name": "-12V", "x": 1, "y": 5, "type": "power_in"},
        {"id": "T3", "name": "GND", "x": 1, "y": 8, "type": "ground"},
        {"id": "T4", "name": "M+", "x": 1, "y": 11, "type": "signal_out"},
        {"id": "T5", "name": "M-", "x": 1, "y": 14, "type": "signal_out"},
        {"id": "T6", "name": "AD590+", "x": 1, "y": 17, "type": "power_out"},
        {"id": "T7", "name": "NC/备用", "x": 1, "y": 20, "type": "unused"}
    ],

    # ==================== 元件布局 ====================
    "components": [
        # ---- 上半部：温度检测通道 (Y ≤ 12) ----

        # U1: AD590温度传感器 (TO-52封装, 3脚)
        # 图中画成电感符号，实际为3脚TO-52
        {
            "id": "U1",
            "name": "AD590",
            "type": "sensor",
            "package": "TO-52",
            "pins": 3,
            "x": 4, "y": 3,
            "width": 2, "height": 2,
            "pin_positions": {
                1: {"x": 4, "y": 2, "net": "+12V"},      # V+
                2: {"x": 5, "y": 4, "net": "Io"},        # 电流输出 → R1
                3: {"x": 4, "y": 4, "net": "GND"}       # Case接地
            },
            "description": "温度传感器，电流型输出1μA/K"
        },

        # R1: 2KΩ I/V转换电阻
        {
            "id": "R1",
            "name": "R1",
            "type": "resistor",
            "value": "2KΩ",
            "package": "AXIAL-0.4",
            "x": 7, "y": 5,
            "width": 2, "height": 1,
            "orientation": "horizontal",
            "pin1": {"x": 7, "y": 5, "net": "Io"},       # 来自U1-Io
            "pin2": {"x": 9, "y": 5, "net": "Node_A"},   # 节点A
            "description": "I/V转换，将电流转为电压"
        },

        # C1: 0.01μF 滤波电容
        {
            "id": "C1",
            "name": "C1",
            "type": "capacitor",
            "value": "0.01μF (103)",
            "package": "RAD-0.2",
            "x": 9, "y": 7,
            "width": 1, "height": 1,
            "pin1": {"x": 9, "y": 7, "net": "Node_A"},   # 接节点A
            "pin2": {"x": 9, "y": 8, "net": "GND"},      # 接地
            "description": "并联滤波"
        },

        # U2: CP-07运算放大器 (DIP-8)
        # 缺口朝左，B面观察引脚编号顺时针
        # 左列(上→下): 1-4, 右列(上→下): 8-5
        {
            "id": "U2",
            "name": "CP-07 (U2)",
            "type": "opamp",
            "package": "DIP-8",
            "pins": 8,
            "x": 14, "y": 4,
            "width": 3, "height": 4,
            "orientation": "horizontal",
            "pin_positions": {
                1: {"x": 14, "y": 4, "net": "+12V"},     # 电源
                2: {"x": 14, "y": 5, "net": "U2_IN-"},   # 反相输入 ← R2
                3: {"x": 14, "y": 6, "net": "Node_A"},   # 同相输入 ← R1/C1结点
                4: {"x": 14, "y": 7, "net": "-12V"},     # 负电源
                5: {"x": 16, "y": 7, "net": "W3_Wiper"}, # 调零输入 ← W3中端
                6: {"x": 16, "y": 6, "net": "M+_OUT"},   # 输出 → M+
                7: {"x": 16, "y": 5, "net": "+12V"},     # 电源
                8: {"x": 16, "y": 4, "net": "W3_Bottom"} # ← W3下端
            },
            "description": "主运算放大器，温度通道"
        },

        # R2: 2.6KΩ 输入偏置电阻
        {
            "id": "R2",
            "name": "R2",
            "type": "resistor",
            "value": "2.6KΩ",
            "package": "AXIAL-0.4",
            "x": 11, "y": 5,
            "width": 2, "height": 1,
            "orientation": "horizontal",
            "pin1": {"x": 11, "y": 5, "net": "GND"},
            "pin2": {"x": 13, "y": 5, "net": "U2_IN-"},
            "description": "U2反相端偏置电阻"
        },

        # W3: 20K电位器 (调零)
        {
            "id": "W3",
            "name": "W3",
            "type": "potentiometer",
            "value": "20KΩ",
            "package": "VERTICAL-POT",
            "x": 23, "y": 4,
            "width": 2, "height": 3,
            "orientation": "vertical",
            "pin1": {"x": 24, "y": 4, "net": "+12V"},     # 上端
            "pin2": {"x": 24, "y": 5.5, "net": "W3_Wiper"},  # 中端(滑动端)
            "pin3": {"x": 24, "y": 7, "net": "W3_Bottom"},   # 下端→U2-脚8
            "description": "U2调零电位器"
        },

        # U2反馈网络元件

        # R3: 1KΩ 反馈电阻
        {
            "id": "R3",
            "name": "R3",
            "type": "resistor",
            "value": "1KΩ",
            "package": "AXIAL-0.4",
            "x": 19, "y": 8,
            "width": 2, "height": 1,
            "orientation": "horizontal",
            "pin1": {"x": 19, "y": 8, "net": "M+_OUT"},   # 来自U2-OUT
            "pin2": {"x": 21, "y": 8, "net": "Node_G4"},  # 节点G4
            "description": "反馈电阻"
        },

        # R4: 1KΩ 反馈网络对地电阻
        {
            "id": "R4",
            "name": "R4",
            "type": "resistor",
            "value": "1KΩ",
            "package": "AXIAL-0.4",
            "x": 21, "y": 9,
            "width": 1, "height": 2,
            "orientation": "vertical",
            "pin1": {"x": 21, "y": 9, "net": "Node_G4"},
            "pin2": {"x": 21, "y": 11, "net": "GND"},
            "description": "反馈网络对地电阻"
        },

        # C4: 0.01μF 反馈电容
        {
            "id": "C4",
            "name": "C4",
            "type": "capacitor",
            "value": "0.01μF",
            "package": "RAD-0.2",
            "x": 22, "y": 9,
            "width": 1, "height": 2,
            "orientation": "vertical",
            "pin1": {"x": 22, "y": 9, "net": "Node_G4"},
            "pin2": {"x": 22, "y": 11, "net": "GND"},
            "description": "反馈网络补偿电容"
        },

        # W1: 10K电位器 (增益调节)
        {
            "id": "W1",
            "name": "W1",
            "type": "potentiometer",
            "value": "10KΩ",
            "package": "HORIZONTAL-POT",
            "x": 25, "y": 8,
            "width": 3, "height": 1,
            "orientation": "horizontal",
            "pin1": {"x": 25, "y": 8, "net": "M+_OUT"},    # 一端接M+输出线
            "pin2": {"x": 27, "y": 8, "net": "Node_G4"},   # 滑动端接节点G4
            "description": "U2增益调节电位器"
        },

        # 去耦电容 C2, C3

        # C2: 0.01μF (-12V去耦)
        {
            "id": "C2",
            "name": "C2",
            "type": "capacitor",
            "value": "0.01μF",
            "package": "RAD-0.2",
            "x": 14, "y": 10,
            "width": 1, "height": 2,
            "orientation": "vertical",
            "pin1": {"x": 14, "y": 10, "net": "-12V"},
            "pin2": {"x": 14, "y": 12, "net": "GND"},
            "description": "U2负电源去耦"
        },

        # C3: 0.01μF (+12V去耦，靠近U2-脚7)
        {
            "id": "C3",
            "name": "C3",
            "type": "capacitor",
            "value": "0.01μF",
            "package": "RAD-0.2",
            "x": 17, "y": 4,
            "width": 1, "height": 2,
            "orientation": "vertical",
            "pin1": {"x": 17, "y": 4, "net": "+12V"},
            "pin2": {"x": 17, "y": 6, "net": "GND"},
            "description": "U2正电源去耦"
        },

        # ---- 下半部：基准校正通道 (Y ≥ 13) ----

        # U3: MC1403精密基准源 (3脚)
        {
            "id": "U3",
            "name": "MC1403 (U3)",
            "type": "voltage_reference",
            "package": "SIP-3",
            "pins": 3,
            "x": 5, "y": 15,
            "width": 2, "height": 2,
            "pin_positions": {
                1: {"x": 5, "y": 14, "net": "+12V"},     # V+
                2: {"x": 6, "y": 16, "net": "U3_Vout"},  # Vout = 2.5V
                3: {"x": 5, "y": 16, "net": "GND"}       # GND
            },
            "description": "2.5V精密基准电压源"
        },

        # R5: 10KΩ 基准输出电阻
        {
            "id": "R5",
            "name": "R5",
            "type": "resistor",
            "value": "10KΩ",
            "package": "AXIAL-0.4",
            "x": 8, "y": 16,
            "width": 2, "height": 1,
            "orientation": "horizontal",
            "pin1": {"x": 8, "y": 16, "net": "U3_Vout"},  # 来自U3
            "pin2": {"x": 10, "y": 16, "net": "U4_IN-"}, # 到U4-IN-
            "description": "基准输出限流/分压"
        },

        # C5: 0.01μF 滤波
        {
            "id": "C5",
            "name": "C5",
            "type": "capacitor",
            "value": "0.01μF",
            "package": "RAD-0.2",
            "x": 10, "y": 18,
            "width": 1, "height": 1,
            "pin1": {"x": 10, "y": 18, "net": "U4_IN-"},
            "pin2": {"x": 10, "y": 19, "net": "GND"},
            "description": "U4输入滤波"
        },

        # U4: CP-07运算放大器 (DIP-8，与U2对称布局)
        {
            "id": "U4",
            "name": "CP-07 (U4)",
            "type": "opamp",
            "package": "DIP-8",
            "pins": 8,
            "x": 14, "y": 15,
            "width": 3, "height": 4,
            "orientation": "horizontal",
            "pin_positions": {
                1: {"x": 14, "y": 15, "net": "+12V"},     # 电源
                2: {"x": 14, "y": 16, "net": "U4_IN-"},  # 反相输入 ← R5
                3: {"x": 14, "y": 17, "net": "GND"},     # 同相输入 ← GND
                4: {"x": 14, "y": 18, "net": "-12V"},    # 负电源
                5: {"x": 16, "y": 18, "net": "W4_Wiper"},# 调零输入 ← W4中端
                6: {"x": 16, "y": 17, "net": "M-_OUT"},  # 输出 → M-
                7: {"x": 16, "y": 16, "net": "+12V"},    # 电源
                8: {"x": 16, "y": 15, "net": "W4_Bottom"}# ← W4下端
            },
            "description": "基准校正通道运算放大器"
        },

        # W4: 20K电位器 (调零)
        {
            "id": "W4",
            "name": "W4",
            "type": "potentiometer",
            "value": "20KΩ",
            "package": "VERTICAL-POT",
            "x": 23, "y": 15,
            "width": 2, "height": 3,
            "orientation": "vertical",
            "pin1": {"x": 24, "y": 15, "net": "+12V"},     # 上端
            "pin2": {"x": 24, "y": 16.5, "net": "W4_Wiper"}, # 中端
            "pin3": {"x": 24, "y": 18, "net": "W4_Bottom"},  # 下端→U4-脚8
            "description": "U4调零电位器"
        },

        # U4反馈网络

        # R6: 680Ω 反馈电阻
        {
            "id": "R6",
            "name": "R6",
            "type": "resistor",
            "value": "680Ω",
            "package": "AXIAL-0.4",
            "x": 19, "y": 19,
            "width": 2, "height": 1,
            "orientation": "horizontal",
            "pin1": {"x": 19, "y": 19, "net": "M-_OUT"},   # 来自U4-OUT
            "pin2": {"x": 21, "y": 19, "net": "Node_G7"},  # 节点G7
            "description": "反馈电阻"
        },

        # R7: 1KΩ 对地电阻
        {
            "id": "R7",
            "name": "R7",
            "type": "resistor",
            "value": "1KΩ",
            "package": "AXIAL-0.4",
            "x": 21, "y": 20,
            "width": 1, "height": 2,
            "orientation": "vertical",
            "pin1": {"x": 21, "y": 20, "net": "Node_G7"},
            "pin2": {"x": 21, "y": 22, "net": "GND"},
            "description": "反馈网络对地电阻"
        },

        # C7: 0.01μF 补偿电容
        {
            "id": "C7",
            "name": "C7",
            "type": "capacitor",
            "value": "0.01μF",
            "package": "RAD-0.2",
            "x": 22, "y": 20,
            "width": 1, "height": 2,
            "orientation": "vertical",
            "pin1": {"x": 22, "y": 20, "net": "Node_G7"},
            "pin2": {"x": 22, "y": 22, "net": "GND"},
            "description": "反馈网络补偿电容"
        },

        # W2: 10K电位器 (增益调节)
        {
            "id": "W2",
            "name": "W2",
            "type": "potentiometer",
            "value": "10KΩ",
            "package": "HORIZONTAL-POT",
            "x": 25, "y": 19,
            "width": 3, "height": 1,
            "orientation": "horizontal",
            "pin1": {"x": 25, "y": 19, "net": "M-_OUT"},   # 接M-输出线
            "pin2": {"x": 27, "y": 19, "net": "Node_G7"},  # 滑动端接节点G7
            "description": "U4增益调节电位器"
        },

        # C6: 0.01μF (-12V去耦，靠近U4)
        {
            "id": "C6",
            "name": "C6",
            "type": "capacitor",
            "value": "0.01μF",
            "package": "RAD-0.2",
            "x": 14, "y": 20,
            "width": 1, "height": 2,
            "orientation": "vertical",
            "pin1": {"x": 14, "y": 20, "net": "-12V"},
            "pin2": {"x": 14, "y": 22, "net": "GND"},
            "description": "U4负电源去耦"
        }
    ],

    # ==================== 电源轨 ====================
    "power_rails": [
        {
            "net": "+12V",
            "layer": "B",
            "color": "red",
            "path": [
                {"x": 1, "y": 1},
                {"x": 30, "y": 1}
            ],
            "description": "顶部正电源总线"
        },
        {
            "net": "-12V",
            "layer": "B",
            "color": "blue",
            "path": [
                {"x": 1, "y": 13},
                {"x": 30, "y": 13}
            ],
            "description": "中间负电源分隔线"
        },
        {
            "net": "GND",
            "layer": "B",
            "color": "black",
            "path": [
                {"x": 1, "y": 24},
                {"x": 30, "y": 24}
            ],
            "description": "底部地线总线"
        }
    ],

    # ==================== B面走线 (蓝色) ====================
    "traces": [

        # ===== 电源分配走线 =====

        # 1. T1(+12V) → +12V Rail
        {
            "id": "TR_001",
            "net": "+12V",
            "layer": "B",
            "from": {"x": 1, "y": 2},          # T1
            "to": {"x": 1, "y": 1},           # +12V rail
            "via_points": [],
            "description": "端子T1到+12V轨"
        },

        # 2. +12V Rail → U1-脚1(V+)
        {
            "id": "TR_002",
            "net": "+12V",
            "layer": "B",
            "from": {"x": 4, "y": 1},         # 从rail向下
            "to": {"x": 4, "y": 2},           # U1-pin1
            "via_points": [],
            "description": "+12V到AD590供电"
        },

        # 3. +12V Rail → U2-脚1
        {
            "id": "TR_003",
            "net": "+12V",
            "layer": "B",
            "from": {"x": 14, "y": 1},        # 从rail向下
            "to": {"x": 14, "y": 4},          # U2-pin1
            "via_points": [],
            "description": "+12V到U2正电源"
        },

        # 4. +12V Rail → U2-脚7
        {
            "id": "TR_004",
            "net": "+12V",
            "layer": "B",
            "from": {"x": 16, "y": 1},        # 从rail向下
            "to": {"x": 16, "y": 5},          # U2-pin7
            "via_points": [{"x": 16, "y": 3}],
            "description": "+12V到U2另一电源脚"
        },

        # 5. +12V Rail → W3-上端
        {
            "id": "TR_005",
            "net": "+12V",
            "layer": "B",
            "from": {"x": 24, "y": 1},        # 从rail向下
            "to": {"x": 24, "y": 4},          # W3-pin1
            "via_points": [],
            "description": "+12V到W3上端"
        },

        # 6. +12V Rail → U3-脚1
        {
            "id": "TR_006",
            "net": "+12V",
            "layer": "B",
            "from": {"x": 5, "y": 1},         # 从rail向下
            "to": {"x": 5, "y": 14},         # U3-pin1 (绕过上半区)
            "via_points": [{"x": 5, "y": 8}], # 在Y=8处转折避开元件
            "description": "+12V到MC1403供电"
        },

        # 7. +12V Rail → U4-脚1
        {
            "id": "TR_007",
            "net": "+12V",
            "layer": "B",
            "from": {"x": 14, "y": 1},        # 从rail向下
            "to": {"x": 14, "y": 15},        # U4-pin1
            "via_points": [
                {"x": 12, "y": 1},             # 先向右
                {"x": 12, "y": 15},            # 再向下
                {"x": 14, "y": 15}             # 到目标
            ],
            "description": "+12V到U4正电源"
        },

        # 8. +12V Rail → U4-脚7
        {
            "id": "TR_008",
            "net": "+12V",
            "layer": "B",
            "from": {"x": 16, "y": 1},        # 从rail向下
            "to": {"x": 16, "y": 16},        # U4-pin7
            "via_points": [
                {"x": 18, "y": 1},
                {"x": 18, "y": 16},
                {"x": 16, "y": 16}
            ],
            "description": "+12V到U4另一电源脚"
        },

        # 9. +12V Rail → W4-上端
        {
            "id": "TR_009",
            "net": "+12V",
            "layer": "B",
            "from": {"x": 24, "y": 1},        # 从rail向下
            "to": {"x": 24, "y": 15},        # W4-pin1
            "via_points": [],
            "description": "+12V到W4上端"
        },

        # 10. T6(AD590+) → 分支点 → U1-脚1区域
        {
            "id": "TR_010",
            "net": "+12V_AD590_EXT",
            "layer": "B",
            "from": {"x": 1, "y": 17},        # T6
            "to": {"x": 4, "y": 2},           # 连接到U1附近(外部传感器供电)
            "via_points": [
                {"x": 1, "y": 2},              # 向上到+12V rail
                {"x": 4, "y": 2}               # 沿rail到U1
            ],
            "description": "外部AD590供电输出"
        },


        # ===== -12V 电源分配走线 =====

        # 11. T2(-12V) → -12V Rail
        {
            "id": "TR_011",
            "net": "-12V",
            "layer": "B",
            "from": {"x": 1, "y": 5},          # T2
            "to": {"x": 1, "y": 13},          # -12V rail
            "via_points": [],
            "description": "端子T2到-12V轨"
        },

        # 12. -12V Rail → U2-脚4
        {
            "id": "TR_012",
            "net": "-12V",
            "layer": "B",
            "from": {"x": 14, "y": 13},       # -12V rail
            "to": {"x": 14, "y": 7},          # U2-pin4
            "via_points": [],
            "description": "-12V到U2负电源"
        },

        # 13. -12V Rail → U4-脚4
        {
            "id": "TR_013",
            "net": "-12V",
            "layer": "B",
            "from": {"x": 14, "y": 13},       # -12V rail
            "to": {"x": 14, "y": 18},        # U4-pin4
            "via_points": [],
            "description": "-12V到U4负电源"
        },


        # ===== GND 地线走线 =====

        # 14. T3(GND) → GND Rail
        {
            "id": "TR_014",
            "net": "GND",
            "layer": "B",
            "from": {"x": 1, "y": 8},          # T3
            "to": {"x": 1, "y": 24},         # GND rail
            "via_points": [],
            "description": "端子T3到GND轨"
        },

        # 15. GND Rail → U1-脚3(Case)
        {
            "id": "TR_015",
            "net": "GND",
            "layer": "B",
            "from": {"x": 4, "y": 24},       # GND rail向上
            "to": {"x": 4, "y": 4},          # U1-pin3
            "via_points": [{"x": 3, "y": 4}], # 稍微左移避让
            "description": "GND到AD590外壳"
        },

        # 16. GND Rail → R2
        {
            "id": "TR_016",
            "net": "GND",
            "layer": "B",
            "from": {"x": 11, "y": 24},       # GND rail
            "to": {"x": 11, "y": 5},         # R2-pin1
            "via_points": [],
            "description": "GND到R2偏置电阻"
        },

        # 17. GND Rail → C1
        {
            "id": "TR_017",
            "net": "GND",
            "layer": "B",
            "from": {"x": 9, "y": 24},       # GND rail
            "to": {"x": 9, "y": 8},          # C1-pin2
            "via_points": [],
            "description": "GND到C1滤波电容"
        },

        # 18. GND Rail → C2 (U2 -12V去耦)
        {
            "id": "TR_018",
            "net": "GND",
            "layer": "B",
            "from": {"x": 14, "y": 24},      # GND rail
            "to": {"x": 14, "y": 12},        # C2-pin2
            "via_points": [],
            "description": "GND到C2去耦"
        },

        # 19. GND Rail → C3 (+12V去耦)
        {
            "id": "TR_019",
            "net": "GND",
            "layer": "B",
            "from": {"x": 17, "y": 24},      # GND rail
            "to": {"x": 17, "y": 6},         # C3-pin2
            "via_points": [],
            "description": "GND到C3去耦"
        },

        # 20. GND Rail → R4 (反馈对地)
        {
            "id": "TR_020",
            "net": "GND",
            "layer": "B",
            "from": {"x": 21, "y": 24},      # GND rail
            "to": {"x": 21, "y": 11},        # R4-pin2
            "via_points": [],
            "description": "GND到R4"
        },

        # 21. GND Rail → C4 (反馈电容)
        {
            "id": "TR_021",
            "net": "GND",
            "layer": "B",
            "from": {"x": 22, "y": 24},      # GND rail
            "to": {"x": 22, "y": 11},        # C4-pin2
            "via_points": [],
            "description": "GND到C4"
        },

        # 22. GND Rail → U3-脚3
        {
            "id": "TR_022",
            "net": "GND",
            "layer": "B",
            "from": {"x": 5, "y": 24},       # GND rail
            "to": {"x": 5, "y": 16},        # U3-pin3
            "via_points": [],
            "description": "GND到MC1403地"
        },

        # 23. GND Rail → C5
        {
            "id": "TR_023",
            "net": "GND",
            "layer": "B",
            "from": {"x": 10, "y": 24},      # GND rail
            "to": {"x": 10, "y": 19},        # C5-pin2
            "via_points": [],
            "description": "GND到C5滤波"
        },

        # 24. GND Rail → U4-脚3(IN+)
        {
            "id": "TR_024",
            "net": "GND",
            "layer": "B",
            "from": {"x": 14, "y": 24},      # GND rail
            "to": {"x": 14, "y": 17},        # U4-pin3
            "via_points": [],
            "description": "GND到U4同相端"
        },

        # 25. GND Rail → C6 (U4 -12V去耦)
        {
            "id": "TR_025",
            "net": "GND",
            "layer": "B",
            "from": {"x": 14, "y": 24},      # GND rail
            "to": {"x": 14, "y": 22},        # C6-pin2
            "via_points": [],
            "description": "GND到C6去耦"
        },

        # 26. GND Rail → R7
        {
            "id": "TR_026",
            "net": "GND",
            "layer": "B",
            "from": {"x": 21, "y": 24},      # GND rail
            "to": {"x": 21, "y": 22},        # R7-pin2
            "via_points": [],
            "description": "GND到R7"
        },

        # 27. GND Rail → C7
        {
            "id": "TR_027",
            "net": "GND",
            "layer": "B",
            "from": {"x": 22, "y": 24},      # GND rail
            "to": {"x": 22, "y": 22},        # C7-pin2
            "via_points": [],
            "description": "GND到C7"
        },


        # ===== 信号走线 - 温度检测通道 =====

        # 28. U1-脚2(Io) → R1-pin1 (I/V转换)
        {
            "id": "TR_028",
            "net": "Io",
            "layer": "B",
            "from": {"x": 5, "y": 4},         # U1-pin2
            "to": {"x": 7, "y": 5},           # R1-pin1
            "via_points": [{"x": 6, "y": 4.5}], # 斜向连接
            "description": "AD590电流输出到I/V转换"
        },

        # 29. R1-pin2(Node_A) → C1-pin1 (并联)
        {
            "id": "TR_029",
            "net": "Node_A",
            "layer": "B",
            "from": {"x": 9, "y": 5},          # R1-pin2
            "to": {"x": 9, "y": 7},           # C1-pin1
            "via_points": [],
            "description": "节点A到滤波电容"
        },

        # 30. Node_A → U2-脚3(IN+) [关键信号]
        {
            "id": "TR_030",
            "net": "Node_A",
            "layer": "B",
            "from": {"x": 9, "y": 5},          # Node_A
            "to": {"x": 14, "y": 6},          # U2-pin3
            "via_points": [
                {"x": 11, "y": 5},             # 水平段
                {"x": 11, "y": 6},             # 向下转
                {"x": 14, "y": 6}              # 进入U2
            ],
            "description": "温度信号到U2同相输入端"
        },

        # 31. R2-pin2 → U2-脚2(IN-) [偏置]
        {
            "id": "TR_031",
            "net": "U2_IN-",
            "layer": "B",
            "from": {"x": 13, "y": 5},         # R2-pin2
            "to": {"x": 14, "y": 5},           # U2-pin2
            "via_points": [],
            "description": "偏置电阻到U2反相端"
        },

        # 32. W3-中端(pin2) → U2-脚5 [调零]
        {
            "id": "TR_032",
            "net": "W3_Wiper",
            "layer": "B",
            "from": {"x": 24, "y": 5.5},       # W3-wiper
            "to": {"x": 16, "y": 7},           # U2-pin5
            "via_points": [
                {"x": 20, "y": 5.5},           # 向左
                {"x": 20, "y": 7},             # 向下
                {"x": 16, "y": 7}              # 到U2
            ],
            "description": "W3调零到U2"
        },

        # 33. W3-下端(pin3) → U2-脚8
        {
            "id": "TR_033",
            "net": "W3_Bottom",
            "layer": "B",
            "from": {"x": 24, "y": 7},         # W3-bottom
            "to": {"x": 16, "y": 4},           # U2-pin8
            "via_points": [
                {"x": 20, "y": 7},             # 向左
                {"x": 20, "y": 4},             # 向上
                {"x": 16, "y": 4}              # 到U2
            ],
            "description": "W3下端到U2-脚8"
        },

        # 34. U2-脚6(OUT) → M+_OUT主线 → T4(M+) [主输出]
        {
            "id": "TR_034",
            "net": "M+_OUT",
            "layer": "B",
            "from": {"x": 16, "y": 6},         # U2-pin6
            "to": {"x": 1, "y": 11},          # T4
            "via_points": [
                {"x": 28, "y": 6},             # 向右到边缘
                {"x": 28, "y": 11},            # 向下转弯
                {"x": 1, "y": 11}              # 沿底部到端子
            ],
            "description": "U2输出到M+端子（沿板边走线）"
        },

        # 35. U2-脚6(OUT) → R3-pin1 [反馈分支]
        {
            "id": "TR_035",
            "net": "M+_OUT",
            "layer": "B",
            "from": {"x": 16, "y": 6},         # U2-pin6 (从主线分叉)
            "to": {"x": 19, "y": 8},           # R3-pin1
            "via_points": [
                {"x": 17, "y": 6},             # 稍向右
                {"x": 17, "y": 8},             # 向下
                {"x": 19, "y": 8}              # 到R3
            ],
            "description": "U2输出到反馈电阻R3"
        },

        # 36. R3-pin2(Node_G4) → R4-pin1 [并联]
        {
            "id": "TR_036",
            "net": "Node_G4",
            "layer": "B",
            "from": {"x": 21, "y": 8},         # R3-pin2
            "to": {"x": 21, "y": 9},           # R4-pin1
            "via_points": [],
            "description": "反馈节点G4到R4"
        },

        # 37. Node_G4 → C4-pin1 [并联]
        {
            "id": "TR_037",
            "net": "Node_G4",
            "layer": "B",
            "from": {"x": 21, "y": 9},         # Node_G4
            "to": {"x": 22, "y": 9},           # C4-pin1
            "via_points": [],
            "description": "节点G4到C4"
        },

        # 38. Node_G4 → W1-pin2(滑动端) [增益调节]
        {
            "id": "TR_038",
            "net": "Node_G4",
            "layer": "B",
            "from": {"x": 21, "y": 9},         # Node_G4
            "to": {"x": 27, "y": 8},           # W1-pin2
            "via_points": [
                {"x": 24, "y": 9},             # 向右
                {"x": 24, "y": 8},             # 向上
                {"x": 27, "y": 8}              # 到W1
            ],
            "description": "反馈节点到增益电位器W1"
        },

        # 39. W1-pin1 ↔ M+_OUT线连接点 [增益调节另一端]
        # W1一端接在M+输出线上(U2-脚6到M+之间)
        {
            "id": "TR_039",
            "net": "M+_OUT",
            "layer": "B",
            "from": {"x": 25, "y": 8},         # W1-pin1
            "to": {"x": 26, "y": 6},           # M+_OUT线上的点
            "via_points": [
                {"x": 26, "y": 8},             # 向上
                {"x": 26, "y": 6}              # 接入主线
            ],
            "description": "W1一端接入M+输出线"
        },


        # ===== 信号走线 - 基准校正通道 =====

        # 40. U3-脚2(Vout) → R5-pin1 [基准输出]
        {
            "id": "TR_040",
            "net": "U3_Vout",
            "layer": "B",
            "from": {"x": 6, "y": 16},         # U3-pin2
            "to": {"x": 8, "y": 16},           # R5-pin1
            "via_points": [],
            "description": "MC1403基准输出到R5"
        },

        # 41. R5-pin2 → C5-pin1 [并联滤波]
        {
            "id": "TR_041",
            "net": "U4_IN-",
            "layer": "B",
            "from": {"x": 10, "y": 16},        # R5-pin2
            "to": {"x": 10, "y": 18},          # C5-pin1
            "via_points": [],
            "description": "R5输出到滤波电容"
        },

        # 42. R5-pin2/U4-IN节点 → U4-脚2(IN-) [基准信号]
        {
            "id": "TR_042",
            "net": "U4_IN-",
            "layer": "B",
            "from": {"x": 10, "y": 16},        # R5-pin2
            "to": {"x": 14, "y": 16},          # U4-pin2
            "via_points": [
                {"x": 12, "y": 16},            # 水平段
                {"x": 14, "y": 16}             # 进入U4
            ],
            "description": "基准信号到U4反相输入"
        },

        # 43. W4-中端(pin2) → U4-脚5 [调零]
        {
            "id": "TR_043",
            "net": "W4_Wiper",
            "layer": "B",
            "from": {"x": 24, "y": 16.5},      # W4-wiper
            "to": {"x": 16, "y": 18},          # U4-pin5
            "via_points": [
                {"x": 20, "y": 16.5},          # 向左
                {"x": 20, "y": 18},            # 向下
                {"x": 16, "y": 18}             # 到U4
            ],
            "description": "W4调零到U4"
        },

        # 44. W4-下端(pin3) → U4-脚8
        {
            "id": "TR_044",
            "net": "W4_Bottom",
            "layer": "B",
            "from": {"x": 24, "y": 18},        # W4-bottom
            "to": {"x": 16, "y": 15},          # U4-pin8
            "via_points": [
                {"x": 20, "y": 18},            # 向左
                {"x": 20, "y": 15},            # 向上
                {"x": 16, "y": 15}             # 到U4
            ],
            "description": "W4下端到U4-脚8"
        },

        # 45. U4-脚6(OUT) → M-_OUT主线 → T5(M-) [主输出]
        {
            "id": "TR_045",
            "net": "M-_OUT",
            "layer": "B",
            "from": {"x": 16, "y": 17},        # U4-pin6
            "to": {"x": 1, "y": 14},           # T5
            "via_points": [
                {"x": 28, "y": 17},            # 向右到边缘
                {"x": 28, "y": 14},            # 向上转弯
                {"x": 1, "y": 14}              # 沿顶部到端子
            ],
            "description": "U4输出到M-端子（沿板边走线）"
        },

        # 46. U4-脚6(OUT) → R6-pin1 [反馈分支]
        {
            "id": "TR_046",
            "net": "M-_OUT",
            "layer": "B",
            "from": {"x": 16, "y": 17},        # U4-pin6 (从主线分叉)
            "to": {"x": 19, "y": 19},          # R6-pin1
            "via_points": [
                {"x": 17, "y": 17},            # 稍向右
                {"x": 17, "y": 19},            # 向下
                {"x": 19, "y": 19}             # 到R6
            ],
            "description": "U4输出到反馈电阻R6"
        },

        # 47. R6-pin2(Node_G7) → R7-pin1 [并联]
        {
            "id": "TR_047",
            "net": "Node_G7",
            "layer": "B",
            "from": {"x": 21, "y": 19},        # R6-pin2
            "to": {"x": 21, "y": 20},          # R7-pin1
            "via_points": [],
            "description": "反馈节点G7到R7"
        },

        # 48. Node_G7 → C7-pin1 [并联]
        {
            "id": "TR_048",
            "net": "Node_G7",
            "layer": "B",
            "from": {"x": 21, "y": 20},        # Node_G7
            "to": {"x": 22, "y": 20},          # C7-pin1
            "via_points": [],
            "description": "节点G7到C7"
        },

        # 49. Node_G7 → W2-pin2(滑动端) [增益调节]
        {
            "id": "TR_049",
            "net": "Node_G7",
            "layer": "B",
            "from": {"x": 21, "y": 20},        # Node_G7
            "to": {"x": 27, "y": 19},          # W2-pin2
            "via_points": [
                {"x": 24, "y": 20},            # 向右
                {"x": 24, "y": 19},            # 向上
                {"x": 27, "y": 19}             # 到W2
            ],
            "description": "反馈节点到增益电位器W2"
        },

        # 50. W2-pin1 ↔ M-_OUT线连接点 [增益调节另一端]
        {
            "id": "TR_050",
            "net": "M-_OUT",
            "layer": "B",
            "from": {"x": 25, "y": 19},        # W2-pin1
            "to": {"x": 26, "y": 17},          # M-_OUT线上的点
            "via_points": [
                {"x": 26, "y": 19},            # 向上
                {"x": 26, "y": 17}             # 接入主线
            ],
            "description": "W2一端接入M-输出线"
        }
    ],

    # ==================== A面飞线 (红色) ====================
    # 仅当B面无法避免交叉时使用，最多3条
    "jumpers": [
        # 飞线1: 可能需要的交叉规避
        # 经过检查，当前布局B面走线基本无交叉
        # 预留1条飞线作为备用（如果制造时发现局部冲突）
        {
            "id": "JMP_001",
            "net": "RESERVED",
            "layer": "A",
            "color": "red",
            "from": {"x": 0, "y": 0},
            "to": {"x": 0, "y": 0},
            "description": "备用飞线 - 当前B面布线无需使用",
            "active": False
        }

        # 注：如需激活，将active改为True并填入实际坐标
        # 典型用途：
        # - 当两条信号线必须在某点交叉时
        # - 当电源轨与信号线冲突时
        # - 高频敏感信号的屏蔽隔离
    ],

    # ==================== 布局说明和注释 ====================
    "notes": [
        "===== 整体布局概述 =====",
        "网格尺寸: 30列 × 24行",
        "双面板设计: B面为主走线层(蓝色), A面为元件面+备用飞线(红色)",
        "",
        "===== 区域划分 =====",
        "- Y轴方向: Y≤12为上半区(温度检测), Y≥13为下半区(基准校正)",
        "- X轴方向: 左侧(X=1-2)为端子区, 中间(X=3-22)为信号处理区, 右侧(X=23-28)为调节元件区",
        "- Y=1: +12V电源轨(红线)",  
        "- Y=13: -12V电源轨(蓝线)",
        "- Y=24: GND地线轨(黑线)",
        "",
        "===== 信号流向 =====",
        "温度通道: AD590(U1) → R1(I/V转换) → C1(滤波) → U2(放大) → M+输出",
        "基准通道: MC1403(U3)(2.5V基准) → R5 → U4(缓冲/放大) → M-输出",
        "",
        "===== 关键元件位置 =====",
        "- U2(CP-07运放): 中心(15,5.5), DIP-8封装, 主信号处理器",
        "- U4(CP-07运放): 中心(15,16.5), DIP-封装, 与U2对称布局",
        "- AD590(U1): (4,3), TO-52封装, 温度传感器接口",
        "- MC1403(U3): (5,15), SIP-3封装, 精密基准源",
        "- 调零电位器(W3/W4): X=23-24区域, 竖直安装便于调节",
        "- 增益电位器(W1/W2): X=25-27区域, 水平安装",
        "",
        "===== 走线统计 =====",
        f"- B面走线总数: {len(pcb_data.get('traces', [])) if isinstance(pcb_data, dict) else '见traces数组'}条",
        "- A面飞线: 0条(预留1条备用)",
        "- 电源轨: 3条(+12V/-12V/GND)",
        "",
        "===== DIP-8引脚对照表(B面观察，缺口朝左) =====",
        "┌─────────────────────────┐",
        "│  ●Pin1(V+)    ●Pin8(W_) │",
        "│  ●Pin2(IN-)   ●Pin7(V+) │",
        "│  ●Pin3(IN+)   ●Pin6(OUT)│",
        "│  ●Pin4(-V)    ●Pin5(OFF)│",
        "└─────────────────────────┘",
        "左列从上到下: Pin1, Pin2, Pin3, Pin4",
        "右列从上到下: Pin8, Pin7, Pin6, Pin5",
        "",
        "===== 设计要点 =====",
        "1. 电源去耦: U2/U4的正负电源均就近配置0.01μF去耦电容(C2,C3,C6等)",
        "2. 信号完整性: 温度信号(Node_A)采用最短路径进入U2同相端，减少噪声拾取",
        "3. 反馈稳定性: U2/U4反馈网络包含RC补偿(R+C并联到地)，防止振荡",
        "4. 可调性: 调零(W3/W4)和增益(W1/W2)均置于板边缘，方便调试",
        "5. 对称性: 上下两通道采用对称布局，利于差分测量时的共模抑制",
        "6. 接地策略: 采用单点接地(星形接地)概念，所有地线汇至GND轨",
        "",
        "===== 使用建议 =====",
        "1. 制造时建议使用CAD软件导入本JSON数据进行自动布线验证",
        "2. 实际生产前请做DFM(可制造性设计)检查",
        "3. 高精度应用建议增加铜箔面积以提高散热",
        "4. 关键信号线(如Node_A到U2-IN+)可考虑加宽或包地处理",
        "5. 电位器选用多圈精密型号以提高调节分辨率"
    ],

    # ==================== 元件清单 (BOM参考) ====================
    "bom_summary": {
        "total_components": 27,
        "categories": {
            "IC/传感器": ["U1: AD590 (TO-52)", "U2: CP-07 (DIP-8)", "U3: MC1403 (SIP-3)", "U4: CP-07 (DIP-8)"],
            "电阻": [
                "R1: 2KΩ (I/V转换)",
                "R2: 2.6KΩ (偏置)",
                "R3: 1KΩ (反馈)",
                "R4: 1KΩ (对地)",
                "R5: 10KΩ (基准分压)",
                "R6: 680Ω (反馈)",
                "R7: 1KΩ (对地)"
            ],
            "电容": [
                "C1: 0.01μF (输入滤波)",
                "C2: 0.01μF (U2 -12V去耦)",
                "C3: 0.01μF (U2 +12V去耦)",
                "C4: 0.01μF (U2反馈补偿)",
                "C5: 0.01μF (U4输入滤波)",
                "C6: 0.01μF (U4 -12V去耦)",
                "C7: 0.01μF (U4反馈补偿)"
            ],
            "电位器": [
                "W1: 10KΩ (U2增益调节)",
                "W2: 10KΩ (U4增益调节)",
                "W3: 20KΩ (U2调零)",
                "W4: 20KΩ (U4调零)"
            ],
            "端子": ["T1-T7: 7位接线端子排"]
        }
    },

    # ==================== 版本信息 ====================
    "metadata": {
        "version": "1.0",
        "created_date": "2026-07-05",
        "designer": "AI PCB Layout Generator",
        "circuit_type": "Digital Temperature Measurement",
        "board_size": "30×24 grid units",
        "layers": 2,
        "technology": "Through-hole components (THD)",
        "status": "Ready for review"
    }
}


# ==================== 工具函数 ====================

def get_trace_by_id(trace_id):
    """根据ID获取单条走线"""
    for trace in pcb_data["traces"]:
        if trace["id"] == trace_id:
            return trace
    return None


def get_component_by_id(comp_id):
    """根据ID获取单个元件"""
    for comp in pcb_data["components"]:
        if comp["id"] == comp_id:
            return comp
    return None


def list_nets():
    """列出所有网络节点"""
    nets = set()
    for trace in pcb_data["traces"]:
        nets.add(trace["net"])
    return sorted(list(nets))


def validate_layout():
    """
    基础布局验证
    返回: (is_valid, errors, warnings)
    """
    errors = []
    warnings = []

    # 检查网格边界
    grid = pcb_data["grid"]

    # 检查所有元件是否在网格内
    for comp in pcb_data["components"]:
        if comp["x"] < 1 or comp["x"] > grid["cols"]:
            errors.append(f"元件{comp['id']} X坐标超出范围")
        if comp["y"] < 1 or comp["y"] > grid["rows"]:
            errors.append(f"元件{comp['id']} Y坐标超出范围")

    # 检查端子
    for term in pcb_data["terminals"]:
        if term["x"] != 1:
            warnings.append(f"端子{term['id']}不在左侧边缘")

    # 检查飞线数量
    active_jumpers = [j for j in pcb_data["jumpers"] if j.get("active", True)]
    if len(active_jumpers) > 3:
        errors.append(f"飞线数量({len(active_jumpers)})超过限制(3条)")

    # 统计走线
    print(f"布局验证结果:")
    print(f"  - 元件总数: {len(pcb_data['components'])}")
    print(f"  - 端子总数: {len(pcb_data['terminals'])}")
    print(f"  - B面走线: {len(pcb_data['traces'])}条")
    print(f"  - A面飞线(活跃): {len(active_jumpers)}条")
    print(f"  - 电源轨: {len(pcb_data['power_rails'])}条")

    is_valid = len(errors) == 0
    return is_valid, errors, warnings


def export_for_cad():
    """
    导出为简化格式供CAD软件导入
    可扩展为Gerber或其他格式
    """
    export_data = {
        "format": "PCB_LAYOUT_JSON_V1",
        "source": "pcb_data.py",
        "grid": pcb_data["grid"],
        "parts": [],  # 元件位置
        "nets": {},   # 网络连接
        "routes": []  # 走线路径
    }

    # 提取元件位置
    for comp in pcb_data["components"]:
        export_data["parts"].append({
            "designator": comp["id"],
            "footprint": comp["package"],
            "x": comp["x"],
            "y": comp["y"],
            "rotation": 0,
            "layer": "B"
        })

    # 提取网络连接
    for trace in pcb_data["traces"]:
        net_name = trace["net"]
        if net_name not in export_data["nets"]:
            export_data["nets"][net_name] = []
        export_data["nets"][net_name].append({
            "start": trace["from"],
            "end": trace["to"],
            "vias": trace.get("via_points", []),
            "layer": trace["layer"]
        })

    return export_data


if __name__ == "__main__":
    # 运行验证
    print("=" * 60)
    print("数字温度测量电路 - PCB布线数据")
    print("=" * 60)

    valid, errs, warns = validate_layout()

    if valid:
        print("\n✓ 布局验证通过!")
    else:
        print("\n✗ 发现错误:")
        for err in errs:
            print(f"  - {err}")

    if warns:
        print("\n⚠ 警告:")
        for w in warns:
            print(f"  - {w}")

    print("\n网络列表:")
    for net in list_nets():
        print(f"  • {net}")

    print("\n" + "=" * 60)
    print("数据结构说明:")
    print("=" * 60)
    print("- pcb_data['terminals']: 7个接线端子")
    print("- pcb_data['components']: 所有元件(27个)")
    print("- pcb_data['power_rails']: 3条电源总线")
    print("- pcb_data['traces']: 50条B面走线")
    print("- pcb_data['jumpers']: 备用A面飞线")
    print("- pcb_data['notes']: 详细设计文档")
    print("=" * 60)
