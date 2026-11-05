"""«Бизнинг ҳамкорлар» v4 — Flow-кадры + наш монтаж. 15 с под трек + концовка OZOD JAMOL."""
import os, sys, subprocess, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
F9 = "/home/claude/fnt/montserrat-900.ttf"
RED = (255, 16, 36)
D = "/home/claude/fin"
os.makedirs(f"{D}/seg", exist_ok=True)

def sh(c): subprocess.run(c, shell=True, check=True)

# 1) партнёры: (файл, начало, конец, реверс) -> 3,0 с каждый
PARTS = [("shod.mp4", 0.5, 8.0, False), ("gw.mp4", 2.0, 7.0, True),
         ("vol.mp4", 0.6, 7.6, True), ("danburg.mp4", 2.0, 8.0, False)]
for i, (f, a, b, rev) in enumerate(PARTS):
    k = (b - a) / 3.0
    vf = f"trim={a}:{b},setpts=PTS-STARTPTS" + (",reverse" if rev else "") + \
         f",setpts=PTS/{k:.4f},fps={FPS},scale={W}:{H}:flags=lanczos,trim=0:3,setpts=PTS-STARTPTS"
    sh(f'ffmpeg -v error -y -i {D}/{f} -an -vf "{vf}" -c:v libx264 -crf 14 -preset veryfast -pix_fmt yuv420p {D}/seg/p{i}.mp4')

# 2) кадры для графики
def font(sz): return ImageFont.truetype(F9, sz)
def text_img(txt, sz, fill=(255, 255, 255), track=4, shadow=True):
    f = font(sz); ws = [f.getlength(c) for c in txt]
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
HEAD = text_img("БИЗНИНГ ҲАМКОРЛАР", 50, (255, 255, 255), 6)
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

# 4) финал 13–15 с: 4 логотипа (последние кадры работ) + пустое место
def last_frame(path, t):
    sh(f"ffmpeg -v error -y -ss {t} -i {path} -frames:v 1 -vf scale={W}:{H} {D}/lf.png")
    return Image.open(f"{D}/lf.png").convert("RGBA")
tiles = []
for path, t, cy in [(f"{D}/seg/p0.mp4", 2.95, .50), (f"{D}/seg/p1.mp4", 2.95, .47),
                    (f"{D}/seg/p2.mp4", 2.95, .44), (f"{D}/seg/p3.mp4", 2.95, .47)]:
    im = last_frame(path, t); s = 1000 if "p0" in path else 760; cx = W // 2; cyy = int(H * cy)
    c = im.crop((cx - s // 2, cyy - s // 2, cx + s // 2, cyy + s // 2)).resize((400, 400), Image.LANCZOS)
    m = Image.new("L", (400, 400), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, 399, 399], 40, fill=255); c.putalpha(m)
    fr = Image.new("RGBA", (420, 420), (0, 0, 0, 0)); ImageDraw.Draw(fr).rounded_rectangle([0, 0, 419, 419], 48, fill=RED + (255,))
    fr.alpha_composite(c, (10, 10)); tiles.append(fr)
pos = [(W * .27, H * .2), (W * .73, H * .2), (W * .27, H * .43), (W * .73, H * .43)]
frm = [(-W, H * .2), (2 * W, H * .2), (-W, H * .43), (2 * W, H * .43)]
L1 = text_img("БУ ЖОЙ —", 64); L2 = text_img("СИЗНИНГ БРЕНДИНГИЗ УЧУН", 50, track=2); L3 = text_img("@Ozodjamol", 74, RED, 2)
os.makedirs(f"{D}/fin", exist_ok=True)
for n in range(int(2.0 * FPS)):
    t = n / FPS; cv = BGI.copy()
    for j in range(4):
        e = back_out(clamp((t - j * .08) / .4))
        xx = frm[j][0] + (pos[j][0] - frm[j][0]) * e; yy = frm[j][1] + (pos[j][1] - frm[j][1]) * e
        place(cv, tiles[j], xx, yy)
    pa = clamp((t - .45) / .2); pul = .5 + .5 * math.sin(t * 10)
    if pa > 0:
        box = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(box)
        x0, y0, x1, y1 = W * .1, H * .57, W * .9, H * .74
        d.rounded_rectangle([x0, y0, x1, y1], 36, fill=RED + (int(25 + 45 * pul),))
        for s_ in range(0, int(x1 - x0), 46):
            d.line([(x0 + s_, y0), (x0 + s_ + 26, y0)], fill=RED + (255,), width=9); d.line([(x0 + s_, y1), (x0 + s_ + 26, y1)], fill=RED + (255,), width=9)
        for s_ in range(0, int(y1 - y0), 46):
            d.line([(x0, y0 + s_), (x0, y0 + s_ + 26)], fill=RED + (255,), width=9); d.line([(x1, y0 + s_), (x1, y0 + s_ + 26)], fill=RED + (255,), width=9)
        box.putalpha(box.getchannel("A").point(lambda v: int(v * pa))); cv.alpha_composite(box)
    place(cv, L1, W / 2, H * .62, 1, clamp((t - .6) / .2))
    place(cv, L2, W / 2, H * .69, 1, clamp((t - .75) / .2))
    place(cv, L3, W / 2, H * .82, 1, clamp((t - .95) / .2))
    if t < .12: cv.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(220 * (1 - t / .12)))))
    cv.convert("RGB").save(f"{D}/fin/{n:03d}.jpg", quality=93)
sh(f"ffmpeg -v error -y -framerate {FPS} -i {D}/fin/%03d.jpg -c:v libx264 -crf 14 -preset veryfast -pix_fmt yuv420p {D}/seg/final.mp4")

# 5) склейка 0–15 с: интро + 4 партнёра (шапка + вспышки на долях) + финал
lst = "\n".join(f"file '{D}/seg/{n}.mp4'" for n in ["intro", "p0", "p1", "p2", "p3", "final"])
open(f"{D}/list.txt", "w").write(lst)
sh(f"ffmpeg -v error -y -f concat -safe 0 -i {D}/list.txt -c copy {D}/main_raw.mp4")
fl = []
for b in [1.0, 4.0, 7.0, 10.0]:
    for j, al in enumerate([0.8, 0.5, 0.25]):
        fl.append(f"drawbox=x=0:y=0:w=iw:h=ih:color=white@{al}:t=fill:enable='between(t\\,{b+j*0.04:.2f}\\,{b+(j+1)*0.04:.2f})'")
vf = "[0:v][1:v]overlay=enable='between(t\\,1\\,13)'[v1];[v1]" + ",".join(fl) + "[v]"
sh(f'ffmpeg -v error -y -i {D}/main_raw.mp4 -loop 1 -i {D}/head.png -i /home/claude/in/m.mp3 -filter_complex "{vf};'
   f'[2:a]atrim=0:15,afade=t=out:st=14.3:d=0.7,aresample=48000,aformat=channel_layouts=stereo[a]" '
   f'-map "[v]" -map "[a]" -t 15 -c:v libx264 -crf 15 -preset veryfast -pix_fmt yuv420p -r {FPS} -c:a aac -b:a 192k {D}/main.mp4')
K = "/home/claude/papa/docs/brand/ozod-jamol/koncovka/2s/OZOD_JAMOL_KONCOVKA_CHERNAYA.mp4"
sh(f'ffmpeg -v error -y -i {D}/main.mp4 -i {K} -filter_complex "[1:a]aresample=48000,aformat=channel_layouts=stereo[ka];'
   f'[0:v][0:a][1:v][ka]concat=n=2:v=1:a=1[v][a]" -map "[v]" -map "[a]" -c:v libx264 -crf 15 -preset veryfast -pix_fmt yuv420p '
   f'-c:a aac -b:a 192k {D}/BIZNING_HAMKORLAR_v4.mp4')
print("ok")
