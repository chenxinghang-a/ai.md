from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

wb = Workbook()

# ===== Sheet 1: 元件清单 BOM =====
ws1 = wb.active
ws1.title = "元件清单"

header_font = Font(bold=True, size=11)
header_fill = PatternFill("solid", fgColor="4472C4")
header_font_white = Font(bold=True, size=11, color="FFFFFF")
center = Alignment(horizontal="center", vertical="center")
thin_border = Border(
    left=Side(style='thin'), right=Side(style='thin'),
    top=Side(style='thin'), bottom=Side(style='thin')
)
jumper_fill = PatternFill("solid", fgColor="FFFF00")  # 黄色标记飞线
power_fill = PatternFill("solid", fgColor="E2EFDA")   # 浅绿-电源
signal_fill = PatternFill("solid", fgColor="DDEBF7")    # 浅蓝-信号

bom_headers = ["序号", "位号", "型号/参数", "数量", "封装/备注"]
for col, h in enumerate(bom_headers, 1):
    cell = ws1.cell(row=1, column=col, value=h)
    cell.font = header_font_white
    cell.fill = header_fill
    cell.alignment = center
    cell.border = thin_border

bom_data = [
    [1, "U2", "CP-07 运放", 1, "DIP-8"],
    [2, "U4", "CP-07 运放", 1, "DIP-8"],
    [3, "U3", "MC1403 基准源", 1, "DIP-3"],
    [4, "U1", "电感/变压器", 1, "插件"],
    [5, "R1", "2K Ω", 1, "1/4W"],
    [6, "R2", "2.6K Ω", 1, "1/4W"],
    [7, "R3", "1K Ω", 1, "1/4W"],
    [8, "R4", "1K Ω", 1, "1/4W"],
    [9, "R5", "10K Ω", 1, "1/4W"],
    [10, "R6", "680 Ω", 1, "1/4W"],
    [11, "R7", "1K Ω", 1, "1/4W"],
    [12, "C1", "0.01μF", 1, "瓷片/独石"],
    [13, "C2", "0.01μF", 1, "瓷片/独石"],
    [14, "C3", "0.01μF", 1, "瓷片/独石"],
    [15, "C4", "0.01μF", 1, "瓷片/独石"],
    [16, "C5", "0.01μF", 1, "瓷片/独石"],
    [17, "C6", "0.01μF", 1, "瓷片/独石"],
    [18, "C7", "0.01μF", 1, "瓷片/独石"],
    [19, "W1", "电位器", 1, "侧调"],
    [20, "W2", "电位器", 1, "侧调"],
    [21, "W3", "20K 电位器", 1, "侧调"],
    [22, "W4", "20K 电位器", 1, "侧调"],
]

for r, row_data in enumerate(bom_data, 2):
    for c, val in enumerate(row_data, 1):
        cell = ws1.cell(row=r, column=c, value=val)
        cell.alignment = center
        cell.border = thin_border

for col in range(1, 6):
    ws1.column_dimensions[get_column_letter(col)].width = 16


# ===== Sheet 2: 布线总表 (核心) =====
ws2 = wb.create_sheet("布线总表")

wire_headers = ["序号", "起始端(从)", "终止端(到)", "导线类型", "走线说明", "备注"]
for col, h in enumerate(wire_headers, 1):
    cell = ws2.cell(row=1, column=col, value=h)
    cell.font = header_font_white
    cell.fill = header_fill
    cell.alignment = center
    cell.border = thin_border

# 所有连线数据 — 根据电路图逐条分析
wire_data = [
    # === 电源部分 ===
    [1, "+12V电源输入", "U1 上端(Pin1)", "电源总线", "沿板边走线", ""],
    [2, "+12V电源输入", "U2 Pin1(+VCC)", "电源总线", "沿板边走线", ""],
    [3, "+12V电源输入", "U2 Pin7(+VCC)", "电源总线", "沿板边走线", ""],
    [4, "+12V电源输入", "U4 Pin1(+VCC)", "电源总线", "沿板边走线", ""],
    [5, "+12V电源输入", "U4 Pin7(+VCC)", "电源总线", "沿板边走线", ""],
    [6, "+12V电源输入", "U3 Pin1(VIN)", "电源总线", "沿板边走线", ""],
    [7, "+12V电源输入", "W3 左端(固定端)", "电源总线", "沿板边走线", ""],
    [8, "+12V电源输入", "W4 左端(固定端)", "电源总线", "沿板边走线", ""],

    [9, "-12V电源输入", "U2 Pin4(-VEE)", "电源总线", "沿板边走线", ""],
    [10, "-12V电源输入", "U4 Pin4(-VEE)", "电源总线", "沿板边走线", ""],

    [11, "GND", "R1 下端", "地线", "就近接地", ""],
    [12, "GND", "C1 下端", "地线", "就近接地", ""],
    [13, "GND", "C2 下端", "地线", "就近接地", ""],
    [14, "GND", "C3 下端", "地线", "就近接地", ""],
    [15, "GND", "R2 左端", "地线", "就近接地", ""],
    [16, "GND", "R4 下端", "地线", "就近接地", ""],
    [17, "GND", "U3 Pin3(GND)", "地线", "就近接地", ""],
    [18, "GND", "R5 下端", "地线", "就近接地", ""],
    [19, "GND", "C5 下端", "地线", "就近接地", ""],
    [20, "GND", "C6 下端", "地线", "就近接地", ""],
    [21, "GND", "R7 下端", "地线", "就近接地", ""],

    # === U2 运放周边 (上半部) ===
    [22, "U1 下端(Pin2)", "C3 上端 / R1-C1节点", "信号线", "元件引脚直连或短跨接", "U1耦合到RC网络"],
    [23, "R1 上端 / C1右", "U2 Pin3(同相输入)", "信号线", "就近连接", ""],
    [24, "C1 左端 / R1上端节点", "U2 Pin2(反相输入)", "信号线", "就近连接", ""],
    [25, "R2 右端", "U2 Pin2 / C1左端节点", "信号线", "就近连接", "R2反馈电阻"],
    [26, "C3 上端", "U2 Pin3 / R1下端节点", "信号线", "就近连接", ""],
    [27, "C2 上端", "U2 Pin4(-VEE)", "信号线", "就近连接", "去耦电容"],
    [28, "U2 Pin8", "W3 滑片(中端)", "信号线", "就近连接", "偏置调节"],

    # === U2 输出及反馈网络 (右侧) ===
    [29, "U2 Pin6(输出)", "M+ 输出端子", "信号线", "引出到接线端子", "通道A输出"],
    [30, "M+ 输出端子", "W1 上端(固定端1)", "信号线", "就近连接", ""],
    [31, "W1 滑片(中端)", "R3 左端", "信号线", "就近连接", ""],
    [32, "R3 右端", "G4 节点", "信号线", "就近连接", ""],
    [33, "G4 节点", "R4 上端", "信号线", "就近连接", ""],
    [34, "G4 节点", "C4 右端", "信号线", "就近连接", ""],
    [35, "C4 左端", "U2 Pin2 反相输入侧", "信号线", "就近连接", "反馈电容，⚠️可能需飞线①"],
    [36, "W1 下端(固定端2)", "G4 节点", "信号线", "就近连接", "电位器另一端"],

    # === U3 MC1403 基准源 ===
    [37, "U3 Pin2(OUT)", "R5 左端", "信号线", "就近连接", "基准电压输出"],
    
    # === U4 运放周边 (下半部) ===
    [38, "R5 右端", "U4 Pin2(反相输入)", "信号线", "就近连接", ""],
    [39, "C5 上端", "U4 Pin3(同相输入)", "信号线", "就近连接", ""],
    [40, "C6 上端", "U4 Pin4(-VEE)", "信号线", "就近连接", "去耦电容"],
    [41, "U4 Pin8", "W4 滑片(中端)", "信号线", "就近连接", "偏置调节"],

    # === U4 输出及反馈网络 (右下侧) ===
    [42, "U4 Pin6(输出)", "M- 输出端子", "信号线", "引出到接线端子", "通道B输出"],
    [43, "M- 输出端子", "W2 上端(固定端1)", "信号线", "就近连接", ""],
    [44, "W2 滑片(中端)", "R6 左端", "信号线", "就近连接", ""],
    [45, "R6 右端", "H4 节点", "信号线", "就近连接", ""],
    [46, "H4 节点", "R7 上端", "信号线", "就近连接", ""],
    [47, "H4 节点", "C7 右端", "信号线", "就近连接", ""],
    [48, "C7 左端", "U4 Pin2 反相输入侧", "信号线", "就近连接", "反馈电容，⚠️可能需飞线②"],
    [49, "W2 下端(固定端2)", "H4 节点", "信号线", "就近连接", "电位器另一端"],
    
    # === 飞线标注 (最多3条) ===
    [50, "C4 左端", "U2 Pin2 区域", "🔴 飞线①", "跨区跳接", "唯一飞线：反馈回路跨接"],
    [51, "C7 左端", "U4 Pin2 区域", "🔴 飞线②", "跨区跳接", "唯一飞线：反馈回路跨接"],
    [52, "U2 Pin6→M+", "接线柱(输出A)", "🔴 飞线③", "引出到板边端子", "输出引线(若端子在远处)"],
]

for r, row_data in enumerate(wire_data, 2):
    for c, val in enumerate(row_data, 1):
        cell = ws2.cell(row=r, column=c, value=val)
        cell.alignment = center
        cell.border = thin_border
        # 根据导线类型着色
        if "电源" in str(row_data[3]) or "地线" in str(row_data[3]):
            cell.fill = power_fill
        elif "飞线" in str(val) or ("飞线" in str(row_data[3])):
            cell.fill = jumper_fill
        elif "信号" in str(row_data[3]):
            cell.fill = signal_fill

ws2_col_widths = [6, 28, 28, 12, 22, 24]
for col, w in enumerate(ws2_col_widths, 1):
    ws2.column_dimensions[get_column_letter(col)].width = w


# ===== Sheet 3: IC引脚详细接线表 =====
ws3 = wb.create_sheet("IC引脚接线表")

ic_headers = ["IC位号", "引脚编号", "引脚功能", "连接去向", "导线/飞线", "备注"]
for col, h in enumerate(ic_headers, 1):
    cell = ws3.cell(row=1, column=col, value=h)
    cell.font = header_font_white
    cell.fill = header_fill
    cell.alignment = center
    cell.border = thin_border

ic_data = [
    # U2 CP-07
    ["U2(CP-07)", "1", "+VCC", "+12V 电源轨", "电源总线", "运放正电源"],
    ["U2(CP-07)", "2", "IN-", "C1左/R2右/C4左(经G4反馈)", "信号线+飞线①", "反相输入"],
    ["U2(CP-07)", "3", "IN+", "R1上/C1右/C3上/U1下端", "信号线", "同相输入(RC网络)"],
    ["U2(CP-07)", "4", "-VEE", "-12V 电源轨", "电源总线", "运放负电源"],
    ["U2(CP-07)", "5", "NC", "悬空", "-", "空脚"],
    ["U2(CP-07)", "6", "OUT", "M+输出/W1上端", "信号线", "通道A输出"],
    ["U2(CP-07)", "7", "+VCC", "+12V 电源轨", "电源总线", "运放正电源"],
    ["U2(CP-07)", "8", "OFFSET NULL", "W3滑片(中端)", "信号线", "调零/偏置"],
    # U3 MC1403
    ["U3(MC1403)", "1", "VIN", "+12V 电源轨", "电源总线", "基准源供电"],
    ["U3(MC1403)", "2", "OUT", "R5左端(10K)", "信号线", "基准输出≈2.5V"],
    ["U3(MC1403)", "3", "GND", "GND 地线", "地线", "地"],
    # U4 CP-07
    ["U4(CP-07)", "1", "+VCC", "+12V 电源轨", "电源总线", "运放正电源"],
    ["U4(CP-07)", "2", "IN-", "R5右/C7左(经H4反馈)", "信号线+飞线②", "反相输入"],
    ["U4(CP-07)", "3", "IN+", "C5上端", "信号线", "同相输入"],
    ["U4(CP-07)", "4", "-VEE", "-12V 电源轨", "电源总线", "运放负电源"],
    ["U4(CP-07)", "5", "NC", "悬空", "-", "空脚"],
    ["U4(CP-07)", "6", "OUT", "M-输出/W2上端", "信号线", "通道B输出"],
    ["U4(CP-07)", "7", "+VCC", "+12V 电源轨", "电源总线", "运放正电源"],
    ["U4(CP-07)", "8", "OFFSET NULL", "W4滑片(中端)", "信号线", "调零/偏置"],
]

for r, row_data in enumerate(ic_data, 2):
    for c, val in enumerate(row_data, 1):
        cell = ws3.cell(row=r, column=c, value=val)
        cell.alignment = Alignment(horizontal="left" if c>2 else "center", vertical="center")
        cell.border = thin_border
        if "飞线" in str(val):
            cell.fill = jumper_fill
        elif "电源" in str(row_data[4]) or row_data[4] == "地线":
            cell.fill = power_fill
        else:
            cell.fill = signal_fill

for col, w in enumerate([14, 8, 14, 30, 14, 18], 1):
    ws3.column_dimensions[get_column_letter(col)].width = w


# ===== Sheet 4: 飞线汇总 (≤3条) =====
ws4 = wb.create_sheet("飞线汇总(共3条)")

flyer_headers = ["飞线编号", "起点", "终点", "长度估计", "原因分析", "优化建议"]
for col, h in enumerate(flyer_headers, 1):
    cell = ws4.cell(row=1, column=col, value=h)
    cell.font = header_font_white
    cell.fill = PatternFill("solid", fgColor="FF0000")
    cell.alignment = center
    cell.border = thin_border

flyer_data = [
    ["飞线①", "C4 左端", "U2 Pin2 反相输入区域", "~3-5cm", 
     "C4位于右侧反馈网络区，U2-Pin2在左侧输入区，距离较远无法直连",
     "布局时尽量将C4靠近U2放置；若仍需跳接则用短飞线"],
    ["飞线②", "C7 左端", "U4 Pin2 反相输入区域", "~3-5cm",
     "同理：C7在右下方反馈区，U4-Pin2在左下方输入区",
     "布局时尽量将C7靠近U4放置；若仍需跳接则用短飞线"],
    ["飞线③", "U2-Pin6/M+输出", "板边接线端子", "~5-8cm(可选)",
     "输出端子通常在板边，与IC有一定距离",
     "若端子紧靠IC可免此飞线；否则算第3条飞线"],
]

for r, row_data in enumerate(flyer_data, 2):
    for c, val in enumerate(row_data, 1):
        cell = ws4.cell(row=r, column=c, value=val)
        cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        cell.border = thin_border
        cell.fill = jumper_fill

for col, w in enumerate([10, 24, 26, 12, 38, 34], 1):
    ws4.column_dimensions[get_column_letter(col)].width = w
for row in range(2, 5):
    ws4.row_dimensions[row].height = 45

# 汇总行
summary_row = 6
ws4.cell(row=summary_row, column=1, value="汇总").font = Font(bold=True)
ws4.cell(row=summary_row, column=2, value="飞线总数：3条（符合≤3条要求）").font = Font(bold=True, color="008000")
ws4.merge_cells(start_row=summary_row, start_column=2, end_row=summary_row, end_column=5)


# ===== Sheet 5: 布局建议 =====
ws5 = wb.create_sheet("布局建议")

layout_headers = ["区域", "推荐摆放元件", "布局要点"]
for col, h in enumerate(layout_headers, 1):
    cell = ws5.cell(row=1, column=col, value=h)
    cell.font = header_font_white
    cell.fill = header_fill
    cell.alignment = center
    cell.border = thin_border

layout_data = [
    ["左侧电源区", "+12V/-12V/GND 接线端子、U1", "电源从左侧进入，沿上下边缘布电源轨"],
    ["左上 IC区", "U2(CP-07)、C1、C2、C3、R1、R2", "U2居中，周围紧凑排RC网络元件"],
    ["右上 反馈区(A)", "W1、R3、R4、C4、M+端子", "U2右侧放反馈网络和输出端子"],
    ["左下 IC区", "U4(CP-07)、C5、C6、R5", "U4居中，U3(MC1403)放在U4左上方"],
    ["右下 反馈区(B)", "W2、R6、R7、C7、M-端子", "U4右侧放反馈网络和输出端子"],
    ["中部偏右 电位器区", "W3(20K)、W4(20K)", "两个20K电位器并排放置，便于调节"],
    ["板边缘", "M+/M-输出端子、电源输入座", "统一在右侧或下侧边缘布置端子"],
]

for r, row_data in enumerate(layout_data, 2):
    for c, val in enumerate(row_data, 1):
        cell = ws5.cell(row=r, column=c, value=val)
        cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        cell.border = thin_border

for col, w in enumerate([16, 36, 56], 1):
    ws5.column_dimensions[get_column_letter(col)].width = w
for row in range(2, 9):
    ws5.row_dimensions[row].height = 35


out_path = r"C:\Users\cxx\WorkBuddy\2026-07-05-22-13-37\布线表.xlsx"
wb.save(out_path)
print(f"Done! Saved to {out_path}")
