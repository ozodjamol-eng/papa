#!/usr/bin/env python3
"""Карта звука образца (приём OBSION, 09.11.2026): громкость каждые 0,5 с + удары → под них ставим события ролика.
usage: python3 -I zvuk_karta.py <ref.mp4> <out_dir> [шаг_с=0.5]
Пишет: <out>/zvuk_karta.md (таблица время | громкость dB | полоска | удар), <out>/zvuk_karta.json, <out>/zvuk_karta.png (график).
Удар = резкий рост громкости (окно 50 мс) выше соседей на 6 dB. Только ffmpeg + numpy + PIL, сеть не нужна."""
import json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw

ref, out = sys.argv[1], sys.argv[2]
step = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
os.makedirs(out, exist_ok=True)
SR = 16000
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', ref, '-vn', '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'],
                     capture_output=True).stdout
a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
if a.size == 0:
    open(os.path.join(out, 'zvuk_karta.md'), 'w').write('# Карта звука\nЗвука в образце нет.\n'); print('нет звука'); sys.exit(0)

def db(x):
    return 20 * np.log10(np.sqrt(np.mean(x * x)) + 1e-9)

# громкость по шагам
n = int(np.ceil(len(a) / (SR * step)))
lv = [round(float(db(a[int(i * step * SR):int((i + 1) * step * SR)])), 1) for i in range(n)]
# удары: окна 50 мс, рост энергии
w = int(SR * 0.05); m = len(a) // w
e = np.array([db(a[i * w:(i + 1) * w]) for i in range(m)])
hits = []
for i in range(3, m):
    if e[i] > -45 and e[i] - np.mean(e[i - 3:i]) >= 6 and (not hits or i * 0.05 - hits[-1] >= 0.2):
        hits.append(round(i * 0.05, 2))
top = sorted(hits, key=lambda t: -e[int(t / 0.05)])[:max(1, len(hits) // 3)]
lo, hi = min(lv), max(lv)
rows = ['# Карта звука образца', f'Длина {len(a)/SR:.1f} с · шаг {step} с · громкость {lo}…{hi} dB · ударов {len(hits)} (★ = самые сильные)', '',
        '| время | dB | уровень | удары в отрезке |', '|---|---|---|---|']
for i, v in enumerate(lv):
    t0, t1 = i * step, (i + 1) * step
    bar = '█' * int(round((v - lo) / max(hi - lo, 1) * 12))
    hs = [f"{h:.2f}{'★' if h in top else ''}" for h in hits if t0 <= h < t1]
    rows.append(f'| {t0:5.1f} | {v:6.1f} | {bar} | {" ".join(hs)} |')
open(os.path.join(out, 'zvuk_karta.md'), 'w').write('\n'.join(rows) + '\n')
json.dump({'step': step, 'levels_db': lv, 'hits': hits, 'strong': sorted(top)}, open(os.path.join(out, 'zvuk_karta.json'), 'w'))
# график
W, H = max(600, n * 8), 200
im = Image.new('RGB', (W, H + 20), (16, 16, 16)); d = ImageDraw.Draw(im)
for i, v in enumerate(lv):
    hh = int((v - lo) / max(hi - lo, 1) * (H - 10))
    d.rectangle([i * W / n, H - hh, (i + 1) * W / n - 1, H], fill=(90, 160, 255))
for h in hits:
    x = h / (n * step) * W
    d.line([x, 0, x, H], fill=(255, 90, 60) if h in top else (120, 70, 60))
for s in range(0, int(n * step) + 1, 5):
    d.text((s / (n * step) * W + 2, H + 4), f'{s}s', fill=(200, 200, 200))
im.save(os.path.join(out, 'zvuk_karta.png'))
print(f'OK: {n} шагов, {len(hits)} ударов → {out}/zvuk_karta.md')
