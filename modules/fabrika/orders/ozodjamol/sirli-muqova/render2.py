"""«Сирли муқова» — KATTA DAVRA. Бумажная диорама (по приёму @birfoiz_). 9:16, 30 fps."""
import numpy as np, cv2, json, subprocess, sys, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
K = '/home/claude/k/'
F = K + 'fonts/'
TABLE_Y = 1240
RED = (255, 16, 36, 255)

def font(name, size, var=b'Black'):
    f = ImageFont.truetype(F + name, size)
    try: f.set_variation_by_name(var)
    except Exception: pass
    return f

def ease_back(t, s=1.7):
    t = min(max(t, 0), 1); t -= 1
    return t*t*((s+1)*t + s) + 1
def ease_io(t):
    t = min(max(t, 0), 1); return t*t*(3-2*t)
def ease_out(t):
    t = min(max(t, 0), 1); return 1-(1-t)**3

# ---------- материал ----------
COVER4 = Image.open(K + 'cover4x.png').convert('RGB')   # 4x Real-ESRGAN
def crop4(b): return COVER4.crop(tuple(v*4 for v in b))

def paper(img, border=10, alpha_thr=110):
    img = img.convert('RGBA')
    al = np.array(img)[:, :, 3]
    bb = Image.fromarray(((al > alpha_thr)*255).astype(np.uint8)).getbbox()
    img = img.crop(bb)
    pad = border*3
    c = Image.new('RGBA', (img.width+2*pad, img.height+2*pad), (0, 0, 0, 0))
    c.paste(img, (pad, pad), img)
    src = np.array(c)
    a = (src[:, :, 3] > alpha_thr).astype(np.uint8)*255
    n, lab, st, _ = cv2.connectedComponentsWithStats(a)
    if n > 2:
        mx = st[1:, cv2.CC_STAT_AREA].max()
        a = np.isin(lab, [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 0.04*mx]).astype(np.uint8)*255
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (border*2+1, border*2+1))
    big = cv2.GaussianBlur(cv2.dilate(a, k), (5, 5), 0)
    out = np.zeros_like(src); out[:, :, :3] = (246, 243, 236); out[:, :, 3] = big
    edge = cv2.dilate(big, np.ones((3, 3), np.uint8)) - big
    out[edge > 40, :3] = (165, 160, 152); out[edge > 40, 3] = 255
    base = Image.fromarray(out)
    src[:, :, 3] = np.where(a > 0, src[:, :, 3], 0)
    base.alpha_composite(Image.fromarray(src))
    return base

def shaped(img, shape, r=40):
    w, h = img.size
    m = Image.new('L', (w, h), 0); d = ImageDraw.Draw(m)
    if shape == 'circle': d.ellipse((0, 0, w-1, h-1), fill=255)
    elif shape == 'arch':
        rr = w//2; d.rectangle((0, rr, w, h), fill=255); d.ellipse((0, 0, w, 2*rr), fill=255)
    else: d.rounded_rectangle((0, 0, w-1, h-1), radius=r, fill=255)
    o = img.convert('RGBA'); o.putalpha(m); return o

def fitw(img, w):
    return img.resize((int(w), int(img.height*w/img.width)), Image.LANCZOS)

def card(box, shape='rect', w=500, border=14, r=60):
    return paper(shaped(fitw(crop4(box), w-2*border*3), shape, r), border)

def seg(name, w, border=11):
    return fitw(paper(Image.open(K + f'cut/{name}.png'), border), w)

# элементы сцен (координаты — исходная обложка 912×1168)
E = {}
E['cover'] = paper(fitw(COVER4, 900), 14)
COVER_SC = 900/912; COVER_PAD = 42
E['arch'] = card((372, 343, 545, 478), 'arch', 560)
E['crown'] = seg('crown', 300)
E['angL'] = seg('angelL', 400); E['angR'] = seg('angelR', 400)
E['people'] = card((300, 560, 600, 760), 'rect', 600, r=50)
E['horse'] = card((540, 655, 765, 765), 'rect', 760, r=50)
E['moon'] = card((776, 626, 836, 690), 'circle', 300)
E['hour'] = card((794, 706, 848, 806), 'rect', 250, r=30)
E['flags'] = card((238, 792, 352, 892), 'rect', 560, r=40)
E['tank'] = card((145, 875, 275, 945), 'rect', 480, r=40)
E['smoke'] = card((25, 690, 160, 835), 'rect', 360, r=40)
E['ai'] = card((622, 855, 765, 955), 'rect', 560, r=40)
E['cams'] = card((695, 815, 795, 875), 'rect', 360, r=34)
E['money'] = card((575, 800, 700, 885), 'rect', 380, r=34)
E['btc'] = card((628, 958, 684, 1012), 'circle', 260)
E['crowd'] = card((225, 935, 615, 1050), 'rect', 900, r=50)
E['earth'] = card((235, 1040, 700, 1135), 'rect', 940, r=50)

def tag(text, size=60, dark=True):
    f = font('Montserrat.ttf', size)
    bb = f.getbbox(text); tw, th = bb[2]-bb[0], bb[3]-bb[1]
    px, py = int(size*0.55), int(size*0.36)
    im = Image.new('RGBA', (tw+2*px, th+2*py+8), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, im.width-1, im.height-1), fill=(18, 18, 18, 255) if dark else (246, 243, 236, 255))
    d.text((px-bb[0], py-bb[1]), text, font=f, fill=(255, 255, 255, 255) if dark else (18, 18, 18, 255))
    d.rectangle((0, im.height-8, im.width, im.height), fill=RED)
    return im

def sign():   # табличка-вопрос как у Каримова (бумага, серифный жирный)
    w, h = 960, 500
    im = Image.new('RGBA', (w, h), (246, 243, 236, 255)); d = ImageDraw.Draw(im)
    f1 = font('PlayfairDisplay.ttf', 56, b'Bold') ; f2 = font('PlayfairDisplay.ttf', 80, b'Black')
    def ctr(t, f, y, fill):
        bb = f.getbbox(t); d.text(((w-(bb[2]-bb[0]))/2-bb[0], y), t, font=f, fill=fill)
    ctr('Ростини айтинг:', f1, 60, (60, 55, 50))
    ctr('Сиз бунга', f2, 165, (18, 18, 18)); ctr('ишонганмидингиз?', f2, 290, (18, 18, 18))
    d.rectangle((0, 0, w-1, h-1), outline=(190, 184, 175), width=3)
    return paper(im, 12)

def frame_card():  # пустая рамка «ҳақиқий муқова»
    w, h = 620, 800
    im = Image.new('RGBA', (w, h), (246, 243, 236, 255)); d = ImageDraw.Draw(im)
    d.rectangle((30, 30, w-30, h-30), outline=(18, 18, 18), width=6)
    f = font('PlayfairDisplay.ttf', 380); bb = f.getbbox('?')
    d.text(((w-(bb[2]-bb[0]))/2-bb[0], (h-(bb[3]-bb[1]))/2-bb[1]), '?', font=f, fill=(255, 16, 36))
    f2 = font('Montserrat.ttf', 64); t = '2027'; bb = f2.getbbox(t)
    d.text(((w-(bb[2]-bb[0]))/2-bb[0], 70), t, font=f2, fill=(18, 18, 18))
    return paper(im, 12)

def stamp():
    f = font('Montserrat.ttf', 190); t = 'СОХТА'; bb = f.getbbox(t)
    w, h = bb[2]-bb[0]+120, bb[3]-bb[1]+110
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((8, 8, w-8, h-8), radius=26, outline=(225, 14, 32, 255), width=16)
    d.text((60-bb[0], 55-bb[1]), t, font=f, fill=(225, 14, 32, 255))
    a = np.array(im); rng = np.random.default_rng(7)   # чернильная фактура штампа
    holes = rng.random(a.shape[:2]) < 0.10
    holes = cv2.GaussianBlur(holes.astype(np.float32), (0, 0), 1.6) > 0.16
    a[:, :, 3] = np.where(holes, (a[:, :, 3]*0.25).astype(np.uint8), a[:, :, 3])
    return Image.fromarray(a).rotate(-9, expand=True, resample=Image.BICUBIC)

E['sign'] = sign(); E['frame'] = frame_card(); STAMP = stamp()

# ---------- фон ----------
def make_bg():
    y = np.arange(H)[:, None]; x = np.arange(W)[None, :]
    bg = np.zeros((H, W, 3), np.float32)
    back = np.array([30, 28, 30], np.float32); table = np.array([236, 231, 222], np.float32)
    g = np.clip((y-TABLE_Y+40)/80.0, 0, 1)[..., None]
    bg[:] = back*(1-g) + table*g
    glow = np.exp(-(((x-W/2)/(W*0.45))**2 + ((y-700)/(H*0.22))**2))[..., None]
    bg += glow*np.array([60, 6, 12], np.float32)
    d = np.sqrt(((x-W/2)/(W*0.62))**2 + ((y-1050)/(H*0.55))**2)
    bg *= np.clip(1.25-d, 0.18, 1.0)[..., None]
    bg += np.random.default_rng(3).normal(0, 3.0, (H, W, 1))
    return np.clip(bg, 0, 255).astype(np.uint8)
BG = Image.fromarray(make_bg()).convert('RGBA')
DARK = Image.new('RGBA', (W, H), (8, 7, 8, 255))

# ---------- примитивы ----------
def safe_comp(c, im, x, y):
    x0, y0 = max(x, 0), max(y, 0); cx, cy = x0-x, y0-y
    if cx >= im.width or cy >= im.height or x0 >= c.width or y0 >= c.height: return
    c.alpha_composite(im.crop((cx, cy, min(im.width, cx+c.width-x0), min(im.height, cy+c.height-y0))), (x0, y0))

def stand(img, t):
    if t <= 0.012: return None
    hh = max(2, int(img.height*t)); w0 = img.width
    tw = w0*(0.72+0.28*min(t, 1.06)); dx = (w0-tw)/2
    M = cv2.getPerspectiveTransform(np.float32([[0, 0], [w0, 0], [w0, img.height], [0, img.height]]),
                                    np.float32([[dx, 0], [w0-dx, 0], [w0, hh], [0, hh]]))
    a = cv2.warpPerspective(np.array(img), M, (w0, hh), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
    a[:, :, :3] = (a[:, :, :3]*(0.78+0.22*min(t, 1))).astype(np.uint8)
    return Image.fromarray(a)

_SH = {}
def place(c, key, t, fx, fy):
    img = E[key]; im = stand(img, t)
    if im is None: return
    w = img.width
    sh = Image.new('L', (int(w*1.1)+80, 120), 0)
    ImageDraw.Draw(sh).ellipse((40, 30, sh.width-40, 90), fill=int(150*min(t, 1)))
    sh = sh.filter(ImageFilter.GaussianBlur(18))
    lay = Image.new('RGBA', sh.size, (10, 8, 8, 0)); lay.putalpha(sh)
    safe_comp(c, lay, int(fx-sh.width/2), int(fy-60))
    a = np.array(im)[:, :, 3]
    s = Image.fromarray((a*0.42*min(t, 1)).astype(np.uint8)).filter(ImageFilter.GaussianBlur(14))
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0)); lay.putalpha(s)
    x, y = int(fx-w/2), int(fy-im.height)
    safe_comp(c, lay, x+18, y+14); safe_comp(c, im, x, y)

_TAGS = {}
def put_tag(c, text, u, t0, cx, y, size=60, rot=-2.5):
    lt = ease_back((u-t0)/0.4, 2.2)
    if lt <= 0.02: return
    key = (text, size)
    if key not in _TAGS: _TAGS[key] = tag(text, size)
    tg = _TAGS[key]
    tg = tg.resize((max(1, int(tg.width*lt)), max(1, int(tg.height*lt))), Image.LANCZOS).rotate(rot, expand=True, resample=Image.BICUBIC)
    safe_comp(c, tg, int(cx-tg.width/2), int(y))

def camera(c, zoom, dx=0, dy=0):
    w2, h2 = int(W*zoom), int(H*zoom)
    big = c.resize((w2, h2), Image.BILINEAR)
    x0 = int((w2-W)/2+dx); y0 = int((h2-H)/2+dy)
    x0 = min(max(x0, 0), w2-W); y0 = min(max(y0, 0), h2-H)
    return big.crop((x0, y0, x0+W, y0+H))

# ---------- таймлайн из озвучки ----------
TL = json.load(open(K + 'timeline.json'))   # {"starts":[...], "durs":[...], "end": total}
S = TL['starts']; D = TL['durs']

def scene_window(i):
    st = S[i] - (0.25 if i else 0.0)
    en = S[i+1] - 0.25 if i+1 < len(S) else TL['end']
    return st, en

def life(u, t0, dur, fall=0.32, rise=0.7, s=1.7):
    """рост по ease_back с t0, падение в конце сцены"""
    up = ease_back((u-t0)/rise, s)
    down = 1-ease_io((u-(dur-fall))/fall)
    return up*down

def cover_xy(px, py):   # точка исходной обложки → экран (обложка стоит, t=1)
    fx, fy = W/2, TABLE_Y+140
    x = fx - E['cover'].width/2 + COVER_PAD + px*COVER_SC
    y = fy - E['cover'].height + COVER_PAD + py*COVER_SC
    return x, y

def marker(c, px, py, rad, prog, width=7):
    if prog <= 0: return
    x, y = cover_xy(px, py)
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.arc((x-rad*1.15, y-rad, x+rad*1.15, y+rad), start=-100, end=-100+370*min(prog, 1), fill=RED, width=width)
    c.alpha_composite(lay)

SPOTS = [(457, 300, 75), (650, 710, 70), (295, 840, 60), (690, 900, 70), (655, 985, 34), (440, 1000, 80)]

def render(T):
    c = BG.copy(); zoom, dx, dy = 1.0, 0, 0
    i = max([k for k in range(len(S)) if scene_window(k)[0] <= T] or [0])
    st, en = scene_window(i); u = T - st; dur = en - st
    k = ease_io(u/max(dur, 0.1)); off = (S[i]-st)    # off: смещение начала фразы внутри окна
    a = lambda tt: tt + off                          # время слова (от начала фразы) → время сцены

    if i == 0:   # 1. Хук: обложка встаёт, красные круги «ҳар бир расм — бир сир»
        t = life(u, 0.0, dur, rise=1.1, s=1.2)
        place(c, 'cover', 0.3+0.7*t if u < dur-0.32 else t, W/2, TABLE_Y+140)
        if u < dur-0.32:
            for j, (px, py, r) in enumerate(SPOTS[:3]):
                marker(c, px, py, r, ease_out((u-a(3.4)-j*0.25)/0.45))
        zoom = 1.0 + 0.10*ease_io((u-a(5.0))/2.0); dy = -260*ease_io((u-a(5.0))/2.0)
    elif i == 1:  # 2. Верх: арка, корона, люди, ангелы
        place(c, 'arch', life(u, a(0.0), dur), W/2, TABLE_Y+80)
        ct = ease_back((u-a(0.6))/0.7, 1.2)*(1-ease_io((u-(dur-0.32))/0.32))
        if ct > 0:
            land = TABLE_Y+80-E['arch'].height-int(E['crown'].height*0.55)
            safe_comp(c, E['crown'], int(W/2-E['crown'].width/2), int(-E['crown'].height+ct*(land+E['crown'].height)))
        place(c, 'people', life(u, a(2.6), dur), W/2, TABLE_Y+330)
        place(c, 'angL', life(u, a(4.9), dur), 255, TABLE_Y+250)
        place(c, 'angR', life(u, a(5.1), dur), 825, TABLE_Y+250)
        put_tag(c, 'ОХИРЗАМОН?', u if u < dur-0.32 else -9, a(5.7), W/2, 300)
        zoom = 1.04+0.05*k
    elif i == 2:  # 3. Справа: всадники, луна, песочные часы
        place(c, 'moon', life(u, a(2.0), dur), 810, TABLE_Y-40)
        place(c, 'horse', life(u, a(0.9), dur), W/2-40, TABLE_Y+120)
        place(c, 'hour', life(u, a(3.1), dur), 860, TABLE_Y+330)
        put_tag(c, 'ВАҚТ', u if u < dur-0.32 else -9, a(4.15), W/2, 420, 72)
        zoom = 1.04+0.05*k; dx = 40*k
    elif i == 3:  # 4. Низ: флаги, танк, дым
        place(c, 'smoke', life(u, a(3.2), dur), 230, TABLE_Y+40)
        place(c, 'flags', life(u, a(0.9), dur), W/2+60, TABLE_Y+110)
        place(c, 'tank', life(u, a(2.8), dur), 330, TABLE_Y+330)
        put_tag(c, 'АҚШ × ХИТОЙ', u if u < dur-0.32 else -9, a(1.5), W/2+60, 480)
        zoom = 1.04+0.05*k; dx = -40*k
    elif i == 4:  # 5. Технологии: ИИ, камеры, валюты, биткоин
        ok = u < dur-0.32
        place(c, 'money', life(u, a(3.4), dur), 220, TABLE_Y+20)
        place(c, 'cams', life(u, a(1.3), dur), 870, TABLE_Y+20)
        place(c, 'ai', life(u, a(0.0), dur), W/2, TABLE_Y+170)
        place(c, 'btc', life(u, a(5.2), dur), 760, TABLE_Y+380)
        put_tag(c, 'ИИ', u if ok else -9, a(0.4), W/2, 560, 64)
        put_tag(c, 'КУЗАТУВ', u if ok else -9, a(1.5), 870, 820, 44, 2)
        put_tag(c, '$ € ¥ ↓', u if ok else -9, a(3.6), 220, 780, 48)
        put_tag(c, 'BITCOIN', u if ok else -9, a(5.4), 760, 1290, 48, 2)
        zoom = 1.04+0.05*k
    elif i == 5:  # 6. Самый низ: земля, толпа
        place(c, 'earth', life(u, a(0.0), dur)*0.45, W/2, TABLE_Y+420)
        place(c, 'crowd', life(u, a(0.5), dur), W/2, TABLE_Y+200)
        put_tag(c, 'ВАҲИМА', u if u < dur-0.32 else -9, a(2.3), W/2, 640, 72)
        zoom = 1.04+0.06*k
    elif i == 6:  # 7. Обложка снова целиком, круги по всем деталям, «ким чизган?»
        place(c, 'cover', life(u, a(0.0), dur+5, rise=0.9, s=1.3), W/2, TABLE_Y+140)
        for j, (px, py, r) in enumerate(SPOTS):
            marker(c, px, py, r, ease_out((u-a(0.6)-j*0.18)/0.35))
        put_tag(c, 'КИМ ЧИЗГАН?', u, a(4.25), W/2, 1560, 70, 1.5)
        zoom = 1.0+0.06*ease_io((u-a(2.2))/3.0)
        dim = int(150*ease_io((u-a(2.2))/2.0))
    elif i == 7:  # 8. Разоблачение: шапка зачёркнута, штамп СОХТА, «манбани текширинг»
        place(c, 'cover', 1.0, W/2, TABLE_Y+140)
        x0, y0 = cover_xy(318, 4); x1, y1 = cover_xy(592, 62)
        p1 = ease_out((u-a(0.85))/0.25); p2 = ease_out((u-a(1.05))/0.25)
        d = ImageDraw.Draw(c)
        for wdt, col in ((26, (246, 243, 236)), (14, (18, 18, 18))):
            if p1 > 0: d.line((x0, y0, x0+(x1-x0)*p1, y0+(y1-y0)*p1), fill=col, width=wdt)
            if p2 > 0: d.line((x1, y0, x1-(x1-x0)*p2, y0+(y1-y0)*p2), fill=col, width=wdt)
        sp = (u-a(3.62))/0.22
        if sp > 0:
            s = 1.0 + 1.3*(1-ease_out(sp)); stp = STAMP.resize((int(STAMP.width*s), int(STAMP.height*s)), Image.LANCZOS)
            al = np.array(stp); al[:, :, 3] = (al[:, :, 3]*min(1, sp*1.6)).astype(np.uint8); stp = Image.fromarray(al)
            cx, cy = cover_xy(456, 560); safe_comp(c, stp, int(cx-stp.width/2), int(cy-stp.height/2))
        put_tag(c, 'МАНБАНИ ТЕКШИРИНГ', u, a(7.35), W/2, 1530, 58, 1.5)
        dim = 150
        shake = (u-a(3.62));
        if 0 < shake < 0.35:
            dx = 14*math.sin(shake*90)*(1-shake/0.35); dy = 10*math.cos(shake*77)*(1-shake/0.35)
        zoom = 1.06
    elif i == 8:  # 9. Крючок: обложка уходит, пустая рамка «2027 — тез кунда»
        ct = 1-ease_io(u/0.5)
        if ct > 0: place(c, 'cover', ct, W/2, TABLE_Y+140)
        place(c, 'frame', life(u, a(0.4), dur), W/2, TABLE_Y+160)
        put_tag(c, '2027 — ТЕЗ КУНДА', u if u < dur-0.32 else -9, a(1.4), W/2, 330, 60)
        put_tag(c, '@kattadavrauz', u if u < dur-0.32 else -9, a(4.5), W/2, 1480, 56, 1.5)
        zoom = 1.04+0.05*k
        dim = int(150*(1-ease_io(u/0.6)))
    else:         # 10. Вопрос-табличка
        place(c, 'sign', life(u, a(0.0), dur+5), W/2, TABLE_Y+120)
        put_tag(c, 'Изоҳда ёзинг', u, a(3.1), W/2, 1450, 60, 1.5)
        zoom = 1.03+0.04*k
    if i in (6, 7, 8) and 'dim' in dir() and dim > 0:
        pass
    out = camera(c, zoom, dx, dy)
    if i in (6, 7, 8):
        dv = locals().get('dim', 0)
        if dv > 0:   # сжатый прожектор: края темнее, обложка в свете
            out.alpha_composite(VIGN[dv])
    if T < 0.35:
        out.alpha_composite(Image.new('RGBA', (W, H), (8, 7, 8, int(255*(1-ease_io(T/0.35))))))
    return out

def make_vign():
    y = np.arange(H)[:, None]; x = np.arange(W)[None, :]
    d = np.clip(np.sqrt(((x-W/2)/(W*0.55))**2 + ((y-900)/(H*0.42))**2) - 0.55, 0, 1)
    out = {}
    for v in range(0, 256, 1):
        a = np.zeros((H, W, 4), np.uint8); a[:, :, 3] = (d*v).astype(np.uint8)
        out[v] = None if v == 0 else a
    return out
_VA = np.clip(np.sqrt(((np.arange(W)[None, :]-W/2)/(W*0.55))**2 + ((np.arange(H)[:, None]-900)/(H*0.42))**2) - 0.55, 0, 1)
class _V(dict):
    def __missing__(self, v):
        a = np.zeros((H, W, 4), np.uint8); a[:, :, 3] = (_VA*v).astype(np.uint8)
        im = Image.fromarray(a); self[v] = im; return im
VIGN = _V()

if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'still':
        for s in map(float, sys.argv[2:]):
            render(s).convert('RGB').save(K + f'f/s_{s:05.1f}.jpg', quality=85)
    else:   # part: out a b
        out, a, b = sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
        p = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                              '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '15', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
        for f in range(a, b):
            p.stdin.write(np.array(render(f/FPS).convert('RGB')).tobytes())
        p.stdin.close(); p.wait()
