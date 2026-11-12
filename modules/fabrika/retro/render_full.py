"""РЕТРО ДАВРА — режим «цельный кадр» (12.11.2026, урок владельца: «всегда ориентируйся на кадр»).
Клип во весь экран, без рамки/кассеты/обрезки и без эффектов на людях. Только: наша плашка закрывает чужое лого,
лёгкие надписи внизу (название → факт → вопрос), PAPARAZZI UZ в промежутках, финальный вопрос.
Запуск: python3 render_full.py cfg.json [stills]   (cfg: dir, dur, artist, song, year, fact[2], logo [x0,y0,x1,y1] в пикселях исходника)
"""
import sys, subprocess
import numpy as np, cv2
sys.path.insert(0, "/home/claude/papa/modules/fabrika/retro")
import render_retro as R
from render_retro import text, pill, put, ease, win, CFG, WD, SRC, DUR, W, H, FPS, SW, SH, BLK, MAG, CYA, WHT, YEL

OUT = f"{WD}/full.mp4"
lx0, ly0, lx1, ly1 = [int(v * W / SW) for v in CFG["logo"]]
PLATE = pill(("КАТТА ДАВРА", "РЕТРО"), (46, 40), (WHT, YEL), a=1.0, border=MAG)
pw, ph = max(lx1 - lx0 + 40, PLATE.shape[1]), max(ly1 - ly0 + 40, PLATE.shape[0])
PLATE = cv2.resize(PLATE, (pw, ph), interpolation=cv2.INTER_AREA)
PCX, PCY = (lx0 + lx1) / 2, (ly0 + ly1) / 2
T1 = text(f"{CFG['artist']} — {CFG['song']}", 60, WHT, BLK)
if T1.shape[1] > W - 40: T1 = cv2.resize(T1, (W - 40, int(T1.shape[0] * (W - 40) / T1.shape[1])), interpolation=cv2.INTER_AREA); T2 = text(CFG["year"], 76, YEL, BLK, glow=MAG, track=6)
FACT = pill(tuple(CFG["fact"]), (50, 50), (YEL, WHT), a=0.72, border=MAG)
Q = pill(("ЁДИНГИЗДАМИ?",), (70,), (WHT,), a=0.72, border=CYA)
PAPL = text("PAPARAZZI UZ", 64, WHT, BLK, glow=MAG, track=5)
F1 = text("ЎШАНДА НЕЧА ЁШДА", 76, WHT, BLK); F2 = text("ЭДИНГИЗ?", 120, YEL, BLK, glow=MAG)
F3 = text("ИЗОҲДА ЁЗИНГ ↓", 60, WHT, BLK); F4 = text("@kattadavrauz", 64, WHT, BLK, glow=CYA)
CAPY = 1500
PAP = [a for a in range(28, 600, 30) if a < DUR - 10]
CARDS = [(c0, c1, L) for c0, c1, L in [(18, 25, FACT), (44, 49.5, Q), (104, 111, FACT), (140, 145.5, Q)] if c1 < DUR - 6]


def frame(t, src):
    cv = cv2.resize(src, (W, H), interpolation=cv2.INTER_CUBIC)
    if t > DUR - 4.4:                                   # финал: кадр темнее, чтобы читался вопрос
        k = ease((t - (DUR - 4.4)) / .7); cv = (cv * (1 - 0.6 * k)).astype(np.uint8)
    put(cv, PLATE, PCX, PCY)
    k = win(t, 1.0, 8.0, .5, .5)
    put(cv, T1, W / 2, CAPY + 30 * (1 - ease((t - 1.0) / .6)), k); put(cv, T2, W / 2, CAPY + 110, win(t, 1.6, 8.0, .5, .5))
    for a, b, L in CARDS:
        put(cv, L, W / 2, CAPY + 40 + 40 * (1 - ease((t - a) / .5)), win(t, a, b))
    for a in PAP:
        if a <= t < a + 4:
            p = (t - a) / 4
            put(cv, PAPL, W / 2, 1620 - 330 * p, 0.92 * min(1, p / .15) * min(1, (1 - p) / .35))
    if t > DUR - 4.0:
        b0 = DUR - 4.0
        put(cv, F1, W / 2, 700, win(t, b0, 999)); put(cv, F2, W / 2, 850, win(t, b0 + .4, 999))
        put(cv, F3, W / 2, 1020, win(t, b0 + 1.0, 999)); put(cv, F4, W / 2, 1170, win(t, b0 + 1.5, 999))
        put(cv, PAPL, W / 2, 1310, win(t, b0 + 1.9, 999))
    if t < .4: cv = (cv * (t / .4)).astype(np.uint8)
    if t > DUR - .5: cv = (cv * max(0, (DUR - t) / .5)).astype(np.uint8)
    return cv


if __name__ == "__main__":
    if "stills" in sys.argv:
        for t in [3.0, 21.0, 30.0, 46.0, 60.0, DUR - 1.0]:
            cv2.imwrite(f"{WD}/f_{t:05.1f}.jpg", frame(t, next(R.reader(ss=t)))[:, :, ::-1])
        sys.exit()
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "15", "-pix_fmt", "yuv420p", OUT], stdin=subprocess.PIPE)
    for i, s in enumerate(R.reader()):
        if i >= int(DUR * FPS): break
        enc.stdin.write(frame(i / FPS, s).tobytes())
    enc.stdin.close(); enc.wait()
