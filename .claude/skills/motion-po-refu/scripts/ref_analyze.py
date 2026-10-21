#!/usr/bin/env python3
"""Разбор образца (реф-ролика) цифрами — основа для раскадровки «по образцу».
usage: python3 -I ref_analyze.py <ref.mp4> <out_dir>
Пишет: <out>/sheet_XX.jpg (кадры каждые 0.5 с, подписи времени), <out>/cuts.txt (склейки), <out>/palette.png,
<out>/analysis_auto.md — цифры (длина, склеек/с, средний план, палитра, яркость/контраст по секундам) + пустые разделы, которые Claude
заполняет глазами: шрифты, движение, приёмы → каталог, «что берём / что не берём». Сеть не нужна. Только ffmpeg + PIL."""
import json, os, re, subprocess, sys
from PIL import Image, ImageDraw, ImageStat
ref, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
pr = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=width,height,r_frame_rate,codec_type', '-of', 'json', ref], capture_output=True, text=True).stdout)
dur = float(pr['format']['duration']); vs = next(s for s in pr['streams'] if s.get('codec_type') == 'video')
w, h = vs['width'], vs['height']; num, den = map(int, vs['r_frame_rate'].split('/')); fps = num / den
has_audio = any(s.get('codec_type') == 'audio' for s in pr['streams'])
# склейки: scdet (порог 10) — и запасной select scene
r = subprocess.run(['ffmpeg', '-hide_banner', '-i', ref, '-vf', 'scdet=threshold=10', '-an', '-f', 'null', '-'], capture_output=True, text=True).stderr
cuts = sorted({round(float(m), 3) for m in re.findall(r'lavfi\.scd\.time:\s*([\d.]+)', r)})
raw = cuts; runs = []  # подряд идущие «склейки» чаще 0.15 с = покадровая анимация (на двойках), а не монтаж
for c in raw:
    if runs and c - runs[-1][-1] < 0.15: runs[-1].append(c)
    else: runs.append([c])
cuts = [r[0] for r in runs]; twos = [(r[0], r[-1]) for r in runs if len(r) >= 4]
open(os.path.join(out, 'cuts.txt'), 'w').write('\n'.join(f'{c:.3f}' for c in cuts) + '\n')
# кадры каждые 0.5 с
fr = os.path.join(out, 'fr'); os.makedirs(fr, exist_ok=True)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', ref, '-vf', 'fps=2,scale=360:-2', '-q:v', '4', os.path.join(fr, 'f_%04d.jpg')], check=True)
fs = sorted(os.listdir(fr)); ims = [Image.open(os.path.join(fr, f)).convert('RGB') for f in fs]
cols, rows = 6, 5; tw, th = ims[0].size if ims else (360, 202)
for si in range(0, len(ims), cols * rows):
    sh = Image.new('RGB', (cols * tw, rows * (th + 22)), (16, 16, 16)); d = ImageDraw.Draw(sh)
    for k, im in enumerate(ims[si:si + cols * rows]):
        x, y = (k % cols) * tw, (k // cols) * (th + 22); sh.paste(im, (x, y)); t = (si + k) * 0.5
        mark = any(abs(c - t) < 0.26 for c in cuts); d.text((x + 6, y + th + 4), f'{t:5.1f}s' + ('  ✂' if mark else ''), fill=(255, 210, 60) if mark else (220, 220, 220))
    sh.save(os.path.join(out, f'sheet_{si // (cols * rows) + 1:02d}.jpg'), quality=86)
# палитра по всем кадрам
big = Image.new('RGB', (len(ims) * 64 or 1, 36))
for i, im in enumerate(ims): big.paste(im.resize((64, 36)), (i * 64, 0))
q = big.quantize(colors=10, method=Image.Quantize.MEDIANCUT); pal = q.getpalette()[:30]; cnt = sorted(q.getcolors(), reverse=True)
swatch = [(n, '#%02X%02X%02X' % tuple(pal[i * 3:i * 3 + 3])) for n, i in cnt]
tot = sum(n for n, _ in swatch); P = Image.new('RGB', (100 * len(swatch), 80), 'white'); dp = ImageDraw.Draw(P)
for i, (n, hx) in enumerate(swatch): dp.rectangle([i * 100, 0, i * 100 + 99, 56], fill=hx); dp.text((i * 100 + 4, 60), f'{hx} {100 * n / tot:.0f}%', fill='black')
P.save(os.path.join(out, 'palette.png'))
lum = [ImageStat.Stat(im.convert('L')) for im in ims]
per_s = [(i * 0.5, round(s.mean[0]), round(s.stddev[0])) for i, s in enumerate(lum)][::2]
shots = [b - a for a, b in zip([0.0] + cuts, cuts + [dur])]
md = f"""# Разбор образца: {os.path.basename(ref)}
## Цифры (авто)
- Длина {dur:.2f} с · {w}×{h} · {fps:.2f} fps · звук: {'есть' if has_audio else 'нет'}
- Склеек: {len(cuts)} · {len(cuts) / dur:.2f} в секунду · средний план {sum(shots) / len(shots):.2f} с · самый длинный {max(shots):.2f} с
- Склейки (с): {', '.join(f'{c:.2f}' for c in cuts) or '—'}
- Покадровая анимация «на двойках/тройках» (не склейки): {', '.join(f'{a:.2f}–{b:.2f}' for a, b in twos) or '—'}
- Палитра: {', '.join(f'{hx} {100 * n / tot:.0f}%' for n, hx in swatch)}
- Яркость/контраст по секундам (0–255): {'; '.join(f'{t:.0f}s {m}/{s}' for t, m, s in per_s)}
- Листы кадров: sheet_*.jpg (каждые 0.5 с, ✂ = склейка)

## Заполнить глазами (Claude, по листам и полному просмотру кадров 12 fps там, где движение)
### Шрифты (на что похожи, вес, регистр, кириллица есть?)
### Сетка и композиция (где текст, поля, сколько слоёв)
### Движение (кривые: резко/плавно, overshoot, «на двойках», камера)
### Переходы (каждая склейка: тип)
### Каталог приёмов (приём → время в образце → как сделать у нас → какой инструмент: vizavi-motion / paper-collage-film / mebel_kit)
### Звук (темп BPM, где удары, SFX)
### Берём / не берём (берём ТЕХНИКУ, сюжет и слова — свои; чужие логотипы, плашки, людей — нет)
"""
open(os.path.join(out, 'analysis_auto.md'), 'w').write(md); print(md.split('## Заполнить')[0])
