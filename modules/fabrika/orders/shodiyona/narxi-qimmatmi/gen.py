"""Shodiyona 9:16 «Нархи қимматми?» — озвучка главным диктором. python3 gen.py stills|video"""
import sys, json, subprocess, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, '/home/claude/shm_film/mebel_motion')
import mm
W, H = 1080, 1920; mm.W, mm.H = W, H; FPS = 30
FD = '/usr/share/fonts/opentype/inter/'
def F(n, s): return ImageFont.truetype(FD + n, s)
GREEN, OAK, WAL, CREAM = (31, 58, 40), (184, 129, 74), (116, 66, 30), (251, 248, 241)
def bgr(c): return c[::-1]
ZP = '/home/claude/papa/modules/fabrika/orders/shodiyona/zhivoy-poster/src/'
PH = '/mnt/user-data/outputs/shm/shef_foto/shef_%02d.jpg'
TM = json.load(open('/home/claude/shm9/timing.json')); P = TM['P']
VEND = TM['end_voice']; HOLD = VEND + 3.0; TOTAL = HOLD
def eo(x): x = min(1, max(0, x)); return 1 - (1 - x) ** 3
def ez(x): x = min(1, max(0, x)); return 4*x**3 if x < .5 else 1 - (-2*x+2)**3/2
def spring(x):  # пружина с перелётом
    x = min(1, max(0, x)); return 1 - np.exp(-6*x) * np.cos(9*x)
def png(n):
    im = cv2.imread(ZP + n + '.png', cv2.IMREAD_UNCHANGED); return im
_C = {}
def prod(key, hgt):
    k = (key, int(hgt))
    if k not in _C:
        r = png(key) if isinstance(key, str) else mm.cutout(PH % key)
        _C[k] = mm.place(r, hgt)
    return _C[k]
LOGO = png('logo'); ICON = png('icon')
ICONC = ICON.copy(); ICONC[..., :3] = bgr(CREAM)

def bg_cream(t, grid=False):
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.clip(np.sqrt(((xx-W/2)/(W*.75))**2 + ((yy-H*.42)/(H*.62))**2), 0, 1)
    f = np.dstack([241 - 30*r, 248 - 24*r, 251 - 18*r]).astype(np.float32)
    if grid:
        g = np.zeros((H, W), np.float32); g[::40, :] = 1; g[:, ::40] = 1; g[::200, :] = 2.2; g[:, ::200] = 2.2
        f -= g[..., None] * np.array([3.0, 4.0, 6.0])
    return np.clip(f, 0, 255).astype(np.uint8)
BG = bg_cream(0); BGG = bg_cream(0, True)

def cam(f, k, cx=W/2, cy=H/2, rot=0.0):
    """камера: масштаб k вокруг точки, лёгкий поворот"""
    M = cv2.getRotationMatrix2D((cx, cy), rot, k); return cv2.warpAffine(f, M, (W, H), borderMode=cv2.BORDER_REFLECT)

def put(f, rgba, cx, by, alpha=1.0, shadow=True, scale=1.0):
    r = rgba
    if scale != 1.0: r = cv2.resize(r, (max(2, int(r.shape[1]*scale)), max(2, int(r.shape[0]*scale))), interpolation=cv2.INTER_AREA)
    h, w = r.shape[:2]
    if shadow: f = mm.floor_shadow(f, int(cx), int(by - 6), int(w * .9), alpha)
    return mm.blend(f, r, int(cx - w/2), int(by - h), alpha)

def L(): return Image.new('RGBA', (W, H), (0, 0, 0, 0))
def over(f, Ly): return mm.overlay(f, Ly)
def ctext(d, y, s, fn, fill, a=255, x=None, track=0):
    tw = sum(d.textlength(c, font=fn) for c in s) + track*(len(s)-1); x0 = (W - tw)/2 if x is None else x
    for c in s: d.text((x0, y), c, font=fn, fill=fill + (a,)); x0 += d.textlength(c, font=fn) + track
    return tw

# ---------- видео-карточки (предзагрузка) ----------
_V = {}
def clip(n, a, dur, size, sp=0.6):
    k = (n, a, size)
    if k not in _V:
        c = cv2.VideoCapture('/home/claude/dji/d%02d.mov' % n); fps = c.get(5); c.set(1, int(a*fps)); fr = []
        need = int(dur*sp*fps) + 4
        for _ in range(need):
            ok, im = c.read()
            if not ok: break
            fw, fh = size; s = max(fw/im.shape[1], fh/im.shape[0]) * 1.06
            im = cv2.resize(im, (int(im.shape[1]*s)+1, int(im.shape[0]*s)+1), interpolation=cv2.INTER_AREA)
            oy, ox = (im.shape[0]-fh)//2, (im.shape[1]-fw)//2; fr.append(im[oy:oy+fh, ox:ox+fw])
        _V[k] = (fr, fps, sp)
    return _V[k]
def clipf(n, a, dur, size, lt, sp=0.6):
    fr, fps, sp = clip(n, a, dur, size, sp); i = min(len(fr)-1, int(lt*sp*fps)); return fr[i]
def rounded_paste(f, img, x, y, rad=28, alpha=1.0, shadow=True):
    h, w = img.shape[:2]
    m = np.zeros((h, w), np.uint8); cv2.rectangle(m, (rad, 0), (w-rad, h), 255, -1); cv2.rectangle(m, (0, rad), (w, h-rad), 255, -1)
    for cx, cy in [(rad, rad), (w-rad, rad), (rad, h-rad), (w-rad, h-rad)]: cv2.circle(m, (cx, cy), rad, 255, -1, cv2.LINE_AA)
    if shadow:
        s = np.zeros((H, W), np.float32); cv2.rectangle(s, (x+10, y+24), (x+w+10, y+h+24), 1, -1); s = cv2.GaussianBlur(s, (0, 0), 26) * .32 * alpha
        f = (f * (1 - s[..., None])).astype(np.uint8)
    return mm.blend(f, np.dstack([img, m]), x, y, alpha)

# ---------- субтитры: зелёная плашка, крем, золотая черта ----------
SUBS = {'s01': ['Мебел олмоқчисиз...', 'лекин нархи қимматми?'], 's02': ['Сабаби оддий:', 'ўртакаш ўз устамасини қўшади.'],
        's03': ['«Шодиёна мебел» —', 'Андижондаги ишлаб чиқарувчи.', 'Беш йилдан бери — ўз цехимизда.'],
        's04': ['Металл каркасдан юмшоқ қопламагача —', 'ҳаммасини ўзимиз тайёрлаймиз.'],
        's05': ['Ошхона, уй, мактаб, тиббиёт ва офис учун —', 'буюртма асосида, хоҳлаган ўлчамда.'],
        's06': ['Дизайн хизмати — мутлақо бепул.'], 's07': ['Заводдан нархда — воситачисиз.'],
        's08': ['Буюртма учун — Телеграм ботимизга', 'ёзинг ёки қўнғироқ қилинг.']}
def sub_chunks():
    out = []
    for k, parts in SUBS.items():
        a, b = P[k]; ws = TM['W'][k]; n = len(parts)
        # граница кусков — по словам: делим слова пропорционально числу слов в кусках
        cnt = [len(p.split()) for p in parts]; idx = 0; starts = []
        real = [w for w in ws if w[0] not in ('—', '...')]
        for c in cnt: starts.append(real[min(idx, len(real)-1)][1]); idx += c
        for i, p in enumerate(parts):
            s = starts[i]; e = starts[i+1] - 0.05 if i+1 < n else b + 0.25
            out.append((s - 0.08, e, p))
    return out
SUB = sub_chunks(); FS = F('Inter-Bold.otf', 46)
def sub_layer(t, Ly):
    for a, b, s in SUB:
        if a <= t < b:
            al = min(1, (t-a)/0.12, (b-t)/0.12); d = ImageDraw.Draw(Ly)
            words = s.split(); lines = []; cur = ''
            for w_ in words:
                if d.textlength(cur + ' ' + w_, font=FS) > 860 and cur: lines.append(cur); cur = w_
                else: cur = (cur + ' ' + w_).strip()
            lines.append(cur); lh = 60
            tw = max(d.textlength(l, font=FS) for l in lines); bw, bh = tw + 80, lh*len(lines) + 34
            x0, y0 = (W - bw)/2, 1505 - bh
            d.rounded_rectangle([x0, y0, x0+bw, y0+bh], 18, fill=GREEN + (int(236*al),))
            d.rectangle([x0+20, y0+20, x0+25, y0+bh-20], fill=OAK + (int(255*al),))
            y = y0 + 14
            for l in lines:
                w_ = d.textlength(l, font=FS); d.text((x0+42+(tw-w_)/2, y), l, font=FS, fill=CREAM + (int(255*al),)); y += lh
    return Ly

# ================= СЦЕНЫ =================
T = lambda k, i=0: P[k][i]
def word(k, w):
    for s, t in TM['W'][k]:
        if s.lower().startswith(w): return t
    raise KeyError(w)
FB = F('InterDisplay-Black.otf', 120); FB2 = F('InterDisplay-Black.otf', 92); FX = F('InterDisplay-ExtraBold.otf', 58); FM = F('Inter-Bold.otf', 40)

def sc_hook(t):  # 0 → s02 start
    f = BG.copy(); k = spring((t - 0.25) / 0.9)
    ch = prod('p13', 560); by = 1230 - int(260 * (1 - k)) if k < 1 else 1230
    f = put(f, ch, W/2 + 30, 1040 - (1 - min(1, k)) * 380, min(1, k*1.5))
    Ly = L(); d = ImageDraw.Draw(Ly)
    a1 = eo((t - 0.6) / 0.4); ctext(d, 300 + 30*(1-a1), 'МЕБЕЛ', FX, WAL, int(255*a1), track=8)
    a2 = eo((t - 1.1) / 0.4); ctext(d, 370 + 30*(1-a2), 'ОЛМОҚЧИМИСИЗ?', FX, WAL, int(255*a2), track=4)
    tq = word('s01', 'нархи')
    if t > tq - 0.1:
        q = spring((t - tq + 0.1) / 0.6); sc = max(0.01, q)
        Lb = L(); db = ImageDraw.Draw(Lb); ctext(db, 1060, 'НАРХИ', FB, GREEN); ctext(db, 1195, 'ҚИММАТМИ?', FB2, GREEN)
        arr = np.array(Lb); M = cv2.getRotationMatrix2D((W/2, 1200), 0, sc); arr = cv2.warpAffine(arr, M, (W, H))
        Ly = Image.alpha_composite(Ly, Image.fromarray(arr))
        # ценник «???» качается
        d = ImageDraw.Draw(Ly); ang = 14 * np.sin((t - tq) * 5) * np.exp(-(t - tq) * 1.2)
        tag = Image.new('RGBA', (300, 170), (0, 0, 0, 0)); dt = ImageDraw.Draw(tag)
        dt.polygon([(40, 0), (300, 0), (300, 170), (40, 170), (0, 85)], fill=OAK + (255,)); dt.ellipse([22, 74, 40, 92], fill=CREAM + (255,))
        tw = dt.textlength('???', font=FB2); dt.text((60 + (240 - tw)/2, 22), '???', font=FB2, fill=CREAM + (255,))
        tag = tag.rotate(ang, resample=Image.BICUBIC, expand=True, center=(31, 83)); a = min(1, (t - tq) / 0.25)
        tag.putalpha(tag.getchannel('A').point(lambda v: int(v * a))); Ly.alpha_composite(tag, (700, 520))
    f = over(f, Ly)
    return cam(f, 1.0 + 0.035 * t / 5, W/2, 900, 0.4 * np.sin(t * .6))

def node(d, y, title, sub, a, x_off=0, col=GREEN, txt=CREAM):
    bw, bh = 640, 170; x0 = (W - bw)/2 + x_off
    d.rounded_rectangle([x0, y, x0+bw, y+bh], 26, fill=col + (int(255*a),))
    tw = d.textlength(title, font=FX); d.text((x0 + (bw-tw)/2, y + 30), title, font=FX, fill=txt + (int(255*a),))
    if sub: tw = d.textlength(sub, font=FM); d.text((x0 + (bw-tw)/2, y + 104), sub, font=FM, fill=txt + (int(200*a),))
def arrow(d, y0, y1, a):
    d.line([(W/2, y0), (W/2, y0 + (y1-y0)*a)], fill=WAL + (255,), width=8)
    if a > .95: d.polygon([(W/2-22, y1-26), (W/2+22, y1-26), (W/2, y1+4)], fill=WAL + (255,))
def chain(t, t0, mode):
    """mode a: завод → ўртакаш(+устама) → сиз;  mode b: ўртакаш вычёркивается"""
    f = BG.copy(); Ly = L(); d = ImageDraw.Draw(Ly)
    a1 = eo((t - t0) / .4); node(d, 330, 'ЗАВОД', 'ишлаб чиқарувчи', a1, 120*(1-a1))
    if mode == 'a':
        tm = word('s02', "o'rtakash") - 0.15; arrow(d, 510, 650, eo((t - t0 - .3) / .4))
        a2 = eo((t - tm) / .4); node(d, 660, 'ЎРТАКАШ', 'воситачи', a2, 300*(1-a2), col=(214, 205, 190), txt=GREEN)
        arrow(d, 840, 980, eo((t - tm - .3) / .4))
        a3 = eo((t - tm - .5) / .4); node(d, 990, 'СИЗ', 'харидор', a3, 120*(1-a3))
        tu = word('s02', 'устамасини')
        if t > tu - .1:  # штамп «+ УСТАМА»
            q = spring((t - tu + .1) / .5); st = Image.new('RGBA', (430, 120), (0, 0, 0, 0)); ds = ImageDraw.Draw(st)
            ds.rounded_rectangle([0, 0, 429, 119], 18, fill=OAK + (255,)); tw = ds.textlength('+ УСТАМА', font=FX); ds.text(((430-tw)/2, 24), '+ УСТАМА', font=FX, fill=CREAM + (255,))
            st = st.rotate(-8, expand=True, resample=Image.BICUBIC); s = max(.05, q); st = st.resize((int(st.width*s), int(st.height*s)))
            Ly.alpha_composite(st, (int(760 - st.width/2), int(640 - st.height/2)))
            # цена у «СИЗ» растёт
            g = eo((t - tu) / .8); ctext(d, 1185, 'НАРХ ↑' if g > .3 else '', FX, (176, 70, 50), int(255*g))
        return over(f, Ly)
    # mode b — колбэк «воситачисиз»
    tm = t0 + .2; arrow(d, 510, 980, eo((t - t0 - .2) / .5))
    a3 = eo((t - t0 - .4) / .4); node(d, 990, 'СИЗ', 'харидор', a3, 120*(1-a3))
    cut = word('s07', 'воситачисиз')
    fall = ez((t - cut) / .6) if t > cut else 0
    mid = Image.new('RGBA', (W, 200), (0, 0, 0, 0)); dm = ImageDraw.Draw(mid); node(dm, 10, 'ЎРТАКАШ', 'воситачи', 1, col=(214, 205, 190), txt=GREEN)
    if t > cut - .5:
        c = eo((t - cut + .5) / .4); dm.line([(220, 30), (220 + 640*c, 170)], fill=(176, 70, 50, 255), width=14); dm.line([(860, 30), (860 - 640*c, 30 + 140*c)], fill=(176, 70, 50, 255), width=14)
    mid = mid.rotate(-25*fall, expand=False, resample=Image.BICUBIC); ma = mid.getchannel('A').point(lambda v: int(v*(1-fall)))
    mid.putalpha(ma); Ly.alpha_composite(mid, (int(500*fall), int(650 + 600*fall)))
    tz = word('s07', 'заводдан'); az = eo((t - tz) / .4)
    if az > 0: ctext(d, 200 + 20*(1-az), 'ЗАВОДДАН НАРХДА', FX, GREEN, int(255*az), track=3)
    if t > cut + .15:
        q = spring((t - cut - .15) / .55); st = Image.new('RGBA', (820, 150), (0, 0, 0, 0)); ds = ImageDraw.Draw(st)
        ds.rounded_rectangle([0, 0, 819, 149], 22, fill=GREEN + (255,)); tw = ds.textlength('ВОСИТАЧИСИЗ', font=FB2); ds.text(((820-tw)/2, 16), 'ВОСИТАЧИСИЗ', font=FB2, fill=CREAM + (255,))
        st = st.rotate(4, expand=True, resample=Image.BICUBIC); s = max(.05, q); st = st.resize((int(st.width*s), int(st.height*s)))
        Ly.alpha_composite(st, (int(W/2 - st.width/2), int(720 - st.height/2)))
    return over(f, Ly)

def sc_chain(t): f = chain(t, P['s02'][0] - .3, 'a'); return cam(f, 1.0 + .03 * (t - P['s02'][0]) / 5, W/2, 800)

def shtorka(f, q):  # зелёная шторка снизу вверх со знаком; q 0..1..2
    if q <= 0 or q >= 2: return f
    y = int(H * (1 - ez(q))) if q < 1 else 0; y1 = H if q < 1 else int(H * (1 - ez(q - 1)))
    g = f.copy(); g[y:y1] = bgr(GREEN)
    ic = cv2.resize(ICONC, (300, int(300 * ICONC.shape[0] / ICONC.shape[1])))
    a = 1 - abs(q - 1) * 2.2
    if a > 0: g = mm.blend(g, ic, (W-300)//2, (H-ic.shape[0])//2, min(1, a))
    return g

def sc_about(t):  # s03: логотип, карточка цеха, «5 ЙИЛ»
    t0 = P['s03'][0] - .7; lt = t - t0; f = BG.copy()
    lg = cv2.resize(LOGO, (520, int(520 * LOGO.shape[0] / LOGO.shape[1]))); a = eo((lt - .5) / .5)
    f = mm.blend(f, lg, (W - 520)//2, 250 + int(30*(1-a)), a)
    t5 = word('s03', 'беш') - .1
    n, aa = (45, 9.0) if t < t5 else (32, 2.0)
    fr = clipf(n, aa, 4, (960, 540), t - (t0 if t < t5 else t5))
    ka = eo((lt - .9) / .5); f = rounded_paste(f, cv2.resize(fr, (900, 506), interpolation=cv2.INTER_AREA), 90, 700 + int(80*(1-ka)), 30, ka)
    Ly = L(); d = ImageDraw.Draw(Ly)
    tA = word('s03', 'андижондаги'); a2 = eo((t - tA) / .4)
    if t < t5: ctext(d, 1250 + 20*(1-a2), 'АНДИЖОН · ИШЛАБ ЧИҚАРУВЧИ', FM, WAL, int(255*a2), track=2)
    else:
        q = spring((t - t5) / .6); nn = 1 + int(min(1, (t - t5) / .7) * 4)
        Lb = L(); db = ImageDraw.Draw(Lb); ctext(db, 1225, f'{nn} ЙИЛ', FB, GREEN); arr = np.array(Lb)
        M = cv2.getRotationMatrix2D((W/2, 1290), 0, max(.05, q)); Ly = Image.alpha_composite(Ly, Image.fromarray(cv2.warpAffine(arr, M, (W, H))))
    f = over(f, Ly); f = cam(f, 1.0 + .03 * lt / 7, W/2, 1000)
    return shtorka(f, 1 + lt / .55) if lt < .55 else f

STRIPS = [(27, 1.0, 'МЕТАЛЛ КАРКАС', 's04', 'металл'), (38, 1.5, 'ЮМШОҚ ҚОПЛАМА', 's04', 'юмшоқ'), (45, 9.5, 'ЎЗ ЦЕХИМИЗДА', 's04', 'ҳаммасини')]
def sc_strips(t):
    t0 = P['s04'][0] - .6; lt = t - t0; f = np.zeros((H, W, 3), np.uint8); f[:] = 12
    Ly = L(); d = ImageDraw.Draw(Ly)
    for j, (n, a, lab, k, w_) in enumerate(STRIPS):
        y = 220 + j * 390; kk = eo((lt - .12 * j) / .45)
        if kk <= 0: continue
        fr = clipf(n, a, 7, (W, 370), lt, .5); dx = int((1 - kk) * W * (1 if j % 2 == 0 else -1))
        X0, X1 = max(0, dx), min(W, W + dx); f[y:y+370, X0:X1] = fr[:, X0-dx:X1-dx]
        tw_ = word(k, w_); q = eo((t - tw_) / .35)
        if q > 0:
            bw = d.textlength(lab, font=FX) + 70; x0 = 40 - 60*(1-q)
            d.rounded_rectangle([x0, y + 20, x0 + bw, y + 100], 14, fill=GREEN + (int(240*q),)); d.rectangle([x0 + 16, y + 36, x0 + 21, y + 84], fill=OAK + (int(255*q),))
            d.text((x0 + 38, y + 28), lab, font=FX, fill=CREAM + (int(255*q),))
    return over(f, Ly)

CATS = [('ОШХОНА', 'p14', 'ошхона'), ('УЙ', 'p01', 'уй'), ('ТАЪЛИМ', 'p35', 'мактаб'), ('ТИББИЁТ', 44, 'тиббиёт'), ('ОФИС', 28, 'офис')]
FCAT = F('InterDisplay-Black.otf', 230)
def cat_page(t, i, ts, te):
    cat, key, _ = CATS[i]; lt = t - ts; f = BG.copy()
    Lc = L(); d = ImageDraw.Draw(Lc); fn = FCAT; tw = d.textlength(cat, font=fn)
    if tw > W * .92: fn = F('InterDisplay-Black.otf', int(230 * W * .92 / tw)); tw = d.textlength(cat, font=fn)
    k = eo(lt / .35); x = (W - tw)/2 + 140*(1-k) - 40*lt
    d.text((x, 330), cat, font=fn, fill=(0, 0, 0, 0), stroke_width=4, stroke_fill=OAK + (int(200*k),))
    f = over(f, Lc)
    p = prod(key, 640 if key not in ('p14', 'p01') else 520)
    if p.shape[1] > 900: p = cv2.resize(p, (900, int(p.shape[0] * 900 / p.shape[1])), interpolation=cv2.INTER_AREA)
    k2 = spring((lt - .05) / .55)
    f = put(f, p, W/2 + 15*lt, 1270 - 90*(1 - min(1, k2)), min(1, k2*1.4))
    return f
def sc_cats(t):
    ts = [word('s05', c[2]) - .12 for c in CATS] + [word('s05', 'буюртма') - .12]
    for i in range(len(CATS)):
        if t < ts[i+1]:
            f = cat_page(t, i, ts[i], ts[i+1])
            if i > 0 and t - ts[i] < .18:  # толчок влево
                pv = cat_page(ts[i] - .01, i-1, ts[i-1], ts[i]); q = ez((t - ts[i]) / .18); sh = int(W*q)
                out = f.copy(); out[:, :W-sh] = pv[:, sh:]; out[:, W-sh:] = f[:, :sh]; f = out
            return cam(f, 1.0 + .02 * (t - ts[0]) / 4, W/2, 1000)
    # «буюртма асосида, хоҳлаган ўлчамда» — стеллаж и размерные стрелки
    lt = t - ts[-1]; f = BGG.copy(); p = prod('p41', 760); h, w = p.shape[:2]
    pv = cat_page(ts[-1] - .01, 4, ts[-2], ts[-1])
    f = put(f, p, W/2, 1300, 1.0)
    Ly = L(); d = ImageDraw.Draw(Ly); col = GREEN + (255,)
    tw2 = word('s05', 'хоҳлаган') - .1; g = eo((t - tw2) / .5); ext = 50 + 60*np.sin(max(0, t - tw2) * 3) * g
    x0, x1, y0, y1 = W/2 - w/2 - ext*.6, W/2 + w/2 + ext*.6, 1300 - h - ext*.4, 1300
    yb = 1335; d.line([(x0, yb), (x1, yb)], fill=col, width=4); [d.line([(x, yb-14), (x, yb+14)], fill=col, width=4) for x in (x0, x1)]
    xr = min(W - 170, x1 + 30); d.line([(xr, y0), (xr, y1)], fill=col, width=4); [d.line([(xr-14, y), (xr+14, y)], fill=col, width=4) for y in (y0, y1)]
    a = eo(lt / .4); ctext(d, 280 + 20*(1-a), 'БУЮРТМА АСОСИДА', FX, GREEN, int(255*a), track=3)
    if g > 0: ctext(d, 350 + 20*(1-g), 'ЎЛЧАМ — СИЗДАН', FX, OAK, int(255*g), track=3)
    f = over(f, Ly)
    if lt < .18:
        q = ez(lt / .18); sh = int(W*q); out = f.copy(); out[:, :W-sh] = pv[:, sh:]; out[:, W-sh:] = f[:, :sh]; f = out
    return cam(f, 1.0 + .03 * lt / 3, W/2, 1000)

_BP = []
def sc_design(t):
    t0 = P['s06'][0] - .5; lt = t - t0
    if not _BP: _BP.append(mm.Blueprint(PH % 13, '', '', hgt=680, cx=W//2))
    bp = _BP[0]; f = bp.frame(min(3.3, 0.55 + lt * 1.0), 6)
    Ly = L(); d = ImageDraw.Draw(Ly)
    a = eo((lt - .2) / .4); ctext(d, 280 + 20*(1-a), 'ДИЗАЙН', FB, GREEN, int(255*a), track=6)
    tb = word('s06', 'бепул')
    if t > tb - .1:
        q = spring((t - tb + .1) / .55); st = Image.new('RGBA', (640, 170), (0, 0, 0, 0)); ds = ImageDraw.Draw(st)
        ds.rounded_rectangle([0, 0, 639, 169], 26, fill=OAK + (255,)); tw = ds.textlength('БЕПУЛ', font=FB); ds.text(((640-tw)/2, 14), 'БЕПУЛ', font=FB, fill=CREAM + (255,))
        st = st.rotate(-6, expand=True, resample=Image.BICUBIC); s = max(.05, q); st = st.resize((int(st.width*s), int(st.height*s)))
        Ly.alpha_composite(st, (int(W/2 - st.width/2), int(1230 - st.height/2)))
    return over(f, Ly)

def sc_chain2(t): f = chain(t, P['s07'][0] - .4, 'b'); return cam(f, 1.0 + .03 * (t - P['s07'][0]) / 4, W/2, 800)

FPH = F('InterDisplay-Black.otf', 96)
def sc_final(t):
    t0 = P['s08'][0] - .5; lt = t - t0; f = BG.copy()
    # ряд изделий снизу (параллакс)
    for j, (key, x) in enumerate([('p13', 165), ('p35', 415), ('p41', 665), ('p14', 905)]):
        p = prod(key, 170)
        if p.shape[1] > 220: p = cv2.resize(p, (220, int(p.shape[0] * 220 / p.shape[1])), interpolation=cv2.INTER_AREA)
        k = eo((lt - .1*j) / .5); f = put(f, p, x - 20*lt*(1 if j % 2 else -1)*.3, 1300 + 60*(1-k), k * .95)
    lg = cv2.resize(LOGO, (440, int(440 * LOGO.shape[0] / LOGO.shape[1]))); a = eo(lt / .5)
    f = mm.blend(f, lg, (W-440)//2, 250, a)
    Ly = L(); d = ImageDraw.Draw(Ly)
    tb = word('s08', 'телеграм') - .1; q = eo((t - tb) / .4)
    if q > 0:
        bw, bh = 820, 120; x0 = (W - bw)/2; y = 690 + 30*(1-q)
        d.rounded_rectangle([x0, y, x0+bw, y+bh], 60, fill=GREEN + (int(255*q),))
        tw = d.textlength('@ShodiyonaMebelUzBot', font=FX); d.text(((W-tw)/2, y + 26), '@ShodiyonaMebelUzBot', font=FX, fill=CREAM + (int(255*q),))
        ctext(d, y - 64, 'TELEGRAM-БОТ', FM, WAL, int(255*q), track=6)
    tp = word('s08', "qo'ng'iroq") - .15; q2 = spring((t - tp) / .6)
    if t > tp:
        Lb = L(); db = ImageDraw.Draw(Lb); ctext(db, 940, '+998 77 923 01 91', FPH, GREEN); ctext(db, 1060, 'БУЮРТМАЛАР ШУ РАҚАМ ОРҚАЛИ', FM, WAL, track=3)
        arr = np.array(Lb); M = cv2.getRotationMatrix2D((W/2, 1010), 0, max(.05, q2)); Ly = Image.alpha_composite(Ly, Image.fromarray(cv2.warpAffine(arr, M, (W, H))))
    f = over(f, Ly)
    return cam(f, 1.0 + .025 * lt / 8, W/2, 900)

SCENES = [(P['s02'][0] - .3, sc_hook), (P['s03'][0] - .7, sc_chain), (P['s04'][0] - .6, sc_about), (P['s05'][0] - .25, sc_strips),
          (P['s06'][0] - .5, sc_cats), (P['s07'][0] - .4, sc_design), (P['s08'][0] - .5, sc_chain2), (99, sc_final)]
def frame(t):
    for end, fn in SCENES:
        if t < end: f = fn(t); break
    Ly = sub_layer(t, L())
    f = over(f, Ly)
    if t > TOTAL - .5: f = cv2.addWeighted(f, 1, np.full_like(f, 255), (t - (TOTAL - .5)) / .5 * 0, 0)
    return f

if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'stills':
        ts = [float(x) for x in sys.argv[2].split(',')]
        ims = [cv2.resize(frame(t), (360, 640)) for t in ts]
        for i, t in enumerate(ts): cv2.putText(ims[i], f'{t:.1f}', (8, 30), 0, .9, (0, 0, 255), 2)
        while len(ims) % 6: ims.append(np.zeros_like(ims[0]))
        cv2.imwrite(sys.argv[3], np.vstack([np.hstack(ims[i:i+6]) for i in range(0, len(ims), 6)]))
    else:
        t0, t1, out = float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                               '-c:v', 'libx264', '-crf', '16', '-preset', 'medium', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
        for n in range(int(round(t0*FPS)), int(round(t1*FPS))): ff.stdin.write(np.ascontiguousarray(frame(n/FPS)).tobytes())
        ff.stdin.close(); ff.wait(); print('ok', out)
