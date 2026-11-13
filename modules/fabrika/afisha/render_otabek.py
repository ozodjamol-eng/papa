# Шаблон «Концертная афиша с озвучкой» — Отабек Муҳаммадзоҳид (13.11.2026)
# python3 -I render_afisha.py stills | full
import cv2, numpy as np, subprocess, math, random, sys, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
V = 4.5                 # старт диктора: ≥4 с музыки до голоса (правило владельца 13.11)
VEND = V + 24.03
DUR = 31.5
BEAT = float(os.environ.get("BEAT", 0.441)); PH = float(os.environ.get("PHASE", 0.0))
WD = "/home/claude/work"
BLK = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
XB = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
SCR = WD + "/fonts/KaushanScript-Regular.ttf"
PF = WD + "/fonts/PlayfairDisplay[wght].ttf"
BOD = "/home/claude/papa/.claude/skills/awesome-ai-motion/lib/fonts/BodoniModa.ttf"
GOLD = np.array([0.93, 0.72, 0.33], np.float32)
rnd = random.Random(7); nrs = np.random.RandomState(7)


def font(path, size):
    f = ImageFont.truetype(path, size)
    if path == PF:
        f.set_variation_by_axes([900])
    if path == BOD:
        try: f.set_variation_by_name("Black")
        except Exception: pass
    return f


def ease(x): x = min(max(x, 0), 1); return 1 - (1 - x) ** 3
def eio(x): x = min(max(x, 0), 1); return x * x * (3 - 2 * x)
def win(t, a, b, fi=0.4, fo=0.3):
    if t < a or t > b: return 0.0
    return min(ease((t - a) / fi), 1.0 if fo <= 0 else min(1, (b - t) / fo))
def app(t, a, d=0.5): return ease((t - a) / d)


def mask_text(text, f, tr=0, pad=70):
    ws = [f.getlength(c) for c in text]
    tw = int(sum(ws) + tr * (len(text) - 1)); asc, desc = f.getmetrics()
    im = Image.new("L", (tw + 2 * pad, asc + desc + 2 * pad), 0); d = ImageDraw.Draw(im); x = pad
    for c, w in zip(text, ws):
        d.text((x, pad), c, font=f, fill=255); x += w + tr
    return np.asarray(im, np.float32) / 255


def gold_fill(m):
    """вертикальный золотой градиент по высоте букв"""
    ys = np.where(m.max(1) > 0.05)[0]; y0, y1 = (ys[0], ys[-1]) if len(ys) else (0, m.shape[0] - 1)
    g = np.clip((np.arange(m.shape[0]) - y0) / max(1, y1 - y0), 0, 1)
    stops = [(0, (1.0, 0.95, 0.72)), (0.35, (0.96, 0.78, 0.38)), (0.62, (0.72, 0.48, 0.14)), (0.8, (0.98, 0.84, 0.47)), (1, (0.80, 0.56, 0.20))]
    col = np.zeros((m.shape[0], 3), np.float32)
    for i in range(3):
        col[:, i] = np.interp(g, [s[0] for s in stops], [s[1][i] for s in stops])
    return np.repeat(col[:, None, :], m.shape[1], 1)


def layer(m, rgb, shadow=0.75, glow=None):
    """маска + цвет → RGBA со своей тенью (тёмная подложка) и, при желании, свечением"""
    sh = cv2.GaussianBlur(m, (0, 0), 7) * shadow
    a = np.maximum(m, sh)
    c = rgb * (m / np.maximum(a, 1e-4))[..., None]
    L = np.dstack([c, a]).astype(np.float32)
    G = None
    if glow is not None:
        G = (cv2.GaussianBlur(m, (0, 0), 22)[..., None] * np.array(glow, np.float32)).astype(np.float32)
    return L, G, m


def gtext(text, path, size, tr=0, glow=(0.5, 0.33, 0.08)):
    m = mask_text(text, font(path, size), tr); return layer(m, gold_fill(m), glow=glow)


def wtext(text, path, size, tr=0, col=(1, 1, 1)):
    m = mask_text(text, font(path, size), tr)
    return layer(m, np.ones(m.shape + (3,), np.float32) * np.array(col, np.float32))


def blit(fr, L, cx, cy, alpha=1.0, scale=1.0, wipe=None, shine=None):
    """L=(rgba, glow, mask). wipe 0..1 — проявление слева направо. shine 0..1 — блик по буквам."""
    if alpha <= 0.003: return
    rgba, G, m = L
    if abs(scale - 1) > 1e-3:
        sz = (max(1, int(rgba.shape[1] * scale)), max(1, int(rgba.shape[0] * scale)))
        rgba = cv2.resize(rgba, sz, interpolation=cv2.INTER_LINEAR)
        G = cv2.resize(G, sz) if G is not None else None; m = cv2.resize(m, sz)
    h, w = rgba.shape[:2]; x0 = int(cx - w / 2); y0 = int(cy - h / 2)
    xa, ya = max(0, x0), max(0, y0); xb, yb = min(W, x0 + w), min(H, y0 + h)
    if xa >= xb or ya >= yb: return
    sl = (slice(ya - y0, yb - y0), slice(xa - x0, xb - x0))
    k = np.full((1, xb - xa, 1), alpha, np.float32)
    if wipe is not None:
        xs = (np.arange(xa - x0, xb - x0) / w)[None, :, None]
        k = k * np.clip((wipe * 1.25 - xs) / 0.12, 0, 1)
    if G is not None:
        fr[ya:yb, xa:xb] += G[sl] * k * 0.8
    a = rgba[sl][..., 3:4] * k
    fr[ya:yb, xa:xb] = fr[ya:yb, xa:xb] * (1 - a) + rgba[sl][..., :3] * a
    if shine is not None and 0 < shine < 1:
        xs = np.arange(xa - x0, xb - x0)[None, :]; ys = np.arange(ya - y0, yb - y0)[:, None]
        band = np.exp(-(((xs - ys * 0.35) - (shine * (w + 300) - 150)) / 55.0) ** 2)
        fr[ya:yb, xa:xb] += (band * m[sl] * alpha)[..., None] * np.array([1, 0.95, 0.8], np.float32) * 0.9


# ───────── ФОН: зал ─────────
def bokeh_layer(n, rmin, rmax, bright, rows, seed):
    r = random.Random(seed); BW, BH = W + 240, H + 240
    im = np.zeros((BH, BW, 3), np.float32)
    for _ in range(n):
        row = r.choice(rows); x = r.uniform(0, BW); y = row * BH + r.gauss(0, 26)
        rad = r.uniform(rmin, rmax); b = bright * r.uniform(0.45, 1.0)
        col = np.array([1.0, r.uniform(0.62, 0.82), r.uniform(0.25, 0.45)], np.float32) * b
        cv2.circle(im, (int(x), int(y)), int(rad), tuple(float(c) for c in col), -1, cv2.LINE_AA)
    return im

BOK = [cv2.GaussianBlur(bokeh_layer(70, 10, 22, 0.55, [0.08, 0.16, 0.25, 0.36, 0.47, 0.58], 1), (0, 0), 13),
       cv2.GaussianBlur(bokeh_layer(46, 16, 34, 0.50, [0.12, 0.22, 0.33, 0.45, 0.60], 2), (0, 0), 22),
       cv2.GaussianBlur(bokeh_layer(22, 30, 60, 0.30, [0.10, 0.30, 0.52, 0.70], 3), (0, 0), 38)]

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
BASE = np.zeros((H, W, 3), np.float32)
rad = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H * 0.36) / (H * 0.5)) ** 2)
BASE[:] = np.array([0.30, 0.16, 0.06], np.float32)
BASE *= np.clip(1.15 - rad, 0.05, 1)[..., None] ** 1.6
VIG = np.clip(1.12 - 0.85 * (((xx / W - .5) ** 2 + (yy / H - .5) ** 2) / .5), 0, 1)[..., None]


def beam(angle_deg, x_top, width, length=1700):
    """мягкий конус света сверху"""
    a = math.radians(angle_deg); dx, dy = math.sin(a), math.cos(a)
    px = xx - x_top; py = yy + 80
    along = px * dx + py * dy; across = -px * dy + py * dx
    wdt = 20 + along * width
    b = np.exp(-(across / np.maximum(wdt, 1)) ** 2) * np.clip(along / 200, 0, 1) * np.clip(1 - along / length, 0, 1)
    return (b[..., None] * np.array([1.0, 0.82, 0.5], np.float32)).astype(np.float32)

BEAMS = [beam(-17, 900, 0.16), beam(15, 160, 0.17), beam(-4, 610, 0.11), beam(24, -60, 0.14)]

# арка
def arch():
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    x0, x1, yt, yb = 120, 960, 255, 1420; r = (x1 - x0) // 2
    d.rounded_rectangle([x0, yt, x1, yb + 400], r, outline=255, width=9)
    d.rounded_rectangle([x0 + 34, yt + 34, x1 - 34, yb + 400], r - 34, outline=150, width=4)
    return np.asarray(im, np.float32) / 255
ARCH = arch(); ARCH_G = cv2.GaussianBlur(ARCH, (0, 0), 16)
ARCH_COL = gold_fill(np.ones((H, W), np.float32))

# ───────── АРТИСТ ─────────
cut = np.asarray(Image.open(WD + "/cut.png").convert("RGBA"), np.float32) / 255
SC = 2.2; AW = int(447 * SC)
art = cv2.resize(cut, (AW, AW), interpolation=cv2.INTER_LANCZOS4)
bl = cv2.GaussianBlur(art[..., :3], (0, 0), 1.8)
art[..., :3] = np.clip(art[..., :3] * 1.4 - bl * 0.4, 0, 1)
art[..., 3] = np.clip(cv2.GaussianBlur(art[..., 3], (0, 0), 1.0) * 1.15 - 0.08, 0, 1)
ay = np.arange(AW, dtype=np.float32)[:, None]
art[..., 3] *= np.clip((AW - 8 - ay) / 150, 0, 1)        # низ растворяется
ART_RIM = cv2.GaussianBlur(art[..., 3], (0, 0), 30)
ART_CX, ART_CY = W // 2, 300 + AW // 2

# нижняя тёмная панель под тексты
PANEL = (np.clip((yy - 960) / 250, 0, 1) ** 1.2 * 0.93)[..., None]
# пыль
DUST = [(rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(14, 46), rnd.uniform(1.2, 3.6), rnd.uniform(0, 6.28), rnd.uniform(0.35, 1.0)) for _ in range(150)]
GRAIN = [nrs.normal(0, 0.010, (H // 2, W // 2, 1)).astype(np.float32) for _ in range(6)]


def ribbon(text, size=37, w=1020, h=78):
    im = np.zeros((h + 80, w + 80, 4), np.float32)
    g = gold_fill(np.ones((h, w), np.float32))
    xs = np.linspace(-1, 1, w, dtype=np.float32)[None, :]
    a = np.clip((1 - np.abs(xs)) / 0.10, 0, 1) * np.ones((h, 1), np.float32)
    im[40:40 + h, 40:40 + w, :3] = g; im[40:40 + h, 40:40 + w, 3] = a
    m = mask_text(text, font(BLK, size), 0.5, pad=10)
    mh, mw = m.shape; ox = (im.shape[1] - mw) // 2; oy = (im.shape[0] - mh) // 2 - 2
    reg = im[oy:oy + mh, ox:ox + mw]
    reg[..., :3] = reg[..., :3] * (1 - m[..., None]) + np.array([0.09, 0.05, 0.02], np.float32) * m[..., None]
    sh = cv2.GaussianBlur(im[..., 3], (0, 0), 12) * 0.6
    a2 = np.maximum(im[..., 3], sh)
    im[..., :3] *= (im[..., 3] / np.maximum(a2, 1e-4))[..., None]; mm = im[..., 3].copy(); im[..., 3] = a2
    return im, None, mm


def chip(day, tm, w=490, h=112):
    im = Image.new("RGBA", (w + 60, h + 60), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([30, 30, 30 + w, 30 + h], 26, fill=(26, 12, 6, 240), outline=(236, 184, 84, 255), width=5)
    f1 = font(BLK, 44); f2 = font(BLK, 44)
    t1 = day + " DEKABR"; w1 = f1.getlength(t1); w2 = f2.getlength(tm); gap = 44
    x = 30 + (w - (w1 + gap + w2)) / 2; y = 30 + (h - 44) / 2 - 7
    d.text((x, y), t1, font=f1, fill=(244, 200, 104, 255))
    d.line([x + w1 + gap / 2, 30 + 26, x + w1 + gap / 2, 30 + h - 26], fill=(236, 184, 84, 255), width=4)
    d.text((x + w1 + gap, y), tm, font=f2, fill=(255, 255, 255, 255))
    a = np.asarray(im, np.float32) / 255
    return a, None, a[..., 3]


def pill(text, size=92):
    f = font(BLK, size); tw = int(f.getlength(text)); ph = size + 56; w = tw + 110
    im = Image.new("L", (w + 80, ph + 80), 0); ImageDraw.Draw(im).rounded_rectangle([40, 40, 40 + w, 40 + ph], ph // 2, fill=255)
    a = np.asarray(im, np.float32) / 255
    rgb = gold_fill(a)
    tm = np.zeros_like(a); m = mask_text(text, f, 2, pad=0)
    oy = (a.shape[0] - m.shape[0]) // 2 - 4; ox = (a.shape[1] - m.shape[1]) // 2
    tm[oy:oy + m.shape[0], ox:ox + m.shape[1]] = m
    rgb = rgb * (1 - tm[..., None]) + np.array([0.08, 0.04, 0.02], np.float32) * tm[..., None]
    return layer(a, rgb, shadow=0.6)

# ───────── ТЕКСТЫ ─────────
T_RIB = ribbon("O'ZBEKISTONDA XIZMAT KO'RSATGAN ARTIST")
T_OTA = gtext("Otabek", SCR, 190)
T_MUH = gtext("MUHAMMADZOHID", PF, 90, 1)
T_KON = gtext("KONSERT DASTURI", BLK, 46, 14, glow=None)
T_V1 = wtext("ISLOM KARIMOV NOMIDAGI", BLK, 38, 9)
T_V2 = gtext("FARG'ONA SAN'AT SAROYI", BLK, 70, 2)
T_INV1 = gtext("BARCHANGIZNI KONSERTDA", BLK, 66, 1)
T_INV2 = gtext("KUTIB QOLAMIZ!", BLK, 96, 2)
D_NUM = {d: gtext(d, BOD, 620) for d in ("19", "20")}
D_DEK = wtext("DEKABR", BLK, 150, 14)
D_PIL = {t: pill("SOAT " + t) for t in ("18:00", "14:00")}
CH1 = chip("19", "18:00"); CH2 = chip("20", "14:00")
P_MAIN = gtext("(94) 555-22-00", BLK, 92, 2)
P_SUB = wtext("(95) 555-22-00   ·   (73) 249-22-00", BLK, 40, 1)
P_LBL = wtext("MA'LUMOT UCHUN", BLK, 34, 10, col=(0.96, 0.80, 0.45))


def line_pair(fr, cy, half, alpha):
    if alpha <= 0.01: return
    for sx in (-1, 1):
        x0 = int(W / 2 + sx * half); x1 = int(x0 + sx * 110 * alpha)
        a, b = min(x0, x1), max(x0, x1)
        fr[cy - 2:cy + 2, a:b] = fr[cy - 2:cy + 2, a:b] * (1 - alpha) + GOLD * alpha


def frame(t):
    fr = BASE.copy()
    off = 150 * (1 - eio((t - (V + 13.2)) / 1.2))   # пока нет дат и телефонов — блок имени стоит ниже
    lights = eio(t / 1.6)                              # зал зажигается
    bt = ((t - PH) / BEAT) % 1.0; pulse = math.exp(-bt * 4.5)       # удар музыки
    push = 1.0 + 0.055 * eio(t / DUR)                  # медленный наезд
    # огни зала (параллакс, мерцание)
    for i, B in enumerate(BOK):
        dx = int(120 + (40 + 30 * i) * math.sin(t * 0.21 + i)); dy = int(120 + (12 + 14 * i) * (t / DUR * 2 - 1))
        fl = 0.80 + 0.14 * math.sin(t * (1.3 + i * 0.7) + i * 2) + 0.16 * pulse
        fr += B[dy:dy + H, dx:dx + W] * (lights * fl * 2.3)
    # лучи
    for i, Bm in enumerate(BEAMS):
        k = 0.36 + 0.16 * math.sin(t * (0.55 + 0.17 * i) + i * 1.9) + 0.07 * pulse
        fr += Bm * (lights * max(k, 0) * (0.9 if i < 2 else 0.6))
    # арка: растёт снизу вверх
    ar = eio((t - 1.0) / 1.6)
    if ar > 0:
        wy = np.clip((yy - (1500 - ar * 1350)) / 120, 0, 1) * np.clip((1210 + off - yy) / 160, 0, 1)
        fr += (ARCH_G * wy)[..., None] * GOLD * (0.42 + 0.14 * pulse)
        a = (ARCH * wy)[..., None]
        fr[:] = fr * (1 - a) + ARCH_COL * a
    # артист: выходит из света
    aa = eio((t - 0.7) / 1.5)
    if aa > 0:
        s = push * (1.06 - 0.06 * aa); sz = int(AW * s)
        A = cv2.resize(art, (sz, sz), interpolation=cv2.INTER_LINEAR); R = cv2.resize(ART_RIM, (sz, sz))
        x0 = ART_CX - sz // 2; y0 = int(ART_CY - sz / 2 + 14 * math.sin(t * 0.5) + off * 0.55)
        xa, xb = max(0, x0), min(W, x0 + sz); sl = (slice(0, sz), slice(xa - x0, xb - x0))
        fr[y0:y0 + sz, xa:xb] += R[sl][..., None] * GOLD * (0.38 + 0.12 * pulse) * aa
        al = A[sl][..., 3:4] * aa
        bloom = (1 - aa) * 0.4                          # в начале — светлее, «из света»
        fr[y0:y0 + sz, xa:xb] = fr[y0:y0 + sz, xa:xb] * (1 - al) + np.clip(A[sl][..., :3] + bloom, 0, 1.2) * al
    fr *= VIG
    fr = fr * (1 - (np.clip((yy - 960 - off) / 250, 0, 1) ** 1.2 * 0.93)[..., None] * eio((t - 1.6) / 1.2))

    # ── сцена «дата на весь экран» ──
    d1 = win(t, V + 10.05, V + 13.05, 0.35, 0.3); d2 = win(t, V + 13.1, V + 15.95, 0.35, 0.35)
    dd = max(d1, d2)
    post = fr                                           # сюда рисуем постерные тексты
    # ── постер: тексты ──
    inv = app(t, V + 21.3, 0.5)
    # площадка (сверху)
    va = app(t, V + 6.5, 0.6) * (1 - inv)
    blit(post, T_V1, W / 2, 128 - 20 * (1 - va), va)
    blit(post, T_V2, W / 2, 206 - 20 * (1 - va), app(t, V + 7.3, 0.6) * (1 - inv), shine=(t - (V + 7.6)) / 1.1)
    # приглашение (сверху, вместо площадки)
    blit(post, T_INV1, W / 2, 122, inv, scale=1.0)
    blit(post, T_INV2, W / 2, 222, app(t, V + 22.2, 0.45), scale=1.12 - 0.12 * app(t, V + 22.2, 0.45), shine=(t - (V + 22.5)) / 1.0)
    # лента
    ra = app(t, V + 0.0, 0.7)
    blit(post, T_RIB, W / 2, 1150 + off, ra, wipe=None if ra >= 1 else ra)
    # имя
    blit(post, T_OTA, W / 2 - 20, 1268 + off, 1.0 if t >= V + 2.6 else 0, wipe=(t - (V + 2.6)) / 0.95 if t < V + 3.7 else None, shine=(t - (V + 3.9)) / 1.2)
    ma = app(t, V + 3.25, 0.55)
    blit(post, T_MUH, W / 2, 1392 + off + 34 * (1 - ma), ma, shine=(t - (V + 4.0)) / 1.2)
    # повторный блик по имени в финале
    if t > V + 21.3:
        blit(post, T_MUH, W / 2, 1392, 0.0)
    ka = app(t, V + 4.7, 0.5)
    blit(post, T_KON, W / 2, 1474 + off, ka); line_pair(post, int(1474 + off), 350, ka)
    # даты-плашки
    c1 = app(t, V + 16.0, 0.5); c2 = app(t, V + 16.25, 0.5)
    blit(post, CH1, 278 - 60 * (1 - c1), 1572, c1); blit(post, CH2, 802 + 60 * (1 - c2), 1572, c2)
    # телефоны
    blit(post, P_LBL, W / 2, 1662, app(t, V + 16.05, 0.5))
    pa = app(t, V + 17.1, 0.5)
    blit(post, P_MAIN, W / 2, 1734, pa, scale=1.08 - 0.08 * pa, shine=(t - (V + 17.5)) / 1.2)
    blit(post, P_SUB, W / 2, 1812, app(t, V + 19.2, 0.6))

    if dd > 0:                                          # перевод фокуса на дату
        sm = cv2.resize(fr, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        sm = cv2.resize(cv2.GaussianBlur(sm, (0, 0), 5), (W, H), interpolation=cv2.INTER_LINEAR)
        fr = fr * (1 - dd) + sm * 0.42 * dd
        for da, num, tm, a0 in ((d1, "19", "18:00", V + 10.05), (d2, "20", "14:00", V + 13.1)):
            if da <= 0: continue
            pop = app(t, a0, 0.4); sc = 1.16 - 0.16 * pop
            blit(fr, D_NUM[num], W / 2, 700, da, scale=sc, shine=(t - a0 - 0.3) / 1.3)
            blit(fr, D_DEK, W / 2, 1120 + 30 * (1 - app(t, a0 + 0.35, 0.45)), da * app(t, a0 + 0.35, 0.45))
            blit(fr, D_PIL[tm], W / 2, 1330 + 30 * (1 - app(t, a0 + 1.25, 0.45)), da * app(t, a0 + 1.25, 0.45))

    # пыль (передний план)
    dl = np.zeros((H, W, 3), np.float32)
    for (x, y, sp, r, ph, br) in DUST:
        px = (x + 26 * math.sin(t * 0.6 + ph)) % W; py = (y - sp * t) % H
        b = br * (0.5 + 0.5 * math.sin(t * 2.1 + ph)) * lights * 0.8
        if b <= 0.02: continue
        cv2.circle(dl, (int(px), int(py)), int(r), (float(b), float(b * 0.8), float(b * 0.45)), -1, cv2.LINE_AA)
    fr += dl
    fr += cv2.resize(GRAIN[int(t * FPS) % 6], (W, H), interpolation=cv2.INTER_NEAREST).reshape(H, W, 1)
    # вход из чёрного и уход в чёрное (под концовку)
    k = min(eio(t / 0.6), eio((DUR - t) / 0.45))
    return (np.clip(fr * k, 0, 1) * 255).astype(np.uint8)


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "stills":
        ts = [float(x) for x in sys.argv[2:]] or [1.2, 2.6, 4.5, 6.9, 10.5, 13.6, 16.5, 21.5, 23.0, 26.0, 27.2]
        for t in ts:
            Image.fromarray(frame(t)).save(f"{WD}/st_{t:05.1f}.jpg", quality=90)
    else:
        tmp = WD + "/main.tmp.mp4"
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                              "-c:v", "libx264", "-preset", "slow", "-crf", "21", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
        n = int(DUR * FPS)
        for i in range(n):
            p.stdin.write(frame(i / FPS).tobytes())
            if i % 90 == 0: print(i, n, flush=True)
        p.stdin.close()
        if p.wait() == 0: os.replace(tmp, WD + "/main.mp4"); print("OK")
