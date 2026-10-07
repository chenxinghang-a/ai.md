"""电路分析演示 —— 用 lcapy 验证 Python 已具备电路分析能力
覆盖:节点电压分析(电阻网络) / 运放增益 / RC 低通传递函数与伯德图
"""
import matplotlib
matplotlib.use("Agg")  # 无显示环境, 存图即可
import matplotlib.pyplot as plt
import numpy as np
import sympy as sym
from lcapy import Circuit, R, C, s

print("=" * 50)
print("1) 节点电压分析(电阻网络)")
print("=" * 50)
cct = Circuit()
cct.add("V1 1 0 10")     # 10V 源
cct.add("R1 1 2 2k")     # 2k
cct.add("R2 2 0 3k")     # 3k 到地
cct.add("R3 2 3 1k")     # 1k
cct.add("R4 3 0 4k")     # 4k 到地
cct.analyse()
v2, v3 = cct[2].v, cct[3].v
print("节点2电压 V2 =", v2, "=", v2.dc.value, "V")
print("节点3电压 V3 =", v3, "=", v3.dc.value, "V")

print()
print("=" * 50)
print("2) 反相运放增益 (R1=1k, Rf=10k)")
print("=" * 50)
R1, Rf = 1000, 10000
gain = -Rf / R1
print(f"Vo/Vi = -Rf/R1 = {gain}  (即放大 {-gain} 倍, 反相)")

print()
print("=" * 50)
print("3) RC 低通传递函数 + 伯德图")
print("=" * 50)
rc = Circuit()
rc.add("R1 1 2 1k")
rc.add("C1 2 0 1u")
rc.add("V1 1 0 step 1")
rc.analyse()
H = rc.transfer(1, 0, 2, 0)          # H(s) = Vout/Vin
print("H(s) = Vout/Vin =", H)
try:
    w = np.logspace(0, 6, 600)                 # 1Hz ~ 1MHz
    s_sym = sym.symbols("s")
    Hsym = sym.sympify(str(H.expr))            # 转纯 sympy 表达式, 通用稳妥
    Hfun = sym.lambdify(s_sym, Hsym, "numpy")  # H(s) 转可调函数
    Hw = Hfun(1j * w)
    mag = 20 * np.log10(np.abs(Hw))            # 幅频 dB
    phase = np.angle(Hw, deg=True)             # 相频 deg
    fig, axes = plt.subplots(2, 1, figsize=(7, 5))
    axes[0].semilogx(w / (2 * np.pi), mag)
    axes[0].set_ylabel("增益 (dB)"); axes[0].grid(True)
    axes[1].semilogx(w / (2 * np.pi), phase)
    axes[1].set_xlabel("频率 (Hz)"); axes[1].set_ylabel("相位 (°)")
    axes[1].grid(True)
    plt.tight_layout()
    plt.savefig("rc_bode.png", dpi=110)
    print("伯德图已保存 -> rc_bode.png")
except Exception as e:
    print("伯德图绘制跳过(非致命):", e)

print()
print("电路分析栈 OK")
