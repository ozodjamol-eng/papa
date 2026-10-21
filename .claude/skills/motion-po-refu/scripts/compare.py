#!/usr/bin/env python3
"""Лист «образец ↔ наш»: N пар кадров в одинаковых долях длины (или по --times). Смотреть глазами перед сдачей.
usage: python3 -I compare.py <ref.mp4> <ours.mp4> <out.jpg> [N=8] [--times 0.5,1.2,...  (секунды нашего, образец — в той же доле)]"""
import os, subprocess, sys, tempfile
from PIL import Image, ImageDraw
a = sys.argv; ref, ours, out = a[1], a[2], a[3]; n = int(a[4]) if len(a) > 4 and not a[4].startswith('--') else 8
dur = lambda f: float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f], capture_output=True, text=True).stdout)
dr, do = dur(ref), dur(ours)
ts = [float(x) for x in a[a.index('--times') + 1].split(',')] if '--times' in a else [do * (i + 0.5) / n for i in range(n)]
td = tempfile.mkdtemp(); W = 480
def grab(f, t, k):
    p = os.path.join(td, f'{k}.jpg'); subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.3f}', '-i', f, '-frames:v', '1', '-vf', f'scale={W}:-2', p], check=True)
    im = Image.open(p).convert('RGB'); return im.resize((W, int(W * 9 / 16))) if im.width / im.height > 1 else im.resize((int(270 * im.width / im.height), 270))
rows = []
for i, t in enumerate(ts):
    r = grab(ref, t / do * dr, f'r{i}'); o = grab(ours, t, f'o{i}'); h = max(r.height, o.height)
    row = Image.new('RGB', (r.width + o.width + 30, h + 24), (18, 18, 18)); row.paste(r, (0, 24)); row.paste(o, (r.width + 30, 24))
    d = ImageDraw.Draw(row); d.text((6, 4), f'образец {t / do * dr:.2f}s', fill=(200, 200, 200)); d.text((r.width + 36, 4), f'наш {t:.2f}s', fill=(255, 210, 60)); rows.append(row)
S = Image.new('RGB', (max(r.width for r in rows), sum(r.height for r in rows)), (18, 18, 18)); y = 0
for r in rows: S.paste(r, (0, y)); y += r.height
S.save(out, quality=85); print(out)
