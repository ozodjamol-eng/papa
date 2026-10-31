"""Образец титров «OZOD JAMOL Дизайн» поверх ролика-рефа + премиальный выход бота.
python3 obr.py <src.mp4> <out_dir> <timings_key>"""
import sys, os, math, subprocess as sp
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SRC, OUT, KEY = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)
W, H, FPS = 1080, 1920, 30
F = '/home/claude/fonts/'
RED = (255, 16, 36); WHITE = (255, 255, 255); INK = (12, 12, 14)
KONC = '/home/claude/papa/docs/brand/ozod-jamol/koncovka/2s/OZOD_JAMOL_KONCOVKA_CHERNAYA.mp4'

def font(n, s, w):
    f = ImageFont.truetype(F + n, s); f.set_variation_by_axes([w]); return f
SERIF = lambda s: font('Lora.ttf', s, 700)
SANS = lambda s, w=800: font('Montserrat.ttf', s, w)

def eo(x): x = min(1, max(0, x)); return 1 - (1 - x) ** 3
def eio(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)

def spaced(txt, f, fill, sp_em):
    d = ImageDraw.Draw(Image.new('L', (1, 1)))
    adv = [d.textlength(c, font=f) for c in txt]; gap = f.size * sp_em
    w = int(sum(adv) + gap * (len(txt) - 1)) + 8; h = int(f.size * 1.45)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); dd = ImageDraw.Draw(im); x = 0
    for c, a in zip(txt, adv): dd.text((x, 0), c, font=f, fill=fill + (255,)); x += a + gap
    return im

def textimg(txt, f, fill):
    d = ImageDraw.Draw(Image.new('L', (1, 1))); w = int(d.textlength(txt, font=f)) + 8
    im = Image.new('RGBA', (w, int(f.size * 1.45)), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((0, 0), txt, font=f, fill=fill + (255,)); return im

def shadow(im, r=10, a=150):
    pad = r * 3; s = Image.new('RGBA', (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    al = Image.new('L', s.size, 0); al.paste(im.getchannel('A'), (pad, pad))
    s.putalpha(al.filter(ImageFilter.GaussianBlur(r)).point(lambda v: int(v * a / 255)))
    s.alpha_composite(im, (pad, pad)); return s, pad

def alpha(im, a):
    if a >= 0.999: return im
    im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v: int(v * a))); return im

def rise(canvas, im, x, y, p, a=1.0):
    """маска-подъём: строка выходит снизу из-под невидимой линии"""
    if p <= 0 or a <= 0: return
    h = im.height; off = int((1 - eo(p)) * h * 0.9)
    vis = im.crop((0, 0, im.width, h - off)) if off < h else None
    if vis is None or vis.height < 1: return
    canvas.alpha_composite(alpha(vis, a * eo(p * 1.4)), (int(x), int(y + off)))

def mark(kind, d=96):
    s = 4; im = Image.new('RGBA', (d * s, d * s), (0, 0, 0, 0)); dd = ImageDraw.Draw(im)
    if kind == 'x':
        dd.ellipse((0, 0, d * s - 1, d * s - 1), fill=RED + (255,)); w = int(d * s * 0.11); m = d * s * 0.31
        dd.line((m, m, d * s - m, d * s - m), fill=WHITE + (255,), width=w)
        dd.line((m, d * s - m, d * s - m, m), fill=WHITE + (255,), width=w)
    else:
        dd.ellipse((0, 0, d * s - 1, d * s - 1), fill=WHITE + (255,)); w = int(d * s * 0.11); D = d * s
        dd.line([(D * .27, D * .52), (D * .44, D * .68), (D * .74, D * .34)], fill=INK + (255,), width=w, joint='curve')
    return im.resize((d, d), Image.LANCZOS)

# ---------- сценарий (узбекская кириллица) ----------
LBL = 'OZOD JAMOL ДИЗАЙН'
T = {  # тайминги под каждый реф (сек)
 'v1': dict(hook=(0.25, 2.9), box=(4.55, 6.3), bad=(6.45, 8.4), good=(9.1, 10.9), d3=(11.1, 13.4), price=(13.5, 15.1), end=15.1),
 'v2': dict(hook=(0.25, 2.9), box=(4.4, 5.6), bad=(5.7, 8.3), good=(8.9, 10.8), d3=(11.0, 13.3), price=(13.4, 15.3), end=15.3),
}[KEY]
SC = [
 ('hook', LBL, ['Таъмирни', 'ўйлаяпсизми?'], None),
 ('box', '01 · КОРОБКА', ['Ҳаммаси', 'коробкадан', 'бошланади'], None),
 ('bad', '02 · ХАТО', ['Бундай', 'қилманг'], 'x'),
 ('good', '03 · ТЎҒРИСИ', ['Мана', 'бундай'], 'v'),
 ('d3', '04 · 3D ЛОЙИҲА', ['Аввал — 3D,', 'кейин таъмир'], None),
]
HX, HY = 84, 210
fL, fH = SANS(38, 900), SERIF(118)
pre = {}
for key, lab, lines, mk in SC:
    li = [shadow(textimg(t, fH, WHITE), 14, 170) for t in lines]
    pre[key] = (shadow(spaced(lab, fL, WHITE, 0.22), 8, 190), li, mark(mk) if mk else None)

def title(c, key, t):
    t0, t1 = T[key]
    if t < t0 - 0.01 or t > t1: return
    lab, li, mk = pre[key]; k = t - t0
    out = 1 - eio((t - (t1 - 0.32)) / 0.32)
    ex = int((1 - out) * -30)  # уход чуть вверх
    # красная линия-акцент растёт
    lw = int(70 * eo(k / 0.45))
    if lw > 0:
        ImageDraw.Draw(c).rectangle((HX, HY + ex, HX + lw, HY + 6 + ex), fill=RED + (int(255 * out),))
    li_lab, pad = lab
    rise(c, li_lab, HX + 92 - pad, HY - 22 - pad + ex, (k - 0.08) / 0.5, out)
    y = HY + 58
    for i, (im, p2) in enumerate(li):
        rise(c, im, HX - p2, y - p2 + ex, (k - 0.18 - 0.11 * i) / 0.55, out); y += 136
    if mk is not None:
        p = eo((k - 0.45) / 0.35);
        if p > 0:
            s = 0.6 + 0.4 * p + 0.08 * math.sin(min(1, p) * math.pi)
            m = mk.resize((int(mk.width * s), int(mk.height * s)), Image.LANCZOS)
            lw2 = int(ImageDraw.Draw(Image.new('L', (1, 1))).textlength(SC[[s_[0] for s_ in SC].index(key)][2][-1], font=fH))
            c.alpha_composite(alpha(m, p * out), (int(HX + lw2 + 34 + (96 - m.width) / 2), int(y - 136 + 30 + (96 - m.height) / 2 + ex)))

fP1, fP2, fP3 = SANS(300, 900), SANS(48, 900), SANS(38, 900)
P_BIG = shadow(textimg('$3', fP1, WHITE), 16, 170)
P_A = shadow(spaced('1 М² УЧУН', fP2, WHITE, 0.25), 6, 150)
P_B = shadow(spaced('3D ДИЗАЙН ЛОЙИҲА', fP3, WHITE, 0.22), 8, 190)
def price(c, t):
    t0, t1 = T['price']
    if t < t0 or t > t1 + 0.2: return
    k = t - t0
    ImageDraw.Draw(c).rectangle((HX, HY, HX + int(70 * eo(k / 0.45)), HY + 6), fill=RED + (255,))
    rise(c, P_B[0], HX + 92 - P_B[1], HY - 22 - P_B[1], (k - 0.05) / 0.5)
    rise(c, P_BIG[0], HX - 10 - P_BIG[1], HY + 30 - P_BIG[1], (k - 0.15) / 0.6)
    rise(c, P_A[0], HX - P_A[1], HY + 400 - P_A[1], (k - 0.35) / 0.5)

# верхняя мягкая тень для читаемости
grad = Image.new('RGBA', (W, H), (0, 0, 0, 0)); g = np.zeros((H, W, 4), np.uint8)
yy = np.arange(H)[:, None]; g[..., 3] = (np.clip(1 - yy / 1150, 0, 1) ** 1.4 * 190).astype(np.uint8).repeat(W, 1)
grad = Image.fromarray(g)

def body_frame(t):
    c = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ga = 1.0 if t < T['end'] - 0.4 else max(0, (T['end'] - t) / 0.4)
    c.alpha_composite(alpha(grad, ga))
    for key, *_ in SC: title(c, key, t)
    price(c, t)
    return c

# ---------- премиальный выход бота (3.2 с) ----------
CARD = 3.2
HANDLE = '@ozodjamoldizaynbot'
fHd = SANS(70, 800)
dch = ImageDraw.Draw(Image.new('L', (1, 1)))
CH = [(ch, dch.textlength(ch, font=fHd)) for ch in HANDLE]
HW = sum(a for _, a in CH) + 2 * (len(CH) - 1)
fT = SERIF(108); TOP = shadow(textimg('OZOD JAMOL', fT, WHITE), 12, 160); TOP2 = shadow(textimg('Дизайн', SERIF(108), RED), 12, 160)
SUB = spaced('ДИЗАЙН  ·  УСТА  ·  3D', SANS(38, 900), (235, 235, 235), 0.25)
LAB = spaced('ТЕЛЕГРАМ БОТ', SANS(36, 900), RED, 0.4)

def card_frame(t, bg):
    c = bg.copy(); LY = 1000
    # 1) имя бренда (засечки) поднимается
    rise(c, TOP[0], (W - TOP[0].width) // 2, 590 - TOP[1], (t - 0.05) / 0.6)
    rise(c, TOP2[0], (W - TOP2[0].width) // 2, 720 - TOP2[1], (t - 0.18) / 0.6)
    # 2) тонкая красная линия раскрывается из центра
    lw = int(560 * eio((t - 0.25) / 0.6))
    if lw > 0: ImageDraw.Draw(c).rectangle(((W - lw) // 2, LY, (W + lw) // 2, LY + 4), fill=RED + (255,))
    # 3) подпись «ТЕЛЕГРАМ БОТ» — проявление с сужением разрядки
    p = eo((t - 0.35) / 0.6)
    if p > 0:
        sc = 1.12 - 0.12 * p; im = LAB.resize((int(LAB.width * sc), LAB.height), Image.LANCZOS)
        c.alpha_composite(alpha(im, p), ((W - im.width) // 2, LY - 72))
    # 4) юзер: буквы по одной выходят из-под линии (каскад), без плашки
    x = (W - HW) / 2; base = LY + 34
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dl = ImageDraw.Draw(layer)
    for i, (ch, a) in enumerate(CH):
        q = eo((t - 0.55 - i * 0.028) / 0.45)
        if q > 0:
            dl.text((x, base + (1 - q) * 70), ch, font=fHd, fill=WHITE + (int(255 * min(1, q * 1.3)),))
        x += a + 2
    # маска: ничего не видно выше линии
    m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).rectangle((0, LY + 6, W, H), fill=255)
    layer.putalpha(Image.fromarray(np.minimum(np.asarray(layer.getchannel('A')), np.asarray(m))))
    # 5) блик-«шиммер» проходит по юзеру один раз
    s = (t - 1.55) / 0.7
    if 0 < s < 1:
        A = np.asarray(layer.getchannel('A')).astype(np.float32) / 255
        xs = np.arange(W)[None, :]; cx = -200 + s * (W + 400)
        band = np.exp(-((xs - cx - (np.arange(H)[:, None] - base) * 0.35) ** 2) / (2 * 55 ** 2))
        glow = (A * band * 255).astype(np.uint8)
        gl = Image.new('RGBA', (W, H), (255, 225, 225, 0)); gl.putalpha(Image.fromarray(glow).filter(ImageFilter.GaussianBlur(10)))
        c.alpha_composite(gl)
    c.alpha_composite(layer)
    # 6) строка услуг
    p = eo((t - 1.25) / 0.6)
    if p > 0: c.alpha_composite(alpha(SUB, p), ((W - SUB.width) // 2, int(LY + 170 + (1 - p) * 20)))
    # общий выход в концовку
    if t > CARD - 0.3:
        a = (t - (CARD - 0.3)) / 0.3; c = Image.blend(c.convert('RGB'), Image.new('RGB', (W, H), (0, 0, 0)), min(1, a)).convert('RGBA')
    return c

def run(c): sp.run(c, check=True)

if __name__ == '__main__':
    END = T['end']
    # 1) тело: исходник 1080x1920 + титры
    run(['ffmpeg', '-v', 'error', '-y', '-i', SRC, '-t', str(END), '-vf', f'scale={W}:{H}:flags=lanczos,fps={FPS},format=yuv420p',
         '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '14', '-an', f'{OUT}/base.mp4'])
    fd = f'{OUT}/ov'; os.makedirs(fd, exist_ok=True)
    N = int(round(END * FPS))
    for i in range(N): body_frame(i / FPS).save(f'{fd}/o{i:04d}.png', compress_level=1)
    run(['ffmpeg', '-v', 'error', '-y', '-i', f'{OUT}/base.mp4', '-framerate', str(FPS), '-i', f'{fd}/o%04d.png', '-filter_complex',
         '[0:v][1:v]overlay=0:0:format=auto,format=yuv420p[o]', '-map', '[o]', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '14', f'{OUT}/body.mp4'])
    # 2) карточка бота на размытом финальном кадре
    run(['ffmpeg', '-v', 'error', '-y', '-sseof', '-0.1', '-i', f'{OUT}/base.mp4', '-frames:v', '1', '-update', '1', f'{OUT}/last.png'])
    bg = Image.open(f'{OUT}/last.png').convert('RGB')
    cd = f'{OUT}/card'; os.makedirs(cd, exist_ok=True)
    for i in range(int(CARD * FPS)):
        t = i / FPS; bl = eio(t / 0.45)
        b = bg.filter(ImageFilter.GaussianBlur(2 + 26 * bl)); b = Image.blend(b, Image.new('RGB', (W, H), (6, 6, 8)), 0.62 * bl)
        b = b.resize((int(W * (1 + 0.04 * t / CARD)), int(H * (1 + 0.04 * t / CARD))), Image.BILINEAR)
        b = b.crop(((b.width - W) // 2, (b.height - H) // 2, (b.width - W) // 2 + W, (b.height - H) // 2 + H)).convert('RGBA')
        card_frame(t, b).convert('RGB').save(f'{cd}/c{i:04d}.png', compress_level=1)
    run(['ffmpeg', '-v', 'error', '-y', '-framerate', str(FPS), '-i', f'{cd}/c%04d.png', '-c:v', 'libx264', '-preset', 'veryfast',
         '-crf', '14', '-pix_fmt', 'yuv420p', f'{OUT}/card.mp4'])
    # 3) звук карточки: мягкий «шиммер» + низкий удар (синтез)
    sr = 48000; n = int(CARD * sr); tt = np.arange(n) / sr; rng = np.random.default_rng(3)
    a = np.zeros(n)
    hit = np.exp(-tt / 0.5) * np.sin(2 * np.pi * 55 * tt) * 0.5; st = int(0.25 * sr); a[st:] += hit[:n - st]
    nz = rng.standard_normal(n); from numpy.fft import rfft, irfft
    for k0, f0 in [(0.55, 3500), (1.55, 6000)]:
        seg = np.zeros(n); s0 = int(k0 * sr); L = int(0.9 * sr); e = np.sin(np.linspace(0, np.pi, L)) ** 2
        X = rfft(nz[:L]); fr = np.fft.rfftfreq(L, 1 / sr); X *= np.exp(-((fr - f0) / 1200) ** 2)
        seg[s0:s0 + L] = irfft(X, L) * e; a += seg / (np.abs(seg).max() + 1e-9) * 0.12
    for fr0 in (1318.5, 1975.5):
        s0 = int(0.6 * sr); env = np.exp(-(tt[:n - s0]) / 0.9) * 0.05; a[s0:] += env * np.sin(2 * np.pi * fr0 * tt[:n - s0])
    a = np.clip(a, -1, 1); a[-int(0.3 * sr):] *= np.linspace(1, 0, int(0.3 * sr))
    import wave
    with wave.open(f'{OUT}/card.wav', 'wb') as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((a * 32000).astype(np.int16).tobytes())
    # 4) склейка: тело (звук рефа, затухание) + карточка + фирменная концовка
    run(['ffmpeg', '-v', 'error', '-y', '-i', f'{OUT}/body.mp4', '-i', SRC, '-i', f'{OUT}/card.mp4', '-i', f'{OUT}/card.wav', '-i', KONC,
         '-filter_complex',
         f'[1:a]aresample=48000,atrim=0:{END},asetpts=PTS-STARTPTS,afade=out:st={END-0.8}:d=0.8,aformat=channel_layouts=stereo[a0];'
         f'[3:a]aresample=48000,aformat=channel_layouts=stereo,volume=0.9[a1];'
         f'[4:a]aresample=48000,aformat=channel_layouts=stereo[a2];'
         f'[4:v]scale={W}:{H},fps={FPS},format=yuv420p,setsar=1[v2];[0:v]setsar=1[v0];[2:v]setsar=1[v1];'
         f'[v0][a0][v1][a1][v2][a2]concat=n=3:v=1:a=1[v][a]',
         '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '16', '-c:a', 'aac', '-b:a', '192k',
         '-movflags', '+faststart', f'{OUT}/final.mp4'])
    print('OK', f'{OUT}/final.mp4')
