# -*- coding: utf-8 -*-
"""
30x24 grid PCB layout in Excel
- Blue cells = B-side traces
- Red cells = A-side jumper wires
- Component cells = bordered boxes with labels
- 7 terminals on left edge
"""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

wb = Workbook()
ws = wb.active
ws.title = "PCB-Layout-30x24"

# ---- Grid constants ----
COLS = 30
ROWS = 24

# ---- Colors ----
BLUE   = "4472C4"   # B面走线
RED    = "FF0000"   # A面飞线
GREEN  = "00B050"   # 电源+
DGREEN = "006100"   # 电源-
BLACK  = "000000"   # GND
IC_BG  = "FFF2CC"   # IC底色
R_BG   = "E2EFDA"   # 电阻底色
C_BG   = "D9E1F2"   # 电容底色
W_BG   = "FCE4D6"   # 电位器底色
TERM_BG= "D6DCE4"   # 端子底色
LABEL_BG="808080"   # 标签底色

# ---- Fonts ----
f_title = Font(bold=True, size=14, color="FFFFFF")
f_hdr   = Font(bold=True, size=8, color="FFFFFF")
f_small = Font(size=7)
f_tiny  = Font(size=6)
f_comp  = Font(bold=True, size=7)
f_pin   = Font(size=5, color="666666")

# ---- Borders ----
thin = Side(style='thin', color='808080')
med  = Side(style='medium', color='000000')
b_thin = Border(left=thin, right=thin, top=thin, bottom=thin)
b_med  = Border(left=med, right=med, top=med, bottom=med)

center = Alignment(horizontal='center', vertical='center', wrap_text=True)

# ---- Helper functions ----
def fill(color):
    return PatternFill("solid", fgColor=color)

def set_cell(ws, x, y, value="", bg=None, font=None, border=b_thin):
    """Set cell at (column=x, row=y), skip if merged"""
    c = ws.cell(row=y, column=x)
    # Check if cell is in a merged range
    from openpyxl.cell.cell import MergedCell
    if isinstance(c, MergedCell):
        return c
    c.value = value
    c.alignment = center
    if bg: c.fill = fill(bg)
    if font: c.font = font
    else: c.font = f_small
    if border: c.border = border
    return c

def draw_trace_h(ws, x1, x2, y, color=BLUE):
    """Draw horizontal trace from x1 to x2 at row y"""
    for x in range(x1, x2+1):
        set_cell(ws, x, y, "", bg=color, font=f_small, border=b_thin)

def draw_trace_v(ws, x, y1, y2, color=BLUE):
    """Draw vertical trace from y1 to y2 at column x"""
    for y in range(y1, y2+1):
        set_cell(ws, x, y, "", bg=color, font=f_small, border=b_thin)

def draw_comp(ws, x, y, w, h, label, sub="", bg=IC_BG):
    """Draw component box at (x,y) with size w×h"""
    ws.merge_cells(start_row=y, start_column=x, end_row=y+h-1, end_column=x+w-1)
    c = ws.cell(row=y, column=x)
    c.value = f"{label}\n{sub}" if sub else label
    c.font = f_comp
    c.fill = fill(bg)
    c.alignment = center
    c.border = b_med
    # Apply border to all cells in merge
    for r in range(y, y+h):
        for col in range(x, x+w):
            cc = ws.cell(row=r, column=col)
            cc.border = b_med
            if bg: cc.fill = fill(bg)

def draw_ic_dip8(ws, x, y, name, pins):
    """
    Draw DIP-8 IC at position (x,y), occupying 3 cols x 5 rows
    pins = list of 8 tuples: (pin_num, pin_name, connection_text)
    Pin layout (B面看, 缺口朝左, 顺时针):
      1  8
      2  7
      3  6
      4  5
    """
    w, h = 4, 5
    # IC body
    ws.merge_cells(start_row=y, start_column=x, end_row=y+h-1, end_column=x+w-1)
    c = ws.cell(row=y, column=x)
    c.value = name
    c.font = Font(bold=True, size=9)
    c.fill = fill(IC_BG)
    c.alignment = center
    c.border = b_med
    for r in range(y, y+h):
        for col in range(x, x+w):
            cc = ws.cell(row=r, column=col)
            cc.border = b_med
            cc.fill = fill(IC_BG)
    # Pin labels - left side (1,2,3,4) and right side (8,7,6,5)
    pin_order = [(1,'L'),(2,'L'),(3,'L'),(4,'L'),(5,'R'),(6,'R'),(7,'R'),(8,'R')]
    for idx, (pnum, side) in enumerate(pin_order):
        if side == 'L':
            py = y + idx
            # Pin number at left edge
            set_cell(ws, x-1, py, str(pnum), bg=LABEL_BG, font=Font(size=6,bold=True,color="FFFFFF"))
        else:
            py = y + (8 - pnum)
            set_cell(ws, x+w, py, str(pnum), bg=LABEL_BG, font=Font(size=6,bold=True,color="FFFFFF"))

# ============================================================
# Set column widths and row heights for square cells
# ============================================================
for col in range(1, COLS+2):
    ws.column_dimensions[get_column_letter(col)].width = 3.0
for row in range(1, ROWS+2):
    ws.row_dimensions[row].height = 18

# ============================================================
# Title row
# ============================================================
ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=COLS)
t = ws.cell(row=1, column=1, value="数字温度计 PCB布线图  30x24  |  Blue=B面走线  Red=A面飞线  |  飞线<=3条")
t.font = f_title
t.fill = fill("2F5496")
t.alignment = center

# Column headers (X coordinates)
for x in range(1, COLS+1):
    set_cell(ws, x, 2, str(x), bg="404040", font=f_hdr)

# Row headers (Y coordinates) in column 31
for y in range(3, ROWS+3):
    set_cell(ws, COLS+1, y, str(y-2), bg="404040", font=f_hdr)

# ============================================================
# Power rails (Blue thick lines)
# ============================================================
# +12V rail at Y=3 (top)
draw_trace_h(ws, 1, COLS, 3, BLUE)
set_cell(ws, 1, 3, "+12V", bg=GREEN, font=Font(bold=True,size=7,color="FFFFFF"))

# -12V rail at Y=13 (middle) - single side supply for lower half
draw_trace_h(ws, 1, COLS, 13, BLUE)
set_cell(ws, 1, 13, "-12V", bg=DGREEN, font=Font(bold=True,size=7,color="FFFFFF"))

# GND rail at Y=24 (bottom)
draw_trace_h(ws, 1, COLS, 24, BLACK)
set_cell(ws, 1, 24, "GND", bg=BLACK, font=Font(bold=True,size=7,color="FFFFFF"))

# ============================================================
# Left edge: 7 terminals (X=1, Y=4~10)
# ============================================================
terminals = [
    (4, "+12V", GREEN),
    (5, "-12V", DGREEN),
    (6, "GND", BLACK),
    (7, "M+", "C00000"),
    (8, "M-", "C00000"),
    (9, "AD590\nV+", GREEN),
    (10, "备用", "808080"),
]
for y, label, color in terminals:
    set_cell(ws, 1, y, label, bg=color, font=Font(bold=True,size=6,color="FFFFFF"))

# ============================================================
# Component placement
# Layout: Upper half = temperature channel (Y=4~12)
#         Lower half = reference channel (Y=14~23)
# ============================================================

# ---- U1: AD590 temperature sensor (3-pin) ----
draw_comp(ws, 3, 4, 2, 2, "U1", "AD590", IC_BG)
set_cell(ws, 2, 4, "1\nV+", bg=LABEL_BG, font=Font(size=5,bold=True,color="FFFFFF"))
set_cell(ws, 5, 4, "2\nI0", bg=LABEL_BG, font=Font(size=5,bold=True,color="FFFFFF"))
set_cell(ws, 5, 5, "3\nNC", bg=LABEL_BG, font=Font(size=5,bold=True,color="FFFFFF"))

# +12V trace: rail(3) -> down to U1-Pin1
draw_trace_v(ws, 3, 3, 4, BLUE)

# ---- R1: 2K (current-to-voltage converter) ----
draw_comp(ws, 6, 5, 2, 1, "R1", "2K", R_BG)
# R1 top connects to U1-Pin2 (I0 output)
# R1 bottom connects to GND
draw_trace_h(ws, 5, 6, 5, BLUE)  # U1-Pin2 -> R1 top
draw_trace_v(ws, 8, 5, 24, BLUE) # R1 bottom -> GND (vertical trace down)

# ---- C1: 0.01uF (parallel with R1) ----
draw_comp(ws, 9, 5, 2, 1, "C1", "0.01u", C_BG)
draw_trace_h(ws, 6, 9, 5, BLUE)  # connect R1 node to C1

# ---- C3: 0.01uF (filter, from U2-Pin3 to GND) ----
draw_comp(ws, 9, 7, 2, 1, "C3", "0.01u", C_BG)

# ---- U2: OP07 DIP-8 (Upper op-amp) ----
draw_ic_dip8(ws, 12, 5, "U2\nOP07", [])
# U2 pins: 1=+VCC(12,5), 2=IN-(12,6), 3=IN+(12,7), 4=-VEE(12,8), 
#          5=NC(15,8), 6=OUT(15,7), 7=+VCC(15,6), 8=NULL(15,5)

# +12V to U2-Pin1 and Pin7
draw_trace_v(ws, 12, 3, 5, BLUE)  # Pin1 -> +12V rail
draw_trace_v(ws, 15, 3, 5, BLUE)  # Pin7 -> +12V rail (via trace up)

# -12V to U2-Pin4
draw_trace_v(ws, 12, 8, 13, BLUE) # Pin4 -> -12V rail

# U2-Pin3 (IN+) <- R1/C1 node (signal input)
draw_trace_h(ws, 8, 12, 7, BLUE)  # from C1/R1 node to U2-Pin3

# C3 connects Pin3 to GND
draw_trace_v(ws, 10, 7, 24, BLUE) # C3 bottom -> GND

# U2-Pin2 (IN-) <- C1 left side / R2
draw_trace_h(ws, 9, 12, 6, BLUE)  # C1 left -> U2-Pin2

# ---- R2: 2.6K (feedback resistor, GND to U2-Pin2) ----
draw_comp(ws, 6, 6, 2, 1, "R2", "2.6K", R_BG)
draw_trace_h(ws, 6, 9, 6, BLUE)   # R2 right -> U2-Pin2 node
draw_trace_v(ws, 6, 6, 24, BLUE)  # R2 left -> GND (down)
# Actually R2 left=GND, so trace down from (6,7) to GND
# Let me fix: R2 is at (6,6)-(7,6), left end at X=6
# R2 left -> GND: trace from (6,7) down to (6,24)

# ---- C2: 0.01uF (decoupling, U2-Pin4 to GND) ----
draw_comp(ws, 10, 9, 2, 1, "C2", "0.01u", C_BG)
draw_trace_h(ws, 10, 12, 9, BLUE)  # C2 top -> U2-Pin4 area

# ---- W3: 20K potentiometer (U2 offset null adjust) ----
draw_comp(ws, 17, 4, 2, 2, "W3", "20K", W_BG)
set_cell(ws, 16, 4, "1\n+12V", bg=LABEL_BG, font=Font(size=5,color="FFFFFF"))
set_cell(ws, 19, 4, "3", bg=LABEL_BG, font=Font(size=5,color="FFFFFF"))
set_cell(ws, 19, 5, "2\n->8", bg=LABEL_BG, font=Font(size=5,color="FFFFFF"))
# W3 left -> +12V
draw_trace_v(ws, 17, 3, 4, BLUE)
# W3 wiper -> U2-Pin8
draw_trace_h(ws, 15, 19, 5, BLUE)  # U2-Pin8 -> W3 wiper

# ---- U2 Pin6 (OUT) -> M+ output ----
# Trace right from Pin6 (15,7) to M+ terminal
draw_trace_h(ws, 15, 22, 7, BLUE)  # Output trace to right area
# M+ terminal at (1,7) - trace from output back to terminal
# Actually M+ is terminal at left. Let's route: U2-Pin6 -> right -> down -> left
# Or better: label the output point
set_cell(ws, 22, 7, "M+", bg="C00000", font=Font(bold=True,size=7,color="FFFFFF"))

# ---- W1: 10K potentiometer (U2 gain adjust) ----
draw_comp(ws, 23, 6, 2, 2, "W1", "10K", W_BG)
set_cell(ws, 22, 6, "3\nOUT", bg=LABEL_BG, font=Font(size=5,color="FFFFFF"))
set_cell(ws, 25, 6, "1", bg=LABEL_BG, font=Font(size=5,color="FFFFFF"))
set_cell(ws, 25, 7, "2", bg=LABEL_BG, font=Font(size=5,color="FFFFFF"))
# W1 top (pin3) -> M+/U2-Pin6 output
draw_trace_h(ws, 22, 23, 7, BLUE)

# ---- R3: 1K (W1 wiper to G4 node) ----
draw_comp(ws, 23, 8, 2, 1, "R3", "1K", R_BG)

# ---- R4: 1K (G4 to GND) ----
draw_comp(ws, 23, 10, 2, 1, "R4", "1K", R_BG)

# ---- C4: 0.01uF (feedback cap, G4 to U2-Pin2) ----
draw_comp(ws, 20, 9, 2, 1, "C4", "0.01u", C_BG)

# G4 node: R3 right + R4 top + C4 right + W1 bottom
draw_trace_h(ws, 23, 25, 9, BLUE)  # R3 right -> W1 bottom
draw_trace_v(ws, 25, 7, 10, BLUE)  # W1 area down

# R4 bottom -> GND
draw_trace_v(ws, 24, 11, 24, BLUE) # R4 -> GND

# C4 right -> G4 node
draw_trace_h(ws, 21, 23, 9, BLUE)

# *** RED JUMPER 1: C4 left -> U2-Pin2 ***
draw_trace_h(ws, 12, 20, 9, RED)   # Red horizontal trace!
set_cell(ws, 16, 9, "FLY1", bg=RED, font=Font(bold=True,size=5,color="FFFFFF"))

# ============================================================
# Lower half: Reference channel (Y=14~23)
# ============================================================

# ---- U3: MC1403 (precision voltage reference, 3-pin) ----
draw_comp(ws, 3, 15, 2, 2, "U3", "MC1403", IC_BG)
set_cell(ws, 2, 15, "1\nVIN", bg=LABEL_BG, font=Font(size=5,bold=True,color="FFFFFF"))
set_cell(ws, 5, 15, "2\nOUT", bg=LABEL_BG, font=Font(size=5,bold=True,color="FFFFFF"))
set_cell(ws, 5, 16, "3\nGND", bg=LABEL_BG, font=Font(size=5,bold=True,color="FFFFFF"))
# U3-Pin1 -> +12V
draw_trace_v(ws, 3, 3, 15, BLUE)
# U3-Pin3 -> GND
draw_trace_v(ws, 5, 16, 24, BLUE)

# ---- R5: 10K (U3 output to U4-Pin2) ----
draw_comp(ws, 7, 15, 2, 1, "R5", "10K", R_BG)
draw_trace_h(ws, 5, 7, 15, BLUE)  # U3-OUT -> R5 left

# ---- C5: 0.01uF (U4-Pin3 filter to GND) ----
draw_comp(ws, 9, 17, 2, 1, "C5", "0.01u", C_BG)

# ---- U4: OP07 DIP-8 (Lower op-amp) ----
draw_ic_dip8(ws, 12, 17, "U4\nOP07", [])
# U4 pins: 1=+VCC(12,17), 2=IN-(12,18), 3=IN+(12,19), 4=-VEE(12,20),
#          5=NC(15,20), 6=OUT(15,19), 7=+VCC(15,18), 8=NULL(15,17)

# +12V to U4-Pin1 and Pin7
draw_trace_v(ws, 12, 3, 17, BLUE)  # Pin1 -> +12V (long trace down)
draw_trace_v(ws, 15, 3, 17, BLUE)  # Pin7 -> +12V

# -12V to U4-Pin4
draw_trace_v(ws, 12, 13, 20, BLUE) # Pin4 -> -12V rail

# U4-Pin2 (IN-) <- R5 right
draw_trace_h(ws, 9, 12, 18, BLUE)  # R5 right -> U4-Pin2

# U4-Pin3 (IN+) <- C5
draw_trace_h(ws, 9, 12, 19, BLUE)  # C5 -> U4-Pin3
# C5 bottom -> GND
draw_trace_v(ws, 10, 18, 24, BLUE)

# ---- C6: 0.01uF (decoupling, U4-Pin4 to GND) ----
draw_comp(ws, 10, 21, 2, 1, "C6", "0.01u", C_BG)
draw_trace_h(ws, 10, 12, 21, BLUE)  # C6 -> U4-Pin4 area
# C6 bottom -> GND
draw_trace_v(ws, 11, 22, 24, BLUE)

# ---- W4: 20K potentiometer (U4 offset null) ----
draw_comp(ws, 17, 16, 2, 2, "W4", "20K", W_BG)
set_cell(ws, 16, 16, "1\n+12V", bg=LABEL_BG, font=Font(size=5,color="FFFFFF"))
set_cell(ws, 19, 16, "3", bg=LABEL_BG, font=Font(size=5,color="FFFFFF"))
set_cell(ws, 19, 17, "2\n->8", bg=LABEL_BG, font=Font(size=5,color="FFFFFF"))
draw_trace_v(ws, 17, 3, 16, BLUE)  # W4 -> +12V
draw_trace_h(ws, 15, 19, 17, BLUE) # U4-Pin8 -> W4 wiper

# ---- U4 Pin6 (OUT) -> M- output ----
draw_trace_h(ws, 15, 22, 19, BLUE)
set_cell(ws, 22, 19, "M-", bg="C00000", font=Font(bold=True,size=7,color="FFFFFF"))

# ---- W2: 10K potentiometer (U4 gain adjust) ----
draw_comp(ws, 23, 18, 2, 2, "W2", "10K", W_BG)
set_cell(ws, 22, 18, "3\nOUT", bg=LABEL_BG, font=Font(size=5,color="FFFFFF"))
set_cell(ws, 25, 18, "1", bg=LABEL_BG, font=Font(size=5,color="FFFFFF"))
set_cell(ws, 25, 19, "2", bg=LABEL_BG, font=Font(size=5,color="FFFFFF"))
draw_trace_h(ws, 22, 23, 19, BLUE)  # W1 top -> M- output

# ---- R6: 680 (W2 wiper to H4 node) ----
draw_comp(ws, 23, 20, 2, 1, "R6", "680", R_BG)

# ---- R7: 1K (H4 to GND) ----
draw_comp(ws, 23, 22, 2, 1, "R7", "1K", R_BG)

# ---- C7: 0.01uF (feedback cap, H4 to U4-Pin2) ----
draw_comp(ws, 20, 21, 2, 1, "C7", "0.01u", C_BG)

# H4 node connections
draw_trace_h(ws, 21, 23, 21, BLUE)  # C7 right -> H4
draw_trace_v(ws, 25, 19, 22, BLUE)  # W2 down

# R7 bottom -> GND (already at Y=23, close to GND at 24)
draw_trace_v(ws, 24, 23, 24, BLUE)

# *** RED JUMPER 2: C7 left -> U4-Pin2 ***
draw_trace_h(ws, 12, 20, 21, RED)  # Red horizontal trace!
set_cell(ws, 16, 21, "FLY2", bg=RED, font=Font(bold=True,size=5,color="FFFFFF"))

# ============================================================
# M+/M- output traces back to left terminals
# ============================================================
# M+ at (22,7) -> terminal (1,7)
# Route: go left along Y=11 (between upper/lower halves)
# But that would cross -12V rail. Use Y=12 instead
draw_trace_h(ws, 1, 22, 12, BLUE)  # M+ trace back (along Y=12)
draw_trace_v(ws, 22, 7, 12, BLUE)  # connect down from M+ to Y=12
draw_trace_v(ws, 1, 7, 12, BLUE)   # connect from terminal to Y=12

# M- at (22,19) -> terminal (1,8)  
# Route: go left along Y=23
draw_trace_h(ws, 1, 22, 23, BLUE)  # M- trace back
draw_trace_v(ws, 22, 19, 23, BLUE)
draw_trace_v(ws, 1, 8, 23, BLUE)

# ============================================================
# Legend
# ============================================================
set_cell(ws, 27, 3, "B", bg=BLUE, font=Font(bold=True,size=8,color="FFFFFF"))
set_cell(ws, 28, 3, "Blue", bg=None, font=f_small)
set_cell(ws, 27, 4, "A", bg=RED, font=Font(bold=True,size=8,color="FFFFFF"))
set_cell(ws, 28, 4, "Red", bg=None, font=f_small)
set_cell(ws, 27, 5, "IC", bg=IC_BG, font=f_comp)
set_cell(ws, 28, 5, "IC", bg=None, font=f_small)
set_cell(ws, 27, 6, "R", bg=R_BG, font=f_comp)
set_cell(ws, 28, 6, "Res", bg=None, font=f_small)
set_cell(ws, 27, 7, "C", bg=C_BG, font=f_comp)
set_cell(ws, 28, 7, "Cap", bg=None, font=f_small)
set_cell(ws, 27, 8, "W", bg=W_BG, font=f_comp)
set_cell(ws, 28, 8, "Pot", bg=None, font=f_small)

# ============================================================
# Summary note
# ============================================================
ws.merge_cells(start_row=26, start_column=1, end_row=26, end_column=COLS)
note = ws.cell(row=26, column=1)
note.value = ("Fly wires (Red, A-side): FLY1=C4->U2-Pin2 | FLY2=C7->U4-Pin2 | Total=2 (<=3 OK)  |  "
              "24-grid lower half: single-side supply (-12V only at Y=13)")
note.font = Font(size=8, bold=True)
note.fill = fill("FFFF00")
note.alignment = center

# Print settings
ws.sheet_properties.pageSetUpPr.fitToPage = True
ws.page_setup.orientation = 'landscape'
ws.page_setup.fitToWidth = 1
ws.page_setup.fitToHeight = 1

out = r"C:\Users\cxx\WorkBuddy\2026-07-05-22-13-37\数字温度计_布线图.xlsx"
wb.save(out)
print("OK: " + out)
