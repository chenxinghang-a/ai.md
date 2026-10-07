"""
PCB layout generator for digital thermometer circuit (30x24 grid)
Usage: python pcb_layout.py > layout.html
Future: pip install matplotlib && python pcb_layout.py --png
"""
import sys

template = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>数字温度计 PCB 30x24</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Microsoft YaHei',Arial,sans-serif;background:#e8e8e8;padding:10px}
.wrap{max-width:1100px;margin:0 auto;background:#fff;border-radius:8px;padding:12px;box-shadow:0 2px 10px rgba(0,0,0,0.1)}
h1,h2{text-align:center;font-size:20px;margin:4px 0}
h1 em{color:#C00;font-style:normal}
.legend{display:flex;gap:14px;justify-content:center;margin:6px 0;flex-wrap:wrap}
.legend span{display:inline-flex;align-items:center;gap:4px;font-size:11px}
.legend .sw{display:inline-block;width:14px;height:14px;border:1px solid #999;border-radius:2px}
.toolbar{text-align:center;margin:8px 0}
.toolbar button{padding:5px 14px;margin:0 3px;cursor:pointer;font-size:13px;border:1px solid #999;border-radius:3px;background:#fff}
.toolbar button:hover{background:#e0e0e0}
canvas{display:block;margin:0 auto;border:1px solid #aaa;max-width:100%}
.foot{text-align:center;font-size:11px;color:#666;margin-top:6px;line-height:1.6}
</style></head>
<body><div class="wrap">
<h1>%TITLE% <em>30x24</em></h1>
<div class="legend">
<span><span class="sw" style="background:#4472C4"></span>B面走线</span>
<span><span class="sw" style="background:#F00"></span>A面飞线</span>
<span><span class="sw" style="background:#00B050"></span>+12V</span>
<span><span class="sw" style="background:#FFF2CC;border-color:#C90"></span>IC</span>
<span><span class="sw" style="background:#E2EFDA"></span>电阻R</span>
<span><span class="sw" style="background:#D9E1F2"></span>电容C</span>
<span><span class="sw" style="background:#FCE4D6"></span>电位器W</span>
<span><span class="sw" style="background:#CCC"></span>端子</span>
</div>
<div class="toolbar">
<button onclick="Z(0.2)">+</button>
<button onclick="Z(-0.2)">-</button>
<button onclick="Z(0,true)">Fit</button>
<button onclick="window.print()" style="background:#2F5496;color:#fff;border-color:#2F5496">Print</button>
</div>
<canvas id="c"></canvas>
<div class="foot">%FOOTER%</div>
</div>
<script>%SCRIPT%</script>
</body></html>'''


if __name__ == '__main__':
    print("PCB Layout Generator ready.")
    print("Edit layout data in code, then run: python pcb_layout.py > output.html")
