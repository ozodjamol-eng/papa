"""Шаблон Фабрики №7 «РЕТРО ДАВРА» (12.11.2026, проба: Maxx «Get-A-Way», 1993).
Живой клип в рамке «старого телевизора»: заставка с годом, наша неоновая плашка, кассета + эквалайзер по музыке,
VHS-сбой на склейках, карточки-факты, знак PAPARAZZI UZ в промежутках, финальный вопрос. Звук — только оригинал песни.
Запуск: python3 render_retro.py [stills]
"""
import sys, subprocess, math
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import json
CFG = json.load(open(sys.argv[1], encoding="utf-8")) if len(sys.argv) > 1 and sys.argv[1].endswith(".json") else {}
WD = CFG.get("dir", "/home/claude/retro")
SRC = f"{WD}/src.mp4"; OUT = f"{WD}/main.mp4"
TALL = bool(CFG.get("tall"))            # исходник — вертикальный клип во весь кадр (как Sandra), а не «окно» (как Maxx)
W, H, FPS = 1080, 1920, 30
SW, SH = 720, 1280
CY0, CY1 = CFG.get("crop", [334, 986])   # клип внутри исходника
DUR = float(CFG.get("dur", 180.0))
ARTIST, SONG, YEAR = CFG.get("artist", "MAXX"), CFG.get("song", "GET-A-WAY"), CFG.get("year", "1993")
FACT = tuple(CFG.get("fact", ("1993 · ГЕРМАНИЯ", "ЕВРОПАДА 1 МИЛЛИОНДАН ОРТИҚ", "НУСХА СОТИЛГАН")))
BLK = "/usr/share/fonts/opentype/inter/Inter-Black.otf"; XB = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
MAG, CYA, WHT, YEL = (255, 45, 170), (40, 230, 255), (255, 255, 255), (255, 214, 64)
CX, CYT = 0, (250 if TALL else 430)                          # клип на холсте
CW, CH = W, int((CY1 - CY0) * W / SW)     # 1080 x 978
CYB = CYT + CH


def text(t, size, col=WHT, font=BLK, glow=None, track=0):
    f = ImageFont.truetype(font, size)
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    w = sum(d.textlength(c, font=f) + track for c in t) - track
    pad = 50
    im = Image.new("RGBA", (int(w) + pad * 2, int(size * 1.35) + pad * 2), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im); x = pad
    for c in t:
        dr.text((x, pad), c, font=f, fill=col + (255,)); x += d.textlength(c, font=f) + track
    if glow:
        g = Image.new("RGBA", im.size, glow + (0,)); g.putalpha(im.split()[3].filter(ImageFilter.GaussianBlur(14)).point(lambda v: min(255, int(v * 1.6))))
        im = Image.alpha_composite(g, im)
    else:
        s = Image.new("RGBA", im.size, (0, 0, 0, 0)); s.putalpha(im.split()[3].filter(ImageFilter.GaussianBlur(8)).point(lambda v: int(v * .8)))
        im = Image.alpha_composite(s, im)
    return np.asarray(im).astype(np.float32) / 255


def pill(lines, sizes, cols, bg=(12, 6, 28), a=0.86, border=MAG):
    ls = [text(t, s, c) for t, s, c in zip(lines, sizes, cols)]
    w = max(l.shape[1] for l in ls) + 20; h = sum(l.shape[0] - 70 for l in ls) + 80
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, w - 1, h - 1], 36, fill=bg + (int(255 * a),), outline=border + (255,), width=5)
    out = np.asarray(im).astype(np.float32) / 255; y = 5
    for l in ls:
        x = (w - l.shape[1]) // 2; r = out[y:y + l.shape[0], x:x + l.shape[1]]
        al = l[..., 3:4]; r[..., :3] = r[..., :3] * (1 - al) + l[..., :3] * al; r[..., 3:4] = np.maximum(r[..., 3:4], al)
        y += l.shape[0] - 70
    return out


def put(cv, L, cx, cy, k=1.0):
    if k <= 0.01: return
    h, w = L.shape[:2]; x = int(cx - w / 2); y = int(cy - h / 2)
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0: return
    l = L[y0 - y:y1 - y, x0 - x:x1 - x]; a = l[..., 3:4] * k
    r = cv[y0:y1, x0:x1]; r[:] = (r * (1 - a) + l[..., :3] * 255 * a).astype(np.uint8)


def ease(x): x = min(1, max(0, x)); return 1 - (1 - x) ** 3
def win(t, a, b, fi=.35, fo=.35): return min(1, max(0, (t - a) / fi)) * min(1, max(0, (b - t) / fo))

# ---------- статичный фон ----------
yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]
bg = np.zeros((H, W, 3), np.float32)
bg[..., 0] = 26 + 30 * yy; bg[..., 1] = 8 + 4 * yy; bg[..., 2] = 52 + 26 * (1 - yy)
BG = bg.astype(np.uint8)
pil = Image.fromarray(BG); d = ImageDraw.Draw(pil)
for y, c in ((CYT - 14, CYA), (CYB + 8, MAG)):                      # неоновые линии
    d.rectangle([0, y, W, y + 6], fill=c)
BG = np.asarray(pil).copy()
gl = cv2.GaussianBlur(BG, (0, 0), 18); BG = cv2.addWeighted(BG, 1.0, gl, 0.55, 0)
if TALL:
    put(BG, text("КАТТА ДАВРА · РЕТРО", 56, WHT, BLK, glow=MAG, track=4), W / 2, 82)
    put(BG, text(f"{ARTIST} — {SONG} · {YEAR}", 40, WHT, BLK), W / 2, 178)
else:
    put(BG, text("КАТТА ДАВРА · РЕТРО", 62, WHT, BLK, glow=MAG, track=4), W / 2, 150)
    put(BG, text(f"{ARTIST} — {SONG}", 58, WHT, BLK), W / 2, 268)
    put(BG, text(YEAR, 54, YEL, BLK, track=6), W / 2, 350)
# кассета
KX, KY, KW, KH = 70, (1578 if TALL else 1500), 400, 250
pil = Image.fromarray(BG); d = ImageDraw.Draw(pil)
d.rounded_rectangle([KX, KY, KX + KW, KY + KH], 26, fill=(18, 12, 30), outline=CYA, width=5)
d.rounded_rectangle([KX + 40, KY + 50, KX + KW - 40, KY + 170], 60, fill=(48, 30, 70), outline=MAG, width=4)
d.rectangle([KX + 30, KY + 16, KX + KW - 30, KY + 40], fill=YEL)
d.polygon([(KX + 60, KY + KH), (KX + 90, KY + 195), (KX + KW - 90, KY + 195), (KX + KW - 60, KY + KH)], fill=(30, 20, 46), outline=CYA)
BG = np.asarray(pil).copy()
put(BG, text("RETRO DAVRA", 17, (20, 10, 30), BLK, track=3)[40:-40], KX + KW / 2, KY + 28)
put(BG, text("@kattadavrauz", 44 if TALL else 50, WHT, BLK, glow=CYA), (760 if TALL else W / 2), (1872 if TALL else 1838))
R1, R2 = (KX + 125, KY + 110), (KX + KW - 125, KY + 110)
# эквалайзер
NB, EX0, EX1, EYB, EHT = 16, 520, 1010, (1815 if TALL else 1740), (216 if TALL else 230)
BWD = (EX1 - EX0) // NB
# оверлеи
L_PLAY = text("PLAY", 34, WHT, BLK, track=3)
L_PAP = text("PAPARAZZI UZ", 64, WHT, BLK, glow=MAG, track=5)
L_FACT = pill(FACT, (44, 42, 42), (YEL, WHT, WHT))
L_Q = pill(("ЁДИНГИЗДАМИ?",), (68,), (WHT,), border=CYA)
I_YEAR = text(YEAR, 330, WHT, BLK, glow=MAG, track=10)
I_T = text("РЕТРО ДАВРА", 118, WHT, BLK, glow=CYA, track=6)
F1 = text("ЎШАНДА НЕЧА ЁШДА", 76, WHT, BLK); F2 = text("ЭДИНГИЗ?", 120, YEL, BLK, glow=MAG)
F3 = text("ИЗОҲДА ЁЗИНГ ↓", 60, WHT, BLK); F4 = text("@kattadavrauz", 64, WHT, BLK, glow=CYA)
DIG = {c: text(c, 34, WHT, BLK)[40:-40, 44:-44] for c in "0123456789:"}
SCAN = np.ones((CH, 1, 1), np.float32); SCAN[1::3] = 0.80
rng = np.random.default_rng(3)

# ---------- звук → полосы эквалайзера ----------
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", SRC, "-ac", "1", "-ar", "22050", "-f", "s16le", "-"], capture_output=True).stdout
au = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
N = 2048; edges = np.geomspace(3, N // 2 - 1, NB + 1).astype(int); hann = np.hanning(N)
def bands(t):
    i = int(t * 22050); s = au[i:i + N]
    if len(s) < N: return np.zeros(NB)
    m = np.abs(np.fft.rfft(s * hann))
    v = np.array([m[edges[k]:max(edges[k] + 1, edges[k + 1])].mean() for k in range(NB)])
    return np.clip(np.log10(1 + v * (1 + np.arange(NB) * .35)) / 1.9, 0, 1)
ALL = np.array([bands(i / FPS) for i in range(int(DUR * FPS) + 2)]); ALL /= max(1e-6, np.percentile(ALL, 99)); ALL = np.clip((ALL - 0.38) / 0.62, 0, 1) ** 1.3

state = {"prev": None, "glitch": -99.0, "eq": np.zeros(NB)}
PAP = [a for a in range(28, 600, 30) if a < DUR - 10]            # знак PAPARAZZI UZ в промежутках
CARDS = [c for c in [(20, 27.5, L_FACT), (62, 67.5, L_Q), (104, 111.5, L_FACT), (140, 145.5, L_Q)] if c[1] < DUR - 6]
PH = 130 if TALL else 96                # высота плашек PLAY / счётчика (в TALL счётчик закрывает чужое лого справа сверху)


def reel(cv, c, ang):
    cv2.circle(cv, c, 44, (235, 235, 245), -1); cv2.circle(cv, c, 44, MAG, 3); cv2.circle(cv, c, 15, (18, 12, 30), -1)
    for k in range(6):
        a = ang + k * math.pi / 3
        cv2.line(cv, (int(c[0] + 18 * math.cos(a)), int(c[1] + 18 * math.sin(a))), (int(c[0] + 38 * math.cos(a)), int(c[1] + 38 * math.sin(a))), (18, 12, 30), 6)


def frame(t, src):
    i = int(round(t * FPS)); cv = BG.copy()
    clip = cv2.resize(src[CY0:CY1], (CW, CH), interpolation=cv2.INTER_CUBIC)
    small = cv2.resize(clip, (64, 58), interpolation=cv2.INTER_AREA).astype(np.int16)
    if state["prev"] is not None and np.abs(small - state["prev"]).mean() > 34 and t - state["glitch"] > 7 and 4 < t < DUR - 6:
        state["glitch"] = t
    state["prev"] = small
    g = t - state["glitch"]
    if 0 <= g < 0.2:                                       # VHS-сбой на склейке
        k = 1 - g / 0.2
        for _ in range(7):
            y = int(rng.integers(0, CH - 60)); hh = int(rng.integers(12, 60)); dx = int(rng.integers(-70, 70) * k)
            clip[y:y + hh] = np.roll(clip[y:y + hh], dx, axis=1)
        clip[..., 0] = np.roll(clip[..., 0], int(10 * k), axis=1); clip[..., 2] = np.roll(clip[..., 2], -int(10 * k), axis=1)
    clip = (clip * SCAN).astype(np.uint8)
    if t > DUR - 4.6:                                      # финал: клип уходит в размытие
        k = ease((t - (DUR - 4.6)) / .8)
        clip = cv2.addWeighted(clip, 1 - k, (cv2.GaussianBlur(clip, (0, 0), 16) * .35).astype(np.uint8), k, 0)
    cv[CYT:CYB] = clip
    # PLAY-плашка (закрывает угол) + счётчик ленты
    cv2.rectangle(cv, (0, CYT), (300, CYT + PH), (10, 6, 22), -1)
    if (i // 20) % 2 == 0: cv2.fillPoly(cv, [np.array([(34, CYT + PH // 2 - 20), (34, CYT + PH // 2 + 20), (70, CYT + PH // 2)])], (60, 255, 120))
    put(cv, L_PLAY, 170, CYT + PH // 2 + 2)
    s = int(t); cnt = f"0:{s // 60:02d}:{s % 60:02d}"; x = W - 30 - sum(DIG[c].shape[1] + 2 for c in cnt)
    if TALL:
        cv2.rectangle(cv, (650, CYT), (W, CYT + PH), (10, 6, 22), -1); x = 650 + (W - 650 - (W - 30 - x)) // 2
    else:
        cv2.rectangle(cv, (x - 20, CYT), (W, CYT + 70), (10, 6, 22), -1)
    for c in cnt:
        put(cv, DIG[c], x + DIG[c].shape[1] / 2, CYT + (PH // 2 if TALL else 36)); x += DIG[c].shape[1] + 2
    # кассета и эквалайзер
    reel(cv, R1, t * 4.2); reel(cv, R2, t * 4.2 + .5)
    e = state["eq"] = np.maximum(ALL[min(i, len(ALL) - 1)], state["eq"] * 0.86)
    for k in range(NB):
        n = int(e[k] * 12 + .5)
        for j in range(n):
            col = MAG if j < 7 else (YEL if j < 10 else CYA)
            y = EYB - (j + 1) * (EHT // 12)
            cv2.rectangle(cv, (EX0 + k * BWD + 3, y + 3), (EX0 + (k + 1) * BWD - 3, y + EHT // 12 - 3), col, -1)
    # карточки
    for a, b, L in CARDS:
        k = win(t, a, b)
        if k > 0: put(cv, L, W / 2, CYB - 190 + 40 * (1 - ease((t - a) / .5)), k)
    # PAPARAZZI UZ: поднимается снизу клипа и гаснет
    for a in PAP:
        if a <= t < a + 4:
            p = (t - a) / 4
            put(cv, L_PAP, W / 2, CYB - 110 - 330 * p, 0.92 * min(1, p / .15) * min(1, (1 - p) / .35))
    # финал
    if t > DUR - 4.2:
        b0 = DUR - 4.2
        put(cv, F1, W / 2, CYT + 250, win(t, b0, 999)); put(cv, F2, W / 2, CYT + 400, win(t, b0 + .4, 999))
        put(cv, F3, W / 2, CYT + 570, win(t, b0 + 1.0, 999)); put(cv, F4, W / 2, CYT + 720, win(t, b0 + 1.5, 999))
        put(cv, L_PAP, W / 2, CYT + 860, win(t, b0 + 1.9, 999))
    # заставка
    if t < 3.0:
        k = 1 - ease((t - 2.4) / .6)
        if k > 0:
            intro = np.zeros((H, W, 3), np.uint8); intro[:] = (14, 6, 30)
            n = rng.integers(0, 50, (H // 6, 1, 1)).astype(np.uint8).repeat(6, 0); intro = cv2.add(intro, np.broadcast_to(n, intro.shape).copy())
            yb = int((t * 900) % H); intro[yb:yb + 26] = cv2.add(intro[yb:yb + 26], 70)
            put(intro, I_YEAR, W / 2 + (rng.integers(-8, 8) if t < .35 else 0), 820, win(t, .1, 9, .2), )
            put(intro, I_T, W / 2, 1120, win(t, 1.0, 9, .35))
            cv = cv2.addWeighted(intro, k, cv, 1 - k, 0)
    if t > DUR - .5: cv = (cv * max(0, (DUR - t) / .5)).astype(np.uint8)
    return cv


def reader(ss=None, n=None):
    cmd = ["ffmpeg", "-v", "error"] + (["-ss", str(ss)] if ss else []) + ["-i", SRC, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    while True:
        b = p.stdout.read(SW * SH * 3)
        if len(b) < SW * SH * 3: break
        yield np.frombuffer(b, np.uint8).reshape(SH, SW, 3)

if __name__ == "__main__":
    if "stills" in sys.argv:
        for t in [1.8, 10.0, 23.0, 30.0, 64.0, DUR - 1.0]:
            state.update(prev=None, glitch=-99.0 if t != 10.0 else 9.95)
            s = next(reader(ss=t)); cv2.imwrite(f"{WD}/s_{t:05.1f}.jpg", frame(t, s)[:, :, ::-1])
        sys.exit()
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "15", "-pix_fmt", "yuv420p", OUT], stdin=subprocess.PIPE)
    last = None
    for i, s in enumerate(reader()):
        if i >= int(DUR * FPS): break
        enc.stdin.write(frame(i / FPS, s).tobytes())
        if i % 600 == 0: print(i, flush=True)
    enc.stdin.close(); enc.wait()
