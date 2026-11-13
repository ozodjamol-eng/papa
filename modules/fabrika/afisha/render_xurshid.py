# Шаблон «Концертная афиша с озвучкой» — вариант «живой клип на весь экран» (Хуршид Расулов, 13.11.2026)
# python3 -I render_xurshid.py stills | full
import sys, os, subprocess, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, cv2
from PIL import Image
import render_otabek as R
from render_otabek import W, H, FPS, gtext, wtext, blit, chip, pill, ribbon, line_pair, eio, ease, app, win, GOLD, BLK, SCR, PF, BOD, font, mask_text, layer, gold_fill

WD = "/home/claude/work"; SRC = "/mnt/user-data/uploads/3a0e0885-8c28db5a.mp4"
V = 4.5; DUR = 29.5        # правило владельца 13.11: ≥4 с музыки до диктора, ~3 с музыки после
ANT = "/home/claude/papa/.claude/skills/talking-head-reels/assets/fonts/Anton-Regular.ttf"
# палитра по анализу фона (palette.py): тон 206° синий → белый текст, акцент лёд, плашка тёмно-синяя, золото запрещено
ICE = np.array([0.58, 0.82, 1.0], np.float32); NAVY = np.array([0.033, 0.088, 0.13], np.float32); GLOW = (0.10, 0.30, 0.48)
def ice_fill(m):
    ys = np.where(m.max(1) > 0.05)[0]; y0, y1 = (ys[0], ys[-1]) if len(ys) else (0, m.shape[0] - 1)
    g = np.clip((np.arange(m.shape[0]) - y0) / max(1, y1 - y0), 0, 1)
    st = [(0, (1, 1, 1)), (0.45, (0.92, 0.97, 1.0)), (0.78, (0.60, 0.83, 1.0)), (1, (0.76, 0.91, 1.0))]
    col = np.stack([np.interp(g, [a for a, _ in st], [c[i] for _, c in st]) for i in range(3)], 1).astype(np.float32)
    return np.repeat(col[:, None, :], m.shape[1], 1)
R.gold_fill = ice_fill; R.GOLD = ICE
def itext(text, path, size, tr=0): return gtext(text, path, size, tr, glow=GLOW)
T = 0.6153; B0 = 0.152
def b(n): return B0 + n * T
# (конец на шкале ролика, начало в клипе, конец в клипе, обработка)
SHOTS = [
    (b(3), 31.15, 32.50, ""),            # сцена, огни            ┐ 4,5 с — только музыка,
    (b(5), 0.20, 1.43, ""),              # зал                    │
    (b(7), 14.15, 15.38, ""),            # зал                    ┘ зритель узнаёт артиста по песне
    (b(10), 18.459, 20.305, ""),         # артист крупно (губы в такт: звук = клип + 14,0 с)
    (b(13), 36.90, 38.75, ""),           # артист средний
    (b(16), 2.80, 4.65, ""),             # зал танцует
    (b(18), 7.35, 8.58, ""),             # зрительница подпевает
    (b(20), 50.20, 51.40, ""),           # зрительница
    (b(22), 15.50, 16.73, ""),           # зал
    (b(29), 39.10, 42.70, ""),           # лучи — под дату
    (b(32), 54.00, 55.85, ""),           # артист
    (b(37), 45.60, 48.68, ""),           # артист на сцене
    (b(40), 56.50, 58.15, ""),           # артист ближе
    (b(42), 22.70, 23.93, ""),           # артист поёт — музыка возвращается
    (b(45), 64.40, 66.25, ""),           # артист на сцене
    (DUR, 70.36, 71.66, "blend"),        # рука вверх — замедленно
]


def shot_frames():
    t0 = 0.0; f0 = 0
    for end, a, c, mode in SHOTS:
        f1 = int(round(end * FPS)); n = f1 - f0; k = (n / FPS) / (c - a)
        vf = f"setpts={k:.5f}*(PTS-STARTPTS)," + ("minterpolate=fps=30:mi_mode=blend," if mode == "blend" else "fps=30,") + \
             "scale=1080:1920:flags=lanczos,unsharp=5:5:0.55:5:5:0.0"
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{a:.3f}", "-t", f"{c - a:.3f}", "-i", SRC, "-an", "-vf", vf,
                              "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        last = None; got = 0
        while got < n:
            buf = p.stdout.read(W * H * 3)
            if len(buf) < W * H * 3: break
            last = np.frombuffer(buf, np.uint8).reshape(H, W, 3); got += 1
            yield last
        while got < n:
            got += 1; yield last
        p.stdout.close(); p.wait(); f0 = f1


yy = R.yy
TOPG = (np.clip((320 - yy) / 320, 0, 1) ** 1.3 * 0.66)[..., None]
T_RIB = ribbon("O'ZBEKISTONDA XIZMAT KO'RSATGAN ARTIST")
T_N1 = wtext("XURSHID", ANT, 104, 16)
T_N2 = itext("RASULOV", ANT, 200, 6)
T_KON = wtext("KONSERT DASTURI", BLK, 46, 14, col=tuple(ICE))
T_V1 = wtext("ISLOM KARIMOV NOMIDAGI", BLK, 38, 9)
T_V2 = itext("FARG'ONA SAN'AT SAROYI", BLK, 70, 2)
T_INV1 = wtext("BARCHANGIZNI KONSERTDA", BLK, 66, 1)
T_INV2 = itext("KUTIB QOLAMIZ!", BLK, 96, 2)
D_NUM = itext("8", ANT, 640)
D_DEK = wtext("DEKABR", BLK, 150, 14)
D_P1 = pill("14:00", 92); D_P2 = pill("18:00", 92); D_VA = wtext("VA", BLK, 64, 4)
D_SOAT = wtext("SOAT", BLK, 54, 16, col=tuple(ICE))


def chip_wide():
    from PIL import ImageDraw
    w, h = 900, 112
    im = Image.new("RGBA", (w + 60, h + 60), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([30, 30, 30 + w, 30 + h], 26, fill=(8, 22, 34, 240), outline=(148, 209, 255, 255), width=5)
    f = font(BLK, 48); t1 = "8 DEKABR"; t2 = "14:00  VA  18:00"; w1 = f.getlength(t1); w2 = f.getlength(t2); gap = 60
    x = 30 + (w - (w1 + gap + w2)) / 2; y = 30 + (h - 48) / 2 - 8
    d.text((x, y), t1, font=f, fill=(148, 209, 255, 255))
    d.line([x + w1 + gap / 2, 56, x + w1 + gap / 2, 30 + h - 26], fill=(148, 209, 255, 255), width=4)
    d.text((x + w1 + gap, y), t2, font=f, fill=(255, 255, 255, 255))
    a = np.asarray(im, np.float32) / 255
    return a, None, a[..., 3]
CHW = chip_wide()
P_MAIN = itext("(94) 555-22-00", BLK, 92, 2)
P_SUB = wtext("(95) 555-22-00   ·   (73) 249-22-00", BLK, 40, 1)
P_LBL = wtext("MA'LUMOT UCHUN", BLK, 34, 10, col=tuple(ICE))


def compose(src, t):
    fr = src.astype(np.float32) / 255
    off = 150 * (1 - eio((t - (V + 10.4)) / 1.2))
    # тёмная подложка под нижние тексты (появляется с лентой)
    pa = eio((t - (V - 0.5)) / 0.8)
    pm_ = (np.clip((yy - 930 - off) / 280, 0, 1) ** 1.15 * 0.95)[..., None] * pa
    fr = fr * (1 - pm_) + NAVY * 0.55 * pm_
    inv = app(t, V + 18.9, 0.5)
    va = app(t, V + 5.9, 0.6) * (1 - inv)
    top = max(va, inv)
    if top > 0: fr = fr * (1 - TOPG * top) + NAVY * 0.5 * TOPG * top
    blit(fr, T_V1, W / 2, 128 - 20 * (1 - va), va)
    blit(fr, T_V2, W / 2, 206 - 20 * (1 - va), app(t, V + 6.7, 0.6) * (1 - inv), shine=(t - (V + 7.0)) / 1.1)
    blit(fr, T_INV1, W / 2, 122, inv)
    i2 = app(t, V + 19.9, 0.45)
    blit(fr, T_INV2, W / 2, 222, i2, scale=1.12 - 0.12 * i2, shine=(t - (V + 20.2)) / 1.0)
    ra = app(t, V + 0.0, 0.7)
    blit(fr, T_RIB, W / 2, 1128 + off, ra, wipe=None if ra >= 1 else ra)
    n1 = app(t, V + 2.2, 0.45)
    blit(fr, T_N1, W / 2, 1218 + off + 24 * (1 - n1), n1)
    ma = app(t, V + 2.75, 0.5)
    blit(fr, T_N2, W / 2, 1376 + off, ma, scale=1.10 - 0.10 * ma, shine=(t - (V + 3.3)) / 1.2)
    ka = app(t, V + 4.13, 0.5)
    blit(fr, T_KON, W / 2, 1506 + off, ka); line_pair(fr, int(1506 + off), 350, ka)
    c1 = app(t, V + 13.6, 0.5)
    blit(fr, CHW, W / 2, 1596 + 40 * (1 - c1), c1)
    blit(fr, P_LBL, W / 2, 1680, app(t, V + 13.75, 0.5))
    pm = app(t, V + 14.8, 0.5)
    blit(fr, P_MAIN, W / 2, 1748, pm, scale=1.08 - 0.08 * pm, shine=(t - (V + 15.2)) / 1.2)
    blit(fr, P_SUB, W / 2, 1822, app(t, V + 17.0, 0.6))
    # дата на весь экран
    dd = win(t, V + 9.45, V + 13.65, 0.35, 0.35)
    if dd > 0:
        sm = cv2.resize(fr, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        sm = cv2.resize(cv2.GaussianBlur(sm, (0, 0), 4), (W, H), interpolation=cv2.INTER_LINEAR)
        fr = fr * (1 - dd) + (sm * 0.34 + NAVY * 0.35) * dd
        a0 = V + 9.45; pop = app(t, a0, 0.4)
        blit(fr, D_NUM, W / 2, 640, dd, scale=1.16 - 0.16 * pop, shine=(t - a0 - 0.3) / 1.3)
        k = app(t, a0 + 0.5, 0.45); blit(fr, D_DEK, W / 2, 1040 + 30 * (1 - k), dd * k)
        k0 = app(t, V + 10.9, 0.4); blit(fr, D_SOAT, W / 2, 1190, dd * k0)
        k1 = app(t, V + 11.2, 0.4); blit(fr, D_P1, 262, 1330 + 30 * (1 - k1), dd * k1)
        k2 = app(t, V + 12.3, 0.4); blit(fr, D_VA, W / 2, 1330, dd * k2); blit(fr, D_P2, 818, 1330 + 30 * (1 - k2), dd * k2)
    kk = min(eio(t / 0.5), eio((DUR - t) / 0.45))
    return (np.clip(fr * kk, 0, 1) * 255).astype(np.uint8)


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "stills":
        want = {int(round(float(x) * FPS)): float(x) for x in (sys.argv[2:] or ["2.5", "5.6", "7.6", "11.9", "16.9", "21.5", "25.6", "28.6"])}
        for i, src in enumerate(shot_frames()):
            if i in want:
                Image.fromarray(compose(src, i / FPS)).save(f"{WD}/x2/st_{want[i]:05.1f}.jpg", quality=90)
            if i > max(want): break
    else:
        tmp = WD + "/x2/main.tmp.mp4"
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                              "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
        n = 0
        for i, src in enumerate(shot_frames()):
            p.stdin.write(compose(src, i / FPS).tobytes()); n += 1
            if i % 90 == 0: print(i, flush=True)
        p.stdin.close()
        if p.wait() == 0: os.replace(tmp, WD + "/x2/main.mp4"); print("OK", n)
