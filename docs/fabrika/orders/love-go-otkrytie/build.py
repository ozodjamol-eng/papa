"""LOVE GO — репортаж открытия 10.11.2026. Сборка видео ~100 с + концовка OZOD JAMOL.
python3 build.py <list.txt> <work_dir> <voice.f32-dir>
list.txt: «номер|тег|длит|путь» (опись клипов). Звук — mix (голос+интервью+музыка) строится здесь же, всё сдвинуто на +4 с (интро).
"""
import json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

LST, WD, VD = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(WD, exist_ok=True)
CL = {l.split('|')[0]: l.split('|')[3] for l in open(LST).read().split('\n') if l}
FONT = '/home/claude/papa/.claude/skills/slovo-udar/fonts/Montserrat.ttf'
OUTRO = '/home/claude/papa/docs/brand/ozod-jamol/koncovka/2s/OZOD_JAMOL_KONCOVKA_CHERNAYA.mp4'
MUS1 = '/mnt/user-data/attachments/e2f8a7c8-e0db-5e00-add3-3d1ef33e7929/bf103de0-file_15671.mp3'
MUS2 = '/mnt/user-data/attachments/e2f8a7c8-e0db-5e00-add3-3d1ef33e7929/e8dc34d9-file_15940.mp3'
W, H, FPS = 1080, 1920, 30
SH = 4.0  # интро

# (клип, вход, длит. на экране, скорость, вспышка)
SEG = [
    ('036', 1.0, 1.0, 1, 0), ('004', 0.5, 1.0, 1, 1), ('078', 0.5, 1.0, 1, 1), ('001', 0.3, 1.0, 1, 1),   # интро 0–4
    ('001', 3.0, 2.0, 1, 1), ('038', 2.0, 2.0, 1, 0),                                                     # Д1
    ('004', 0.0, 3.0, 1, 0), ('002', 2.0, 3.0, 1, 0),                                                     # Д2
    ('063', 0.0, 3.5, 1, 0), ('064', 0.0, 3.0, 1, 0), ('069', 3.0, 3.3, 1, 0),                            # Д3
    ('064', 12.7, 5.9, 1, 0),                                                                             # речь хокимията (синхрон)
    ('069', 10.3, 2.6, 0.75, 0),                                                                          # лента (замедл.)
    ('069', 12.4, 1.7, 1, 0), ('050', 0.3, 1.7, 1, 0),                                                    # аплодисменты
    ('069', 20.0, 2.0, 1, 0), ('078', 0.0, 3.3, 1, 1), ('084', 0.5, 0.5, 1, 0),                           # Д5 толпа
    ('048', 1.0, 4.9, 1, 1), ('048', 13.8, 5.0, 1, 1), ('049', 10.1, 2.8, 1, 1),                          # интервью
    ('089', 0.5, 1.5, 1, 0), ('091', 0.2, 1.5, 1, 0), ('092', 0.5, 1.6, 1, 0),                            # Д6
    ('008', 1.0, 1.4, 1, 1), ('009', 1.0, 1.3, 1, 0), ('011', 0.5, 1.3, 1, 0),                            # Д7 1-қават
    ('015', 0.5, 1.2, 1, 1), ('021', 0.5, 1.3, 1, 0), ('026', 0.2, 1.3, 1, 0),                            # Д8 2-қават
    ('013', 1.0, .54, 1, 0), ('014', 1.0, .54, 1, 0), ('022', .5, .54, 1, 0), ('027', .5, .54, 1, 0),
    ('029', 1.0, .54, 1, 0), ('030', 1.0, .54, 1, 0), ('032', 1.0, .53, 1, 0), ('035', .5, .53, 1, 0),   # товар быстро
    ('097', 0.5, 1.4, 1, 1), ('101', 0.5, 1.5, 1, 0), ('106', 0.5, 1.5, 1, 0),                            # Д9
    ('066', 0.0, 3.0, 1, 0), ('037', 1.0, 3.5, 1, 0),                                                     # Д10
    ('036', 2.0, 2.8, 1, 0), ('005', 0.0, 2.7, 1, 0),                                                     # Д11 адрес
    ('110', 1.2, 13.0, 1, 1),                                                                             # юмор (синхрон)
]

def run(c): subprocess.run(c, check=True)

# 1. сегменты
lst = []; t = 0; cuts = []
for i, (c, a, d, sp, fl) in enumerate(SEG):
    o = f'{WD}/s{i:02d}.mp4'; lst.append(o); cuts.append(round(t, 2)); t += d
    if os.path.exists(o): continue
    vf = f'setpts=PTS/{sp},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},trim=duration={d},setpts=PTS-STARTPTS'
    if fl: vf += ',fade=t=in:st=0:d=0.12:color=white'
    run(['ffmpeg', '-v', 'error', '-y', '-ss', str(a), '-t', str(d * sp + 0.2), '-i', CL[c], '-an', '-vf', vf,
         '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17', '-pix_fmt', 'yuv420p', o])
VID = round(t, 2)
open(f'{WD}/concat.txt', 'w').write(''.join(f"file '{x}'\n" for x in lst))
run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', f'{WD}/concat.txt', '-c', 'copy', f'{WD}/base.mp4'])
print('video', VID)

# 2. титры (внизу, жирный трекинг)
def font(sz, wt=800):
    f = ImageFont.truetype(FONT, sz); f.set_variation_by_axes([wt]); return f
def tracked(d, y, s, f, track, fill):
    ws = [d.textlength(ch, font=f) for ch in s]; tw = sum(ws) + track * (len(s) - 1); x = (W - tw) / 2
    for ch, w in zip(s, ws):
        d.text((x + 3, y + 3), ch, font=f, fill=(0, 0, 0, 150)); d.text((x, y), ch, font=f, fill=fill); x += w + track
def card(name, l1, l2, s1=96, s2=44, y=1460):
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    g = Image.new('L', (1, 520)); g.putdata([int(170 * (i / 520) ** 1.6) for i in range(520)])
    im.paste(Image.new('RGBA', (W, 520), (0, 0, 0, 255)), (0, H - 520), g.resize((W, 520)))
    d = ImageDraw.Draw(im)
    tracked(d, y, l1, font(s1, 900), 6, (255, 255, 255, 255))
    if l2:
        f2 = font(s2, 800); tr = 9
        while sum(d.textlength(ch, font=f2) for ch in l2) + tr * (len(l2) - 1) > W - 90:
            s2 -= 2; f2 = font(s2, 800); tr = max(3, tr - 1)
        tracked(d, y + s1 + 26, l2, f2, tr, (255, 140, 40, 255))
    im.save(f'{WD}/{name}.png')
CAPS = [('t0', 'LOVE GO', 'ХЎЖАОБОД · ОЧИЛИШ · 10.11.2026', 0.3, 3.9, 150, 42),
        ('t1', '1-ҚАВАТ', 'ЭРКАКЛАР · БОЛАЛАР', 58.9, 62.7, 96, 46),
        ('t2', '2-ҚАВАТ', 'АЁЛЛАР · ҚИЗЛАР', 62.9, 66.5, 96, 46),
        ('t3', 'ҲАМЁНБОП', 'УЛГУРЖИ НАРХЛАРДА', 71.0, 75.2, 96, 46),
        ('t4', 'ТЕЗ ОРАДА', 'ЖАЛАҚУДУҚДА ҲАМ', 77.6, 81.7, 96, 46),
        ('t5', 'ХЎЖАОБОД МАРКАЗИ', '«МАЛИКА» САВДО МАРКАЗИ РЎПАРАСИДА', 82.0, 87.2, 76, 36)]
for n, a, b, *_r, s1, s2 in CAPS: card(n, a, b, s1, s2)
inp = ['-i', f'{WD}/base.mp4']; fc = []; last = '0:v'
for k, (n, a, b, t0, t1, *_r) in enumerate(CAPS):
    inp += ['-loop', '1', '-t', str(VID), '-i', f'{WD}/{n}.png']
    fc.append(f'[{k+1}:v]format=rgba,fade=t=in:st={t0}:d=0.3:alpha=1,fade=t=out:st={t1-0.3}:d=0.3:alpha=1[c{k}]')
    fc.append(f'[{last}][c{k}]overlay=0:0:enable=between(t\\,{t0}\\,{t1})[v{k}]'); last = f'v{k}'
run(['ffmpeg', '-v', 'error', '-y', *inp, '-filter_complex', ';'.join(fc), '-map', f'[{last}]', '-t', str(VID),
     '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17', '-pix_fmt', 'yuv420p', f'{WD}/tit.mp4'])

# 3. звук: голос+интервью (+4 с), музыка: трек1 с 0, трек2 с 36 с по кругу
SR = 48000
def load(p, ss=None, t=None, af=None):
    c = ['ffmpeg', '-v', 'error'] + (['-ss', str(ss)] if ss is not None else []) + (['-t', str(t)] if t is not None else []) + ['-i', p]
    c += (['-af', af] if af else []) + ['-ac', '1', '-ar', str(SR), '-f', 'f32le', '-']
    return np.frombuffer(subprocess.run(c, capture_output=True).stdout, np.float32).copy()
def fade(a, f=0.08):
    n = int(f * SR)
    if len(a) > 2 * n: a[:n] *= np.linspace(0, 1, n); a[-n:] *= np.linspace(1, 0, n)
    return a
vo = lambda n: load(f'{VD}/{n}.mp3', af='loudnorm=I=-15:TP=-1.5,aecho=0.8:0.5:40|75:0.12|0.07')
iv = lambda n, s, t, I=-16: fade(load(CL[n], s, t, af=f'loudnorm=I={I}:TP=-1.5'))
TL = [(0.5, vo('D01')), (3.8, vo('D02')), (10.2, vo('D03')), (19.8, iv('064', 12.7, 5.8)), (25.9, vo('D04')),
      (28.0, iv('065', 2.0, 3.6, -20)), (31.7, vo('D05')), (37.5, iv('048', 1.0, 4.8)), (42.6, iv('048', 14.0, 4.7)),
      (47.6, iv('049', 10.3, 2.4)), (50.3, vo('D06')), (54.9, vo('D07')), (58.9, vo('D08')), (66.9, vo('D09')),
      (71.3, vo('D10')), (77.9, vo('D11')), (83.3, iv('110', 1.2, 12.8))]
buf = np.zeros(int(VID * SR), np.float32)
for t0, a in TL:
    i = int((t0 + SH) * SR); n = min(len(a), len(buf) - i); buf[i:i + n] += a[:n]
buf.tofile(f'{WD}/voice.f32')
m1 = load(MUS1, af='loudnorm=I=-23:TP=-6'); m2 = load(MUS2, af='loudnorm=I=-23:TP=-6')
mus = np.zeros_like(buf); xf = int(1.5 * SR)
s = m1.copy(); s[-xf:] *= np.linspace(1, 0, xf); mus[:min(len(s), len(mus))] += s[:len(mus)]
pos = len(m1) - xf
while pos < len(mus):
    s = m2.copy(); s[:xf] *= np.linspace(0, 1, xf); s[-xf:] *= np.linspace(1, 0, xf)
    n = min(len(s), len(mus) - pos); mus[pos:pos + n] += s[:n]; pos += len(s) - xf
fo = int((VID - 0.5 - 1.2) * SR); mus[fo:] *= np.linspace(1, 0, len(mus) - fo)
mus.tofile(f'{WD}/mus.f32')
run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', f'{WD}/voice.f32', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', f'{WD}/mus.f32',
     '-filter_complex', '[0:a]asplit=2[v][sc];[1:a][sc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[d];[v][d]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.95[o]',
     '-map', '[o]', '-ac', '2', '-ar', str(SR), f'{WD}/mix.wav'])

# 4. склейка + концовка OZOD JAMOL
run(['ffmpeg', '-v', 'error', '-y', '-i', f'{WD}/tit.mp4', '-i', f'{WD}/mix.wav', '-i', OUTRO, '-filter_complex',
     f'[0:v]fps={FPS},setsar=1[a];[2:v]scale={W}:{H},fps={FPS},setsar=1[b];[2:a]aresample={SR},aformat=channel_layouts=stereo[ba];[1:a]aformat=channel_layouts=stereo[aa];[a][aa][b][ba]concat=n=2:v=1:a=1[v][o]',
     '-map', '[v]', '-map', '[o]', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', f'{WD}/LOVEGO_otkrytie_v1.mp4'])
json.dump({'cuts': cuts, 'video': VID}, open(f'{WD}/cuts.json', 'w'))
print('OK', f'{WD}/LOVEGO_otkrytie_v1.mp4')
