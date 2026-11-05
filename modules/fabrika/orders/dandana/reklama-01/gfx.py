"""Dandana — графика: золото, тексты, бейдж-логотип (слои RGBA numpy)."""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FNT = "/home/claude/fnt"
OSW = f"{FNT}/oswald-700.ttf"
M9 = f"{FNT}/montserrat-900.ttf"
M8 = f"{FNT}/montserrat-800.ttf"
W, H = 1080, 1920

GOLD_TOP = np.array([250, 230, 170], np.float32)
GOLD_MID = np.array([228, 190, 110], np.float32)
GOLD_BOT = np.array([178, 128, 52], np.float32)


def gold_fill(h, w):
    y = np.linspace(0, 1, h)[:, None, None]
    a = np.clip(y * 2, 0, 1); b = np.clip(y * 2 - 1, 0, 1)
    c = GOLD_TOP * (1 - a) + GOLD_MID * a
    c = c * (1 - b) + GOLD_BOT * b
    return np.broadcast_to(c, (h, w, 3)).copy()


def colorize(mask, color):
    """mask L(0..255) -> RGBA float32 0..1. color: 'gold' | (r,g,b)."""
    m = np.asarray(mask, np.float32) / 255.0
    h, w = m.shape
    rgb = gold_fill(h, w) / 255.0 if color == "gold" else np.broadcast_to(np.array(color, np.float32) / 255.0, (h, w, 3)).copy()
    return np.dstack([rgb, m])


def text_mask(txt, font, size, track=0):
    f = ImageFont.truetype(font, size)
    asc, desc = f.getmetrics()
    widths = [f.getlength(ch) for ch in txt]
    tw = int(sum(widths) + track * max(len(txt) - 1, 0)) + 8
    im = Image.new("L", (tw, asc + desc + 8), 0)
    d = ImageDraw.Draw(im); x = 4
    for ch, cw in zip(txt, widths):
        d.text((x, 4), ch, font=f, fill=255); x += cw + track
    bb = im.getbbox()
    return im.crop((max(bb[0] - 2, 0), 0, bb[2] + 2, im.height))


def text_layer(txt, font, size, color="gold", track=0, shadow=True):
    m = text_mask(txt, font, size, track)
    lay = colorize(m, color)
    if not shadow:
        return lay
    pad = 30
    big = np.zeros((lay.shape[0] + 2 * pad, lay.shape[1] + 2 * pad, 4), np.float32)
    sm = Image.new("L", (big.shape[1], big.shape[0]), 0); sm.paste(m, (pad, pad + 4))
    sm = np.asarray(sm.filter(ImageFilter.GaussianBlur(10)), np.float32) / 255.0 * 0.75
    big[..., 3] = sm
    over(big, lay, pad, pad)
    return big


def over(dst, src, x, y, alpha=1.0):
    """Наложить RGBA src (float 0..1) на dst (RGB или RGBA float) в точке x,y (обрезка по краям)."""
    if alpha <= 0:
        return dst
    H_, W_ = dst.shape[:2]; h, w = src.shape[:2]
    x0, y0 = max(int(x), 0), max(int(y), 0); x1, y1 = min(int(x) + w, W_), min(int(y) + h, H_)
    if x1 <= x0 or y1 <= y0:
        return dst
    s = src[y0 - int(y):y1 - int(y), x0 - int(x):x1 - int(x)]
    a = s[..., 3:4] * alpha
    d = dst[y0:y1, x0:x1]
    if dst.shape[2] == 4:
        da = d[..., 3:4]
        oa = a + da * (1 - a)
        rgb = (s[..., :3] * a + d[..., :3] * da * (1 - a)) / np.maximum(oa, 1e-6)
        dst[y0:y1, x0:x1] = np.concatenate([rgb, oa], 2)
    else:
        dst[y0:y1, x0:x1] = s[..., :3] * a + d * (1 - a)
    return dst


def ease_out(t):
    t = min(max(t, 0.0), 1.0); return 1 - (1 - t) ** 3


def ease_io(t):
    t = min(max(t, 0.0), 1.0); return t * t * (3 - 2 * t)


def back_out(t, s=1.7):
    t = min(max(t, 0.0), 1.0); t -= 1; return t * t * ((s + 1) * t + s) + 1


# ---------- бейдж DANDANA (по вывеске) ----------
SS = 2  # суперсэмплинг


def _burger_mask(D):
    """Иконка бургера, D — диаметр бейджа (px, уже *SS). Возвращает L-маску размера D×D."""
    im = Image.new("L", (D, D), 0); d = ImageDraw.Draw(im)
    cx, w = D / 2, D * 0.40
    top = D * 0.155; bun_b = D * 0.335
    d.pieslice([cx - w / 2, top, cx + w / 2, top + (bun_b - top) * 2], 180, 360, fill=255)
    d.rectangle([cx - w / 2, bun_b - D * 0.004, cx + w / 2, bun_b], fill=255)
    # блик на булке (тёмная дуга)
    d.arc([cx - w * 0.36, top + D * 0.03, cx + w * 0.36, top + D * 0.21], 205, 250, fill=0, width=int(D * 0.010))
    # салат — зигзаг
    y0 = bun_b + D * 0.016; amp = D * 0.016; n = 9
    pts = [(cx - w * 0.53, y0 + amp)]
    for i in range(n + 1):
        x = cx - w * 0.53 + i * (w * 1.06 / n); pts.append((x, y0 + (0 if i % 2 else amp * 1.6)))
    pts += [(cx + w * 0.53, y0 + amp * 2.4), (cx - w * 0.53, y0 + amp * 2.4)]
    d.polygon(pts, fill=255)
    # котлета + сыр-треугольник
    py = y0 + amp * 2.4 + D * 0.012
    d.rounded_rectangle([cx - w * 0.5, py, cx + w * 0.5, py + D * 0.05], radius=int(D * 0.02), fill=255)
    d.polygon([(cx - w * 0.16, py - D * 0.004), (cx + w * 0.16, py - D * 0.004), (cx, py + D * 0.05)], fill=0)
    d.polygon([(cx - w * 0.11, py + D * 0.004), (cx + w * 0.11, py + D * 0.004), (cx, py + D * 0.038)], fill=255)
    # нижняя булка
    by = py + D * 0.064
    d.rounded_rectangle([cx - w * 0.47, by, cx + w * 0.47, by + D * 0.055], radius=int(D * 0.026), fill=255)
    return im


def _star(d, cx, cy, r):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5; rr = r if i % 2 == 0 else r * 0.42
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=255)


def badge_parts(Dout=760):
    """Части бейджа (каждая — RGBA float Dout×Dout): ring, burger, word, sub, stars[3], disk."""
    D = Dout * SS
    def fin(im, color="gold"):
        im = im.resize((Dout, Dout), Image.LANCZOS)
        return colorize(im, color)
    disk = Image.new("L", (D, D), 0); ImageDraw.Draw(disk).ellipse([0, 0, D - 1, D - 1], fill=255)
    ring = Image.new("L", (D, D), 0); ImageDraw.Draw(ring).ellipse([D * 0.035, D * 0.035, D * 0.965, D * 0.965], outline=255, width=int(D * 0.022))
    burger = _burger_mask(D)
    word = Image.new("L", (D, D), 0)
    wm = text_mask("DANDANA", OSW, int(D * 0.175), track=int(D * 0.006))
    word.paste(wm, (int((D - wm.width) / 2), int(D * 0.455)))
    sub = Image.new("L", (D, D), 0)
    sm = text_mask("PIZZA & BURGER", OSW, int(D * 0.066), track=int(D * 0.006))
    sy = int(D * 0.675)
    sub.paste(sm, (int((D - sm.width) / 2), sy))
    sd = ImageDraw.Draw(sub); ly = sy + sm.height * 0.58; gap = D * 0.022; lw = D * 0.045; th = int(D * 0.007)
    x0 = (D - sm.width) / 2
    sd.rectangle([x0 - gap - lw, ly - th / 2, x0 - gap, ly + th / 2], fill=255)
    sd.rectangle([x0 + sm.width + gap, ly - th / 2, x0 + sm.width + gap + lw, ly + th / 2], fill=255)
    stars = []
    for i in (-1, 0, 1):
        s = Image.new("L", (D, D), 0); _star(ImageDraw.Draw(s), D / 2 + i * D * 0.105, D * 0.83, D * 0.032); stars.append(fin(s))
    return dict(disk=fin(disk, (14, 12, 10)), ring=fin(ring), burger=fin(burger), word=fin(word), sub=fin(sub), stars=stars,
                ring_mask=np.asarray(ring.resize((Dout, Dout), Image.LANCZOS), np.float32) / 255.0)


def arc_reveal(D, frac):
    """Маска раскрытия по углу (от верха по часовой), frac 0..1."""
    yy, xx = np.mgrid[0:D, 0:D]
    ang = (np.degrees(np.arctan2(xx - D / 2, -(yy - D / 2))) + 360) % 360
    return (ang <= frac * 360).astype(np.float32)
