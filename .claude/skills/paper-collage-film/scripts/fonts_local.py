#!/usr/bin/env python3
"""Шрифты без Google Fonts CDN (серверы/контейнеры PAPA, где fonts.googleapis.com закрыт).
Берёт семейства из репозитория github.com/google/fonts (sparse-клон, кэш ~/.cache/papa-gfonts),
кладёт TTF в <project>/comp/fonts/ и пишет comp/fonts_local.css с @font-face;
в comp/index.html и comp/font_sheet.html ссылку на fonts.googleapis.com заменяет на fonts_local.css.

usage: fonts_local.py <project> ["Family|Family|..."]
  без списка — берёт семейства из <link> fonts.googleapis.com в comp/index.html и font_sheet.html.
"""
import os, re, shutil, subprocess, sys, urllib.parse

proj = os.path.abspath(sys.argv[1]); extra = sys.argv[2] if len(sys.argv) > 2 else ''
comp = os.path.join(proj, 'comp'); pages = [os.path.join(comp, p) for p in ('index.html', 'font_sheet.html') if os.path.exists(os.path.join(comp, p))]
cache = os.path.expanduser('~/.cache/papa-gfonts')

fams = []
for p in pages:
    for href in re.findall(r'href="(https://fonts\.googleapis\.com/css2\?[^"]+)"', open(p).read()):
        for v in urllib.parse.parse_qs(urllib.parse.urlparse(href.replace('&amp;', '&')).query).get('family', []):
            fams.append(v.split(':')[0])
fams += [f for f in extra.split('|') if f]
fams = list(dict.fromkeys(fams))
slug = lambda f: re.sub(r'[^a-z0-9]', '', f.lower())

if not os.path.isdir(os.path.join(cache, '.git')):
    subprocess.run(['git', 'clone', '-q', '--depth', '1', '--filter=blob:none', '--sparse', 'https://github.com/google/fonts', cache], check=True)
dirs = []
for f in fams:
    for lic in ('ofl', 'apache', 'ufl'):
        dirs.append(f'{lic}/{slug(f)}')
cur = subprocess.run(['git', '-C', cache, 'sparse-checkout', 'list'], capture_output=True, text=True).stdout.split()
subprocess.run(['git', '-C', cache, 'sparse-checkout', 'set', *sorted(set(cur + dirs))], check=True)

os.makedirs(os.path.join(comp, 'fonts'), exist_ok=True)
css, missing = [], []
for f in fams:
    d = next((os.path.join(cache, x) for x in (f'ofl/{slug(f)}', f'apache/{slug(f)}', f'ufl/{slug(f)}') if os.path.isdir(os.path.join(cache, x))), None)
    meta = d and os.path.join(d, 'METADATA.pb')
    if not meta or not os.path.exists(meta): missing.append(f); continue
    m = open(meta).read()
    wr = re.search(r'axes\s*\{\s*tag:\s*"wght"\s*min_value:\s*([\d.]+)\s*max_value:\s*([\d.]+)', m)
    for blk in re.findall(r'fonts\s*\{(.*?)\}', m, re.S):
        name = re.search(r'name:\s*"([^"]+)"', blk).group(1)
        style = re.search(r'style:\s*"([^"]+)"', blk).group(1)
        weight = re.search(r'weight:\s*(\d+)', blk).group(1)
        fn = re.search(r'filename:\s*"([^"]+)"', blk).group(1)
        src = os.path.join(d, fn)
        if not os.path.exists(src): continue
        safe = re.sub(r'[\[\],]', '_', fn); shutil.copy(src, os.path.join(comp, 'fonts', safe))
        w = f'{int(float(wr.group(1)))} {int(float(wr.group(2)))}' if (wr and '[' in fn) else weight
        css.append(f"@font-face{{font-family:'{name}';font-style:{style};font-weight:{w};font-display:block;src:url('fonts/{safe}') format('truetype');}}")
open(os.path.join(comp, 'fonts_local.css'), 'w').write('\n'.join(css) + '\n')
for p in pages:
    s = open(p).read()
    s = re.sub(r'<link[^>]*fonts\.(googleapis|gstatic)\.com[^>]*>', '', s)
    if 'fonts_local.css' not in s:
        s = s.replace('<head>', '<head><link rel="stylesheet" href="fonts_local.css">', 1) if '<head>' in s else '<link rel="stylesheet" href="fonts_local.css">\n' + s
    open(p, 'w').write(s)
print(f'{len(css)} faces, {len(fams) - len(missing)}/{len(fams)} families' + (f'; не найдены: {", ".join(missing)}' if missing else ''))
