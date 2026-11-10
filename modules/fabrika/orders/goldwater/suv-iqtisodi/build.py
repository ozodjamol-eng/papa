import cv2, numpy as np, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
W, H, FPS = 1080, 1920, 30
BLACK = "/usr/share/fonts/opentype/inter/Inter-Black.otf"; XB = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
GOLD = (236, 190, 92); WHITE = (255, 255, 255); GREY = (176, 184, 200)
SEG = "/home/claude/tz/seg"; KONC = "/home/claude/papa/docs/brand/ozod-jamol/koncovka/2s/OZOD_JAMOL_KONCOVKA_CHERNAYA.mp4"
def F(p, s): return ImageFont.truetype(p, s)
def ease(x): x = min(max(x, 0), 1); return 1 - (1 - x) ** 3
def tracked(d, y, text, font, fill, track=5):
    ws = [d.textlength(c, font=font) + track for c in text]; x = W / 2 - (sum(ws) - track) / 2
    for c, w in zip(text, ws): d.text((x, y), c, font=font, fill=fill, anchor="lm"); x += w
def fmt(n): return f"{n:,}".replace(",", " ")

class reader:
    def __init__(s, p, start=0):
        s.c = cv2.VideoCapture(p); s.c.set(cv2.CAP_PROP_POS_FRAMES, start); s.last = None
    def next(s):
        ok, f = s.c.read()
        if ok: s.last = f
        return s.last

ROLLS = {
 1: dict(name="KAPITAL", dur=5.8, src=(f"{SEG}/C.mp4", 0), vo=0.4,
         word="КАПИТАЛ", items=[("num", 1.33, 2300, "$", ""), ("sub", 3.13, "НОЯБРЬ НАРХИ")]),
 2: dict(name="KUNLIK_TUSHUM", dur=8.5, src=(f"{SEG}/C.mp4", 120), vo=0.4,
         word="КУНЛИК ТУШУМ", items=[("line", 0.6, "400 Л × 500 СЎМ"), ("small", 4.1, "ЎРТАЧА"), ("num", 4.25, 200000, "", " СЎМ")]),
 3: dict(name="SERVIS", dur=13.7, src=(f"{SEG}/D.mp4", 0), vo=0.4,
         word="СЕРВИС", items=[("line", 1.1, "БОСҚИЧМА-БОСҚИЧ"), ("row", 3.9, "30 Т", "ПАХТАЛИ ВА КЎМИРЛИ", 0), ("row", 7.15, "60 Т", "МЕМБРАНА", 1), ("row", 9.3, "90 Т", "МИНЕРАЛЛАШТИРУВЧИ", 2)]),
}
WHOLE = True
def render(k):
    R = ROLLS[k]; src = reader(*R["src"])
    out = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS),
        "-i", "-", "-c:v", "libx264", "-crf", "17", "-preset", "slow", "-pix_fmt", "yuv420p", f"w{k}.mp4"], stdin=subprocess.PIPE)
    navy = np.zeros((H, W, 3), np.float32); navy[:] = (70, 26, 8)
    for i in range(int(R["dur"] * FPS)):
        t = i / FPS; fr = src.next().astype(np.float32)
        fr = cv2.GaussianBlur(fr, (0, 0), 14)
        bg = fr * 0.32 + navy * 0.68
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        a = ease(t / 0.45)
        tracked(d, 560 + (1 - a) * 30, R["word"], F(BLACK, 96 if len(R["word"]) < 10 else 84), GOLD + (int(255 * a),), 6)
        d.line([(380, 650), (700, 650)], fill=GOLD + (int(150 * a),), width=4)
        for it in R["items"]:
            kind, ts = it[0], R["vo"] + it[1]
            b = ease((t - ts) / 0.4)
            if b <= 0: continue
            if kind == "num":
                _, _, val, pre, suf = it
                v = int(val * ease((t - ts) / 0.9)); v = v // (100 if val > 10000 else 1) * (100 if val > 10000 else 1)
                txt = pre + fmt(v) + suf; size = 180 if len(txt) < 8 else 132
                d.text((W / 2, 900 if k != 2 else 1040), txt, font=F(BLACK, size), fill=WHITE + (int(255 * b),), anchor="mm")
            elif kind == "sub":
                tracked(d, 1060 + (1 - b) * 20, it[2], F(XB, 52), GREY + (int(255 * b),), 8)
            elif kind == "line":
                tracked(d, 830 + (1 - b) * 20, it[2], F(BLACK, 66 if len(it[2]) < 18 else 54), WHITE + (int(255 * b),), 3)
            elif kind == "small":
                tracked(d, 930 + (1 - b) * 20, it[2], F(XB, 50), GREY + (int(255 * b),), 10)
            elif kind == "row":
                _, _, ton, lab, j = it; y = 980 + j * 150; x0 = 150 + (1 - b) * 50
                d.rounded_rectangle([110, y - 60, W - 110, y + 60], 26, fill=(12, 18, 36, int(200 * b)), outline=GOLD + (int(150 * b),), width=3)
                d.text((x0, y), ton, font=F(BLACK, 64), fill=GOLD + (int(255 * b),), anchor="lm")
                d.text((x0 + 175, y), lab, font=F(BLACK, 46 if len(lab) > 14 else 54), fill=WHITE + (int(255 * b),), anchor="lm")
            elif kind == "big2":
                tracked(d, 980 + (1 - b) * 25, it[2], F(BLACK, 76), GOLD + (int(255 * b),), 2)
        c = ease((t - (R["dur"] - 1.6)) / 0.4)
        if c > 0 and not WHOLE:
            d.rounded_rectangle([120, 1560, W - 120, 1760], 36, fill=(10, 16, 34, int(220 * c)), outline=GOLD + (int(200 * c),), width=3)
            d.text((W / 2, 1620), "+998 97 290 10 40", font=F(BLACK, 64), fill=WHITE + (int(255 * c),), anchor="mm")
            d.text((W / 2, 1705), "@GoldWaterAndijonBot", font=F(XB, 44), fill=GOLD + (int(255 * c),), anchor="mm")
        tracked(d, 1840, "GOLD WATER · СУВ ИҚТИСОДИ", F(XB, 34), GREY + (int(200 * a),), 6)
        rgba = np.asarray(im).astype(np.float32); al = rgba[..., 3:4] / 255
        f = bg * (1 - al) + rgba[..., :3][..., ::-1] * al
        out.stdin.write(f.astype(np.uint8).tobytes())
    kc = cv2.VideoCapture(KONC)
    while not WHOLE:
        ok, f = kc.read()
        if not ok: break
        out.stdin.write(cv2.resize(f, (W, H)).tobytes())
    out.stdin.close(); out.wait()
for k in [int(a) for a in sys.argv[1:]] or [1, 2, 3]: render(k)
