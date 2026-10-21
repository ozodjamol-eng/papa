#!/usr/bin/env python3
"""CLX.title и font_sheet рисуют шрифт с весом 400. Для вариативного шрифта (Unbounded, Rubik…) это даёт обычное начертание.
Скрипт делает статичную копию нужной толщины как ОТДЕЛЬНОЕ семейство «<Family> <wght>» с весом 400 и дописывает @font-face в comp/fonts_local.css.
usage: static_face.py <project> "Unbounded:900|Rubik:900"   → COPY.titleFont = '"Unbounded 900"'"""
import os, re, sys
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
proj = os.path.abspath(sys.argv[1]); comp = os.path.join(proj, 'comp'); fd = os.path.join(comp, 'fonts')
css = os.path.join(comp, 'fonts_local.css'); cur = open(css).read() if os.path.exists(css) else ''
for spec in sys.argv[2].split('|'):
    fam, w = spec.split(':'); w = int(w); slug = re.sub(r'[^A-Za-z0-9]', '', fam)
    src = next((os.path.join(fd, f) for f in sorted(os.listdir(fd)) if f.startswith(slug + '_') and 'Italic' not in f), None)
    if not src: print('нет вариативного файла для', fam, '— сначала fonts_local.py'); continue
    f = TTFont(src); axes = {a.axisTag: a for a in f['fvar'].axes}
    loc = {t: (min(max(w, a.minValue), a.maxValue) if t == 'wght' else a.defaultValue) for t, a in axes.items()}
    inst = instancer.instantiateVariableFont(f, loc); name = f'{fam} {w}'; out = f'{slug}-static-{w}.ttf'
    inst.save(os.path.join(fd, out))
    rule = f"@font-face{{font-family:'{name}';font-style:normal;font-weight:400;font-display:block;src:url('fonts/{out}') format('truetype');}}"
    if name not in cur: cur += rule + '\n'
    print('ok', name, '←', os.path.basename(src))
open(css, 'w').write(cur)
