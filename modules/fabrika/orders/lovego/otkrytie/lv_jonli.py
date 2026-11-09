"""LOVE GO живой анонс: клипы + фото-коллажи под одобренный голос ЭРТАГА (a1p.wav, 26 с)."""
import sys, glob, os
sys.path.insert(0, '/home/claude/lg')
os.chdir('/home/claude/lg')
from v1b import *
os.chdir('/home/claude/lgl')
U = '/mnt/user-data/uploads/'
_fc = {}
def clipf(c, lt, speed=1.0, off=0):
    fs = sorted(glob.glob(f'/home/claude/lgl/fr/{c}/*.jpg'))
    i = int(clamp(off + lt * speed * FPS, 0, len(fs) - 1))
    k = (c, i)
    if k not in _fc:
        if len(_fc) > 6: _fc.clear()
        _fc[k] = cv2.cvtColor(cv2.imread(fs[i]), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
    return _fc[k].copy()

def photo(name, w, h):
    im = Image.open(U + name + '-image.jpg').convert('RGB')
    s = max(w / im.width, h / im.height); im = im.resize((int(im.width * s + 1), int(im.height * s + 1)), Image.LANCZOS)
    x = (im.width - w) // 2; y = (im.height - h) // 2
    a = np.array(im.crop((x, y, x + w, y + h))).astype(np.float32) / 255
    L = np.ones((h, w, 4), np.float32); L[..., :3] = a
    return L

def framed(L, b=10):
    h, w = L.shape[:2]; out = np.ones((h + 2 * b, w + 2 * b, 4), np.float32); out[b:-b, b:-b] = L; return out

# коллажи
MEN = [framed(photo(n, 330, 1000)) for n in ['16502232', 'f4505d62', '1027c547']]
PRICE = [framed(photo(n, 470, 640)) for n in ['71cf9579', '31febab6', 'b38aff7b', '35f1a0eb']]
FAC_ADR = photo('e8a62385', 1080, 1920)[..., :3].copy()
FAC_FAM = photo('5af191a1', 1080, 1920)[..., :3].copy()
TITLE0 = flat_txt('LOVE GO · ХЎЖАОБОД', 46, (255, 255, 255), BLACK, track=10)
T_M = txt3d('ЭРКАКЛАР', 150, 'white', maxw=900); T_W = txt3d('АЁЛЛАР', 150, 'white', maxw=900); T_K = txt3d('БОЛАЛАР', 150, 'white', maxw=900)

def shade(C, top=0, bot=0):
    if top: g = np.linspace(0.6, 0, top)[:, None, None]; C[:top] *= (1 - g)
    if bot: g = np.linspace(0, 0.6, bot)[:, None, None]; C[H - bot:] *= (1 - g)
    return C

def s_open(t):  # 0–3.6
    if t < 1.9: C = clipf('2880', t)
    else: C = clipf('2881', t - 1.9, 0.95)
    shade(C, 0, 520)
    place(C, TITLE0, W / 2, 1480 + 40 * (1 - eout((t - 0.3) / 0.5)), 1, 0, clamp((t - 0.3) * 3) * clamp((3.4 - t) * 4))
    return C

def s_men(t):  # 3.6–4.7 коллаж из 3 полос
    C = bg(t); lt = t - 3.6
    for k, L in enumerate(MEN):
        d = -1 if k % 2 == 0 else 1
        y = 1050 + d * 1400 * (1 - spring(lt - 0.06 * k, 0.4))
        place(C, L, 190 + k * 350, y, 1.0)
    place(C, T_M, W / 2, 330, spring(lt - 0.05, 0.35))
    return C

def s_wom(t):  # 4.7–5.5
    C = shade(clipf('2903', t - 4.7, 1.0, 10), 620, 0)
    place(C, T_W, W / 2, 330, spring(t - 4.72, 0.35)); return C

def s_kid(t):  # 5.5–7.5
    C = shade(clipf('2926', t - 5.5, 0.95), 620, 0)
    place(C, T_K, W / 2, 330, spring(t - 5.52, 0.35)); return C

def s_price(t):  # 7.5–11.2 коллаж 2×2 с ценниками
    C = bg(t); lt = t - 7.5
    pos = [(285, 690), (795, 690), (285, 1350), (795, 1350)]
    for k, (L, (x, y)) in enumerate(zip(PRICE, pos)):
        s = spring(lt - 0.12 * k, 0.45)
        place(C, L, x, y, s * (1 + 0.01 * lt), (-3, 2, 2, -3)[k])
    u = t - 9.7
    if u > 0:
        C *= (1 - 0.45 * clamp(u / 0.2))
        place(C, ULG, W / 2, 900, 1 + 0.8 * (1 - spring(u, 0.45)), 0, clamp(u * 8))
        flash(C, 0.3 * clamp(1 - (u - 0.05) / 0.2) if u > 0.05 else 0)
    if t > 10.2: place(C, NARX, W / 2, 1100 + 300 * (1 - spring(t - 10.2, 0.45)), 1, 0, clamp((t - 10.2) * 8))
    place(C, DONA, W / 2, 1310, spring(t - 10.65, 0.4), -5)
    return C

def s_ret(t):  # 11.2–15.8 проходка по залу + 7 кун
    lt = t - 11.2
    C = clipf('2936', lt, 0.62) if lt < 3.0 else clipf('2900', lt - 3.0, 0.9, 20)
    C *= 0.62
    place(C, CHEK, W / 2, 1430, spring(t - 11.35, 0.45))
    place(C, SEV, -300 + (330 + 300) * spring(t - 12.65, 0.5), 760, 1, -6 * (1 - spring(t - 12.65, .5)))
    place(C, KUN, W + 300 - (W + 300 - 730) * spring(t - 12.9, 0.45), 690)
    place(C, ICH, 730, 830, 1, 0, clamp((t - 13.1) * 5))
    place(C, SAB, W / 2, 1110, spring(t - 13.7, 0.4))
    place(C, QAY, W / 2, 1275, spring(t - 14.2, 0.4))
    return C

def s_ert(t):  # 15.8–20.0
    lt = t - 15.8
    if True:
        C = zoom_frame(FAC_FAM, 1.0 + 0.02 * lt, 0.6)
        C = np.concatenate([np.repeat(C[:1], 380, 0), C[:H - 380]], 0)
    shade(C, 700, 0)
    place(C, ERT, W / 2, -200 + (330 + 200) * spring(t - 16.2, 0.5))
    place(C, SANA, W / 2, 505, spring(t - 17.1, 0.4))
    return C

def s_adr(t):  # 20.0–26.0
    lt = t - 20.0
    C = clipf('2948', lt, 0.8) if lt < 2.2 else zoom_frame(FAC_ADR, 1.0 + 0.02 * (lt - 2.2), 0.35)
    shade(C, 0, 700)
    CONF.draw(C, lt - 4.4)
    place(C, ADR, W / 2, 2200 - (2200 - 1470) * spring(t - 20.6, 0.55))
    place(C, KUT1, W / 2, 1250, spring(t - 24.75, 0.4))
    if t > 25.8: C *= clamp(1 - (t - 25.8) / 0.2)
    return C

SC = [(0, s_open), (3.6, s_men), (4.7, s_wom), (5.5, s_kid), (7.5, s_price), (11.2, s_ret), (15.8, s_ert), (20.0, s_adr)]
WHP = [(3.6, s_open, s_men), (4.7, s_men, s_wom), (5.5, s_wom, s_kid), (7.5, s_kid, s_price), (11.2, s_price, s_ret), (15.8, s_ret, s_ert), (20.0, s_ert, s_adr)]
D = 26.0
def R(t):
    for b, fa, fb in WHP:
        if abs(t - b) < 0.1: return whip(fa, fb, t, b, 0.2, -1)
    return [s for s0, s in SC if t >= s0][-1](t)

if __name__ == '__main__':
    if sys.argv[1:] and sys.argv[1] == 'sheet':
        ts = [float(x) for x in sys.argv[2].split(',')]
        ims = [Image.fromarray((np.clip(R(t), 0, 1) * 255).astype(np.uint8)).resize((216, 384)) for t in ts]
        sh = Image.new('RGB', (216 * len(ims), 384))
        for k, im in enumerate(ims): sh.paste(im, (k * 216, 0))
        sh.save('/home/claude/lgl/sheetL.jpg')
    else:
        wr = Writer('/home/claude/lgl/live_body.mp4')
        for f in range(int(D * FPS)): wr.write(R(f / FPS))
        wr.close()
