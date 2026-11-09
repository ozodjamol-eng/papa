"""LOVE GO минутный живой ролик (~83 c) под ZVUK Cat Walk (aL2.wav)."""
import sys, glob, os
sys.path.insert(0, '/home/claude/lg')
os.chdir('/home/claude/lg')
from v1b import *
os.chdir('/home/claude/lgl')
U = '/mnt/user-data/uploads/'
_fc = {}
_fl = {}
def nframes(c):
    if c not in _fl: _fl[c] = sorted(glob.glob(f'/home/claude/lgl/fr/{c}/*.jpg'))
    return _fl[c]
def src(lt):  # ускорение на входе: 2.2x → 1x за 0.35 c
    if lt < 0.35: return lt + 1.2 * (lt - lt * lt / 0.7)
    return lt + 0.21
def clipf(c, lt, off=0.0, ramp=True, speed=1.0):
    fs = nframes(c)
    s = (src(lt) if ramp else lt) * speed + off
    i = int(clamp(s * FPS, 0, len(fs) - 1))
    k = (c, i)
    if k not in _fc:
        if len(_fc) > 6: _fc.clear()
        _fc[k] = cv2.cvtColor(cv2.imread(fs[i]), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
    return _fc[k].copy()

def photo_whole(name, w=880):
    im = Image.open(U + name + '-image.jpg').convert('RGB')
    h = int(im.height * w / im.width)
    im = im.resize((w, h), Image.LANCZOS)
    a = np.array(im).astype(np.float32) / 255
    b = 12; L = np.ones((h + 2 * b, w + 2 * b, 4), np.float32); L[b:-b, b:-b, :3] = a
    return L

def photo_cover(name):
    im = Image.open(U + name + '-image.jpg').convert('RGB')
    s = max(W / im.width, H / im.height); im = im.resize((int(im.width * s + 1), int(im.height * s + 1)), Image.LANCZOS)
    x = (im.width - W) // 2; y = (im.height - H) // 2
    return np.array(im.crop((x, y, x + W, y + H))).astype(np.float32) / 255

def shade(C, top=0, bot=0):
    if top: g = np.linspace(0.6, 0, top)[:, None, None]; C[:top] *= (1 - g)
    if bot: g = np.linspace(0, 0.6, bot)[:, None, None]; C[H - bot:] *= (1 - g)
    return C

def lab(s): return txt3d(s, 120, 'white', maxw=920)
LABS = {k: lab(k) for k in ['ЭРКАКЛАР', 'БОЛАЛАР', 'ОЁҚ КИЙИМ · СУМКАЛАР', '2-ҚАВАТ', 'АЁЛЛАР БЎЛИМИ', 'ИЧКИ КИЙИМ · ЁТОҚ БУЮМЛАРИ']}
TITLE0 = flat_txt('LOVE GO · ХЎЖАОБОД', 46, (255, 255, 255), BLACK, track=10)
FAC_ADR = photo_cover('e8a62385'); FAC_FAM = photo_cover('5af191a1')
PILLOW = photo_cover('11e0eac1')
PH_MEN = [photo_cover(n) for n in ['16502232', 'f4505d62', '17899604', '1027c547']]
PH_WOM = [photo_cover(n) for n in ['f112b13a', '21a2c56d', '2676956c', 'ea20af73', '39eb937d']]
PH_JNS = [photo_cover(n) for n in ['71cf9579', '35f1a0eb', 'b38aff7b', '31febab6']]
DIRS = [(0, -1), (-1, 0), (0, 1), (1, 0)]  # сверху, слева, снизу, справа

def photo_pass(t, t0, t1, PH):
    n = len(PH); dur = (t1 - t0) / n
    k = int(clamp((t - t0) / dur, 0, n - 1)); lt = t - (t0 + k * dur)
    dx, dy = DIRS[k % 4]
    e = eout(lt / 0.22)
    ox, oy = int(dx * W * (1 - e)), int(dy * H * (1 - e))
    cur = zoom_frame(PH[k], 1.0 + 0.04 * clamp(lt / dur), 0.5)
    prev = zoom_frame(PH[k - 1], 1.04, 0.5) if k > 0 else bg(t)
    C = prev.copy()
    if e < 1:
        M = np.float32([[1, 0, ox], [0, 1, oy]])
        sh = cv2.warpAffine(cur, M, (W, H), borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
        m = cv2.warpAffine(np.ones((H, W), np.float32), M, (W, H))[..., None]
        C = C * (1 - m) + sh * m
        if dx: C = cv2.blur(C, (int(1 + 70 * (1 - e)), 1))
        else: C = cv2.blur(C, (1, int(1 + 70 * (1 - e))))
    else:
        C = cur
    flash(C, 0.8 * clamp(1 - abs(lt - 0.2) / 0.12))
    return C

# сегменты: (t0, t1, функция)
def C_(c, off=0.0, label=None, lab_t=None, dim=1.0, ramp=True, speed=1.0, title=False):
    def f(t, t0):
        C = clipf(c, t - t0, off, ramp, speed)
        if dim < 1: C *= dim
        if label:
            shade(C, 640, 0); place(C, LABS[label], W / 2, 330, spring(t - (lab_t or t0) - 0.05, 0.4))
        if title:
            shade(C, 0, 520); place(C, TITLE0, W / 2, 1480, 1, 0, clamp((t - 0.3) * 3))
        return C
    return f

def ulg(t, t0):
    C = clipf('2923', t - t0, 0, True, 0.8) * 0.55
    place(C, HATTO, W / 2, 640, 1, 0, clamp((t - 61.3) * 4))
    u = t - 63.0
    if u > 0:
        place(C, ULG, W / 2, 850, 1 + 0.8 * (1 - spring(u, 0.45)), 0, clamp(u * 8))
        flash(C, 0.3 * clamp(1 - (u - 0.05) / 0.2) if u > 0.05 else 0)
    if t > 63.5: place(C, NARX, W / 2, 1050 + 300 * (1 - spring(t - 63.5, 0.45)), 1, 0, clamp((t - 63.5) * 8))
    place(C, DONA, W / 2, 1270, spring(t - 63.95, 0.4), -5)
    return C

def ret(t, t0):
    lt = t - t0
    C = (clipf('2937', lt, 0, True, 0.75) if lt < 2.6 else clipf('2910', lt - 2.6, 0, False, 0.9)) * 0.58
    place(C, CHEK, W / 2, 1430, spring(t - 65.1, 0.45))
    place(C, SEV, -300 + (330 + 300) * spring(t - 66.4, 0.5), 760, 1, -6 * (1 - spring(t - 66.4, .5)))
    place(C, KUN, W + 300 - (W + 300 - 730) * spring(t - 66.65, 0.45), 690)
    place(C, ICH, 730, 830, 1, 0, clamp((t - 66.85) * 5))
    place(C, SAB, W / 2, 1110, spring(t - 67.5, 0.4))
    place(C, QAY, W / 2, 1275, spring(t - 68.0, 0.4))
    return C

def ert(t, t0):
    C = zoom_frame(FAC_FAM, 1.0 + 0.02 * (t - t0), 0.6)
    C = np.concatenate([np.repeat(C[:1], 380, 0), C[:H - 380]], 0)
    shade(C, 700, 0)
    place(C, ERT, W / 2, -200 + (330 + 200) * spring(t - 70.2, 0.5))
    place(C, SANA, W / 2, 505, spring(t - 71.1, 0.4))
    return C

def adr1(t, t0):
    C = shade(clipf('2948', t - t0, 0, True, 0.8), 0, 700)
    place(C, ADR, W / 2, 2200 - (2200 - 1470) * spring(t - 74.9, 0.55)); return C

def adr2(t, t0):
    C = shade(zoom_frame(FAC_ADR, 1.0 + 0.02 * (t - t0), 0.35), 0, 700)
    CONF.draw(C, t - 79.5)
    place(C, ADR, W / 2, 1470)
    place(C, KUT1, W / 2, 1250, spring(t - 79.65, 0.4))
    if t > 82.9: C *= clamp(1 - (t - 82.9) / 0.2)
    return C

LOGO = make_logo()
def logo_anim(t, t0):
    C = bg(t); lt = t - t0
    s = 0.85 * spring(lt - 0.05, 0.55) + 0.02 * lt
    place(C, logo_sweep(lt - 0.3), W / 2, H * 0.46, s, -10 * (1 - eout(lt / .5)), clamp(lt * 6))
    flash(C, 0.45 * clamp(1 - (lt - 0.2) / 0.25) if lt > 0.2 else 0)
    if t > 7.6: C *= 1  # 
    return C

def pillow(t, t0):
    lt = t - t0
    C = zoom_frame(PILLOW, 1.0 + 0.03 * lt, 0.5); flash(C, 0.8 * clamp(1 - lt / 0.15)); return C

SEG = [
    (0.0, 2.0, C_('2948', title=True)), (2.0, 4.8, C_('2880', title=True)), (4.8, 6.3, C_('2881', ramp=False)), (6.3, 8.3, logo_anim),
    (8.3, 10.3, C_('2900')), (10.3, 12.4, C_('2936')),
    (12.4, 16.3, lambda t, t0: photo_pass(t, t0, 16.3, PH_MEN)),
    (16.3, 18.4, C_('2938', label='ЭРКАКЛАР')), (18.4, 20.5, C_('2932', label='ЭРКАКЛАР', lab_t=16.3)),
    (20.5, 22.8, C_('2933', label='ЭРКАКЛАР', lab_t=16.3)),
    (22.8, 25.0, C_('2926', label='БОЛАЛАР')), (25.0, 27.2, C_('2892', label='БОЛАЛАР', lab_t=22.8)),
    (27.2, 28.4, C_('2884', label='ОЁҚ КИЙИМ · СУМКАЛАР')), (28.4, 29.4, C_('2888', label='ОЁҚ КИЙИМ · СУМКАЛАР', lab_t=27.2)),
    (29.4, 30.4, C_('2889', label='ОЁҚ КИЙИМ · СУМКАЛАР', lab_t=27.2)),
    (30.4, 32.6, C_('2895', speed=1.3)), (32.6, 34.3, C_('2941')),
    (34.3, 36.3, C_('2896', label='АЁЛЛАР БЎЛИМИ')), (36.3, 38.4, C_('2903')), (38.4, 40.6, C_('2909')),
    (40.6, 42.9, C_('2891')), (42.9, 45.0, C_('2911')), (45.0, 46.6, C_('2925')),
    (46.6, 51.1, lambda t, t0: photo_pass(t, t0, 51.1, PH_WOM)),
    (51.1, 53.4, C_('2898', label='ИЧКИ КИЙИМ · ЁТОҚ БУЮМЛАРИ')), (53.4, 55.2, C_('2899', label='ИЧКИ КИЙИМ · ЁТОҚ БУЮМЛАРИ', lab_t=51.1)),
    (55.2, 56.8, pillow),
    (56.8, 60.3, lambda t, t0: photo_pass(t, t0, 60.3, PH_JNS)),
    (60.3, 65.0, ulg), (65.0, 69.8, ret), (69.8, 74.4, ert), (74.4, 77.0, adr1), (77.0, 83.1, adr2),
]
NOWHIP = {77.0}
D = 83.1
def seg_at(t):
    for s in SEG:
        if s[0] <= t < s[1]: return s
    return SEG[-1]
def R(t):
    for i in range(1, len(SEG)):
        b = SEG[i][0]
        if b not in NOWHIP and abs(t - b) < 0.1:
            a, c = SEG[i - 1], SEG[i]
            return whip(lambda x: a[2](x, a[0]), lambda x: c[2](x, c[0]), t, b, 0.2, -1 if i % 2 else 1)
    s = seg_at(t)
    return s[2](t, s[0])

if __name__ == '__main__':
    if sys.argv[1] == 'sheet':
        ts = [float(x) for x in sys.argv[2].split(',')]
        ims = [Image.fromarray((np.clip(R(t), 0, 1) * 255).astype(np.uint8)).resize((180, 320)) for t in ts]
        sh = Image.new('RGB', (180 * min(12, len(ims)), 320 * ((len(ims) + 11) // 12)))
        for k, im in enumerate(ims): sh.paste(im, ((k % 12) * 180, (k // 12) * 320))
        sh.save('/home/claude/lgl/sheet2.jpg')
    else:
        a, b = int(sys.argv[1]), int(sys.argv[2])
        wr = Writer(f'/home/claude/lgl/part_{a}.mp4')
        for f in range(a, b): wr.write(R(f / FPS))
        wr.close()
