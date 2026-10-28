"""«Тарих» №1 — как появился ИИ (OpenAI → Anthropic). Тёмный минимализм, Inter, пустые круглые рамки под фото.
Фото реальных людей владелец вставляет сам в CapCut — таблица рамок пишется в slots.json."""
import json, math, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 24
F = "/usr/share/fonts/opentype/inter/Inter-%s.otf"
_fc = {}
def font(w, s):
    k = (w, s)
    if k not in _fc: _fc[k] = ImageFont.truetype(F % w, s)
    return _fc[k]

WD = json.load(open("/home/claude/tarix/words.json"))
KEYS = [f"T{i:02d}" for i in range(1, 13)]
DUR = {k: float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                f"/home/claude/tarix/vo/{k}.mp3"], capture_output=True, text=True).stdout) for k in KEYS}
GAP, T0 = 0.35, 0.4
ST = {}; t = T0
for k in KEYS:
    ST[k] = t; t += DUR[k] + GAP
TOTAL = t + 0.6
def cue(p, i): return ST[KEYS[p]] + WD[KEYS[p]]["t"][i][0]
def pend(p): return ST[KEYS[p + 1]] if p + 1 < 12 else TOTAL

# цвета
BG = (10, 10, 13); WHITE = (244, 244, 246); GREY = (130, 132, 140); DIM = (60, 62, 70)
ORANGE = (255, 122, 48); PURPLE = (150, 92, 255); RED = (255, 64, 64); GREEN = (40, 214, 130)
BLUE = (64, 140, 255); TG = (42, 171, 238); CLAUDE = (217, 119, 87)

def eo(x): x = min(max(x, 0.0), 1.0); return 1 - (1 - x) ** 3
def eb(x):  # back-out
    x = min(max(x, 0.0), 1.0); c = 1.7; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2
def win(t, a, b, fi=0.3, fo=0.3):
    if t < a or t > b: return 0.0
    return min(1.0, (t - a) / fi if fi else 1, (b - t) / fo if fo else 1)

# ---------- спрайты ----------
_sc = {}
def txt_sprite(text, w, s, col, glow=0, spacing=0):
    k = ("t", text, w, s, col, glow, spacing)
    if k in _sc: return _sc[k]
    f = font(w, s)
    lines = text.split("\n")
    bbs = [f.getbbox(l) for l in lines]
    lh = int(s * 1.12)
    tw = max(b[2] - b[0] for b in bbs) + 2 * glow + 20; th = lh * len(lines) + 2 * glow + 20
    im = Image.new("RGBA", (tw, th), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for i, l in enumerate(lines):
        d.text((tw / 2, glow + 10 + lh * i + lh / 2), l, font=f, fill=col + (255,), anchor="mm")
    if glow:
        g = Image.new("RGBA", im.size, col + (0,)); g.putalpha(im.getchannel("A").point(lambda v: int(v * 0.75)))
        g = g.filter(ImageFilter.GaussianBlur(glow / 2.2))
        g.alpha_composite(im); im = g
    _sc[k] = im; return im

def place(img, spr, cx, cy, a=1.0, sc=1.0, rot=0):
    if a <= 0.003: return
    s = spr
    if sc != 1.0:
        s = s.resize((max(1, int(s.width * sc)), max(1, int(s.height * sc))), Image.BILINEAR)
    if rot: s = s.rotate(rot, expand=True, resample=Image.BICUBIC)
    if a < 1: s = s.copy(); s.putalpha(s.getchannel("A").point(lambda v: int(v * a)))
    img.alpha_composite(s, (int(cx - s.width / 2), int(cy - s.height / 2)))

def T(img, text, w, s, col, cx, cy, a=1.0, sc=1.0, glow=0, rot=0):
    place(img, txt_sprite(text, w, s, col, glow), cx, cy, a, sc, rot)

def pill_sprite(text, col, s=40, fill=None, tcol=None, w="SemiBold", pad=34):
    k = ("p", text, col, s, fill, tcol, w)
    if k in _sc: return _sc[k]
    f = font(w, s); b = f.getbbox(text); tw = b[2] - b[0] + pad * 2; th = int(s * 1.9)
    im = Image.new("RGBA", (tw + 8, th + 8), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    fl = fill if fill else col + (38,)
    d.rounded_rectangle((4, 4, tw + 4, th + 4), radius=th // 2, fill=fl, outline=col + (255,), width=3)
    d.text((tw / 2 + 4, th / 2 + 4), text, font=f, fill=(tcol or col) + (255,), anchor="mm")
    _sc[k] = im; return im

def P(img, text, col, cx, cy, a=1.0, sc=1.0, **kw):
    place(img, pill_sprite(text, col, **kw), cx, cy, a, sc)

def card_sprite(wd, ht, col=(28, 28, 34), out=(60, 62, 70), r=36):
    k = ("c", wd, ht, col, out, r)
    if k in _sc: return _sc[k]
    im = Image.new("RGBA", (wd + 80, ht + 80), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((40, 50, wd + 40, ht + 50), radius=r, fill=(0, 0, 0, 120)); im = im.filter(ImageFilter.GaussianBlur(14))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((40, 40, wd + 40, ht + 40), radius=r, fill=col + (255,), outline=out + (255,), width=2)
    _sc[k] = im; return im

# ---------- рамки под фото ----------
SLOTS = []
def slot_def(name, role, t_in, t_out, cx, cy, d, col):
    SLOTS.append(dict(name=name, role=role, t_in=round(t_in, 2), t_out=round(t_out, 2), cx=cx, cy=cy, d=d, col=col))

def slot_sprite(name, role, d, col):
    k = ("s", name, role, d, col)
    if k in _sc: return _sc[k]
    pad = 60; sz = d + 2 * pad
    im = Image.new("RGBA", (sz, sz + 170), (0, 0, 0, 0))
    g = Image.new("RGBA", im.size, (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
    gd.ellipse((pad - 10, pad - 10, pad + d + 10, pad + d + 10), outline=col + (150,), width=16)
    g = g.filter(ImageFilter.GaussianBlur(18)); im.alpha_composite(g)
    dr = ImageDraw.Draw(im)
    dr.ellipse((pad, pad, pad + d, pad + d), fill=(22, 22, 28, 255))
    dr.ellipse((pad - 7, pad - 7, pad + d + 7, pad + d + 7), outline=col + (255,), width=6)
    ini = "".join(w[0] for w in name.split()[:2]).upper()
    dr.text((sz / 2, pad + d / 2 - 14), ini, font=font("Bold", int(d * 0.26)), fill=(48, 48, 56, 255), anchor="mm")
    dr.text((sz / 2, pad + d / 2 + d * 0.2), "ФОТО", font=font("Medium", 26), fill=(70, 70, 80, 255), anchor="mm")
    dr.text((sz / 2, pad + d + 46), name, font=font("Bold", 46), fill=WHITE + (255,), anchor="mm")
    if role: dr.text((sz / 2, pad + d + 100), role, font=font("Medium", 32), fill=GREY + (255,), anchor="mm")
    _sc[k] = (im, pad); return _sc[k]

def draw_slot(img, t, s):
    a = win(t, s["t_in"], s["t_out"], 0.3, 0.35)
    if a <= 0: return
    im, pad = slot_sprite(s["name"], s["role"], s["d"], s["col"])
    if a < 1: im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    img.alpha_composite(im, (int(s["cx"] - s["d"] / 2 - pad), int(s["cy"] - s["d"] / 2 - pad)))

# ---------- фон ----------
yy, xx = np.mgrid[0:H, 0:W]
def glow_bg(col, cy=820, r=820, k=0.22):
    dist = np.sqrt((xx - W / 2) ** 2 + ((yy - cy) * 0.8) ** 2) / r
    g = np.clip(1 - dist, 0, 1) ** 2 * k
    base = np.array(BG, float)[None, None] + g[..., None] * (np.array(col, float) - np.array(BG, float))[None, None]
    return base
grid = np.zeros((H, W), bool); grid[::54, :] = True; grid[:, ::54] = True
SCOL = [ORANGE, WHITE, PURPLE, GREEN, ORANGE, RED, RED, ORANGE, GREEN, BLUE, CLAUDE, TG]
BGS = []
for c in SCOL:
    b = glow_bg(c); b[grid] += 7
    BGS.append(b)
rng = np.random.default_rng(3)
GRAIN = [rng.normal(0, 4.5, (H, W, 1)).astype(np.float32) for _ in range(6)]
VIG = (1 - 0.45 * np.clip(np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2) * 1.6 - 0.3, 0, 1))[..., None]

def scene_of(t):
    p = 0
    for i, k in enumerate(KEYS):
        if t >= ST[k] - GAP * 0.5: p = i
    return p

# ---------- вспышки ----------
FLASH = []  # (t0, t1, col, text, tcol)
def flash(t0, t1, col, text, tcol=(10, 10, 13)): FLASH.append((t0, t1, col, text, tcol))

# ---------- субтитры (настоящие названия брендов) ----------
DISP = {
    "T04": {"Оупен": "OpenAI.", "Эй": "", "Ай.": ""},
    "T05": {"Гуглдан": "Google'дан"},
    "T07": {"Майкрософтдан": "Microsoft'дан"},
    "T11": {"Антропик": "Anthropic", "Клодни": "Claude'ни"},
    "T12": {"Клодда": "Claude'да", "Телеграм": "Telegram"},
}
def disp_words(k):
    ws = list(WD[k]["words"]); out = []
    i = 0
    while i < len(ws):
        w = ws[i]
        if w == "Чат" and i + 1 < len(ws) and ws[i + 1].startswith("Жи-Пи-Ти"):
            out += ["ChatGPT" + ws[i + 1][len("Жи-Пи-Ти"):].replace("нинг", "'нинг"), ""]; i += 2; continue
        if w == "Жи-Пи-Ти" and i + 1 < len(ws) and ws[i + 1] in ("икки", "учни"):
            out += ["GPT-2" if ws[i + 1] == "икки" else "GPT-3'ни", ""]; i += 2; continue
        out.append(DISP.get(k, {}).get(w, w)); i += 1
    return out
SUB = []
for p, k in enumerate(KEYS):
    dw = disp_words(k); tm = WD[k]["t"]
    items = [(w, ST[k] + a, ST[k] + b) for w, (a, b) in zip(dw, tm) if w]
    chunk = []
    for it in items:
        chunk.append(it)
        if len(" ".join(x[0] for x in chunk)) > 18 or it[0][-1] in ".:!?»—,":
            SUB.append((chunk, p)); chunk = []
    if chunk: SUB.append((chunk, p))
SUBT = []
for i, (ch, p) in enumerate(SUB):
    a = ch[0][1]; b = ch[-1][2] + 0.25
    if i + 1 < len(SUB): b = min(b, SUB[i + 1][0][0][1])
    SUBT.append((a, b, ch, p))

def draw_sub(img, t):
    for a, b, ch, p in SUBT:
        if a - 0.05 <= t < b:
            acc = SCOL[p] if SCOL[p] != WHITE else ORANGE
            f = font("Bold", 62)
            words = [w for w, _, _ in ch]; widths = [f.getlength(w + " ") for w in words]
            x = W / 2 - sum(widths) / 2; y = 1640
            lay = Image.new("RGBA", (W, 160), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
            for (w, s0, s1), wd in zip(ch, widths):
                col = acc if s0 <= t < s1 + 0.08 else (WHITE if t >= s0 else (150, 150, 158))
                d.text((x + 3, 83), w, font=f, fill=(0, 0, 0, 200), anchor="lm")
                d.text((x, 80), w, font=f, fill=col + (255,), anchor="lm"); x += wd
            k = eo((t - a) / 0.15)
            if k < 1: lay.putalpha(lay.getchannel("A").point(lambda v: int(v * k)))
            img.alpha_composite(lay, (0, y - 80 + int((1 - k) * 18)))
            return

# ---------- значки ----------
def building(img, cx, cy, a, col, sc=1.0):
    if a <= 0: return
    lay = Image.new("RGBA", (400, 460), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rectangle((90, 60, 310, 440), fill=(26, 24, 36, 255), outline=col + (255,), width=5)
    for r in range(6):
        for c in range(3):
            d.rectangle((120 + c * 62, 95 + r * 55, 150 + c * 62, 125 + r * 55), fill=col + (200,))
    place(img, lay, cx, cy, a, sc)

def dots(img, t, cx, cy, n_c, n_r, step, r, col_fn, a):
    if a <= 0: return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    x0 = cx - (n_c - 1) * step / 2; y0 = cy - (n_r - 1) * step / 2
    for j in range(n_r):
        for i in range(n_c):
            c = col_fn(i, j)
            d.ellipse((x0 + i * step - r, y0 + j * step - r, x0 + i * step + r, y0 + j * step + r), fill=c)
    if a < 1: lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a)))
    img.alpha_composite(lay)

def plane(img, cx, cy, s, a):
    lay = Image.new("RGBA", (s * 2, s * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.ellipse((0, 0, s * 2 - 1, s * 2 - 1), fill=TG + (255,))
    k = s / 100
    d.polygon([(44 * k, 100 * k), (150 * k, 56 * k), (128 * k, 148 * k), (100 * k, 126 * k), (84 * k, 142 * k), (82 * k, 116 * k)], fill=(255, 255, 255, 255))
    d.polygon([(82 * k, 116 * k), (150 * k, 56 * k), (100 * k, 126 * k)], fill=(205, 230, 245, 255))
    place(img, lay, cx, cy, a)

def fmt(n): return f"{int(n):,}".replace(",", " ")

# ================= сцены =================
SC = []
def scene(p):
    def deco(fn): SC.append((p, fn)); return fn
    return deco

# P1 ---------------------------------------------------------------
@scene(0)
def s1(img, t):
    a = win(t, ST["T01"], pend(0), 0.3, 0.3)
    P(img, "ТАРИХ  ·  01", ORANGE, W / 2, 360, a * eo((t - ST["T01"]) / 0.4), s=36)
    full = "СУНЪИЙ\nИНТЕЛЛЕКТ"
    k = eo((t - cue(0, 3)) / (cue(0, 5) + 0.5 - cue(0, 3)))
    n = int(len(full) * k)
    if n:
        shown = full[:n]
        sp = txt_sprite(full, "Black", 128, WHITE)
        tmp = txt_sprite(shown + "\n" * (1 - shown.count("\n")), "Black", 128, WHITE)
        place(img, sp, W / 2, 760, a * 0.07)
        # печать по буквам — рисуем строками
        lines = shown.split("\n")
        for i, l in enumerate(lines):
            if l: T(img, l, "Black", 128, WHITE, W / 2 - (txt_sprite(full.split("\n")[i], "Black", 128, WHITE).width - txt_sprite(l, "Black", 128, WHITE).width) / 2, 690 + i * 143, a)
        if k < 1 and int(t * 4) % 2 == 0:
            T(img, "▍", "Black", 110, ORANGE, W / 2 + 330, 690 + (len(lines) - 1) * 143, a)
    q = eb((t - cue(0, 6)) / 0.45)
    if t > cue(0, 6):
        T(img, "қандай пайдо бўлган?", "Bold", 66, ORANGE, W / 2, 1010, a * min(1, q), 0.8 + 0.2 * q)
    if t > cue(0, 9):
        b = eo((t - cue(0, 9)) / 0.4)
        T(img, "Бу — бир", "Medium", 48, GREY, W / 2, 1160, a * b)
        T(img, "ТОРТИШУВДАН", "Black", 92, WHITE, W / 2, 1250, a * eb((t - cue(0, 12)) / 0.4), glow=0)
        T(img, "бошланган", "Medium", 48, GREY, W / 2, 1340, a * eo((t - cue(0, 13)) / 0.4))

# P2 ---------------------------------------------------------------
slot_def("Илон Маск", "", cue(1, 8), pend(1) - 0.1, 300, 900, 340, WHITE)
slot_def("Сэм Олтман", "", cue(1, 11), pend(1) - 0.1, 780, 900, 340, WHITE)
@scene(1)
def s2(img, t):
    a = win(t, ST["T02"], pend(1), 0.3, 0.3)
    P(img, "2015", ORANGE, W / 2, 380, a * eb((t - ST["T02"]) / 0.4), s=48, w="Bold")
    T(img, "Кремний водийси", "SemiBold", 54, WHITE, W / 2, 490, a * eo((t - cue(1, 2)) / 0.4))
    if t > cue(1, 4):
        k = eo((t - cue(1, 4)) / 0.6)
        lay = Image.new("RGBA", (W, 40), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        d.line((W / 2 - 420 * k, 20, W / 2 + 420 * k, 20), fill=DIM + (255,), width=3)
        place(img, lay, W / 2, 1290, a)
        T(img, "РЕСТОРАН  ·  ИККИ КИШИ", "SemiBold", 34, GREY, W / 2, 1345, a * k)

# P3 ---------------------------------------------------------------
@scene(2)
def s3(img, t):
    a = win(t, ST["T03"], pend(2), 0.3, 0.3)
    T(img, "ҚЎРҚУВ", "Black", 44, PURPLE, W / 2, 380, a * eo((t - ST["T03"]) / 0.4), glow=0)
    T(img, "бир нарса қўрқитади", "Medium", 46, GREY, W / 2, 450, a * eo((t - cue(2, 2)) / 0.4))
    tb = cue(2, 8)
    if t > tb:
        k = eb((t - tb) / 0.5)
        building(img, W / 2, 760, a, PURPLE, 0.6 + 0.4 * min(k, 1.1))
        P(img, "1 КОРПОРАЦИЯ", PURPLE, W / 2, 1020, a * min(1, k), s=40, w="Bold")
    th = cue(2, 13)
    def cf(i, j):
        if t < th: return DIM + (255,)
        d = math.hypot(i - 9, j - 2.5); k2 = eo((t - th) / 0.9 - d * 0.05)
        c = tuple(int(DIM[m] + (PURPLE[m] - DIM[m]) * k2) for m in range(3)); return c + (255,)
    dots(img, t, W / 2, 1250, 19, 6, 46, 9, cf, a * eo((t - cue(2, 12)) / 0.5))
    if t > cue(2, 15):
        T(img, "ҲОКИМИЯТ", "Black", 96, PURPLE, W / 2, 1470, a * eb((t - cue(2, 15)) / 0.4), glow=24)

# P4 ---------------------------------------------------------------
@scene(3)
def s4(img, t):
    a = win(t, ST["T04"], pend(3), 0.3, 0.3)
    s = ST["T04"]
    def cf(i, j):
        k2 = eo((t - s) / 0.8 - (i + j) * 0.03)
        c = tuple(int(PURPLE[m] + (GREEN[m] - PURPLE[m]) * k2) for m in range(3)); return c + (255,)
    dots(img, t, W / 2, 560, 19, 6, 46, 9, cf, a)
    T(img, "бутун инсоният учун", "SemiBold", 50, WHITE, W / 2, 820, a * eo((t - cue(3, 3)) / 0.4))
    if t > cue(3, 6):
        P(img, "ОЧИҚ ЛАБОРАТОРИЯ", GREEN, W / 2, 930, a * eb((t - cue(3, 6)) / 0.4), s=42, w="Bold")
    if t > cue(3, 11):
        k = eb((t - cue(3, 11)) / 0.5)
        T(img, "OpenAI", "Bold", 170, WHITE, W / 2, 1180, a * min(1, k), 0.7 + 0.3 * k, glow=30)
        T(img, "нотижорат  ·  2015", "Medium", 40, GREY, W / 2, 1320, a * eo((t - cue(3, 11) - 0.4) / 0.4))

# P5 ---------------------------------------------------------------
slot_def("Илья Суцкевер", "Google'дан олим", cue(4, 3), pend(4) - 0.1, 300, 820, 320, WHITE)
slot_def("Дарио Амодеи", "", cue(4, 10), pend(4) - 0.1, 780, 820, 320, ORANGE)
@scene(4)
def s5(img, t):
    a = win(t, ST["T05"], pend(4), 0.3, 0.3)
    P(img, "OpenAI  командаси", WHITE, W / 2, 400, a * eo((t - ST["T05"]) / 0.4), s=38)
    if t > cue(4, 12):
        k = eb((t - cue(4, 12)) / 0.35)
        P(img, "БУ ИСМНИ ЭСЛАБ ҚОЛИНГ", ORANGE, W / 2, 1290, a * min(1, k), 0.6 + 0.4 * k, s=46, w="Black",
          fill=ORANGE + (255,), tcol=BG)
        # стрелка к Дарио
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        kk = eo((t - cue(4, 12) - 0.2) / 0.4)
        d.line((780, 1240, 780, 1240 - 90 * kk), fill=ORANGE + (255,), width=6)
        if kk > 0.9: d.polygon([(760, 1160), (800, 1160), (780, 1135)], fill=ORANGE + (255,))
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a))); img.alpha_composite(lay)

# P6 ---------------------------------------------------------------
slot_def("Илон Маск", "", ST["T06"] + 0.05, cue(5, 12) + 0.6, 540, 640, 360, WHITE)
@scene(5)
def s6(img, t):
    a = win(t, ST["T06"], pend(5), 0.3, 0.3)
    T(img, "ШАРТ", "Black", 44, RED, W / 2, 340, a * eo((t - cue(5, 1)) / 0.4))
    if t > cue(5, 3):
        k = eb((t - cue(5, 3)) / 0.45)
        place(img, card_sprite(880, 250), W / 2, 1110, a * min(1, k), 0.85 + 0.15 * k)
        T(img, "«Акцияларнинг кўпи ва\nраҳбарлик — меники»", "SemiBold", 50, WHITE, W / 2, 1110, a * min(1, k), 0.85 + 0.15 * k)
    if t > cue(5, 10):
        k = eb((t - cue(5, 10)) / 0.3)
        P(img, "ЙЎҚ", RED, W / 2 + 300, 945, a * min(1, k), 1.6 - 0.6 * min(k, 1), s=70, w="Black", fill=RED + (255,), tcol=WHITE)
    if t > cue(5, 12):
        T(img, "Маск кетади  →", "Bold", 58, GREY, W / 2, 1360, a * eo((t - cue(5, 12)) / 0.4))

# P7 ---------------------------------------------------------------
flash(ST["T07"] - 0.1, ST["T07"] + 1.0, RED, "ПУЛ ЙЎҚ", WHITE)
@scene(6)
def s7(img, t):
    a = win(t, ST["T07"], pend(6), 0.3, 0.3)
    tq = cue(6, 3)
    if t > tq:
        k = eo((t - tq) / 0.4)
        T(img, "«инсоният учун»", "SemiBold", 60, WHITE, W / 2, 560, a * k)
        tm = cue(6, 6)
        if t > tm:  # зачёркиваем
            kk = eo((t - tm) / 0.5)
            lay = Image.new("RGBA", (W, 60), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
            d.line((W / 2 - 260, 30, W / 2 - 260 + 520 * kk, 30), fill=RED + (255,), width=8)
            place(img, lay, W / 2, 565, a)
    tm = cue(6, 6)
    if t > tm:
        P(img, "Microsoft", WHITE, W / 2, 800, a * eb((t - tm) / 0.4), s=48, w="Bold")
    t1, t2 = cue(6, 7), cue(6, 9) + 0.5
    k = eo((t - t1) / (t2 - t1)) if t > t1 else 0
    val = 1_000_000_000 * k
    if t > ST["T07"] + 0.9:
        T(img, "$" + fmt(val), "Black", 104, GREEN if k >= 1 else WHITE, W / 2, 1060, a, glow=26 if k >= 1 else 0)
        T(img, "бир миллиард доллар", "Medium", 44, GREY, W / 2, 1180, a * eo((t - t1) / 0.4))

# P8 ---------------------------------------------------------------
tf8 = cue(7, 14) - 0.12
slot_def("Дарио Амодеи", "", ST["T08"] + 0.05, tf8, 540, 600, 340, ORANGE)
flash(tf8, pend(7) + 0.05, ORANGE, "ВА У\nКЕТАДИ")
@scene(7)
def s8(img, t):
    a = win(t, ST["T08"], pend(7), 0.3, 0.3)
    if t > cue(7, 1):
        P(img, "GPT-2", WHITE, W / 2 - 160, 930, a * eb((t - cue(7, 1)) / 0.4), s=48, w="Bold")
    if t > cue(7, 4):
        P(img, "GPT-3", WHITE, W / 2 + 160, 930, a * eb((t - cue(7, 4)) / 0.4), s=48, w="Bold")
    t1 = cue(7, 8)
    if t > t1 - 0.3:
        k = eo((t - t1) / 1.6) if t > t1 else 0
        aa = a * eo((t - t1 + 0.3) / 0.3)
        T(img, "ХАВФСИЗЛИК", "Bold", 40, GREY, W / 2, 1090, aa)
        lay = Image.new("RGBA", (W, 80), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        d.rounded_rectangle((140, 20, 940, 60), radius=20, outline=DIM + (255,), width=3)
        lv = 1 - 0.82 * k; c = tuple(int(GREEN[m] + (RED[m] - GREEN[m]) * k) for m in range(3))
        d.rounded_rectangle((146, 26, 146 + 788 * lv, 54), radius=14, fill=c + (255,))
        place(img, lay, W / 2, 1160, aa)
        T(img, f"{int(100 * lv)}%", "Black", 60, c, W / 2, 1260, aa)

# P9 ---------------------------------------------------------------
@scene(8)
def s9(img, t):
    a = win(t, ST["T09"], pend(8), 0.3, 0.3)
    s = ST["T09"]
    place(img, card_sprite(520, 140), W / 2, 420, a * eb((t - s) / 0.4))
    T(img, "30.11.2022", "Bold", 64, WHITE, W / 2, 420, a * eo((t - s) / 0.4))
    if t > cue(8, 4):
        k = eb((t - cue(8, 4)) / 0.5)
        T(img, "ChatGPT", "Black", 160, GREEN, W / 2, 720, a * min(1, k), 0.7 + 0.3 * k, glow=34)
        T(img, "чиқади", "Medium", 46, GREY, W / 2, 850, a * eo((t - cue(8, 6)) / 0.4))
    t1 = cue(8, 7); t2 = ST["T09"] + DUR["T09"] - 0.2
    if t > t1:
        k = eo((t - t1) / (t2 - t1))
        T(img, fmt(1_000_000 * k), "Black", 130, WHITE, W / 2, 1080, a, glow=20 if k >= 1 else 0)
        T(img, "одам", "SemiBold", 48, GREY, W / 2, 1190, a)
        P(img, "5 КУНДА", GREEN, W / 2, 1310, a * eb((t - t1) / 0.4), s=44, w="Bold")

# P10 --------------------------------------------------------------
tf10 = cue(9, 16) - 0.05
slot_def("Сэм Олтман", "", ST["T10"] + 0.05, tf10, 540, 520, 300, BLUE)
flash(tf10, pend(9) + 0.05, BLUE, "ЯНА\nРАҲБАР", WHITE)
@scene(9)
def s10(img, t):
    a = win(t, ST["T10"], pend(9), 0.3, 0.3)
    P(img, "1 ЙИЛДАН КЕЙИН", BLUE, W / 2, 300, a * eo((t - ST["T10"]) / 0.4), s=36)
    t1 = cue(9, 4); t2 = cue(9, 6)
    ka = win(t, t1, t2 + 0.1, 0.35, 0.3)
    if ka > 0:
        k = eb((t - t1) / 0.4)
        place(img, card_sprite(820, 220, (40, 18, 20), RED), W / 2, 980, a * ka, 0.85 + 0.15 * min(k, 1))
        T(img, "⚠  Сиз ишдан\nбўшатилдингиз", "Bold", 56, (255, 200, 200), W / 2, 980, a * ka, 0.85 + 0.15 * min(k, 1))
    if t > t2:
        b = a * eo((t - t2) / 0.4)
        tc = cue(9, 9); kc = eo((t - tc) / 1.3) if t > tc else 0
        n = int(745 * kc)
        T(img, f"{n}", "Black", 120, BLUE, W / 2 - 110, 860, b, glow=18 if kc >= 1 else 0)
        T(img, "/ 770", "Bold", 70, GREY, W / 2 + 150, 875, b)
        T(img, "ходим", "Medium", 40, GREY, W / 2, 950, b)
        def cf(i, j):
            idx = j * 35 + i
            return (BLUE + (255,)) if idx < n else (DIM + (255,))
        dots(img, t, W / 2, 1215, 35, 22, 21, 6, cf, b)
        if t > cue(9, 11):
            T(img, "«Сэмни қайтаринг!»", "Bold", 60, WHITE, W / 2, 1500, b * eb((t - cue(9, 11)) / 0.4))

# P11 --------------------------------------------------------------
slot_def("Дарио Амодеи", "", ST["T11"] + 0.05, pend(10) - 0.1, 540, 500, 300, CLAUDE)
@scene(10)
def s11(img, t):
    a = win(t, ST["T11"], pend(10), 0.3, 0.3)
    if t > cue(10, 4):
        P(img, "Anthropic", CLAUDE, W / 2, 830, a * eb((t - cue(10, 4)) / 0.4), s=46, w="Bold")
    if t > cue(10, 7):
        k = eb((t - cue(10, 7)) / 0.5)
        T(img, "Claude", "Black", 190, CLAUDE, W / 2, 1040, a * min(1, k), 0.7 + 0.3 * k, glow=40)
    if t > cue(10, 10):
        b = a * eo((t - cue(10, 10)) / 0.4)
        T(img, "ChatGPT", "Bold", 60, GREEN, W / 2 - 250, 1290, b)
        T(img, "VS", "Black", 50, GREY, W / 2, 1290, b)
        T(img, "Claude", "Bold", 60, CLAUDE, W / 2 + 240, 1290, b)
        T(img, "асосий рақиб", "Medium", 42, GREY, W / 2, 1380, a * eo((t - cue(10, 15)) / 0.4))

# P12 --------------------------------------------------------------
@scene(11)
def s12(img, t):
    a = win(t, ST["T12"], TOTAL, 0.3, 0.6)
    tc = cue(11, 9)
    a1 = a * win(t, ST["T12"], tc, 0.3, 0.3)
    if a1 > 0:
        T(img, "ChatGPT'нинг", "Bold", 64, GREEN, W / 2, 620, a1 * eo((t - ST["T12"]) / 0.4))
        T(img, "миясини қурган одам", "Bold", 64, WHITE, W / 2, 710, a1 * eo((t - cue(11, 2)) / 0.4))
        if t > cue(11, 6):
            T(img, "унга РАҚИБ", "Black", 110, CLAUDE, W / 2, 900, a1 * eb((t - cue(11, 6)) / 0.4), glow=30)
            T(img, "яратди", "Bold", 64, WHITE, W / 2, 1020, a1 * eo((t - cue(11, 8)) / 0.4))
    if t > tc:
        b = a * eo((t - tc) / 0.45)
        T(img, "Мен Claude'да нималар", "SemiBold", 52, WHITE, W / 2, 520, b)
        T(img, "қураётганимни", "SemiBold", 52, WHITE, W / 2, 590, b)
        tt = cue(11, 15)
        if t > tt:
            k = eb((t - tt) / 0.5)
            plane(img, W / 2, 860, int(120 * min(k, 1.05)) + 1, a * min(1, k))
            T(img, "@Ozodjamol", "Black", 96, WHITE, W / 2, 1080, a * eo((t - tt) / 0.4), glow=0)
            T(img, "Telegram каналимда", "Medium", 44, GREY, W / 2, 1170, a * eo((t - tt) / 0.4))
        tb = cue(11, 18)
        if t > tb:
            k = eb((t - tb) / 0.4); pul = 1 + 0.04 * math.sin((t - tb) * 7)
            P(img, "ОБУНА БЎЛИНГ", TG, W / 2, 1340, a * min(1, k), (0.7 + 0.3 * min(k, 1.1)) * pul, s=54, w="Black",
              fill=TG + (255,), tcol=WHITE, pad=56)

def draw_flash(img, t):
    for t0, t1, col, text, tcol in FLASH:
        if t0 <= t < t1:
            a = min(1, (t - t0) / 0.07, (t1 - t) / 0.22)
            lay = Image.new("RGBA", (W, H), col + (int(255 * a),)); img.alpha_composite(lay)
            k = eb((t - t0) / 0.35)
            T(img, text, "Black", 170, tcol, W / 2, H / 2 - 60, a, 0.8 + 0.2 * k)

# ================= рендер =================
def main():
    json.dump(dict(TOTAL=TOTAL, ST=ST, SLOTS=SLOTS, FLASH=[f[:2] for f in FLASH],
                   POPS=[s["t_in"] for s in SLOTS]), open("/home/claude/tarix/timeline.json", "w"), ensure_ascii=False, indent=1)
    N = int(TOTAL * FPS)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                            "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p",
                            "/home/claude/tarix/video.mp4"], stdin=subprocess.PIPE)
    import sys
    only = [float(x) for x in sys.argv[1:]]
    frames = [int(x * FPS) for x in only] if only else range(N)
    for i in frames:
        t = i / FPS
        p = scene_of(t)
        b = BGS[p]
        if p > 0:
            tb = ST[KEYS[p]] - GAP * 0.5; k = min(1, (t - tb) / 0.5)
            if k < 1: b = BGS[p - 1] * (1 - k) + b * k
        base = np.clip(b * VIG + GRAIN[i % 6], 0, 255).astype(np.uint8)
        img = Image.fromarray(base).convert("RGBA")
        for sp, fn in SC:
            if ST[KEYS[sp]] - 0.3 <= t <= pend(sp) + 0.3: fn(img, t)
        for s in SLOTS: draw_slot(img, t, s)
        draw_sub(img, t)
        draw_flash(img, t)
        if only: img.convert("RGB").save(f"/home/claude/tarix/chk_{t:05.1f}.jpg", quality=85)
        else: enc.stdin.write(img.convert("RGB").tobytes())
    enc.stdin.close(); enc.wait()
    print("ok", TOTAL, N)

if __name__ == "__main__":
    main()
