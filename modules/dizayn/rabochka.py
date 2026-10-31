"""Рабочка (ишчи чизмалар) — синов: хонадон 82,5 м². OZOD JAMOL · интерьер дизайн.
Чизмалар SVG (см бирлигида) → HTML A3 → PDF (Playwright). Масштаб 1:50 (1 см = 0,2 мм)."""
import math
from pathlib import Path
from geo import WALLS, WINDOWS, GLASS, DOORS, BAL_DOOR, ROOMS, area

OUT = Path(__file__).parent / "out"; OUT.mkdir(exist_ok=True)
S = 0.2          # мм на 1 см (1:50)
OX, OY = 38, 40  # отступ плана на листе, мм
WALL = "#3d3d3d"; FUR = "#a5743f"; DIM = "#c62828"; EL = "#1565c0"; LT = "#e0a100"; GRY = "#777"
ERK = dict(x0=865, y0=377, x1=1034, y1=634, bulge=1085)

# ---------- базовые элементы ----------
def rect(x0, y0, x1, y1, fill="none", stroke=FUR, w=1.2, extra=""):
    return f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="{fill}" stroke="{stroke}" stroke-width="{w}" {extra}/>'

def line(x0, y0, x1, y1, stroke=FUR, w=1.2, extra=""):
    return f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y1}" stroke="{stroke}" stroke-width="{w}" {extra}/>'

def text(x, y, s, size=14, fill="#222", anchor="middle", weight=400, rot=0, extra=""):
    tr = f' transform="rotate({rot} {x} {y})"' if rot else ""
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" font-weight="{weight}"'
            f' dominant-baseline="middle"{tr} {extra}>{s}</text>')

def shell(furniture=False, light=False):
    """Стены, окна, витраж, двери, эркер."""
    g = []
    if light:                                   # для электрики/потолка — стены светлее, чтобы символы читались
        wcol = "#6b6b6b"
    else:
        wcol = WALL
    for x0, y0, x1, y1 in WALLS:
        if x1 > x0 and y1 > y0:
            g.append(rect(x0, y0, x1, y1, fill=wcol, stroke=wcol, w=0.5))
    for x0, y0, x1, y1, _ in WINDOWS:              # окно: рама + 2 стекла
        g.append(rect(x0, y0, x1, y1, fill="#fff", stroke="#333", w=1))
        if x1 - x0 < y1 - y0:
            for k in (0.35, 0.65):
                xx = x0 + (x1 - x0) * k
                g.append(line(xx, y0, xx, y1, stroke="#3a86c8", w=1.4))
        else:
            for k in (0.35, 0.65):
                yy = y0 + (y1 - y0) * k
                g.append(line(x0, yy, x1, yy, stroke="#3a86c8", w=1.4))
    for x0, y0, x1, y1 in GLASS:                   # стеклянная перегородка
        g.append(rect(x0, y0, x1, y1, fill="#fff", stroke="#333", w=1))
        g.append(line((x0 + x1) / 2, y0, (x0 + x1) / 2, y1, stroke="#3a86c8", w=1.6))
    # эркер — полукруглое остекление
    e = ERK; cx = 2 * e["bulge"] - 1034; my = (e["y0"] + e["y1"]) / 2
    for off, col, ww in ((0, "#333", 1.2), (-6, "#3a86c8", 1.4), (-12, "#333", 1.2)):
        g.append(f'<path d="M1034 {e["y0"]} Q {cx+off*2} {my} 1034 {e["y1"]}" fill="none" stroke="{col}" stroke-width="{ww}"/>')
    # двери
    for d in DOORS:
        x0, x1, y = d["x0"], d["x1"], d["y"]; w = x1 - x0
        if d["side"] == "in_up":                 # входная: проём y..y+15, открывается внутрь (вверх)
            yy = y
        else:
            yy = y
        g.append(rect(x0, yy, x1, yy + 15, fill="#fff", stroke="#fff", w=0.1))
        if d["side"] == "out":                   # открывается наружу (в меҳмонхону)
            g.append(line(x0, yy + 15, x0, yy + 15 + w, stroke="#333", w=1.6))
            g.append(f'<path d="M{x0} {yy+15+w} A {w} {w} 0 0 0 {x1} {yy+15}" fill="none" stroke="#666" stroke-width="0.9" stroke-dasharray="6 4"/>')
            continue
        g.append(line(x0, yy, x0, yy - w, stroke="#333", w=1.6))
        g.append(f'<path d="M{x0} {yy-w} A {w} {w} 0 0 1 {x1} {yy}" fill="none" stroke="#666" stroke-width="0.9" stroke-dasharray="6 4"/>')
    bx0, by0, bx1, by1 = BAL_DOOR                  # стеклянная дверь в эркер
    g.append(rect(bx0, by0, bx1, by1, fill="#fff", stroke="#fff", w=0.1))
    g.append(line(bx0, by0, bx0 - 90, by0, stroke="#333", w=1.6))
    g.append(f'<path d="M{bx0-90} {by0} A 90 90 0 0 0 {bx0} {by1}" fill="none" stroke="#666" stroke-width="0.9" stroke-dasharray="6 4"/>')
    return "\n".join(g)

def room_labels(small=False, with_area=True):
    g = []
    for i, (n, poly, (cx, cy)) in enumerate(ROOMS, 1):
        a = area(poly) + (0.68 if n == "Эркер" else 0)
        r = 22
        if n == "Эркер":
            g.append(text(cx, cy - 8, n.upper(), 13, "#333", weight=600)); g.append(text(cx, cy + 10, f"{a:.1f} м²".replace(".", ","), 12, "#555"))
            continue
        g.append(f'<circle cx="{cx}" cy="{cy-30}" r="{r}" fill="#fff" stroke="{FUR}" stroke-width="1.5"/>')
        g.append(text(cx, cy - 29, str(i), 22, FUR, weight=600))
        g.append(text(cx, cy + 6, n.upper(), 17 if not small else 14, "#333", weight=600))
        if with_area:
            g.append(text(cx, cy + 28, f"{a:.1f} м²".replace(".", ","), 15, "#555"))
    return "\n".join(g)

# ---------- размерные цепочки ----------
def hdim(x0, x1, y, ext_from=None, label=None, size=15, col=DIM, up=True):
    g = [line(x0, y, x1, y, col, 1)]
    for x in (x0, x1):
        g.append(line(x - 5, y + 5, x + 5, y - 5, col, 1.6))
        if ext_from is not None:
            g.append(line(x, ext_from, x, y + (4 if ext_from > y else -4), col, 0.6))
    v = label if label is not None else str(round(x1 - x0))
    g.append(text((x0 + x1) / 2, y - 9 if up else y + 11, v, size, col, weight=500))
    return "\n".join(g)

def vdim(y0, y1, x, ext_from=None, label=None, size=15, col=DIM, left=True):
    g = [line(x, y0, x, y1, col, 1)]
    for y in (y0, y1):
        g.append(line(x - 5, y + 5, x + 5, y - 5, col, 1.6))
        if ext_from is not None:
            g.append(line(ext_from, y, x + (4 if ext_from > x else -4), y, col, 0.6))
    v = label if label is not None else str(round(y1 - y0))
    xx = x - 10 if left else x + 10
    g.append(text(xx, (y0 + y1) / 2, v, size, col, weight=500, rot=-90))
    return "\n".join(g)

def chain_h(points, y, ext_from, size=14):
    return "\n".join(hdim(points[i], points[i + 1], y, ext_from, size=size) for i in range(len(points) - 1))

def chain_v(points, x, ext_from, size=14):
    return "\n".join(vdim(points[i], points[i + 1], x, ext_from, size=size) for i in range(len(points) - 1))

def dims_measure():
    g = []
    # снаружи — сверху: общий и по осям
    g.append(chain_h([0, 37, 212, 227, 504, 544, 994, 1034], -45, 0, 13))
    g.append(hdim(0, 1034, -95, 0, size=16))
    # снизу: вход, стены
    g.append(chain_h([0, 68, 168, 747, 759], 1015, 969, 13)); g.append(hdim(759, 996, 1015, 969, label="236", size=13)); g.append(hdim(996, 1036, 1015, 969, size=13))
    g.append(hdim(0, 1036, 1065, 969, size=16))
    # слева
    g.append(chain_v([0, 35, 362, 377, 954, 969], -45, 0, 13))
    g.append(vdim(0, 969, -95, 0, size=16))
    # справа: окна
    g.append(chain_v([0, 90, 238, 362, 377, 634, 652, 778, 928, 969], 1150, 1036, 13))
    # внутренние размеры комнат
    g.append(hdim(37, 212, 85, label="175")); g.append(vdim(35, 362, 70, label="327"))
    g.append(hdim(227, 504, 85, label="277")); g.append(vdim(47, 362, 262, label="315"))
    g.append(hdim(544, 994, 85, label="450")); g.append(vdim(47, 343, 960, label="296", left=True))
    g.append(hdim(40, 855, 645, label="815")); g.append(vdim(377, 954, 75, label="577"))
    g.append(hdim(40, 747, 880, label="707"))
    g.append(hdim(759, 996, 690, label="236")); g.append(vdim(652, 944, 795, label="292"))
    # проёмы
    for d in DOORS:
        y = d["y"] + 15 + 22 if d["side"] != "in_up" else d["y"] - 120
        if d["side"] == "in_up":
            g.append(hdim(d["x0"], d["x1"], 925, label=str(d["w"]), col="#6a1b9a", size=13))
        else:
            g.append(hdim(d["x0"], d["x1"], 398, label=str(d["w"]), col="#6a1b9a", size=13))
    g.append(vdim(412, 466, 845, label="55", col="#6a1b9a", size=12))
    g.append(vdim(466, 556, 845, label="90", col="#6a1b9a", size=12))
    g.append(vdim(556, 611, 845, label="55", col="#6a1b9a", size=12))
    return "\n".join(g)

# ---------- мебель ----------
def wardrobe(x0, y0, x1, y1, doors=2):
    g = [rect(x0, y0, x1, y1, "#fff", FUR, 1.3)]
    if x1 - x0 > y1 - y0:
        step = (x1 - x0) / doors
        for k in range(1, doors):
            g.append(line(x0 + step * k, y0, x0 + step * k, y1, FUR, 0.8))
    else:
        step = (y1 - y0) / doors
        for k in range(1, doors):
            g.append(line(x0, y0 + step * k, x1, y0 + step * k, FUR, 0.8))
    g.append(line(x0, y0, x1, y1, FUR, 0.5, 'stroke-dasharray="5 5"'))
    return "\n".join(g)

def bed(x, y, w, h, head="top", pillows=2):
    g = [rect(x, y, x + w, y + h, "#fff", FUR, 1.4, 'rx="4"')]
    if head == "top":
        g.append(rect(x, y, x + w, y + 10, "#f3e7d8", FUR, 1))
        pw = (w - 30) / pillows
        for k in range(pillows):
            g.append(rect(x + 10 + k * (pw + 10), y + 16, x + 10 + k * (pw + 10) + pw, y + 50, "#fff", FUR, 1, 'rx="8"'))
        g.append(line(x, y + h * 0.45, x + w, y + h * 0.45, FUR, 1))
        g.append(line(x + w * 0.1, y + h * 0.45, x + w * 0.35, y + h * 0.62, FUR, 0.6))
    return "\n".join(g)

def nightstand(x, y, s=45):
    return rect(x, y, x + s, y + 40, "#fff", FUR, 1.1) + f'<circle cx="{x+s/2}" cy="{y+20}" r="9" fill="none" stroke="{FUR}" stroke-width="0.8"/>'

def chair(cx, cy, rot=0, s=44):
    return (f'<g transform="rotate({rot} {cx} {cy})">' + rect(cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2, "#fff", FUR, 1, 'rx="6"')
            + line(cx - s / 2 + 3, cy - s / 2 + 7, cx + s / 2 - 3, cy - s / 2 + 7, FUR, 1.2) + "</g>")

def dining(x, y, w, h, seats_long=3):
    g = [rect(x, y, x + w, y + h, "#fff", FUR, 1.4, 'rx="4"')]
    step = w / seats_long
    for k in range(seats_long):
        cx = x + step * (k + 0.5)
        g.append(chair(cx, y - 30, 0)); g.append(chair(cx, y + h + 30, 180))
    g.append(chair(x - 30, y + h / 2, -90)); g.append(chair(x + w + 30, y + h / 2, 90))
    return "\n".join(g)

def sofa(x, y, w, d, face="left"):
    """Диван: спинка с противоположной стороны от face."""
    g = [rect(x, y, x + w, y + d, "#fff", FUR, 1.4, 'rx="6"')]
    if face == "left":     # сидит лицом влево, спинка справа (вертикальный)
        g.append(rect(x + w - 18, y, x + w, y + d, "#f3e7d8", FUR, 1))
        g.append(rect(x, y, x + w - 18, y + 16, "#f3e7d8", FUR, 1))
        g.append(rect(x, y + d - 16, x + w - 18, y + d, "#f3e7d8", FUR, 1))
        n = 3; step = (d - 32) / n
        for k in range(1, n):
            g.append(line(x, y + 16 + step * k, x + w - 18, y + 16 + step * k, FUR, 0.7))
    return "\n".join(g)

def armchair(cx, cy, rot=0, s=75):
    return (f'<g transform="rotate({rot} {cx} {cy})">' + rect(cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2, "#fff", FUR, 1.2, 'rx="12"')
            + rect(cx - s / 2, cy - s / 2, cx + s / 2, cy - s / 2 + 16, "#f3e7d8", FUR, 1, 'rx="6"') + "</g>")

def plant(cx, cy, r=22):
    g = [f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#eef5e9" stroke="#6b8e4e" stroke-width="1"/>']
    for a in range(0, 360, 45):
        g.append(line(cx, cy, cx + r * 0.85 * math.cos(math.radians(a)), cy + r * 0.85 * math.sin(math.radians(a)), "#6b8e4e", 0.7))
    return "\n".join(g)

def rug(x0, y0, x1, y1):
    return rect(x0, y0, x1, y1, "none", "#b9a58a", 1, 'stroke-dasharray="8 5" rx="6"')

def furniture():
    g = []
    # 1 Санузел (37..212 × 35..362), дверь 100..180 — наружу
    g.append(rect(37, 35, 212, 125, "#f4f8fb", FUR, 1.3))                  # душ 175×90
    g.append(line(37, 125, 212, 125, "#3a86c8", 2))
    g.append(line(37, 35, 212, 125, FUR, 0.5, 'stroke-dasharray="5 5"')); g.append(line(212, 35, 37, 125, FUR, 0.5, 'stroke-dasharray="5 5"'))
    g.append('<circle cx="124" cy="80" r="7" fill="none" stroke="#3a86c8" stroke-width="1.2"/>')
    g.append(rect(160, 145, 212, 200, "#fff", FUR, 1.2))                   # унитаз (инсталляция)
    g.append(f'<ellipse cx="180" cy="172" rx="22" ry="17" fill="#fff" stroke="{FUR}" stroke-width="1.2"/>')
    g.append(rect(152, 220, 212, 300, "#fff", FUR, 1.2))                   # тумба+раковина
    g.append(f'<ellipse cx="190" cy="260" rx="14" ry="22" fill="none" stroke="{FUR}" stroke-width="1"/>')
    g.append(rect(37, 140, 97, 200, "#fff", FUR, 1.2))                     # кир ювиш машинаси
    g.append(f'<circle cx="67" cy="170" r="20" fill="none" stroke="{FUR}" stroke-width="1"/>')
    g.append(rect(37, 205, 77, 280, "#fff", FUR, 1, 'stroke-dasharray="4 3"'))  # шкаф-колонна
    # 2 Болалар хонаси (227..504 × 47..362), дверь 342..432
    g.append(bed(232, 52, 90, 200, pillows=1))
    g.append(wardrobe(444, 52, 504, 290, 3))
    g.append(rect(330, 47, 440, 100, "#fff", FUR, 1.2))                    # стол
    g.append(chair(385, 125, 180))
    g.append(rect(232, 260, 322, 300, "#fff", FUR, 1, 'stroke-dasharray="4 3"'))  # стеллаж
    g.append(rug(330, 160, 430, 250))
    # 3 Ётоқхона (544..994 × 47..343), дверь 569..659
    g.append(nightstand(705, 52)); g.append(bed(752, 52, 160, 205)); g.append(nightstand(917, 52))
    g.append(wardrobe(549, 52, 609, 262, 4))
    g.append(rect(895, 290, 989, 338, "#fff", FUR, 1.2))                   # туалетный столик
    g.append(chair(940, 268, 0, 38))
    g.append(rug(735, 210, 935, 285))
    # 4 Меҳмонхона — юқори: овқатланиш зонаси, буфет; пастки: дам олиш (ТВ пастки деворда)
    g.append(rect(40, 430, 85, 640, "#fff", FUR, 1.3))                     # буфет/витрина
    g.append(text(100, 535, "буфет", 12, FUR, rot=-90))
    g.append(armchair(235, 470, 0)); g.append(plant(300, 425, 18))
    g.append(dining(340, 470, 220, 95, 3))                                 # стол 220×95, 8 кишилик
    g.append(rect(640, 600, 740, 637, "#fff", FUR, 1, 'stroke-dasharray="4 3"'))  # консоль
    g.append(rug(270, 670, 640, 885))
    g.append(sofa_l(300, 680, 300, 95, 170))                               # бурчакли диван, ТВ га қараб
    g.append(rect(390, 815, 500, 870, "#fff", FUR, 1.2, 'rx="8"'))         # журнал столи
    g.append(f'<circle cx="680" cy="720" r="16" fill="#fff" stroke="{FUR}" stroke-width="1"/>')   # торшер
    g.append(rect(330, 902, 570, 944, "#fff", FUR, 1.3))                   # ТВ тумба
    g.append(rect(400, 936, 500, 944, "#333", "#333", 0.5)); g.append(text(450, 922, "ТВ", 12, FUR))
    # эркер: 2 кресло дераза олдида
    g.append(armchair(990, 470, 90, 66)); g.append(armchair(990, 565, 90, 66))
    # кириш зонаси: шкаф чап деворда, банкетка
    g.append(wardrobe(40, 660, 100, 845, 3))
    g.append(rect(180, 905, 290, 940, "#fff", FUR, 1.1))                   # банкетка
    g.append(plant(720, 905))
    # 5 Ошхона (759..996 × 652..944): Г-шаклли, ювгич дераза олдида
    g.append(rect(936, 652, 996, 944, "#fff", FUR, 1.3))
    g.append(rect(759, 884, 936, 944, "#fff", FUR, 1.3))
    g.append(rect(944, 820, 988, 875, "#fff", FUR, 1))
    g.append(f'<ellipse cx="966" cy="847" rx="15" ry="20" fill="none" stroke="{FUR}" stroke-width="1"/>')
    for cx, cy in ((800, 902), (830, 902), (800, 928), (830, 928)):
        g.append(f'<circle cx="{cx}" cy="{cy}" r="10" fill="none" stroke="{FUR}" stroke-width="1"/>')
    g.append(rect(936, 652, 996, 720, "#fff", FUR, 1.4)); g.append(text(966, 686, "ХЛ", 12, FUR))
    g.append(line(759, 700, 759, 790, "#c62828", 1.2, 'stroke-dasharray="4 3"'))   # сурилма эшик
    return "\n".join(g)

def sofa_l(x, y, w, d, side):
    """Бурчакли диван: орқаси юқорида, ўнг қисми пастга чўзилган (ТВ пастки деворда)."""
    g = [rect(x, y, x + w, y + d, "#fff", FUR, 1.4, 'rx="6"'), rect(x, y, x + w, y + 18, "#f3e7d8", FUR, 1)]
    g.append(rect(x + w - d, y, x + w, y + side, "#fff", FUR, 1.4, 'rx="6"'))
    g.append(rect(x + w - 18, y, x + w, y + side, "#f3e7d8", FUR, 1))
    for k in (1, 2):
        g.append(line(x + (w - d) * k / 3, y + 18, x + (w - d) * k / 3, y + d, FUR, 0.7))
    return "\n".join(g)

# ---------- электрика ----------
def socket(x, y, n=1, rot=0, kind="", col=EL, ldy=16):
    g = [f'<g transform="rotate({rot} {x} {y})">']
    for k in range(n):
        xx = x + (k - (n - 1) / 2) * 16
        g.append(f'<path d="M{xx-7} {y} A 7 7 0 0 1 {xx+7} {y}" fill="none" stroke="{col}" stroke-width="1.6"/>')
        g.append(line(xx, y - 7, xx, y - 13, col, 1.6))
    g.append(line(x - 7 - (n - 1) * 8, y, x + 7 + (n - 1) * 8, y, col, 1.6))
    g.append("</g>")
    if kind:
        g.append(text(x, y + ldy, kind, 10, col, weight=600))
    return "\n".join(g)

def switch(x, y, n=1, col="#2e7d32"):
    g = [f'<circle cx="{x}" cy="{y}" r="6" fill="#fff" stroke="{col}" stroke-width="1.6"/>']
    for k in range(n):
        g.append(line(x + 4, y - 4 + k * 5, x + 15, y - 12 + k * 5, col, 1.6))
    return "\n".join(g)

def electrics():
    g = []
    # Санузел
    g.append(socket(67, 215, 1, 0, "IP44")); g.append(socket(205, 270, 1, 90, "IP44"))
    g.append(switch(85, 382))                                     # выключатель снаружи у двери С/У
    # Болалар
    g.append(socket(330, 105, 2, 0, "75")); g.append(socket(235, 260, 1, -90)); g.append(socket(500, 320, 1, 90))
    g.append(switch(442, 345, 1)); g.append(socket(325, 255, 1, 0, "БН"))
    # Ётоқхона
    g.append(socket(728, 100, 2, 0, "75")); g.append(socket(940, 100, 2, 0, "75"))
    g.append(socket(942, 300, 1, 0, "90")); g.append(socket(620, 330, 1, 0))
    g.append(switch(675, 345, 2)); g.append(switch(705, 85, 1)); g.append(switch(935, 85, 1))
    # Меҳмонхона — ТВ пастки деворда
    g.append(socket(420, 930, 2, 180)); g.append(socket(480, 930, 2, 180)); g.append(socket(450, 895, 1, 180, "ТВ+LAN"))
    g.append(socket(290, 700, 1, -90, "пол")); g.append(socket(610, 700, 1, 90, "пол"))
    g.append(socket(90, 460, 2, 90)); g.append(socket(90, 615, 1, 90)); g.append(socket(450, 395, 1, 180))
    g.append(socket(830, 470, 1, 90)); g.append(socket(830, 600, 1, 90)); g.append(socket(735, 720, 1, 90))
    g.append(socket(110, 905, 1, 0, "чангютгич"))
    g.append(switch(190, 932, 3)); g.append(switch(740, 395, 2)); g.append(switch(870, 455, 1)); g.append(switch(730, 860, 2))
    # Ошхона
    for yy in (760, 800, 870):
        g.append(socket(930, yy, 1, -90, "110"))
    g.append(socket(800, 878, 2, 0, "110")); g.append(socket(845, 938, 1, 180, "плита 32А", ldy=-22))
    g.append(socket(930, 690, 1, -90, "ХЛ")); g.append(socket(905, 878, 1, 0, "ИЮМ"))
    g.append(switch(770, 665, 2))
    # щиток
    g.append(rect(300, 930, 340, 944, EL, EL, 0.5)); g.append(text(320, 918, "ЩР", 11, EL, weight=700))
    return "\n".join(g)

# ---------- потолок и свет ----------
def track(x0, y0, x1, y1):
    return line(x0, y0, x1, y1, "#111", 4) + "".join(
        f'<rect x="{x0+(x1-x0)*k-5}" y="{y0+(y1-y0)*k-5}" width="10" height="10" fill="{LT}" stroke="#111" stroke-width="0.8"/>'
        for k in (0.15, 0.4, 0.65, 0.9))

def spot(x, y):
    return f'<circle cx="{x}" cy="{y}" r="7" fill="#fff" stroke="#111" stroke-width="1.3"/><circle cx="{x}" cy="{y}" r="2.5" fill="#111"/>'

def led(x0, y0, x1, y1):
    return line(x0, y0, x1, y1, LT, 3, 'stroke-dasharray="10 4"')

def pendant(x, y, r=26):
    return (f'<circle cx="{x}" cy="{y}" r="{r}" fill="none" stroke="#111" stroke-width="1.3"/>'
            + line(x - r * .7, y - r * .7, x + r * .7, y + r * .7, "#111", 1) + line(x - r * .7, y + r * .7, x + r * .7, y - r * .7, "#111", 1))

def ceiling():
    g = []
    gk = 'fill="none" stroke="#7b5ea7" stroke-width="1.4" stroke-dasharray="14 6"'
    # Меҳмонхона: короб по периметру 30 см, ниша с LED
    g.append(f'<rect x="70" y="407" width="755" height="507" {gk}/>')
    g.append(led(75, 412, 820, 412)); g.append(led(75, 909, 742, 909))
    g.append(track(150, 470, 150, 620)); g.append(track(330, 730, 610, 730)); g.append(track(330, 840, 610, 840))
    g.append(pendant(450, 517)); g.append(spot(360, 517)); g.append(spot(540, 517))
    for y in (690, 760, 830):
        g.append(spot(70, y))
    g.append(spot(945, 470)); g.append(spot(945, 570)); g.append(spot(700, 620))
    # Ошхона
    g.append(f'<rect x="774" y="667" width="207" height="262" {gk}/>')
    g.append(led(946, 670, 946, 930)); g.append(led(775, 880, 930, 880))
    for x, y in ((830, 730), (830, 790), (880, 760)):
        g.append(spot(x, y))
    # Ётоқхона: ниша над кроватью, LED
    g.append(f'<rect x="700" y="60" width="270" height="120" {gk}/>')
    g.append(led(705, 65, 965, 65)); g.append(track(600, 200, 860, 200))
    g.append(spot(620, 300)); g.append(spot(940, 300)); g.append(spot(580, 90))
    # Болалар
    g.append(f'<rect x="242" y="62" width="247" height="285" {gk}/>')
    g.append(led(245, 65, 485, 65)); g.append(pendant(380, 200, 22)); g.append(spot(270, 320)); g.append(spot(470, 320))
    # Санузел: влагостойкий ГКЛ, споты IP44
    for x, y in ((124, 80), (124, 180), (124, 280)):
        g.append(spot(x, y))
    g.append(led(150, 230, 150, 300))
    # отметки высот
    for x, y, h in ((200, 760, "+270"), (660, 470, "+280"), (880, 700, "+260"), (800, 120, "+270"), (360, 140, "+270"), (124, 130, "+250")):
        g.append(rect(x - 30, y - 12, x + 30, y + 12, "#fff", "#7b5ea7", 1, 'rx="4"'))
        g.append(text(x, y, h, 13, "#7b5ea7", weight=600))
    return "\n".join(g)

# ---------- пол ----------
def floor():
    g = ['<defs>'
         '<pattern id="parq" width="60" height="20" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
         '<path d="M0 10 H60 M30 0 V10 M0 0 V10" stroke="#c9a77c" stroke-width="0.8" fill="none"/></pattern>'
         '<pattern id="tile" width="60" height="60" patternUnits="userSpaceOnUse">'
         '<path d="M0 0 H60 V60" stroke="#8fa3b5" stroke-width="0.8" fill="none"/></pattern>'
         '<pattern id="tile2" width="120" height="60" patternUnits="userSpaceOnUse">'
         '<path d="M0 0 H120 V60 M0 30 H120" stroke="#9aa59b" stroke-width="0.8" fill="none"/></pattern>'
         '</defs>']
    for n, poly, _ in ROOMS:
        pts = " ".join(f"{x},{y}" for x, y in poly)
        pat = {"Санузел": "tile", "Ошхона": "tile2"}.get(n, "parq")
        g.append(f'<polygon points="{pts}" fill="url(#{pat})" stroke="none"/>')
    g.append(f'<rect x="40" y="840" width="160" height="104" fill="url(#tile2)" stroke="#555" stroke-width="1" stroke-dasharray="6 3"/>')
    return "\n".join(g)

# ---------- лист ----------
TITLE = "Хонадон интерьери · 82,5 м²"
def sheet(no, total, name, body, legend="", notes="", scale="1:50"):
    plan = f'<svg x="{OX}mm" y="{OY}mm" width="{1180*S}mm" height="{1130*S}mm" viewBox="-120 -130 1300 1250">{body}</svg>'
    return f"""<section class="page">
<svg class="frame" width="420mm" height="297mm" viewBox="0 0 420 297">
 <rect x="10" y="8" width="402" height="281" fill="none" stroke="#222" stroke-width="0.5"/>
 <line x1="306" y1="8" x2="306" y2="289" stroke="#222" stroke-width="0.5"/>
</svg>
<div class="plan">{plan_svg(body)}</div>
<div class="tb">
  <div class="brand"><div class="logo">OZOD JAMOL</div><div class="sub">интерьер дизайн</div></div>
  <div class="row"><b>Лойиҳа:</b> {TITLE}</div>
  <div class="row"><b>Манзил:</b> Навоийшоҳ кўч., 111/45 (9 қават)</div>
  <div class="row big">{name}</div>
  <div class="legend">{legend}</div>
  <div class="notes">{notes}</div>
  <div class="foot">
    <div><b>Масштаб</b><br>{scale}</div><div><b>Сана</b><br>31.10.2026</div><div><b>Варақ</b><br>{no} / {total}</div>
  </div>
  <div class="test">СИНОВ НУСХАСИ · ички солиштириш учун</div>
</div>
</section>"""

def plan_svg(body):
    return (f'<svg width="{1300*S}mm" height="{1250*S}mm" viewBox="-130 -140 1300 1250" '
            f'font-family="Inter, DejaVu Sans, sans-serif">{body}</svg>')

def leg(items):
    return "".join(f'<div class="li"><svg width="34" height="16" viewBox="-17 -8 34 16">{sym}</svg><span>{t}</span></div>' for sym, t in items)

CSS = """
@page { size: 420mm 297mm; margin: 0 }
* { box-sizing: border-box }
body { margin: 0; font-family: Inter, 'DejaVu Sans', sans-serif; color: #222 }
.page { width: 420mm; height: 297mm; position: relative; page-break-after: always; overflow: hidden }
.frame { position: absolute; left: 0; top: 0 }
.plan { position: absolute; left: 14mm; top: 12mm; width: 290mm; height: 274mm; display: flex; align-items: center; justify-content: center }
.plan svg { max-width: 290mm; max-height: 274mm }
.tb { position: absolute; left: 309mm; top: 11mm; width: 100mm; height: 275mm; display: flex; flex-direction: column; gap: 3mm; font-size: 3.1mm }
.brand { border-bottom: 0.4mm solid #222; padding-bottom: 3mm }
.logo { font-weight: 800; letter-spacing: 1.2mm; font-size: 7mm }
.sub { color: #a5743f; letter-spacing: 0.6mm; font-size: 3.2mm; text-transform: uppercase }
.row b { color: #555; font-weight: 600 }
.big { font-size: 5mm; font-weight: 700; padding: 2mm 0; border-top: 0.2mm solid #ccc; border-bottom: 0.2mm solid #ccc }
.legend { display: flex; flex-direction: column; gap: 1.6mm; font-size: 2.9mm }
.li { display: flex; align-items: center; gap: 2mm }
.notes { font-size: 2.75mm; line-height: 1.45; color: #333 }
.notes ol { margin: 0; padding-left: 4mm }
.foot { margin-top: auto; display: grid; grid-template-columns: 1fr 1fr 1fr; border-top: 0.4mm solid #222; padding-top: 2mm; font-size: 3mm }
.test { color: #c62828; font-size: 2.6mm; font-weight: 600; letter-spacing: 0.3mm }
table.sch { border-collapse: collapse; font-size: 3.2mm; width: 270mm }
table.sch th, table.sch td { border: 0.25mm solid #999; padding: 1.6mm 2.4mm; text-align: left }
table.sch th { background: #f3e7d8 }
.cover { position: absolute; left: 20mm; top: 20mm; width: 270mm }
.cover h1 { font-size: 15mm; margin: 0 0 4mm; letter-spacing: 0.5mm }
.cover .k { color: #a5743f; text-transform: uppercase; letter-spacing: 1mm; font-size: 4mm }
.cover dl { display: grid; grid-template-columns: 50mm 1fr; gap: 2mm 6mm; font-size: 4.5mm; margin-top: 10mm }
.cover dt { color: #777 } .cover dd { margin: 0; font-weight: 600 }
.toc { margin-top: 12mm; font-size: 4mm; line-height: 1.9 }
"""

def build():
    T = 8
    rooms_tbl = "".join(
        f"<tr><td>{i}</td><td>{n}</td><td>{(area(p) + (0.68 if n == 'Эркер' else 0)):.1f} м²</td></tr>".replace(".", ",")
        for i, (n, p, _) in enumerate(ROOMS, 1))
    total = sum(area(p) for _, p, _ in ROOMS) + 0.68
    pages = []
    # 1 — титул
    pages.append(f"""<section class="page">
<svg class="frame" width="420mm" height="297mm" viewBox="0 0 420 297">
 <rect x="10" y="8" width="402" height="281" fill="none" stroke="#222" stroke-width="0.5"/>
 <line x1="306" y1="8" x2="306" y2="289" stroke="#222" stroke-width="0.5"/></svg>
<div class="cover"><div class="k">Ишчи чизмалар тўплами</div><h1>{TITLE}</h1>
<dl><dt>Буюртмачи</dt><dd>Эксанов Авазбек</dd><dt>Манзил</dt><dd>Навоийшоҳ кўч., 111/45</dd>
<dt>Умумий майдон</dt><dd>82,5 м² (хоналар бўйича {total:.1f} м²)</dd><dt>Услуб</dt><dd>Замонавий минимализм</dd>
<dt>Шифт баландлиги</dt><dd>жойида ўлчанади (чизмада +280 деб олинган)</dd></dl>
<div class="toc"><b>Варақлар:</b><br>1. Титул · 2. Ўлчов чизмаси · 3. Мебель жойлашуви · 4. Электр: розетка ва ўчиргичлар ·
5. Шифт ва ёритиш · 6. Пол қопламаси · 7. Эшик ва деразалар · 8. Умумий изоҳлар</div></div>
<div class="plan" style="left:150mm;top:110mm;width:150mm;height:170mm">{plan_svg(shell() + room_labels(small=True))}</div>
<div class="tb"><div class="brand"><div class="logo">OZOD JAMOL</div><div class="sub">интерьер дизайн</div></div>
<div class="row"><b>Хоналар:</b></div><table class="sch" style="width:95mm;font-size:3mm"><tr><th>№</th><th>Хона</th><th>Майдон</th></tr>{rooms_tbl}</table>
<div class="foot"><div><b>Масштаб</b><br>—</div><div><b>Сана</b><br>31.10.2026</div><div><b>Варақ</b><br>1 / {T}</div></div>
<div class="test">СИНОВ НУСХАСИ · ички солиштириш учун</div></div></section>""".replace(f"{total:.1f}", f"{total:.1f}".replace(".", ",")))
    # 2 — обмер
    pages.append(sheet(2, T, "Ўлчов чизмаси", shell() + dims_measure() + room_labels(),
        leg([(line(-15, 0, 15, 0, DIM, 1.5), "Ички ва ташқи ўлчамлар, см"), (line(-15, 0, 15, 0, "#6a1b9a", 1.5), "Эшик ва дераза ўринлари, см"),
             ('<rect x="-15" y="-6" width="30" height="12" fill="#3d3d3d"/>', "Девор / устун")]),
        "<ol><li>Барча ўлчамлар сантиметрда.</li><li>Ўлчамлар AutoCAD ўлчов чизмасидан олинган — ишни бошлашдан олдин жойида қайта текширилсин.</li>"
        "<li>Тўсиқ деворлар бузилмайди; деворлар қалинлиги — мавжуд ҳолатда.</li></ol>"))
    # 3 — мебель
    pages.append(sheet(3, T, "Мебель жойлашуви", shell() + furniture() + room_labels(),
        leg([(rect(-15, -6, 15, 6, "#fff", FUR, 1.2), "Мебель (ўлчамлари билан ишлаб чиқарувчига)"),
             (rug(-15, -6, 15, 6), "Гилам"), (line(-15, 0, 15, 0, "#3a86c8", 3), "Ойна / шиша")]),
        "<ol><li>Меҳмонхона: юқори қисмда 8 кишилик овқатланиш столи (қандил остида) ва буфет; пастки қисмда бурчакли диван, ТВ — пастки деворда.</li>"
        "<li>Кириш зонаси: деворга ўрнатилган шкаф 185 см ва банкетка.</li><li>Эркерда — дераза олдида 2 кресло (дам олиш бурчаги).</li>"
        "<li>Ошхона — Г-шаклли, ювгич дераза олдида, холодильник бурчакда; меҳмонхонадан шиша тўсиқдаги сурилма эшик орқали.</li><li>Санузел эшиги ташқарига очилади.</li><li>Шкафлар чуқурлиги — 60 см.</li></ol>"))
    # 4 — электрика
    pages.append(sheet(4, T, "Электр: розетка ва ўчиргичлар", shell(light=True) + furniture().replace(FUR, "#d9c4ab") + electrics(),
        leg([(socket(0, 4, 1), "Розетка, пол сатҳидан 30 см (бошқача ёзилмаган бўлса)"), (socket(0, 4, 2), "Икки ўринли розетка"),
             (switch(-4, 0, 1), "Ўчиргич, 90 см"), (switch(-4, 0, 2), "Икки клавишали ўчиргич"),
             (text(0, 0, "110", 10, EL, weight=600), "Рақам — баландлик, см"), (text(0, 0, "IP44", 9, EL, weight=600), "Намликка чидамли")]),
        "<ol><li>Плита учун алоҳида линия 32 А, кабель 3×6 мм².</li><li>Ошхона ва санузел линиялари — ДИФ автомат (УЗО) орқали.</li>"
        "<li>ТВ ортида: 2 розетка + интернет (LAN) + ТВ кабели.</li><li>Кровать ёнида — розетка 75 см + USB.</li>"
        "<li>ЩР — электр шчити, кириш зонасида банкетка ёнида.</li></ol>"))
    # 5 — потолок и свет
    pages.append(sheet(5, T, "Шифт ва ёритиш", shell(light=True) + ceiling(),
        leg([(track(-15, 0, 15, 0), "Магнит трек-чироқлар"), (spot(0, 0), "Нуқтали чироқ (спот)"), (led(-15, 0, 15, 0), "LED лента (нишада)"),
             (pendant(0, 0, 7), "Осма қандил"), ('<rect x="-15" y="-6" width="30" height="12" fill="none" stroke="#7b5ea7" stroke-dasharray="5 2"/>', "Гипсокартон шифт чегараси"),
             ('<rect x="-14" y="-7" width="28" height="14" fill="#fff" stroke="#7b5ea7" rx="3"/>' + text(0, 0, "+270", 7, "#7b5ea7"), "Шифт баландлиги, см")]),
        "<ol><li>Меҳмонхона: периметр бўйлаб 30 см гипсокартон қути, ичида LED ёритиш; марказда трек-тизим.</li>"
        "<li>Овқатланиш столи устида — осма қандил, стол марказида.</li><li>Санузел — намликка чидамли гипсокартон, споты IP44.</li>"
        "<li>Ётоқхона: кровать устида ниша ва LED.</li></ol>"))
    # 6 — пол
    pages.append(sheet(6, T, "Пол қопламаси", shell() + floor() + room_labels(),
        leg([('<rect x="-15" y="-6" width="30" height="12" fill="#e9d9c3" stroke="#c9a77c"/>', "Ламинат / паркет (ёғоч рангли), «ёлка»"),
             ('<rect x="-15" y="-6" width="30" height="12" fill="#e7edf2" stroke="#8fa3b5"/>', "Кафель 60×60 (санузел)"),
             ('<rect x="-15" y="-6" width="30" height="12" fill="#e8ece8" stroke="#9aa59b"/>', "Керамогранит 120×60 (ошхона, кириш)")]),
        "<ol><li>Хоналар орасида пол бир сатҳда, бўсағасиз.</li><li>Санузелда пол 1–2 см паст, қия трапга қараб.</li>"
        "<li>Иссиқ пол — санузел ва ошхонада (тавсия).</li></ol>"))
    # 7 — эшик/дераза
    rows = [("Э-1", "Кириш эшиги (метал, иссиқлик сақловчи)", "100 × 210", "1"), ("Э-2", "Санузел эшиги (намликка чидамли)", "80 × 210", "1"),
            ("Э-3", "Болалар хонаси эшиги", "90 × 210", "1"), ("Э-4", "Ётоқхона эшиги", "90 × 210", "1"),
            ("Э-5", "Эркерга шиша эшик", "90 × 210", "1"), ("В-1/В-2", "Эшик ёнидаги шиша витраж", "55 × 210", "2"),
            ("Д-1", "Ётоқхона деразаси", "148 × ...", "1"), ("Д-2", "Ошхона деразаси", "150 × ...", "1"),
            ("П-1", "Ошхона — меҳмонхона шиша тўсиқ (сурилма эшик билан)", "292 × 280", "1")]
    tbl = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td><td>{d}</td></tr>" for a, b, c, d in rows)
    pages.append(f"""<section class="page"><svg class="frame" width="420mm" height="297mm" viewBox="0 0 420 297">
 <rect x="10" y="8" width="402" height="281" fill="none" stroke="#222" stroke-width="0.5"/><line x1="306" y1="8" x2="306" y2="289" stroke="#222" stroke-width="0.5"/></svg>
<div style="position:absolute;left:20mm;top:22mm"><h2 style="margin:0 0 6mm">Эшик ва деразалар жадвали</h2>
<table class="sch"><tr><th>Белги</th><th>Номи</th><th>Ўлчами (эн × баландлик), см</th><th>Сони</th></tr>{tbl}</table>
<p style="font-size:3.2mm;color:#555;margin-top:6mm">Деразалар баландлиги жойида ўлчанади («...»). Эшиклар баландлиги 210 см — шифт 280 бўлса яширин қутили 240 ҳам мумкин.</p></div>
<div class="tb"><div class="brand"><div class="logo">OZOD JAMOL</div><div class="sub">интерьер дизайн</div></div>
<div class="row"><b>Лойиҳа:</b> {TITLE}</div><div class="row big">Эшик ва деразалар</div>
<div class="foot"><div><b>Масштаб</b><br>—</div><div><b>Сана</b><br>31.10.2026</div><div><b>Варақ</b><br>7 / {T}</div></div>
<div class="test">СИНОВ НУСХАСИ · ички солиштириш учун</div></div></section>""")
    # 8 — общие примечания
    notes = ["Барча ўлчамлар сантиметрда. Ишни бошлашдан олдин ўлчамлар жойида текширилсин.",
             "Чизмалар орасида фарқ бўлса — дизайнер билан келишилсин, ўзбошимча ўзгартирилмасин.",
             "Электр кабеллари — мис, гофра ичида; розеткалар ерга уланган (3 симли).",
             "Ошхона ва санузел линиялари — алоҳида автомат ва ДИФ ҳимоя (30 мА).",
             "Гипсокартон шифт қутиларида LED лента учун профил ва трансформатор жойи қолдирилсин.",
             "Санузелда девор ва пол гидроизоляцияси — пол + девор 20 см, душ зонасида 200 см гача.",
             "Шкаф ва ошхона мебели — девор текисланиб, бўялгандан кейин ўлчаб буюртма қилинади.",
             "Ранглар ва материаллар — дизайн альбомидаги палитра бўйича."]
    nl = "".join(f"<li>{n}</li>" for n in notes)
    pages.append(f"""<section class="page"><svg class="frame" width="420mm" height="297mm" viewBox="0 0 420 297">
 <rect x="10" y="8" width="402" height="281" fill="none" stroke="#222" stroke-width="0.5"/><line x1="306" y1="8" x2="306" y2="289" stroke="#222" stroke-width="0.5"/></svg>
<div style="position:absolute;left:20mm;top:22mm;width:270mm"><h2 style="margin:0 0 6mm">Умумий изоҳлар қурувчилар учун</h2>
<ol style="font-size:4.2mm;line-height:1.9">{nl}</ol></div>
<div class="tb"><div class="brand"><div class="logo">OZOD JAMOL</div><div class="sub">интерьер дизайн</div></div>
<div class="row"><b>Лойиҳа:</b> {TITLE}</div><div class="row big">Умумий изоҳлар</div>
<div class="foot"><div><b>Масштаб</b><br>—</div><div><b>Сана</b><br>31.10.2026</div><div><b>Варақ</b><br>8 / {T}</div></div>
<div class="test">СИНОВ НУСХАСИ · ички солиштириш учун</div></div></section>""")
    html = f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{''.join(pages)}</body></html>"
    (OUT / "rabochka.html").write_text(html, encoding="utf-8")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page()
        pg.goto((OUT / "rabochka.html").as_uri()); pg.wait_for_timeout(500)
        pg.pdf(path=str(OUT / "OZOD_JAMOL_rabochka_TEST.pdf"), width="420mm", height="297mm", print_background=True)
        b.close()
    print("ok", OUT / "OZOD_JAMOL_rabochka_TEST.pdf")

if __name__ == "__main__":
    build()
