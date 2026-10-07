# -*- coding: utf-8 -*-
"""30x24 grid PCB layout, matching standard answer."""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

wb = Workbook()
ws = wb.active
ws.title = "PCB-30x24"

COLS, ROWS = 30, 24
BLUE = "4472C4"   # B trace
RED = "FF0000"    # A jumper
GRN = "00B050"    # +12V
DGR = "006100"    # -12V
BLK = "000000"    # GND
IC_ = "FFF2CC"    # IC
R_  = "E2EFDA"    # R
C_  = "D9E1F2"    # C
W_  = "FCE4D6"    # Pot
LAB = "808080"    # label

fT = Font(bold=True, size=14, color="FFFFFF")
fH = Font(bold=True, size=8, color="FFFFFF")
fS = Font(size=7)
fB = Font(bold=True, size=7)
fP = Font(size=5, bold=True, color="FFFFFF")

th = Side(style='thin', color='A0A0A0')
md = Side(style='medium', color='000000')
bT = Border(left=th, right=th, top=th, bottom=th)
bM = Border(left=md, right=md, top=md, bottom=md)
CT = Alignment(horizontal='center', vertical='center', wrap_text=True)

def F(c): return PatternFill("solid", fgColor=c)

def sc(ws, x, y, v="", bg=None, ft=None, bd=bT):
    from openpyxl.cell.cell import MergedCell
    c = ws.cell(row=y, column=x)
    if isinstance(c, MergedCell): return c
    c.value = v; c.alignment = CT
    if bg: c.fill = F(bg)
    c.font = ft or fS
    if bd: c.border = bd
    return c

def hln(ws, x1, x2, y, c=BLUE):
    for x in range(x1, x2+1): sc(ws, x, y, "", c)
def vln(ws, x, y1, y2, c=BLUE):
    for y in range(y1, y2+1): sc(ws, x, y, "", c)

def box(ws, x, y, w, h, txt, bg=IC_, ft=fB):
    ws.merge_cells(start_row=y, start_column=x, end_row=y+h-1, end_column=x+w-1)
    c = ws.cell(row=y, column=x)
    c.value = txt; c.font = ft; c.fill = F(bg); c.alignment = CT; c.border = bM
    for r in range(y, y+h):
        for col in range(x, x+w):
            cc = ws.cell(row=r, column=col)
            cc.border = bM; cc.fill = F(bg)

def ic8(ws, x, y, name):
    """DIP-8, 4x5 body. B-view: notch left, pins 1-4 left, 8-5 right."""
    box(ws, x, y, 4, 5, name, IC_, Font(bold=True, size=8))
    for i in range(4):
        sc(ws, x-1, y+i, str(i+1), LAB, fP)      # left: 1,2,3,4
        sc(ws, x+4, y+i, str(8-i), LAB, fP)      # right: 8,7,6,5

# ---- sizing ----
for col in range(1, 32):
    ws.column_dimensions[get_column_letter(col)].width = 3.0
for row in range(1, 27):
    ws.row_dimensions[row].height = 18

# ---- title ----
ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=COLS)
t = ws.cell(row=1, column=1)
t.value = "数字温度计 PCB 30x24 | Blue=B面 Red=A面飞线 | 飞线<=3"
t.font = fT; t.fill = F("2F5496"); t.alignment = CT

# coord headers
for x in range(1, COLS+1): sc(ws, x, 2, str(x), "404040", fH)
for y in range(3, ROWS+3): sc(ws, 31, y, str(y-2), "404040", fH)

# ---- power rails ----
hln(ws, 1, COLS, 3, BLUE);  sc(ws, 1, 3, "+12V", GRN, fB)
hln(ws, 1, COLS, 13, BLUE); sc(ws, 1, 13, "-12V", DGR, fB)
hln(ws, 1, COLS, 24, BLK);  sc(ws, 1, 24, "GND", BLK, fB)

# ---- left 7 terminals ----
terms = [(4,"+12V",GRN),(5,"-12V",DGR),(6,"GND",BLK),(7,"M+","C00000"),
         (8,"M-","C00000"),(9,"AD590\n+",GRN),(10,"备用","808080")]
for y,lab,co in terms: sc(ws, 1, y, lab, co, fB)

# ============================================================
# UPPER HALF: Temperature channel (Y=4~12)
# ============================================================

# U1 AD590 (3-pin) at (3,4)
box(ws, 3, 4, 2, 2, "U1\nAD590", IC_, fB)
sc(ws, 2, 4, "1", LAB, fP); sc(ws, 5, 4, "2", LAB, fP); sc(ws, 5, 5, "3", LAB, fP)
vln(ws, 3, 3, 4, BLUE)   # +12V -> U1-Pin1

# R1 2K (6,5) horizontal
box(ws, 6, 5, 2, 1, "R1\n2K", R_, fB)
hln(ws, 5, 6, 5, BLUE)    # U1-Pin2 -> R1 left

# C1 0.01u (9,5) horizontal
box(ws, 9, 5, 2, 1, "C1\n0.01u", C_, fB)
hln(ws, 6, 9, 5, BLUE)    # R1 -> C1

# U2 OP07 (12,5) DIP-8
ic8(ws, 12, 5, "U2\nOP07")
vln(ws, 12, 3, 5, BLUE)  # Pin1 +VCC
vln(ws, 15, 3, 5, BLUE)  # Pin7 +VCC
vln(ws, 12, 8, 13, BLUE) # Pin4 -VEE

# R2 2.6K (6,6) vertical feedback
box(ws, 6, 6, 2, 1, "R2\n2.6K", R_, fB)
hln(ws, 6, 12, 6, BLUE)  # R2 right -> U2-Pin2
vln(ws, 6, 7, 24, BLUE)  # R2 left -> GND

# C3 0.01u (10,7) horizontal, U2-Pin3 filter
box(ws, 10, 7, 2, 1, "C3\n0.01u", C_, fB)
hln(ws, 8, 12, 7, BLUE)  # C1/R1 node -> U2-Pin3
vln(ws, 11, 8, 24, BLUE) # C3 -> GND

# C2 0.01u (10,9) decoupling, U2-Pin4
box(ws, 10, 9, 2, 1, "C2\n0.01u", C_, fB)
hln(ws, 10, 12, 9, BLUE) # C2 -> U2-Pin4
vln(ws, 11, 10, 24, BLUE) # C2 -> GND

# W3 20K (16,4) vertical, offset null
box(ws, 16, 4, 2, 2, "W3\n20K", W_, fB)
sc(ws, 15, 4, "1", LAB, fP); sc(ws, 19, 4, "3", LAB, fP); sc(ws, 19, 5, "2", LAB, fP)
vln(ws, 16, 3, 4, BLUE)   # W3-1 -> +12V
hln(ws, 15, 19, 5, BLUE)  # W3-2 -> U2-Pin8

# M+ output (22,7)
sc(ws, 22, 7, "M+", "C00000", fB)
hln(ws, 15, 22, 7, BLUE)  # U2-Pin6 -> M+

# W1 10K (20,6) vertical, gain adjust
box(ws, 20, 6, 2, 2, "W1\n10K", W_, fB)
sc(ws, 19, 6, "3", LAB, fP); sc(ws, 23, 6, "1", LAB, fP); sc(ws, 23, 7, "2", LAB, fP)
hln(ws, 19, 20, 7, BLUE)  # W1-3 -> M+/U2-Pin6

# R3 1K (20,9) horizontal
box(ws, 20, 9, 2, 1, "R3\n1K", R_, fB)

# R4 1K (24,9) horizontal
box(ws, 24, 9, 2, 1, "R4\n1K", R_, fB)
vln(ws, 25, 10, 24, BLUE) # R4 -> GND

# C4 0.01u (22,8) vertical, feedback cap
box(ws, 22, 8, 2, 1, "C4\n0.01u", C_, fB)

# node connections (upper right feedback network)
hln(ws, 21, 24, 9, BLUE)  # R3-R4-C4-W1 node (G4)
vln(ws, 23, 7, 9, BLUE)   # W1-2 -> node
vln(ws, 22, 9, 10, BLUE)  # C4 down to node

# *** RED FLY 1: C4 left -> U2-Pin2 ***
hln(ws, 12, 22, 8, RED)
sc(ws, 16, 8, "J1", RED, Font(bold=True, size=6, color="FFFFFF"))

# M+ back to left terminal (1,7)
vln(ws, 22, 7, 11, BLUE)
hln(ws, 1, 22, 11, BLUE)
vln(ws, 1, 7, 11, BLUE)

# ============================================================
# LOWER HALF: Reference channel (Y=14~23)
# ============================================================

# U3 MC1403 (3,15)
box(ws, 3, 15, 2, 2, "U3\nMC1403", IC_, fB)
sc(ws, 2, 15, "1", LAB, fP); sc(ws, 5, 15, "2", LAB, fP); sc(ws, 5, 16, "3", LAB, fP)
vln(ws, 3, 3, 15, BLUE)   # +12V -> U3-Pin1
vln(ws, 5, 16, 24, BLUE)  # U3-Pin3 -> GND

# R5 10K (6,15) horizontal
box(ws, 6, 15, 2, 1, "R5\n10K", R_, fB)
hln(ws, 5, 6, 15, BLUE)   # U3-Pin2 -> R5

# C5 0.01u (10,17) horizontal, U4-Pin3 filter
box(ws, 10, 17, 2, 1, "C5\n0.01u", C_, fB)

# U4 OP07 (12,17) DIP-8
ic8(ws, 12, 17, "U4\nOP07")
vln(ws, 12, 3, 17, BLUE)  # Pin1 +VCC
vln(ws, 15, 3, 17, BLUE)  # Pin7 +VCC
vln(ws, 12, 13, 20, BLUE) # Pin4 -VEE

# R5 -> U4-Pin2
hln(ws, 6, 12, 18, BLUE)

# C5 -> U4-Pin3
hln(ws, 10, 12, 19, BLUE)
vln(ws, 11, 19, 24, BLUE) # C5 -> GND

# C6 0.01u (10,21) decoupling, U4-Pin4
box(ws, 10, 21, 2, 1, "C6\n0.01u", C_, fB)
hln(ws, 10, 12, 21, BLUE)
vln(ws, 11, 22, 24, BLUE) # C6 -> GND

# W4 20K (16,16) vertical, offset null
box(ws, 16, 16, 2, 2, "W4\n20K", W_, fB)
sc(ws, 15, 16, "1", LAB, fP); sc(ws, 19, 16, "3", LAB, fP); sc(ws, 19, 17, "2", LAB, fP)
vln(ws, 16, 3, 16, BLUE)   # W4-1 -> +12V
hln(ws, 15, 19, 17, BLUE)  # W4-2 -> U4-Pin8

# M- output (22,19)
sc(ws, 22, 19, "M-", "C00000", fB)
hln(ws, 15, 22, 19, BLUE)  # U4-Pin6 -> M-

# W2 10K (20,18) vertical, gain adjust
box(ws, 20, 18, 2, 2, "W2\n10K", W_, fB)
sc(ws, 19, 18, "3", LAB, fP); sc(ws, 23, 18, "1", LAB, fP); sc(ws, 23, 19, "2", LAB, fP)
hln(ws, 19, 20, 19, BLUE)  # W2-3 -> M-/U4-Pin6

# R6 680 (20,21) horizontal
box(ws, 20, 21, 2, 1, "R6\n680", R_, fB)

# R7 1K (24,21) horizontal
box(ws, 24, 21, 2, 1, "R7\n1K", R_, fB)
vln(ws, 25, 22, 24, BLUE)  # R7 -> GND

# C7 0.01u (22,20) vertical, feedback cap
box(ws, 22, 20, 2, 1, "C7\n0.01u", C_, fB)

# node connections (lower right feedback network)
hln(ws, 21, 24, 21, BLUE)  # R6-R7-C7-W2 node (H4)
vln(ws, 23, 19, 21, BLUE)   # W2-2 -> node
vln(ws, 22, 21, 22, BLUE)   # C7 down to node

# *** RED FLY 2: C7 left -> U4-Pin2 ***
hln(ws, 12, 22, 20, RED)
sc(ws, 16, 20, "J2", RED, Font(bold=True, size=6, color="FFFFFF"))

# M- back to left terminal (1,8)
vln(ws, 22, 19, 23, BLUE)
hln(ws, 1, 22, 23, BLUE)
vln(ws, 1, 8, 23, BLUE)

# ============================================================
# Legend & note
# ============================================================
sc(ws, 27, 3, "B", BLUE, fB); sc(ws, 28, 3, "B面", None, fS)
sc(ws, 27, 4, "A", RED, fB);  sc(ws, 28, 4, "A面", None, fS)
sc(ws, 27, 5, "IC", IC_, fB); sc(ws, 28, 5, "IC", None, fS)
sc(ws, 27, 6, "R", R_, fB);   sc(ws, 28, 6, "电阻", None, fS)
sc(ws, 27, 7, "C", C_, fB);   sc(ws, 28, 7, "电容", None, fS)
sc(ws, 27, 8, "W", W_, fB);   sc(ws, 28, 8, "电位器", None, fS)

ws.merge_cells(start_row=26, start_column=1, end_row=26, end_column=COLS)
n = ws.cell(row=26, column=1)
n.value = "飞线2条: J1=C4->U2-Pin2 | J2=C7->U4-Pin2 | 24格下半部-12V单侧供电 | 左侧7端子"
n.font = Font(size=8, bold=True)
n.fill = F("FFFF00")
n.alignment = CT

ws.page_setup.orientation = 'landscape'
ws.page_setup.fitToWidth = 1
ws.sheet_properties.pageSetUpPr.fitToPage = True

out = r"C:\Users\cxx\WorkBuddy\2026-07-05-22-13-37\数字温度计_布线图_v2.xlsx"
wb.save(out)
print("OK: " + out)
