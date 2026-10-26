"""OZOD JAMOL — реклама «инфографика на белом» (26.10.2026).
Белый фон + выноски «для чего» (техника мебели Shodiyona), фирменный красно-чёрный — только в финале (интро).
python3 ad_white.py 916|169  › кадры в ffmpeg (видео без звука) out_<fmt>_v.mp4
"""
import glob
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FMT = sys.argv[1] if len(sys.argv) > 1 else "916"
V = FMT == "916"
W, H = (1080, 1920) if V else (1920, 1080)
FPS = 30
T_WHITE = 21.0          # конец белой части
T_INTRO = 21.5          # начало интро
DUR = T_INTRO + 8.0
N = int(DUR * FPS)
FD = "/home/claude/fonts/Montserrat-{}.ttf"
INK, RED, GREY, WHITE = (17, 17, 17), (255, 16, 36), (118, 118, 122), (255, 255, 255)
_fc = {}


def F(w, s):
    k = (w, s)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(FD.format(w), s)
    return _fc[k]


def eo(x):
    x = np.clip(x, 0, 1)
    return 1 - (1 - x) ** 3


def eio(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def back(x):                      # выход с перелётом
    x = np.clip(x, 0, 1)
    c = 1.70158
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


# ---------- фон: чистый белый с мягким светом и точечной сеткой инфографики ----------
def make_bg():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = W / 2, H * (0.46 if V else 0.5)
    r = np.sqrt(((xx - cx) / W) ** 2 + ((yy - cy) / H) ** 2)
    v = 255 - 22 * np.clip(r / 0.75, 0, 1) ** 1.6
    img = np.stack([v, v, v - 1.5], -1)
    g = Image.fromarray(img.clip(0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(g)
    step = 54
    for x in range(step // 2, W, step):
        for y in range(step // 2, H, step):
            d.ellipse((x - 1.6, y - 1.6, x + 1.6, y + 1.6), fill=(212, 212, 214, 255))
    fade = Image.fromarray((255 * np.clip(1 - r / 0.55, 0, 1) ** 0.8).astype(np.uint8))   # сетка тает к краям
    clean = Image.fromarray(img.clip(0, 255).astype(np.uint8)).convert("RGBA")
    return Image.composite(clean, g, fade.point(lambda p: 255 - p)).convert("RGBA")


BG = make_bg()


def load_seq(d):
    return [Image.open(p).convert("RGB") for p in sorted(glob.glob(f"cl/{d}/*.jpg"))]


CL = {k: load_seq(k) for k in ("gwm", "d3", "gwr", "sho")}
LOGO = Image.open("cl/logo/end.jpg").convert("RGB")
INTRO = sorted(glob.glob(f"intro{FMT}/*.jpg"))


def cover(im, size):
    r = max(size[0] / im.width, size[1] / im.height)
    im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1), Image.BILINEAR)
    x, y = (im.width - size[0]) // 2, (im.height - size[1]) // 2
    return im.crop((x, y, x + size[0], y + size[1]))


def seq_at(name, u, speed=1.0):
    s = CL[name]
    return s[int(min(len(s) - 1, max(0, u * FPS * speed)))]


def rounded(img, r):
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, img.width - 1, img.height - 1), r, fill=255)
    o = img.convert("RGBA")
    o.putalpha(m)
    return o


def put(c, im, cx, cy, a=1.0, s=1.0):
    if a <= 0.01 or im is None:
        return
    if abs(s - 1.0) > 1e-3:
        im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BICUBIC)
    if a < 0.999:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    c.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


def shadow(w, h, r, blur, a=0.28):
    pad = blur * 3
    s = Image.new("L", (w + pad * 2, h + pad * 2), 0)
    ImageDraw.Draw(s).rounded_rectangle((pad, pad, pad + w, pad + h), r, fill=int(255 * a))
    s = s.filter(ImageFilter.GaussianBlur(blur))
    o = Image.new("RGBA", s.size, (0, 0, 0, 0))
    o.putalpha(s)
    return o


# ---------- текст ----------
def text_img(lines, w, size, cols=None, spacing=1.08, align="center", track=0):
    f = F(w, size)
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    ws = [d.textlength(l, font=f) + track * max(0, len(l) - 1) for l in lines]
    if max(ws) > W - 110:                       # не вылезать за край кадра
        size = int(size * (W - 110) / max(ws))
        f = F(w, size)
        ws = [d.textlength(l, font=f) + track * max(0, len(l) - 1) for l in lines]
    tw, th = int(max(ws)) + 20, int(size * spacing * len(lines) + size * 0.35)
    im = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    dd = ImageDraw.Draw(im)
    for i, l in enumerate(lines):
        x = 10 if align == "left" else (tw - ws[i]) / 2
        col = (cols[i] if cols else INK) + (255,)
        if track:
            for ch in l:
                dd.text((x, i * size * spacing), ch, font=f, fill=col)
                x += d.textlength(ch, font=f) + track
        else:
            dd.text((x, i * size * spacing), l, font=f, fill=col)
    return im


def reveal(im, p, direction="up"):
    """Маска-шторка: текст выезжает из-под линии."""
    if p <= 0:
        return None
    if p >= 1:
        return im
    o = Image.new("RGBA", im.size, (0, 0, 0, 0))
    if direction == "up":
        dy = int((1 - eo(p)) * im.height)
        o.alpha_composite(im.crop((0, 0, im.width, im.height - dy)), (0, dy))
    else:          # слева направо
        wv = int(eo(p) * im.width)
        if wv > 0:
            o.alpha_composite(im.crop((0, 0, wv, im.height)), (0, 0))
    return o


# ---------- телефон ----------
PW, PH, BZ = 520, 1080, 16
SW, SH = PW - 2 * BZ, PH - 2 * BZ
PH_SHADOW = shadow(PW, PH, 76, 38, 0.30)


def phone(screen):
    ph = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
    d = ImageDraw.Draw(ph)
    d.rounded_rectangle((0, 0, PW - 1, PH - 1), 76, fill=(22, 22, 24, 255))
    d.rounded_rectangle((3, 3, PW - 4, PH - 4), 73, outline=(70, 70, 76, 255), width=2)
    ph.alpha_composite(rounded(cover(screen, (SW, SH)), 60), (BZ, BZ))
    d.rounded_rectangle((PW // 2 - 62, BZ + 14, PW // 2 + 62, BZ + 46), 16, fill=(8, 8, 8, 255))
    return ph


def put_phone(c, screen, cx, cy, s=1.0, a=1.0):
    put(c, PH_SHADOW, cx + 10 * s, cy + 34 * s, a=a * 0.9, s=s)
    put(c, phone(screen), cx, cy, a=a, s=s)


# ---------- экраны услуг (рисуем сами: бот и воронка) ----------
def ui_font(w, s):
    return F(w, s)


def bot_screen(u):
    im = Image.new("RGB", (SW, SH), (238, 240, 243))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, SW, 150), fill=(255, 255, 255))
    d.ellipse((24, 70, 84, 130), fill=RED)
    d.text((40, 84), "S", font=ui_font(900, 30), fill=WHITE)
    d.text((100, 72), "Shodiyona Mebel", font=ui_font(800, 28), fill=INK)
    d.text((100, 106), "бот · онлайн", font=ui_font(500, 22), fill=(60, 140, 230))
    msgs = [(0.15, "bot", ["Ассалому алайкум!", "Сизга нима керак?"]),
            (0.75, "kb", ["Каталог", "Манзил", "Қўнғироқ", "Хонада кўриш"]),
            (1.15, "me", ["Каталог"]),
            (1.45, "bot", ["Диванлар · Ошхона", "Ётоқхона · Болалар"])]
    y = 180
    for t0, kind, lines in msgs:
        p = eo((u - t0) / 0.25)
        if p <= 0:
            break
        off = int((1 - p) * 30)
        if kind == "kb":
            for i, l in enumerate(lines):
                bx, by = 22 + (i % 2) * 232, y + (i // 2) * 74 + off
                d.rounded_rectangle((bx, by, bx + 222, by + 62), 16, fill=(255, 255, 255), outline=(220, 222, 226))
                tw = d.textlength(l, font=ui_font(700, 25))
                d.text((bx + 111 - tw / 2, by + 16), l, font=ui_font(700, 25), fill=RED)
            y += 160
            continue
        f = ui_font(700 if kind == "me" else 500, 30)
        tw = max(d.textlength(l, font=f) for l in lines)
        bh = 44 * len(lines) + 26
        if kind == "me":
            x1 = SW - 22
            d.rounded_rectangle((x1 - tw - 40, y + off, x1, y + bh + off), 22, fill=(220, 248, 198))
            for i, l in enumerate(lines):
                d.text((x1 - tw - 20, y + 12 + i * 44 + off), l, font=f, fill=INK)
        else:
            d.rounded_rectangle((22, y + off, 22 + tw + 40, y + bh + off), 22, fill=WHITE)
            for i, l in enumerate(lines):
                d.text((42, y + 12 + i * 44 + off), l, font=f, fill=INK)
        y += bh + 22
    return im


def funnel_screen(u):
    im = Image.new("RGB", (SW, SH), WHITE)
    d = ImageDraw.Draw(im)
    if u < 1.0:                                   # изоҳлар
        d.rectangle((0, 0, SW, 130), fill=WHITE)
        d.text((24, 74), "Изоҳлар", font=ui_font(800, 30), fill=INK)
        d.line((0, 130, SW, 130), fill=(232, 232, 232), width=2)
        rows = [(0.05, "aziza_07", "Нархи қанча?"), (0.30, "bek_andijon", "+"), (0.55, "paparazzi.uz", "Директга ёздик")]
        y = 160
        for t0, who, txt in rows:
            p = eo((u - t0) / 0.2)
            if p <= 0:
                break
            col = RED if who == "paparazzi.uz" else (200, 200, 205)
            d.ellipse((24, y, 84, y + 60), fill=col)
            d.text((100, y + 2), who, font=ui_font(800, 24), fill=INK)
            d.text((100, y + 34), txt, font=ui_font(500, 26), fill=(40, 40, 40))
            y += 104
    else:                                         # директ
        v = u - 1.0
        d.rectangle((0, 0, SW, 130), fill=WHITE)
        d.text((24, 74), "Директ", font=ui_font(800, 30), fill=INK)
        d.line((0, 130, SW, 130), fill=(232, 232, 232), width=2)
        p = eo(v / 0.25)
        if p > 0:
            off = int((1 - p) * 30)
            lines = ["Ассалому алайкум!", "Каналимизга марҳамат:"]
            d.rounded_rectangle((22, 170 + off, 440, 290 + off), 26, fill=(239, 239, 241))
            for i, l in enumerate(lines):
                d.text((44, 186 + i * 42 + off), l, font=ui_font(500, 26), fill=INK)
        p2 = eo((v - 0.35) / 0.25)
        if p2 > 0:
            off = int((1 - p2) * 30)
            d.rounded_rectangle((22, 310 + off, 440, 384 + off), 26, fill=RED)
            d.text((60, 330 + off), "Telegram каналга ›", font=ui_font(800, 26), fill=WHITE)
    return im


# ---------- выноски ----------
SERV = [("01", "МОУШН-ГРАФИК", "реклама роликлар"),
        ("02", "ИИ ВИДЕО", "3D ва аватар"),
        ("03", "TELEGRAM-БОТ", "24/7 ишлайди"),
        ("04", "INSTAGRAM ВОРОНКА", "изоҳ › директ"),
        ("05", "БРЕНДИНГ", "логотип ва стиль")]


def label_img(num, title, sub, align, size=40):
    words = title.split(" ") if len(title) > 11 else [title]
    if len(words) == 1 and "-" in title and len(title) > 11:
        a, b = title.split("-", 1)
        words = [a + "-", b]
    lines = words
    f9, f5, fn = F(900, size), F(500, int(size * 0.68)), F(900, int(size * 0.62))
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    tw = int(max([d.textlength(l, font=f9) for l in lines] + [d.textlength(sub, font=f5)])) + 16
    th = int(size * 1.05 * len(lines) + size * 0.62 * 1.6 + size * 0.9)
    im = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    dd = ImageDraw.Draw(im)

    def x_of(s, f):
        return 0 if align == "left" else tw - d.textlength(s, font=f)
    dd.text((x_of(num, fn), 0), num, font=fn, fill=RED + (255,))
    y = size * 0.82
    for l in lines:
        dd.text((x_of(l, f9), y), l, font=f9, fill=INK + (255,))
        y += size * 1.05
    dd.text((x_of(sub, f5), y + 4), sub, font=f5, fill=GREY + (255,))
    return im


def callouts_layout():
    """(якорь на телефоне относительно центра (доля), точка излома, край подписи, выравнивание)."""
    if V:
        # телефон по центру, подписи слева/справа и одна снизу
        return [((-0.5, -0.30), "L", 0.33), ((0.5, -0.12), "R", 0.43),
                ((-0.5, 0.06), "L", 0.58), ((0.5, 0.26), "R", 0.70), ((-0.5, 0.38), "L", 0.80)]
    return [((-0.5, -0.32), "L", 0.22), ((0.5, -0.20), "R", 0.30),
            ((-0.5, 0.02), "L", 0.50), ((0.5, 0.18), "R", 0.62), ((-0.5, 0.36), "L", 0.80)]


LAB = [label_img(n, t, s, "right" if side == "L" else "left", 42 if V else 48)
       for (n, t, s), (_, side, _) in zip(SERV, callouts_layout())]


def draw_callouts(c0, pcx, pcy, ps, u, alpha=1.0):
    c = Image.new("RGBA", c0.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    for i, ((ax, ay), side, ly) in enumerate(callouts_layout()):
        p = (u - i * 0.5) / 0.45
        if p <= 0:
            continue
        x0 = pcx + ax * PW * ps + (-6 if side == "L" else 6)
        y0 = pcy + ay * PH * ps
        y1 = H * ly
        mx = (W * (0.31 if V else 0.30)) if side == "L" else (W * (0.69 if V else 0.70))
        mx2 = (mx - 30) if side == "L" else (mx + 30)
        pts = [(x0, y0), ((x0 + mx) / 2, y1), (mx2, y1)]
        seg = eo(p)
        # точка
        r = 11 * eo(p / 0.4)
        d.ellipse((x0 - r - 5, y0 - r - 5, x0 + r + 5, y0 + r + 5), fill=WHITE + (255,))
        d.ellipse((x0 - r, y0 - r, x0 + r, y0 + r), fill=RED + (255,))
        # линия: сначала наклонная, потом горизонталь
        L1 = np.hypot(pts[1][0] - pts[0][0], pts[1][1] - pts[0][1])
        L2 = abs(pts[2][0] - pts[1][0])
        dist = seg * (L1 + L2)
        if dist <= L1:
            q = dist / max(L1, 1)
            e = (pts[0][0] + (pts[1][0] - pts[0][0]) * q, pts[0][1] + (pts[1][1] - pts[0][1]) * q)
            d.line([pts[0], e], fill=INK + (255,), width=3)
        else:
            q = (dist - L1) / max(L2, 1)
            e = (pts[1][0] + (pts[2][0] - pts[1][0]) * q, y1)
            d.line([pts[0], pts[1], e], fill=INK + (255,), width=3, joint="curve")
        lab = reveal(LAB[i], (u - i * 0.5 - 0.3) / 0.4, "up")
        avail = (mx2 - 14 - 28) if side == "L" else (W - 28 - mx2 - 14)
        if lab is not None and lab.width > avail:              # не вылезать за край
            k = avail / lab.width
            lab = lab.resize((int(lab.width * k), int(lab.height * k)), Image.BICUBIC)
        if lab is not None:
            if side == "L":
                c.alpha_composite(lab, (int(mx2 - 14 - lab.width), int(y1 - lab.height * 0.55)))
            else:
                c.alpha_composite(lab, (int(mx2 + 14), int(y1 - lab.height * 0.55)))
    if alpha < 0.999:
        c.putalpha(c.getchannel("A").point(lambda v: int(v * alpha)))
    c0.alpha_composite(c)


# ---------- сцены ----------
HOOK1 = text_img(["Реклама"], 900, 158 if V else 150)
HOOK2 = text_img(["ишламаяптими?"], 900, 112 if V else 132, cols=[RED])
CAP2 = text_img(["Биз бизнесни", "экранга олиб чиқамиз"] if V else ["Биз бизнесни экранга олиб чиқамиз"],
                800, 58 if V else 54)
BADGE = ["9:16 · 16:9", "3D · ИИ", "24/7", "изоҳ › директ › канал", "логотип · шрифт · ранг"]
S3_TITLES = [(text_img([n], 900, 150 if V else 140, cols=[RED]),
              text_img([t], 900, 78 if V else 84, align="left"),
              text_img([s], 500, 44 if V else 46, cols=[GREY], align="left")) for n, t, s in SERV]


def badge_img(txt):
    f = F(800, 40 if V else 42)
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    tw = d.textlength(txt, font=f)
    im = Image.new("RGBA", (int(tw) + 76, 86), (0, 0, 0, 0))
    dd = ImageDraw.Draw(im)
    dd.rounded_rectangle((0, 0, im.width - 1, 85), 43, fill=WHITE + (255,), outline=RED + (255,), width=4)
    dd.text((38, 18), txt, font=f, fill=INK + (255,))
    return im


BADGES = [badge_img(b) for b in BADGE]
BADGE_SH = [shadow(b.width, b.height, 43, 14, 0.18) for b in BADGES]
NAV1 = text_img(["Энди навбат —"], 900, 92 if V else 88)
NAV2 = text_img(["сиздa!".replace("a", "а")], 900, 120 if V else 110, cols=[RED])
ORDER = text_img(["Буюртма учун:"], 500, 50, cols=[WHITE])


def user_pill():
    f = F(900, 72)
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    tw = d.textlength("@Ozodjamol", font=f)
    im = Image.new("RGBA", (int(tw) + 170, 130), (0, 0, 0, 0))
    dd = ImageDraw.Draw(im)
    dd.rounded_rectangle((0, 0, im.width - 1, 129), 65, fill=RED + (255,))
    cx, cy = 64, 65
    dd.polygon([(cx - 30, cy - 2), (cx + 30, cy - 26), (cx + 18, cy + 28), (cx + 2, cy + 12), (cx - 8, cy + 24), (cx - 6, cy + 8)],
               fill=WHITE + (255,))
    dd.text((115, 20), "@Ozodjamol", font=f, fill=WHITE + (255,))
    return im


PILL = user_pill()


def card(img, w, label):
    h = int(img.height * w / img.width)
    pad = 60
    c = Image.new("RGBA", (w + pad * 2, h + pad * 2 + 110), (0, 0, 0, 0))
    c.alpha_composite(shadow(w, h, 34, 22, 0.25), (pad - 66 + 10, pad - 66 + 24))
    c.alpha_composite(rounded(img.resize((w, h), Image.BILINEAR), 34), (pad, pad))
    d = ImageDraw.Draw(c)
    f = F(900, 46)
    tw = d.textlength(label, font=f)
    x0 = pad + w / 2 - tw / 2
    d.rounded_rectangle((x0 - 28, pad + h + 26, x0 + tw + 28, pad + h + 100), 37, fill=RED + (255,))
    d.text((x0, pad + h + 38), label, font=f, fill=WHITE + (255,))
    return c


def screen_for(i, u):
    if i == 0:
        return seq_at("gwm", u * 1.2)
    if i == 1:
        return seq_at("d3", u, 0.65)
    if i == 2:
        return bot_screen(u)
    if i == 3:
        return funnel_screen(u)
    return LOGO.resize((int(LOGO.width * (1 + 0.04 * u)), int(LOGO.height * (1 + 0.04 * u))), Image.BILINEAR)


def frame(fi):
    t = fi / FPS
    if t >= T_INTRO:                                       # S6 — фирменное интро
        k = min(len(INTRO) - 1, int((t - T_INTRO) * FPS))
        c = Image.open(INTRO[k]).convert("RGBA")
        pu = eo((t - (T_INTRO + 4.6)) / 0.45)
        if pu > 0:
            if V:
                put(c, ORDER, W / 2, H * 0.80, a=pu)
                put(c, PILL, W / 2, H * 0.86, a=pu, s=0.9 + 0.1 * pu)
            else:
                put(c, ORDER, W / 2 - PILL.width * 0.55 - 40, H * 0.86, a=pu)
                put(c, PILL, W / 2 + 140, H * 0.86, a=pu, s=0.8 + 0.08 * pu)
        return c
    c = BG.copy()
    if t < 3.0:                                            # S1 — хук
        p1, p2 = (t - 0.15) / 0.45, (t - 0.45) / 0.45
        out = eio((t - 2.55) / 0.45)
        dy = -out * H * 0.25
        cy = H * (0.44 if V else 0.42) + dy
        a = 1 - out
        im1, im2 = reveal(HOOK1, p1), reveal(HOOK2, p2)
        if im1 is not None:
            put(c, im1, W / 2, cy - HOOK1.height * 0.55, a=a)
        if im2 is not None:
            put(c, im2, W / 2, cy + HOOK2.height * 0.55, a=a)
        bar = eo((t - 1.0) / 0.4) * HOOK2.width * 0.62
        if bar > 2:
            d = ImageDraw.Draw(c)
            yb = cy + HOOK2.height * 1.18
            d.rectangle((W / 2 - bar / 2, yb, W / 2 + bar / 2, yb + 12), fill=RED + (int(255 * a),))
        # фирменная диагональ в углу
        q = eo((t - 0.6) / 0.5) * a
        if q > 0:
            d = ImageDraw.Draw(c)
            L = 260 * q
            x0, y0 = W - 80, 140 if V else 110
            d.line((x0 - L * 0.7, y0 + L * 0.7, x0, y0), fill=RED + (255,), width=18)
    elif t < 8.0:                                          # S2 — телефон и выноски «для чего»
        u = t - 3.0
        rise = back(u / 0.6)
        ps = (0.54 if V else 0.70) * (1 + 0.025 * eio(u / 5))
        pcx, pcy = W / 2, H * (0.53 if V else 0.56) + (1 - rise) * H * 0.9
        put(c, CAP2, W / 2, H * (0.13 if V else 0.11), a=eo((u - 0.3) / 0.4) * (1 - eio((u - 4.6) / 0.4)))
        put_phone(c, seq_at("gwm", u), pcx, pcy, s=ps)
        if u > 0.9:
            draw_callouts(c, pcx, pcy, ps, u - 0.9, alpha=1 - eio((u - 4.6) / 0.4))
    elif t < 18.0:                                         # S3 — каждая услуга крупно
        u = t - 8.0
        i = min(4, int(u / 2.0))
        v = u - i * 2.0
        ps = 0.78 if V else 0.74
        pcx, pcy = (W / 2, H * 0.60) if V else (W * 0.66, H * 0.55)
        if i == 0:
            intro_p = eo(v / 0.5)
            ps = (0.555 + (ps - 0.555) * intro_p) if V else (0.70 + (ps - 0.70) * intro_p)
            pcx = W / 2 + (pcx - W / 2) * intro_p
            pcy = H * (0.53 if V else 0.56) + (pcy - H * (0.53 if V else 0.56)) * intro_p
        # смена экрана — сдвиг с пружиной
        sw = 1 - eo(v / 0.35)
        scr = screen_for(i, v)
        if sw > 0:
            prev = screen_for(i - 1, 2.0) if i > 0 else seq_at("gwm", 5.0)
            mix = Image.new("RGB", (SW, SH))
            off = int(sw * SW)
            mix.paste(cover(prev, (SW, SH)), (off - SW, 0))
            mix.paste(cover(scr, (SW, SH)), (off, 0))
            scr = mix
        bounce = 1 + 0.02 * np.sin(np.clip(v / 0.35, 0, 1) * np.pi)
        put_phone(c, scr, pcx, pcy, s=ps * bounce)
        num, tit, sub = S3_TITLES[i]
        tx = W * 0.08 if V else W * 0.07
        ty = H * 0.075 if V else H * 0.20
        pin = (v - 0.1) / 0.35
        pout = eio((v - 1.78) / 0.22) if i < 4 else 0
        for k, (im, dy) in enumerate(((num, 0), (tit, num.height * 0.92), (sub, num.height * 0.92 + tit.height * 1.0))):
            r = reveal(im, pin - k * 0.25, "up")
            if r is not None:
                c.alpha_composite(r, (int(tx), int(ty + dy - pout * 80)))
        # плашка-факт с выноской к телефону
        bp = back((v - 0.45) / 0.4) * (1 - pout)
        if bp > 0.01:
            b = BADGES[i]
            bx = (W * 0.08 + b.width / 2) if V else (W * 0.07 + b.width / 2)
            by = H * (0.30 if V else 0.66)
            d = ImageDraw.Draw(c)
            ex = pcx - PW * ps / 2 - 4
            ey = by + (H * 0.12 if V else 0)
            if (v - 0.6) > 0:
                q = eo((v - 0.6) / 0.3)
                sx = bx + b.width / 2 if not V else bx
                sy = by if not V else by + b.height / 2
                d.line([(sx, sy), (sx + (ex - sx) * q, sy + (ey - sy) * q)], fill=INK + (255,), width=3)
                if q > 0.95:
                    d.ellipse((ex - 9, ey - 9, ex + 9, ey + 9), fill=RED + (255,))
            put(c, BADGE_SH[i], bx + 4, by + 12, a=min(1, bp), s=bp)
            put(c, b, bx, by, a=min(1, bp), s=bp)
        if i == 4 and v > 1.55:                              # телефон уходит
            q = eio((v - 1.55) / 0.45)
            c2 = BG.copy()
            c = Image.blend(c, c2, q) if q < 1 else c2
    else:                                                  # S4 — доказательство + «Энди навбат — сизда!»
        u = t - 18.0
        w1 = 400 if V else 380
        g1 = card(seq_at("gwr", u, 0.3), w1, "GOLD WATER")
        g2 = card(seq_at("sho", u, 0.35), 560 if V else 600, "SHODIYONA MEBEL")
        p1, p2 = back((u - 0.05) / 0.45), back((u - 0.3) / 0.45)
        if V:
            put(c, g1, W * 0.5, H * 0.33 + (1 - min(1, p1)) * 140, a=min(1, eo(u / 0.3)), s=0.92 + 0.08 * min(1, p1))
            put(c, g2, W * 0.5, H * 0.645 + (1 - min(1, p2)) * 140, a=min(1, eo((u - 0.25) / 0.3)), s=0.92 + 0.08 * min(1, p2))
            ny = H * 0.82
        else:
            put(c, g1, W * 0.30, H * 0.47 + (1 - min(1, p1)) * 120, a=min(1, eo(u / 0.3)), s=0.92 + 0.08 * min(1, p1))
            put(c, g2, W * 0.70, H * 0.40 + (1 - min(1, p2)) * 120, a=min(1, eo((u - 0.25) / 0.3)), s=0.92 + 0.08 * min(1, p2))
            ny = H * 0.80
        r1, r2 = reveal(NAV1, (u - 0.8) / 0.4), reveal(NAV2, (u - 1.05) / 0.4)
        if V:
            if r1 is not None:
                put(c, r1, W / 2, ny)
            if r2 is not None:
                put(c, r2, W / 2, ny + NAV1.height * 1.05, s=1 + 0.06 * np.sin(np.clip((u - 1.05) / 0.5, 0, 1) * np.pi))
        else:
            if r1 is not None:
                put(c, r1, W * 0.70 - NAV2.width * 0.35, ny)
            if r2 is not None:
                put(c, r2, W * 0.70 + NAV1.width * 0.45, ny - 8)
        # S5 — переход: чёрная фирменная диагональ закрывает белое
        if t > T_WHITE - 0.05:
            q = eio((t - (T_WHITE - 0.05)) / (T_INTRO - T_WHITE + 0.05))
            band = Image.new("RGBA", (int(np.hypot(W, H)) * 2, int(np.hypot(W, H)) * 2), (0, 0, 0, 0))
            bd = ImageDraw.Draw(band)
            bw = band.width
            edge = bw * (1 - q) * 0.5
            bd.rectangle((0, edge, bw, bw), fill=(0, 0, 0, 255))
            bd.rectangle((0, edge - 26, bw, edge), fill=RED + (255,))
            band = band.rotate(-35, resample=Image.BILINEAR)
            c.alpha_composite(band, (int(W / 2 - bw / 2), int(H / 2 - bw / 2)))
    return c


if __name__ == "__main__":
    out = f"out_{FMT}_v.mp4"
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
                          "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    rng = np.random.default_rng(1)
    only = [float(x) for x in sys.argv[2:]]                  # проверочные кадры: python3 ad_white.py 916 1.0 5.2 …
    if only:
        for tt in only:
            frame(int(tt * FPS)).convert("RGB").save(f"peek/f_{FMT}_{tt:05.2f}.jpg", quality=88)
        p.stdin.close()
        p.wait()
        sys.exit(0)
    for fi in range(N):
        a = np.asarray(frame(fi).convert("RGB"), dtype=np.uint8)
        p.stdin.write(a.tobytes())
        if fi % 150 == 0:
            print(f"{FMT}: {fi}/{N}", flush=True)
    p.stdin.close()
    p.wait()
    print("ok", out)
