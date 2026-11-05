"""«Бизнинг ҳамкорлар» v3 — 13 с под трек + концовка. Партнёры влетают с разных сторон,
у каждого свой переход, после логотипа — кадр нашей работы для него, красная нить, пустое место."""
import math, random, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, "/home/claude/anim")
W, H, FPS = 1080, 1920, 30
F9 = "/home/claude/fnt/montserrat-900.ttf"
C = "/home/claude/works/c"
OUT = "/home/claude/anim/frames3"; os.makedirs(OUT, exist_ok=True)
RED = (255, 16, 36)

def clamp(x, a=0., b=1.): return max(a, min(b, x))
def ease_out(t): return 1 - (1 - t) ** 3
def ease_in(t): return t ** 3
def ease_io(t): return 3 * t * t - 2 * t ** 3
def back_out(t, s=1.5): t -= 1; return t * t * ((s + 1) * t + s) + 1

# ---------- логотипы ----------
def load_logo(path, key=None, circle=False, size=760):
    im = Image.open(path).convert("RGBA")
    if key == "dark":
        a = np.asarray(im).astype(np.float32); a[..., 3] = np.clip((a[..., :3].max(2) - 25) * 4, 0, 255)
        im = Image.fromarray(a.astype(np.uint8))
    if circle:
        m = Image.new("L", im.size, 0); w, h = im.size
        ImageDraw.Draw(m).ellipse([w * .015, h * .015, w * .985, h * .985], fill=255)
        im.putalpha(Image.fromarray(np.minimum(np.asarray(m), np.asarray(im.getchannel("A")))))
    im = im.crop(im.getbbox()); k = size / max(im.size)
    return im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)

def extrude(im, depth=24):
    pad = depth + 70; cw, ch = im.width + pad * 2, im.height + pad * 2
    out = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    sh = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); sh.paste((0, 0, 0, 160), (pad + depth + 20, pad + depth + 34), im.getchannel("A"))
    out = Image.alpha_composite(out, sh.filter(ImageFilter.GaussianBlur(28)))
    a = np.asarray(im).astype(np.float32)
    for i in range(depth, 0, -1):
        s = a.copy(); s[..., :3] *= 0.30 + 0.25 * (1 - i / depth)
        out.alpha_composite(Image.fromarray(s.astype(np.uint8)), (pad + i, pad + i))
    out.alpha_composite(im, (pad, pad)); return out

A = "/home/claude/anim"
OJ = extrude(load_logo(f"{A}/oj_full.png", key="dark", size=860), 14)
LOGO = {"shod": extrude(load_logo(f"{A}/shod.png", size=800), 9),
        "gw": extrude(load_logo(f"{A}/gw.png", circle=True, size=760), 28),
        "vol": extrude(load_logo(f"{A}/vol.png", circle=True, size=740), 28),
        "dan": extrude(load_logo(f"{A}/dandana.png", size=760), 28)}

def pill(txt, sz, fill=(255, 255, 255), bg=(255, 16, 36, 255), track=3):
    t = text_img(txt, sz, fill, track); px, py = int(sz * .7), int(sz * .35)
    im = Image.new("RGBA", (t.width + 2 * px, t.height + py), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=im.height // 2, fill=bg)
    im.alpha_composite(t, (px, int(py * .75))); return im

def text_img(txt, sz, fill=(255, 255, 255), track=4):
    f = ImageFont.truetype(F9, sz); ws = [f.getlength(c) for c in txt]
    im = Image.new("RGBA", (int(sum(ws) + track * len(txt)) + 24, int(sz * 1.35)), (0, 0, 0, 0)); d = ImageDraw.Draw(im); x = 12
    for c, w in zip(txt, ws): d.text((x, 0), c, font=f, fill=fill); x += w + track
    return im

# ---------- кадры наших работ ----------
def cover(im):
    k = max(W / im.width, H / im.height); im = im.resize((int(im.width * k + .5), int(im.height * k + .5)), Image.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 2; return im.crop((x, y, x + W, y + H))

def seq(name, fix=None):
    fs = sorted(os.listdir(f"{C}/{name}")); return [f"{C}/{name}/{f}" for f in fs], fix

def fix_kaaba(im):  # убрать нашу плашку шоурила: берём верх кадра
    h = int(im.height * .72); w = int(h * 9 / 16); x = (im.width - w) // 2
    return im.crop((x, 0, x + w, h))

def fix_shod(im):  # закрасить плашку: тянем фон сверху-снизу
    a = np.asarray(im.convert("RGB")).astype(np.float32); Hh = a.shape[0]
    y0, y1 = int(Hh * .735), int(Hh * .815); top, bot = a[y0 - 1], a[y1 + 1]
    for y in range(y0, y1 + 1):
        k = (y - y0) / (y1 - y0); a[y] = top * (1 - k) + bot * k
    return Image.fromarray(a.astype(np.uint8))

CLIPS = {"kaaba": seq("kaaba", fix_kaaba), "dan": seq("dan"), "shod": seq("shod", fix_shod)}
_cache = {}
def clip_frame(name, t):
    fs, fix = CLIPS[name]; i = min(len(fs) - 1, int(t * FPS)); key = (name, i)
    if key not in _cache:
        im = Image.open(fs[i]).convert("RGB"); im = fix(im) if fix else im; _cache[key] = cover(im).convert("RGBA")
    return _cache[key].copy()

GWP = Image.open(f"{C}/gw.png").convert("RGBA")
def gw_work(t):  # постер аппарата GOLD WATER: студийный свет, медленный наезд
    c = world("gw", t + 1.2)
    s = 1.85 + .08 * t; im = GWP.resize((int(GWP.width * s), int(GWP.height * s)), Image.LANCZOS)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(glow).ellipse([W * .1, H * .25, W * .9, H * .8], fill=(90, 200, 255, 90))
    c.alpha_composite(glow.filter(ImageFilter.GaussianBlur(120)))
    c.alpha_composite(im, (int(W / 2 - im.width / 2), int(H * .52 - im.height / 2))); return c

WORK = {"shod": lambda t: clip_frame("shod", t), "gw": gw_work,
        "vol": lambda t: clip_frame("kaaba", t), "dan": lambda t: clip_frame("dan", t)}

# ---------- миры: у каждого своя пара цветов + передний план в расфокусе ----------
def radial(c_in, c_out, cx=.5, cy=.42):
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.clip(np.sqrt((x / W - cx) ** 2 + ((y / H - cy) * .56) ** 2) / .62, 0, 1)[..., None]
    return (np.array(c_in) * (1 - d) + np.array(c_out) * d).astype(np.uint8)
BG = {"oj": radial((50, 6, 12), (0, 0, 0)), "shod": radial((250, 238, 218), (210, 188, 150)),
      "gw": radial((30, 140, 190), (5, 16, 60)), "vol": radial((130, 20, 34), (34, 2, 10)),
      "dan": radial((46, 30, 12), (0, 0, 0)), "end": radial((70, 6, 14), (0, 0, 0))}
ACC = {"oj": [RED], "shod": [(38, 84, 58), (150, 98, 52)], "gw": [(60, 220, 230), (240, 196, 90)],
       "vol": [(240, 190, 100)], "dan": [(245, 175, 60), (255, 120, 30)], "end": [RED]}
rnd = random.Random(11); PART = [(rnd.random(), rnd.random(), rnd.random()) for _ in range(70)]

def world(k, t):
    img = Image.fromarray(BG[k]).convert("RGBA")
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    if k == "shod":  # тёмно-зелёная диагональ + ореховая полоса
        d.polygon([(0, H * .72), (W, H * .58), (W, H * .66), (0, H * .80)], fill=(38, 84, 58, 235))
        d.polygon([(0, H * .80), (W, H * .66), (W, H * .685), (0, H * .825)], fill=(150, 98, 52, 255))
    if k == "gw":
        for i in range(5):
            x = W * (.1 + .2 * i) + math.sin(t * 2 + i) * 30
            d.polygon([(x, 0), (x + 90, 0), (x + 260, H), (x + 120, H)], fill=(170, 235, 255, 24))
        for (a, b, c) in PART[:40]:
            y = (b - t * (.15 + .2 * c)) % 1; r = 6 + 16 * c
            d.ellipse([a * W - r, y * H - r, a * W + r, y * H + r], outline=(210, 245, 255, 150), width=3)
    if k == "vol":
        cx, cy = W / 2, H * .42
        for i in range(12):
            g = i * math.pi / 6 + t * .25
            d.polygon([(cx, cy), (cx + math.cos(g - .08) * 1700, cy + math.sin(g - .08) * 1700),
                       (cx + math.cos(g + .08) * 1700, cy + math.sin(g + .08) * 1700)], fill=(255, 205, 120, 20))
        for (a, b, c) in PART:
            y = (b - t * .06 * (1 + c)) % 1; r = 2 + 4 * c
            d.ellipse([a * W - r, y * H - r, a * W + r, y * H + r], fill=(255, 215, 140, int(120 + 100 * c)))
    if k == "dan":
        for (a, b, c) in PART[:14]:
            r = 50 + 90 * c; d.ellipse([a * W - r, b * H * .6 - r, a * W + r, b * H * .6 + r], fill=(255, 150, 50, 45))
        for (a, b, c) in PART[14:]:
            y = (b - t * (.35 + .4 * c)) % 1; x = a * W + math.sin(t * 6 + c * 9) * 20; r = 3 + 4 * c
            d.ellipse([x - r, y * H - r, x + r, y * H + r], fill=(255, 170, 60, 220))
    if k in ("oj", "end"):
        for (a, b, c) in PART[:30]:
            y = (b - t * .05) % 1; r = 2 + 3 * c
            d.ellipse([a * W - r, y * H - r, a * W + r, y * H + r], fill=(255, 40, 60, 100))
    img = Image.alpha_composite(img, ov.filter(ImageFilter.GaussianBlur(3 if k != "dan" else 9)))
    # передний план: крупные размытые пятна акцентных цветов (глубина)
    fg = Image.new("RGBA", (W, H), (0, 0, 0, 0)); fd = ImageDraw.Draw(fg)
    for j, (a, b, c) in enumerate(PART[50:54]):
        col = ACC[k][j % len(ACC[k])]; r = 140 + 120 * c
        x = (a * W + t * 90 * (1 if j % 2 else -1)) % (W + 400) - 200; y = b * H
        fd.ellipse([x - r, y - r, x + r, y + r], fill=col + (70,))
    img.alpha_composite(fg.filter(ImageFilter.GaussianBlur(60)))
    return img

def place(cv, im, cx, cy, s, a=1., rot=0.):
    if s <= .01 or a <= 0: return
    im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BILINEAR)
    if rot: im = im.rotate(rot, Image.BICUBIC, expand=True)
    if a < 1: im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    cv.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def flash(cv, a, col=(255, 255, 255)):
    if a > 0: cv.alpha_composite(Image.new("RGBA", (W, H), col + (int(255 * clamp(a)),)))

def glint(cv, t):
    if not 0 <= t <= 1: return
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); x = -400 + t * (W + 800)
    ImageDraw.Draw(ov).polygon([(x, 0), (x + 120, 0), (x - 380, H), (x - 500, H)], fill=(255, 255, 255, 60))
    cv.alpha_composite(ov.filter(ImageFilter.GaussianBlur(30)))

def thread(cv, p, y=.86):
    """Красная нить OZOD JAMOL — тянется слева направо через каждого партнёра."""
    if p <= 0: return
    d = ImageDraw.Draw(cv); x1 = int(W * clamp(p))
    d.rectangle([0, int(H * y) - 5, x1, int(H * y) + 5], fill=RED + (255,))
    d.ellipse([x1 - 13, int(H * y) - 13, x1 + 13, int(H * y) + 13], fill=RED + (255,))

def work_card(cv, k, lt):
    """Кадр нашей работы: на весь экран, тонкая красная рамка + метка."""
    im = WORK[k](lt); cv.alpha_composite(im)
    d = ImageDraw.Draw(cv); m = 26
    d.rounded_rectangle([m, m, W - m, H - m], radius=40, outline=RED + (255,), width=8)

LAB = {"shod": "МЕБЕЛЬ РЕКЛАМАСИ", "gw": "СУВ АППАРАТИ ДИЗАЙНИ", "vol": "ИИ-ВИДЕО · УМРА", "dan": "ТАОМ РЕКЛАМАСИ"}
TAG = pill("БИЗНИНГ ИШИМИЗ", 44)
HEAD = text_img("БИЗНИНГ ҲАМКОРЛАР", 54, (255, 255, 255), 6); HEAD_D = text_img("БИЗНИНГ ҲАМКОРЛАР", 54, (30, 60, 42), 6)
OJW = text_img("OZOD JAMOL", 74, (255, 255, 255), 6)

SEQ = [("shod", 1.6), ("gw", 4.0), ("vol", 6.4), ("dan", 8.8)]; SEG = 2.4; FIN = 11.2; END = 13.0
def enter(k, lt):
    """Вход логотипа — у каждого свой: (cx, cy, s, a, rot)."""
    e = clamp(lt / .55)
    if k == "shod":  # слева, мягкий отскок
        return W / 2 - (1 - back_out(e, 1.3)) * W * 1.2, H * .44, 1, 1, (1 - ease_out(e)) * 10
    if k == "gw":    # снизу из всплеска
        return W / 2, H * .44 + (1 - back_out(e, 1.6)) * H * .8, .9 + .1 * e, 1, 0
    if k == "vol":   # медленно сверху, в лучах
        e = clamp(lt / .8); return W / 2, H * .44 - (1 - ease_out(e)) * H * .6, 1, ease_out(e), 0
    # dan — из глубины на камеру
    return W / 2, H * .44, .1 + .9 * back_out(e, 1.2), clamp(lt / .2), 0

def frame(t):
    if t < 1.0:  # тихое вступление: 3 вспышки наших работ → удар OJ на дроп
        i = int(t / .333); nm = ["vol", "dan", "shod"][min(i, 2)]
        cv = WORK[nm](t % .333 + .3)
        cv.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 90)))
        flash(cv, 1 - (t % .333) / .08)
        return cv
    if t < 1.6:  # удар логотипа
        lt = t - 1.0; cv = world("oj", lt)
        place(cv, OJ, W / 2, H * .42, 1.25 - .25 * back_out(clamp(lt / .25)) + .03 * lt)
        place(cv, OJW, W / 2, H * .62, 1, clamp((lt - .1) / .2))
        flash(cv, 1 - lt / .12)
        if lt > .45: place_exit = (lt - .45) / .15; cv.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * ease_in(clamp(place_exit))))))
        return cv
    for n, (k, t0) in enumerate(SEQ):
        if t0 <= t < t0 + SEG:
            lt = t - t0
            if lt < 1.2:  # логотип в своём мире
                cv = world(k, lt)
                place(cv, HEAD_D if k == "shod" else HEAD, W / 2, H * .11, 1)
                cx, cy, s, a, rot = enter(k, lt)
                place(cv, LOGO[k], cx, cy, s + .04 * lt, a, rot); glint(cv, (lt - .6) / .45)
                if k == "gw" and lt < .4:  # кольца-всплеск
                    d = ImageDraw.Draw(cv)
                    for j in range(3):
                        r = (lt / .4) * 500 + j * 80
                        d.ellipse([W / 2 - r, H * .6 - r * .3, W / 2 + r, H * .6 + r * .3], outline=(220, 250, 255, int(200 * (1 - lt / .4))), width=6)
                if k == "vol": flash(cv, (.25 - lt) / .25 * .6, (255, 220, 150))
                thread(cv, (n + lt / 1.2) / 4 * .999)
            else:         # кадр нашей работы
                wt = lt - 1.2; cv = Image.new("RGBA", (W, H)); work_card(cv, k, wt)
                tg = TAG; place(cv, tg, W / 2, H * .875, 1, clamp(wt / .15))
                place(cv, pill(LAB[k], 50, bg=(0, 0, 0, 215)), W / 2, H * .935, 1, clamp((wt - .1) / .15))
                # вход в работу: быстрый наезд из логотипа
                if wt < .15: flash(cv, 1 - wt / .15, (255, 255, 255) if k != "dan" else (255, 170, 60))
                # выход — у каждого свой
                out = (wt - .9) / .3
                if 0 < out <= 1:
                    if k == "shod":   # свайп вправо
                        sh = int(ease_in(out) * W); tmp = Image.new("RGBA", (W, H), (0, 0, 0, 255)); tmp.alpha_composite(cv, (sh, 0)); cv = tmp
                    elif k == "gw":   # круг-капля закрывает
                        m = Image.new("L", (W, H), 0); r = ease_in(out) * 1300
                        ImageDraw.Draw(m).ellipse([W / 2 - r, H / 2 - r, W / 2 + r, H / 2 + r], fill=255)
                        cv.paste(Image.fromarray(BG["vol"]).convert("RGBA"), (0, 0), m)
                    elif k == "vol":  # золотая вспышка
                        flash(cv, ease_in(out), (255, 210, 130))
                    else:             # огонь в чёрный
                        flash(cv, ease_in(out), (255, 120, 20)); flash(cv, clamp(out * 2 - 1), (0, 0, 0))
            return cv
    # финал 11.2–13.0: логотипы слетаются с разных сторон + пустое место
    lt = t - FIN; cv = world("end", lt)
    place(cv, text_img("4 ҲАМКОР · СИЗ — 5-ЧИ", 50, (255, 255, 255), 4), W / 2, H * .10, 1, clamp(lt / .2))
    slots = [(W * .28, H * .24), (W * .72, H * .24), (W * .28, H * .43), (W * .72, H * .43)]
    starts = [(-W * .6, H * .24), (W * 1.6, H * .24), (-W * .6, H * .43), (W * 1.6, H * .43)]
    for j, k in enumerate(["shod", "gw", "vol", "dan"]):
        e = back_out(clamp((lt - j * .07) / .35), 1.2)
        x = starts[j][0] + (slots[j][0] - starts[j][0]) * e; y = starts[j][1] + (slots[j][1] - starts[j][1]) * e
        place(cv, LOGO[k], x, y, .36)
    # пустое место — пульсирует
    pa = clamp((lt - .35) / .2); pul = .5 + .5 * math.sin(lt * 9)
    if pa > 0:
        box = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(box)
        x0, y0, x1, y1 = W * .14, H * .53, W * .86, H * .70
        for s in range(0, int(x1 - x0), 44):  # пунктир
            d.line([(x0 + s, y0), (x0 + s + 24, y0)], fill=RED + (255,), width=8); d.line([(x0 + s, y1), (x0 + s + 24, y1)], fill=RED + (255,), width=8)
        for s in range(0, int(y1 - y0), 44):
            d.line([(x0, y0 + s), (x0, y0 + s + 24)], fill=RED + (255,), width=8); d.line([(x1, y0 + s), (x1, y0 + s + 24)], fill=RED + (255,), width=8)
        d.rounded_rectangle([x0, y0, x1, y1], radius=30, fill=(255, 16, 36, int(30 + 40 * pul)))
        box.putalpha(box.getchannel("A").point(lambda v: int(v * pa))); cv.alpha_composite(box)
        place(cv, text_img("?", 150, (255, 255, 255), 0), W / 2, H * .585, .9 + .1 * pul, pa)
    l1 = clamp((lt - .55) / .2); l2 = clamp((lt - .7) / .2)
    place(cv, text_img("БУ ЖОЙ —", 58, (255, 255, 255), 3), W / 2, H * .66, 1, l1)
    place(cv, text_img("СИЗНИНГ БРЕНДИНГИЗ УЧУН", 58, (255, 255, 255), 2), W / 2, H * .755, 1, l1)
    place(cv, text_img("@Ozodjamol", 72, RED, 2), W / 2, H * .84, 1, l2)
    thread(cv, 1, .885)
    if lt < .1: flash(cv, 1 - lt / .1, (255, 120, 20))
    return cv

if __name__ == "__main__":
    ts = [float(x) for x in sys.argv[1:]]
    if ts:
        for t in ts: frame(t).convert("RGB").save(f"/home/claude/anim/q_{t:05.2f}.jpg", quality=85)
    else:
        for i in range(int(END * FPS)): frame(i / FPS).convert("RGB").save(f"{OUT}/{i:04d}.jpg", quality=92)
