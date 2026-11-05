"""Новость «DIDI заходит в Узбекистан» — моушн под озвучку владельца. 1080x1920, 30 fps."""
import os, sys, math, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
DUR = 79.0
D = "/home/claude/didi"
F9 = "/home/claude/fnt/montserrat-900.ttf"
F8 = "/home/claude/fnt/montserrat-800.ttf"
RED = (255, 30, 50); ORA = (255, 122, 0); YEL = (255, 204, 0); GRN = (40, 220, 120)
WHITE = (255, 255, 255); GREY = (150, 160, 180); TG = (42, 171, 238)
_fc = {}
def font(sz, f=F9):
    k = (sz, f)
    if k not in _fc: _fc[k] = ImageFont.truetype(f, sz)
    return _fc[k]

# ---------- easing ----------
def cl(x, a=0., b=1.): return max(a, min(b, x))
def eo(t): t = cl(t); return 1 - (1 - t) ** 3
def eio(t): t = cl(t); return 3 * t * t - 2 * t * t * t
def back(t, s=1.7): t = cl(t) - 1; return t * t * ((s + 1) * t + s) + 1
def prog(t, a, d): return cl((t - a) / d)

# ---------- text ----------
_tc = {}
def text_img(txt, sz, fill=WHITE, f=F9, track=0, shadow=True, stroke=0):
    k = (txt, sz, fill, f, track, shadow, stroke)
    if k in _tc: return _tc[k]
    fo = font(sz, f)
    w = int(sum(fo.getlength(c) for c in txt) + track * len(txt)) + 40 + 2 * stroke
    asc, desc = fo.getmetrics()
    im = Image.new("RGBA", (w, asc + desc + 30), (0, 0, 0, 0)); d = ImageDraw.Draw(im); x = 20 + stroke
    for c in txt:
        d.text((x, 12), c, font=fo, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0)); x += fo.getlength(c) + track
    im = im.crop(im.getbbox()) if im.getbbox() else im
    if shadow:
        pad = 24; s = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
        a = Image.new("L", s.size, 0); a.paste(im.getchannel("A"), (pad, pad + 6))
        s.putalpha(a.filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * .75)))
        s.alpha_composite(im, (pad, pad)); im = s
    _tc[k] = im; return im

def fit(im, maxw):
    if im.width <= maxw: return im
    return im.resize((maxw, int(im.height * maxw / im.width)), Image.LANCZOS)

def place(cv, im, cx, cy, s=1., a=1., rot=0):
    if a <= 0.01 or s <= 0.01: return
    if s != 1: im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BILINEAR)
    if rot: im = im.rotate(rot, Image.BILINEAR, expand=True)
    if a < 1:
        im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    cv.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def rrect(w, h, r, fill, outline=None, ow=0, glow=None):
    pad = 40 if glow else 0
    im = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    if glow:
        g = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(g).rounded_rectangle([pad, pad, pad + w, pad + h], r, fill=glow)
        im.alpha_composite(g.filter(ImageFilter.GaussianBlur(22)))
    ImageDraw.Draw(im).rounded_rectangle([pad, pad, pad + w - 1, pad + h - 1], r, fill=fill, outline=outline, width=ow)
    return im

def card(lines, w, fill=(20, 26, 40, 235), outline=(255, 255, 255, 40), glow=None, padx=50, pady=40, gap=14):
    """lines: list of PIL images, stacked centered"""
    h = sum(l.height for l in lines) + gap * (len(lines) - 1) + 2 * pady
    c = rrect(w, h, 36, fill, outline, 3, glow); pad = 40 if glow else 0; y = pad + pady
    for l in lines:
        c.alpha_composite(l, (pad + (w - l.width) // 2, y)); y += l.height + gap
    return c

# ---------- icons ----------
def car_icon(w, color=ORA, sign=True):
    h = int(w * .62); im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    body_y = int(h * .42)
    d.rounded_rectangle([int(w * .2), int(h * .18), int(w * .8), int(h * .55)], int(w * .08), fill=color)       # cabin
    d.rounded_rectangle([int(w * .27), int(h * .25), int(w * .73), int(h * .45)], int(w * .04), fill=(20, 30, 45))  # windows
    d.line([w // 2, int(h * .25), w // 2, int(h * .45)], fill=color, width=max(2, w // 40))
    d.rounded_rectangle([int(w * .04), body_y, int(w * .96), int(h * .82)], int(w * .09), fill=color)          # body
    for cx in (.26, .74):
        d.ellipse([int(w * cx - w * .11), int(h * .66), int(w * cx + w * .11), int(h * .66 + w * .22)], fill=(15, 18, 25))
        d.ellipse([int(w * cx - w * .05), int(h * .66 + w * .06), int(w * cx + w * .05), int(h * .66 + w * .16)], fill=(90, 95, 110))
    d.ellipse([int(w * .07), int(h * .5), int(w * .17), int(h * .6)], fill=(255, 250, 210))
    d.ellipse([int(w * .83), int(h * .5), int(w * .93), int(h * .6)], fill=(255, 250, 210))
    if sign:
        d.rounded_rectangle([int(w * .38), 0, int(w * .62), int(h * .15)], 6, fill=WHITE)
        t = text_img("TAXI", max(10, int(w * .085)), (20, 20, 20), shadow=False)
        im.alpha_composite(t, (w // 2 - t.width // 2, max(0, int(h * .075) - t.height // 2)))
    return im

def check_icon(sz, color=GRN):
    im = Image.new("RGBA", (sz, sz), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([0, 0, sz - 1, sz - 1], fill=color)
    d.line([(sz * .27, sz * .52), (sz * .44, sz * .68), (sz * .75, sz * .34)], fill=WHITE, width=int(sz * .11), joint="curve")
    return im

def qmark_icon(sz, color=RED):
    im = Image.new("RGBA", (sz, sz), (0, 0, 0, 0)); ImageDraw.Draw(im).ellipse([0, 0, sz - 1, sz - 1], fill=color)
    t = text_img("?", int(sz * .7), WHITE, shadow=False); im.alpha_composite(t, (sz // 2 - t.width // 2, sz // 2 - t.height // 2)); return im

def warn_icon(sz, color=YEL):
    im = Image.new("RGBA", (sz, sz), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.polygon([(sz / 2, sz * .05), (sz * .97, sz * .92), (sz * .03, sz * .92)], fill=color)
    t = text_img("!", int(sz * .6), (20, 20, 20), shadow=False); im.alpha_composite(t, (sz // 2 - t.width // 2, int(sz * .58) - t.height // 2)); return im

def arrow_icon(sz, color, up=True):
    im = Image.new("RGBA", (sz, sz), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts = [(sz / 2, sz * .08), (sz * .92, sz * .55), (sz * .64, sz * .55), (sz * .64, sz * .94), (sz * .36, sz * .94), (sz * .36, sz * .55), (sz * .08, sz * .55)]
    d.polygon(pts, fill=color)
    return im if up else im.rotate(180)

def send_icon(sz):
    im = Image.new("RGBA", (sz, sz), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([0, 0, sz - 1, sz - 1], fill=TG)
    d.polygon([(sz * .22, sz * .5), (sz * .8, sz * .27), (sz * .62, sz * .78), (sz * .5, sz * .58)], fill=WHITE)
    d.polygon([(sz * .5, sz * .58), (sz * .8, sz * .27), (sz * .47, sz * .7)], fill=(200, 230, 250))
    return im

# ---------- map ----------
import geopandas as gpd
_world = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
def country_polys(name):
    g = _world[_world.name == name].geometry.iloc[0]
    geoms = list(g.geoms) if g.geom_type == "MultiPolygon" else [g]
    return [np.array(p.exterior.coords) for p in geoms]

def map_img(focus, others, box, w, hl=RED, hl_fill=(255, 30, 50, 70)):
    """box=(lon0,lon1,lat0,lat1) -> RGBA w x h"""
    lon0, lon1, lat0, lat1 = box; k = math.cos(math.radians((lat0 + lat1) / 2))
    sx = w / ((lon1 - lon0) * k); h = int((lat1 - lat0) * sx)
    S = 2; im = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    def P(a): return [((x - lon0) * k * sx * S, (lat1 - y) * sx * S) for x, y in a]
    for n in others:
        for p in country_polys(n): d.polygon(P(p), fill=(40, 48, 66, 255), outline=(80, 92, 118, 255))
    glow = Image.new("RGBA", im.size, (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
    for p in country_polys(focus): gd.line(P(p) + [P(p)[0]], fill=hl + (255,), width=18 * S)
    im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(14 * S)))
    for p in country_polys(focus): d.polygon(P(p), fill=(60, 18, 26, 255) if hl == RED else (70, 40, 10, 255)); d.line(P(p) + [P(p)[0]], fill=hl + (255,), width=5 * S)
    im = im.resize((w, h), Image.LANCZOS)
    yy_, xx_ = np.mgrid[0:h, 0:w].astype(np.float32)
    m = np.clip(np.minimum.reduce([xx_, w - 1 - xx_, yy_, h - 1 - yy_]) / 90, 0, 1) ** 1.5
    a = np.asarray(im.getchannel("A")).astype(np.float32) * m; im.putalpha(Image.fromarray(a.astype(np.uint8)))
    def proj(lon, lat): return ((lon - lon0) * k * sx, (lat1 - lat) * sx)
    return im, proj

CA = ["Kazakhstan", "Kyrgyzstan", "Tajikistan", "Turkmenistan", "Afghanistan", "China", "Iran", "Russia", "Mongolia"]
MAP_UZ, PROJ_UZ = map_img("Uzbekistan", [c for c in CA if c != "Uzbekistan"], (54, 84, 34, 47.5), 1000)
MAP_KZ, PROJ_KZ = map_img("Kazakhstan", ["Uzbekistan", "Kyrgyzstan", "Turkmenistan", "China", "Russia", "Mongolia", "Tajikistan"], (45, 90, 38, 56), 1000, hl=ORA)

# ---------- background ----------
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
base = np.zeros((H, W, 3), np.float32)
g = (yy / H)[..., None]
base[:] = (np.array([8, 10, 18]) * (1 - g) + np.array([16, 20, 34]) * g)
grid = ((xx % 60 < 2) | (yy % 60 < 2)).astype(np.float32)[..., None] * 7
BG = np.clip(base + grid, 0, 255)
vig = np.clip(1 - ((xx / W - .5) ** 2 + (yy / H - .45) ** 2 * .5) * 1.1, .35, 1)[..., None]
BG = (BG * vig).astype(np.uint8)
GLOW = {}
def glow_layer(color, r):
    k = (color, r)
    if k not in GLOW:
        s = 2 * r; y, x = np.mgrid[0:s, 0:s].astype(np.float32)
        a = np.clip(1 - np.sqrt((x - r) ** 2 + (y - r) ** 2) / r, 0, 1) ** 2 * 120
        im = np.zeros((s, s, 4), np.uint8); im[..., :3] = color; im[..., 3] = a.astype(np.uint8)
        GLOW[k] = Image.fromarray(im)
    return GLOW[k]

# ---------- subtitles ----------
SUBS = json.load(open(f"{D}/subs.json"))   # [[start,end,text],...]
def sub_at(t):
    for a, b, tx in SUBS:
        if a <= t < b: return a, tx
    return None

def render_sub(cv, t):
    s = sub_at(t)
    if not s: return
    a, tx = s; e = eo(prog(t, a, .18))
    words = tx.split(); lines = []; cur = ""
    for wd in words:
        test = (cur + " " + wd).strip()
        if font(58).getlength(test) > 900 and cur: lines.append(cur); cur = wd
        else: cur = test
    lines.append(cur)
    ims = []
    for ln in lines:
        hl = any(ch.isdigit() for ch in ln) or "DIDI" in ln.upper() or "YANDEX" in ln.upper()
        ims.append(text_img(ln, 58, YEL if hl else WHITE, shadow=False))
    w = max(i.width for i in ims) + 60; h = sum(i.height for i in ims) + 14 * (len(ims) - 1) + 40
    box = rrect(w, h, 22, (0, 0, 0, 170)); y = 20
    for i in ims: box.alpha_composite(i, ((w - i.width) // 2, y)); y += i.height + 14
    place(cv, box, W / 2, 1520 + 30 * (1 - e), 1, e)

# ---------- header ----------
HDR_TAG = None
def header(cv, t):
    pill = rrect(300, 70, 35, RED + (255,))
    tg = text_img("ЯНГИЛИК", 38, WHITE, shadow=False); pill.alpha_composite(tg, (150 - tg.width // 2 + 18, 35 - tg.height // 2))
    d = ImageDraw.Draw(pill); r = 9 + 3 * (math.sin(t * 6) > 0); d.ellipse([40 - r, 35 - r, 40 + r, 35 + r], fill=WHITE)
    cv.alpha_composite(pill, (60, 90))
    oj = text_img("OZOD JAMOL", 40, WHITE, track=4, shadow=False); cv.alpha_composite(oj, (W - 60 - oj.width, 125 - oj.height // 2))
    d = ImageDraw.Draw(cv); d.rectangle([60, 188, W - 60, 193], fill=(255, 255, 255, 40)); d.rectangle([60, 188, 60 + int((W - 120) * t / DUR), 193], fill=RED + (255,))

# ---------- scenes ----------
CY = 780   # центр сцены

def s1(cv, t):  # 0–4.2 хук
    e = eo(prog(t, 0, .6)); place(cv, MAP_UZ, W / 2, CY + 130, .92 + .08 * e, e)
    x0, y0 = PROJ_UZ(80, 41); x1, y1 = PROJ_UZ(66.5, 40.9)
    mx, my = W / 2 - MAP_UZ.width / 2, CY + 130 - MAP_UZ.height / 2
    k = eio(prog(t, .5, 2.2)); cx = mx + x0 + (x1 - x0) * k; cy = my + y0 + (y1 - y0) * k
    d = ImageDraw.Draw(cv)
    for i in range(14):
        kk = max(0, k - i * .025); px = mx + x0 + (x1 - x0) * kk; py = my + y0 + (y1 - y0) * kk
        rr = 10 - i * .6
        if rr > 1 and k > 0: d.ellipse([px - rr, py - rr, px + rr, py + rr], fill=ORA + (int(200 - i * 13),))
    if k > 0: place(cv, glow_layer(ORA, 150), cx, cy, 1, .9); place(cv, car_icon(170), cx, cy - 20, back(prog(t, .5, .5)))
    place(cv, text_img("ХИТОЙ ТАКСИСИ", 104, WHITE), W / 2, 380, back(prog(t, .15, .45)), eo(prog(t, .15, .3)))
    place(cv, fit(text_img("ЎЗБЕКИСТОНГА КИРМОҚДА", 76, RED), 980), W / 2, 495, 1, eo(prog(t, .55, .35)))
    if 2.6 < t: place(cv, text_img("ТОШКЕНТ", 34, WHITE), cx, cy + 75, 1, eo(prog(t, 2.6, .3)))

def s2(cv, t):  # 4.2–11
    lt = t - 4.2
    n = int(5000 * eio(prog(lt, 0, 1.8)))
    place(cv, text_img(f"{n:,}".replace(",", " "), 230, ORA), W / 2, 470, back(prog(lt, 0, .4)), eo(prog(lt, 0, .3)))
    place(cv, text_img("ТА МАШИНА", 84, WHITE), W / 2, 640, 1, eo(prog(lt, .3, .3)))
    ic = car_icon(78, ORA, sign=False)
    for i in range(40):
        r, c = divmod(i, 8); a = prog(lt, .4 + i * .035, .25)
        if a > 0: place(cv, ic, 160 + c * 108, 790 + r * 72, back(a), eo(a))
    if lt > 3.2:
        e = eo(prog(lt, 3.2, .45))
        cd = card([warn_icon(90), text_img("ШОШИЛМАНГ!", 72, YEL), fit(text_img("БОЗОР ҲАЛИ ЭГАЛЛАНМАДИ", 54, WHITE), 860)], 940,
                  fill=(40, 30, 6, 245), outline=YEL + (200,), glow=YEL + (90,))
        place(cv, cd, W / 2, 1050 + 120 * (1 - e), 1, e)

def s3(cv, t):  # 11–14.2
    lt = t - 11
    e = back(prog(lt, 0, .45)); place(cv, glow_layer(TG, 260), W / 2, 650, 1, eo(prog(lt, 0, .5)))
    fly = eio(prog(lt, 2.3, .8)); place(cv, send_icon(260), W / 2 + 600 * fly, 650 - 300 * fly, e * (1 - .4 * fly), 1 - fly)
    bub = card([fit(text_img("ТАКСИДА ИШЛАЙДИГАН", 62, WHITE), 860), fit(text_img("ТАНИШИНГИЗГА ЮБОРИНГ", 62, WHITE), 860)], 940,
               fill=TG + (240,), outline=None, glow=TG + (120,))
    place(cv, bub, W / 2, 1000, back(prog(lt, .35, .45)), eo(prog(lt, .35, .3)))

def doc_card(title, lines, w=900, hl=None):
    ims = [text_img(title, 46, RED)]
    bar = Image.new("RGBA", (w - 120, 6), (255, 255, 255, 40)); ims.append(bar)
    ims += lines
    return card(ims, w, fill=(245, 246, 250, 250), outline=None, glow=(255, 255, 255, 60), gap=22)

def s4(cv, t):  # 14.2–28
    lt = t - 14.2
    if lt < 4.8:
        e = eo(prog(lt, 0, .5))
        dc = doc_card("ТРАНСПОРТ ВАЗИРЛИГИ", [text_img("ХИТОЙНИНГ ЙИРИК", 58, (20, 24, 34), shadow=False),
                                              text_img("ТАКСИ КОМПАНИЯСИ", 58, (20, 24, 34), shadow=False),
                                              text_img("БОЗОРГА КИРАДИ", 58, ORA, shadow=False)])
        place(cv, dc, W / 2, 760 + 80 * (1 - e), 1, e * (1 - eo(prog(lt, 4.4, .4))))
    elif lt < 10.8:
        l2 = lt - 4.8; e = eo(prog(l2, 0, .5))
        place(cv, text_img("НОМИ РАСМАН АЙТИЛМАДИ", 56, GREY), W / 2, 420, 1, e)
        rev = eo(prog(l2, 2.0, .6))
        nm = text_img("DIDI TAXI MChJ", 70, ORA if rev > .5 else (200, 200, 210), shadow=False).copy()
        if rev < 1:
            dn = ImageDraw.Draw(nm); cw = int(nm.width * (1 - rev))
            dn.rounded_rectangle([nm.width - cw, 0, nm.width, nm.height], 10, fill=(30, 34, 46, 255))
        dc = doc_card("БИЗНЕС РЕЕСТР", [text_img("ТОШКЕНТ ВИЛОЯТИ", 50, (60, 66, 80), shadow=False), nm,
                                        text_img("РЎЙХАТДАН ЎТГАН", 46, (40, 160, 90), shadow=False)])
        place(cv, dc, W / 2, 800 + 80 * (1 - e), 1, e * (1 - eo(prog(l2, 5.6, .4))))
        if l2 > 2.4: place(cv, check_icon(110), W / 2 + 390, 650, back(prog(l2, 2.4, .4)))
    else:
        l3 = lt - 10.8
        place(cv, glow_layer(ORA, 420), W / 2, 700, 1, eo(prog(l3, 0, .5)))
        place(cv, text_img("DIDI", 330, ORA), W / 2, 700, back(prog(l3, 0, .5)) * (1 + .03 * l3), eo(prog(l3, 0, .3)))
        place(cv, fit(text_img("ХИТОЙДАГИ ЭНГ МАШҲУР", 60, WHITE), 960), W / 2, 960, 1, eo(prog(l3, .4, .3)))
        place(cv, text_img("ТАКСИ ГИГАНТИ", 76, YEL), W / 2, 1050, 1, eo(prog(l3, .7, .3)))

def s5(cv, t):  # 28–37
    lt = t - 28
    c1 = card([check_icon(120), text_img("5 000", 96, WHITE), text_img("МАШИНА", 50, GRN)], 450, fill=(10, 40, 26, 240), outline=GRN + (200,), glow=GRN + (70,))
    c2 = card([qmark_icon(120), text_img("ҲАЙДОВЧИ", 62, WHITE), text_img("АЙТИЛМАДИ", 46, RED)], 450, fill=(46, 10, 16, 240), outline=RED + (200,), glow=RED + (70,))
    place(cv, c1, 295 - 300 * (1 - eo(prog(lt, 0, .5))), 620, 1, eo(prog(lt, 0, .4)))
    place(cv, c2, 785 + 300 * (1 - eo(prog(lt, .6, .5))), 620, 1, eo(prog(lt, .6, .4)))
    if lt > 4:
        e = eo(prog(lt, 4, .45))
        cd = card([fit(text_img("КИМ ҲАЙДАЙДИ? ҚАНДАЙ ШАРТЛАРДА?", 46, GREY), 880), text_img("ҲАЛИ ОЧИҚЛАНМАГАН", 66, YEL)], 960,
                  fill=(26, 26, 10, 240), outline=YEL + (160,), glow=YEL + (60,))
        place(cv, cd, W / 2, 1040 + 100 * (1 - e), 1, e)

def s6(cv, t):  # 37–46
    lt = t - 37
    if lt < 5:
        n = int(570000 * eio(prog(lt, 0, 1.8)))
        place(cv, text_img(f"{n:,}+".replace(",", " "), 170, WHITE), W / 2, 560, back(prog(lt, 0, .4)), eo(prog(lt, 0, .3)))
        place(cv, text_img("ҲАЙДОВЧИ", 84, GRN), W / 2, 720, 1, eo(prog(lt, .4, .3)))
        place(cv, fit(text_img("АГРЕГАТОРЛАР ОРҚАЛИ ИШЛАЙДИ", 50, GREY), 960), W / 2, 820, 1, eo(prog(lt, .8, .3)))
    else:
        l2 = lt - 5; R = 300; cx, cy = W / 2, 720
        im = Image.new("RGBA", (2 * R + 80, 2 * R + 80), (0, 0, 0, 0)); d = ImageDraw.Draw(im); o = 40
        d.ellipse([o, o, o + 2 * R, o + 2 * R], outline=(70, 80, 105, 255), width=90)
        ang = 360 * .009 * eo(prog(l2, .3, .8)) * 4  # визуально увеличено ×4, иначе не видно
        if ang > 0: d.arc([o, o, o + 2 * R, o + 2 * R], -90, -90 + ang, fill=ORA + (255,), width=90)
        place(cv, im, cx, cy, back(prog(l2, 0, .4)), eo(prog(l2, 0, .3)))
        place(cv, text_img("0,9%", 150, ORA), cx, cy - 10, back(prog(l2, .6, .4)), eo(prog(l2, .6, .3)))
        place(cv, text_img("5 000 / 570 000", 46, GREY), cx, cy + 100, 1, eo(prog(l2, .9, .3)))
        place(cv, fit(text_img("АТИГИ 0,9 ФОИЗ", 66, WHITE), 900), W / 2, 1150, 1, eo(prog(l2, 1.1, .3)))

def s7(cv, t):  # 46–58.1
    lt = t - 46
    if lt < 2:
        place(cv, text_img("ЛЕКИН БУ", 90, WHITE), W / 2, 640, back(prog(lt, 0, .4)), eo(prog(lt, 0, .3)))
        place(cv, text_img("БАРИБИР МУҲИМ", 96, YEL), W / 2, 770, back(prog(lt, .3, .4)), eo(prog(lt, .3, .3)))
        return
    l2 = lt - 2
    # Yandex Go блок (слева / в центре до появления DIDI)
    didi_in = eo(prog(l2, 6.0, .6))
    yx = W / 2 - 280 * didi_in
    yb = card([text_img("YANDEX GO", 66, (20, 20, 20), shadow=False), text_img("ДЕЯРЛИ ЯККАҲОКИМ", 34, (60, 50, 0), shadow=False)], 470,
              fill=YEL + (250,), outline=None, glow=YEL + (90,))
    place(cv, yb, yx, 600, back(prog(l2, 0, .45)), eo(prog(l2, 0, .3)))
    if 3 < l2 < 6.2:
        a = eo(prog(l2, 3, .3)) * (1 - eo(prog(l2, 5.8, .3)))
        place(cv, card([text_img("УЗИЛИШЛАР", 60, WHITE)], 520, fill=(46, 10, 16, 240), outline=RED + (200,)), W / 2 - 110, 860, 1, a)
        place(cv, warn_icon(110, RED), W / 2 + 250, 860, back(prog(l2, 3, .4)), a)
        place(cv, card([text_img("НАРХЛАР", 60, WHITE)], 520, fill=(46, 10, 16, 240), outline=RED + (200,)), W / 2 - 110, 1030, 1, eo(prog(l2, 4.2, .3)) * (1 - eo(prog(l2, 5.8, .3))))
        place(cv, arrow_icon(110, RED, True), W / 2 + 250, 1030 - 20 * math.sin(l2 * 8), back(prog(l2, 4.2, .4)), (1 - eo(prog(l2, 5.8, .3))))
    if l2 > 6:
        db = card([text_img("DIDI", 72, WHITE, shadow=False), text_img("ЯНГИ РАҚИБ", 34, (255, 230, 200), shadow=False)], 470, fill=ORA + (250,), outline=None, glow=ORA + (90,))
        place(cv, db, W / 2 + 280 + 400 * (1 - didi_in), 600, 1, didi_in)
        vs = Image.new("RGBA", (110, 110), (0, 0, 0, 0)); ImageDraw.Draw(vs).ellipse([0, 0, 109, 109], fill=(15, 18, 28, 255), outline=WHITE + (255,), width=5)
        tv = text_img("VS", 44, WHITE, shadow=False); vs.alpha_composite(tv, (55 - tv.width // 2, 55 - tv.height // 2))
        place(cv, vs, W / 2, 600, back(prog(l2, 6.4, .4)))
        a = eo(prog(l2, 7, .4))
        place(cv, card([text_img("НАРХ", 70, WHITE)], 420, fill=(10, 40, 26, 240), outline=GRN + (200,), glow=GRN + (60,)), W / 2 - 240, 930, 1, a)
        place(cv, arrow_icon(130, GRN, False), W / 2 - 240, 1110 + 12 * math.sin(l2 * 6), back(prog(l2, 7, .4)), a)
        b = eo(prog(l2, 7.6, .4))
        place(cv, card([text_img("ХИЗМАТ", 70, WHITE)], 420, fill=(10, 40, 26, 240), outline=GRN + (200,), glow=GRN + (60,)), W / 2 + 240, 930, 1, b)
        place(cv, arrow_icon(130, GRN, True), W / 2 + 240, 1110 - 12 * math.sin(l2 * 6), back(prog(l2, 7.6, .4)), b)

def s8(cv, t):  # 58.1–72.1
    lt = t - 58.1
    if lt < 1.3:
        place(cv, text_img("ЭНДИ", 90, WHITE), W / 2, 640, back(prog(lt, 0, .35)))
        place(cv, fit(text_img("ВАЪДА ҚИЛИНГАН ГАП", 84, RED), 980), W / 2, 760, back(prog(lt, .2, .35)))
        return
    l2 = lt - 1.3
    if l2 < 9:
        e = eo(prog(l2, 0, .5)); mx, my = W / 2 - MAP_KZ.width / 2, 760 - MAP_KZ.height / 2
        place(cv, MAP_KZ, W / 2, 760, .94 + .06 * e, e)
        place(cv, text_img("ҚОЗОҒИСТОН", 70, ORA), W / 2, 420, 1, e)
        ax, ay = PROJ_KZ(76.9, 43.25)   # Алматы
        enter = eio(prog(l2, .5, 1.6)); leave = eio(prog(l2, 5.2, 1.8))
        sx0 = mx + PROJ_KZ(90, 44)[0]
        cx = sx0 + (mx + ax - sx0) * enter + (W + 200 - (mx + ax)) * leave; cy = my + ay - 20
        place(cv, glow_layer(ORA, 120), cx, cy, 1, .8 * (1 - leave)); place(cv, car_icon(150), cx, cy - 10, 1, 1 - leave * .3)
        # таймлайн
        d = ImageDraw.Draw(cv); y = 1120; x0, x1 = 160, W - 160
        d.rounded_rectangle([x0, y - 6, x1, y + 6], 6, fill=(70, 80, 105, 255))
        tp = eio(prog(l2, 1.8, 3.4)); d.rounded_rectangle([x0, y - 6, x0 + (x1 - x0) * tp, y + 6], 6, fill=ORA + (255,))
        for xx_, lab, at in [(x0, "2021 МАЙ", 1.2), (x1, "2022 МАРТ", 4.6)]:
            a = eo(prog(l2, at, .3)); d.ellipse([xx_ - 18, y - 18, xx_ + 18, y + 18], fill=ORA + (int(255 * a),))
            place(cv, text_img(lab, 44, WHITE), xx_, y + 70, 1, a)
        if l2 > 5.6:
            st = card([text_img("1 ЙИЛ ҲАМ", 64, WHITE), text_img("ИШЛАМАДИ", 74, WHITE)], 620, fill=RED + (235,), outline=WHITE + (220,))
            place(cv, st, W / 2, 760, 1.4 - .4 * back(prog(l2, 5.6, .35)), eo(prog(l2, 5.6, .2)), rot=-8)
    else:
        l3 = l2 - 9; e = eo(prog(l3, 0, .5))
        place(cv, MAP_UZ, W / 2, 760, 1, e * .9)
        place(cv, card([text_img("ЁҚМАСА —", 66, WHITE), fit(text_img("ЧИҚИБ КЕТИШИ МУМКИН", 64, YEL), 860)], 940, fill=(20, 22, 30, 235), outline=YEL + (160,), glow=YEL + (60,)),
              W / 2, 760, back(prog(l3, .3, .45)), eo(prog(l3, .3, .3)))

def s9(cv, t):  # 72.1–79
    lt = t - 72.1
    place(cv, text_img("СИЗ НИМА ДЕЙСИЗ?", 82, WHITE), W / 2, 420, back(prog(lt, 0, .4)), eo(prog(lt, 0, .3)))
    p = 1 + .03 * math.sin(lt * 5)
    b1 = card([text_img("А", 60, ORA), fit(text_img("ҚОЛАДИ ВА НАРХНИ ТУШИРАДИ", 50, WHITE), 820)], 920, fill=(40, 24, 8, 245), outline=ORA + (220,), glow=ORA + (70,))
    b2 = card([text_img("Б", 60, RED), fit(text_img("ҚОЗОҒИСТОНДАГИДЕК КЕТАДИ", 50, WHITE), 820)], 920, fill=(46, 10, 16, 245), outline=RED + (220,), glow=RED + (70,))
    place(cv, b1, W / 2 - 600 * (1 - eo(prog(lt, .8, .5))), 680, p, eo(prog(lt, .8, .4)))
    place(cv, b2, W / 2 + 600 * (1 - eo(prog(lt, 2.0, .5))), 960, p, eo(prog(lt, 2.0, .4)))
    if lt > 4.8:
        e = back(prog(lt, 4.8, .45))
        place(cv, text_img("ИЗОҲДА ЁЗИНГ", 86, YEL), W / 2, 1200, e)
        place(cv, arrow_icon(110, YEL, False), W / 2, 1320 + 18 * math.sin(lt * 7), e)

SCENES = [(0, 4.2, s1), (4.2, 11, s2), (11, 14.2, s3), (14.2, 28, s4), (28, 37, s5), (37, 46, s6), (46, 58.1, s7), (58.1, 72.1, s8), (72.1, 79.1, s9)]

def frame(n):
    t = n / FPS
    cv = Image.fromarray(BG).convert("RGBA")
    place(cv, glow_layer(RED, 520), W * (.5 + .3 * math.sin(t * .3)), 300 + 80 * math.sin(t * .23), 1, .35)
    for a, b, fn in SCENES:
        if a <= t < b:
            fade = min(eo(prog(t, a, .25)), 1 - eo(prog(t, b - .2, .2)) if fn is not s9 else 1)
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); fn(layer, t)
            if fade < 1: layer.putalpha(layer.getchannel("A").point(lambda v: int(v * fade)))
            cv.alpha_composite(layer)
    header(cv, t); render_sub(cv, t)
    return cv.convert("RGB")

if __name__ == "__main__":
    a, b = int(sys.argv[1]), int(sys.argv[2]); os.makedirs(f"{D}/fr", exist_ok=True)
    for n in range(a, b):
        frame(n).save(f"{D}/fr/{n:05d}.jpg", quality=92)
