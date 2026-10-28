"""«Занжир» — эпоха Вивальди (барокко). Живые картины Flow + цепь ремёсел кодом + титры в стиле эпохи."""
import numpy as np, subprocess, math, json
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

W, H, FPS = 1080, 1920, 24
SRC = "/home/claude/bar/src/"
FG = "/home/claude/bar/fonts/cormorant-garamond-700.ttf"
FG6 = "/home/claude/bar/fonts/cormorant-garamond-600.ttf"
FSC = "/home/claude/bar/fonts/cormorant-sc-700.ttf"
F = lambda s, p=FG: ImageFont.truetype(p, s)
GOLD = (226, 176, 74)
CREAM = (243, 230, 200)
BROWN = (52, 34, 22)
INK = (40, 24, 14)

V = {"Z01": 0.30, "Z02": 8.25, "Z03": 18.35, "Z04": 29.20, "Z05": 35.30, "Z06": 40.30}
SC = [("crowd", 0.0, 8.1), ("herald", 8.1, 14.0), ("cat", 14.0, 18.15), ("sage", 18.15, 21.9),
      ("chain", 21.9, 29.0), ("break", 29.0, 31.75), ("crowd2", 31.75, 35.05), ("reveal", 35.05, 40.1),
      ("cta", 40.1, 45.4)]
TOTAL = 45.4

WORDS = {
 "Z01": [("1725 йил,", 0, 1.78), ("Венеция.", 2.02, 2.66), ("Бу", 3.04, 3.22), ("савдогар", 3.22, 3.74), ("бир", 4.0, 4.16),
         ("ҳафтада", 4.16, 4.62), ("бутун", 4.62, 5.06), ("шаҳарга", 5.06, 5.5), ("машҳур", 5.5, 5.88), ("бўлди.", 5.88, 6.24),
         ("Сири", 6.44, 6.8), ("нимада?", 6.8, 7.45)],
 "Z02": [("Аввалига", 0, .5), ("у", .58, .84), ("битта", .84, 1.3), ("жарчи", 1.3, 1.64), ("ёллади.", 1.64, 2.0),
         ("Жарчи", 2.34, 2.78), ("бақирди,", 2.78, 3.38), ("расм", 3.62, 4.0), ("чизди,", 4.0, 4.5), ("шеър", 4.7, 5.05),
         ("ёзди...", 5.05, 5.48), ("Натижа:", 5.92, 6.4), ("битта", 6.78, 7.24), ("мушук", 7.24, 7.54), ("келди.", 7.54, 7.94),
         ("Унинг", 8.22, 8.5), ("ҳам", 8.5, 8.7), ("пули", 8.7, 8.98), ("йўқ", 8.98, 9.2), ("экан.", 9.2, 9.5)],
 "Z03": [("Шунда", 0, .28), ("донишманд", .28, .8), ("келди:", .8, 1.26), ("«Савдо", 1.64, 2.16), ("— бу", 2.16, 2.56),
         ("занжир!", 2.56, 3.18), ("Маслаҳатчи,", 3.54, 4.34), ("жарчи,", 4.58, 5.08), ("рассом,", 5.42, 6.0),
         ("шоир,", 6.16, 6.72), ("мусаввир,", 6.88, 7.48), ("наққош,", 7.82, 8.42), ("котиб", 8.64, 9.14), ("ва", 9.14, 9.42),
         ("камончи.»", 9.42, 10.05)],
 "Z04": [("Битта", 0, .36), ("ҳалқа", .36, .74), ("узилса —", .74, 1.16), ("занжир", 1.16, 1.86), ("ишламайди.", 1.86, 2.42),
         ("Ҳаммаси", 2.66, 3.38), ("бирга", 3.38, 3.68), ("бўлса —", 3.68, 4.06), ("бозор", 4.06, 4.76), ("сеники!", 4.76, 5.3)],
 "Z05": [("Ўша", 0, .28), ("донишманд", .28, .82), ("ҳалиям", .82, 1.3), ("ишлаяпти.", 1.3, 1.76), ("Фақат", 2.04, 2.56),
         ("энди", 2.56, 2.86), ("исми —", 2.86, 3.26), ("Озод", 3.26, 3.84), ("Жамол.", 3.84, 4.35)],
 "Z06": [("Бизнесингизга", 0, .78), ("тўлиқ", .78, 1.34), ("занжир", 1.34, 1.72), ("керакми?", 1.72, 2.22),
         ("Ёзинг:", 2.22, 3.02), ("@Ozodjamol", 3.02, 4.2)],
}
CHUNKS = {"Z01": [[0, 1], [2, 3], [4, 5, 6], [7, 8, 9], [10, 11]],
          "Z02": [[0, 1, 2, 3], [4], [5, 6], [7, 8], [9, 10], [11], [12, 13, 14], [15, 16, 17], [18, 19]],
          "Z03": [[0, 1, 2], [3, 4, 5], [6], [7], [8], [9], [10], [11], [12, 13, 14]],
          "Z04": [[0, 1, 2], [3, 4], [5, 6, 7], [8, 9]],
          "Z05": [[0, 1], [2, 3], [4, 5, 6], [7, 8]],
          "Z06": [[0, 1], [2, 3], [4, 5]]}
SUBS = []
for z, chs in CHUNKS.items():
    ws = WORDS[z]; t0 = V[z]
    for k, ch in enumerate(chs):
        s = t0 + ws[ch[0]][1]
        e = t0 + (ws[chs[k + 1][0]][1] if k + 1 < len(chs) else ws[ch[-1]][2] + .4)
        SUBS.append((s, e, [(ws[i][0], t0 + ws[i][1], t0 + ws[i][2]) for i in ch]))

def eob(x, s=1.7):
    x = min(max(x, 0), 1) - 1
    return x * x * ((s + 1) * x + s) + 1
def eo(x): x = min(max(x, 0), 1); return 1 - (1 - x) ** 3

class Clip:
    def __init__(self, path, ss=0.0, speed=1.0):
        vf = f"scale={W}:{H},setpts={1/speed}*PTS,fps={FPS}"
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", str(ss), "-i", path, "-vf", vf, "-f", "rawvideo",
                                   "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.last = None
    def next(self):
        b = self.p.stdout.read(W * H * 3)
        if len(b) == W * H * 3:
            self.last = Image.frombytes("RGB", (W, H), b)
        return self.last.copy()

def tw(dr, s, f): return dr.textlength(s, font=f)

# ---------- общие слои: виньетка, зерно, нижняя тень под титры ----------
yy, xx = np.mgrid[0:H, 0:W]
r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H * 0.45) / (H * 0.62)) ** 2)
VIG = Image.fromarray((np.clip((r - 0.55) / 0.7, 0, 1) ** 1.6 * 200).astype("uint8"), "L")
BOT = Image.fromarray((np.clip((yy - 1450) / 470, 0, 1) ** 1.3 * 215).astype("uint8"), "L")
BLACK = Image.new("RGB", (W, H), (8, 5, 3))
rng = np.random.default_rng(7)
GRAINS = [Image.fromarray(rng.normal(128, 18, (H // 2, W // 2)).clip(0, 255).astype("uint8"), "L").resize((W, H)) for _ in range(6)]

def finish(img, fi):
    img = Image.composite(BLACK, img, VIG)
    img = Image.composite(BLACK, img, BOT)
    g = GRAINS[fi % len(GRAINS)]
    return Image.blend(img, Image.merge("RGB", (g, g, g)), 0.045)

def draw_subs(img, t):
    for s, e, words in SUBS:
        if s <= t < e:
            dr = ImageDraw.Draw(img)
            size = 84
            f = F(size); line = " ".join(w for w, _, _ in words); L = tw(dr, line, f)
            if L > W - 110:
                size = int(size * (W - 110) / L); f = F(size); L = tw(dr, line, f)
            a = eo((t - s) / 0.2)
            y = 1712 + (1 - a) * 18
            sh = Image.new("RGBA", img.size, (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
            x = W / 2 - L / 2
            for w, ws, we in words:
                sd.text((x + 3, y + 4), w, font=f, fill=(0, 0, 0, int(220 * a)))
                x += tw(dr, w + " ", f)
            sh = sh.filter(ImageFilter.GaussianBlur(5))
            img.paste(sh, (0, 0), sh)
            ov = Image.new("RGBA", img.size, (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
            x = W / 2 - L / 2
            for w, ws, we in words:
                col = GOLD if ws <= t < we + 0.06 else CREAM
                od.text((x, y), w, font=f, fill=col + (int(255 * a),))
                x += tw(dr, w + " ", f)
            img.paste(ov, (0, 0), ov)
            return

def ornament_title(img, text, t, t0, t1, y=150, size=72, sub=None):
    if t < t0 or t > t1: return
    a = min(eo((t - t0) / 0.5), eo((t1 - t) / 0.4))
    top = Image.new("RGBA", (W, 420), (0, 0, 0, 0)); td = ImageDraw.Draw(top)
    for yy3 in range(420):
        td.line((0, yy3, W, yy3), fill=(10, 6, 3, int(170 * a * (1 - yy3 / 420) ** 1.2)))
    img.paste(top, (0, 0), top)
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    f = F(size, FSC); L = tw(od, text, f)
    od.text((W / 2 - L / 2 + 2, y + 3), text, font=f, fill=(0, 0, 0, int(180 * a)))
    od.text((W / 2 - L / 2, y), text, font=f, fill=GOLD + (int(255 * a),))
    ln = (L / 2 + 40) * eo((t - t0) / 0.8)
    cy = y + size + 18
    od.line((W / 2 - ln, cy, W / 2 - 18, cy), fill=GOLD + (int(220 * a),), width=3)
    od.line((W / 2 + 18, cy, W / 2 + ln, cy), fill=GOLD + (int(220 * a),), width=3)
    od.regular_polygon((W / 2, cy, 9), 4, rotation=45, fill=GOLD + (int(255 * a),))
    if sub:
        fs = F(40, FG6); Ls = tw(od, sub, fs)
        od.text((W / 2 - Ls / 2, cy + 22), sub, font=fs, fill=CREAM + (int(230 * a),))
    img.paste(ov, (0, 0), ov)

# ---------- цепь ремёсел ----------
grid = Image.open(SRC + "grid.jpg").convert("RGB")
BOX = [(116, 642, 132, 742), (116, 638, 804, 1391), (668, 1184, 148, 738), (668, 1185, 806, 1390),
       (1212, 1724, 157, 740), (1213, 1725, 806, 1390), (1752, 2263, 158, 739), (1756, 2265, 808, 1390)]
MW, MH = 262, 230
MED = []
for (y0, y1, x0, x1) in BOX:
    c = grid.crop((x0, y0, x1, y1)).resize((MW, MH), Image.LANCZOS).convert("RGBA")
    m = Image.new("L", (MW, MH), 0); ImageDraw.Draw(m).ellipse((3, 3, MW - 3, MH - 3), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(2)); c.putalpha(m); MED.append(c)
TRADES = ["МАСЛАҲАТЧИ", "ЖАРЧИ", "РАССОМ", "ШОИР", "МУСАВВИР", "НАҚҚОШ", "КОТИБ", "КАМОНЧИ"]
ROLES = ["стратегия", "SMM", "дизайн", "сценарий", "съёмка", "монтаж", "копирайтинг", "таргет"]
XL, XR = 290, 790
YS = [450, 785, 1120, 1455]
POS = [(XL, YS[0]), (XR, YS[0]), (XR, YS[1]), (XL, YS[1]), (XL, YS[2]), (XR, YS[2]), (XR, YS[3]), (XL, YS[3])]
ROLE_T = [V["Z03"] + WORDS["Z03"][i][1] for i in (6, 7, 8, 9, 10, 11, 12, 14)]
BRK = V["Z04"] + 0.9
BRK_I = 5
# фон — тёмный холст
bg = rng.normal(0, 1, (H // 8, W // 8))
bg = Image.fromarray(((bg - bg.min()) / (bg.max() - bg.min()) * 255).astype("uint8")).resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(14))
CANVAS = Image.merge("RGB", [bg.point(lambda v, k=k: int(k[0] + v / 255 * k[1])) for k in ((38, 30), (24, 22), (14, 16))])

def links(a, b):
    (x1, y1), (x2, y2) = a, b
    hor = abs(x2 - x1) > abs(y2 - y1)
    out = []
    if hor:
        gap = MW / 2 + 6; Ltot = abs(x2 - x1); n = max(2, int((Ltot - 2 * gap) / 34)); sgn = 1 if x2 > x1 else -1
        for k in range(n):
            out.append((x1 + sgn * (gap + 17 + k * (Ltot - 2 * gap) / n), y1, True, k % 2))
    else:
        top = y1 + MH / 2 + 88; bot = y2 - MH / 2 - 4; n = max(2, int((bot - top) / 34))
        for k in range(n):
            out.append((x1, top + 17 + k * (bot - top - 34) / max(1, n - 1), False, k % 2))
    return out

def link(dr, cx, cy, hor, kind, col, a=255):
    c = col + (a,)
    if kind == 0:
        w, h = (54, 30) if hor else (30, 54)
        dr.rounded_rectangle((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), 15, outline=c, width=9)
    else:
        w, h = (54, 11) if hor else (11, 54)
        dr.rounded_rectangle((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), 5, fill=c)

def chain_frame(t, scene):
    img = CANVAS.copy()
    brk = BRK if scene == "break" else 1e9
    shake = 16 * math.sin((t - brk) * 90) * (1 - (t - brk) / 0.35) if brk <= t < brk + 0.35 else 0
    grey = eo((t - brk - 0.15) / 0.6) if t >= brk else 0
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    for i in range(1, 8):
        prog = eo((t - ROLE_T[i]) / 0.35) if scene == "chain" else 1
        ls = links(POS[i - 1], POS[i]); nsh = int(len(ls) * prog + 0.999) if prog > 0 else 0
        for k, (cx, cy, hor, kind) in enumerate(ls[:nsh]):
            col = tuple(int(GOLD[j] * (1 - grey) + 110 * grey) for j in range(3))
            if i == BRK_I and t >= brk:
                dt = t - brk; side = -1 if k < len(ls) / 2 else 1
                cx += side * 120 * dt; cy += 900 * dt * dt - 150 * dt
                link(od, cx + shake, cy, hor, kind, GOLD, int(255 * max(0, 1 - dt / 1.2))); continue
            link(od, cx + shake, cy, hor, kind, col)
    img.paste(ov, (0, 0), ov)
    dr = ImageDraw.Draw(img)
    for i, (x, y) in enumerate(POS):
        ti = ROLE_T[i] if scene == "chain" else -10
        if t < ti: continue
        sc = eob((t - ti) / 0.35)
        w, h = max(2, int(MW * sc)), max(2, int(MH * sc))
        m = MED[i].resize((w, h), Image.LANCZOS)
        if grey > 0:
            a = m.getchannel("A"); m = ImageEnhance.Color(m.convert("RGB")).enhance(1 - 0.9 * grey).convert("RGBA"); m.putalpha(a)
        drop = 40 * grey if (scene == "break" and i >= BRK_I) else 0
        xx0, yy0 = int(x - w / 2 + shake), int(y - h / 2 + drop)
        sh = Image.new("RGBA", (w + 60, h + 60), (0, 0, 0, 0))
        ImageDraw.Draw(sh).ellipse((30, 40, 30 + w, 40 + h), fill=(0, 0, 0, 150)); sh = sh.filter(ImageFilter.GaussianBlur(14))
        img.paste(sh, (xx0 - 30, yy0 - 30), sh); img.paste(m, (xx0, yy0), m)
        if sc > 0.6:
            f1, f2 = F(40, FSC), F(30, FG6)
            col1 = tuple(int(GOLD[j] * (1 - grey) + 140 * grey) for j in range(3))
            L1 = tw(dr, TRADES[i], f1); L2 = tw(dr, ROLES[i], f2)
            by = yy0 + h + 2
            dr.text((x - L1 / 2 + shake + 2, by + 2), TRADES[i], font=f1, fill=(0, 0, 0))
            dr.text((x - L1 / 2 + shake, by), TRADES[i], font=f1, fill=col1)
            dr.text((x - L2 / 2 + shake, by + 44), ROLES[i], font=f2, fill=CREAM if grey < .5 else (150, 150, 150))
    ornament_title(img, "САВДО — ЗАНЖИР", t, V["Z03"] + 1.64 if scene == "chain" else -10, 99, y=110, size=82)
    if t >= brk:
        fl = max(0, 1 - (t - brk) / 0.25)
        if fl > 0:
            o = Image.new("RGBA", (W, H), (180, 30, 20, int(80 * fl))); img.paste(o, (0, 0), o)
    return img

# ---------- поворот и призыв ----------
def reveal_title(img, t):
    t0 = V["Z05"] + 3.26
    if t < t0: return
    a = eo((t - t0) / 0.6)
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    f = F(150, FSC); s = "OZOD JAMOL"; L = tw(od, s, f)
    y = 230 - (1 - a) * 30
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
    gd.text((W / 2 - L / 2, y), s, font=f, fill=(255, 200, 90, int(160 * a))); glow = glow.filter(ImageFilter.GaussianBlur(18))
    img.paste(glow, (0, 0), glow)
    od.text((W / 2 - L / 2 + 3, y + 4), s, font=f, fill=(0, 0, 0, int(200 * a)))
    od.text((W / 2 - L / 2, y), s, font=f, fill=GOLD + (int(255 * a),))
    fs = F(40, FG6); sub = "MEDIA • BUSINESS • CREATIVE"; Ls = tw(od, sub, fs)
    od.text((W / 2 - Ls / 2, y + 175), sub, font=fs, fill=CREAM + (int(230 * a),))
    img.paste(ov, (0, 0), ov)

paper_n = rng.normal(0, 1, (H // 6, W // 6))
PAPER_N = Image.fromarray(((paper_n - paper_n.min()) / np.ptp(paper_n) * 255).astype("uint8")).resize((W, H), Image.BICUBIC)

def cta_frame(t, base):
    img = base.filter(ImageFilter.GaussianBlur(10))
    img = ImageEnhance.Brightness(img).enhance(0.45)
    a = eob((t - SC[-1][1]) / 0.6)
    cw, ch = 880, 760
    card = Image.new("RGB", (cw, ch), (236, 220, 184))
    pn = PAPER_N.crop((0, 0, cw, ch))
    card = Image.blend(card, Image.merge("RGB", (pn, pn, pn)), 0.10)
    yy2, xx2 = np.mgrid[0:ch, 0:cw]
    e = np.minimum.reduce([xx2, yy2, cw - xx2, ch - yy2]).astype(float)
    burn = Image.fromarray((np.clip(1 - e / 90, 0, 1) ** 2 * 200).astype("uint8"), "L")
    card = Image.composite(Image.new("RGB", (cw, ch), (120, 72, 30)), card, burn)
    cd = ImageDraw.Draw(card)
    cd.rectangle((34, 34, cw - 34, ch - 34), outline=(150, 105, 45), width=3)
    f1 = F(76); l1 = "Бизнесингизга"; l2 = "тўлиқ занжир керакми?"
    for i, s in enumerate((l1, l2)):
        L = tw(cd, s, f1); cd.text((cw / 2 - L / 2, 110 + i * 92), s, font=f1, fill=INK)
    cd.line((cw / 2 - 160, 318, cw / 2 + 160, 318), fill=(150, 105, 45), width=3)
    f2 = F(64, FSC); s = "Ёзинг:"; L = tw(cd, s, f2); cd.text((cw / 2 - L / 2, 350), s, font=f2, fill=(110, 30, 20))
    f3 = F(92); s = "@Ozodjamol"; L = tw(cd, s, f3); cd.text((cw / 2 - L / 2 + 50, 470), s, font=f3, fill=INK)
    # сургучная печать с бумажным самолётиком (Telegram)
    ts = V["Z06"] + 2.22
    sa = eob((t - ts) / 0.4)
    if t >= ts:
        R = int(62 * max(sa, .01)); sx, sy = int(cw / 2 - L / 2 - 30), 528
        cd.ellipse((sx - R, sy - R, sx + R, sy + R), fill=(150, 22, 26))
        cd.ellipse((sx - R + 8, sy - R + 8, sx + R - 8, sy + R - 8), outline=(200, 60, 55), width=3)
        k = R / 62
        cd.polygon([(sx - 30 * k, sy + 2 * k), (sx + 30 * k, sy - 24 * k), (sx + 14 * k, sy + 28 * k), (sx + 2 * k, sy + 12 * k)], fill=(245, 225, 200))
    cs = max(0.01, a)
    card = card.resize((int(cw * cs), int(ch * cs)), Image.LANCZOS)
    sh = Image.new("RGBA", (card.width + 80, card.height + 80), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle((40, 55, 40 + card.width, 55 + card.height), fill=(0, 0, 0, 170)); sh = sh.filter(ImageFilter.GaussianBlur(20))
    x, y = W // 2 - card.width // 2, 760 - card.height // 2
    img.paste(sh, (x - 40, y - 40), sh); img.paste(card, (x, y))
    return img

# ---------- главный цикл ----------
clips = {"crowd": Clip(SRC + "v_crowd.mp4", 0, 6 / 8.1), "herald": Clip(SRC + "v_herald.mp4"),
         "cat": Clip(SRC + "v_cat.mp4", 1.5), "sage": Clip(SRC + "v_sage.mp4", 1.5),
         "crowd2": Clip(SRC + "v_crowd.mp4", 2.6), "reveal": Clip(SRC + "v_reveal.mp4", 0.6)}
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                        "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p",
                        "/home/claude/bar/body.mp4"], stdin=subprocess.PIPE)
N = int(round(TOTAL * FPS)); last_reveal = None
for fi in range(N):
    t = fi / FPS
    sc, s0, s1 = next((x for x in SC if x[1] <= t < x[2]), SC[-1])
    lt = t - s0
    if sc in clips:
        fr = clips[sc].next()
        if sc == "reveal": last_reveal = fr.copy(); reveal_title(fr, t)
    elif sc in ("chain", "break"):
        fr = chain_frame(t, sc)
    else:
        fr = cta_frame(t, last_reveal)
    if sc == "crowd":
        ornament_title(fr, "1725 · ВЕНЕЦИЯ", t, 0.15, 3.0, y=140, size=78, sub=None)
        if t >= V["Z01"] + 6.44:
            ornament_title(fr, "СИРИ НИМАДА?", t, V["Z01"] + 6.44, 8.1, y=140, size=78)
    if sc == "chain" and lt < 0.2:
        fr = Image.blend(Image.new("RGB", (W, H)), fr, eo(lt / 0.2))
    if fi > 0 and lt < 0.22 and sc not in ("break",):
        z = 1 + 0.05 * (1 - eo(lt / 0.22)); zw, zh = int(W * z), int(H * z)
        fr = fr.resize((zw, zh), Image.BILINEAR).crop(((zw - W) // 2, (zh - H) // 2, (zw - W) // 2 + W, (zh - H) // 2 + H))
    fr = finish(fr, fi).convert("RGBA")
    draw_subs(fr, t)
    enc.stdin.write(fr.convert("RGB").tobytes())
enc.stdin.close(); enc.wait()
json.dump({"V": V, "SC": SC, "ROLE_T": ROLE_T, "BRK": BRK, "SEAL": V["Z06"] + 2.22, "TOTAL": TOTAL},
          open("/home/claude/bar/timeline.json", "w"))
print("frames", N)
