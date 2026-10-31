"""Ролики офиса OZOD JAMOL из рендеров ofis_etapy.py (01.11.2026).
A — «Чертёж оживает»: коробка → «не так» → сканер превращает всё в чертёж → по чертежу собирается офис → вечер.
B — «Щелчок света»: коробка с лампочкой → темнота → светильники зажигаются по одному и открывают новый офис.
Титры — утверждённый стиль Б (внизу, Raleway ExtraBold с разрядкой). Своих звуков нет.
python3 ofis_rolik.py A|B RENDERS_DIR OUT_DIR"""
import sys, os, json, subprocess as sp
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

VAR, RD, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)
W, H, FPS = 1080, 1920, 30
F = '/home/claude/fonts/'
RED = (255, 16, 36); WHITE = (255, 255, 255)
KONC = '/home/claude/papa/docs/brand/ozod-jamol/koncovka/2s/OZOD_JAMOL_KONCOVKA_CHERNAYA.mp4'

def eo(x): x = min(1, max(0, x)); return 1 - (1 - x) ** 3
def eio(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
def cl(x): return min(1.0, max(0.0, x))

# ---------- кадры этапов (float32, 0..1), 1080×1920
def load(n):
    im = Image.open(f'{RD}/{n}.png').convert('RGB').resize((W, H), Image.LANCZOS)
    return np.asarray(im).astype(np.float32) / 255
ST = {n: load(n) for n in ('box', 'wrong', 'base', 'tv', 'sofa', 'full', 'night')}
ids = np.asarray(Image.open(f'{RD}/ids.png').convert('RGB').resize((W, H), Image.NEAREST)).astype(np.int16)
# линии чертежа: границы между предметами разных цветов
e = np.zeros((H, W), bool)
e[:, 1:] |= np.abs(ids[:, 1:] - ids[:, :-1]).sum(-1) > 30
e[1:, :] |= np.abs(ids[1:] - ids[:-1]).sum(-1) > 30
LINE = np.asarray(Image.fromarray((e * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.8))).astype(np.float32) / 255
GLOW = np.asarray(Image.fromarray((LINE * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6))).astype(np.float32) / 255
BP_BG = np.array([0.045, 0.05, 0.06], np.float32)
xx = np.arange(W)[None, :].astype(np.float32); yy = np.arange(H)[:, None].astype(np.float32)

def blueprint(draw=1.0):
    """тёмный лист + белые линии; draw — доля прорисовки (от центра наружу по кругу)"""
    r = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H * 0.45) / W) ** 2) / 1.05
    m = np.clip((draw * 1.15 - r) / 0.08, 0, 1)
    g = np.zeros((H, W, 3), np.float32) + BP_BG
    # мелкая сетка листа
    grid = ((np.mod(xx, 60) < 1.2) | (np.mod(yy, 60) < 1.2)).astype(np.float32) * 0.035
    g += grid[..., None]
    g = g * (1 - LINE[..., None] * m[..., None]) + np.array([0.93, 0.95, 1.0]) * (LINE * m)[..., None]
    g += np.array([0.35, 0.45, 0.6]) * (GLOW * m * 0.35)[..., None]
    return np.clip(g, 0, 1)

def wipe(a, b, p, glow=True):
    """сканер: вертикальная светящаяся линия идёт слева направо, за ней — кадр b"""
    if p <= 0: return a
    if p >= 1: return b
    x0 = -60 + p * (W + 120); m = np.clip((x0 - xx) / 50, 0, 1)[..., None] * np.ones((H, 1, 1), np.float32)
    o = a * (1 - m) + b * m
    if glow:
        g = np.exp(-((xx - x0) ** 2) / (2 * 7 ** 2)) * 0.9 + np.exp(-((xx - x0) ** 2) / (2 * 40 ** 2)) * 0.25
        o = o + g[..., None] * np.array([1.0, 0.97, 0.94], np.float32)
    return np.clip(o, 0, 1)

def mix(a, b, p): p = eio(p); return a * (1 - p) + b * p

def zoom(img, t, total):  # медленный общий наезд (одинаковый для всех слоёв)
    s = 1.0 + 0.05 * t / total
    if s <= 1.0005: return img
    im = Image.fromarray((img * 255).astype(np.uint8)); w2, h2 = int(W * s), int(H * s)
    im = im.resize((w2, h2), Image.BILINEAR); x, y = (w2 - W) // 2, (h2 - H) // 2
    return np.asarray(im.crop((x, y, x + W, y + H))).astype(np.float32) / 255

# ---------- титры (стиль Б)
def font(n, s, w):
    f = ImageFont.truetype(F + n, s); f.set_variation_by_axes([w]); return f
fMAIN, fSUB = font('Raleway.ttf', 64, 800), font('Montserrat.ttf', 27, 800)
FE = ['lnum', 'pnum']
def spaced(txt, f, fill, em):
    d = ImageDraw.Draw(Image.new('L', (1, 1))); adv = [d.textlength(c, font=f, features=FE) for c in txt]; g = f.size * em
    im = Image.new('RGBA', (int(sum(adv) + g * (len(txt) - 1)) + 4, int(f.size * 1.4)), (0, 0, 0, 0)); dd = ImageDraw.Draw(im); x = 0
    for c, a in zip(txt, adv): dd.text((x, 0), c, font=f, fill=fill + (255,), features=FE); x += a + g
    return im
def two(lines):
    ims = [spaced(l, fMAIN, WHITE, 0.14) for l in lines]
    if len(ims) == 1: return ims[0]
    gap = 12; w = max(i.width for i in ims); out = Image.new('RGBA', (w, sum(i.height for i in ims) + gap), (0, 0, 0, 0)); y = 0
    for i in ims: out.alpha_composite(i, ((w - i.width) // 2, y)); y += i.height + gap
    return out
def shadow(im, r=9, a=170):
    p = r * 3; s = Image.new('RGBA', (im.width + 2 * p, im.height + 2 * p), (0, 0, 0, 0)); al = Image.new('L', s.size, 0)
    al.paste(im.getchannel('A'), (p, p)); s.putalpha(al.filter(ImageFilter.GaussianBlur(r)).point(lambda v: int(v * a / 255)))
    s.alpha_composite(im, (p, p)); return s, p
def alpha(im, a):
    if a >= 0.999: return im
    im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v: int(v * a))); return im
def mark(kind, d=50):
    s = 4; D = d * s; im = Image.new('RGBA', (D, D), (0, 0, 0, 0)); dd = ImageDraw.Draw(im); w = int(D * 0.12)
    if kind == 'x':
        dd.ellipse((0, 0, D - 1, D - 1), fill=RED + (255,)); m = D * 0.32
        dd.line((m, m, D - m, D - m), fill=WHITE + (255,), width=w); dd.line((m, D - m, D - m, m), fill=WHITE + (255,), width=w)
    else:
        dd.ellipse((0, 0, D - 1, D - 1), fill=WHITE + (255,))
        dd.line([(D * .27, D * .52), (D * .44, D * .68), (D * .74, D * .34)], fill=(12, 12, 14, 255), width=w, joint='curve')
    return im.resize((d, d), Image.LANCZOS)

Y_BAR, Y_MAIN = 1302, 1330
grad = np.zeros((H, W, 4), np.uint8); grad[..., 3] = (np.clip((yy - 1050) / 870, 0, 1) ** 1.4 * 185).astype(np.uint8).repeat(W, 1)
GRAD = Image.fromarray(grad)

def make_titles(spec):
    pre = []
    for (t0, t1, main, sub, mk) in spec:
        pre.append((t0, t1, shadow(two(main.split('|'))), shadow(spaced(sub, fSUB, (232, 232, 232), 0.4), 7, 180), mark(mk) if mk else None))
    return pre

def titles(c, t, pre):
    c.alpha_composite(GRAD)
    for (t0, t1, (mi, mp), (si, spd), mk) in pre:
        if not (t0 <= t <= t1): continue
        k = t - t0; out = 1 - eio((t - (t1 - 0.35)) / 0.35)
        bw = int(44 * eo(k / 0.4))
        if bw > 0: ImageDraw.Draw(c).rectangle((W // 2 - bw // 2, Y_BAR, W // 2 + bw // 2, Y_BAR + 4), fill=RED + (int(255 * out),))
        p = eo((k - 0.08) / 0.6)
        if p > 0:
            sc = 1.035 - 0.035 * p; im = mi.resize((int(mi.width * sc), mi.height), Image.LANCZOS)
            off = int((1 - p) * 26); x = (W - im.width) // 2
            if mk is not None: x -= (mk.width + 34) // 2
            c.alpha_composite(alpha(im, p * out), (x, Y_MAIN - mp + off))
            if mk is not None:
                q = eo((k - 0.4) / 0.35)
                if q > 0: c.alpha_composite(alpha(mk, q * out), (x + im.width - mp + 34, Y_MAIN + 12 + off))
        q = eo((k - 0.28) / 0.55)
        ys = Y_MAIN + (mi.height - 2 * mp) + 8
        if q > 0: c.alpha_composite(alpha(si, q * out), ((W - si.width) // 2, ys - spd + int((1 - q) * 14)))

# ---------- сценарии
if VAR == 'A':
    TOTAL = 15.5
    TT = make_titles([
        (0.3, 2.3, 'КОРОБКА', '01 · БОШЛАНИШИ', None),
        (2.9, 4.8, 'БУНДАЙ ЭМАС', '02 · ХАТО', 'x'),
        (5.2, 7.6, 'АВВАЛ — ЛОЙИҲА', '03 · 3D ЧИЗМА', None),
        (8.0, 11.0, 'МАНА БУНДАЙ', '04 · ТЎҒРИСИ', 'v'),
        (11.6, TOTAL, 'ИЛИҚ|МИНИМАЛИЗМ', 'OZOD JAMOL ОФИС', None)])
    def scene(t):
        if t < 2.4: return ST['box']
        if t < 3.2: return wipe(ST['box'], ST['wrong'], (t - 2.4) / 0.8)
        if t < 4.9: return ST['wrong']
        if t < 5.7: return wipe(ST['wrong'], blueprint(eo((t - 4.9) / 1.6)), (t - 4.9) / 0.8)
        if t < 7.4: return blueprint(eo((t - 4.9) / 1.6))
        # по чертежу: сканер проявляет отделку, линии гаснут медленно
        if t < 8.2:
            o = wipe(blueprint(), ST['base'], (t - 7.4) / 0.8, glow=True); return o
        seq = [('base', 8.2), ('tv', 8.9), ('sofa', 9.6), ('full', 10.3)]
        if t < 11.2:
            cur = ST['base']
            for (a, ta), (b, tb) in zip(seq, seq[1:]):
                if t >= tb - 0.35: cur = ST[b]
                elif t >= ta: cur = mix(ST[a], ST[b], (t - (tb - 0.7)) / 0.35) if t > tb - 0.7 else ST[a]
            lf = cl(1 - (t - 7.6) / 1.6) * 0.55  # линии чертежа ещё видны поверх, потом тают
            if lf > 0: cur = np.clip(cur + LINE[..., None] * lf * np.array([0.95, 0.97, 1.0]), 0, 1)
            return cur
        if t < 12.6: return mix(ST['full'], ST['night'], (t - 11.2) / 1.4)
        return ST['night']
else:
    TOTAL = 13.5
    # координаты светильников на кадре (найдены по яркости на night.png)
    SP = [(0.54, 0.19), (0.445, 0.34), (0.69, 0.36), (0.06, 0.31), (0.89, 0.31)]
    TT = make_titles([
        (0.3, 2.2, 'КОРОБКА', '01 · БОШЛАНИШИ', None),
        (4.0, 7.6, 'ҲАР БИР ЧИРОҚ —|ЎЗ ЖОЙИДА', '02 · ЁРИТИШ ЛОЙИҲАСИ', None),
        (8.6, TOTAL, 'ИЛИҚ|МИНИМАЛИЗМ', 'OZOD JAMOL ОФИС', None)])
    DARK = ST['night'] * 0.035
    def pool(i, t):
        t0 = 3.1 + i * 0.55
        if t < t0: return np.zeros((H, W), np.float32)
        p = eo((t - t0) / 0.9); cx, cy = SP[i][0] * W, SP[i][1] * H
        # конус света вниз от светильника: эллипс шире книзу
        dx = (xx - cx) / (W * (0.25 + 0.30 * p)); dy = (yy - (cy + H * 0.28)) / (H * (0.22 + 0.32 * p))
        m = np.clip(1.25 - np.sqrt(dx ** 2 + dy ** 2), 0, 1) * p
        flick = 1.0 if t - t0 > 0.12 else 0.55  # короткий «зажёгся»
        return m * flick
    def scene(t):
        if t < 2.35: return ST['box']
        if t < 2.6: return mix(ST['box'], np.zeros_like(DARK), (t - 2.35) / 0.25)
        if t < 3.1: return mix(np.zeros_like(DARK), DARK, (t - 2.6) / 0.5)
        m = np.zeros((H, W), np.float32)
        for i in range(5): m = np.maximum(m, pool(i, t))
        # подсветка потолка — последней, открывает всё
        c = eio((t - 6.2) / 1.6); m = np.maximum(m, c)
        return DARK * (1 - m[..., None]) + ST['night'] * m[..., None]

# ---------- рендер
def run(c): sp.run(c, check=True)
fd = f'{OUT}/fr'; os.makedirs(fd, exist_ok=True)
N = int(TOTAL * FPS)
for i in range(N):
    t = i / FPS
    img = zoom(scene(t), t, TOTAL)
    c = Image.fromarray((img * 255).astype(np.uint8)).convert('RGBA'); titles(c, t, TT)
    c.convert('RGB').save(f'{fd}/f{i:04d}.png', compress_level=1)
run(['ffmpeg', '-v', 'error', '-y', '-framerate', str(FPS), '-i', f'{fd}/f%04d.png', '-f', 'lavfi', '-t', str(TOTAL), '-i',
     'anullsrc=r=48000:cl=stereo', '-i', KONC, '-filter_complex',
     f'[0:v]format=yuv420p,setsar=1[v0];[2:v]scale={W}:{H},fps={FPS},format=yuv420p,setsar=1[v1];'
     f'[2:a]aresample=48000,aformat=channel_layouts=stereo[a1];[v0][1:a][v1][a1]concat=n=2:v=1:a=1[v][a]',
     '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '16', '-c:a', 'aac', '-b:a', '192k',
     '-movflags', '+faststart', f'{OUT}/final.mp4'])
print('OK', f'{OUT}/final.mp4')
