# «Живой постер» Safo Marva — Хўжаобод филиали (02.11.2026, черновик для показа владельцу).
# Фирменный стиль Safo Marva: красный + белый, бордовый + золото, арка с полумесяцем, пальмами и холмами (Сафо и Марва), засечный шрифт.
# Эмблема перерисована по фото вывески — ЗАГЛУШКА до оригинального файла логотипа от клиента.
# Без ИИ-картинок святынь; без музыки (умра-аудитория) — только концовка OZOD JAMOL со своим звуком.
# Запуск: python3 poster_xojaobod.py <out.mp4> [телефон]
import sys, math, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
OUT = sys.argv[1]; PHONE = sys.argv[2] if len(sys.argv) > 2 else "+998 90 766 82 84"
W, H, FPS, DUR = 1080, 1920, 30, 12.8
F = "/home/claude/fonts/"
def font(n, s): return ImageFont.truetype(F + n, s)
MB, CZ = "Montserrat800.ttf", "Cinzel800.ttf"
RED, WHITE, GOLD, GOLD2 = (227, 16, 30), (255, 255, 255), (214, 170, 92), (246, 214, 150)

def ease(x): x = min(1, max(0, x)); return 1 - (1 - x) ** 3
def win(t, a, b, fi=0.45, fo=0.4):
    if t < a or t > b: return 0.0
    return min(ease((t - a) / fi), ease((b - t) / fo) if b - t < fo else 1)

# ---------- фон: бордовый градиент + золотой узор (8-конечные звёзды) ----------
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
g = np.clip(1 - np.hypot((xx - W / 2) / W, (yy - H * 0.38) / H) * 1.25, 0, 1)[..., None]
BG = (np.array([46, 5, 10]) * (1 - g) + np.array([118, 14, 26]) * g).astype(np.float32)
pat = Image.new("L", (W + 240, H + 240), 0); pd = ImageDraw.Draw(pat)
for cy in range(0, H + 240, 120):
    for cx in range(0, W + 240, 120):
        for k in range(2):
            pts = [(cx + 34 * math.cos(math.radians(45 * i + 22.5 * k)), cy + 34 * math.sin(math.radians(45 * i + 22.5 * k))) for i in range(0, 8, 2)]
            pd.polygon(pts, outline=255)
PAT = np.asarray(pat).astype(np.float32) / 255

# ---------- эмблема (арка) ----------
def emblem(sz=520):
    S = sz * 2; im = Image.new("RGBA", (S, int(S * 1.18)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    w, h = S, int(S * 1.18); lw = int(S * 0.035)
    arch = [(lw, w // 2), (w - lw, h - lw)]
    d.rounded_rectangle([lw, w // 2, w - lw, h - lw], radius=int(S * 0.04), fill=(120, 14, 24, 255))
    d.pieslice([lw, lw, w - lw, w - lw], 180, 360, fill=(120, 14, 24, 255))
    d.rectangle([lw, w // 2, w - lw, w // 2 + lw], fill=(120, 14, 24, 255))
    # контур
    d.arc([lw, lw, w - lw, w - lw], 180, 360, fill=GOLD + (255,), width=lw)
    d.line([(lw + lw // 2, w // 2), (lw + lw // 2, h - lw)], fill=GOLD + (255,), width=lw)
    d.line([(w - lw - lw // 2, w // 2), (w - lw - lw // 2, h - lw)], fill=GOLD + (255,), width=lw)
    d.line([(lw, h - lw - lw // 2), (w - lw, h - lw - lw // 2)], fill=GOLD + (255,), width=lw)
    c = GOLD2 + (255,)
    # полумесяц
    cx, cy, r = int(w * 0.27), int(h * 0.27), int(S * 0.07)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c); d.ellipse([cx - r + r // 2, cy - r - r // 5, cx + r + r // 2, cy + r - r // 5], fill=(120, 14, 24, 255))
    # холмы
    base = int(h * 0.86)
    d.polygon([(int(w * .12), base), (int(w * .40), int(h * .58)), (int(w * .58), base)], fill=c)
    d.polygon([(int(w * .42), base), (int(w * .70), int(h * .64)), (int(w * .90), base)], fill=c)
    d.rectangle([int(w * .1), base, int(w * .9), base + lw], fill=c)
    # пальмы
    def palm(x, y, hgt, sc):
        top = (x + hgt * 0.10, y - hgt)
        # ствол — сужающийся, слегка изогнутый
        pts_l, pts_r = [], []
        for i in range(21):
            u = i / 20; px = x + (top[0] - x) * u + math.sin(u * math.pi) * hgt * 0.04; py = y + (top[1] - y) * u
            wdt = sc * (0.075 - 0.04 * u); pts_l.append((px - wdt, py)); pts_r.append((px + wdt, py))
        d.polygon(pts_l + pts_r[::-1], fill=c)
        # листья — изогнутые сужающиеся «перья»
        for a, L in ((-170, .95), (-140, 1.0), (-110, .8), (-75, .8), (-40, 1.0), (-10, .95), (150, .7), (30, .7)):
            L *= sc; ra = math.radians(a); up, dn = [], []
            for i in range(25):
                u = i / 24; dx = math.cos(ra) * L * u; dy = math.sin(ra) * L * u + (L * 0.55) * u * u   # провисание
                nx, ny = -math.sin(ra), math.cos(ra); wdt = sc * 0.11 * math.sin(math.pi * min(1, u * 1.15)) + 1
                up.append((top[0] + dx + nx * wdt, top[1] + dy + ny * wdt)); dn.append((top[0] + dx - nx * wdt, top[1] + dy - ny * wdt))
            d.polygon(up + dn[::-1], fill=c)
    palm(int(w * .55), int(h * .68), int(h * .40), S * 0.20)
    palm(int(w * .30), int(h * .74), int(h * .25), S * 0.13)
    return im.resize((sz, int(sz * 1.18)), Image.LANCZOS)
EMB = emblem(430)

def text_img(txt, fnt, fill, track=0, stroke=0):
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    wds = [d.textlength(ch, font=fnt) for ch in txt]; tw = int(sum(wds) + track * (len(txt) - 1)) + 20
    a, b = fnt.getmetrics(); im = Image.new("RGBA", (tw, a + b + 20), (0, 0, 0, 0)); dd = ImageDraw.Draw(im); x = 10
    for ch, wd in zip(txt, wds):
        dd.text((x, 10), ch, font=fnt, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0, 120)); x += wd + track
    return im
def fit(txt, name, size, maxw, fill, track=0):
    while True:
        im = text_img(txt, font(name, size), fill, track)
        if im.width <= maxw or size < 20: return im
        size -= 2
def shadow(im, r=14, op=0.65):
    a = im.split()[3].filter(ImageFilter.GaussianBlur(r)).point(lambda v: int(v * op))
    s = Image.new("RGBA", im.size, (0, 0, 0, 0)); s.putalpha(a); return s

WORD = fit("SAFO MARVA", CZ, 140, 960, WHITE, track=6)
SUB1 = fit("УМРА ЗИЁРАТИ", MB, 46, 900, GOLD2, track=14)
BIG1 = fit("ЭНДИ ХЎЖАОБОДДА!", MB, 92, 960, WHITE)
SUB2 = fit("Янги филиал эшикларини очди", MB, 62, 960, WHITE)
N14 = fit("14", MB, 230, 600, GOLD2)
T14a = fit("Ўзбекистонда расмий умра", MB, 58, 960, WHITE)
T14b = fit("лицензиясига эга компаниядан бири", MB, 58, 960, WHITE)
T30a = fit("га яқин зиёратчи ишонч билдирган", MB, 58, 960, WHITE)
RAM = fit("РАМАЗОН — 2027", MB, 104, 980, GOLD2)
RAMb = fit("Жойлар банд қилинмоқда", MB, 66, 960, WHITE)
PH = fit(PHONE, MB, 70, 820, RED)
SLOG = fit("Umra safari — Safo Marva bilan birga!", CZ, 48, 1000, WHITE, track=1)

def paste(fr, im, cx, cy, alpha=1.0, scale=1.0, sh=True):
    if alpha <= 0.01: return
    if scale != 1.0: im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    x, y = int(cx - im.width / 2), int(cy - im.height / 2)
    if alpha < 1: a = im.split()[3].point(lambda v: int(v * alpha)); im = im.copy(); im.putalpha(a)
    if sh: fr.alpha_composite(shadow(im), (x, y + 6))
    fr.alpha_composite(im, (x, y))

def frame(t):
    off = (t * 9) % 120
    p = PAT[int(off):int(off) + H, int(off):int(off) + W][..., None]
    base = BG + p * np.array(GOLD) * 0.07
    fr = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
    # 1) эмблема + слово
    a1 = win(t, 0.0, 3.4, 0.9, 0.4)
    emb_y = 760 - 330 * ease((t - 3.0) / 0.6) if t > 3.0 else 760
    emb_s = 1.0 - 0.45 * ease((t - 3.0) / 0.6) if t > 3.0 else 0.92 + 0.08 * ease(t / 1.2)
    a_e = min(1, ease(t / 0.9)) * (1 - ease((t - 9.3) / 0.4) if t > 9.3 else 1)
    paste(fr, EMB, W / 2, emb_y, a_e, emb_s)
    if t < 3.4:
        paste(fr, WORD, W / 2, 1160 + 30 * (1 - ease((t - 0.7) / 0.8)), win(t, 0.7, 3.4, 0.8))
        paste(fr, SUB1, W / 2, 1290, win(t, 1.5, 3.4, 0.6))
    # 2) «Энди Хўжаободда»
    a2 = win(t, 3.4, 6.6)
    if a2 > 0:
        bx = int(-W + W * ease((t - 3.4) / 0.5)); d = ImageDraw.Draw(fr)
        d.rectangle([bx, 860, bx + W, 1040], fill=RED + (int(255 * a2),))
        paste(fr, BIG1, W / 2, 950, a2 * min(1, ease((t - 3.7) / 0.35)), sh=False)
        paste(fr, SUB2, W / 2, 1130, win(t, 3.9, 6.6))
        paste(fr, WORD, W / 2, 1330, win(t, 4.2, 6.6), 0.7)
    # 3) доверие: 14 и 30 000
    a3 = win(t, 6.6, 9.6)
    if a3 > 0:
        paste(fr, N14, W / 2, 760, a3, 0.9 + 0.1 * ease((t - 6.6) / 0.5))
        paste(fr, T14a, W / 2, 930, a3); paste(fr, T14b, W / 2, 1005, a3)
        n = int(30000 * ease((t - 7.4) / 1.4)); txt = f"{n:,}".replace(",", " ")
        num = fit(txt, MB, 130, 900, GOLD2)
        paste(fr, num, W / 2, 1200, win(t, 7.3, 9.6)); paste(fr, T30a, W / 2, 1320, win(t, 7.5, 9.6))
    # 4) Рамазон + телефон
    a4 = win(t, 9.6, DUR, 0.45, 0.6)
    if a4 > 0:
        paste(fr, EMB, W / 2, 470, a4, 0.55)
        paste(fr, RAM, W / 2, 800, a4, 0.92 + 0.08 * ease((t - 9.6) / 0.5))
        paste(fr, RAMb, W / 2, 920, win(t, 9.9, DUR, 0.45, 0.6))
        ap = win(t, 10.3, DUR, 0.45, 0.6)
        if ap > 0:
            pw, ph = PH.width + 90, PH.height + 40; pill = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
            ImageDraw.Draw(pill).rounded_rectangle([0, 0, pw - 1, ph - 1], radius=ph // 2, fill=WHITE + (255,))
            pill.alpha_composite(PH, (45, 20)); paste(fr, pill, W / 2, 1110, ap, 0.9 + 0.1 * ease((t - 10.3) / 0.4))
        paste(fr, SLOG, W / 2, 1290, win(t, 10.8, DUR, 0.5, 0.6))
    # блик по краям и затемнение в конце
    out = np.asarray(fr.convert("RGB")).astype(np.float32)
    out *= min(1, t / 0.5, (DUR - t) / 0.35 + 0.0001) if t > DUR - 0.35 or t < 0.5 else 1
    return np.clip(out, 0, 255).astype(np.uint8)

if OUT.endswith(".png"):   # проверка: лист кадров
    ims = [Image.fromarray(frame(tt)).resize((270, 480)) for tt in (1.8, 3.0, 5.0, 8.6, 11.8)]
    sheet = Image.new("RGB", (270 * len(ims), 480)); [sheet.paste(im, (270 * i, 0)) for i, im in enumerate(ims)]
    sheet.save(OUT); sys.exit()
base = OUT + ".main.mp4"
ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                       "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                       "-pix_fmt", "yuv420p", "-c:a", "aac", base], stdin=subprocess.PIPE)
for n in range(int(DUR * FPS)):
    ff.stdin.write(frame(n / FPS).tobytes())
ff.stdin.close(); ff.wait()
END = "/home/claude/papa/docs/brand/ozod-jamol/koncovka/2s/OZOD_JAMOL_KONCOVKA_KRASNAYA.mp4"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", base, "-i", END, "-filter_complex",
                "[0:v]fps=30,setsar=1[a];[1:v]fps=30,scale=1080:1920,setsar=1[b];[0:a]aresample=48000[x];[1:a]aresample=48000[y];[a][x][b][y]concat=n=2:v=1:a=1[v][au]",
                "-map", "[v]", "-map", "[au]", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart", OUT], check=True)
print("готово", OUT)
