"""Dandana — сборка ролика 9:16 60 к/с (0 … 28.48 с), концовка OZOD JAMOL добавляется отдельно."""
import subprocess, sys
import numpy as np, cv2
from PIL import Image, ImageFilter
sys.path.insert(0, ".")
import gfx
from gfx import over, ease_out, ease_io, back_out, text_layer, M9, M8, OSW, W, H

FPS = 60
T_END = 28.48
T_FOOD, T_MENU, T_PEOPLE, T_DELIV, T_LOGO = 3.29, 16.50, 20.07, 22.49, 25.51
N = int(round(T_END * FPS))
ONLY = [float(x) for x in sys.argv[1:]]  # превью: список секунд → PNG

# ---------- фасад: день → ночь, зажигание света ----------
day = cv2.imread("day.jpg").astype(np.float32) / 255
night = cv2.imread("night_al.jpg").astype(np.float32) / 255
lum = cv2.cvtColor(night, cv2.COLOR_BGR2GRAY)
lm = np.clip((lum - 0.45) / 0.35, 0, 1)
lm = cv2.GaussianBlur(lm, (0, 0), 4)[..., None]
night_off = night * (1 - 0.82 * lm)
night_off = night_off * 0.92
hh, ww = lum.shape
yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
Tmap = np.where(yy < 300, 1.75 + 0.75 * (xx / ww), np.where(yy < 640, 2.55, 2.8 + 0.25 * (xx / ww))).astype(np.float32)
CX, CROP_W = 690, int(hh * 9 / 16)


def facade(t, img_override=None, zoom0=1.06, zoom1=1.09, dur=3.6):
    if img_override is None:
        a = ease_io((t - 0.6) / 1.3)
        base = day * (1 - a) + night_off * a
        rev = np.clip((t - Tmap) / 0.14, 0, 1)[..., None]
        # мерцание лампочек при включении
        flick = (np.sin(t * 90 + xx * 0.05) * 0.5 + 0.5)[..., None]
        rev = np.where((rev > 0) & (rev < 1), rev * (0.6 + 0.4 * flick), rev)
        img = base + (night - night_off) * rev * a
    else:
        img = img_override
    z = zoom0 + (zoom1 - zoom0) * ease_io(t / dur)
    cw, ch = CROP_W / z, hh / z
    x0, y0 = CX - cw / 2, (hh - ch) / 2 - 20 * (z - 1)
    M = np.float32([[W / cw, 0, -x0 * W / cw], [0, H / ch, -y0 * H / ch]])
    out = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    bl = cv2.GaussianBlur(out, (0, 0), 1.6)
    out = np.clip(out * 1.5 - bl * 0.5, 0, 1)  # мягкая резкость после апскейла
    return out[..., ::-1]  # BGR→RGB


# ---------- тексты ----------
def label(lines, size=78):
    lays = [text_layer(s, M9, size, color=(255, 255, 255), track=5) for s in lines]
    return lays


LABELS = [  # (start, end, строки)
    (T_FOOD, 5.68, ["ГЎШТ ТАОМЛАРИ"]),
    (5.68, 8.09, ["ЯНГИ САЛАТЛАР"]),
    (8.09, 11.69, ["ОЛОВДА ПИШГАН", "ШАШЛИК"]),
    (11.69, 12.88, ["МЕВА ТАРЕЛКАСИ"]),
    (12.88, 15.29, ["ИССИҚ ЧОЙ"]),
    (15.29, T_MENU, ["ТАНДИР НОН"]),
    (T_PEOPLE, T_DELIV, ["ОИЛАНГИЗ БИЛАН", "КЕЛИНГ"]),
]
LAB = [(a, b, label(ls)) for a, b, ls in LABELS]
KICK = text_layer("DANDANA", M9, 42, color="gold", track=16, shadow=True)


def draw_label(fr, t, a, b, lays):
    if not (a - 0.01 <= t < b):
        return
    k_in = ease_out((t - a - 0.05) / 0.4)
    k_out = 1 - ease_io((t - (b - 0.22)) / 0.2)
    if k_in <= 0:
        return
    base_y = 1430
    # золотая черта
    bw = int(140 * k_in)
    if bw > 2:
        bar = np.zeros((7, bw, 4), np.float32); bar[..., :3] = gfx.gold_fill(7, bw)[..., :3] / 255; bar[..., 3] = 1
        over(fr, bar, (W - bw) // 2, base_y - 26, alpha=k_out)
    over(fr, KICK, (W - KICK.shape[1]) // 2, base_y - 120 + int(20 * (1 - k_in)), alpha=k_in * k_out)
    y = base_y + 6
    for i, L in enumerate(lays):
        ki = ease_out((t - a - 0.12 - 0.1 * i) / 0.45)
        dy = int(46 * (1 - ki))
        over(fr, L, (W - L.shape[1]) // 2, y + dy, alpha=ki * k_out)
        y += L.shape[0] - 52


def bottom_grad(fr, k=1.0):
    g = np.linspace(0, 1, 760)[:, None, None] ** 1.6 * 0.78 * k
    fr[H - 760:] *= (1 - g)


# мини-бейдж в углу во время еды
PARTS = gfx.badge_parts(760)
MINI = None


def mini_badge():
    global MINI
    if MINI is None:
        b = np.zeros((760, 760, 4), np.float32)
        for k in ["disk", "ring", "burger", "word", "sub"]:
            over(b, PARTS[k], 0, 0)
        for s in PARTS["stars"]:
            over(b, s, 0, 0)
        MINI = cv2.resize(b, (150, 150), interpolation=cv2.INTER_AREA)
    return MINI


# ---------- меню-карточка ----------
ITEMS = ["ПИЦЦА", "БУРГЕР", "ШАШЛИК", "ОШ", "ШЎРВА", "ТАНДИР"]
ITEM_L = [text_layer(s, M9, 66, color=(255, 255, 255), track=4, shadow=False) for s in ITEMS]
MENU_K = text_layer("DANDANA  МЕНЮСИ", M9, 46, color="gold", track=10)
HAM1 = text_layer("ҲАММАСИ", M9, 108, color="gold", track=4)
HAM2 = text_layer("БИР ЖОЙДА", M9, 108, color="gold", track=4)
TW, TH = 440, 150


def tile(i):
    im = Image.new("L", (TW * 2, TH * 2), 0)
    from PIL import ImageDraw
    d = ImageDraw.Draw(im); d.rounded_rectangle([3, 3, TW * 2 - 4, TH * 2 - 4], radius=36, outline=255, width=6)
    border = gfx.colorize(im.resize((TW, TH), Image.LANCZOS), "gold")
    fill = np.zeros((TH, TW, 4), np.float32); fill[..., 3] = 0.55
    m = np.asarray(Image.new("L", (TW, TH), 0), np.float32)
    rr = Image.new("L", (TW * 2, TH * 2), 0); ImageDraw.Draw(rr).rounded_rectangle([3, 3, TW * 2 - 4, TH * 2 - 4], radius=36, fill=255)
    fill[..., 3] *= np.asarray(rr.resize((TW, TH), Image.LANCZOS), np.float32) / 255
    over(fill, border, 0, 0)
    L = ITEM_L[i]; over(fill, L, (TW - L.shape[1]) // 2, (TH - L.shape[0]) // 2)
    return fill


TILES = [tile(i) for i in range(6)]


def menu(fr, t):
    a = T_MENU
    k = ease_out((t - a) / 0.35)
    fr *= (1 - 0.62 * k)
    over(fr, MENU_K, (W - MENU_K.shape[1]) // 2, 430 - int(30 * (1 - k)), alpha=k)
    for i, Tl in enumerate(TILES):
        ti = a + 0.25 + i * 0.3
        ki = back_out((t - ti) / 0.4)
        ka = ease_out((t - ti) / 0.25)
        if ka <= 0:
            continue
        col, row = i % 2, i // 2
        x = 90 + col * (TW + 20); y = 560 + row * (TH + 26)
        s = 0.7 + 0.3 * ki
        T2 = cv2.resize(Tl, (max(int(TW * s), 1), max(int(TH * s), 1)), interpolation=cv2.INTER_AREA)
        over(fr, T2, x + (TW - T2.shape[1]) // 2, y + (TH - T2.shape[0]) // 2, alpha=ka)
    for j, L in enumerate([HAM1, HAM2]):
        tj = a + 2.38 + j * 0.12
        kj = ease_out((t - tj) / 0.45)
        over(fr, L, (W - L.shape[1]) // 2, 1150 + j * 120 + int(50 * (1 - kj)), alpha=kj)


# ---------- доставка ----------
DOST = text_layer("ДОСТАВКА", M9, 132, color="gold", track=6)
PH = [text_layer(s, M9, 104, color=(255, 255, 255), track=2) for s in ["97 990-00-01", "91 484-90-00"]]
SUBT = text_layer("БУЮРТМА УЧУН ҚЎНҒИРОҚ ҚИЛИНГ", M8, 40, color=(235, 225, 205), track=4)


def pill(w, h):
    from PIL import ImageDraw
    im = Image.new("L", (w * 2, h * 2), 0)
    ImageDraw.Draw(im).rounded_rectangle([3, 3, w * 2 - 4, h * 2 - 4], radius=h, outline=255, width=6)
    p = gfx.colorize(im.resize((w, h), Image.LANCZOS), "gold")
    rr = Image.new("L", (w * 2, h * 2), 0); ImageDraw.Draw(rr).rounded_rectangle([3, 3, w * 2 - 4, h * 2 - 4], radius=h, fill=255)
    f = np.zeros((h, w, 4), np.float32); f[..., 3] = 0.5 * np.asarray(rr.resize((w, h), Image.LANCZOS), np.float32) / 255
    over(f, p, 0, 0)
    return f


PILL = pill(860, 170)
NIGHT_BG = None


def delivery(t):
    global NIGHT_BG
    tt = t - T_DELIV
    fr = facade(tt, img_override=night, zoom0=1.12, zoom1=1.2, dur=3.0)
    fr = cv2.GaussianBlur(fr, (0, 0), 26) * 0.30
    k = ease_out(tt / 0.4)
    over(fr, DOST, (W - DOST.shape[1]) // 2, 560 + int(60 * (1 - k)), alpha=k)
    for i, L in enumerate(PH):
        ti = T_DELIV + 0.6 + i * 0.6
        ki = back_out((t - ti) / 0.45); ka = ease_out((t - ti) / 0.3)
        if ka <= 0:
            continue
        y = 800 + i * 210
        s = 0.8 + 0.2 * ki
        P2 = cv2.resize(PILL, (int(860 * s), int(170 * s)), interpolation=cv2.INTER_AREA)
        over(fr, P2, (W - P2.shape[1]) // 2, y + (170 - P2.shape[0]) // 2, alpha=ka)
        over(fr, L, (W - L.shape[1]) // 2, y + (170 - L.shape[0]) // 2 - 4, alpha=ka)
    ks = ease_out((t - T_DELIV - 1.6) / 0.4)
    over(fr, SUBT, (W - SUBT.shape[1]) // 2, 1260, alpha=ks)
    return fr


# ---------- логотип ----------
D = 760
ARCS = {}


def logo(t):
    tt = t - T_LOGO
    yy2, xx2 = np.mgrid[0:H, 0:W].astype(np.float32)
    fr = np.zeros((H, W, 3), np.float32) + np.array([0.035, 0.03, 0.025])
    glow = np.exp(-(((xx2 - W / 2) / 520) ** 2 + ((yy2 - H / 2) / 620) ** 2)) * 0.22 * ease_out(tt / 0.8)
    fr += glow[..., None] * np.array([0.95, 0.7, 0.35])
    lay = np.zeros((D, D, 4), np.float32)
    kd = ease_out(tt / 0.4)
    over(lay, PARTS["disk"], 0, 0, alpha=kd)
    fa = round(min(max(ease_io(tt / 0.6), 0), 1), 2)
    if fa > 0:
        if fa not in ARCS:
            ARCS[fa] = gfx.arc_reveal(D, fa)
        r = PARTS["ring"].copy(); r[..., 3] *= ARCS[fa]
        over(lay, r, 0, 0)
    kb = back_out((tt - 0.35) / 0.45); kba = ease_out((tt - 0.35) / 0.25)
    if kba > 0:
        s = max(0.01, 0.6 + 0.4 * kb)
        B = cv2.resize(PARTS["burger"], (int(D * s), int(D * s)), interpolation=cv2.INTER_AREA)
        cy = int(D * 0.29)
        over(lay, B, (D - B.shape[1]) // 2, int(cy - cy * s), alpha=kba)
    # DANDANA — проявление снизу вверх маской
    kw = ease_out((tt - 0.55) / 0.5)
    if kw > 0:
        Wd = PARTS["word"].copy()
        top, bot = int(D * 0.45), int(D * 0.66)
        cut = int(bot - (bot - top) * kw)
        Wd[:cut, :, 3] = 0
        sh = int(30 * (1 - kw))
        over(lay, np.roll(Wd, sh, axis=0), 0, 0)
    ks = ease_out((tt - 0.95) / 0.35)
    over(lay, PARTS["sub"], 0, int(15 * (1 - ks)), alpha=ks)
    for i, st in enumerate(PARTS["stars"]):
        ti = 1.21 + i * 0.29
        k = back_out((tt - ti) / 0.35); ka = ease_out((tt - ti) / 0.15)
        if ka > 0:
            s = max(0.01, k)
            cx, cy = D / 2 + (i - 1) * D * 0.105, D * 0.83
            M = np.float32([[s, 0, cx - s * cx], [0, s, cy - s * cy]])
            S2 = cv2.warpAffine(st, M, (D, D))
            over(lay, S2, 0, 0, alpha=ka)
    # блик-перелив по золоту
    sweep = (tt - 1.95) / 0.7
    if 0 < sweep < 1:
        band = np.exp(-(((xx2[:D, :D] + yy2[:D, :D] * 0.6) - (-200 + sweep * (D * 1.6 + 400))) / 60) ** 2)
        lay[..., :3] = np.clip(lay[..., :3] + band[..., None] * 0.55 * (lay[..., 3:4] > 0.5) * (lay[..., :3].mean(2, keepdims=True) > 0.4), 0, 1)
    z = 0.96 + 0.06 * ease_io(tt / 3.0)
    L2 = cv2.resize(lay, (int(D * z), int(D * z)), interpolation=cv2.INTER_AREA)
    over(fr, L2, (W - L2.shape[1]) // 2, (H - L2.shape[0]) // 2 - 40)
    return fr


def flash(fr, t, at, w=0.18, k=0.55):
    a = np.exp(-((t - at) / w) ** 2) * k
    if a > 0.01:
        fr[:] = fr * (1 - a) + np.array([1.0, 0.9, 0.7]) * a


# ---------- основной цикл ----------
def main():
    base = None
    if not ONLY:
        base = subprocess.Popen(["ffmpeg", "-v", "error", "-i", "base.mp4", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                                "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "body.mp4"], stdin=subprocess.PIPE)
    else:
        cap = cv2.VideoCapture("base.mp4")
    f0 = int(round(T_FOOD * FPS)); nb = 0; last = None
    frames = [int(round(s * FPS)) for s in ONLY] if ONLY else range(N)
    for f in frames:
        t = f / FPS
        if t < T_FOOD:
            fr = facade(t)
        elif t < T_DELIV:
            if ONLY:
                cap.set(cv2.CAP_PROP_POS_FRAMES, f - f0); ok, b = cap.read(); fr = b[..., ::-1].astype(np.float32) / 255
            else:
                while nb <= f - f0:
                    raw = base.stdout.read(W * H * 3)
                    if len(raw) == W * H * 3:
                        last = np.frombuffer(raw, np.uint8).reshape(H, W, 3)
                    nb += 1
                fr = last.astype(np.float32) / 255
            # живая камера: лёгкий наезд внутри каждой сцены
            if t < T_MENU or t >= T_PEOPLE:
                fr = np.ascontiguousarray(fr)
            if T_MENU <= t < T_PEOPLE:
                fr = cv2.GaussianBlur(fr, (0, 0), 14)
                menu(fr, t)
            else:
                bottom_grad(fr)
                for a, b, lays in LAB:
                    draw_label(fr, t, a, b, lays)
                mb = mini_badge(); kmb = ease_out((t - T_FOOD - 0.3) / 0.4) * (1 - ease_io((t - T_MENU + 0.2) / 0.2) if t < T_MENU else 1)
                over(fr, mb, W - 150 - 50, 90, alpha=0.92 * kmb)
        elif t < T_LOGO:
            fr = delivery(t)
        else:
            fr = logo(t)
        flash(fr, t, T_FOOD - 0.02, 0.09, 0.85)
        flash(fr, t, T_LOGO, 0.07, 0.35)
        out = (np.clip(fr, 0, 1) * 255).astype(np.uint8)
        if ONLY:
            Image.fromarray(out).save(f"prev_{t:05.2f}.png")
        else:
            enc.stdin.write(out.tobytes())
            if f % 120 == 0:
                print(f"{t:.1f}s", flush=True)
    if not ONLY:
        enc.stdin.close(); enc.wait(); base.terminate()


if __name__ == "__main__":
    main()
