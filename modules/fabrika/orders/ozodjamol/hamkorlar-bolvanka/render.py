"""Болванка «Бизнинг ҳамкорлар» 13 с, 9:16 — аниматик для владельца."""
import math, random, subprocess, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

W, H, FPS = 1080, 1920, 30
F9 = "/home/claude/fnt/montserrat-900.ttf"
OUT = "/home/claude/anim/frames"; os.makedirs(OUT, exist_ok=True)

def ease_out(t): return 1 - (1 - t) ** 3
def ease_in(t): return t ** 3
def back_out(t, s=1.6): t -= 1; return t * t * ((s + 1) * t + s) + 1
def clamp(x, a=0, b=1): return max(a, min(b, x))

# ---------- логотипы: объём (выдавливание) + тень ----------
def load_logo(path, key=None, circle=False, size=760):
    im = Image.open(path).convert("RGBA")
    if key == "dark":
        a = np.asarray(im).astype(np.float32); lum = a[..., :3].max(2)
        a[..., 3] = np.clip((lum - 25) * 4, 0, 255); im = Image.fromarray(a.astype(np.uint8))
    if circle:
        m = Image.new("L", im.size, 0); w, h = im.size
        ImageDraw.Draw(m).ellipse([w * .015, h * .015, w * .985, h * .985], fill=255)
        im.putalpha(Image.fromarray(np.minimum(np.asarray(m), np.asarray(im.getchannel("A")))))
    im = im.crop(im.getbbox()); k = size / max(im.size)
    im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
    return im

def extrude(im, depth=26, side=(0.35, 0.35, 0.35)):
    """Толщина: стопка затемнённых копий вниз-вправо + мягкая тень на пол."""
    pad = depth + 60
    cw, ch = im.width + pad * 2, im.height + pad * 2
    out = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    sh = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    sh.paste((0, 0, 0, 170), (pad + depth + 18, pad + depth + 30), im.getchannel("A"))
    out = Image.alpha_composite(out, sh.filter(ImageFilter.GaussianBlur(26)))
    a = np.asarray(im).astype(np.float32)
    for i in range(depth, 0, -1):
        k = 0.30 + 0.25 * (1 - i / depth)
        s = a.copy(); s[..., :3] *= k
        out.alpha_composite(Image.fromarray(s.astype(np.uint8)), (pad + i, pad + i))
    out.alpha_composite(im, (pad, pad))
    return out

oj = load_logo("oj_full.png", key="dark", size=820)
LOGOS = {
    "shod": extrude(load_logo("shod.png", size=780), 9),
    "gw": extrude(load_logo("gw.png", circle=True, size=760), 28),
    "vol": extrude(load_logo("vol.png", circle=True, size=740), 28),
    "dan": extrude(load_logo("dandana.png", size=760), 28),
    "love": extrude(load_logo("love.png", size=900), 22),
}
OJ = extrude(oj, 14)

def font(sz): return ImageFont.truetype(F9, sz)
def text_img(txt, sz, fill=(255, 255, 255), track=4):
    f = font(sz); ws = [f.getlength(c) for c in txt]; tw = int(sum(ws) + track * (len(txt) - 1)) + 20
    im = Image.new("RGBA", (tw, int(sz * 1.35)), (0, 0, 0, 0)); d = ImageDraw.Draw(im); x = 10
    for c, w in zip(txt, ws): d.text((x, 0), c, font=f, fill=fill); x += w + track
    return im

# ---------- миры (фоны) ----------
def radial(c_in, c_out, cx=.5, cy=.42, r=1.0):
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((x / W - cx) * 1.0) ** 2 + ((y / H - cy) * 0.56) ** 2) / (0.62 * r)
    d = np.clip(d, 0, 1)[..., None]
    return (np.array(c_in) * (1 - d) + np.array(c_out) * d).astype(np.float32)

BG = {
    "oj": radial((40, 6, 10), (0, 0, 0)),
    "shod": radial((246, 232, 210), (196, 170, 135)),
    "gw": radial((40, 120, 200), (4, 18, 52)),
    "vol": radial((120, 18, 30), (30, 2, 8)),
    "dan": radial((40, 26, 12), (0, 0, 0)),
    "end": radial((60, 6, 12), (0, 0, 0)),
    "love": radial((50, 80, 230), (8, 14, 80)),
}
rnd = random.Random(7)
PART = {k: [(rnd.random(), rnd.random(), rnd.random()) for _ in range(60)] for k in BG}

def world(k, t):
    """Фон мира + живые частицы (t — время внутри сцены)."""
    img = Image.fromarray(BG[k].astype(np.uint8)).convert("RGBA")
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    if k == "shod":  # тёплый пол + мягкое окно-свет
        d.rectangle([0, int(H * .68), W, H], fill=(170, 140, 105, 90))
        for i in range(3):
            x = int(W * (.15 + .3 * i) + t * 40)
            d.polygon([(x, 0), (x + 160, 0), (x + 420, H), (x + 260, H)], fill=(255, 250, 235, 22))
    if k == "gw":  # лучи и пузырьки вверх
        for i in range(5):
            x = int(W * (.1 + .2 * i) + math.sin(t * 2 + i) * 30)
            d.polygon([(x, 0), (x + 90, 0), (x + 260, H), (x + 120, H)], fill=(160, 220, 255, 26))
        for (a, b, c) in PART[k]:
            y = (b - t * (0.15 + 0.2 * c)) % 1.0; r = 6 + 16 * c
            d.ellipse([a * W - r, y * H - r, a * W + r, y * H + r], outline=(200, 240, 255, 150), width=3)
    if k == "vol":  # золотые лучи вращаются + золотая пыль
        cx, cy = W / 2, H * .42
        for i in range(12):
            ang = i * math.pi / 6 + t * 0.25
            p2 = (cx + math.cos(ang - .08) * 1600, cy + math.sin(ang - .08) * 1600)
            p3 = (cx + math.cos(ang + .08) * 1600, cy + math.sin(ang + .08) * 1600)
            d.polygon([(cx, cy), p2, p3], fill=(255, 200, 110, 18))
        for (a, b, c) in PART[k]:
            y = (b - t * 0.06 * (1 + c)) % 1.0; r = 2 + 4 * c
            d.ellipse([a * W - r, y * H - r, a * W + r, y * H + r], fill=(255, 215, 140, int(120 + 100 * c)))
    if k == "dan":  # тёплые лампы (боке) + искры вверх
        for (a, b, c) in PART[k][:14]:
            r = 50 + 90 * c
            d.ellipse([a * W - r, b * H * .6 - r, a * W + r, b * H * .6 + r], fill=(255, 150, 50, 40))
        for (a, b, c) in PART[k][14:]:
            y = (b - t * (0.35 + 0.4 * c)) % 1.0; x = a * W + math.sin(t * 6 + c * 9) * 20; r = 3 + 4 * c
            d.ellipse([x - r, y * H - r, x + r, y * H + r], fill=(255, 170, 60, 220))
    if k == "love":  # лёгкая ткань волнами + синие искры (цвет тележки)
        for j in range(4):
            pts = []
            for xi in range(0, W + 60, 60):
                y = H * (.18 + .2 * j) + math.sin(xi / 170 + t * 2.2 + j) * 70
                pts.append((xi, y))
            poly = pts + [(W + 60, pts[-1][1] + 120), (0, pts[0][1] + 120)]
            d.polygon(poly, fill=(255, 235, 210, 34))
        for (a, b, c) in PART[k][:30]:
            y = (b - t * 0.12 * (1 + c)) % 1.0; r = 3 + 5 * c
            d.ellipse([a * W - r, y * H - r, a * W + r, y * H + r], fill=(255, 140, 40, 220))
    if k in ("oj", "end"):
        for (a, b, c) in PART[k][:25]:
            y = (b - t * 0.05) % 1.0; r = 2 + 3 * c
            d.ellipse([a * W - r, y * H - r, a * W + r, y * H + r], fill=(255, 40, 60, 90))
    ov = ov.filter(ImageFilter.GaussianBlur(4 if k != "dan" else 10))
    return Image.alpha_composite(img, ov)

def place(canvas, im, cx, cy, scale, alpha=1.0, rot=0):
    if scale <= 0.01 or alpha <= 0: return
    w, h = max(1, int(im.width * scale)), max(1, int(im.height * scale))
    s = im.resize((w, h), Image.BILINEAR)
    if rot: s = s.rotate(rot, Image.BICUBIC, expand=True)
    if alpha < 1:
        a = s.getchannel("A").point(lambda v: int(v * alpha)); s.putalpha(a)
    canvas.alpha_composite(s, (int(cx - s.width / 2), int(cy - s.height / 2)))

def glint(canvas, t, strength=1.0):
    """Блик по логотипу: светлая диагональная полоса проходит на ударе."""
    if not (0 <= t <= 1): return
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    x = -400 + t * (W + 800)
    d.polygon([(x, 0), (x + 120, 0), (x - 380, H), (x - 500, H)], fill=(255, 255, 255, int(60 * strength)))
    canvas.alpha_composite(ov.filter(ImageFilter.GaussianBlur(30)))

# ---------- монтаж ----------
LABELS = {"shod": ("МЕБЕЛЬ", (40, 70, 50)), "gw": ("ТОЗА СУВ", (255, 255, 255)),
          "vol": ("УМРА ЗИЁРАТИ", (255, 220, 150)), "dan": ("ПИЦЦА & БУРГЕР", (255, 200, 90)),
          "love": ("КИЙИМ-КЕЧАК", (255, 170, 80))}
HEAD = text_img("БИЗНИНГ ҲАМКОРЛАР", 54, (255, 255, 255), 6)
HEAD_D = text_img("БИЗНИНГ ҲАМКОРЛАР", 54, (40, 30, 20), 6)
SEQ = [("shod", 1.0), ("gw", 2.5), ("vol", 4.0), ("love", 5.5), ("dan", 7.0)]   # по 1,5 с
SEG = 1.5
HOOK1 = text_img("НАВБАТДАГИ", 92, (255, 255, 255), 4)
HOOK2 = text_img("ҲАМКОР — СИЗ?", 92, (255, 16, 36), 4)
CTA = text_img("@Ozodjamol", 64, (255, 255, 255), 2)
OJWORD = text_img("OZOD JAMOL", 70, (255, 255, 255), 6)
END = 10.6

def frame(t):
    if t < 1.0:  # интро: OJ из темноты → летит в камеру на дроп
        c = world("oj", t)
        a = ease_out(clamp(t / .5)); s = 0.82 + 0.08 * t
        if t > .8: s *= 1 + ease_in((t - .8) / .2) * 3.5; a *= 1 - ease_in((t - .8) / .2)
        place(c, OJ, W / 2, H * .44, s, a)
        place(c, OJWORD, W / 2, H * .64, s * .9, a * clamp((t - .2) / .3))
        return c
    for i, (k, t0) in enumerate(SEQ):
        if t0 <= t < t0 + SEG:
            lt = t - t0; c = world(k, lt)
            # заголовок сверху
            place(c, HEAD_D if k == "shod" else HEAD, W / 2, H * .12, 1.0, clamp(lt / .25) if i == 0 else 1)
            enter = back_out(clamp(lt / .45)); s = 0.15 + 0.85 * enter + 0.05 * lt
            a = clamp(lt / .2); rot = (1 - ease_out(clamp(lt / .5))) * (-8 if i % 2 else 8)
            if lt > SEG - .25:  # пролёт мимо камеры
                e = ease_in((lt - (SEG - .25)) / .25); s *= 1 + e * 4; a *= 1 - e
            place(c, LOGOS[k], W / 2, H * .44, s, a, rot)
            lab, col = LABELS[k]
            la = clamp((lt - .35) / .25) * (1 - clamp((lt - (SEG - .3)) / .15))
            place(c, text_img(lab, 64, col, 5), W / 2, H * .72 + (1 - clamp((lt - .35) / .25)) * 40, 1, la)
            glint(c, (lt - .55) / .5, 1.0)
            if lt < .12:  # вспышка на ударе
                fl = Image.new("RGBA", (W, H), (255, 255, 255, int(200 * (1 - lt / .12)))); c.alpha_composite(fl)
            return c
    # 8.5–10.6: все партнёры + хук
    lt = t - 8.5; c = world("end", lt)
    pos = [(W * .22, H * .2, .30), (W * .5, H * .2, .30), (W * .78, H * .2, .30), (W * .5, H * .335, .42), (W * .5, H * .46, .30)]
    for j, k in enumerate(["shod", "gw", "vol", "love", "dan"]):
        e = back_out(clamp((lt - j * .1) / .35))
        place(c, LOGOS[k], pos[j][0], pos[j][1], pos[j][2] * e, clamp((lt - j * .1) / .15))
    h1 = clamp((lt - .5) / .25); h2 = clamp((lt - .75) / .25)
    place(c, HOOK1, W / 2, H * .62, .9 + .1 * ease_out(h1), h1)
    place(c, HOOK2, W / 2, H * .68, .9 + .1 * ease_out(h2), h2)
    place(c, CTA, W / 2, H * .77, 1, clamp((lt - 1.05) / .25))
    if lt < .12:
        fl = Image.new("RGBA", (W, H), (255, 255, 255, int(200 * (1 - lt / .12)))); c.alpha_composite(fl)
    if lt > 1.9: c.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * clamp((lt - 1.9) / .2)))))
    return c

if __name__ == "__main__":
    import sys
    only = [float(x) for x in sys.argv[1:]]
    if only:
        for t in only: frame(t).convert("RGB").save(f"/home/claude/anim/p_{t:05.2f}.jpg", quality=85)
    else:
        n = int(END * FPS)
        for i in range(n):
            frame(i / FPS).convert("RGB").save(f"{OUT}/{i:04d}.jpg", quality=92)
