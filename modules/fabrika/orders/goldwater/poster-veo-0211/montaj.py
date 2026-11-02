"""GOLD WATER — монтаж Veo-роликов: клипы + титры стиль «Б» внизу (Raleway 800 разрядка) + финальная карточка + концовка OZOD JAMOL.
python3 montaj.py <spec.json> <out.mp4>"""
import sys, json, subprocess as sp, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
SPEC = json.load(open(sys.argv[1])); OUT = sys.argv[2]
W, H, FPS = 1080, 1920, 24
F = '/home/claude/fonts/'
GOLD = (200, 147, 52); GOLDL = (250, 226, 137); WHITE = (255, 255, 255); NAVY = (0, 26, 67)
KONC = '/home/claude/papa/docs/brand/ozod-jamol/koncovka/2s/OZOD_JAMOL_KONCOVKA_CHERNAYA.mp4'
def font(n, s, w=800):
    f = ImageFont.truetype(F + n, s); f.set_variation_by_axes([w]); return f
fMAIN, fSUB = font('Raleway.ttf', 64), font('Montserrat.ttf', 28)
eo = lambda k: 1 - (1 - min(1, max(0, k))) ** 3
def spaced(txt, f, fill, em):
    d = ImageDraw.Draw(Image.new('L', (1, 1))); FE = ['lnum', 'pnum']; adv = [d.textlength(c, font=f, features=FE) for c in txt]; g = f.size * em
    w = int(sum(adv) + g * (len(txt) - 1)) + 8; im = Image.new('RGBA', (w, int(f.size * 1.45)), (0, 0, 0, 0))
    dd = ImageDraw.Draw(im); x = 0
    for c, a in zip(txt, adv): dd.text((x, 0), c, font=f, fill=fill + (255,), features=FE); x += a + g
    return im
def title_img(l1, l2):
    a = spaced(l1, fMAIN, WHITE, .14)
    if a.width > 1000: a = a.resize((1000, int(a.height * 1000 / a.width)), Image.LANCZOS)
    b = spaced(l2, fSUB, GOLDL, .4) if l2 else None
    if b is not None and b.width > 1000: b = b.resize((1000, int(b.height * 1000 / b.width)), Image.LANCZOS)
    h = 14 + 26 + a.height + (b.height + 10 if b else 0)
    im = Image.new('RGBA', (W, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle((W // 2 - 40, 0, W // 2 + 40, 5), fill=GOLD + (255,))
    im.alpha_composite(a, ((W - a.width) // 2, 26))
    if b: im.alpha_composite(b, ((W - b.width) // 2, 26 + a.height + 6))
    # мягкая тень для читаемости
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); sh.putalpha(im.getchannel('A').filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * .75)))
    out = Image.new('RGBA', im.size, (0, 0, 0, 0)); out.alpha_composite(sh, (0, 4)); out.alpha_composite(im); return out
# нижний градиент под титры
grad = np.zeros((H, W, 1), np.float32); ys = np.arange(H)
grad[:, :, 0] = np.clip((ys[:, None] - 1250) / 670, 0, 1) ** 1.6 * .62
def read_clip(path, t0, t1, grade, crop=None):
    vf = (f'crop={crop},' if crop else '') + 'scale=1080:1920,fps=24'
    if grade == 'cool':  # убрать «пивной» жёлтый оттенок: холоднее, меньше насыщенности в тёплых
        vf += ',colorbalance=rs=-.10:gs=-.02:bs=.12:rm=-.12:gm=-.03:bm=.10:rh=-.06:bh=.06,hue=s=.55,eq=contrast=1.06:brightness=.01'
    r = sp.run(['ffmpeg', '-v', 'error', '-ss', str(t0), '-t', str(t1 - t0), '-i', path, '-vf', vf, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, H, W, 3)
segs = []
for s in SPEC['segs']: segs.append(read_clip(s['file'], s['in'], s['out'], s.get('grade'), s.get('crop')))
XF = int(.4 * FPS)
# склейка с перекрёстным растворением
class Frames:
    """Ленивый доступ к кадрам с растворением на стыках (без копии в float — экономия памяти)."""
    def __init__(self, segs):
        self.idx = []; pos = 0
        for si, s in enumerate(segs):
            st = pos if si == 0 else pos - XF
            self.idx.append(st); pos = st + len(s)
        self.n = pos; self.segs = segs
    def __len__(self): return self.n
    def __getitem__(self, i):
        if i < 0: i += self.n
        res = None
        for si, s in enumerate(self.segs):
            st = self.idx[si]
            if st <= i < st + len(s):
                f = s[i - st].astype(np.float32)
                if res is None: res = f
                else:
                    k = (i - st + 1) / (XF + 1); res = res * (1 - k) + f * k
        return res
frames = Frames(segs)
N = len(frames)
# финальная карточка
logo = Image.open('/home/claude/shm/gw/src/logo.png').convert('RGBA').resize((420, 420), Image.LANCZOS)
def endcard(k, t):
    bg = Image.new('RGB', (W, H), NAVY); g = Image.new('L', (W, H), 0); gd = ImageDraw.Draw(g); gd.ellipse((-300, 300, 1380, 1500), fill=110)
    g = g.filter(ImageFilter.GaussianBlur(160)); blue = Image.new('RGB', (W, H), (1, 67, 154)); bg = Image.composite(blue, bg, g).convert('RGBA')
    s = .9 + .1 * eo(k / .5); lg = logo.resize((int(420 * s), int(420 * s)), Image.LANCZOS); a = lg.getchannel('A').point(lambda v: int(v * min(1, k * 3)))
    lg.putalpha(a); bg.alpha_composite(lg, ((W - lg.width) // 2, 560 - lg.height // 2 + int((1 - eo(k / .5)) * 40)))
    return bg
def card_lines(k):
    out = []
    for i, (txt, fam, size, col, em, y) in enumerate(SPEC['card']):
        kk = eo((k - .2 - i * .12) / .4)
        if kk <= 0: continue
        im = spaced(txt, font(fam, size), tuple(col), em)
        if im.width > 980: im = im.resize((980, int(im.height * 980 / im.width)), Image.LANCZOS)
        a = im.getchannel('A').point(lambda v: int(v * kk)); im.putalpha(a); out.append((im, y + int((1 - kk) * 24)))
    return out
CARD = SPEC.get('card_sec', 3.4); NC = int(CARD * FPS)
titles = [(int(t['t0'] * FPS), int(t['t1'] * FPS), title_img(t['l1'], t.get('l2', ''))) for t in SPEC['titles']]
ff = sp.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
               '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '/home/claude/shm/veo/_v.mp4'], stdin=sp.PIPE)
for i in range(N):
    fr = frames[i]
    act = [(a, b, im) for a, b, im in titles if a <= i < b]
    if act:
        fr = fr * (1 - grad)
    img = Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8)).convert('RGBA')
    for a, b, im in act:
        k_in = eo((i - a) / (.5 * FPS)); k_out = eo((b - i) / (.4 * FPS)); k = min(k_in, k_out)
        t2 = im.copy(); t2.putalpha(t2.getchannel('A').point(lambda v: int(v * k)))
        img.alpha_composite(t2, (0, SPEC.get('title_y', 1600) + int((1 - k_in) * 30)))
    ff.stdin.write(img.convert('RGB').tobytes())
last = Image.fromarray(np.clip(frames[-1], 0, 255).astype(np.uint8)).convert('RGBA')
for j in range(NC):
    k = j / FPS
    bg = endcard(k, j / FPS)
    if k < .5:  # растворение из последнего кадра
        bg = Image.blend(last, bg, eo(k / .5))
    for im, y in card_lines(k): bg.alpha_composite(im, ((W - im.width) // 2, y))
    ff.stdin.write(bg.convert('RGB').tobytes())
ff.stdin.close(); ff.wait()
TOT = N / FPS + CARD
# звук: родной звук клипов (с растворением) + тихая музыка
parts = []; t = 0
for s in SPEC['segs']:
    parts.append((s['file'], s['in'], s['out'], t)); t += (s['out'] - s['in']) - XF / FPS
inputs = []; flt = []
for i, (f, a, b, st) in enumerate(parts):
    inputs += ['-ss', str(a), '-t', str(b - a), '-i', f]
    flt.append(f'[{i}:a]aresample=48000,afade=t=in:d=0.3,afade=t=out:st={b - a - 0.4:.3f}:d=0.4,volume={SPEC.get("nat_vol", .8)},adelay={int(st * 1000)}|{int(st * 1000)}[n{i}]')
mi = len(parts); inputs += ['-i', SPEC['music']]
flt.append(f'[{mi}:a]aresample=48000,atrim=0:{TOT:.3f},afade=t=out:st={TOT - 0.8:.3f}:d=0.8,volume={SPEC.get("mus_vol", .35)}[m]')
flt.append(''.join(f'[n{i}]' for i in range(mi)) + f'[m]amix=inputs={mi + 1}:normalize=0,atrim=0:{TOT:.3f},loudnorm=I=-16:TP=-1.5[a]')
sp.run(['ffmpeg', '-v', 'error', '-y', *inputs, '-filter_complex', ';'.join(flt), '-map', '[a]', '-ar', '48000', '/home/claude/shm/veo/_a.wav'], check=True)
sp.run(['ffmpeg', '-v', 'error', '-y', '-i', '/home/claude/shm/veo/_v.mp4', '-i', '/home/claude/shm/veo/_a.wav', '-i', KONC, '-filter_complex',
        '[0:v]setsar=1,fps=30[v0];[2:v]setsar=1,fps=30,format=yuv420p[v2];[1:a]aresample=48000[a0];[2:a]aresample=48000[a2];[v0][a0][v2][a2]concat=n=2:v=1:a=1[v][a]',
        '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', OUT], check=True)
print('OK', TOT + 2.3)
