"""«Бизнинг ҳамкорлар» v4 — Flow-кадры + наш монтаж. 15 с под трек + концовка OZOD JAMOL."""
import os, sys, subprocess, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
LANG = os.environ.get("LANG_V", "uz")
F9 = "/home/claude/fnt/montserrat-900.ttf"
FZH = "/home/claude/fnt/notosc-900.ttf"
TX = {"uz": ("БИЗНИНГ ҲАМКОРЛАР", "БУ ЖОЙ —", "СИЗНИНГ БРЕНДИНГИЗ УЧУН"),
      "ru": ("НАШИ ПАРТНЁРЫ", "ЭТО МЕСТО —", "ДЛЯ ВАШЕГО БРЕНДА"),
      "zh": ("我们的合作伙伴", "下一个合作伙伴", "就是您！")}[LANG]
RED = (255, 16, 36)
D = "/home/claude/fin"
os.makedirs(f"{D}/seg", exist_ok=True)

def sh(c): subprocess.run(c, shell=True, check=True)

# 1) партнёры: (файл, начало, конец, реверс) -> 3,0 с каждый
SEG = 4.0
PARTS = [("shod.mp4", 0.5, 8.0, False), ("gw.mp4", 2.0, 7.0, True),
         ("vol.mp4", 0.6, 7.6, True), ("danburg.mp4", 2.0, 8.0, False)]
for i, (f, a, b, rev) in enumerate(PARTS):
    k = (b - a) / SEG
    vf = f"trim={a}:{b},setpts=PTS-STARTPTS" + (",reverse" if rev else "") + \
         f",setpts=PTS/{k:.4f},fps={FPS},scale={W}:{H}:flags=lanczos,trim=0:4,setpts=PTS-STARTPTS"
    sh(f'ffmpeg -v error -y -i {D}/{f} -an -vf "{vf}" -c:v libx264 -crf 14 -preset veryfast -pix_fmt yuv420p {D}/seg/p{i}.mp4')

# 2) кадры для графики
def font(sz, zh=False): return ImageFont.truetype(FZH if zh else F9, sz)
def text_img(txt, sz, fill=(255, 255, 255), track=4, shadow=True):
    f = font(sz, any(ord(c) > 0x2E80 for c in txt)); ws = [f.getlength(c) for c in txt]
    im = Image.new("RGBA", (int(sum(ws) + track * len(txt)) + 60, int(sz * 1.5)), (0, 0, 0, 0)); d = ImageDraw.Draw(im); x = 30
    for c, w in zip(txt, ws): d.text((x, 10), c, font=f, fill=fill); x += w + track
    if shadow:
        s = Image.new("RGBA", im.size, (0, 0, 0, 0)); s.putalpha(im.getchannel("A").point(lambda v: int(v * .8)))
        s = s.filter(ImageFilter.GaussianBlur(10)); s.alpha_composite(im); im = s
    return im
def place(cv, im, cx, cy, s=1., a=1.):
    if s <= .01 or a <= 0: return
    im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BILINEAR)
    if a < 1: im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    cv.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))
def clamp(x, a=0., b=1.): return max(a, min(b, x))
def back_out(t, s=1.4): t -= 1; return t * t * ((s + 1) * t + s) + 1
def ease_out(t): return 1 - (1 - t) ** 3

# шапка поверх партнёров
HEAD = text_img(TX[0], 50, (255, 255, 255), 6)
hd = Image.new("RGBA", (W, H), (0, 0, 0, 0)); place(hd, HEAD, W / 2, H * .075); hd.save(f"{D}/head.png")

# 3) интро 0–1,0 с: OJ из темноты (тихое вступление трека)
sys.path.insert(0, "/home/claude/anim")
OJ = Image.open("/home/claude/anim/oj_full.png").convert("RGBA")
a = np.asarray(OJ).astype(np.float32); a[..., 3] = np.clip((a[..., :3].max(2) - 25) * 4, 0, 255)
OJ = Image.fromarray(a.astype(np.uint8)); OJ = OJ.crop(OJ.getbbox()); k = 820 / OJ.width; OJ = OJ.resize((820, int(OJ.height * k)), Image.LANCZOS)
OJW = text_img("OZOD JAMOL", 72, (255, 255, 255), 8)
y, x = np.mgrid[0:H, 0:W].astype(np.float32)
dd = np.clip(np.sqrt((x / W - .5) ** 2 + ((y / H - .45) * .56) ** 2) / .62, 0, 1)[..., None]
BGI = Image.fromarray((np.array((60, 6, 12)) * (1 - dd)).astype(np.uint8)).convert("RGBA")
os.makedirs(f"{D}/intro", exist_ok=True)
for n in range(int(1.0 * FPS)):
    t = n / FPS; cv = BGI.copy()
    place(cv, OJ, W / 2, H * .43, .88 + .1 * t, ease_out(clamp(t / .6)))
    place(cv, OJW, W / 2, H * .6, 1, clamp((t - .3) / .3))
    cv.convert("RGB").save(f"{D}/intro/{n:03d}.jpg", quality=93)
sh(f"ffmpeg -v error -y -framerate {FPS} -i {D}/intro/%03d.jpg -c:v libx264 -crf 14 -preset veryfast -pix_fmt yuv420p {D}/seg/intro.mp4")

# 4) ПРЕМИУМ-финал: золотая рама на пьедестале (Flow), наезд, блик по золоту, золотая пыль
ZH = LANG == "zh"
if ZH:
    vf = f"trim=0.2:5.8,setpts=PTS-STARTPTS,reverse,setpts=PTS/1.4,fps={FPS},scale={W}:{H}:flags=lanczos,trim=0:4,setpts=PTS-STARTPTS"
    sh(f'ffmpeg -v error -y -i {D}/love.mp4 -an -vf "{vf}" -c:v libx264 -crf 14 -preset veryfast -pix_fmt yuv420p {D}/seg/p4.mp4')
GOLD = [(255, 236, 170), (232, 186, 82), (176, 122, 30)]
def gold_text(txt, sz, track=4):
    base = text_img(txt, sz, (255, 255, 255), track, shadow=False); A = base.getchannel("A")
    g = np.zeros((base.height, base.width, 3), np.float32); yy = np.linspace(0, 1, base.height)[:, None]
    c0, c1, c2 = [np.array(c, np.float32) for c in GOLD]
    col = np.where(yy[..., None] < .5, c0 + (c1 - c0) * (yy[..., None] / .5), c1 + (c2 - c1) * ((yy[..., None] - .5) / .5))
    g[:] = col; im = Image.fromarray(g.astype(np.uint8)).convert("RGBA"); im.putalpha(A)
    sdw = Image.new("RGBA", im.size, (0, 0, 0, 0)); sdw.putalpha(A.point(lambda v: int(v * .9))); sdw = sdw.filter(ImageFilter.GaussianBlur(12))
    sdw.alpha_composite(im); return sdw
def white_text(txt, sz, track=4): return text_img(txt, sz, (255, 255, 255), track)
FT = {"uz": [("w", "БУ ЖОЙ —", 96), ("g", "СИЗНИНГ", 92), ("g", "БРЕНДИНГИЗ УЧУН", 80)],
      "ru": [("w", "ЭТО МЕСТО —", 96), ("g", "ДЛЯ ВАШЕГО", 92), ("g", "БРЕНДА", 104)],
      "zh": [("w", "下一个合作伙伴", 104), ("g", "就是您！", 128)]}[LANG]
LINES = []
for kind, tx, sz in FT:
    im = gold_text(tx, sz) if kind == "g" else white_text(tx, sz)
    if im.width > W - 60: im = im.resize((W - 60, int(im.height * (W - 60) / im.width)), Image.LANCZOS)
    LINES.append(im)
HANDLE = gold_text("@Ozodjamol", 76, 3)
BG = Image.open(f"{D}/fbg.png").convert("RGB"); BGA = np.asarray(BG).astype(np.float32)
gm = ((BGA[..., 0] > 150) & (BGA[..., 1] > 100) & (BGA[..., 2] < 140)).astype(np.float32)
gm[:850] = 0; gm[1420:] = 0; GM = Image.fromarray((gm * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5))
FCX, FCY = 541, 1143          # центр рамы
IN = (412, 952, 670, 1336)    # внутреннее поле рамы
rng = np.random.default_rng(7); PART = rng.random((90, 4))
if ZH:  # LOVE GO — «картина» в раме: последний кадр его сцены
    sh(f"ffmpeg -v error -y -sseof -0.05 -i {D}/seg/p4.mp4 -frames:v 1 {D}/lg.png")
    lg = Image.open(f"{D}/lg.png").convert("RGB"); iw, ih = IN[2] - IN[0], IN[3] - IN[1]
    cw = 820; ch = int(cw * ih / iw); cx0 = 120; cy0 = 922 - ch // 2
    PIC = lg.crop((cx0, cy0, cx0 + cw, cy0 + ch)).resize((iw, ih), Image.LANCZOS).convert("RGBA")
FD = 3.2 if ZH else 3.1
os.makedirs(f"{D}/fin", exist_ok=True)
for f_ in os.listdir(f"{D}/fin"): os.remove(f"{D}/fin/{f_}")
for n in range(int(round(FD * FPS))):
    t = n / FPS; cv = Image.fromarray(BGA.astype(np.uint8)).convert("RGBA")
    if ZH and t > .7:
        e = ease_out(clamp((t - .7) / .5)); p = PIC.copy(); p.putalpha(int(255 * e)); cv.alpha_composite(p, IN[:2])
    # блик по золоту рамы (диагональная полоса слева направо)
    sp = (t - .5) / 1.0
    if 0 < sp < 1.3:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        band = np.clip(1 - np.abs((xx - 300) + (yy - 900) * .45 - sp * 520) / 60, 0, 1)
        add = (band * np.asarray(GM, np.float32) / 255 * 200)
        rgb = np.asarray(cv.convert("RGB")).astype(np.float32); rgb += add[..., None] * np.array([1, .9, .6]); cv = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).convert("RGBA")
    # тёплое свечение рамы (дыхание)
    glow = .5 + .5 * math.sin(t * 4)
    gl = Image.new("RGBA", (W, H), (255, 190, 90, 0)); gl.putalpha(GM.filter(ImageFilter.GaussianBlur(28)).point(lambda v: int(v * (.25 + .25 * glow))))
    cv.alpha_composite(gl)
    # золотая пыль
    d = ImageDraw.Draw(cv)
    for px, py, ps, ph in PART:
        x = 330 + px * 420 + 14 * math.sin(t * 2 + ph * 6); y = (py * 1500 + 120 * t * (0.5 + ps)) % 1500 + 150
        r = 1.5 + ps * 3; a = int(150 + 100 * math.sin(t * 6 + ph * 9) ** 2)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 215, 130, a))
    # наезд камеры 1.00→1.07 к раме
    z = 1 + (.32 if ZH else .12) * ease_out(clamp(t / FD)); cw_, ch_ = W / z, H / z; ox = FCX - cw_ / 2 * (FCX / (W / 2)) ; ox = clamp(FCX - cw_ * FCX / W, 0, W - cw_); oy = clamp(FCY - ch_ * FCY / H, 0, H - ch_)
    cv = cv.crop((int(ox), int(oy), int(ox + cw_), int(oy + ch_))).resize((W, H), Image.BICUBIC)
    cv = cv.convert('RGBA')
    # текст
    ys = [300, 420, 525] if not ZH else [330, 480]
    for j, (im, yy_) in enumerate(zip(LINES, ys)):
        e = ease_out(clamp((t - .25 - j * .18) / .45)); place(cv, im, W / 2, yy_ + 40 * (1 - e), 1, e)
    e = ease_out(clamp((t - 1.0) / .4)); place(cv, HANDLE, W / 2, 1770 + 30 * (1 - e), 1, e)
    if ZH and t > 1.0:
        lt = white_text("LOVE GO × OZOD JAMOL", 46, 3); place(cv, lt, W / 2, 1660, 1, ease_out(clamp((t - 1.2) / .4)))
    if t < .3: cv = Image.blend(Image.new("RGBA", (W, H), (0, 0, 0, 255)), cv, t / .3)
    cv.convert("RGB").save(f"{D}/fin/{n:03d}.jpg", quality=93)
sh(f"ffmpeg -v error -y -framerate {FPS} -i {D}/fin/%03d.jpg -c:v libx264 -crf 14 -preset veryfast -pix_fmt yuv420p {D}/seg/final.mp4")

# 5) склейка 0–15 с: интро + 4 партнёра (шапка + вспышки на долях) + финал
lst = "\n".join(f"file '{D}/seg/{n}.mp4'" for n in ["intro", "p0", "p1", "p2", "p3"] + (["p4"] if ZH else []) + ["final"])
open(f"{D}/list.txt", "w").write(lst)
sh(f"ffmpeg -v error -y -f concat -safe 0 -i {D}/list.txt -c copy {D}/main_raw.mp4")
fl = []
for b in ([1.0, 5.0, 9.0, 13.0, 17.0] if ZH else [1.0, 5.0, 9.0, 13.0]):
    for j, al in enumerate([0.8, 0.5, 0.25]):
        fl.append(f"drawbox=x=0:y=0:w=iw:h=ih:color=white@{al}:t=fill:enable='between(t\\,{b+j*0.04:.2f}\\,{b+(j+1)*0.04:.2f})'")
vf = "[0:v][1:v]overlay=enable='between(t\\,1\\,17)'[v1];[v1]" + ",".join(fl) + "[v]"
TOT = 24.2 if ZH else 20.1
AF = ("[2:a]atrim=0:13.103,asetpts=PTS-STARTPTS[x1];[2:a]atrim=9.0:20.1,asetpts=PTS-STARTPTS[x2];"
      "[x1][x2]acrossfade=d=0.03[am];[am]") if ZH else "[2:a]"
sh(f'ffmpeg -v error -y -i {D}/main_raw.mp4 -loop 1 -i {D}/head.png -i /home/claude/fin/m2.mp3 -filter_complex "{vf};'
   f'{AF}atrim=0:{TOT},afade=t=out:st={TOT-0.8:.2f}:d=0.8,aresample=48000,aformat=channel_layouts=stereo[a]" '
   f'-map "[v]" -map "[a]" -t {TOT} -c:v libx264 -crf 15 -preset veryfast -pix_fmt yuv420p -r {FPS} -c:a aac -b:a 192k {D}/main.mp4')
K = "/home/claude/papa/docs/brand/ozod-jamol/koncovka/2s/OZOD_JAMOL_KONCOVKA_CHERNAYA.mp4"
sh(f'ffmpeg -v error -y -i {D}/main.mp4 -i {K} -filter_complex "[1:a]aresample=48000,aformat=channel_layouts=stereo[ka];'
   f'[0:v][0:a][1:v][ka]concat=n=2:v=1:a=1[v][a]" -map "[v]" -map "[a]" -c:v libx264 -crf 15 -preset veryfast -pix_fmt yuv420p '
   f'-c:a aac -b:a 192k {D}/BIZNING_HAMKORLAR_v6_{LANG}.mp4')
print("ok")
