import cv2, numpy as np, subprocess, json, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
BLACK = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
XB = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
GOLD = (236, 190, 92); WHITE = (255, 255, 255); RED = (225, 60, 60); GREY = (170, 176, 190)
SEG = "/home/claude/tz/seg"
def F(p, s): return ImageFont.truetype(p, s)
def ease(x): x = min(max(x, 0), 1); return 1 - (1 - x) ** 3
def dur(p): return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]))
VO = {f"N{i:02d}": dur(f"vo/N{i:02d}.mp3") for i in range(1, 12)}

def frames(path, speed=1.0, start=0.0):
    cap = cv2.VideoCapture(path); fr = []
    while True:
        ok, f = cap.read()
        if not ok: break
        fr.append(f)
    n0 = int(start * FPS)
    i = n0
    while True:
        k = int(round(i if speed == 1 else n0 + (i - n0) * speed))
        if k >= len(fr): k = len(fr) - 1
        yield fr[k]
        i += 1

def comp(fr, layer):
    rgba = np.asarray(layer).astype(np.float32); a = rgba[..., 3:4] / 255.0
    return (fr * (1 - a) + rgba[..., :3][..., ::-1] * a).astype(np.uint8)

def shade(fr, s=0.6, st=0.5):
    g = np.ones((H, 1, 1), np.float32); k = int(H * st)
    g[k:, 0, 0] = 1 - s * np.linspace(0, 1, H - k) ** 1.3
    return (fr.astype(np.float32) * g).astype(np.uint8)

def tracked(d, x_center, y, text, font, fill, track=3, anchor_mid=True):
    ws = [d.textlength(c, font=font) + track for c in text]; tw = sum(ws) - track
    x = x_center - tw / 2
    for c, w in zip(text, ws):
        d.text((x, y), c, font=font, fill=fill, anchor="lm"); x += w
    return tw

def plate(im, y0, y1, a):
    p = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(p).rectangle([0, y0, W, y1], fill=(8, 12, 24, int(160 * a)))
    return Image.alpha_composite(im, p.filter(ImageFilter.GaussianBlur(45)))

# ---------- backgrounds
def dark_bg():
    y = np.linspace(0, 1, H)[:, None]
    top = np.array([40, 22, 10], np.float32); bot = np.array([14, 8, 4], np.float32)
    g = (top * (1 - y) + bot * y)[:, None, :].repeat(W, 1)
    return np.ascontiguousarray(g.astype(np.uint8))   # BGR navy-ish

def iron_box(t):
    """generic grey vending box silhouette (not GOLD WATER)"""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    a = ease(t / 0.6); dy = (1 - a) * 60
    x0, y0, x1, y1 = 330, 470 + dy, 750, 1250 + dy
    d.rounded_rectangle([x0, y0, x1, y1], 26, fill=(92, 96, 104, int(255 * a)))
    d.rounded_rectangle([x0 + 30, y0 + 40, x1 - 30, y0 + 170], 14, fill=(60, 63, 70, int(255 * a)))
    d.rounded_rectangle([x0 + 70, y0 + 300, x1 - 70, y0 + 560], 16, fill=(38, 40, 46, int(255 * a)))
    d.rectangle([x0 + 200, y0 + 330, x0 + 220, y0 + 400], fill=(120, 124, 130, int(255 * a)))
    for i in range(3):
        d.ellipse([x1 - 120, y0 + 220 + i * 26, x1 - 100, y0 + 240 + i * 26], fill=(130, 134, 140, int(255 * a)))
    return im

out = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                        "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "17", "-preset", "slow", "-pix_fmt", "yuv420p",
                        "video.mp4"], stdin=subprocess.PIPE)
T = 0.0; VOPOS = []
def emit(f):
    global T
    out.stdin.write(f.tobytes()); T += 1 / FPS

BG = dark_bg()
# ---------- S1+S2: $800 / ФАҚАТ ТЕМИР
s1 = 0.35 + VO["N01"] + 0.35; s2 = 0.2 + VO["N02"] + 0.45
VOPOS.append(("N01", T + 0.35)); VOPOS.append(("N02", T + s1 + 0.2))
n = int((s1 + s2) * FPS)
for i in range(n):
    t = i / FPS
    im = iron_box(t); d = ImageDraw.Draw(im)
    a = ease((t - 0.5) / 0.4)
    if a > 0:
        sc = 1 + 0.25 * (1 - a)
        f = F(BLACK, int(190 * sc))
        d.text((W / 2, 1460), "$800", font=f, fill=WHITE + (int(255 * a),), anchor="mm")
        tracked(d, W / 2, 1600, "ИНТЕРНЕТДА", F(XB, 44), GREY + (int(255 * a),), 6)
    if t > s1 + 1.3:   # stamp
        b = ease((t - s1 - 1.3) / 0.25); sc = 1.6 - 0.6 * b
        st = Image.new("RGBA", (760, 170), (0, 0, 0, 0)); sd = ImageDraw.Draw(st)
        sd.rounded_rectangle([6, 6, 754, 164], 18, outline=RED + (255,), width=10)
        sd.text((380, 88), "ФАҚАТ ТЕМИР", font=F(BLACK, 92), fill=RED + (255,), anchor="mm")
        st = st.resize((int(760 * sc), int(170 * sc))).rotate(-8, expand=True, resample=Image.BICUBIC)
        stA = np.asarray(st).copy(); stA[..., 3] = (stA[..., 3] * b).astype(np.uint8); st = Image.fromarray(stA)
        im.alpha_composite(st, (int(W / 2 - st.width / 2), int(860 - st.height / 2)))
    emit(comp(BG.copy(), im))

# ---------- S3: four questions (timed to N03 pauses: 0, 1.56, 2.78, 4.24)
s3 = 0.3 + VO["N03"] + 0.45; VOPOS.append(("N03", T + 0.3))
Q = [("ЖОЙ?", 0.0), ("ЎРНАТИШ?", 1.56), ("ФИЛЬТР?", 2.78), ("ТАЪМИР?", 4.24)]
for i in range(int(s3 * FPS)):
    t = i / FPS
    im = iron_box(10); d = ImageDraw.Draw(im)
    # dim box
    arr = np.asarray(im).copy(); arr[..., 3] = (arr[..., 3] * 0.35).astype(np.uint8); im = Image.fromarray(arr); d = ImageDraw.Draw(im)
    for k, (q, tq) in enumerate(Q):
        a = ease((t - 0.3 - tq) / 0.3)
        if a <= 0: continue
        y = 560 + k * 230; x = W / 2 + (1 - a) * 80
        d.rounded_rectangle([170, y - 85, W - 170, y + 85], 30, fill=(28, 34, 52, int(235 * a)), outline=GOLD + (int(200 * a),), width=4)
        d.text((x, y), q, font=F(BLACK, 92), fill=WHITE + (int(255 * a),), anchor="mm")
    emit(comp(BG.copy(), im))

# ---------- S4: real machine footage, ТАЙЁР БИЗНЕС (C 0..)
s4 = 0.3 + VO["N04"] + 0.4; VOPOS.append(("N04", T + 0.3))
gC = frames(f"{SEG}/C.mp4")
for i in range(int(s4 * FPS)):
    t = i / FPS; fr = shade(next(gC))
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    a = ease((t - 0.3 - 1.4) / 0.45)   # on "Тайёр бизнес"
    if a > 0:
        im = plate(im, 1420, 1760, a); d = ImageDraw.Draw(im)
        tracked(d, W / 2, 1520, "GOLD WATER", F(XB, 48), GOLD + (int(255 * a),), 8)
        tracked(d, W / 2, 1630 + (1 - a) * 30, "ТАЙЁР БИЗНЕС", F(BLACK, 104), WHITE + (int(255 * a),), 4)
    emit(comp(fr, im))

# ---------- S5..S9: checklist over C (rest) then D slowed
ITEMS = [("N05", "ЖОЙНИ БИРГА ТАНЛАЙМИЗ"), ("N06", "ЎРНАТИБ БЕРАМИЗ"), ("N07", "ЎРГАТАМИЗ"),
         ("N08", "10 БОСҚИЧЛИ ТОЗАЛАШ"), ("N09", "СЕРВИС ВА ТАЪМИР")]
starts = []; acc = 0
for k, _ in ITEMS:
    starts.append(acc + 0.15); acc += 0.15 + VO[k] + 0.2
total = acc + 0.3
for (k, _), s in zip(ITEMS, starts): VOPOS.append((k, T + s))
def bgseq():
    for f in gC:
        yield f
gC2 = iter(()); usedC = 0
cframes = []
cap = cv2.VideoCapture(f"{SEG}/C.mp4")
while True:
    ok, f = cap.read()
    if not ok: break
    cframes.append(f)
cpos = int(s4 * FPS)
gD = frames(f"{SEG}/D.mp4", speed=0.75)
for i in range(int(total * FPS)):
    t = i / FPS
    if cpos < len(cframes): fr = cframes[cpos]; cpos += 1
    else: fr = next(gD)
    fr = shade(fr, 0.7, 0.42)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    im = plate(im, 1060, 1800, min(1, t / 0.4)); d = ImageDraw.Draw(im)
    for j, ((k, txt), s) in enumerate(zip(ITEMS, starts)):
        a = ease((t - s) / 0.35)
        if a <= 0: continue
        y = 1150 + j * 128; x0 = 105 + (1 - a) * 60
        d.ellipse([x0, y - 38, x0 + 76, y + 38], fill=GOLD + (int(255 * a),))
        d.line([(x0 + 20, y + 2), (x0 + 34, y + 18), (x0 + 58, y - 16)], fill=(20, 24, 40, int(255 * a)), width=9)
        d.text((x0 + 110, y), txt, font=F(BLACK, 54), fill=WHITE + (int(255 * a),), anchor="lm")
    emit(comp(fr, im))

# ---------- S10: price card
s10 = 0.3 + VO["N10"] + 0.5; VOPOS.append(("N10", T + 0.3))
lastD = cv2.GaussianBlur(fr, (0, 0), 30); navy = np.zeros_like(lastD); navy[:] = (60, 22, 8)
bgP = cv2.addWeighted(lastD, 0.3, navy, 0.7, 0)
for i in range(int(s10 * FPS)):
    t = i / FPS
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    a = ease(t / 0.4)
    tracked(d, W / 2, 640, "НОЯБРЬ ОЙИДА", F(XB, 56), GOLD + (int(255 * a),), 8)
    b = ease((t - 0.5) / 0.4)
    d.text((W / 2, 820), "$2 700", font=F(BLACK, 110), fill=GREY + (int(220 * b),), anchor="mm")
    if t > 1.0:
        s = ease((t - 1.0) / 0.3); d.line([(300, 840), (300 + 480 * s, 800)], fill=RED + (255,), width=12)
    c = ease((t - 1.5) / 0.4)
    if c > 0:
        d.text((W / 2, 1060 + (1 - c) * 40), "$2 300", font=F(BLACK, 230), fill=GOLD + (int(255 * c),), anchor="mm")
    emit(comp(bgP.copy(), im))

# ---------- S11: final thought (timed: "Арзон аппарат — бир марта тўлов." 0..2.39, "Тайёр бизнес — ҳар куни даромад" 2.8..)
s11 = 0.3 + VO["N11"] + 0.8; VOPOS.append(("N11", T + 0.3))
for i in range(int(s11 * FPS)):
    t = i / FPS
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    a = ease((t - 0.3) / 0.4); b = ease((t - 0.3 - 2.8) / 0.45)
    tracked(d, W / 2, 700, "АРЗОН АППАРАТ", F(BLACK, 76), GREY + (int(255 * a),), 3)
    tracked(d, W / 2, 800, "БИР МАРТА ТЎЛОВ", F(XB, 50), GREY + (int(230 * a),), 6)
    if b > 0:
        d.line([(240, 920), (W - 240, 920)], fill=GOLD + (int(160 * b),), width=3)
        tracked(d, W / 2, 1060 + (1 - b) * 30, "ТАЙЁР БИЗНЕС", F(BLACK, 104), WHITE + (int(255 * b),), 4)
        tracked(d, W / 2, 1190 + (1 - b) * 30, "ҲАР КУНИ ДАРОМАД", F(BLACK, 76), GOLD + (int(255 * b),), 4)
    fo = 1 - ease((t - (s11 - 0.35)) / 0.35) if t > s11 - 0.35 else 1
    f = comp(bgP.copy(), im)
    emit((f.astype(np.float32) * fo).astype(np.uint8))

# ---------- S12: contact card (from «Сувнинг йўли») with slow push + koncovka
MUS_END = T
cap = cv2.VideoCapture(f"{SEG}/F.mp4"); i = 0
while True:
    ok, f = cap.read()
    if not ok or i >= int(4.2 * FPS): break
    z = 1 + 0.035 * i / (4.2 * FPS)
    M = cv2.getRotationMatrix2D((W / 2, H * 0.42), 0, z)
    emit(cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)); i += 1
KON = T
cap = cv2.VideoCapture(f"{SEG}/G.mp4")
while True:
    ok, f = cap.read()
    if not ok: break
    emit(f)
out.stdin.close(); out.wait()
json.dump({"vo": VOPOS, "music_end": KON, "kon": KON, "total": T}, open("timeline.json", "w"), indent=1)
print(json.dumps({"total": T, "kon": KON}))
