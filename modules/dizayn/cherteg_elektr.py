"""Рабочий чертёж «Электр чизмаси» по образцу Anoor/Ali Homes: стены, двери, мебель сверху,
розетки/выключатели с H= и расстоянием от угла в см, штамп справа. Комната 345×390 см, потолок 210."""
from pathlib import Path
D = Path(__file__).parent
K = 2.05                 # px на см
OX, OY = 230, 175        # левый-верхний (северо-западный) внутренний угол
WC, LC = 345, 390        # см
WALL = 22                # толщина стены, см (рисуем)

def X(x): return OX + x * K
def Y(y): return OY + (LC - y) * K     # y от южной стены

out = []
A = out.append

def line(x0, y0, x1, y1, cls): A(f'<line x1="{X(x0):.1f}" y1="{Y(y0):.1f}" x2="{X(x1):.1f}" y2="{Y(y1):.1f}" class="{cls}"/>')
def rect(x0, y0, x1, y1, cls, rx=0): A(f'<rect x="{X(x0):.1f}" y="{Y(y1):.1f}" width="{(x1-x0)*K:.1f}" height="{(y1-y0)*K:.1f}" rx="{rx}" class="{cls}"/>')
def txt(x, y, t, cls, anchor="start", rot=0):
    tr = f' transform="rotate({rot} {X(x):.1f} {Y(y):.1f})"' if rot else ""
    A(f'<text x="{X(x):.1f}" y="{Y(y):.1f}" class="{cls}" text-anchor="{anchor}" dominant-baseline="central"{tr}>{t}</text>')

# ---------- стены (серые, толстые), с проёмами
T = WALL
rect(-T, LC, WC + T, LC + T, "wall")            # север
rect(-T, -T, WC + T, 0, "wall")                 # юг
rect(-T, -T, 0, LC + T, "wall")                 # запад
rect(WC, -T, WC + T, LC + T, "wall")            # восток
rect(155, LC - 1, 278, LC + T + 1, "open")      # проём входа
rect(240, -T - 1, 334, 1, "open")               # проём 2-й комнаты
# вход: блок окно+дверь (линии остекления как в образце — голубым)
line(155, LC + T / 2, 278, LC + T / 2, "glass")
line(155, LC, 155, LC + T, "frame"); line(278, LC, 278, LC + T, "frame"); line(193, LC, 193, LC + T, "frame")
A(f'<path d="M{X(205):.1f} {Y(LC):.1f} A {72*K:.1f} {72*K:.1f} 0 0 0 {X(277):.1f} {Y(LC-72):.1f}" class="swing"/>')
line(277, LC, 277, LC - 72, "leaf")
# дверь во 2-ю комнату (открывание в офис)
line(240, 0, 240, -T, "frame"); line(334, 0, 334, -T, "frame")
A(f'<path d="M{X(246):.1f} {Y(0):.1f} A {82*K:.1f} {82*K:.1f} 0 0 1 {X(328):.1f} {Y(82):.1f}" class="swing"/>')
line(328, 0, 328, 82, "leaf")

# ---------- мебель (вид сверху, тонкие коричневые линии)
rect(4, LC - 6, 150, LC, "slat")                                  # рейки на стене ТВ
rect(25, LC - 40, 145, LC - 6, "furn")                            # тумба
rect(30, LC - 9, 142, LC - 6, "tv")                               # ТВ
# угловой диван
rect(6, 6, 96, 305, "furn", 4); rect(96, 6, 220, 96, "furn", 4)
rect(6, 6, 28, 305, "furnin"); rect(96, 6, 220, 28, "furnin")
for cy in (60, 140, 220): rect(30, cy, 92, cy + 70, "furnin", 3)
for cx in (110, 160): rect(cx, 30, cx + 45, 92, "furnin", 3)
txt(60, 250, "Бурчак", "fl", "middle"); txt(60, 235, "диван", "fl", "middle")
rect(125, 135, 185, 255, "furn", 3); txt(155, 195, "Стол", "fl", "middle")
rect(262, 155, 340, 235, "furn", 6); rect(318, 155, 340, 235, "furnin"); txt(290, 195, "Кресло", "fl", "middle")
rect(286, LC - 22, 340, LC, "acd"); txt(313, LC - 30, "Кондиционер", "fl", "middle")
rect(55, LC - 3, 77, LC, "fan")

# ---------- электрика: символы, подписи, размеры от угла
def sock(x, y, wall):
    # символ розетки: полукруг к стене + черта
    cx, cy = X(x), Y(y)
    d = {"n": (0, 1), "s": (0, -1), "w": (1, 0), "e": (-1, 0)}[wall]
    ox, oy = d[0] * 13, d[1] * 13
    A(f'<circle cx="{cx+ox:.1f}" cy="{cy+oy:.1f}" r="9" class="sock"/>')
    A(f'<line x1="{cx+ox-d[1]*9:.1f}" y1="{cy+oy-d[0]*9:.1f}" x2="{cx+ox+d[1]*9:.1f}" y2="{cy+oy+d[0]*9:.1f}" class="sockl"/>')
    return cx + ox, cy + oy
def switch(x, y, wall):
    cx, cy = X(x), Y(y)
    d = {"n": (0, 1), "s": (0, -1), "w": (1, 0), "e": (-1, 0)}[wall]
    ox, oy = d[0] * 13, d[1] * 13
    A(f'<circle cx="{cx+ox:.1f}" cy="{cy+oy:.1f}" r="8" class="sw"/>')
    A(f'<line x1="{cx+ox:.1f}" y1="{cy+oy:.1f}" x2="{cx+ox+11:.1f}" y2="{cy+oy-11:.1f}" class="swl"/>')
def note(px, py, lines, anchor="start"):
    for i, t in enumerate(lines):
        A(f'<text x="{px:.1f}" y="{py + i*19:.1f}" class="el" text-anchor="{anchor}">{t}</text>')
def dim_h(x0, x1, y, off):   # горизонтальный размер вдоль стены, off — смещение в px
    yy = Y(y) + off
    A(f'<line x1="{X(x0):.1f}" y1="{yy:.1f}" x2="{X(x1):.1f}" y2="{yy:.1f}" class="dim"/>')
    for xv in (x0, x1):
        A(f'<line x1="{X(xv)-5:.1f}" y1="{yy+5:.1f}" x2="{X(xv)+5:.1f}" y2="{yy-5:.1f}" class="dimt2"/>')
    A(f'<text x="{(X(x0)+X(x1))/2:.1f}" y="{yy-7:.1f}" class="dn" text-anchor="middle">{abs(x1-x0):g}</text>')
def dim_v(y0, y1, x, off):
    xx = X(x) + off
    A(f'<line x1="{xx:.1f}" y1="{Y(y0):.1f}" x2="{xx:.1f}" y2="{Y(y1):.1f}" class="dim"/>')
    for yv in (y0, y1):
        A(f'<line x1="{xx-5:.1f}" y1="{Y(yv)+5:.1f}" x2="{xx+5:.1f}" y2="{Y(yv)-5:.1f}" class="dimt2"/>')
    m = (Y(y0) + Y(y1)) / 2
    A(f'<text x="{xx-7:.1f}" y="{m:.1f}" class="dn" text-anchor="middle" transform="rotate(-90 {xx-7:.1f} {m:.1f})">{abs(y1-y0):g}</text>')

# 1 ТВ ортида H=110 (2 роз + интернет), 2 тумба H=30
sock(85, LC, "n"); sock(45, LC, "n")
dim_h(0, 45, LC, 52); dim_h(45, 85, LC, 52)
note(X(30), Y(LC) + 92, ["Розетка 2x + интернет H=110", "Розетка 2x H=30"])
# 3 диван боши H=75, 4 диван бурчаги H=90 (запад)
sock(0, 320, "w"); sock(0, 45, "w")
dim_v(LC, 320, 0, 40); dim_v(0, 45, 0, 40)
note(X(0) + 52, Y(320) + 4, ["Розетка 2x + USB H=75"])
note(X(0) + 52, Y(45) - 30, ["Розетка 1x + USB H=90"])
# 5 съёмка H=30, 7 хизмат H=30 (восток)
sock(WC, 270, "e"); sock(WC, 75, "e")
dim_v(LC, 270, WC, -40); dim_v(0, 75, WC, -40)
note(X(WC) - 52, Y(270) - 14, ["Розетка 2x H=30", "(съёмка: ҳалқа чироқ)"], "end")
note(X(WC) - 52, Y(75) - 30, ["Розетка 1x H=30"], "end")
# 6 кондиционер H=200
sock(332, LC, "n"); dim_h(332, WC, LC, 52)
note(X(WC) - 4, Y(LC) + 92, ["Розетка конд. H=200"], "end")
# выключатели
switch(292, LC, "n"); dim_h(278, 292, LC, 30)
note(X(292) - 6, Y(LC) + 128, ["Включатель 3 кл. H=90", "спот / LED / рейка"], "end")
switch(225, 0, "s"); dim_h(225, 240, 0, -30)
note(X(225) - 8, Y(0) - 56, ["Включатель 2 кл. H=90", "спот / вытяжка"], "end")
# LED подсветка рейка

# ---------- общие размеры снаружи
def odim_h(x0, x1, y, off, t):
    yy = Y(y) + off
    A(f'<line x1="{X(x0):.1f}" y1="{yy:.1f}" x2="{X(x1):.1f}" y2="{yy:.1f}" class="dim"/>')
    for xv in (x0, x1):
        A(f'<line x1="{X(xv)-5:.1f}" y1="{yy+5:.1f}" x2="{X(xv)+5:.1f}" y2="{yy-5:.1f}" class="dimt2"/>')
    A(f'<text x="{(X(x0)+X(x1))/2:.1f}" y="{yy-8:.1f}" class="dn2" text-anchor="middle">{t}</text>')
def odim_v(y0, y1, x, off, t):
    xx = X(x) + off
    A(f'<line x1="{xx:.1f}" y1="{Y(y0):.1f}" x2="{xx:.1f}" y2="{Y(y1):.1f}" class="dim"/>')
    for yv in (y0, y1):
        A(f'<line x1="{xx-5:.1f}" y1="{Y(yv)+5:.1f}" x2="{xx+5:.1f}" y2="{Y(yv)-5:.1f}" class="dimt2"/>')
    m = (Y(y0) + Y(y1)) / 2
    A(f'<text x="{xx-9:.1f}" y="{m:.1f}" class="dn2" text-anchor="middle" transform="rotate(-90 {xx-9:.1f} {m:.1f})">{t}</text>')
odim_h(0, 155, LC, -(T * K) - 30, "155"); odim_h(155, 278, LC, -(T * K) - 30, "123"); odim_h(278, WC, LC, -(T * K) - 30, "67")
odim_h(0, WC, LC, -(T * K) - 68, "349")
odim_h(0, 240, 0, T * K + 34, "240"); odim_h(240, 334, 0, T * K + 34, "94"); odim_h(334, WC, 0, T * K + 34, "11")
odim_h(0, WC, 0, T * K + 72, "339")
odim_v(0, LC, 0, -(T * K) - 36, "395")
odim_v(0, LC, WC, (T * K) + 46, "387")

plan = "".join(out)

TITLE = """
<div class="tb">
 <div class="tb1">OZOD JAMOL<br/>ЧИЗМАСИ</div>
 <div class="tbr">Офис · 13,5 м² · H=210</div>
 <div class="tbr">Электр чизмаси · M 1:25</div>
 <div class="tbh">Шартли белгилар</div>
 <div class="lg"><svg width="40" height="26"><circle cx="20" cy="15" r="9" class="sock"/><line x1="11" y1="15" x2="29" y2="15" class="sockl"/></svg>Розетка</div>
 <div class="lg"><svg width="40" height="26"><circle cx="16" cy="15" r="8" class="sw"/><line x1="16" y1="15" x2="27" y2="4" class="swl"/></svg>Включатель</div>
 <div class="lg"><svg width="40" height="26"><line x1="4" y1="13" x2="36" y2="13" class="glass"/></svg>Ойна</div>
 <div class="lg"><svg width="40" height="26"><line x1="4" y1="13" x2="36" y2="13" class="dim"/></svg>Ўлчам, см</div>
 <div class="lg"><svg width="40" height="26"><rect x="4" y="8" width="32" height="10" fill="#e8d3b3" stroke="#8a5a32"/></svg>Рейка + LED H=205 / H=5</div>
 <div class="tbr sm">H — полдан баландлик, см</div>
 <div class="tbsp"></div>
 <div class="tbr sm">Дизайнер: Озод Жамол</div>
 <div class="tbh">Эслатма</div>
 <div class="tbr sm">1. Ўлчамларни объектнинг ўзида текшириб олинсин.<br/>2. Кабел фақат вертикал ва горизонтал ётқизилсин.</div>
 <div class="tbn">ВАРАҚ 2</div>
</div>"""

CSS = """
@page{size:1600px 1131px;margin:0}*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter';font-weight:700;background:#fff;color:#222}
.sheet{width:1600px;height:1131px;position:relative;border:3px solid #111;margin:0}
.draw{position:absolute;left:0;top:0;width:1280px;height:1125px}
.tb{position:absolute;right:0;top:0;width:314px;height:1125px;border-left:3px solid #111;display:flex;flex-direction:column}
.tb>div{border-bottom:2px solid #111;padding:10px 14px}
.tb1{font-size:26px;font-weight:900;line-height:1.15}.tbr{font-size:19px;font-weight:800}.sm{font-size:16px;font-weight:700;line-height:1.35}
.tbh{font-size:19px;font-weight:900;background:#f2f2f2}
.lg{display:flex;align-items:center;gap:10px;font-size:17px;font-weight:800;border-bottom:1px solid #ccc!important}
.tbsp{flex:1}.tbn{font-size:24px;font-weight:900;text-align:center;border-bottom:none!important}
.wall{fill:#5f6062}.open{fill:#fff}
.glass{stroke:#1aa3e0;stroke-width:4}.frame{stroke:#6b4a2e;stroke-width:2}
.swing{fill:none;stroke:#8a6a4a;stroke-width:1.6}.leaf{stroke:#8a6a4a;stroke-width:2.5}
.furn{fill:#fff;stroke:#8a5a32;stroke-width:1.8}.furnin{fill:none;stroke:#b08360;stroke-width:1.2}
.slat{fill:#e8d3b3;stroke:#8a5a32;stroke-width:1.2}.tv{fill:#333}
.acd{fill:none;stroke:#555;stroke-width:1.6;stroke-dasharray:6 4}.fan{fill:#fff;stroke:#333;stroke-width:1.5}
.fl{font-size:14px;font-weight:800;fill:#8a5a32;paint-order:stroke;stroke:#fff;stroke-width:4px}
.sock{fill:#fff;stroke:#d11;stroke-width:2.4}.sockl{stroke:#d11;stroke-width:2.4}
.sw{fill:#fff;stroke:#d11;stroke-width:2.4}.swl{stroke:#d11;stroke-width:2.4}
.el{font-size:15px;font-weight:800;fill:#e0680a;paint-order:stroke;stroke:#fff;stroke-width:5px;stroke-linejoin:round}
.dim{stroke:#d11;stroke-width:1.3}.dimt2{stroke:#d11;stroke-width:1.8}
.dn{font-size:14px;font-weight:900;fill:#d11;paint-order:stroke;stroke:#fff;stroke-width:4px}.dn2{font-size:16px;font-weight:900;fill:#111}
.room{font-size:20px;font-weight:900;fill:#e0680a}
"""
html = f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<div class="sheet"><svg class="draw" viewBox="0 0 1280 1125">{plan}</svg>{TITLE}</div></body></html>"""
(D / "cherteg.html").write_text(html, encoding="utf-8")
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1600, "height": 1131})
    pg.goto((D / "cherteg.html").as_uri()); pg.wait_for_timeout(500)
    pg.screenshot(path=str(D / "cherteg_elektr.png"), full_page=False)
    pg.pdf(path=str(D / "cherteg_elektr.pdf"), width="1600px", height="1131px", print_background=True)
    b.close()
print("ok")
