# Тизер-интрига «Safo Marva — Хўжаобод» перед открытием (02.11.2026).
# Тьма → золотой свет → контур арки рисуется → тексты-намёки → вспышка и раскрытие эмблемы → лицензия, «очилиш яқин кунларда», номер.
# Музыка — Eleven Music, хор без слов и без инструментов (UMRA_A2_hor). Святыни не рисуем. В конце — концовка OZOD JAMOL.
# Запуск: python3 teaser_xojaobod.py <music.mp3> <out.mp4|sheet.png>
import sys, math, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from safomarva_brand import emblem, RED, WHITE, GOLD, GOLD2
MUS, OUT = sys.argv[1], sys.argv[2]
PHONE = "+998 90 766 82 84"
W, H, FPS, DUR = 1080, 1920, 30, 16.0
F = "/home/claude/fonts/"
MB, CZ = F + "Montserrat800.ttf", F + "Cinzel800.ttf"

def ease(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
def eo(x): x = min(1, max(0, x)); return 1 - (1 - x) ** 3
def win(t, a, b, fi=0.6, fo=0.5):
    if t < a or t > b: return 0.0
    return min(eo((t - a) / fi), eo((b - t) / fo))

def text_img(txt, size, fill, track=0, fnt=MB):
    f = ImageFont.truetype(fnt, size); d = ImageDraw.Draw(Image.new("L", (1, 1)))
    ws = [d.textlength(c, font=f) for c in txt]; tw = int(sum(ws) + track * (len(txt) - 1)) + 40
    a, b = f.getmetrics(); im = Image.new("RGBA", (tw, a + b + 40), (0, 0, 0, 0)); dd = ImageDraw.Draw(im); x = 20
    for c, w in zip(txt, ws): dd.text((x, 20), c, font=f, fill=fill); x += w + track
    return im
def fit(txt, size, fill, track=0, fnt=MB, maxw=960):
    while True:
        im = text_img(txt, size, fill, track, fnt)
        if im.width <= maxw: return im
        size -= 2
def glow(im, r, k):
    a = im.split()[3].filter(ImageFilter.GaussianBlur(r)).point(lambda v: min(255, int(v * k)))
    g = Image.new("RGBA", im.size, GOLD2 + (0,)); g.putalpha(a); return g
def paste(fr, im, cx, cy, al=1.0, sc=1.0, gl=0):
    if al <= 0.01: return
    if sc != 1: im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.LANCZOS)
    if al < 1: im = im.copy(); im.putalpha(im.split()[3].point(lambda v: int(v * al)))
    x, y = int(cx - im.width / 2), int(cy - im.height / 2)
    if gl: fr.alpha_composite(glow(im, 18, gl), (x, y))
    fr.alpha_composite(im, (x, y))

# --- ресурсы ---
# 02.11: официальная эмблема клиента (золото, вырезана из их логотипа, фон убран)
EMB = Image.open("/home/claude/papa/docs/fabrika/orders/umra-assets/safomarva_emblema_zoloto.png").convert("RGBA")
EMB = EMB.resize((480, int(480 * EMB.height / EMB.width)), Image.LANCZOS); EW, EH = EMB.size
k = EW / 540; lw = max(6, int(14 * k)); R = 233 * k; cxE, cyE = 271 * k, 271 * k; xl, xr, yb = 38 * k, 505 * k, 760 * k
_bgA = Image.new("RGBA", (EW, EH), (0, 0, 0, 0)); _bd = ImageDraw.Draw(_bgA); _fill = (150, 10, 18, 255)   # фирменный красный, как фон их логотипа
_bd.pieslice([xl, cyE - R, xr, cyE + R], 180, 360, fill=_fill); _bd.rectangle([xl, cyE, xr, yb], fill=_fill)
_bgA.alpha_composite(EMB); EMB = _bgA
path = [(cxE, yb), (xl, yb), (xl, cyE)]
path += [(cxE - R * math.cos(math.radians(a)), cyE - R * math.sin(math.radians(a))) for a in range(0, 181, 3)]
path += [(xr, yb), (cxE, yb)]
seg = [math.dist(path[i], path[i + 1]) for i in range(len(path) - 1)]; TOT = sum(seg)
def outline(frac):
    im = Image.new("RGBA", (EW, EH), (0, 0, 0, 0)); d = ImageDraw.Draw(im); left = TOT * frac; pts = [path[0]]
    for i, s in enumerate(seg):
        if left <= 0: break
        p0, p1 = path[i], path[i + 1]; u = min(1, left / max(s, 1e-6)); pts.append((p0[0] + (p1[0] - p0[0]) * u, p0[1] + (p1[1] - p0[1]) * u)); left -= s
    if len(pts) > 1: d.line(pts, fill=GOLD2 + (255,), width=lw, joint="curve")
    return im

T_SOON = fit("ТЕЗ ОРАДА…", 64, GOLD2, track=18)
T_XOJ = fit("ХЎЖАОБОДДА", 96, WHITE, track=10)
T_S1 = fit("МУҚАДДАС САФАР САРИ", 62, WHITE, track=6)
T_S2 = fit("ЙЎЛ ЯҚИНЛАШМОҚДА", 62, GOLD2, track=6)
WORD0 = fit("SAFO MARVA", 120, GOLD2, track=10, fnt=CZ, maxw=760)
WORD = Image.new("RGBA", (1040, WORD0.height), (0, 0, 0, 0)); WORD.alpha_composite(WORD0, ((1040 - WORD0.width) // 2, 0))
_d = ImageDraw.Draw(WORD); _yl = WORD0.height // 2 + 6
_d.line([(10, _yl), ((1040 - WORD0.width) // 2 - 10, _yl)], fill=GOLD2 + (255,), width=4)
_d.line([((1040 + WORD0.width) // 2 + 10, _yl), (1030, _yl)], fill=GOLD2 + (255,), width=4)
T_UM = fit("УМРА ЗИЁРАТИ", 52, GOLD2, track=16)
T_LIC = fit("РАСМИЙ ЛИЦЕНЗИЯ № UT 0005", 44, GOLD2, track=6)
T_OP = fit("ОЧИЛИШ — ЯҚИН КУНЛАРДА", 70, WHITE)
T_PH = fit(PHONE, 66, RED)

# --- фон, пылинки, лучи ---
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
rng = np.random.default_rng(5); NP = 220
P = np.c_[rng.uniform(0, W, NP), rng.uniform(0, H, NP), rng.uniform(1.0, 3.4, NP), rng.uniform(8, 30, NP), rng.uniform(0, 6.28, NP)]
VIG = np.clip(1 - 0.55 * (((xx - W / 2) / (W / 2)) ** 2 * 0.5 + ((yy - H / 2) / (H / 2)) ** 2 * 0.7), 0.25, 1)[..., None]
CY = 820   # центр сцены (эмблема)

def frame(t):
    reveal = eo((t - 9.0) / 0.5) if t > 9.0 else 0          # момент раскрытия (пик музыки)
    light = min(1, eo((t - 0.6) / 3.0)) * 0.55 + 0.45 * reveal
    flash = math.exp(-((t - 9.05) / 0.22) ** 2) if 8.5 < t < 10 else 0
    # фон: тьма → бордово-золотое свечение из-за арки
    rr = np.hypot((xx - W / 2) / W, (yy - CY) / H)
    glow_bg = np.exp(-(rr / (0.18 + 0.22 * light)) ** 2)[..., None] * light
    bg = np.array([8, 2, 4], np.float32) + glow_bg * np.array([150, 70, 40]) + glow_bg ** 2 * np.array([90, 60, 20]) * reveal
    # лучи из-за арки
    ang = np.arctan2(yy - CY, xx - W / 2)
    rays = (0.5 + 0.5 * np.sin(ang * 14 + t * 0.35)) ** 6 * np.exp(-rr * 2.2)[...] * (0.25 * light + 0.75 * reveal)
    bg = bg + rays[..., None] * np.array([120, 90, 45])
    fr = Image.fromarray(np.clip(bg * VIG, 0, 255).astype(np.uint8)).convert("RGBA")
    # эмблема: контур рисуется 2.8–8.6 с, на раскрытии — полная эмблема со свечением
    push = 1.0 + 0.05 * (t / DUR)
    if t > 2.8:
        frac = eo((t - 2.8) / 5.8)
        ol = outline(frac); paste(fr, ol, W / 2, CY, (1 - reveal) * min(1, (t - 2.8) / 0.4), push, gl=1.6)
    if reveal > 0:
        e_y = CY - 170 * eo((t - 11.4) / 0.8) if t > 11.4 else CY
        e_s = push * (1 - 0.35 * eo((t - 11.4) / 0.8) if t > 11.4 else push)
        paste(fr, EMB, W / 2, e_y, reveal, e_s * (1.08 - 0.08 * reveal), gl=1.2 + 1.5 * flash)
    # тексты-намёки
    paste(fr, T_SOON, W / 2, 1360, win(t, 0.8, 3.6))
    paste(fr, T_XOJ, W / 2, 1360, win(t, 3.8, 6.3), 0.96 + 0.04 * eo((t - 3.8) / 0.8), gl=0.5)
    paste(fr, T_S1, W / 2, 1330, win(t, 6.4, 8.8)); paste(fr, T_S2, W / 2, 1420, win(t, 6.7, 8.8))
    # раскрытие
    paste(fr, WORD, W / 2, 1330 - 200 * eo((t - 11.4) / 0.8) if t > 11.4 else 1330, win(t, 9.2, DUR, 0.7, 0.4), gl=0.4)
    paste(fr, T_UM, W / 2, 1450 - 200 * eo((t - 11.4) / 0.8) if t > 11.4 else 1450, win(t, 9.7, DUR, 0.6, 0.4))
    # финал
    paste(fr, T_LIC, W / 2, 1360, win(t, 11.9, DUR, 0.6, 0.4))
    paste(fr, T_OP, W / 2, 1470, win(t, 12.3, DUR, 0.6, 0.4), 0.95 + 0.05 * eo((t - 12.3) / 0.6))
    ap = win(t, 13.0, DUR, 0.5, 0.4)
    if ap > 0:
        pw, ph = T_PH.width + 70, T_PH.height + 10; pill = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        ImageDraw.Draw(pill).rounded_rectangle([0, 0, pw - 1, ph - 1], radius=ph // 2, fill=WHITE + (255,))
        pill.alpha_composite(T_PH, (35, 5)); paste(fr, pill, W / 2, 1620, ap)
    out = np.asarray(fr.convert("RGB")).astype(np.float32)
    # пылинки
    dd = Image.new("L", (W, H), 0); dr = ImageDraw.Draw(dd)
    for (x0, y0, r, sp, ph) in P:
        x = (x0 + 14 * math.sin(t * 0.5 + ph)) % W; y = (y0 - sp * t) % H
        dr.ellipse([x - r, y - r, x + r, y + r], fill=int(255 * (0.5 + 0.5 * math.sin(t * 1.9 + ph))))
    ov = np.asarray(dd.filter(ImageFilter.GaussianBlur(1.4)), np.float32)[..., None] / 255
    out = out + ov * np.array(GOLD2, np.float32) * (0.25 + 0.5 * light)
    out = out + flash * 45
    out = out + rng.normal(0, 3.0, (H // 2, W // 2, 1)).repeat(2, 0).repeat(2, 1)
    out *= min(1, t / 0.6, (DUR - t) / 0.4)
    return np.clip(out, 0, 255).astype(np.uint8)

if OUT.endswith(".png"):
    tt = [1.8, 4.5, 7.5, 9.1, 10.5, 14.5]
    ims = [Image.fromarray(frame(x)).resize((270, 480)) for x in tt]
    sh = Image.new("RGB", (270 * len(ims), 480)); [sh.paste(im, (270 * i, 0)) for i, im in enumerate(ims)]; sh.save(OUT); sys.exit()

base = OUT + ".main.mp4"
ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                       "-i", MUS, "-filter_complex", f"[1:a]atrim=0:{DUR},afade=t=out:st={DUR - 0.8}:d=0.8,aresample=48000,pan=stereo|c0=c0|c1=c1[a]",
                       "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p",
                       "-c:a", "aac", "-b:a", "192k", "-t", str(DUR), base], stdin=subprocess.PIPE)
for n in range(int(DUR * FPS)):
    ff.stdin.write(frame(n / FPS).tobytes())
ff.stdin.close(); ff.wait()
END = "/home/claude/papa/docs/brand/ozod-jamol/koncovka/2s/OZOD_JAMOL_KONCOVKA_KRASNAYA.mp4"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", base, "-i", END, "-filter_complex",
                "[0:v]fps=30,setsar=1[a];[1:v]fps=30,scale=1080:1920,setsar=1[b];[0:a]aresample=48000[x];[1:a]aresample=48000[y];[a][x][b][y]concat=n=2:v=1:a=1[v][au]",
                "-map", "[v]", "-map", "[au]", "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart", OUT], check=True)
print("готово", OUT)
