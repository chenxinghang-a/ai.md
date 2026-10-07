# -*- coding: utf-8 -*-
"""把 results/ 下的分项报告汇编成单文件 HTML 报告。"""
import os
import re
import html as htmlmod
import markdown
from markdown.extensions.toc import TocExtension

BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(BASE, "results")
OUT = os.path.join(BASE, "港卡调研报告.html")

ORDER = [
    "00-总览与决策指南.md",
    "10-最终筛选结论.md",
    "07-筛选-卡型核实.md",
    "08-筛选-传统银行核实.md",
    "09-筛选-Google订阅与境外刷卡实操.md",
    "11-筛选-实体银行最简单两家.md",
    "12-筛选-其他实体银行排名.md",
    "13-核实-中银学生豁免条款.md",
    "14-核实-学生证明文件清单.md",
    "15-深挖-众安银行ZA_Bank.md",
    "16-深挖-中银香港BOCHK.md",
    "17-核实-赴港开户时间成本.md",
    "01-传统银行A组.md",
    "02-传统银行B组与中资行.md",
    "03-虚拟银行.md",
    "04-政策监管与合规红线.md",
    "05-投资与券商入金.md",
    "06-实操避坑与维护.md",
]


def collect_ids(tokens):
    out = []
    for t in tokens:
        out.append(t["id"])
        out.extend(collect_ids(t.get("children", [])))
    return out


def build_nav(tokens, prefix, depth=0):
    items = []
    for t in tokens:
        items.append((t["level"], prefix + "-" + t["id"], t["name"]))
        items.extend(build_nav(t.get("children", []), prefix, depth + 1))
    return items


sections_html = []
nav_html = []
stats = []

for idx, fname in enumerate(ORDER):
    path = os.path.join(RESULTS, fname)
    if not os.path.exists(path):
        continue
    with open(path, encoding="utf-8") as f:
        text = f.read()

    lines = len(text.splitlines())
    stats.append((fname, lines))

    md = markdown.Markdown(
        extensions=["extra", "sane_lists", TocExtension(toc_depth="1-3")],
        output_format="html5",
    )
    body = md.convert(text)
    prefix = "f%d" % idx

    for i in sorted(collect_ids(md.toc_tokens), key=len, reverse=True):
        body = body.replace('id="%s"' % i, 'id="%s-%s"' % (prefix, i))
        body = re.sub(r'href="#%s"' % re.escape(i), 'href="#%s-%s"' % (prefix, i), body)

    # 表格加滚动容器
    body = body.replace("<table>", '<div class="table-wrap"><table>')
    body = body.replace("</table>", "</table></div>")
    # 锚点链接去掉 ¶
    body = body.replace('[¶]', '')

    nav_html.append('<div class="nav-sec">%s</div>' % md.toc)

    sections_html.append(
        '<section class="doc" id="doc%d">%s</section>' % (idx, body)
    )

total_lines = sum(s[1] for s in stats)

CSS = """
:root{
  --bg:#ffffff; --bg-soft:#f8fafc; --bg-alt:#f1f5f9;
  --fg:#0f172a; --fg-soft:#475569; --fg-mute:#94a3b8;
  --line:#e2e8f0; --accent:#1d4ed8; --accent-soft:#eff6ff;
  --red:#b91c1c; --amber:#b45309; --green:#15803d;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{
  margin:0; background:var(--bg); color:var(--fg);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
  font-size:15px; line-height:1.75;
  -webkit-font-smoothing:antialiased;
}
.layout{display:flex; align-items:flex-start; max-width:1500px; margin:0 auto;}

/* ---------- sidebar ---------- */
aside{
  position:sticky; top:0; flex:0 0 300px; width:300px; max-height:100vh;
  overflow-y:auto; padding:24px 18px 60px 24px;
  border-right:1px solid var(--line); background:var(--bg-soft);
  font-size:13px; line-height:1.6;
}
aside .brand{font-weight:700; font-size:15px; margin:0 0 4px}
aside .sub{color:var(--fg-mute); font-size:12px; margin-bottom:18px}
aside a{color:var(--fg-soft); text-decoration:none; display:block; padding:2px 0}
aside a:hover{color:var(--accent)}
aside ul{list-style:none; margin:0; padding:0}
aside .nav-sec{margin-bottom:6px}
aside .nav-sec > ul > li > a{font-weight:600; color:var(--fg); margin-top:14px}
aside .nav-sec ul ul{padding-left:14px; border-left:2px solid var(--line); margin-left:2px}
aside .nav-sec ul ul a{font-size:12.5px; color:var(--fg-mute)}
aside::-webkit-scrollbar{width:8px}
aside::-webkit-scrollbar-thumb{background:#cbd5e1; border-radius:4px}

/* ---------- main ---------- */
main{flex:1 1 auto; min-width:0; padding:40px 56px 120px; max-width:1060px}
h1,h2,h3,h4{line-height:1.35; font-weight:700}
h1{font-size:27px; margin:0 0 18px; padding-bottom:14px; border-bottom:2px solid var(--fg)}
h2{font-size:21px; margin:44px 0 14px; padding-left:11px; border-left:4px solid var(--accent); color:#0b1220}
h3{font-size:17px; margin:30px 0 10px; color:#111c33}
h4{font-size:15px; margin:22px 0 8px; color:var(--fg-soft)}
p{margin:11px 0}
a{color:var(--accent)}
strong{color:#0b1220; font-weight:700}
hr{border:0; border-top:1px solid var(--line); margin:38px 0}
ul,ol{padding-left:24px; margin:10px 0}
li{margin:5px 0}
code{
  background:var(--bg-alt); padding:2px 6px; border-radius:4px;
  font-family:ui-monospace,SFMono-Regular,Consolas,monospace; font-size:13px; color:#0f172a;
}
pre{background:#0f172a; color:#e2e8f0; padding:14px 18px; border-radius:8px; overflow-x:auto}
pre code{background:none; color:inherit; padding:0}

/* ---------- table ---------- */
.table-wrap{overflow-x:auto; margin:16px 0; border:1px solid var(--line); border-radius:8px}
table{border-collapse:collapse; width:100%; font-size:13.5px; background:#fff}
th,td{border-bottom:1px solid var(--line); border-right:1px solid var(--line); padding:8px 12px; text-align:left; vertical-align:top}
th:last-child,td:last-child{border-right:0}
tr:last-child td{border-bottom:0}
thead th{background:var(--bg-alt); font-weight:700; color:#0b1220; white-space:nowrap}
tbody tr:nth-child(even){background:#fcfdfe}
tbody tr:hover{background:var(--accent-soft)}

/* ---------- blockquote / callouts ---------- */
blockquote{
  margin:16px 0; padding:12px 18px; border-left:4px solid var(--accent);
  background:var(--accent-soft); border-radius:0 6px 6px 0; color:#1e293b;
}
blockquote p{margin:6px 0}
blockquote strong{color:var(--accent)}

/* ---------- section divider ---------- */
.doc{padding-top:8px}
.doc + .doc{border-top:1px dashed #cbd5e1; margin-top:70px; padding-top:40px}

/* ---------- cover ---------- */
.cover{
  background:linear-gradient(135deg,#0f172a 0%,#1e3a8a 100%); color:#fff;
  border-radius:14px; padding:36px 40px; margin-bottom:36px;
}
.cover h1{border:0; font-size:32px; margin:0 0 10px; color:#fff; padding:0}
.cover p{margin:6px 0; color:#cbd5e1; font-size:14px}
.cover .meta{margin-top:22px; display:flex; flex-wrap:wrap; gap:10px}
.cover .chip{
  background:rgba(255,255,255,.12); border:1px solid rgba(255,255,255,.22);
  padding:5px 13px; border-radius:999px; font-size:12.5px; color:#e2e8f0;
}

@media (max-width:1000px){
  aside{display:none}
  main{padding:28px 18px 80px}
}
@media print{
  aside{display:none}
  main{max-width:none; padding:0}
  .doc + .doc{border-top:none; page-break-before:always}
}
"""

cover = """
<div class="cover">
  <h1>大学生开港卡 · 全景深度调研</h1>
  <p>香港银行卡 · 全卡商 / 全卡种 / 政策 / 费率 / 便利性 / 优惠 —— 精细拆解到每一点</p>
  <div class="meta">
    <span class="chip">调研时点 2026-09-16</span>
    <span class="chip">对象：中国内地大学生 · 无资产无收入</span>
    <span class="chip">%d 份分项报告 / %d 行</span>
    <span class="chip">6 路并行调研 + 3 路筛选核实</span>
  </div>
</div>
""" % (len(sections_html), total_lines)

page = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>大学生开港卡 · 全景深度调研</title>
<style>%s</style>
</head>
<body>
<div class="layout">
<aside>
  <div class="brand">大学生开港卡调研</div>
  <div class="sub">2026-09-16 · 7 份分项报告</div>
  %s
</aside>
<main>
%s
%s
</main>
</div>
</body>
</html>
""" % (CSS, "\n".join(nav_html), cover, "\n".join(sections_html))

with open(OUT, "w", encoding="utf-8") as f:
    f.write(page)

print("OUT:", OUT)
print("sections:", len(sections_html), "total_lines:", total_lines)
for s in stats:
    print("  ", s[0], s[1])
