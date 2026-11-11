import cv2, numpy as np, subprocess, math, random, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
DUR = 35.5
V = 16.5  # старт диктора
BLK = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
XB = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
RED = (255, 16, 36)

src = cv2.imread("/home/claude/vs/fr12.png")[:, :, ::-1].astype(np.float32) / 255
photo = src[165:880, 45:678]  # 633x715
# карточка
CW, CH = 880, 1000
CX, CY = (W - CW) // 2, 250


def cover(img, w, h, s=1.0, cx=0.5, cy=0.5):
    ih, iw = img.shape[:2]
    k = max(w / iw, h / ih) * s
    r = cv2.resize(img, (int(iw * k) + 2, int(ih * k) + 2), interpolation=cv2.INTER_CUBIC)
    rh, rw = r.shape[:2]
    x = int(np.clip(cx * rw - w / 2, 0, rw - w)); y = int(np.clip(cy * rh - h / 2, 0, rh - h))
    return r[y:y + h, x:x + w]


# фон: размытое фото + фиолетовый тон + виньетка
bg_big = cover(photo, int(W * 1.15), int(H * 1.15), 1.0, 0.5, 0.35)
bg_big = cv2.GaussianBlur(bg_big, (0, 0), 38)
tint = np.array([0.32, 0.05, 0.25], np.float32)
bg_big = bg_big * 0.42 + tint * 0.22
yy, xx = np.mgrid[0:bg_big.shape[0], 0:bg_big.shape[1]].astype(np.float32)
vig = 1 - 0.65 * (((xx / bg_big.shape[1] - .5) ** 2 + (yy / bg_big.shape[0] - .5) ** 2) / .5)
bg_big = np.clip(bg_big * vig[..., None], 0, 1)

# фото высокого качества для карточки (апскейл + лёгкая резкость)
ph_up = cv2.resize(photo, (int(633 * 1.75), int(715 * 1.75)), interpolation=cv2.INTER_LANCZOS4)
bl = cv2.GaussianBlur(ph_up, (0, 0), 1.6)
ph_up = np.clip(ph_up * 1.35 - bl * 0.35, 0, 1)

# маска скруглённой карточки
def rmask(w, h, r):
    m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=255)
    return np.asarray(m, np.float32) / 255
CMASK = rmask(CW, CH, 54)
bord = Image.new("L", (CW, CH), 0); ImageDraw.Draw(bord).rounded_rectangle([1, 1, CW - 2, CH - 2], 54, outline=255, width=3)
CBORD = np.asarray(bord, np.float32) / 255 * 0.45
# нижний градиент в карточке
gy = np.linspace(0, 1, CH, dtype=np.float32)
CGRAD = np.clip((gy - 0.55) / 0.45, 0, 1) ** 1.3 * 0.88
# тень
sh = Image.new("L", (CW + 200, CH + 200), 0); ImageDraw.Draw(sh).rounded_rectangle([100, 120, CW + 100, CH + 120], 54, fill=200)
SHADOW = np.asarray(sh.filter(ImageFilter.GaussianBlur(40)), np.float32) / 255


def text_layer(lines, glow=True):
    """lines: [(text, font, size, color, tracking, dy)] → RGBA float, центр по X."""
    pad = 60
    imgs = []
    total_h = 0
    for t, f, s, col, tr, gap in lines:
        fnt = ImageFont.truetype(f, s)
        widths = [fnt.getlength(c) for c in t]
        tw = int(sum(widths) + tr * (len(t) - 1))
        asc, desc = fnt.getmetrics()
        im = Image.new("RGBA", (tw + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
        d = ImageDraw.Draw(im); x = pad
        for c, w in zip(t, widths):
            d.text((x, pad), c, font=fnt, fill=col + (255,)); x += w + tr
        imgs.append((im, gap)); total_h += im.height - 2 * pad + gap
    mw = max(i.width for i, _ in imgs)
    out = Image.new("RGBA", (mw, total_h + 2 * pad), (0, 0, 0, 0))
    y = 0
    for im, gap in imgs:
        out.alpha_composite(im, ((mw - im.width) // 2, y)); y += im.height - 2 * pad + gap
    a = np.asarray(out, np.float32) / 255
    if glow:
        g = cv2.GaussianBlur(a[..., 3], (0, 0), 14) * 0.55
        sh = cv2.GaussianBlur(a[..., 3], (0, 0), 6) * 0.7
        base_a = np.maximum(a[..., 3], sh)
        rgb = a[..., :3] * a[..., 3:4] / np.maximum(base_a, 1e-4)[..., None]
        a = np.dstack([rgb, base_a])
    return a


def pill(text, size=34, fill=(255, 255, 255), fg=(30, 8, 30), icon=True):
    fnt = ImageFont.truetype(XB, size)
    tw = int(fnt.getlength(text)); ph = size + 34; iw = (ph - 12) if icon else 0
    w = tw + 56 + iw + (14 if icon else 0)
    im = Image.new("RGBA", (w + 40, ph + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([20, 20, 20 + w, 20 + ph], ph // 2, fill=fill + (235,))
    x = 20 + 28
    if icon:  # иконка Telegram: круг + «самолётик»
        cx, cy, r = x + iw // 2 - 6, 20 + ph // 2, iw // 2 - 4
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(42, 171, 238, 255))
        d.polygon([(cx - r * .55, cy - r * .02), (cx + r * .5, cy - r * .45), (cx + r * .22, cy + r * .5), (cx - r * .05, cy + r * .12)], fill=(255, 255, 255, 255))
        x += iw + 8
    d.text((x, 20 + (ph - size) // 2 - size * 0.12), text, font=fnt, fill=fg + (255,))
    return np.asarray(im, np.float32) / 255


def over(fr, layer, cx, cy, alpha=1.0, scale=1.0):
    if alpha <= 0.003: return
    L = layer
    if abs(scale - 1) > 1e-3:
        L = cv2.resize(L, (max(1, int(L.shape[1] * scale)), max(1, int(L.shape[0] * scale))), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
    h, w = L.shape[:2]; x0 = int(cx - w / 2); y0 = int(cy - h / 2)
    xa, ya = max(0, x0), max(0, y0); xb, yb = min(W, x0 + w), min(H, y0 + h)
    if xa >= xb or ya >= yb: return
    l = L[ya - y0:yb - y0, xa - x0:xb - x0]
    a = l[..., 3:4] * alpha
    fr[ya:yb, xa:xb] = fr[ya:yb, xa:xb] * (1 - a) + l[..., :3] * a


def ease(x): x = min(max(x, 0), 1); return 1 - (1 - x) ** 3
def win(t, a, b, fi=0.45, fo=0.35):
    if t < a or t > b: return 0.0
    return min(ease((t - a) / fi), 1.0 if fo <= 0 else min(1, (b - t) / fo))
def rise(t, a, d=0.5, px=40): return (1 - ease((t - a) / d)) * px

# слои текста
L_PREM_BIG = text_layer([("ПРЕМЬЕРА", BLK, 128, (255, 255, 255), 6, 0)])
L_PREM_TOP = text_layer([("ПРЕМЬЕРА", BLK, 42, (255, 255, 255), 16, 0)])
L_DATE = text_layer([("12-НОЯБРЬ", BLK, 76, (255, 255, 255), 2, 0)])
L_TIME = text_layer([("СОАТ 18:00", XB, 44, (255, 225, 240), 3, 0)])
L_NAME = text_layer([("ДИЛНОЗА АКБАРОВА", BLK, 60, (255, 255, 255), 1, 0)])
L_SONG = text_layer([("«РАШК»", XB, 46, (255, 200, 225), 4, 0)])
P_TG = pill("КАТТА ДАВРА · @kattadavrauz", 34)
C_DATE = text_layer([("12-НОЯБРЬ", BLK, 150, (255, 255, 255), 2, 0)])
C_TIME = text_layer([("СОАТ 18:00", BLK, 96, (255, 255, 255), 4, 0)])
C_N1 = text_layer([("ДИЛНОЗА", BLK, 140, (255, 255, 255), 2, 0)])
C_N2 = text_layer([("АКБАРОВА", BLK, 140, (255, 255, 255), 2, 0)])
C_SONG = pill("«РАШК»", 84, fill=RED, fg=(255, 255, 255), icon=False)
C_PREMSI = text_layer([("ҚЎШИҒИНИНГ ПРЕМЬЕРАСИ", XB, 46, (255, 225, 240), 6, 0)])
D_W = [text_layer([(w, BLK, 74, (255, 255, 255), 3, 0)]) for w in ("СЕВГИ", "РИТМ", "ҚАЛБ")]
D_NEW = text_layer([("ЯНГИ ҚЎШИҚ", BLK, 92, (255, 255, 255), 4, 0)])
E_1 = text_layer([("ПРЕМЬЕРАНИ", XB, 52, (255, 225, 240), 10, 0)])
E_2 = text_layer([("КАТТА ДАВРА", BLK, 116, (255, 255, 255), 2, 0)])
E_3 = text_layer([("КАНАЛИДА КУТИНГ!", BLK, 64, (255, 255, 255), 3, 0)])
E_4 = text_layer([("12-НОЯБРЬ · 18:00", XB, 50, (255, 210, 230), 4, 0)])
P_TG_BIG = pill("@kattadavrauz", 46)

# пыль
random.seed(7)
DUST = [(random.random() * W, random.random() * H, random.uniform(1, 3.2), random.uniform(-14, 14), random.uniform(-40, -10), random.uniform(0.25, 0.9), random.random() * 6) for _ in range(140)]


def dust(fr, t):
    for x, y, r, vx, vy, a, ph in DUST:
        px = (x + vx * t) % W; py = (y + vy * t) % H
        al = a * (0.6 + 0.4 * math.sin(t * 2 + ph))
        cv2.circle(fr, (int(px), int(py)), int(r), (1, 1, 1), -1, lineType=cv2.LINE_AA) if al > 0.75 else None
        if al <= 0.75:
            y0, x0 = int(py), int(px)
            if 2 < y0 < H - 3 and 2 < x0 < W - 3:
                fr[y0 - 1:y0 + 2, x0 - 1:x0 + 2] = fr[y0 - 1:y0 + 2, x0 - 1:x0 + 2] * (1 - al) + al


def bg(t, k=1.0):
    s = 1.0 + 0.04 * (t / DUR)
    bh, bw = bg_big.shape[:2]
    cw, ch = int(W / s * 1.0), int(H / s)
    x = (bw - cw) // 2 + int(10 * math.sin(t * .3)); y = (bh - ch) // 2
    return cv2.resize(bg_big[y:y + ch, x:x + cw], (W, H)) * k


def leak(fr, strength, t):
    if strength <= 0.003: return
    g = np.zeros_like(fr)
    cx = W * (0.15 + 0.5 * math.sin(t * 1.3)); cy = H * 0.3
    d = np.sqrt((XX - cx) ** 2 + ((YY - cy) * 0.7) ** 2)
    m = np.exp(-(d / 650) ** 2)[..., None]
    g = m * np.array([1.0, 0.55, 0.25], np.float32)
    fr += g * strength
    np.clip(fr, 0, 1, out=fr)


YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
BAND = None


def sweep(fr, t, t0, dur=1.4, region=None):
    p = (t - t0) / dur
    if p < 0 or p > 1: return
    x = -400 + p * (W + 800)
    d = (XX - x) + (YY - H / 2) * 0.35
    m = np.exp(-(d / 70) ** 2) * 0.35 * math.sin(p * math.pi)
    fr += m[..., None]


def card(fr, t, alpha, scale, inner_zoom):
    if alpha <= 0: return
    cw, ch = int(CW * scale), int(CH * scale)
    pz = cover(ph_up, CW, CH, inner_zoom, 0.5, 0.42)
    pz = pz * (1 - CGRAD[:, None, None]) + np.array([0.12, 0.02, 0.1], np.float32) * CGRAD[:, None, None]
    pz = pz * (1 - CBORD[..., None]) + CBORD[..., None]
    lay = np.dstack([pz, CMASK])
    shl = np.dstack([np.zeros((*SHADOW.shape, 3), np.float32), SHADOW * 0.8])
    over(fr, shl, W / 2, CY + CH / 2 + 10, alpha, scale)
    over(fr, lay, W / 2, CY + CH / 2, alpha, scale)


def frame(t):
    fr = bg(t)
    # A: интро 0–2.1
    if t < 2.15:
        z = 2.3 - 0.5 * ease(t / 2.1)
        cl = cover(ph_up, W, H, z, 0.5, 0.34)
        b = max(0, 22 * (1 - t / 1.1))
        if b > 0.5: cl = cv2.GaussianBlur(cl, (0, 0), b)
        fr = cl * 0.8
        leak(fr, 1.1 * max(0, 1 - t / 1.0), t)
        a = win(t, 0.75, 2.1, 0.35, 0.3)
        over(fr, L_PREM_BIG, W / 2, H / 2, a, 1.12 - 0.12 * ease((t - 0.75) / 0.6))
        fr = fr * min(1, (2.15 - t) / 0.12 + 0) if t > 2.03 else fr
    # B: постер 2.0–16.4
    if 2.0 <= t < 16.6:
        a = win(t, 2.0, 16.6, 0.6, 0.45)
        s = 0.93 + 0.07 * ease((t - 2.0) / 0.8) + 0.03 * (t - 2) / 14
        card(fr, t, a, s, 1.0 + 0.08 * (t - 2) / 14)
        k = s
        over(fr, L_PREM_TOP, W / 2, 170 - rise(t, 2.4), win(t, 2.4, 16.4))
        by = CY + CH * k - (CH * k - CH) / 2
        over(fr, L_DATE, W / 2, by - 255 + rise(t, 2.9), win(t, 2.9, 16.4))
        over(fr, L_TIME, W / 2, by - 190 + rise(t, 3.2), win(t, 3.2, 16.4))
        over(fr, L_NAME, W / 2, by - 118 + rise(t, 3.6), win(t, 3.6, 16.4))
        over(fr, L_SONG, W / 2, by - 58 + rise(t, 3.9), win(t, 3.9, 16.4))
        over(fr, P_TG, W / 2, 1400 + rise(t, 4.4), win(t, 4.4, 16.4))
        sweep(fr, t, 6.3); sweep(fr, t, 12.0)
        leak(fr, 0.9 * max(0, 1 - abs(t - 2.05) / 0.35), t)
    # C: дата/артист 16.4–24.6
    if 16.3 <= t < 24.7:
        leak(fr, 0.8 * max(0, 1 - abs(t - 16.5) / 0.4), t)
        over(fr, C_DATE, W / 2, 840 + rise(t, V + 0.0, .4, 60), win(t, V + 0.0, V + 2.95, .35, .3), 1.06 - 0.06 * ease((t - V) / .5))
        over(fr, C_TIME, W / 2, 1010 + rise(t, V + 1.38, .4, 60), win(t, V + 1.38, V + 2.95, .35, .3))
        over(fr, C_N1, W / 2, 760 + rise(t, V + 3.16, .4, 60), win(t, V + 3.16, V + 7.6, .35, .3))
        over(fr, C_N2, W / 2, 920 + rise(t, V + 3.6, .4, 60), win(t, V + 3.6, V + 7.6, .35, .3))
        over(fr, C_SONG, W / 2, 1110, win(t, V + 5.15, V + 7.6, .25, .3), 1.25 - 0.25 * ease((t - V - 5.15) / .35))
        over(fr, C_PREMSI, W / 2, 1240 + rise(t, V + 5.8, .4, 40), win(t, V + 5.8, V + 7.6, .35, .3))
    # D: описание 24.1–31.2 (карточка + слова)
    if V + 7.5 <= t < V + 14.7:
        a = win(t, V + 7.5, V + 14.7, 0.5, 0.4)
        card(fr, t, a, 0.9, 1.04 + 0.05 * (t - V - 7.5) / 7)
        xs = [W / 2 - 300, W / 2, W / 2 + 300]
        for i, (w, ts) in enumerate(zip(D_W, (V + 8.3, V + 9.3, V + 10.6))):
            over(fr, w, xs[i], 1010 + rise(t, ts, .4, 50), win(t, ts, V + 14.5, .35, .3), 0.82)
        over(fr, D_NEW, W / 2, 1115 + rise(t, V + 12.9, .4, 50), win(t, V + 12.9, V + 14.5, .35, .3))
        sweep(fr, t, V + 11.0)
    # E: призыв
    if t >= V + 14.5:
        over(fr, E_1, W / 2, 700 + rise(t, V + 14.6), win(t, V + 14.6, 99))
        over(fr, E_2, W / 2, 830 + rise(t, V + 15.1, .45, 60), win(t, V + 15.1, 99), 1.08 - 0.08 * ease((t - V - 15.1) / .5))
        over(fr, E_3, W / 2, 960 + rise(t, V + 15.9), win(t, V + 15.9, 99))
        over(fr, P_TG_BIG, W / 2, 1130 + rise(t, V + 16.5), win(t, V + 16.5, 99))
        over(fr, E_4, W / 2, 1270 + rise(t, V + 17.0), win(t, V + 17.0, 99))
        sweep(fr, t, V + 17.2, 1.2)
    dust(fr, t)
    # зерно
    fr += (np.random.rand(H // 4, W // 4).astype(np.float32).repeat(4, 0).repeat(4, 1)[..., None] - .5) * 0.025
    return np.clip(fr, 0, 1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stills":
        for t in [1.2, 5.0, 17.5, 22.0, 27.5, 30.0, 34.5]:
            cv2.imwrite(f"/home/claude/vs/st_{t:05.1f}.jpg", (frame(t)[:, :, ::-1] * 255).astype(np.uint8))
        sys.exit()
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", "/home/claude/vs/main.mp4"], stdin=subprocess.PIPE)
    n = int(DUR * FPS)
    for i in range(n):
        p.stdin.write((frame(i / FPS) * 255).astype(np.uint8).tobytes())
        if i % 150 == 0: print(i, n, flush=True)
    p.stdin.close(); p.wait()
