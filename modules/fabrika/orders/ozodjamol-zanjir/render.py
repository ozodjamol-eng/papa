import numpy as np, subprocess, math, json
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

W, H, FPS = 1080, 1920, 24
BG = (246, 234, 216)
DARK = (26, 26, 26)
RED = (255, 16, 36)
SRC = "/home/claude/zanjir/src/"
FB = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
FBL = "/usr/share/fonts/opentype/inter/Inter-Light.otf"
F = lambda s, p=FB: ImageFont.truetype(p, s)

# ---------- timeline ----------
V = {  # voice part: start time (BAS single take cut at pauses, offset 0.2)
    "Z01": 0.2, "Z02": 3.95, "Z03": 7.60, "Z04": 18.05, "Z05": 21.70, "Z06": 28.15}
SC = [  # scene, start, end
    ("s1", 0.0, 3.95), ("s2", 3.95, 7.6), ("s3", 7.6, 18.05), ("s4", 18.05, 21.7),
    ("s5", 21.7, 28.15), ("s6", 28.15, 33.6)]
TOTAL = 33.6

# words: (text, start, end) relative to voice part
WORDS = {
 "Z01": [("Реклама", 0, .52), ("қилдингиз —", .52, 1.28), ("натижа", 1.28, 2.1), ("йўқ.", 2.1, 2.5), ("Нега?", 2.96, 3.5)],
 "Z02": [("Чунки", .23, .55), ("рекламадан", .55, 1.19), ("битта", 1.19, 1.45), ("одам", 1.45, 1.95), ("жавоб", 1.95, 2.35),
         ("бериши", 2.35, 2.69), ("мумкин", 2.69, 3.1), ("эмас.", 3.1, 3.55)],
 "Z03": [("Аслида", .12, .58), ("реклама —", .58, 1.2), ("бу", 1.2, 1.64), ("занжир:", 1.64, 2.36), ("стратегия,", 2.76, 3.66),
         ("саҳифа,", 3.84, 4.32), ("дизайн,", 4.86, 5.34), ("сценарий,", 5.66, 6.28), ("съёмка,", 6.6, 7.26),
         ("монтаж,", 7.52, 8.1), ("копирайтинг", 8.32, 9.06), ("ва", 9.06, 9.5), ("таргет.", 9.5, 9.95)],
 "Z04": [("Битта", .13, .67), ("ҳалқа", .67, 1.05), ("узилса —", 1.05, 1.59), ("бутун", 1.59, 2.23), ("занжир", 2.23, 2.77),
         ("ишламайди.", 2.77, 3.5)],
 "Z05": [("Озод", .16, .54), ("Жамол", .54, 1.04), ("бу", 1.04, 1.34), ("занжирни", 1.34, 2.06), ("бир", 2.06, 2.32),
         ("жойда", 2.32, 2.76), ("бирлаштиради:", 2.76, 3.56), ("тажриба", 3.78, 4.42), ("ва", 4.42, 4.7),
         ("сунъий", 4.7, 5.42), ("интеллект.", 5.42, 6.0)],
 "Z06": [("Бизнесингизга", .33, 1.23), ("тўлиқ", 1.23, 1.63), ("занжир", 1.63, 2.11), ("керакми?", 2.11, 2.69),
         ("Ёзинг:", 2.93, 3.55), ("@Ozodjamol", 3.55, 4.85)],
}
# chunks (indices of words per chunk)
CHUNKS = {"Z01": [[0, 1], [2, 3], [4]], "Z02": [[0, 1], [2, 3, 4], [5, 6, 7]],
          "Z03": [[0, 1], [2, 3], [4], [5], [6], [7], [8], [9], [10, 11, 12]],
          "Z04": [[0, 1, 2], [3, 4], [5]], "Z05": [[0, 1], [2, 3], [4, 5, 6], [7, 8], [9, 10]],
          "Z06": [[0], [1, 2, 3], [4, 5]]}
SUBS = []  # (abs_start, abs_end, [(word, ws, we)])
for z, chs in CHUNKS.items():
    ws = WORDS[z]; t0 = V[z]
    for k, ch in enumerate(chs):
        s = t0 + ws[ch[0]][1]
        e = t0 + (WORDS[z][CHUNKS[z][k + 1][0]][1] if k + 1 < len(chs) else ws[ch[-1]][2] + .35)
        SUBS.append((s, e, [(ws[i][0], t0 + ws[i][1], t0 + ws[i][2]) for i in ch]))

# ---------- helpers ----------
def ease_out_back(x, s=1.7):
    x = min(max(x, 0), 1); x -= 1
    return x * x * ((s + 1) * x + s) + 1
def ease_out(x): x = min(max(x, 0), 1); return 1 - (1 - x) ** 3
def ease_in_out(x): x = min(max(x, 0), 1); return 3 * x * x - 2 * x * x * x

class Clip:
    def __init__(self, path):
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", f"scale={W}:{H}", "-f", "rawvideo",
                                   "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.last = None
    def next(self):
        b = self.p.stdout.read(W * H * 3)
        if len(b) == W * H * 3:
            self.last = Image.frombytes("RGB", (W, H), b)
        return self.last.copy()

def shadow_circle(d, blur=18, off=10, alpha=70):
    s = Image.new("RGBA", (d + 80, d + 80), (0, 0, 0, 0))
    ImageDraw.Draw(s).ellipse((40, 40 + off, 40 + d, 40 + d + off), fill=(80, 50, 20, alpha))
    return s.filter(ImageFilter.GaussianBlur(blur))

def text_w(dr, s, f): return dr.textlength(s, font=f)

def draw_subs(img, t):
    for s, e, words in SUBS:
        if s <= t < e:
            dr = ImageDraw.Draw(img)
            f = F(74)
            line = " ".join(w for w, _, _ in words)
            tw = text_w(dr, line, f)
            if tw > W - 120:
                f = F(int(74 * (W - 120) / tw)); tw = text_w(dr, line, f)
            pop = ease_out_back((t - s) / 0.18)
            y = 1745
            # backdrop pill
            pad = 34
            ov = Image.new("RGBA", img.size, (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
            od.rounded_rectangle((W / 2 - tw / 2 - pad, y - 22, W / 2 + tw / 2 + pad, y + 100), 40, fill=(255, 255, 255, int(215 * min(1, pop))))
            img.alpha_composite(ov) if img.mode == "RGBA" else img.paste(ov, (0, 0), ov)
            dr = ImageDraw.Draw(img)
            x = W / 2 - tw / 2
            dy = (1 - min(1, pop)) * 25
            for w, ws, we in words:
                col = RED if ws <= t < we + 0.05 else DARK
                dr.text((x, y + dy), w, font=f, fill=col)
                x += text_w(dr, w + " ", f)
            return

def title(img, lines, t0, t, y=150, size=84):
    if t < t0: return
    dr = ImageDraw.Draw(img)
    for i, (s, col) in enumerate(lines):
        a = ease_out((t - t0 - i * 0.12) / 0.3)
        if a <= 0: continue
        f = F(size); tw = text_w(dr, s, f)
        ov = Image.new("RGBA", img.size, (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
        od.text((W / 2 - tw / 2, y + i * (size + 14) + (1 - a) * 40), s, font=f, fill=col + (int(255 * a),))
        img.paste(ov, (0, 0), ov)

# ---------- chain scene ----------
AV = [Image.open(f"{SRC}av/a{i}.png").convert("RGBA") for i in range(1, 9)]
ROLES = ["СТРАТЕГИЯ", "САҲИФА", "ДИЗАЙН", "СЦЕНАРИЙ", "СЪЁМКА", "МОНТАЖ", "КОПИРАЙТИНГ", "ТАРГЕТ"]
XL, XR = 300, 780
YS = [470, 815, 1160, 1505]
POS = [(XL, YS[0]), (XR, YS[0]), (XR, YS[1]), (XL, YS[1]), (XL, YS[2]), (XR, YS[2]), (XR, YS[3]), (XL, YS[3])]
D = 230
role_t = [V["Z03"] + WORDS["Z03"][i][1] for i in range(4, 12)] + [V["Z03"] + WORDS["Z03"][12][1]]
role_t = role_t[:7] + [V["Z03"] + WORDS["Z03"][12][1]]
GREY = None
BRK_I = 5

def chain_links(a, b):
    """return list of (cx, cy, horizontal, kind) along a→b"""
    (x1, y1), (x2, y2) = a, b
    hor = abs(x2 - x1) > abs(y2 - y1)
    L = math.hypot(x2 - x1, y2 - y1) - D  # gap between circle edges
    n = max(2, int(L / 34))
    out = []
    for k in range(n):
        f = (D / 2 + 17 + k * (L - 0) / n) / math.hypot(x2 - x1, y2 - y1)
        out.append((x1 + (x2 - x1) * f, y1 + (y2 - y1) * f, hor, k % 2))
    return out

def draw_link(dr, cx, cy, hor, kind, col, a=255):
    c = col + (a,)
    if kind == 0:
        w, h = (54, 30) if hor else (30, 54)
        dr.rounded_rectangle((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), 15, outline=c, width=10)
    else:
        w, h = (54, 12) if hor else (12, 54)
        dr.rounded_rectangle((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), 6, fill=c)

def chain_frame(t, scene):
    img = Image.new("RGB", (W, H), BG)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    brk = V["Z04"] + 1.2 if scene == "s4" else 1e9
    shake = 0
    if t >= brk and t < brk + 0.35:
        shake = 18 * math.sin((t - brk) * 90) * (1 - (t - brk) / 0.35)
    grey = ease_out((t - brk - 0.15) / 0.6) if t >= brk else 0
    # links
    for i in range(1, 8):
        ti = role_t[i] if scene == "s3" else 0
        prog = ease_out((t - ti) / 0.35) if scene == "s3" else 1
        links = chain_links(POS[i - 1], POS[i])
        nshow = int(len(links) * prog + 0.999) if prog > 0 else 0
        for k, (cx, cy, hor, kind) in enumerate(links[:nshow]):
            col = tuple(int(RED[j] * (1 - grey) + 150 * grey) for j in range(3))
            if i == BRK_I and t >= brk:  # broken link: pieces fall
                dt = t - brk
                side = -1 if k < len(links) / 2 else 1
                cx += side * 120 * dt + (k - len(links) / 2) * 6 * dt
                cy += 900 * dt * dt + (-150 * dt)
                a = int(255 * max(0, 1 - dt / 1.2))
                draw_link(od, cx + shake, cy, hor, kind, (RED[0], RED[1], RED[2]), a)
                continue
            draw_link(od, cx + shake, cy, hor, kind, col)
    img.paste(ov, (0, 0), ov)
    # nodes
    for i, (x, y) in enumerate(POS):
        ti = role_t[i] if scene == "s3" else -10
        if t < ti: continue
        sc = ease_out_back((t - ti) / 0.3)
        d = max(2, int(D * sc))
        av = AV[i].resize((d, d), Image.LANCZOS)
        if grey > 0:
            g = ImageEnhance.Color(av).enhance(1 - 0.9 * grey)
            g = ImageEnhance.Brightness(g).enhance(1 - 0.15 * grey)
            av = g
        sh = shadow_circle(d)
        xx = int(x - d / 2 + shake); yy = int(y - d / 2 + (40 * grey if i >= BRK_I else 0) * (1 if scene == "s4" else 0))
        img.paste(sh, (xx - 40, yy - 40), sh)
        ring = Image.new("RGBA", (d + 20, d + 20), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse((0, 0, d + 19, d + 19), fill=(255, 255, 255, 255))
        img.paste(ring, (xx - 10, yy - 10), ring)
        img.paste(av, (xx, yy), av)
        # label pill
        if sc > 0.6:
            dr = ImageDraw.Draw(img)
            f = F(34); s = ROLES[i]; tw = text_w(dr, s, f)
            pc = tuple(int(DARK[j] * (1 - grey) + 120 * grey) for j in range(3))
            by = yy + d - 18
            dr.rounded_rectangle((x - tw / 2 - 22 + shake, by, x + tw / 2 + 22 + shake, by + 54), 27, fill=pc)
            dr.text((x - tw / 2 + shake, by + 7), s, font=f, fill=(255, 255, 255))
    # title
    tt = V["Z03"] + 0.5 if scene == "s3" else -10
    title(img, [("РЕКЛАМА =", DARK), ("ЗАНЖИР", RED if grey < .5 else (150, 150, 150))], tt, t, y=120, size=92)
    if t >= brk:  # flash
        fl = max(0, 1 - (t - brk) / 0.25)
        if fl > 0:
            ov = Image.new("RGBA", (W, H), (255, 16, 36, int(90 * fl))); img.paste(ov, (0, 0), ov)
    return img

# ---------- overlays ----------
def brand_pill(img, t, t0):
    a = ease_out_back((t - t0) / 0.35)
    if t < t0: return
    dr = ImageDraw.Draw(img)
    f1, f2 = F(76), F(76, FBL)
    w1 = text_w(dr, "OZOD ", f1); w2 = text_w(dr, "JAMOL", f2)
    tw = w1 + w2; x0 = W / 2 - tw / 2; y0 = 120 - (1 - min(a, 1)) * 200
    dr.rounded_rectangle((x0 - 46, y0 - 18, x0 + tw + 46, y0 + 104), 50, fill=(0, 0, 0))
    dr.rectangle((x0 - 46 + 50, y0 + 98, x0 + tw + 46 - 50, y0 + 104), fill=RED)
    dr.text((x0, y0), "OZOD ", font=f1, fill=(255, 255, 255))
    dr.text((x0 + w1, y0), "JAMOL", font=f2, fill=(255, 255, 255))

def chip(img, s, cx, cy, t, t0, fill=(255, 255, 255), col=DARK, border=RED):
    if t < t0: return
    a = ease_out_back((t - t0) / 0.3)
    dr = ImageDraw.Draw(img); f = F(int(48 * min(1.05, max(a, .01))))
    tw = text_w(dr, s, f)
    dr.rounded_rectangle((cx - tw / 2 - 30, cy - 38, cx + tw / 2 + 30, cy + 38), 38, fill=fill, outline=border, width=5)
    dr.text((cx - tw / 2, cy - 30), s, font=f, fill=col)

def tg_card(img, t, t0):
    if t < t0: return
    a = ease_out_back((t - t0) / 0.4)
    card = Image.new("RGBA", (780, 170), (0, 0, 0, 0)); cd = ImageDraw.Draw(card)
    cd.rounded_rectangle((0, 0, 779, 169), 85, fill=(255, 255, 255, 255))
    cd.ellipse((22, 22, 148, 148), fill=(42, 171, 238, 255))
    # paper plane
    cd.polygon([(52, 86), (122, 54), (104, 120), (86, 98)], fill=(255, 255, 255, 255))
    cd.polygon([(86, 98), (122, 54), (78, 92)], fill=(200, 230, 250, 255))
    f = F(70); cd.text((178, 40), "@Ozodjamol", font=f, fill=DARK + (255,))
    s = max(0.01, a)
    cw, ch = int(780 * s), int(170 * s)
    card = card.resize((cw, ch), Image.LANCZOS)
    sh = Image.new("RGBA", (cw + 80, ch + 80), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((40, 52, 40 + cw, 52 + ch), int(85 * s), fill=(60, 40, 20, 80))
    sh = sh.filter(ImageFilter.GaussianBlur(16))
    x, y = int(W / 2 - cw / 2), int(1430 - ch / 2)
    img.paste(sh, (x - 40, y - 40), sh); img.paste(card, (x, y), card)

# ---------- main ----------
clips = {"s1": Clip(SRC + "v_confused.mp4"), "s2": Clip(SRC + "v_juggle.mp4"),
         "s5": Clip(SRC + "v_team_slow.mp4"), "s6": Clip(SRC + "v_happy.mp4")}
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                        "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p",
                        "/home/claude/zanjir/body.mp4"], stdin=subprocess.PIPE)
N = int(round(TOTAL * FPS))
for fi in range(N):
    t = fi / FPS
    sc, s0, s1 = next(x for x in SC if x[1] <= t < x[2]) if t < TOTAL else SC[-1]
    lt = t - s0
    if sc in clips:
        fr = clips[sc].next()
        if sc == "s1":
            base = Image.new("RGB", (W, H), BG)
            sm = fr.resize((int(W * .88), int(H * .88)), Image.LANCZOS)
            base.paste(sm, (int(W * .06), 190)); fr = base
            title(fr, [("РЕКЛАМА НАТИЖА", DARK), ("БЕРМАЯПТИМИ?", RED)], 0.0, t + 1, y=110, size=80)
        if sc == "s5":
            brand_pill(fr, t, V["Z05"])
            dr = ImageDraw.Draw(fr); f48 = F(48)
            w1 = text_w(dr, "ТАЖРИБА", f48) + 60; w2 = text_w(dr, "СУНЪИЙ ИНТЕЛЛЕКТ", f48) + 60
            x0 = W / 2 - (w1 + w2 + 70) / 2
            chip(fr, "ТАЖРИБА", x0 + w1 / 2, 330, t, V["Z05"] + 3.78)
            if t >= V["Z05"] + 4.42: dr.text((x0 + w1 + 16, 288), "+", font=F(70), fill=RED)
            chip(fr, "СУНЪИЙ ИНТЕЛЛЕКТ", x0 + w1 + 70 + w2 / 2, 330, t, V["Z05"] + 4.7, fill=DARK, col=(255, 255, 255))
        if sc == "s6":
            tg_card(fr, t, V["Z06"] + 2.93)
    else:
        fr = chain_frame(t, sc)
    # scene punch-in
    if fi > 0 and lt < 0.25:
        z = 1 + 0.06 * (1 - ease_out(lt / 0.25))
        zw, zh = int(W * z), int(H * z)
        fr = fr.resize((zw, zh), Image.BILINEAR).crop(((zw - W) // 2, (zh - H) // 2, (zw - W) // 2 + W, (zh - H) // 2 + H))
    fr = fr.convert("RGBA")
    draw_subs(fr, t)
    enc.stdin.write(fr.convert("RGB").tobytes())
enc.stdin.close(); enc.wait()
json.dump({"V": V, "SC": SC, "role_t": role_t, "brk": V["Z04"] + 1.2, "tg": V["Z06"] + 2.93, "TOTAL": TOTAL},
          open("/home/claude/zanjir/timeline.json", "w"))
print("frames", N)
