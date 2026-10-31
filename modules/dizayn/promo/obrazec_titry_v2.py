"""Образец v2: минимальные титры внизу (вариант Б: Raleway ExtraBold, заглавные с разрядкой),
без своих звуков, без карточки — ник бота последним титром, потом концовка OZOD JAMOL.
python3 obr2.py <src.mp4> <out_dir> v1|v2"""
import sys, os, subprocess as sp
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SRC, OUT, KEY = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)
W, H, FPS = 1080, 1920, 30
F = '/home/claude/fonts/'
RED = (255, 16, 36); WHITE = (255, 255, 255)
KONC = '/home/claude/papa/docs/brand/ozod-jamol/koncovka/2s/OZOD_JAMOL_KONCOVKA_CHERNAYA.mp4'
HOLD = 1.6  # стоп-кадр в конце, чтобы ник успели прочитать

def font(n, s, w):
    f = ImageFont.truetype(F + n, s); f.set_variation_by_axes([w]); return f
fMAIN = font('Raleway.ttf', 64, 800)
fHAND = font('Raleway.ttf', 60, 800)
fSUB = font('Montserrat.ttf', 27, 800)

def eo(x): x = min(1, max(0, x)); return 1 - (1 - x) ** 3
def eio(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)

def spaced(txt, f, fill, em):
    FE = ['lnum', 'pnum']
    d = ImageDraw.Draw(Image.new('L', (1, 1))); adv = [d.textlength(c, font=f, features=FE) for c in txt]; g = f.size * em
    w = int(sum(adv) + g * (len(txt) - 1)) + 4; im = Image.new('RGBA', (w, int(f.size * 1.4)), (0, 0, 0, 0))
    dd = ImageDraw.Draw(im); x = 0
    for c, a in zip(txt, adv): dd.text((x, 0), c, font=f, fill=fill + (255,), features=FE); x += a + g
    return im

def two(lines, f, em):
    ims = [spaced(l, f, WHITE, em) for l in lines]
    if len(ims) == 1: return ims[0]
    gap = int(f.size * 0.18); w = max(i.width for i in ims); h = sum(i.height for i in ims) + gap
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0)); y = 0
    for i in ims: out.alpha_composite(i, ((w - i.width) // 2, y)); y += i.height + gap
    return out

def shadow(im, r=9, a=170):
    p = r * 3; s = Image.new('RGBA', (im.width + 2 * p, im.height + 2 * p), (0, 0, 0, 0))
    al = Image.new('L', s.size, 0); al.paste(im.getchannel('A'), (p, p))
    s.putalpha(al.filter(ImageFilter.GaussianBlur(r)).point(lambda v: int(v * a / 255))); s.alpha_composite(im, (p, p)); return s, p

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

T = {
 'v1': dict(hook=(0.3, 2.9), box=(4.0, 5.8), bad=(6.1, 8.4), good=(9.1, 10.9), d3=(11.0, 12.6), price=(12.7, 14.1), bot=(14.2, 15.1 + HOLD), end=15.1),
 'v2': dict(hook=(0.3, 2.9), box=(4.3, 5.6), bad=(5.7, 8.3), good=(8.9, 10.8), d3=(10.9, 12.5), price=(12.6, 14.0), bot=(14.1, 15.3 + HOLD), end=15.3),
}[KEY]
SC = [  # ключ, главная строка, подпись, значок, главная строчными (для ника)
 ('hook', 'ТАЪМИРНИ|ЎЙЛАЯПСИЗМИ?', 'OZOD JAMOL ДИЗАЙН', None),
 ('box', 'ҲАММАСИ КОРОБКАДАН', '01 · БОШЛАНИШИ', None),
 ('bad', 'БУНДАЙ ҚИЛМАНГ', '02 · ХАТО', 'x'),
 ('good', 'МАНА БУНДАЙ', '03 · ТЎҒРИСИ', 'v'),
 ('d3', 'АВВАЛ 3D,|КЕЙИН ТАЪМИР', '04 · 3D ЛОЙИҲА', None),
 ('price', '1 М² — $3', '3D ДИЗАЙН ЛОЙИҲА', None),
 ('bot', '@ozodjamoldizaynbot', 'ТЕЛЕГРАМ БОТ', None),
]
PRE = {}
for key, main, sub, mk in SC:
    m = two(main.split('|'), fHAND if key == 'bot' else fMAIN, 0.03 if key == 'bot' else 0.14)
    PRE[key] = (shadow(m), shadow(spaced(sub, fSUB, (232, 232, 232), 0.4), 7, 180), mark(mk) if mk else None)

Y_BAR, Y_MAIN, Y_SUB = 1302, 1330, 0   # выше нижней зоны интерфейса Instagram/TikTok

grad = np.zeros((H, W, 4), np.uint8); yy = np.arange(H)[:, None]
grad[..., 3] = (np.clip((yy - 1050) / 870, 0, 1) ** 1.4 * 185).astype(np.uint8).repeat(W, 1); GRAD = Image.fromarray(grad)

def frame(t):
    c = Image.new('RGBA', (W, H), (0, 0, 0, 0)); c.alpha_composite(GRAD)
    for key, *_ in SC:
        t0, t1 = T[key]
        if not (t0 <= t <= t1): continue
        (mi, mp), (si, spd), mk = PRE[key]; k = t - t0
        out = 1 - eio((t - (t1 - 0.35)) / 0.35) if key != 'bot' else 1.0
        # красная черта раскрывается из центра
        bw = int(44 * eo(k / 0.4))
        if bw > 0: ImageDraw.Draw(c).rectangle((W // 2 - bw // 2, Y_BAR, W // 2 + bw // 2, Y_BAR + 4), fill=RED + (int(255 * out),))
        # главная строка: подъём из-под маски + проявление, разрядка чуть сужается
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
    return c

def run(c): sp.run(c, check=True)

if __name__ == '__main__':
    END = T['end']; TOT = END + HOLD
    run(['ffmpeg', '-v', 'error', '-y', '-i', SRC, '-t', str(END), '-vf',
         f'scale={W}:{H}:flags=lanczos,fps={FPS},tpad=stop_mode=clone:stop_duration={HOLD},format=yuv420p',
         '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '14', '-an', f'{OUT}/base.mp4'])
    fd = f'{OUT}/ov'; os.makedirs(fd, exist_ok=True)
    for i in range(int(round(TOT * FPS))): frame(i / FPS).save(f'{fd}/o{i:04d}.png', compress_level=1)
    run(['ffmpeg', '-v', 'error', '-y', '-i', f'{OUT}/base.mp4', '-framerate', str(FPS), '-i', f'{fd}/o%04d.png', '-filter_complex',
         '[0:v][1:v]overlay=0:0:format=auto,format=yuv420p,setsar=1[o]', '-map', '[o]', '-t', str(TOT),
         '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '14', f'{OUT}/body.mp4'])
    # звук: только родной звук ролика (затухает на стоп-кадре) → звук концовки. Своих звуков нет.
    run(['ffmpeg', '-v', 'error', '-y', '-i', f'{OUT}/body.mp4', '-i', SRC, '-i', KONC, '-filter_complex',
         f'[1:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{END},asetpts=PTS-STARTPTS,apad=whole_dur={TOT},'
         f'afade=out:st={END - 0.6}:d={HOLD + 0.6}[a0];'
         f'[2:a]aresample=48000,aformat=channel_layouts=stereo[a1];[2:v]scale={W}:{H},fps={FPS},format=yuv420p,setsar=1[v1];'
         f'[0:v][a0][v1][a1]concat=n=2:v=1:a=1[v][a]', '-map', '[v]', '-map', '[a]',
         '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '16', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', f'{OUT}/final.mp4'])
    print('OK', f'{OUT}/final.mp4')
