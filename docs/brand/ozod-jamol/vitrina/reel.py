# Ролик-витрина OZOD JAMOL «КРАСНАЯ ЛИНИЯ» — 2D-сборка всех сцен (1080x1920, 30 fps)
# запуск: python reel.py <start_frame> <end_frame>
import sys, os, math, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
W, H, FPS = 1080, 1920, 30
RED = (255, 16, 36); WHITE = (255, 255, 255); GRAY = (170, 170, 175)
M9 = '/home/claude/fonts/Montserrat-900.ttf'; M8 = '/home/claude/fonts/Montserrat-800.ttf'; M5 = '/home/claude/fonts/Montserrat-500.ttf'
U9 = '/home/claude/b3d/Unbounded-900.ttf'; U4 = '/home/claude/b3d/Unbounded-400.ttf'
OUT = '/home/claude/reel/fr'; os.makedirs(OUT, exist_ok=True)
# --- таймлайн (секунды) ---
T_S2, T_S3, T_S4, T_S5, T_S6, T_S7, T_END = 2.0, 6.0, 12.0, 17.0, 22.0, 26.0, 30.0
TR = 0.27  # длительность перехода «красная линия»
rng = np.random.default_rng(7)
_fc = {}
def font(p, s):
    k = (p, s)
    if k not in _fc: _fc[k] = ImageFont.truetype(p, s)
    return _fc[k]
_tc = {}
def text(txt, p, s, fill=WHITE, track=0.0):
    k = (txt, p, s, fill, track)
    if k in _tc: return _tc[k]
    f = font(p, s); d = ImageDraw.Draw(Image.new('L', (1, 1)))
    wds = [d.textlength(c, font=f) for c in txt]; tw = sum(wds) + track * s * (len(txt) - 1)
    im = Image.new('RGBA', (int(tw) + s, int(s * 1.6)), (0, 0, 0, 0)); dd = ImageDraw.Draw(im); x = s // 2
    for c, wd in zip(txt, wds): dd.text((x, int(s * 0.15)), c, font=f, fill=fill + (255,)); x += wd + track * s
    im = im.crop(im.getbbox()); _tc[k] = im; return im
def eo(x): x = min(max(x, 0), 1); return 1 - (1 - x) ** 3
def eio(x): x = min(max(x, 0), 1); return x * x * (3 - 2 * x)
def eback(x, s=1.7):
    x = min(max(x, 0), 1) - 1; return x * x * ((s + 1) * x + s) + 1
def alpha(im, a):
    if a >= 0.999: return im
    im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v: int(v * max(a, 0)))); return im
def put(c, im, cx, cy, a=1.0, s=1.0, rot=0.0, maxw=W * 0.9):
    if a <= 0.01 or s <= 0.01: return
    if im.width * s > maxw and not rot: s = maxw / im.width
    if abs(s - 1) > 0.003: im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BICUBIC)
    if rot: im = im.rotate(rot, Image.BICUBIC, expand=True)
    c.alpha_composite(alpha(im, a), (int(cx - im.width / 2), int(cy - im.height / 2)))
def glow(im, rad, col=RED, k=1.0):
    pad = rad * 3; a = Image.new('L', (im.width + 2 * pad, im.height + 2 * pad), 0); a.paste(im.getchannel('A'), (pad, pad))
    g = Image.new('RGBA', a.size, col + (0,)); g.putalpha(a.filter(ImageFilter.GaussianBlur(rad)).point(lambda v: min(255, int(v * k)))); g.alpha_composite(im, (pad, pad)); return g
def load(p, size=(W, H)):
    return Image.open(p).convert('RGBA').resize(size, Image.LANCZOS)
def load3d(folder, f, last):
    f = min(f, last)
    if f % 2 == 0 or f + 1 > last: return load(f'{folder}/f{f - (f % 2):03d}.png')
    return Image.blend(load(f'{folder}/f{f - 1:03d}.png'), load(f'{folder}/f{f + 1:03d}.png'), 0.5)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
def radial_bg(cx, cy, col=(0.10, 0.02, 0.03), r0=1.9):
    r = np.sqrt(((xx - cx) / H) ** 2 + ((yy - cy) / H) ** 2); base = np.array([0.008, 0.008, 0.009])
    a = base + (np.array(col) - base) * np.clip(1 - r * r0, 0, 1)[..., None] ** 1.6
    return Image.fromarray((a * 255).astype(np.uint8)).convert('RGBA')
BG_C = radial_bg(W / 2, H * 0.45)
BG_DARK = radial_bg(W / 2, H * 0.5, (0.035, 0.02, 0.022))
# диагональ бренда: 45° снизу-слева вверх-вправо
DX, DY = 0.7071, -0.7071
def red_line(c, p0, p1, width=10, a=1.0, glowr=26):
    """отрезок красной линии с неоновым ореолом"""
    L = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    d.line([p0, p1], fill=RED + (255,), width=width)
    g = L.filter(ImageFilter.GaussianBlur(glowr)); core = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(core).line([p0, p1], fill=(255, 200, 205, 255), width=max(2, width // 3))
    out = Image.new('RGBA', (W, H), (0, 0, 0, 0)); out.alpha_composite(g); out.alpha_composite(g); out.alpha_composite(L); out.alpha_composite(core)
    c.alpha_composite(alpha(out, a))
def diag_pts(off, length=3000):
    """линия 45° через центр, смещённая перпендикулярно на off"""
    cx, cy = W / 2 + off * 0.7071, H / 2 + off * 0.7071
    return (cx - DX * length, cy - DY * length), (cx + DX * length, cy + DY * length)
def wipe(a, b, p):
    """переход: красная линия идёт по диагонали, за ней — следующая сцена"""
    D = (W + H) * 0.7071; off = -D / 2 - 200 + p * (D + 400)
    m = Image.fromarray(((((xx - W / 2) * 0.7071 + (yy - H / 2) * 0.7071) < off) * 255).astype(np.uint8))
    out = a.copy(); out.paste(b, (0, 0), m)
    p0, p1 = diag_pts(off); red_line(out, p0, p1, 14, 1.0, 30)
    return out
# ---------- СЦЕНА 1: хук «УЧ СОНИЯ» ----------
def s1(t):
    c = BG_DARK.copy()
    # линия разрезает кадр 0.0–0.25
    p = eo(t / 0.25); L = 1600 * p
    if t < 0.6:
        p0, p1 = diag_pts(0, L); red_line(c, p0, p1, 12, 1.0 - max(0, (t - 0.4) / 0.2))
    # «3» огромная из разреза
    if t > 0.12:
        q = eback((t - 0.12) / 0.35); im = glow(text('3', M9, 900, WHITE), 40, RED, 0.8)
        sh = (rng.normal(0, 1, 2) * 10 * max(0, 1 - (t - 0.12) / 0.25))
        put(c, im, W / 2 + sh[0], H * 0.42 + sh[1], min(1, (t - 0.12) / 0.1), 0.6 + 0.4 * q - 0.03 * max(0, t - 0.6))
    if t > 0.45:
        q = eo((t - 0.45) / 0.3); put(c, text('СОНИЯ', U9 if False else M9, 150, RED, 0.12), W / 2, H * 0.66 + (1 - q) * 60, q)
    return c
# ---------- СЦЕНА 2: лента листается, слова бьют ----------
FEED = None
def make_card(i):
    r = np.random.default_rng(100 + i); w, h = 860, 1300
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    g = int(r.uniform(28, 48)); d.rounded_rectangle((0, 0, w - 1, h - 1), 48, fill=(g, g, g + 3, 255))
    d.rounded_rectangle((40, 40, w - 40, h - 330), 30, fill=(g + 18, g + 18, g + 22, 255))
    d.ellipse((40, h - 290, 120, h - 210), fill=(90, 90, 95, 255)); d.rounded_rectangle((140, h - 270, 520, h - 240), 12, fill=(85, 85, 90, 255))
    d.rounded_rectangle((40, h - 180, w - 160, h - 150), 12, fill=(70, 70, 75, 255)); d.rounded_rectangle((40, h - 120, w - 300, h - 90), 12, fill=(60, 60, 65, 255))
    return im
CARDS = [make_card(i) for i in range(6)]
WORDS = [('ОДАМЛАР', 0.1), ('ШУНЧА', 0.6), ('ВАҚТДА', 1.05), ('ВАРАҚЛАБ', 1.53), ('ЎТИБ', 2.15), ('КЕТАДИ', 2.5)]
def s2(t):
    c = BG_DARK.copy()
    # лента: скорость растёт, на 3.55 — стоп
    stop = 3.35; tt = min(t, stop); pos = 900 * tt + 900 * tt * tt * 0.9
    speed = 900 + 1800 * tt * 0.9 if t < stop else 0
    nblur = 6 if speed > 1500 else 3
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for k in range(-1, 3):
        idx = int(pos // 1380) + k; y = H / 2 + k * 1380 - (pos % 1380)
        im = CARDS[idx % 6]
        for b in range(nblur if t < stop else 1):
            put(layer, im, W / 2, y + b * speed / FPS / nblur, 1.0 / (b + 1) ** 0.6)
    dim = 0.55 if t < stop else 0.55 + 0.25 * eo((t - stop) / 0.3)
    layer = alpha(layer, 1 - dim * 0.6); c.alpha_composite(layer)
    # слова
    for i, (wd, t0) in enumerate(WORDS):
        if t >= t0 and (i == len(WORDS) - 1 or t < WORDS[i + 1][1] + 0.05) and t < stop:
            q = (t - t0) / 0.22; s = 1.8 - 0.8 * eo(q)
            im = text(wd, M9, 175 if len(wd) < 7 else 150, WHITE if i % 2 == 0 else RED)
            put(c, im, W / 2, H * 0.5, min(1, q * 3), s, rot=(-4 if i % 2 else 3) * (1 - eo(q)))
    # стоп: красная линия режет ленту, кадр «замерзает»
    if t >= stop:
        q = eo((t - stop) / 0.18); p0, p1 = diag_pts(0, 1700 * q); red_line(c, p0, p1, 12, 1.0)
        if t > stop + 0.12:
            q2 = eo((t - stop - 0.12) / 0.3)
            put(c, glow(text('ТЎХТАТАМИЗ', M9, 150, WHITE), 30, RED, 0.7), W / 2, H * 0.5, q2, 1.25 - 0.25 * q2)
            put(c, text('БИЗ УЛАРНИ', M8, 70, RED, 0.25), W / 2, H * 0.5 - 140, q2)
    return c
# ---------- СЦЕНА 3: 3D-флакон + выноски ----------
def callout(c, ax, ay, bx, by, label, sub, p, left):
    if p <= 0: return
    d = ImageDraw.Draw(c); q1 = eo(p / 0.35); q2 = eo((p - 0.3) / 0.35)
    d.ellipse((ax - 9, ay - 9, ax + 9, ay + 9), outline=RED + (255,), width=4)
    d.ellipse((ax - 4, ay - 4, ax + 4, ay + 4), fill=WHITE + (255,))
    mx, my = ax + (bx - ax) * q1, ay + (by - ay) * q1; d.line([(ax, ay), (mx, my)], fill=WHITE + (230,), width=3)
    if q2 > 0:
        ex = bx + (-1 if left else 1) * 230 * q2; d.line([(bx, by), (ex, by)], fill=WHITE + (230,), width=3)
        im = glow(text(label, M9, 44, WHITE, 0.08), 10, (0, 0, 0), 1.6); im2 = glow(text(sub, M5, 30, (215, 215, 220), 0.05), 8, (0, 0, 0), 1.8)
        def X(w): return max(40, min(W - 40 - w, (ex - w if left else bx + 30)))
        put(c, im, X(im.width) + im.width / 2, by - 36, q2)
        put(c, im2, X(im2.width) + im2.width / 2, by + 32, q2)
def s3(t):
    im = load3d('/home/claude/reel/b3', int(t * FPS), 148)
    c = im.copy()
    # подпись сверху
    q = eo((t - 0.6) / 0.4); put(c, text('3D ВИЗУАЛИЗАЦИЯ', M9, 74, WHITE, 0.06), W / 2, 230 + (1 - q) * 30, q)
    put(c, text('ИСТАЛГАН МАҲСУЛОТ — СТУДИЯ НУРИДА', M5, 32, GRAY, 0.12), W / 2, 310, eo((t - 0.85) / 0.4))
    callout(c, 600, 555, 820, 430, 'ҚОПҚОҚ', 'металл ялтироқлиги', (t - 1.3) / 0.9, False)
    callout(c, 300, 1000, 330, 860, 'ШИША', 'ҳақиқий синиш', (t - 1.9) / 0.9, True)
    callout(c, 620, 1680, 760, 1560, 'АКС', 'ойнадек пол', (t - 2.5) / 0.9, False)
    return c
# ---------- СЦЕНА 4: «ҲАР ҚАНДАЙ УСЛУБДА» — монтаж стилей по долям ----------
def glitch_word(t):
    c = BG_DARK.copy(); im = text('GLITCH', U9, 170, WHITE)
    base = Image.new('RGBA', (W, H), (0, 0, 0, 0)); put(base, im, W / 2, H / 2)
    a = np.asarray(base).astype(np.int16); o = np.zeros_like(a); sh = int(18 + 14 * math.sin(t * 40))
    o[..., 0] = np.roll(a[..., 0], sh, 1); o[..., 1] = a[..., 1]; o[..., 2] = np.roll(a[..., 2], -sh, 1); o[..., 3] = np.maximum.reduce([np.roll(a[..., 3], sh, 1), a[..., 3], np.roll(a[..., 3], -sh, 1)])
    r = np.random.default_rng(int(t * 30))
    for _ in range(7):
        y0 = r.integers(700, 1200); hh = r.integers(10, 60); o[y0:y0 + hh] = np.roll(o[y0:y0 + hh], r.integers(-80, 80), 1)
    c.alpha_composite(Image.fromarray(np.clip(o, 0, 255).astype(np.uint8))); return c
def neon_word(t):
    c = BG_DARK.copy(); im = text('NEON', U9, 210, (255, 60, 80)); fl = 1.0 if (int(t * 30) % 7) else 0.4
    put(c, glow(glow(im, 18, RED, 1.2), 50, RED, 0.9), W / 2, H / 2, fl); return c
def frames3d(folder, f0, f1, t, dur, opaque=False):
    f = int(f0 + (f1 - f0) * min(1, t / dur)); im = load(f'{folder}/f{f:03d}.png')
    if opaque: return im
    c = BG_C.copy(); c.alpha_composite(im); return c
def type_word(t):
    c = BG_DARK.copy(); words = ['TYPO', 'GRA', 'FIKA']
    for i, w in enumerate(words):
        q = eo((t - i * 0.1) / 0.2); put(c, text(w, U9, 190, WHITE if i != 1 else RED), W / 2 + (1 - q) * (300 if i % 2 else -300), H / 2 - 230 + i * 230, q)
    return c
CUTS = [  # (длит., функция, подпись)
    (0.5, lambda t: frames3d('/home/claude/o3d/F3', 20, 52, t, 0.5), '3D'),
    (0.5, glitch_word, 'GLITCH'),
    (0.5, lambda t: frames3d('/home/claude/o3d/F2', 4, 30, t, 0.5, True), 'LAZER'),
    (0.5, neon_word, 'NEON'),
    (0.5, type_word, 'TIPOGRAFIKA'),
    (0.5, lambda t: frames3d('/home/claude/o3d/F1', 30, 52, t, 0.5), 'ANIMATSIYA'),
    (0.5, lambda t: frames3d('/home/claude/o3d/F3', 26, 50, t, 0.5), 'ZARRALAR'),
]
TILES = None
def s4(t):
    global TILES
    if TILES is None: TILES = [CUTS[k][1](0.45) for k in range(6)]
    acc = 0
    for i, (d, fn, lab) in enumerate(CUTS):
        if t < acc + d or i == len(CUTS) - 1:
            lt = t - acc
            c = fn(lt) if t < acc + d else None
            break
        acc += d
    if t >= sum(d for d, _, _ in CUTS):
        # финал сцены: все стили сжимаются в сетку + надпись
        tt = t - sum(d for d, _, _ in CUTS); c = BG_DARK.copy()
        tiles = TILES; TW, TH = 450, 470
        def tile(k, tw, th, rr):
            tl = tiles[k]; r = tw / th
            if r > W / H: ch = W / r; src = tl.crop((0, int((H - ch) / 2), W, int((H + ch) / 2)))
            else: cw = H * r; src = tl.crop((int((W - cw) / 2), 0, int((W + cw) / 2), H))
            im = src.resize((tw, th), Image.BICUBIC); m = Image.new('L', im.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, tw - 1, th - 1), rr, fill=255); im.putalpha(m); return im
        def slot(k): return W / 2 + ((k % 2) - 0.5) * 480, H / 2 + ((k // 2) - 1) * 500 - 90
        for k in range(5):
            q = eback((tt - 0.12 - k * 0.05) / 0.3)
            if q > 0: x, y = slot(k); put(c, tile(k, TW, TH, 28), x, y, min(1, (tt - 0.12 - k * 0.05) * 6), q, maxw=99999)
        q = eo(tt / 0.45); x, y = slot(5)
        put(c, tile(5, int(W + (TW - W) * q), int(H + (TH - H) * q), int(28 * q)), W / 2 + (x - W / 2) * q, H / 2 + (y - H / 2) * q, 1, maxw=99999)
        q2 = eo((tt - 0.35) / 0.35)
        put(c, glow(text('ҲАР ҚАНДАЙ УСЛУБДА', M9, 82, WHITE, 0.04), 24, RED, 0.6), W / 2, 1735, q2, 1.15 - 0.15 * q2)
        return c
    # метка стиля
    lab = text(lab, U4, 40, RED, 0.3); put(c, lab, W / 2, H * 0.84, 1)
    put(c, text(f'0{i + 1}', U9, 40, WHITE), W / 2, H * 0.80, 0.8)
    return c
# ---------- СЦЕНА 5: аудитория — график и счётчики ----------
def s5(t):
    c = BG_DARK.copy(); d = ImageDraw.Draw(c)
    # сетка
    for k in range(9):
        y = 620 + k * 100; d.line([(90, y), (W - 90, y)], fill=(255, 255, 255, 18), width=2)
    # растущая кривая из красной линии
    n = 60; p = eo(t / 2.6); pts = []
    for i in range(int(n * p) + 1):
        u = i / n; y = 1400 - 760 * (u ** 1.7) - 35 * math.sin(u * 14) * (1 - u)
        pts.append((90 + u * (W - 180), y))
    if len(pts) > 1:
        L = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(L).line(pts, fill=RED + (255,), width=12, joint='curve')
        c.alpha_composite(L.filter(ImageFilter.GaussianBlur(22))); c.alpha_composite(L)
        # заливка под кривой
        poly = pts + [(pts[-1][0], 1420), (pts[0][0], 1420)]; F = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(F).polygon(poly, fill=RED + (40,)); c.alpha_composite(F)
        hx, hy = pts[-1]; d.ellipse((hx - 16, hy - 16, hx + 16, hy + 16), fill=WHITE + (255,))
    # счётчики
    def counter(val, lab, x, y, t0):
        q = eo((t - t0) / 1.6)
        if t < t0: return
        v = val if q > 0.99 else int(val * q); s = f'{v // 1000}K' if v >= 1000 else str(v)
        put(c, glow(text(s + ('+' if q > 0.99 else ''), M9, 150, WHITE), 26, RED, 0.5), x, y, min(1, (t - t0) * 4))
        put(c, text(lab, M8, 36, RED, 0.18), x, y + 105, min(1, (t - t0) * 3))
    counter(575000, 'YOUTUBE', W * 0.5, 330, 0.3)
    counter(238000, 'INSTAGRAM', W * 0.5, 1560, 1.2)
    if t > 3.2:
        q = eo((t - 3.2) / 0.4); put(c, text('ЯРИМ МИЛЛИОН АУДИТОРИЯ', M9, 50, WHITE, 0.04), W / 2, 1790, q, 1.1 - 0.1 * q)
    return c
# ---------- СЦЕНА 6: 3D-телефон ----------
HEART = None
def heart(s, col=RED):
    im = Image.new('RGBA', (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im); r = s * 0.27
    d.ellipse((s * 0.5 - 2 * r, s * 0.3 - r, s * 0.5, s * 0.3 + r), fill=col + (255,)); d.ellipse((s * 0.5, s * 0.3 - r, s * 0.5 + 2 * r, s * 0.3 + r), fill=col + (255,))
    d.polygon([(s * 0.5 - 2 * r + 2, s * 0.36), (s * 0.5 + 2 * r - 2, s * 0.36), (s * 0.5, s * 0.92)], fill=col + (255,)); return im
HE = heart(120); HE2 = heart(120, WHITE)
HSEED = [(np.random.default_rng(i).uniform(1.3, 3.6), (np.random.default_rng(i + 50).uniform(120, 280) if i % 2 else np.random.default_rng(i + 50).uniform(800, 960)), np.random.default_rng(i + 90).uniform(0.45, 0.85)) for i in range(16)]
def s6(t):
    c = load3d('/home/claude/reel/b6', int(t * FPS) + 14, 118)
    for i, (t0, x, s) in enumerate(HSEED):
        lt = t - t0
        if 0 < lt < 1.4:
            y = 1500 - lt * 700; a = min(1, lt * 5) * (1 - max(0, lt - 1.0) / 0.4)
            put(c, glow(HE if i % 3 else HE2, 14, RED, 0.6), x + 60 * math.sin(lt * 4 + i), y, a, s * (0.6 + 0.4 * eback(lt / 0.3)))
    q = eo((t - 0.9) / 0.4); put(c, text('REELS  •  REKLAMA  •  INTRO', U4, 40, WHITE, 0.12), W / 2, 1745 + (1 - q) * 30, q)
    return c
# ---------- СЦЕНА 7: призыв ----------
def s7(t):
    c = BG_C.copy()
    lines = [('БИЗНЕСНИ', WHITE, 0.0), ('ҲАРАКАТГА', RED, 0.18), ('КЕЛТИРАМИЗ', WHITE, 0.36)]
    for i, (wd, col, t0) in enumerate(lines):
        q = eback((t - t0) / 0.4)
        if t > t0: put(c, text(wd, M9, 140 if i != 2 else 128, col), W / 2 + (1 - q) * (-500 if i % 2 == 0 else 500), 640 + i * 170, min(1, (t - t0) * 5))
    if t > 1.1:
        q = eo((t - 1.1) / 0.5); p0, p1 = (W / 2 - 380 * q, 1180), (W / 2 + 380 * q, 1180); red_line(c, p0, p1, 6, 1, 14)
    if t > 1.4:
        q = eo((t - 1.4) / 0.45); put(c, text('MOTION GRAFIKA XIZMATLARI', U4, 38, GRAY, 0.22), W / 2, 1270 + (1 - q) * 20, q)
    if t > 1.75:
        q = eo((t - 1.75) / 0.45); put(c, glow(text('Telegram  @Ozodjamol', U9, 60, RED, 0.04), 18, RED, 0.5), W / 2, 1390 + (1 - q) * 20, q)
    return c
# ---------- КОНЦОВКА: интро OZOD JAMOL (кадры готовы) ----------
def send(t):
    f = min(239, int(t * FPS)); return load(f'/home/claude/intro/fr916/f{f:04d}.png')
SC = [(0, T_S2, s1), (T_S2, T_S3, s2), (T_S3, T_S4, s3), (T_S4, T_S5, s4), (T_S5, T_S6, s5), (T_S6, T_S7, s6), (T_S7, T_END, s7), (T_END, T_END + 8, send)]
def frame(t):
    for i, (a, b, fn) in enumerate(SC):
        if a <= t < b:
            c = fn(t - a)
            # переход в начало следующей сцены (кроме перехода в концовку — у неё своё начало из темноты)
            if i + 1 < len(SC) and t > b - TR and i + 1 != 7 and i != 0:
                c = wipe(c, SC[i + 1][2](0.0), (t - (b - TR)) / TR)
            if i == 6 and t > b - 0.3:  # затемнение перед концовкой
                k = 1 - (t - (b - 0.3)) / 0.3; c = Image.fromarray((np.asarray(c.convert('RGB')).astype(np.float32) * k).astype(np.uint8)).convert('RGBA')
            return c
    return send(7.99)
def post(c, t, f):
    a = np.asarray(c.convert('RGB')).astype(np.float32)
    if t < T_END:
        # лёгкие хром. аберрации на ударах сцен
        hit = max([math.exp(-abs(t - b) * 18) for b in (T_S2, T_S3, T_S4, T_S5, T_S6, T_S7)])
        if hit > 0.05:
            s = int(10 * hit); a[..., 0] = np.roll(a[..., 0], s, 1); a[..., 2] = np.roll(a[..., 2], -s, 1)
        a += np.random.default_rng(f).normal(0, 1.6, (H, W, 1))
        a *= np.clip(1 - ((xx / W - 0.5) ** 2 + (yy / H - 0.5) ** 2) * 0.8, 0, 1)[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
if __name__ == '__main__':
    a, b = int(sys.argv[1]), int(sys.argv[2])
    for f in range(a, b):
        t = f / FPS; post(frame(t), t, f).save(f'{OUT}/f{f:04d}.png', compress_level=1)
    print('ok', a, b)
