import math, os, random, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS, DUR = 1080, 1920, 30, 15.0
N = int(FPS * DUR)
BEAT = 0.6
F = "/home/claude/fonts/"
OUT = "/home/claude/story/frames"
os.makedirs(OUT, exist_ok=True)

YEL, BLK, PINK, WHT = (255, 214, 10), (14, 14, 16), (255, 46, 126), (255, 255, 255)
TEAL, ORNG, BLUE, PURP = (0, 201, 167), (255, 106, 26), (40, 90, 255), (130, 70, 255)

_fc = {}
def font(sz, w=900):
    k = (sz, w)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(f"{F}Mont{w}.ttf", sz)
    return _fc[k]

def fit(text, maxw, w=900, start=260):
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    s = start
    while d.textlength(text, font=font(s, w)) > maxw and s > 20:
        s -= 4
    return font(s, w)

def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))

def spring(t, k=10.0, z=0.35):
    """0→1 с перелётом (пружина)."""
    if t <= 0: return 0.0
    if t >= 2.5: return 1.0
    return 1 - math.exp(-z * k * t) * math.cos(k * math.sqrt(1 - z * z) * t)

def ease_out(t):
    t = clamp(t); return 1 - (1 - t) ** 3

def ease_io(t):
    t = clamp(t); return t * t * (3 - 2 * t)

# ---------- фон: большие мягкие пятна (задний план) ----------
def make_bg(base, c1, c2, seed):
    random.seed(seed)
    big = Image.new("RGB", (W + 400, H + 400), base)
    lay = Image.new("RGB", big.size, base)
    d = ImageDraw.Draw(lay)
    for col in (c1, c2, c1):
        r = random.randint(380, 560)
        x, y = random.randint(0, big.width), random.randint(0, big.height)
        d.ellipse([x - r, y - r, x + r, y + r], fill=col)
    lay = lay.filter(ImageFilter.GaussianBlur(160))
    return Image.blend(big, lay, 0.55)

def lighten(c, k):
    return tuple(int(v + (255 - v) * k) for v in c)

def darken(c, k):
    return tuple(int(v * (1 - k)) for v in c)

SCENES_BG = {
    "hook": make_bg(BLK, (60, 50, 0), (70, 10, 40), 1),
    "menu": make_bg(BLK, (50, 40, 0), (10, 30, 70), 2),
    "count": make_bg((20, 20, 24), (80, 60, 0), (60, 10, 30), 3),
    "cta": make_bg(YEL, lighten(YEL, 0.5), (255, 170, 0), 4),
}

# частицы переднего плана
random.seed(7)
PARTS = [(random.uniform(0, W), random.uniform(0, H), random.uniform(3, 9), random.uniform(0.6, 1.6)) for _ in range(40)]

# ---------- текстовые блоки ----------
def text_img(text, f, fill, plaque=None, pad=(34, 18), r=22):
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    bb = d.textbbox((0, 0), text, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pw, ph = (tw + 2 * pad[0], th + 2 * pad[1]) if plaque else (tw + 10, th + 10)
    im = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    dd = ImageDraw.Draw(im)
    if plaque:
        dd.rounded_rectangle([0, 0, pw - 1, ph - 1], r, fill=plaque)
        dd.text((pad[0] - bb[0], pad[1] - bb[1]), text, font=f, fill=fill)
    else:
        dd.text((5 - bb[0], 5 - bb[1]), text, font=f, fill=fill)
    return im

def place(canvas, im, cx, cy, scale=1.0, alpha=1.0, rot=0.0, dx=0, dy=0):
    if alpha <= 0.01 or scale <= 0.02: return
    if abs(scale - 1) > 0.01:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if abs(rot) > 0.1:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 0.99:
        a = im.split()[3].point(lambda v: int(v * alpha))
        im = im.copy(); im.putalpha(a)
    canvas.alpha_composite(im, (int(cx - im.width / 2 + dx), int(cy - im.height / 2 + dy)))

def slam(canvas, im, cx, cy, t0, t, out_t=None, rot=0.0):
    """появление ударом: большой → 1.0 с пружиной."""
    lt = t - t0
    if lt < 0: return
    s = 1.0 + 0.8 * (1 - spring(lt, 14, 0.42))
    a = clamp(lt / 0.08)
    if out_t is not None and t > out_t:
        o = clamp((t - out_t) / 0.18)
        a *= 1 - o; s *= 1 + 0.25 * o
    place(canvas, im, cx, cy, s, a, rot)

def slide(canvas, im, cx, cy, t0, t, frm=-1, dist=700, out_t=None):
    lt = t - t0
    if lt < 0: return
    p = spring(lt, 11, 0.5)
    x = cx + frm * dist * (1 - p)
    a = clamp(lt / 0.1)
    if out_t is not None and t > out_t:
        o = ease_io((t - out_t) / 0.2); x -= frm * 900 * o; a *= 1 - o
    place(canvas, im, x, cy, 1.0, a)

# ---------- заготовки текстов ----------
T_SIZ = text_img("СИЗ ҲАЛИ", fit("СИЗ ҲАЛИ", 900, start=220), WHT)
T_KD = text_img("КАТТА ДАВРА", fit("КАТТА ДАВРА", 880, start=170), BLK, plaque=YEL)
T_DA = text_img("ДА ЭМАСМИСИЗ?", fit("ДА ЭМАСМИСИЗ?", 900), PINK)

T_NIMA = text_img("КАНАЛДА НИМА БОР?", font(60), BLK, plaque=WHT)
RUBRICS = [
    ("ТРЕНДЛАР", "ДУНЁДА НИМА ГАП", PINK),
    ("ФОЙДАЛИ", "ҲАЁТИЙ МАСЛАҲАТЛАР", TEAL),
    ("КУЛГИ", "КАЙФИЯТ УЧУН", YEL),
    ("МУСИҚА", "КУНИГА 3 МАРТА", PURP),
    ("МОТИВАЦИЯ", "ҲАР КУНИ ИЛҲОМ", ORNG),
    ("УЙ БИЗНЕСИ", "УЙДА ПУЛ ТОПИШ", BLUE),
]
R_IMG = []
for name, sub, col in RUBRICS:
    fg = BLK if col in (YEL, TEAL) else WHT
    big = text_img(name, fit(name, 860, start=210), fg)
    card = Image.new("RGBA", (960, 620), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle([0, 0, 959, 619], 48, fill=col)
    card.alpha_composite(big, ((960 - big.width) // 2, 150))
    s = text_img(sub, font(46, 700), fg)
    card.alpha_composite(s, ((960 - s.width) // 2, 440))
    R_IMG.append(card)

T_KUN = text_img("КУНИГА", font(80), WHT)
T_POST = text_img("ЯНГИ ПОСТ", font(96), YEL)
T_LOGO = text_img("КАТТА ДАВРА", fit("КАТТА ДАВРА", 900, start=180), YEL, plaque=BLK, pad=(40, 26), r=30)
T_USER = text_img("@kattadavrauz", font(64), BLK)
T_OBUNA = text_img("ОБУНА БЎЛИНГ", font(70), WHT, plaque=PINK)
T_LINK = text_img("ҲАВОЛАНИ БОСИНГ", font(50), BLK)

def bg_frame(name, t, cam):
    b = SCENES_BG[name]
    ox = 200 + 120 * math.sin(t * 0.7) + cam[0] * 0.4
    oy = 200 + 90 * math.cos(t * 0.5) + cam[1] * 0.4
    return b.crop((int(ox), int(oy), int(ox) + W, int(oy) + H)).convert("RGBA")

def particles(canvas, t, col, cam):
    d = ImageDraw.Draw(canvas)
    for x, y, r, sp in PARTS:
        yy = (y - t * 120 * sp + cam[1] * 1.6) % H
        xx = (x + math.sin(t * sp + y) * 30 + cam[0] * 1.6) % W
        d.ellipse([xx - r, yy - r, xx + r, yy + r], fill=col + (90,))

def camera(t):
    # камера не стоит: дрейф + толчки на ударах
    kick = 0
    for bt in (0.6, 1.2, 2.4, 9.6, 12.0):
        dt = t - bt
        if 0 <= dt < 0.4: kick += math.exp(-dt * 12) * 18
    return (math.sin(t * 0.9) * 25 + kick, math.cos(t * 0.7) * 20 - kick * 0.6), 1.03 + 0.02 * math.sin(t * 0.6)

def render(i):
    t = i / FPS
    cam, zoom = camera(t)
    if t < 2.4: sc = "hook"
    elif t < 9.6: sc = "menu"
    elif t < 12.0: sc = "count"
    else: sc = "cta"
    c = bg_frame(sc, t, cam)
    particles(c, t, BLK if sc == "cta" else YEL, cam)
    mid = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cx, cy = W / 2 + cam[0], H / 2 + cam[1]

    if sc == "hook":
        slam(mid, T_SIZ, cx, cy - 300, 0.05, t)
        slam(mid, T_KD, cx, cy - 40, 0.6, t, rot=-3)
        slam(mid, T_DA, cx, cy + 250, 1.2, t)
    elif sc == "menu":
        lt = t - 2.4
        p = ease_io((lt - 0.35) / 0.3)
        hy = (cy) * (1 - p) + (330 + cam[1]) * p
        hs = (min(1000 / T_NIMA.width, 1.0 + 0.7 * spring(lt, 13, 0.45))) * (1 - p) + 1.0 * p
        place(mid, T_NIMA, cx, hy, hs, clamp(lt / 0.08))
        for k, card in enumerate(R_IMG):
            t0 = 3.0 + k * 1.1
            lt = t - t0
            if lt < 0 or lt > 1.25: continue
            p = spring(lt, 12, 0.45)
            x = cx + 1100 * (1 - p)
            rot = 6 * (1 - p)
            a = 1.0
            if lt > 0.95:
                o = ease_io((lt - 0.95) / 0.3); x -= 1100 * o; rot -= 6 * o
            # стопка-подложка (глубина)
            place(mid, card, x + 26, cy + 60 + 26, 1.0, 0.25 * a, rot)
            place(mid, card, x, cy + 60, 1.0, a, rot)
        # счётчик рубрик
        k = int(clamp((t - 3.0) / 1.1, 0, 5.99))
        if t >= 3.0:
            prog = text_img(f"{k + 1} / 6", font(44, 700), WHT)
            place(mid, prog, cx, 1470 + cam[1], 1, clamp((t - 3) / 0.2))
    elif sc == "count":
        lt = t - 9.6
        slam(mid, T_KUN, cx, cy - 330, 9.6, t)
        n = int(round(20 * ease_out(lt / 1.2)))
        num = text_img(f"{n}+", font(330), WHT)
        place(mid, num, cx, cy - 20, 1.0 + 0.06 * math.sin(lt * 9) * (1 if n < 20 else 0) + (0.12 * math.exp(-max(0, lt - 1.2) * 8) if lt > 1.2 else 0), clamp(lt / 0.1))
        slam(mid, T_POST, cx, cy + 260, 10.4, t)
    else:
        lt = t - 12.0
        slam(mid, T_LOGO, cx, cy - 300, 12.0, t, rot=-2)
        slide(mid, T_USER, cx, cy - 110 + cam[1] * 0.2, 12.4, t, frm=1)
        slam(mid, T_OBUNA, cx, cy + 70, 12.9, t)
        if t > 13.4:
            bob = math.sin((t - 13.4) * 7) * 18
            place(mid, T_LINK, cx, cy + 290, 1, clamp((t - 13.4) / 0.2))
            d = ImageDraw.Draw(mid)
            ax, ay = cx, cy + 400 + bob
            d.polygon([(ax - 50, ay - 30), (ax + 50, ay - 30), (ax, ay + 35)], fill=BLK)

    # переход-«вжух» между сценами: размытие по горизонтали вокруг стыка
    for cut in (2.4, 9.6, 12.0):
        dt = abs(t - cut)
        if dt < 0.12:
            k = int((0.12 - dt) / 0.12 * 40) + 1
            mid = mid.filter(ImageFilter.BoxBlur(k // 3 + 1))
    c.alpha_composite(mid)
    if abs(zoom - 1) > 0.001:
        zw, zh = int(W * zoom), int(H * zoom)
        c = c.resize((zw, zh), Image.BILINEAR).crop(((zw - W) // 2, (zh - H) // 2, (zw - W) // 2 + W, (zh - H) // 2 + H))
    # белая вспышка на стыках
    for cut in (2.4, 9.6, 12.0):
        dt = t - cut
        if 0 <= dt < 0.1:
            c = Image.blend(c, Image.new("RGBA", (W, H), (255, 255, 255, 255)), 0.5 * (1 - dt / 0.1))
    c.convert("RGB").save(f"{OUT}/f{i:04d}.jpg", quality=92)

if __name__ == "__main__":
    a, b = int(sys.argv[1]), int(sys.argv[2])
    for i in range(a, min(b, N)):
        render(i)
