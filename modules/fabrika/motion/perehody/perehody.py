"""PAPA · библиотека переходов и эффектов (по рефам PUMA / Starbucks / Amazon / TEN x YOU, 09.11.2026).
Все функции работают с кадрами float32 RGB 0..1, 1080x1920. Время — секунды.
"""
import math, random
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def eout(p): p = clamp(p); return 1 - (1 - p) ** 3
def einout(p): p = clamp(p); return 3 * p * p - 2 * p * p * p

# 1. ВСПЫШКА (белая/цветная) — на смене блоков
def flash(C, a, col=(1, 1, 1)):
    if a > 0: C *= (1 - a); C += np.array(col, np.float32) * a
    return C

# 2. ЗУМ-БЛЮР (радиальное размытие + наезд) — «влететь в кадр/в объектив» (Amazon, TEN x YOU)
def zoom_blur(C, strength, cx=0.5, cy=0.5, steps=10):
    """strength 0..1: сила наезда-размытия."""
    if strength <= 0.01: return C
    acc = np.zeros_like(C)
    for i in range(steps):
        s = 1 + strength * 0.6 * i / (steps - 1)
        M = np.float32([[s, 0, W * cx * (1 - s)], [0, s, H * cy * (1 - s)]])
        acc += cv2.warpAffine(C, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    return acc / steps

def zoom_through(A, B, p, cx=0.5, cy=0.5):
    """Переход A→B: A влетает в центр (зум-блюр нарастает), вспышка, B выходит из зум-блюра."""
    if p < 0.5:
        q = p / 0.5
        s = 1 + 1.5 * q * q
        M = np.float32([[s, 0, W * cx * (1 - s)], [0, s, H * cy * (1 - s)]])
        X = cv2.warpAffine(A, M, (W, H), borderMode=cv2.BORDER_REFLECT)
        return flash(zoom_blur(X, q, cx, cy), 0.5 * q * q)
    q = (1 - p) / 0.5
    X = zoom_blur(B.copy(), q, cx, cy)
    return flash(X, 0.5 * q * q)

# 3. СТРОБ-ОЧЕРЕДЬ (PUMA): N склеек по 2 кадра подряд
def strobe_pick(frames_list, t, t0, frame_len=2 / 30):
    """frames_list: список функций f(t)->кадр. Возвращает кадр строб-очереди."""
    k = int((t - t0) / frame_len) % len(frames_list)
    return frames_list[k](t)

# 4. Ч/Б УДАР (PUMA): кадр в ч/б + контраст
def bw_hit(C, contrast=1.25):
    g = (C[..., 0] * 0.3 + C[..., 1] * 0.59 + C[..., 2] * 0.11)
    g = np.clip((g - 0.5) * contrast + 0.5, 0, 1)
    return np.repeat(g[..., None], 3, 2).astype(np.float32)

# 5. БЕЛЫЙ СИЛУЭТ (PUMA): человек залит белым поверх ч/б кадра
_rembg = None
def person_mask(C):
    """Маска человека (0..1) через rembg. Медленно — считать 1 раз на кадр-заморозку."""
    global _rembg
    from rembg import remove, new_session
    if _rembg is None: _rembg = new_session('u2net_human_seg')
    im = Image.fromarray((np.clip(C, 0, 1) * 255).astype(np.uint8))
    a = np.array(remove(im, session=_rembg, only_mask=True)).astype(np.float32) / 255
    return cv2.GaussianBlur(a, (0, 0), 1.2)

def white_silhouette(C, mask, amount=1.0, glow=True):
    X = bw_hit(C) * 0.75
    m = mask[..., None] * amount
    if glow:
        g = cv2.GaussianBlur(mask, (0, 0), 18)[..., None] * 0.6 * amount
        X = X * (1 - g) + g
    return X * (1 - m) + m

# 6. СВЕТЯЩИЙСЯ ТИТР над предметом (Starbucks): загорается, держится, гаснет вспышкой
def glow_title(C, text, font_path, cx, cy, t, t0, dur=1.6, size=90, col=(255, 200, 90)):
    lt = t - t0
    if lt < 0 or lt > dur: return C
    f = ImageFont.truetype(font_path, size)
    l, tp, r, b = f.getbbox(text); w, h = r - l + 80, b - tp + 80
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).text((40 - l, 40 - tp), text, font=f, fill=255)
    m = np.array(m).astype(np.float32) / 255
    glow = cv2.GaussianBlur(m, (0, 0), 14) * 1.6 + cv2.GaussianBlur(m, (0, 0), 4) * 0.8
    a_in = eout(lt / 0.25); a_out = 1 - clamp((lt - (dur - 0.25)) / 0.25)
    flick = 1.0 if lt > 0.25 else (0.3 + 0.7 * (int(lt * 40) % 2))
    a = a_in * a_out * flick
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    x1, y1 = max(0, x0), max(0, y0); x2, y2 = min(W, x0 + w), min(H, y0 + h)
    if x2 <= x1 or y2 <= y1: return C
    sub = (slice(y1 - y0, y2 - y0), slice(x1 - x0, x2 - x0))
    c = np.array(col, np.float32) / 255
    roi = C[y1:y2, x1:x2]
    dark = np.clip(cv2.GaussianBlur(m, (0, 0), 22) * 2.2, 0, 1)
    roi *= (1 - dark[sub][..., None] * 0.6 * a)
    roi += (glow[sub][..., None] * c * 0.7) * a
    roi[:] = roi * (1 - m[sub][..., None] * a) + m[sub][..., None] * a
    np.clip(C, 0, 1, out=C)
    if lt > dur - 0.12: flash(C, 0.6 * (1 - (dur - lt) / 0.12))
    return C

# 7. РВАНАЯ БУМАГА (Starbucks): полоса фото с рваными краями + цветной вырезанный человек
def torn_mask(h, w, top, bot, seed=1, rough=18):
    r = random.Random(seed)
    m = np.zeros((h, w), np.float32)
    xs = np.arange(0, w + 20, 20)
    def edge(y0):
        pts = [(x, y0 + r.uniform(-rough, rough)) for x in xs]
        return pts
    poly = edge(top) + list(reversed(edge(bot)))
    cv2.fillPoly(m, [np.array(poly, np.int32)], 1.0, cv2.LINE_AA)
    return m

def paper_strip(C, photo, top, bot, p, seed=1, from_left=True, bw=True):
    """Полоса photo (кадр W×H) рвётся на экран между top..bot, белая бумажная кромка. p 0..1 — выезд."""
    m = torn_mask(H, W, top, bot, seed)
    edge = cv2.dilate(m, np.ones((15, 15), np.uint8)) - m
    off = int((1 - eout(p)) * W * (1 if from_left else -1)) * (-1)
    M = np.float32([[1, 0, off], [0, 1, 0]])
    m = cv2.warpAffine(m, M, (W, H)); edge = cv2.warpAffine(edge, M, (W, H))
    ph = cv2.warpAffine(bw_hit(photo, 1.1) * 0.95 + 0.04 if bw else photo, M, (W, H))
    sh = cv2.GaussianBlur(np.clip(m + edge, 0, 1), (0, 0), 10)
    sh = np.roll(sh, 10, 0)[..., None] * 0.35
    C = C * (1 - sh)
    C = C * (1 - edge[..., None]) + edge[..., None] * np.array([0.97, 0.95, 0.9], np.float32)
    C = C * (1 - m[..., None]) + ph * m[..., None]
    return C

# 8. СЛОВА ПО ОДНОМУ (TEN x YOU): крупное слово по центру, сменяется в такт речи
def word_card(C, word, font_path, size=150, y=None, a=1.0, scale=1.0):
    sz = int(size * scale)
    while ImageFont.truetype(font_path, sz).getlength(word) > 960 and sz > 30: sz -= 4
    f = ImageFont.truetype(font_path, sz)
    l, tp, r, b = f.getbbox(word); w, h = r - l + 40, b - tp + 40
    im = Image.new('L', (w, h), 0); ImageDraw.Draw(im).text((20 - l, 20 - tp), word, font=f, fill=255)
    m = np.array(im).astype(np.float32) / 255
    sh = cv2.GaussianBlur(m, (0, 0), 6) * 0.6
    x0 = int(W / 2 - w / 2); y0 = int((y or H * 0.62) - h / 2)
    roi = C[y0:y0 + h, x0:x0 + w]
    roi *= (1 - sh[..., None] * a)
    roi[:] = roi * (1 - m[..., None] * a) + m[..., None] * a
    return C

# 9. WHIP-БРОСОК и 10. SPEED-RAMP — см. eng.whip / lv2.src
