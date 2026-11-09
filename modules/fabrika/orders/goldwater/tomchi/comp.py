import cv2, numpy as np, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
W, H, FPS = 1080, 1920, 30
BLACK = "/usr/share/fonts/opentype/inter/Inter-Black.otf"; XB = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
GOLD = (236, 190, 92); WHITE = (255, 255, 255)
SEG = "/home/claude/tz/seg"
def F(p, s): return ImageFont.truetype(p, s)
def ease(x): x = min(max(x, 0), 1); return 1 - (1 - x) ** 3
class load:
    def __init__(s, path):
        s.cap = cv2.VideoCapture(path); s.i = -1; s.f = None
        s.n = int(s.cap.get(cv2.CAP_PROP_FRAME_COUNT))
    def __len__(s): return s.n
    def __getitem__(s, k):
        k = min(k, s.n - 1)
        while s.i < k:
            ok, f = s.cap.read()
            if not ok: break
            s.f = f; s.i += 1
        return s.f
    def __iter__(s):
        while True:
            ok, f = s.cap.read()
            if not ok: return
            yield f
def comp(fr, im):
    a = np.asarray(im).astype(np.float32); al = a[..., 3:4] / 255
    return (fr * (1 - al) + a[..., :3][..., ::-1] * al).astype(np.uint8)
def tracked(d, y, text, font, fill, track=4):
    ws = [d.textlength(c, font=font) + track for c in text]; x = W / 2 - (sum(ws) - track) / 2
    for c, w in zip(text, ws): d.text((x, y), c, font=font, fill=fill, anchor="lm"); x += w
def title(lines, t, t0, t1, y0=1560):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if t < t0 or t > t1: return im
    a = ease((t - t0) / 0.45) * (1 - ease((t - (t1 - 0.35)) / 0.35))
    p = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hh = sum(int(s * 1.25) for _, s, _ in lines)
    ImageDraw.Draw(p).rectangle([0, y0 - 80, W, y0 + hh + 20], fill=(6, 10, 24, int(150 * a)))
    im = p.filter(ImageFilter.GaussianBlur(45)); d = ImageDraw.Draw(im); y = y0
    for txt, s, col in lines:
        tracked(d, y + (1 - a) * 25, txt, F(BLACK, s), col + (int(255 * a),)); y += int(s * 1.25)
    return im
out = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS),
                        "-i", "-", "-c:v", "libx264", "-crf", "17", "-preset", "slow", "-pix_fmt", "yuv420p", "video.mp4"], stdin=subprocess.PIPE)
n = 0
def emit(f):
    global n; out.stdin.write(f.tobytes()); n += 1
D3 = load("drop3d.mp4"); C = load(f"{SEG}/C.mp4"); Dd = load(f"{SEG}/D.mp4")
# A: 0–10.6 3D
for i in range(int(10.6 * FPS)):
    t = i / FPS
    emit(comp(D3[i], title([("ТОМЧИ", 110, WHITE), ("ОДДИЙ СУВ ТОМЧИСИ", 46, GOLD)], t, 0.6, 3.9)))
# live: C 2.5→5.6 (T4 at 10.8) then D 0→3.2 with counter (T5 at 14.0)
for k in range(int(3.1 * FPS)):
    t = 10.6 + k / FPS
    emit(comp(C[int(2.5 * FPS) + k], title([("GOLD WATER", 64, GOLD)], t, 10.9, 13.6)))
for k in range(int(3.2 * FPS)):
    t = 13.7 + k / FPS; fr = Dd[min(k, len(Dd) - 1)]
    im = title([("БОСҚИЧ", 50, GOLD)], t, 14.0, 16.9, 1700)
    c = ease((t - 14.1) / 2.0); num = max(1, min(10, 1 + int(c * 9.999)))
    if t >= 14.0:
        a = ease((t - 14.0) / 0.3); d = ImageDraw.Draw(im)
        d.text((W / 2, 1600), str(num), font=F(BLACK, 190), fill=WHITE + (int(255 * a),), anchor="mm")
    emit(comp(fr, im))
# B: 16.9–27.0 → 3D scene 11.0–21.1
for k in range(int(10.1 * FPS)):
    t = 16.9 + k / FPS; i = int(11.0 * FPS) + k
    emit(comp(D3[min(i, len(D3) - 1)], title([("ЕНГИЛ · ТИНИҚ · ТОЗА", 64, WHITE)], t, 23.0, 26.9)))
# final live: C 6.0→7.93 slowed 0.5 → 3.9 s (T8 at 27.2)
for k in range(int(3.9 * FPS)):
    t = 27.0 + k / FPS; fr = C[min(int(6.0 * FPS) + k // 2, len(C) - 1)]
    emit(comp(fr, title([("GOLD WATER", 54, GOLD), ("ҲАР БИР ТОМЧИ ТОЗА", 80, WHITE)], t, 27.4, 30.9, 1500)))
# card + koncovka
F_ = load(f"{SEG}/F.mp4")
for k in range(int(3.5 * FPS)):
    z = 1 + 0.035 * k / (3.5 * FPS); M = cv2.getRotationMatrix2D((W / 2, H * 0.42), 0, z)
    emit(cv2.warpAffine(F_[min(k, len(F_) - 1)], M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT))
KON = n / FPS
for f in load(f"{SEG}/G.mp4"): emit(f)
out.stdin.close(); out.wait(); print("kon", KON, "total", n / FPS)
