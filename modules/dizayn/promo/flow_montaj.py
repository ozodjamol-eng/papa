"""Офис OZOD JAMOL — финал из ролика Google Flow (Veo 3.1, кадры сделаны во Flow, 01.11.2026).
Flow-клип + титры стиль Б + музыка (Aurec — Smooth Soul, Pixabay) + концовка OZOD JAMOL.
python3 flow_montaj.py FLOW_MP4 OUT_DIR"""
import sys, os, subprocess as sp
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
SRC, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
W, H, FPS = 1080, 1920, 30
F = '/home/claude/fonts/'
RED = (255, 16, 36); WHITE = (255, 255, 255)
KONC = '/home/claude/papa/docs/brand/ozod-jamol/koncovka/2s/OZOD_JAMOL_KONCOVKA_CHERNAYA.mp4'
MUS = '/home/claude/papa/modules/fabrika/motion/dayjest/assets/music_kech.mp3'
def eo(x): x = min(1, max(0, x)); return 1 - (1 - x) ** 3
def eio(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
yy = np.arange(H)[:, None].astype(np.float32)
# ---------- титры (стиль Б)
def font(n, s, w):
    f = ImageFont.truetype(F + n, s); f.set_variation_by_axes([w]); return f
fMAIN, fSUB = font('Raleway.ttf', 64, 800), font('Montserrat.ttf', 27, 800)
fHAND = font('Raleway.ttf', 60, 800)
FE = ['lnum', 'pnum']
def spaced(txt, f, fill, em):
    d = ImageDraw.Draw(Image.new('L', (1, 1))); adv = [d.textlength(c, font=f, features=FE) for c in txt]; g = f.size * em
    im = Image.new('RGBA', (int(sum(adv) + g * (len(txt) - 1)) + 4, int(f.size * 1.4)), (0, 0, 0, 0)); dd = ImageDraw.Draw(im); x = 0
    for c, a in zip(txt, adv): dd.text((x, 0), c, font=f, fill=fill + (255,), features=FE); x += a + g
    return im
def two(lines):
    ims = [spaced(l, fHAND, WHITE, 0.03) if l.startswith('@') else spaced(l, fMAIN, WHITE, 0.14) for l in lines]
    if len(ims) == 1: return ims[0]
    gap = 12; w = max(i.width for i in ims); out = Image.new('RGBA', (w, sum(i.height for i in ims) + gap), (0, 0, 0, 0)); y = 0
    for i in ims: out.alpha_composite(i, ((w - i.width) // 2, y)); y += i.height + gap
    return out
def shadow(im, r=9, a=170):
    p = r * 3; s = Image.new('RGBA', (im.width + 2 * p, im.height + 2 * p), (0, 0, 0, 0)); al = Image.new('L', s.size, 0)
    al.paste(im.getchannel('A'), (p, p)); s.putalpha(al.filter(ImageFilter.GaussianBlur(r)).point(lambda v: int(v * a / 255)))
    s.alpha_composite(im, (p, p)); return s, p
def alpha(im, a):
    if a >= 0.999: return im
    im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v: int(v * a))); return im
def mark(kind, d=50):
    s = 4; D = d * s; im = Image.new('RGBA', (D, D), (0, 0, 0, 0)); dd = ImageDraw.Draw(im); w = int(D * 0.12)
    if kind == 'x':
        dd.ellipse((0, 0, D - 1, D - 1), fill=RED + (255,)); m = D * 0.32
        dd.line((m, m, D - m, D - m), fill=WHITE + (255,), width=w); dd.line((m, D - m, D - m, m), fill=WHITE + (255,), width=w)
    else:
        dd.ellipse((0, 0, D - 1, D - 1), fill=WHITE + (255,))
        dd.line([(D * .27, D * .52), (D * .44, D * .68), (D * .74, D * .34)], fill=(12, 12, 14, 255), width=w, joint='curve')
    return im.resize((d, d), Image.LANCZOS)

Y_BAR, Y_MAIN = 1302, 1330
grad = np.zeros((H, W, 4), np.uint8); grad[..., 3] = (np.clip((yy - 1050) / 870, 0, 1) ** 1.4 * 185).astype(np.uint8).repeat(W, 1)
GRAD = Image.fromarray(grad)

def make_titles(spec):
    pre = []
    for (t0, t1, main, sub, mk) in spec:
        pre.append((t0, t1, shadow(two(main.split('|'))), shadow(spaced(sub, fSUB, (232, 232, 232), 0.4), 7, 180), mark(mk) if mk else None))
    return pre

def titles(c, t, pre):
    c.alpha_composite(GRAD)
    for (t0, t1, (mi, mp), (si, spd), mk) in pre:
        if not (t0 <= t <= t1): continue
        k = t - t0; out = 1 - eio((t - (t1 - 0.35)) / 0.35)
        bw = int(44 * eo(k / 0.4))
        if bw > 0: ImageDraw.Draw(c).rectangle((W // 2 - bw // 2, Y_BAR, W // 2 + bw // 2, Y_BAR + 4), fill=RED + (int(255 * out),))
        p = eo((k - 0.08) / 0.6)
        if p > 0:
            sc = 1.035 - 0.035 * p; im = mi.resize((int(mi.width * sc), mi.height), Image.LANCZOS)
            off = int((1 - p) * 26); x = (W - im.width) // 2
            if mk is not None: x -= (mk.width + 34) // 2
            c.alpha_composite(alpha(im, p * out), (x, Y_MAIN - mp + off))
            if mk is not None:
                q = eo((k - 0.4) / 0.35)
                if q > 0: c.alpha_composite(alpha(mk, q * out), (x + im.width - mp + 34, Y_MAIN + 12 + off))
        q = eo((k - 0.28) / 0.55)
        ys = Y_MAIN + (mi.height - 2 * mp) + 8
        if q > 0: c.alpha_composite(alpha(si, q * out), ((W - si.width) // 2, ys - spd + int((1 - q) * 14)))


CLIP = float(sp.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', SRC]))
HOLD = 1.6; TOTAL = CLIP + HOLD
AD = os.environ.get('MODE') == 'ad'   # рекламная версия: цена и бот в конце
if AD: HOLD = 2.6; TOTAL = CLIP + HOLD
TT = make_titles([
    (0.3, 1.7, 'КОРОБКА', '01 · БОШЛАНИШИ', None),
    (1.9, 3.9, 'АВВАЛ — ЛОЙИҲА', '02 · 3D ЧИЗМА', None),
    (4.1, 6.0, 'ЧИЗМА БЎЙИЧА', '03 · ТАЪМИР', None)] + (
    [(6.3, 8.4, '1 М² — $3', '3D ДИЗАЙН ЛОЙИҲА', None), (8.5, TOTAL, '@ozodjamoldizaynbot', 'ТЕЛЕГРАМ БОТ', None)] if AD else
    [(6.3, TOTAL, 'ИЛИҚ|МИНИМАЛИЗМ', 'OZOD JAMOL ОФИС', None)]))
def run(c): sp.run(c, check=True)
run(['ffmpeg', '-v', 'error', '-y', '-i', SRC, '-vf', f'scale={W}:{H}:flags=lanczos,fps={FPS},tpad=stop_mode=clone:stop_duration={HOLD},format=yuv420p',
     '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '14', f'{OUT}/base.mp4'])
fd = f'{OUT}/ov'; os.makedirs(fd, exist_ok=True)
for i in range(int(TOTAL * FPS)):
    c = Image.new('RGBA', (W, H), (0, 0, 0, 0)); titles(c, i / FPS, TT); c.save(f'{fd}/o{i:04d}.png', compress_level=1)
run(['ffmpeg', '-v', 'error', '-y', '-i', f'{OUT}/base.mp4', '-framerate', str(FPS), '-i', f'{fd}/o%04d.png', '-filter_complex',
     '[0:v][1:v]overlay=0:0:format=auto,format=yuv420p,setsar=1[o]', '-map', '[o]', '-t', str(TOTAL), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '14', f'{OUT}/body.mp4'])
run(['ffmpeg', '-v', 'error', '-y', '-i', f'{OUT}/body.mp4', '-i', MUS, '-i', KONC, '-filter_complex',
     f'[1:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{TOTAL},asetpts=PTS-STARTPTS,afade=in:d=0.4,afade=out:st={TOTAL-1.0}:d=1.0,loudnorm=I=-16:TP=-1.5[a0];'
     f'[2:a]aresample=48000,aformat=channel_layouts=stereo[a1];[2:v]scale={W}:{H},fps={FPS},format=yuv420p,setsar=1[v1];'
     f'[0:v][a0][v1][a1]concat=n=2:v=1:a=1[v][a]', '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '16',
     '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', f'{OUT}/final.mp4'])
print('OK', f'{OUT}/final.mp4')
