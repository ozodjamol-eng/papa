"""Альбом дизайна офиса OZOD JAMOL: визуалы, план, электроплан, палитра, материалы → PDF + PNG страниц."""
from pathlib import Path
D = Path(__file__).parent
S = 120  # px на метр
OX, OY = 160, 110
W, L = 3.45, 3.90

def X(x): return OX + x * S
def Y(y): return OY + (L - y) * S

def rect(x0, y0, x1, y1, cls="", extra=""):
    return f'<rect x="{X(x0):.1f}" y="{Y(y1):.1f}" width="{(x1-x0)*S:.1f}" height="{(y1-y0)*S:.1f}" class="{cls}" {extra}/>'

def text(x, y, t, cls="lbl", anchor="middle"):
    return f'<text x="{X(x):.1f}" y="{Y(y):.1f}" class="{cls}" text-anchor="{anchor}" dominant-baseline="central">{t}</text>'

def base(furn=True):
    s = [rect(0, 0, W, L, "room")]
    # проёмы
    s.append(f'<line x1="{X(1.55)}" y1="{Y(L)}" x2="{X(2.78)}" y2="{Y(L)}" class="gap"/>')
    s.append(f'<line x1="{X(2.40)}" y1="{Y(0)}" x2="{X(3.34)}" y2="{Y(0)}" class="gap"/>')
    s.append(rect(1.55, L - 0.04, 2.78, L + 0.04, "door"))
    s.append(rect(2.40, -0.04, 3.34, 0.04, "door2"))
    # дуга открывания двери во 2-ю комнату
    s.append(f'<path d="M{X(2.46)} {Y(0)} A {0.82*S} {0.82*S} 0 0 0 {X(3.28)} {Y(0.82)}" class="swing"/>')
    s.append(f'<line x1="{X(3.28)}" y1="{Y(0)}" x2="{X(3.28)}" y2="{Y(0.82)}" class="swing"/>')
    if furn:
        s.append(rect(0.03, L - 0.06, 1.50, L, "slat"))
        s.append(rect(0.25, L - 0.42, 1.45, L - 0.06, "oak"))
        s.append(rect(0.06, 0.06, 0.96, 3.05, "sofa"))
        s.append(rect(0.96, 0.06, 2.20, 0.96, "sofa"))
        s.append(rect(1.25, 1.35, 1.85, 2.55, "oak"))
        s.append(rect(2.62, 1.55, 3.40, 2.35, "sofa"))
        s.append(rect(2.86, L - 0.22, 3.40, L, "ac"))
        s.append(f'<circle cx="{X(3.15)}" cy="{Y(3.15)}" r="20" class="plant"/>')
    return s

def dims():
    s = []
    def hdim(x0, x1, y, t, off):
        yy = Y(y) + off
        s.append(f'<line x1="{X(x0)}" y1="{yy}" x2="{X(x1)}" y2="{yy}" class="dim"/>')
        for xx in (x0, x1):
            s.append(f'<line x1="{X(xx)}" y1="{yy-7}" x2="{X(xx)}" y2="{yy+7}" class="dim"/>')
        s.append(f'<text x="{(X(x0)+X(x1))/2}" y="{yy-12 if off<0 else yy+20}" class="dimt" text-anchor="middle">{t}</text>')
    def vdim(y0, y1, x, t, off):
        xx = X(x) + off
        s.append(f'<line x1="{xx}" y1="{Y(y0)}" x2="{xx}" y2="{Y(y1)}" class="dim"/>')
        for yv in (y0, y1):
            s.append(f'<line x1="{xx-7}" y1="{Y(yv)}" x2="{xx+7}" y2="{Y(yv)}" class="dim"/>')
        s.append(f'<text x="{xx + (-14 if off<0 else 14)}" y="{(Y(y0)+Y(y1))/2}" class="dimt" text-anchor="{"end" if off<0 else "start"}" dominant-baseline="central">{t}</text>')
    hdim(0, W, L, "3,49 м", -62)
    hdim(1.55, 2.78, L, "1,23", -14)
    hdim(0, W, 0, "3,39 м", 38)
    hdim(2.40, 3.34, 0, "0,94", 14)
    vdim(0, L, 0, "3,95 м", -40)
    vdim(0, L, W, "3,87 м", 40)
    return s

def svg(body, h=700, w=760):
    return f'<svg viewBox="0 0 {w} {h}" class="plan">{"".join(body)}</svg>'

# ---------- стр.3 план
p3 = base() + dims()
p3 += [text(0.51, 1.6, "Бурчак", "lbl"), text(0.51, 1.42, "диван", "lbl"),
       text(1.55, 1.95, "Стол", "lbl"), text(3.01, 1.95, "Кресло", "lbl"),
       text(0.85, L - 0.62, "ТВ + тумба", "lbl"), text(2.165, L - 0.30, "Кириш", "lbl"),
       text(3.13, L - 0.45, "Конд.", "lbl"), text(2.87, 0.30, "2-хона", "lbl")]

# ---------- стр.4 электр
E = base()
# LED по периметру
inset = 0.10
E.append(f'<rect x="{X(inset)}" y="{Y(L-inset)}" width="{(W-2*inset)*S}" height="{(L-2*inset)*S}" class="led"/>')
E.append(f'<line x1="{X(0.05)}" y1="{Y(L-0.10)}" x2="{X(1.50)}" y2="{Y(L-0.10)}" class="led2"/>')
for sx, sy in ((0.9, 1.0), (0.9, 2.9), (2.5, 1.0), (2.5, 2.9), (1.7, 1.95)):
    E.append(f'<circle cx="{X(sx)}" cy="{Y(sy)}" r="11" class="spot"/><circle cx="{X(sx)}" cy="{Y(sy)}" r="4" class="spotc"/>')
def sock(x, y, n, side):
    dx, dy = {"n": (0, 18), "s": (0, -18), "w": (18, 0), "e": (-18, 0)}[side]
    cx, cy = X(x) + dx, Y(y) + dy
    return f'<circle cx="{cx}" cy="{cy}" r="14" class="sock"/><text x="{cx}" y="{cy}" class="sockt" text-anchor="middle" dominant-baseline="central">{n}</text>'
def sw(x, y, n, side):
    dx, dy = {"n": (0, 18), "s": (0, -18), "w": (18, 0), "e": (-18, 0)}[side]
    cx, cy = X(x) + dx, Y(y) + dy
    return f'<rect x="{cx-14}" y="{cy-14}" width="28" height="28" rx="4" class="sw"/><text x="{cx}" y="{cy}" class="swt" text-anchor="middle" dominant-baseline="central">{n}</text>'
E += [sock(0.85, L, "1", "n"), sock(0.45, L, "2", "n"), sock(0, 3.15, "3", "w"),
      sock(0, 0.45, "4", "w"), sock(W, 2.70, "5", "e"), sock(3.32, L, "6", "n"), sock(W, 0.75, "7", "e"),
      sw(2.95, L, "А", "n"), sw(2.25, 0, "Б", "s")]
E.append(f'<rect x="{X(0.55)}" y="{Y(L)+4}" width="26" height="12" class="fan"/>')

PAGE = """<section class="page">{c}<div class="foot"><b>OZOD JAMOL</b> · ДИЗАЙН</div></section>"""
pages = []
pages.append(PAGE.format(n=1, c=f'''<div class="cover"><img src="v1.png"/><div class="ct">
<div class="tag">ОФИС ДИЗАЙНИ</div><h1>ИЛИҚ<br/>МИНИМАЛИЗМ</h1>
<div class="meta">13,5 м² · 3,95 × 3,45 м · шифт 2,10 м</div></div></div>'''))
pages.append(PAGE.format(n=2, c=f'''<h2>ВИЗУАЛ</h2><div class="two wide"><img src="v2.png"/><div class="pts">
<p><b>1.</b> Деворлар — илиқ оқ, силлиқ</p><p><b>2.</b> ТВ девори — оч эман рейкалар</p>
<p><b>3.</b> Шифт бўйлаб илиқ LED ёруғлик</p><p><b>4.</b> Оч кулранг диван ва кресло</p>
<p><b>5.</b> Пол — оч эман ламинат</p><p><b>6.</b> Кириш — зиғир рулон парда</p><p class="warn">Бу расм — материал ва кайфият намунаси. Жиҳозлар жойи — 3-бетдаги режа бўйича</p></div></div>'''))
pages.append(PAGE.format(n=3, c=f'''<h2>ЎЛЧАМЛИ РЕЖА</h2><div class="two">{svg(p3)}<div class="pts">
<p><b>Хона:</b> 3,95 × 3,45 м (13,5 м²)</p><p><b>Шифт:</b> 2,10 м</p>
<p><b>Кириш эшиги:</b> 1,23 м</p><p><b>2-хона эшиги:</b> 0,94 м</p>
<p class="warn">Деворлар тўғри бурчак эмас — уста жойида қайта ўлчайди</p></div></div>'''))
pages.append(PAGE.format(n=4, c=f'''<h2>ЭЛЕКТР РЕЖАСИ</h2><div class="two">{svg(E)}<div class="pts tbl">
<p><span class="c">1</span><span class="tx">ТВ ортида: 2 розетка + интернет — <b>1,10 м</b><br/>экран ортида, сим кўринмайди</span></p>
<p><span class="c">2</span><span class="tx">Тумба: 2 розетка — <b>0,30 м</b><br/>роутер, приставка</span></p>
<p><span class="c">3</span><span class="tx">Диван боши: 2 розетка + USB — <b>0,75 м</b><br/>қўлтиқ устида: телефон, ноутбук</span></p>
<p><span class="c">4</span><span class="tx">Диван бурчаги: 1 розетка + USB — <b>0,90 м</b><br/>суянчиқдан баланд</span></p>
<p><span class="c">5</span><span class="tx">Съёмка: 2 розетка — <b>0,30 м</b><br/>диванга қарши: ҳалқа чироқ, камера</span></p>
<p><span class="c">6</span><span class="tx">Кондиционер — <b>2,00 м</b></span></p>
<p><span class="c">7</span><span class="tx">Хизмат (чангютгич) — <b>0,30 м</b></span></p>
<p><span class="s">А</span><span class="tx">Кириш: 3 клавиш — <b>0,90 м</b><br/>спот / LED / рейка</span></p>
<p><span class="s">Б</span><span class="tx">2-хона эшиги: 2 клавиш — <b>0,90 м</b><br/>спот / вытяжка, тутқич томонда</span></p>
<p><span class="sp"></span> Спот LED 7 Вт, 3000K — 5 дона</p>
<p><span class="ln"></span> LED тасма 2700K шифт бўйлаб</p></div></div>'''))
pal = [("Деворлар", "Илиқ оқ", "#F2EEE6"), ("Рейка, тумба", "Оч эман", "#C9A27C"), ("Пол", "Оч эман ламинат", "#D3B48C"),
       ("Диван, кресло", "Оч кулранг", "#BDBBB6"), ("Ёстиқлар", "Графит", "#5B5B5E"), ("Парда", "Зиғир", "#D8CCB6"),
       ("Ёруғлик", "2700–3000K", "#FFD39A"), ("Гул", "Яшил", "#4E6B3A")]
sw_html = "".join(f'<div class="swc"><div class="chip" style="background:{c}"></div><b>{a}</b><span>{b}</span><span class="hex">{c}</span></div>' for a, b, c in pal)
mat_rows = [("Ламинат 33 класс, оч эман", "15 м²"), ("Плинтус", "13 м"), ("Девор бўёғи, илиқ оқ, мат", "5 л (2 қават)"),
            ("Рейкали панел MDF, оч эман", "1,5 × 2,1 м"), ("Натяжной шифт, мат оқ", "13,5 м²"),
            ("LED тасма 2700K 24V + профил", "18 м"), ("Блок питания 24V 150 Вт", "2 дона"), ("Спот LED 7 Вт", "5 дона"),
            ("Розетка / USB / интернет", "11 / 2 / 1"), ("Ўчиргич 3 + 2 клавиш", "1 + 1"), ("Рулон парда, зиғир", "1,25 × 2,2 м")]
mt = "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in mat_rows)
pages.append(PAGE.format(n=5, c=f'''<h2>РАНГЛАР ВА МАТЕРИАЛЛАР</h2><div class="two"><div class="pal">{sw_html}</div>
<div><table>{mt}</table><p class="warn">Натяжной шифт 3–5 см пасайтиради — шифт 2,05 м бўлади</p></div></div>'''))

CSS = """
@page{size:1600px 1131px;margin:0}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter Display','Inter';font-weight:700;color:#1d1c1a;background:#fff}
.page{width:1600px;height:1131px;position:relative;padding:70px 80px;page-break-after:always;overflow:hidden;background:#FAF8F4}
h2{font-weight:900;font-size:64px;letter-spacing:1px;margin-bottom:34px}
.foot{position:absolute;bottom:34px;left:80px;font-size:22px;color:#8a8478}.foot b{color:#1d1c1a;font-weight:900}
.cover{position:absolute;inset:0}.cover img{width:100%;height:100%;object-fit:cover}
.ct{position:absolute;left:0;bottom:0;padding:60px 80px 90px;background:rgba(20,18,15,.72);color:#fff;width:100%}
.tag{font-size:30px;font-weight:800;letter-spacing:6px;color:#FFD39A}
h1{font-size:120px;font-weight:900;line-height:1;margin:10px 0 16px}.meta{font-size:34px;font-weight:800}
.two{display:grid;grid-template-columns:1.1fr 1fr;gap:50px;align-items:start}
.wide{grid-template-columns:1.9fr 1fr}.two img{width:100%;border-radius:14px}
.pts p{font-size:30px;margin:0 0 20px;line-height:1.25}.pts p b{font-weight:900}
.tx{display:block}.tbl p{font-size:22px;margin-bottom:10px;display:flex;align-items:center;gap:14px;line-height:1.2}
.c,.s{display:inline-flex;width:40px;height:40px;flex:none;align-items:center;justify-content:center;color:#fff;font-weight:900;font-size:22px}
.c{background:#C0392B;border-radius:50%}.s{background:#1F4E79;border-radius:6px}
.sp{width:40px;height:40px;flex:none;border-radius:50%;border:4px solid #E3A400;background:#fff3cc}
.ln{width:40px;height:0;flex:none;border-top:6px dashed #F0A030}
.warn{margin-top:26px;font-size:26px;font-weight:800;color:#A04000;background:#FFF0DE;padding:16px 20px;border-radius:10px}
.plan{width:100%;height:auto;background:#fff;border-radius:14px}
.room{fill:#fff;stroke:#1d1c1a;stroke-width:9}
.gap{stroke:#fff;stroke-width:12}
.door{fill:#7a4a2a}.door2{fill:#9aa3ad}.swing{fill:none;stroke:#9aa3ad;stroke-width:2;stroke-dasharray:6 5}
.slat{fill:#C9A27C}.oak{fill:#E6CFAF;stroke:#B48A5E;stroke-width:2}
.sofa{fill:#D9D7D2;stroke:#8f8c86;stroke-width:2}.ac{fill:#eef1f4;stroke:#7d8791;stroke-width:2}
.plant{fill:#9DBB7E;stroke:#4E6B3A;stroke-width:2}
.lbl{font-size:19px;font-weight:800;fill:#3a3833}
.dim{stroke:#C0392B;stroke-width:2}.dimt{font-size:21px;font-weight:900;fill:#C0392B}
.led{fill:none;stroke:#F0A030;stroke-width:5;stroke-dasharray:12 7}.led2{stroke:#F0A030;stroke-width:7}
.spot{fill:#fff3cc;stroke:#E3A400;stroke-width:4}.spotc{fill:#E3A400}
.sock{fill:#C0392B}.sockt{font-size:16px;font-weight:900;fill:#fff}
.sw{fill:#1F4E79}.swt{font-size:16px;font-weight:900;fill:#fff}.fan{fill:#fff;stroke:#555;stroke-width:2}
.pal{display:grid;grid-template-columns:1fr 1fr;gap:22px}
.swc{display:grid;grid-template-columns:90px 1fr;grid-template-rows:auto auto auto;column-gap:18px;font-size:24px}
.chip{grid-row:1/4;width:90px;height:90px;border-radius:12px;border:2px solid #d8d2c6}
.swc b{font-weight:900;font-size:25px}.swc span{color:#5a564e}.hex{font-size:19px}
table{width:100%;border-collapse:collapse;font-size:24px}
td{padding:12px 8px;border-bottom:2px solid #e6e0d4}td:last-child{text-align:right;font-weight:900;white-space:nowrap}
"""
html = f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{''.join(pages)}</body></html>"
(D / "album.html").write_text(html, encoding="utf-8")

from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1600, "height": 1131})
    pg.goto((D / "album.html").as_uri()); pg.wait_for_timeout(800)
    pg.pdf(path=str(D / "OZOD_JAMOL_ofis_dizayn.pdf"), width="1600px", height="1131px", print_background=True)
    for i, el in enumerate(pg.query_selector_all("section.page"), 1):
        el.screenshot(path=str(D / f"page{i}.png"))
    b.close()
print("ok")
