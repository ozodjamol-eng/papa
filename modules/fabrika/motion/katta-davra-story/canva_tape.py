import math, os, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS, DUR = 1080, 1920, 30, 15.0
N = int(FPS * DUR)
D = "/home/claude/canva/"
OUT = D + "frames"
os.makedirs(OUT, exist_ok=True)

pages = [Image.open(f"{D}p{i}.png").convert("RGBA") for i in range(1, 6)]
# правка опечатки «Kuniga 3 Marta.» → «kuniga 3 marta»
d = ImageDraw.Draw(pages[2])
d.rectangle([45, 1748, 655, 1842], fill=(238, 18, 111))
f = ImageFont.truetype("/home/claude/fonts/Mont900.ttf", 66)
d.text((72, 1760), "kuniga 3 marta", font=f, fill=(255, 255, 255))

# слои каждой страницы: (y0, y1, тип) — photo = фото-полоса (наезд/параллакс), txt = текст (влёт)
BANDS = [
    [(0, 870, "photo"), (870, 1045, "txt"), (1045, 1560, "big"), (1560, 1920, "txt")],
    [(0, 420, "big"), (420, 1110, "card"), (1110, 1920, "card")],
    [(0, 520, "photo"), (520, 870, "big"), (870, 1500, "photo"), (1500, 1920, "txt")],
    [(0, 620, "card"), (620, 1110, "card"), (1110, 1420, "txt"), (1420, 1660, "big"), (1660, 1920, "txt")],
    [(0, 700, "photo"), (700, 1110, "big"), (1110, 1250, "txt"), (1250, 1450, "big"), (1450, 1920, "txt")],
]
LAYERS = [[(y0, y1, k, p.crop((0, y0, W, y1))) for (y0, y1, k) in b] for p, b in zip(pages, BANDS)]
PAGE_T = [0.0, 3.0, 6.0, 9.0, 12.0]
PAGE_LEN = 3.0
BG = (12, 12, 12, 255)

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def spring(t, k=13.0, z=0.45):
    if t <= 0: return 0.0
    if t >= 2.5: return 1.0
    return 1 - math.exp(-z * k * t) * math.cos(k * math.sqrt(1 - z * z) * t)
def eio(t): t = clamp(t); return t * t * (3 - 2 * t)
def ein(t): t = clamp(t); return t ** 3

def put(c, im, x, y, s=1.0, rot=0.0, a=1.0):
    if a <= 0.01: return
    if abs(s - 1) > 0.005:
        im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BICUBIC)
    if abs(rot) > 0.05:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    if a < 0.99:
        al = im.split()[3].point(lambda v: int(v * a)); im = im.copy(); im.putalpha(al)
    c.alpha_composite(im, (int(x - im.width / 2), int(y - im.height / 2)))

def page_frame(pi, lt):
    """lt — время внутри страницы (0..3). Слои влетают, держатся с живым дрейфом, вылетают."""
    c = Image.new("RGBA", (W, H), BG)
    layers = LAYERS[pi]
    n = len(layers)
    for j, (y0, y1, kind, im) in enumerate(layers):
        cy = (y0 + y1) / 2
        t_in = 0.06 + j * 0.13            # каскад в ритме
        t_out = PAGE_LEN - 0.32 + j * 0.03
        a = clamp((lt - t_in) / 0.06)
        if lt < t_in: continue
        p = spring(lt - t_in)
        side = -1 if j % 2 == 0 else 1
        drift = (lt - t_in)
        if kind == "photo":
            s = 1.22 - 0.22 * eio((lt - t_in) / 0.5) + 0.05 * drift   # наезд + живой зум
            x = W / 2 + side * 18 * math.sin(drift * 1.3)
            y = cy + 12 * math.sin(drift * 1.1)
            rot = 0
            # фото режем по своей полосе, чтобы зум шёл внутри окна
            win = Image.new("RGBA", im.size, (0, 0, 0, 0))
            big = im.resize((int(im.width * s), int(im.height * s)), Image.BICUBIC)
            ox = int((big.width - im.width) / 2 + side * 18 * math.sin(drift * 1.3))
            oy = int((big.height - im.height) / 2 + 10 * math.sin(drift * 1.1))
            win.alpha_composite(big.crop((ox, oy, ox + im.width, oy + im.height)))
            yy = cy + (1 - p) * (-140 if j == 0 else 140)
            put(c, win, W / 2, yy, 1.0, 0, a)
            continue
        if kind == "big":
            s = 1.0 + 0.55 * (1 - p) + 0.012 * math.sin(drift * 6)
            x, y, rot = W / 2, cy, -4 * (1 - p)
        elif kind == "card":
            x = W / 2 + side * 1100 * (1 - p)
            y = cy + 8 * math.sin(drift * 2 + j)
            s, rot = 1.0 + 0.01 * math.sin(drift * 2.2 + j), side * 7 * (1 - p)
        else:
            x = W / 2 + side * 900 * (1 - p)
            y, s, rot = cy, 1.0, 0
        # вылет
        if False:
            o = ein((lt - t_out) / 0.3)
            x -= 1300 * o
            rot += 8 * o
        if pi == 4 and j == len(layers) - 1:
            y += 22 * abs(math.sin(lt * 5))
        put(c, im, x, y, s, rot, a)
    if pi < 4 and lt > PAGE_LEN - 0.32:
        pass
    return c

def camera(c, t, lt):
    # камера не стоит: медленный общий наезд + лёгкий поворот + толчок на входе страницы
    kick = math.exp(-lt * 9) * 0.05 if lt < 0.6 else 0
    z = 1.02 + 0.03 * (lt / PAGE_LEN) + kick
    rot = 0.6 * math.sin(t * 0.8)
    zw, zh = int(W * z), int(H * z)
    im = c.resize((zw, zh), Image.BILINEAR).rotate(rot, resample=Image.BILINEAR, fillcolor=BG)
    return im.crop(((zw - W) // 2, (zh - H) // 2, (zw - W) // 2 + W, (zh - H) // 2 + H))

def vblur(im, k):
    if k < 1.5: return im
    small = im.resize((W, max(8, int(H / k))), Image.BILINEAR)
    return small.resize((W, H), Image.BILINEAR)

WHIP = 0.42   # длительность пролёта
def render(i):
    t = i / FPS
    pi = min(4, int(t // PAGE_LEN))
    lt = t - PAGE_T[pi]
    nxt = pi + 1
    if nxt <= 4 and t > PAGE_T[nxt] - WHIP / 2:
        pass
    # пролёт: от (cut - WHIP/2) до (cut + WHIP/2)
    cut = None
    for k in range(1, 5):
        if PAGE_T[k] - WHIP / 2 <= t < PAGE_T[k] + WHIP / 2:
            cut = k
    if cut is not None:
        u = (t - (PAGE_T[cut] - WHIP / 2)) / WHIP
        off = eio(u) * H
        a_lt = t - PAGE_T[cut - 1]
        b_lt = t - PAGE_T[cut] + 0.45
        A = camera(page_frame(cut - 1, a_lt), t, a_lt)
        B = camera(page_frame(cut, max(0.0, b_lt)), t, max(0.0, b_lt))
        c = Image.new("RGBA", (W, H), BG)
        c.alpha_composite(A, (0, int(-off)))
        c.alpha_composite(B, (0, int(H - off)))
        speed = math.sin(math.pi * clamp(u))
        c = vblur(c, 1 + 14 * speed)
    else:
        c = camera(page_frame(pi, lt + (0.45 if pi > 0 else 0.15)), t, lt)
        # камера плывёт вниз внутри страницы
        dy = int(30 * math.sin(lt / PAGE_LEN * math.pi))
        c = c.transform((W, H), Image.AFFINE, (1, 0, 0, 0, 1, -dy), resample=Image.BILINEAR, fillcolor=BG)
    c.convert("RGB").save(f"{OUT}/f{i:04d}.jpg", quality=93)

if __name__ == "__main__":
    a, b = int(sys.argv[1]), int(sys.argv[2])
    for i in range(a, min(b, N)): render(i)
