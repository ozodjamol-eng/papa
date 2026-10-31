"""Рабочие чертежи офиса OZOD JAMOL по стандарту Anoor (ALI HOMES rabochka).
ВАРАҚ 1 умумий жойлашув · 2 электр · 3 мебел ўлчамлари · 4 шифт + разрез · 5 ТВ девори ёйилмаси.
Комната 345×390 см (стены 349/339/395/387), потолок 210. y — от южной стены (дверь во 2-ю комнату)."""
from pathlib import Path
D = Path(__file__).parent
WC, LC, T = 345, 390, 22


class Plan:
    def __init__(self, K=2.05, OX=230, OY=175):
        self.K, self.OX, self.OY, self.o = K, OX, OY, []
    def X(self, x): return self.OX + x * self.K
    def Y(self, y): return self.OY + (LC - y) * self.K
    def A(self, s): self.o.append(s)
    def line(self, x0, y0, x1, y1, c): self.A(f'<line x1="{self.X(x0):.1f}" y1="{self.Y(y0):.1f}" x2="{self.X(x1):.1f}" y2="{self.Y(y1):.1f}" class="{c}"/>')
    def rect(self, x0, y0, x1, y1, c, rx=0): self.A(f'<rect x="{self.X(x0):.1f}" y="{self.Y(y1):.1f}" width="{(x1-x0)*self.K:.1f}" height="{(y1-y0)*self.K:.1f}" rx="{rx}" class="{c}"/>')
    def txt(self, x, y, t, c, a="middle"): self.A(f'<text x="{self.X(x):.1f}" y="{self.Y(y):.1f}" class="{c}" text-anchor="{a}" dominant-baseline="central">{t}</text>')
    def ptxt(self, px, py, lines, a="start", c="el"):
        for i, t in enumerate(lines):
            self.A(f'<text x="{px:.1f}" y="{py + i*19:.1f}" class="{c}" text-anchor="{a}">{t}</text>')

    def walls(self):
        K = self.K
        self.rect(-T, LC, WC + T, LC + T, "wall"); self.rect(-T, -T, WC + T, 0, "wall")
        self.rect(-T, -T, 0, LC + T, "wall"); self.rect(WC, -T, WC + T, LC + T, "wall")
        self.rect(155, LC - 1, 278, LC + T + 1, "open"); self.rect(240, -T - 1, 334, 1, "open")
        self.line(155, LC + T / 2, 278, LC + T / 2, "glass")
        for x in (155, 193, 278): self.line(x, LC, x, LC + T, "frame")
        self.A(f'<path d="M{self.X(205):.1f} {self.Y(LC):.1f} A {72*K:.1f} {72*K:.1f} 0 0 0 {self.X(277):.1f} {self.Y(LC-72):.1f}" class="swing"/>')
        self.line(277, LC, 277, LC - 72, "leaf")
        self.line(240, 0, 240, -T, "frame"); self.line(334, 0, 334, -T, "frame")
        self.A(f'<path d="M{self.X(246):.1f} {self.Y(0):.1f} A {82*K:.1f} {82*K:.1f} 0 0 1 {self.X(328):.1f} {self.Y(82):.1f}" class="swing"/>')
        self.line(328, 0, 328, 82, "leaf")

    def furniture(self, labels=True, faint=False):
        f, fi = ("furnf", "furnf") if faint else ("furn", "furnin")
        self.rect(4, LC - 6, 150, LC, "slat"); self.rect(25, LC - 40, 145, LC - 6, f); self.rect(30, LC - 9, 142, LC - 6, "tv")
        self.rect(6, 6, 96, 305, f, 4); self.rect(96, 6, 220, 96, f, 4)
        self.rect(6, 6, 28, 305, fi); self.rect(96, 6, 220, 28, fi)
        for cy in (60, 140, 220): self.rect(30, cy, 92, cy + 70, fi, 3)
        for cx in (110, 160): self.rect(cx, 30, cx + 45, 92, fi, 3)
        self.rect(136, 135, 191, 255, f, 3)
        self.rect(262, 155, 340, 235, f, 6); self.rect(318, 155, 340, 235, fi)
        self.rect(286, LC - 22, 340, LC, "acd"); self.rect(55, LC - 3, 77, LC, "fan")
        if labels:
            self.txt(60, 250, "Бурчак", "fl"); self.txt(60, 235, "диван", "fl")
            self.txt(163.5, 195, "Стол", "fl"); self.txt(290, 195, "Кресло", "fl")
            self.txt(313, LC - 30, "Кондиционер", "fl"); self.txt(85, LC - 28, "ТВ тумба", "fl")

    def dim(self, x0, y0, x1, y1, off, t=None, c="dn"):
        """размер: горизонтальный (y0==y1) или вертикальный (x0==x1); off в px"""
        if y0 == y1:
            yy = self.Y(y0) + off; a, b = self.X(x0), self.X(x1)
            self.A(f'<line x1="{a:.1f}" y1="{yy:.1f}" x2="{b:.1f}" y2="{yy:.1f}" class="dim"/>')
            for v in (a, b): self.A(f'<line x1="{v-5:.1f}" y1="{yy+5:.1f}" x2="{v+5:.1f}" y2="{yy-5:.1f}" class="dimt2"/>')
            self.A(f'<text x="{(a+b)/2:.1f}" y="{yy-7:.1f}" class="{c}" text-anchor="middle">{t or f"{abs(x1-x0):g}"}</text>')
        else:
            xx = self.X(x0) + off; a, b = self.Y(y0), self.Y(y1)
            self.A(f'<line x1="{xx:.1f}" y1="{a:.1f}" x2="{xx:.1f}" y2="{b:.1f}" class="dim"/>')
            for v in (a, b): self.A(f'<line x1="{xx-5:.1f}" y1="{v+5:.1f}" x2="{xx+5:.1f}" y2="{v-5:.1f}" class="dimt2"/>')
            m = (a + b) / 2
            self.A(f'<text x="{xx-8:.1f}" y="{m:.1f}" class="{c}" text-anchor="middle" transform="rotate(-90 {xx-8:.1f} {m:.1f})">{t or f"{abs(y1-y0):g}"}</text>')

    def overall(self):
        K = self.K
        for a, b in ((0, 155), (155, 278), (278, WC)): self.dim(a, LC, b, LC, -(T*K) - 30, c="dn2", t={155: "155", 278: "123", WC: "67"}[b])
        self.dim(0, LC, WC, LC, -(T*K) - 68, "349", c="dn2")
        for a, b in ((0, 240), (240, 334), (334, WC)): self.dim(a, 0, b, 0, T*K + 34, c="dn2", t={240: "240", 334: "94", WC: "11"}[b])
        self.dim(0, 0, WC, 0, T*K + 72, "339", c="dn2")
        self.dim(0, 0, 0, LC, -(T*K) - 36, "395", c="dn2")
        self.dim(WC, 0, WC, LC, (T*K) + 46, "387", c="dn2")

    def sym_sock(self, x, y, w):
        d = {"n": (0, 1), "s": (0, -1), "w": (1, 0), "e": (-1, 0)}[w]
        cx, cy = self.X(x) + d[0]*13, self.Y(y) + d[1]*13
        self.A(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="9" class="sock"/><line x1="{cx-d[1]*9:.1f}" y1="{cy-d[0]*9:.1f}" x2="{cx+d[1]*9:.1f}" y2="{cy+d[0]*9:.1f}" class="sockl"/>')
    def sym_sw(self, x, y, w):
        d = {"n": (0, 1), "s": (0, -1), "w": (1, 0), "e": (-1, 0)}[w]
        cx, cy = self.X(x) + d[0]*13, self.Y(y) + d[1]*13
        self.A(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="8" class="sw"/><line x1="{cx:.1f}" y1="{cy:.1f}" x2="{cx+11:.1f}" y2="{cy-11:.1f}" class="swl"/>')
    def svg(self): return "".join(self.o)


LEG = {
    "sock": '<svg width="40" height="26"><circle cx="20" cy="15" r="9" class="sock"/><line x1="11" y1="15" x2="29" y2="15" class="sockl"/></svg>Розетка',
    "sw": '<svg width="40" height="26"><circle cx="16" cy="15" r="8" class="sw"/><line x1="16" y1="15" x2="27" y2="4" class="swl"/></svg>Включатель',
    "glass": '<svg width="40" height="26"><line x1="4" y1="13" x2="36" y2="13" class="glass"/></svg>Ойна',
    "dim": '<svg width="40" height="26"><line x1="4" y1="13" x2="36" y2="13" class="dim"/></svg>Ўлчам, см',
    "slat": '<svg width="40" height="26"><rect x="4" y="8" width="32" height="10" class="slat"/></svg>Рейка + LED H=205 / H=5',
    "spot": '<svg width="40" height="26"><circle cx="20" cy="13" r="9" class="spot"/><circle cx="20" cy="13" r="3" class="spotc"/></svg>Спот LED 7 Вт, 3000K',
    "led": '<svg width="40" height="26"><line x1="4" y1="13" x2="36" y2="13" class="led"/></svg>LED тасма 2700K',
    "furn": '<svg width="40" height="26"><rect x="4" y="6" width="32" height="14" class="furn"/></svg>Мебел',
}

def title(name, scale, n, legend, notes):
    lg = "".join(f'<div class="lg">{LEG[k]}</div>' for k in legend)
    nt = "<br/>".join(f"{i}. {t}" for i, t in enumerate(notes, 1))
    return f"""<div class="tb"><div class="tb1">OZOD JAMOL<br/>ЧИЗМАСИ</div>
<div class="tbr">Офис · 13,5 м² · H=210</div><div class="tbr">{name} · {scale}</div>
<div class="tbh">Шартли белгилар</div>{lg}<div class="tbr sm">H — полдан баландлик, см</div>
<div class="tbsp"></div><div class="tbr sm">Дизайнер: Озод Жамол</div>
<div class="tbh">Эслатма</div><div class="tbr sm">{nt}</div><div class="tbn">ВАРАҚ {n}</div></div>"""

NOTE0 = "Ўлчамларни объектнинг ўзида текшириб олинсин."
sheets = []

# ===== ВАРАҚ 1 — умумий жойлашув
p = Plan(); p.walls(); p.furniture(); p.overall()
cx, cy = p.X(190), p.Y(300)
p.A(f'<circle cx="{cx}" cy="{cy}" r="34" class="num"/><text x="{cx}" y="{cy+2}" class="numt" text-anchor="middle" dominant-baseline="central">1</text>')
p.A(f'<text x="{cx}" y="{cy+56}" class="room" text-anchor="middle">ОФИС</text><text x="{cx}" y="{cy+80}" class="room2" text-anchor="middle">13,5 м²</text>')
p.ptxt(p.X(216), p.Y(LC) - 40, ["Кириш (кўча)"], "middle", "el")
p.txt(287, 112, "2-хонага эшик", "el")
sheets.append((p.svg(), title("Умумий жойлашув", "M 1:25", 1, ["glass", "furn", "dim", "slat"],
               [NOTE0, "Деворлар 90° эмас — бурчаклар жойида текширилсин."])))

# ===== ВАРАҚ 2 — электр
p = Plan(); p.walls(); p.furniture(labels=False, faint=True); p.overall()
p.sym_sock(85, LC, "n"); p.sym_sock(45, LC, "n"); p.dim(0, LC, 45, LC, 52); p.dim(45, LC, 85, LC, 52)
p.ptxt(p.X(30), p.Y(LC) + 92, ["Розетка 2x + интернет H=110", "Розетка 2x H=30 (тумба ичида)"])
p.sym_sock(0, 320, "w"); p.sym_sock(0, 45, "w"); p.dim(0, LC, 0, 320, 40); p.dim(0, 0, 0, 45, 40)
p.ptxt(p.X(0) + 52, p.Y(320) + 4, ["Розетка 2x + USB H=75"]); p.ptxt(p.X(0) + 52, p.Y(45) - 30, ["Розетка 1x + USB H=90"])
p.sym_sock(WC, 270, "e"); p.sym_sock(WC, 75, "e"); p.dim(WC, LC, WC, 270, -40); p.dim(WC, 0, WC, 75, -40)
p.ptxt(p.X(WC) - 52, p.Y(270) - 14, ["Розетка 2x H=30", "(съёмка: ҳалқа чироқ)"], "end")
p.ptxt(p.X(WC) - 52, p.Y(75) - 30, ["Розетка 1x H=30"], "end")
p.sym_sock(332, LC, "n"); p.dim(332, LC, WC, LC, 52); p.ptxt(p.X(WC) - 4, p.Y(LC) + 92, ["Розетка конд. H=200"], "end")
p.sym_sw(292, LC, "n"); p.dim(278, LC, 292, LC, 30); p.ptxt(p.X(292) - 6, p.Y(LC) + 128, ["Включатель 3 кл. H=90", "спот / LED / рейка"], "end")
p.sym_sw(225, 0, "s"); p.dim(225, 0, 240, 0, -30); p.ptxt(p.X(225) - 8, p.Y(0) - 56, ["Включатель 2 кл. H=90", "спот / вытяжка"], "end")
sheets.append((p.svg(), title("Электр чизмаси", "M 1:25", 2, ["sock", "sw", "glass", "dim", "slat"],
               [NOTE0, "Кабел фақат вертикал ва горизонтал ётқизилсин.", "Розетка 11, USB 2, интернет 1."])))

# ===== ВАРАҚ 3 — мебел ўлчамлари
p = Plan(); p.walls(); p.furniture(); p.overall()
p.dim(6, 305, 96, 305, -14, "90"); p.dim(96, 6, 96, 305, 14, "300")
p.dim(96, 96, 220, 96, -14, "124"); p.dim(220, 6, 220, 96, 14, "90")
p.dim(136, 255, 191, 255, -14, "55"); p.dim(191, 135, 191, 255, 14, "120")
p.dim(96, 195, 136, 195, 0, "40")
p.dim(262, 235, 340, 235, -14, "78"); p.dim(262, 155, 262, 235, -14, "80")
p.dim(191, 195, 262, 195, 0, "71")
p.dim(25, LC - 40, 145, LC - 40, 20, "120"); p.dim(145, LC - 40, 145, LC - 6, 14, "34")
sheets.append((p.svg(), title("Мебеллар ўлчамлари", "M 1:25", 3, ["furn", "dim", "slat"],
               [NOTE0, "ТВ 50\" (112 см), тумба осма H=28–55.", "Диван буюртмаси жойида ўлчангач берилсин.", "Ўтиш йўллари камида 70 см."])))

# ===== ВАРАҚ 4 — шифт чизмаси + разрез
p = Plan(K=1.75, OX=200, OY=110)
p.walls()
p.A(f'<rect x="{p.X(8):.1f}" y="{p.Y(LC-8):.1f}" width="{(WC-16)*p.K:.1f}" height="{(LC-16)*p.K:.1f}" class="led"/>')
spots = [(90, 100), (90, 290), (255, 100), (255, 290), (172, 195)]
for sx, sy in spots:
    p.A(f'<circle cx="{p.X(sx):.1f}" cy="{p.Y(sy):.1f}" r="11" class="spot"/><circle cx="{p.X(sx):.1f}" cy="{p.Y(sy):.1f}" r="4" class="spotc"/>')
p.dim(0, 290, 90, 290, -20); p.dim(90, 290, 255, 290, -20); p.dim(255, 290, WC, 290, -20)
p.dim(0, LC, 0, 290, 30); p.dim(0, 290, 0, 100, 30); p.dim(0, 100, 0, 0, 30)
p.dim(172, 195, WC, 195, 22, "173"); p.dim(172, 195, 172, 0, 22, "195")
p.ptxt(p.X(WC/2), p.Y(LC) + 46, ["LED тасма 2700K — парящий профил, периметр 14,5 м"], "middle")
# разрез А-А ниже плана
sx0, sy0 = 250, 900
p.A(f'<rect x="{sx0}" y="{sy0}" width="520" height="34" class="hatch"/>')
p.A(f'<rect x="{sx0}" y="{sy0}" width="34" height="150" class="hatch"/><rect x="{sx0+486}" y="{sy0}" width="34" height="150" class="hatch"/>')
p.A(f'<line x1="{sx0+34}" y1="{sy0+44}" x2="{sx0+486}" y2="{sy0+44}" class="ceil"/>')
p.A(f'<rect x="{sx0+34}" y="{sy0+34}" width="12" height="12" class="prof"/><rect x="{sx0+474}" y="{sy0+34}" width="12" height="12" class="prof"/>')
p.A(f'<line x1="{sx0+40}" y1="{sy0+46}" x2="{sx0+40}" y2="{sy0+70}" class="ledglow"/><line x1="{sx0+480}" y1="{sy0+46}" x2="{sx0+480}" y2="{sy0+70}" class="ledglow"/>')
p.A(f'<line x1="{sx0+560}" y1="{sy0+34}" x2="{sx0+560}" y2="{sy0+44}" class="dim"/><text x="{sx0+570}" y="{sy0+44}" class="dn">5</text>')
p.A(f'<text x="{sx0+260}" y="{sy0+76}" class="el" text-anchor="middle">Натяжной шифт (мат оқ) — H=205</text>')
p.A(f'<text x="{sx0+260}" y="{sy0+100}" class="el" text-anchor="middle">Парящий профил + LED (деворда)</text>')
p.A(f'<text x="{sx0+260}" y="{sy0-12}" class="room2" text-anchor="middle">Разрез А-А</text>')
sheets.append((p.svg(), title("Шифт чизмаси", "M 1:30", 4, ["spot", "led", "dim"],
               [NOTE0, "Натяжной шифт 5 см пасаяди: H=205.", "Спот трансформатори шифт ичида, очиладиган жойда."])))

# ===== ВАРАҚ 5 — ТВ девори ёйилмаси (север, вид изнутри)
K5, ex0, ey0 = 2.55, 180, 860   # ey0 — уровень пола
def EX(x): return ex0 + x * K5
def EY(h): return ey0 - h * K5
o = []
A = o.append
A(f'<rect x="{EX(0)}" y="{EY(210)}" width="{WC*K5}" height="{210*K5}" class="elev"/>')
A(f'<rect x="{EX(-10)}" y="{EY(0)}" width="{(WC+20)*K5}" height="12" class="hatch"/>')
A(f'<rect x="{EX(-10)}" y="{EY(218)}" width="{(WC+20)*K5}" height="20" class="hatch"/>')
for i in range(0, 146, 6):  # рейки
    A(f'<rect x="{EX(4+i)}" y="{EY(205)}" width="{3.6*K5}" height="{200*K5}" class="slatv"/>')
A(f'<line x1="{EX(4)}" y1="{EY(205)}" x2="{EX(150)}" y2="{EY(205)}" class="ledglow"/><line x1="{EX(4)}" y1="{EY(5)}" x2="{EX(150)}" y2="{EY(5)}" class="ledglow"/>')
A(f'<rect x="{EX(25)}" y="{EY(55)}" width="{120*K5}" height="{27*K5}" class="furn"/>')
A(f'<rect x="{EX(30)}" y="{EY(158)}" width="{112*K5}" height="{63*K5}" class="tvf"/>')
A(f'<rect x="{EX(155)}" y="{EY(202)}" width="{123*K5}" height="{202*K5}" class="doorf"/>')
A(f'<rect x="{EX(162)}" y="{EY(185)}" width="{30*K5}" height="{90*K5}" class="glassf"/><rect x="{EX(205)}" y="{EY(185)}" width="{65*K5}" height="{90*K5}" class="glassf"/>')
A(f'<rect x="{EX(162)}" y="{EY(198)}" width="{108*K5}" height="{9*K5}" class="glassf"/>')
A(f'<rect x="{EX(286)}" y="{EY(203)}" width="{54*K5}" height="{29*K5}" class="ac"/>')
A(f'<rect x="{EX(55)}" y="{EY(184)}" width="{22*K5}" height="{22*K5}" class="fanf"/>')
def esock(x, h, sw=False):
    if sw: A(f'<rect x="{EX(x)-9}" y="{EY(h)-9}" width="18" height="18" class="swe"/>')
    else: A(f'<rect x="{EX(x)-9}" y="{EY(h)-9}" width="18" height="18" class="socke"/><circle cx="{EX(x)}" cy="{EY(h)}" r="5" class="sockl2"/>')
def ehdim(x, h, side=1, t=None):
    xx = EX(x) + side * 26
    A(f'<line x1="{xx}" y1="{EY(0)}" x2="{xx}" y2="{EY(h)}" class="dim"/>')
    for v in (EY(0), EY(h)): A(f'<line x1="{xx-5}" y1="{v+5}" x2="{xx+5}" y2="{v-5}" class="dimt2"/>')
    m = (EY(0) + EY(h)) / 2
    A(f'<text x="{xx-7}" y="{m}" class="dn" text-anchor="middle" transform="rotate(-90 {xx-7} {m})">{t or h}</text>')
esock(85, 110); esock(45, 30); esock(332, 196); esock(292, 90, True)
ehdim(85, 110, -1); ehdim(45, 30, -1); ehdim(332, 196, -1); ehdim(292, 90, -1)
ehdim(142, 158, 1, "158"); ehdim(145, 55, 1, "55")
def ewdim(x0, x1, h, off, t=None):
    yy = EY(h) + off
    A(f'<line x1="{EX(x0)}" y1="{yy}" x2="{EX(x1)}" y2="{yy}" class="dim"/>')
    for v in (EX(x0), EX(x1)): A(f'<line x1="{v-5}" y1="{yy+5}" x2="{v+5}" y2="{yy-5}" class="dimt2"/>')
    A(f'<text x="{(EX(x0)+EX(x1))/2}" y="{yy-7}" class="dn2" text-anchor="middle">{t or f"{x1-x0:g}"}</text>')
for a, b in ((0, 4), (4, 150), (150, 155), (155, 278), (278, WC)): ewdim(a, b, 0, 44, None if b - a > 6 else "")
ewdim(0, WC, 0, 84, "349")
A(f'<text x="{EX(-14)}" y="{(EY(0)+EY(210))/2}" class="dn2" text-anchor="middle" transform="rotate(-90 {EX(-14)} {(EY(0)+EY(210))/2})">210</text>')
for t, x, h in (("Рейка оч эман + LED", 77, 194), ("ТВ 50\"", 86, 128), ("Тумба осма", 85, 42), ("Кириш эшиги", 216, 100), ("Конд.", 313, 188)):
    A(f'<text x="{EX(x)}" y="{EY(h)}" class="fl" text-anchor="middle">{t}</text>')
sheets.append(("".join(o), title("ТВ девори ёйилмаси", "M 1:20", 5, ["sock", "sw", "slat", "dim"],
               [NOTE0, "Розетка ва кабеллар рейка ўрнатилишидан олдин чиқарилсин.", "ТВ кронштейни учун девор мустаҳкамлансин."])))

CSS = (D / "cherteg.html").read_text(encoding="utf-8").split("<style>")[1].split("</style>")[0]
CSS += """
.furnf{fill:#fff;stroke:#c9b6a3;stroke-width:1.2}.num{fill:none;stroke:#f07a10;stroke-width:3}
.numt{font-size:40px;font-weight:900;fill:#f07a10}.room{font-size:22px;font-weight:900;fill:#f07a10}.room2{font-size:18px;font-weight:900;fill:#f07a10}
.spot{fill:#fff3cc;stroke:#e3a400;stroke-width:3}.spotc{fill:#e3a400}.led{fill:none;stroke:#f0a030;stroke-width:4;stroke-dasharray:12 7}
.hatch{fill:#cfcfcf;stroke:#666;stroke-width:1.5}.ceil{stroke:#111;stroke-width:3}.prof{fill:#888}.ledglow{stroke:#f0a030;stroke-width:5}
.elev{fill:#fbfaf7;stroke:#111;stroke-width:3}.slatv{fill:#d9b98f;stroke:#a77d50;stroke-width:.6}.tvf{fill:#222}
.doorf{fill:#6b4a2e}.glassf{fill:#d6eef8;stroke:#4a3020;stroke-width:1.5}.ac{fill:#fff;stroke:#555;stroke-width:2}.fanf{fill:#fff;stroke:#333;stroke-width:2}
.socke{fill:#fff;stroke:#d11;stroke-width:2.4}.sockl2{fill:none;stroke:#d11;stroke-width:2}.swe{fill:#fff;stroke:#1f4e79;stroke-width:3}
"""
pages = "".join(f'<div class="sheet"><svg class="draw" viewBox="0 0 1280 1125">{svg}</svg>{tb}</div>' for svg, tb in sheets)
html = f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}.sheet{{page-break-after:always}}</style></head><body>{pages}</body></html>'
(D / "sheets.html").write_text(html, encoding="utf-8")
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1600, "height": 1131})
    pg.goto((D / "sheets.html").as_uri()); pg.wait_for_timeout(600)
    pg.pdf(path=str(D / "sheets.pdf"), width="1600px", height="1131px", print_background=True)
    for i, el in enumerate(pg.query_selector_all("div.sheet"), 1):
        el.screenshot(path=str(D / f"varaq{i}.png"))
    b.close()
print("ok", len(sheets))
