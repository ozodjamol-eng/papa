# Тизер «Орзу» — Safo Marva, Хўжаобод (02.11.2026). Вектор в стиле их Instagram: белая линия на бордовом, переходы через чёрное.
# A: рисуется пожилая пара (линейный рисунок Nano Banana, «проявляется» по линии от земли) — «Ота-онангиз бир умр кутган орзу…»
# B: линия-дорога ведёт к арке — «…энди сизга яқинроқ»
# C: арка → официальная золотая эмблема, SAFO MARVA, «ХЎЖАОБОДДА — ТЕЗ ОРАДА», номер. Потом чёрная концовка OZOD JAMOL.
# Музыка: Eleven Music ORZU_M2 (струнные, уд, ней; тихо). Запуск: python3 teaser_orzu.py <couple.jpg> <music.mp3> <out.mp4|sheet.png>
import sys, math, subprocess
from collections import deque
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
COUPLE, MUS, OUT = sys.argv[1:4]
PHONE = "+998 90 766 82 84"
W, H, FPS, DUR = 1080, 1920, 30, 22.5
F = "/home/claude/fonts/"; SERIF, MB, CZ = F + "NotoSerif800.ttf", F + "Montserrat800.ttf", F + "Cinzel800.ttf"
CREAM, MAROON, GOLD2, WHITE, RED = (244, 228, 196), (96, 12, 20), (246, 214, 150), (255, 255, 255), (227, 16, 30)
def eo(x): x = min(1, max(0, x)); return 1 - (1 - x) ** 3
def es(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
def win(t, a, b, fi=0.8, fo=0.6):
    if t < a or t > b: return 0.0
    return min(es((t - a) / fi), es((b - t) / fo))

# ---------- линия пары: маска + «геодезическое» время прорисовки ----------
src = Image.open(COUPLE).convert("L"); sc = W / src.width
src = src.resize((W, int(src.height * sc)), Image.LANCZOS)
L = np.asarray(src, np.float32) / 255; Hc = L.shape[0]
mask = L > 0.28
dist = np.full(mask.shape, -1.0, np.float32)
ys, xs = np.nonzero(mask)
order = np.lexsort((xs, -ys))              # старт: самые нижние точки (земля), слева направо
seen_total = 0.0; nb = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
for k in order:
    y0, x0 = ys[k], xs[k]
    if dist[y0, x0] >= 0: continue
    q = deque([(y0, x0)]); dist[y0, x0] = seen_total; mx = seen_total
    while q:
        y, x = q.popleft(); d = dist[y, x]
        for dy, dx in nb:
            yy, xx = y + dy, x + dx
            if 0 <= yy < Hc and 0 <= xx < W and mask[yy, xx] and dist[yy, xx] < 0:
                dist[yy, xx] = d + 1; mx = max(mx, d + 1); q.append((yy, xx))
    seen_total = mx + 1
DMAX = seen_total
LINE_RGBA = np.dstack([np.full_like(L, 255), np.full_like(L, 255), np.full_like(L, 255), L * 255])
# сдвиг рисунка: пара в нижней трети кадра
OFFY = int(H * 0.60 - Hc * 0.62)

def couple_layer(prog):
    a = L * (dist <= prog * DMAX) * (dist >= 0)
    # мягкий «кончик пера»: соседняя зона чуть светится
    tip = np.exp(-((dist - prog * DMAX) / 25.0) ** 2) * (dist >= 0) * (prog < 1)
    al = np.clip(np.maximum(a, L * tip * 0.6), 0, 1)
    im = np.dstack([np.full_like(L, 255), np.full_like(L, 250), np.full_like(L, 238), al * 255]).astype(np.uint8)
    return Image.fromarray(im, "RGBA")

# ---------- дорога к арке (кодом) ----------
VP = (W / 2, 640)                      # точка арки на горизонте
def road_pts(side, n=140):
    pts = []
    for i in range(n + 1):
        u = i / n; y = 1920 - (1920 - (VP[1] + 175)) * es(u) if False else 1920 - (1920 - (VP[1] + 175)) * u
        half = 26 + 470 * (1 - u) ** 1.6                       # ширина дороги: широко внизу, узко у арки
        bend = 90 * math.sin(u * math.pi) * (1 - u * 0.6)       # мягкий изгиб
        pts.append((W / 2 + bend + side * half, y))
    return pts
ROADL, ROADR = road_pts(-1), road_pts(1)
def arch_pts(cx, cy, w, h, n=90):
    r = w / 2; pts = [(cx - r, cy + h)]; pts += [(cx - r, cy)]
    pts += [(cx - r * math.cos(math.radians(a)), cy - r * math.sin(math.radians(a))) for a in range(0, 181, 3)]
    pts += [(cx + r, cy + h)]; return pts
def partial(pts, frac):
    if frac <= 0: return []
    n = max(2, int(len(pts) * min(1, frac))); return pts[:n]

def text_img(txt, size, fill, fnt=SERIF, track=0):
    f = ImageFont.truetype(fnt, size); d = ImageDraw.Draw(Image.new("L", (1, 1)))
    ws = [d.textlength(c, font=f) for c in txt]; tw = int(sum(ws) + track * (len(txt) - 1)) + 20
    a, b = f.getmetrics(); im = Image.new("RGBA", (tw, a + b + 16), (0, 0, 0, 0)); dd = ImageDraw.Draw(im); x = 10
    for c, w in zip(txt, ws): dd.text((x, 8), c, font=f, fill=fill); x += w + track
    return im
def pill(lines, size=54, fg=MAROON, bg=CREAM, fnt=SERIF):
    ims = [text_img(l, size, fg, fnt) for l in lines]; w = max(i.width for i in ims) + 70; lh = ims[0].height
    h = lh * len(ims) + 34; p = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(p).rounded_rectangle([0, 0, w - 1, h - 1], radius=26, fill=bg + (255,))
    for i, im in enumerate(ims): p.alpha_composite(im, ((w - im.width) // 2, 17 + i * lh))
    return p
CAP1 = pill(["Ота-онангиз бир умр", "кутган орзу…"])
CAP2 = pill(["…энди сизга", "яқинроқ"])
CAP3 = pill(["ХЎЖАОБОДДА —", "ТЕЗ ОРАДА"], size=60, fg=CREAM, bg=MAROON)
PH = pill([PHONE], size=56, fg=RED, bg=WHITE, fnt=MB)
WORD0 = text_img("SAFO MARVA", 104, GOLD2, CZ, track=8)
WORD = Image.new("RGBA", (1000, WORD0.height), (0, 0, 0, 0)); WORD.alpha_composite(WORD0, ((1000 - WORD0.width) // 2, 0))
_d = ImageDraw.Draw(WORD); _y = WORD0.height // 2 + 4
_d.line([(20, _y), ((1000 - WORD0.width) // 2, _y)], fill=GOLD2 + (255,), width=3)
_d.line([((1000 + WORD0.width) // 2, _y), (980, _y)], fill=GOLD2 + (255,), width=3)
EMB = Image.open("/home/claude/papa/docs/fabrika/orders/umra-assets/safomarva_emblema_zoloto.png").convert("RGBA")
EMB = EMB.resize((420, int(420 * EMB.height / EMB.width)), Image.LANCZOS)

def paste(fr, im, cx, cy, al=1.0, s=1.0, glow=0):
    if al <= 0.01: return
    if s != 1: im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    if al < 1: im = im.copy(); im.putalpha(im.split()[3].point(lambda v: int(v * al)))
    x, y = int(cx - im.width / 2), int(cy - im.height / 2)
    if glow:
        g = Image.new("RGBA", im.size, GOLD2 + (0,)); g.putalpha(im.split()[3].filter(ImageFilter.GaussianBlur(22)).point(lambda v: min(255, int(v * glow))))
        fr.alpha_composite(g, (x, y))
    fr.alpha_composite(im, (x, y))

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
BG = (np.array([40, 4, 8]) + np.clip(1 - np.hypot((xx - W / 2) / W, (yy - H * 0.42) / H) * 1.3, 0, 1)[..., None] * np.array([70, 10, 14])).astype(np.float32)
rng = np.random.default_rng(3); NP = 120
P = np.c_[rng.uniform(0, W, NP), rng.uniform(0, H, NP), rng.uniform(0.8, 2.4, NP), rng.uniform(5, 16, NP), rng.uniform(0, 6.28, NP)]
SCENES = [(1.4, 7.9), (8.5, 13.9), (14.5, DUR)]   # бордовые сцены; между ними — чёрное

def frame(t):
    vis = max(win(t, a, b, 0.7, 0.6) for a, b in SCENES)
    fr = Image.fromarray(np.clip(BG * vis, 0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(fr)
    # A — пара
    if 1.4 <= t <= 7.9:
        prog = es((t - 1.9) / 4.6); lay = couple_layer(prog)
        s = 1.0 + 0.04 * (t - 1.4) / 6.5
        if s != 1: lay = lay.resize((int(W * s), int(Hc * s)), Image.LANCZOS)
        lay.putalpha(lay.split()[3].point(lambda v: int(v * vis)))
        fr.alpha_composite(lay, (int((W - lay.width) / 2), int(OFFY - (lay.height - Hc) * 0.6 - 18 * (t - 1.4) / 6.5)))
        paste(fr, CAP1, W / 2, 470, win(t, 4.0, 7.6) * vis)
    # B — дорога к арке
    if 8.5 <= t <= 13.9:
        fr_ = es((t - 8.8) / 3.4); c = (255, 250, 238, int(255 * vis))
        for pts in (ROADL, ROADR):
            pp = partial(pts, fr_)
            if len(pp) > 1: d.line(pp, fill=c, width=4, joint="curve")
        if fr_ > 0.6: d.line([(W / 2 - 300, VP[1] + 175), (W / 2 + 300, VP[1] + 175)], fill=(255, 250, 238, int(255 * vis * es((fr_ - 0.6) / 0.4))), width=3)
        ap = partial(arch_pts(VP[0], VP[1], 220, 170), es((t - 11.0) / 1.6))
        if len(ap) > 1: d.line(ap, fill=c, width=5, joint="curve")
        paste(fr, CAP2, W / 2, 380, win(t, 10.6, 13.6) * vis)
    # C — эмблема и открытие
    if t >= 14.5:
        ax, ay, aw, ah = W / 2, 760, 400, 250
        ap = partial(arch_pts(ax, ay - 40, aw, ah + 120), es((t - 14.7) / 1.0))
        a_out = vis * (1 - es((t - 15.9) / 0.6))
        if len(ap) > 1 and a_out > 0: d.line(ap, fill=(255, 250, 238, int(255 * a_out)), width=6, joint="curve")
        ea = es((t - 15.7) / 0.9) * vis
        paste(fr, EMB, ax, ay + 20, ea, 0.96 + 0.04 * ea, glow=1.3 * ea)
        paste(fr, WORD, W / 2, 1120, win(t, 16.6, DUR, 0.8, 0.6))
        paste(fr, CAP3, W / 2, 1330, win(t, 17.6, DUR, 0.8, 0.6))
        paste(fr, PH, W / 2, 1530, win(t, 18.6, DUR, 0.7, 0.6))
    out = np.asarray(fr.convert("RGB")).astype(np.float32)
    dd = Image.new("L", (W, H), 0); dr = ImageDraw.Draw(dd)
    for (x0, y0, r, sp, ph) in P:
        x = (x0 + 10 * math.sin(t * 0.4 + ph)) % W; y = (y0 - sp * t) % H
        dr.ellipse([x - r, y - r, x + r, y + r], fill=int(255 * (0.5 + 0.5 * math.sin(t * 1.6 + ph))))
    ov = np.asarray(dd.filter(ImageFilter.GaussianBlur(1.2)), np.float32)[..., None] / 255
    out = out + ov * np.array(CREAM, np.float32) * 0.22 * vis
    out = out + rng.normal(0, 2.5, (H // 2, W // 2, 1)).repeat(2, 0).repeat(2, 1) * vis
    return np.clip(out, 0, 255).astype(np.uint8)

if OUT.endswith(".png"):
    tt = [3.0, 6.0, 9.8, 12.8, 15.4, 20.0]
    ims = [Image.fromarray(frame(x)).resize((270, 480)) for x in tt]
    sh = Image.new("RGB", (270 * len(ims), 480)); [sh.paste(im, (270 * i, 0)) for i, im in enumerate(ims)]; sh.save(OUT); sys.exit()

base = OUT + ".main.mp4"
ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                       "-i", MUS, "-filter_complex", f"[1:a]atrim=0:{DUR},afade=t=out:st={DUR - 1.5}:d=1.5,aresample=48000,pan=stereo|c0=c0|c1=c1[a]",
                       "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p",
                       "-c:a", "aac", "-b:a", "192k", "-t", str(DUR), base], stdin=subprocess.PIPE)
for n in range(int(DUR * FPS)):
    ff.stdin.write(frame(n / FPS).tobytes())
ff.stdin.close(); ff.wait()
END = "/home/claude/papa/docs/brand/ozod-jamol/koncovka/2s/OZOD_JAMOL_KONCOVKA_CHERNAYA.mp4"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", base, "-i", END, "-filter_complex",
                "[0:v]fps=30,setsar=1[a];[1:v]fps=30,scale=1080:1920,setsar=1[b];[0:a]aresample=48000[x];[1:a]aresample=48000[y];[a][x][b][y]concat=n=2:v=1:a=1[v][au]",
                "-map", "[v]", "-map", "[au]", "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart", OUT], check=True)
print("готово", OUT)
