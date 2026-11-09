import sys, os, glob
sys.path.insert(0, '/home/claude/lg'); os.chdir('/home/claude/lg')
from eng import *
os.chdir('/home/claude/lgl')
import perehody as P

U = '/mnt/user-data/uploads/'
def frames(c): return sorted(glob.glob(f'/home/claude/lgl/fr/{c}/*.jpg'))
_c = {}
def cf(c, lt, speed=1.0, off=0):
    fs = frames(c); i = int(clamp((off + lt * speed) * FPS, 0, len(fs) - 1))
    if (c, i) not in _c:
        if len(_c) > 8: _c.clear()
        _c[(c, i)] = cv2.cvtColor(cv2.imread(fs[i]), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
    return _c[(c, i)].copy()
def cover(name):
    im = Image.open(U + name + '-image.jpg').convert('RGB')
    s = max(W / im.width, H / im.height); im = im.resize((int(im.width * s + 1), int(im.height * s + 1)), Image.LANCZOS)
    x = (im.width - W) // 2; y = (im.height - H) // 2
    return np.array(im.crop((x, y, x + W, y + H))).astype(np.float32) / 255

FAM = cover('5af191a1'); FAC = cover('e8a62385'); AISLE = cover('3ec14189')
FAM_MASK = P.person_mask(FAM)
LOGO = make_logo()
MAN = sticker(load_png(A + 'a/man.png'), 9)
MAN = cv2.resize(MAN, (int(MAN.shape[1] * 1150 / MAN.shape[0]), 1150), interpolation=cv2.INTER_AREA)
NAME = pill('ИСМ ФАМИЛИЯ', 52, bg=(255, 255, 255), fg=(200, 60, 10))
ROLE = flat_txt('ҲАМКОР', 40, (255, 255, 255), XBOLD, track=8)
def label(C, s):
    L = flat_txt(s, 34, (255, 255, 255), XBOLD, track=4)
    h, w = L.shape[:2]; C[40:40 + h + 20, :] *= 0.45
    place(C, L, W / 2, 60 + h / 2); return C

WORDS = [(0.25, 'ХЎЖАОБОД'), (0.95, 'БУГУН'), (1.6, 'ОЧИЛДИ!')]
STROBE = ['2884', '2903', '2926', '2888', '2909', '2892', '2938', '2889', '2910', '2933', '2924', '2911']

def logo_card(t, t0):
    C = bg(t); lt = t - t0
    place(C, LOGO, W / 2, H * 0.46, 0.85 * spring(lt, 0.5)); return C

def R(t):
    if t < 2.5:
        C = cf('2880', t, 0.9)
        cur = [w for s, w in WORDS if t >= s]
        if cur:
            s0 = [s for s, w in WORDS if t >= s][-1]
            P.word_card(C, cur[-1], BLACK, 150, H * 0.62, 1, 1 + 0.25 * (1 - eout((t - s0) / 0.15)))
        return label(C, '1 · СЎЗЛАР БИТТАДАН (TEN x YOU)')
    if t < 3.3:
        p = (t - 2.5) / 0.8
        C = P.zoom_through(cf('2880', 2.5 * 0.9), cf('2881', 0), p)
        return label(C, '2 · ЗУМ-БЛЮР ЎТИШ (AMAZON)')
    if t < 5.0:
        return label(cf('2881', t - 3.3, 0.9), '2 · ЗУМ-БЛЮР ЎТИШ (AMAZON)')
    if t < 6.6:
        k = int((t - 5.0) / (2 / 30)) % len(STROBE)
        C = cf(STROBE[k], 0.5)
        if k % 3 == 2: C = P.bw_hit(C)
        return label(C, '3 · СТРОБ-ОЧЕРЕДЬ (PUMA)')
    if t < 9.2:
        lt = t - 6.6
        C = cf('2903', lt, 0.8, 0.3)
        P.glow_title(C, 'УЛГУРЖИ НАРХ', BLACK, W / 2, H * 0.36, t, 6.9, 2.0, 96)
        return label(C, '4 · ЁРУҒ ТИТР (STARBUCKS)')
    if t < 11.6:
        lt = t - 9.2
        C = zoom_frame(FAM, 1.0 + 0.03 * lt, 0.6)
        if 0.9 < lt < 1.15: C = P.bw_hit(C)
        elif 1.15 <= lt < 1.55:
            M = zoom_frame(FAM_MASK[..., None].repeat(3, 2), 1.0 + 0.03 * lt, 0.6)[..., 0]
            C = P.white_silhouette(C, M, 1.0)
        if 1.55 <= lt < 1.7: P.flash(C, 0.6 * (1 - (lt - 1.55) / 0.15))
        return label(C, '5 · ОҚ СИЛУЭТ + Қ/О УРИШ (PUMA)')
    if t < 15.2:
        lt = t - 11.6
        C = bg(t)
        C = P.paper_strip(C, FAC, 260, 860, lt / 0.45, seed=3, from_left=True)
        C = P.paper_strip(C, AISLE, 1000, 1640, (lt - 0.35) / 0.45, seed=7, from_left=False)
        if lt > 0.9:
            s = spring(lt - 0.9, 0.45)
            place(C, MAN, W / 2 + 40, H - MAN.shape[0] / 2 + 60 + 900 * (1 - s), 1.0)
        place(C, NAME, W / 2, 1640, spring(lt - 1.5, 0.4), -3)
        place(C, ROLE, W / 2, 1735, 1, 0, clamp((lt - 1.8) * 4))
        return label(C, '6 · ЙИРТИҚ ҚОҒОЗ КОЛЛАЖ (STARBUCKS)')
    if t < 15.4:
        return label(whip(lambda x: R(15.19), lambda x: cf('2936', x - 15.2), t, 15.3, 0.2, -1), '7 · WHIP + ТЕЗЛАНИШ')
    if t < 17.4:
        lt = t - 15.4
        s = lt + 1.2 * (lt - lt * lt / 0.7) if lt < 0.35 else lt + 0.21
        return label(cf('2936', s, 1.0), '7 · WHIP + ТЕЗЛАНИШ')
    if t < 18.2:
        p = (t - 17.4) / 0.8
        C = P.zoom_through(cf('2936', 2.2), logo_card(t, 17.8), p)
        return label(C, '8 · ҲАЛҚА: ЛОГОТИП ОХИРИДА (AMAZON)')
    return label(logo_card(t, 17.8), '8 · ҲАЛҚА: ЛОГОТИП ОХИРИДА (AMAZON)')

D = 20.0
if __name__ == '__main__':
    if sys.argv[1] == 'sheet':
        ts = [float(x) for x in sys.argv[2].split(',')]
        ims = [Image.fromarray((np.clip(R(t), 0, 1) * 255).astype(np.uint8)).resize((180, 320)) for t in ts]
        sh = Image.new('RGB', (180 * len(ims), 320))
        for k, im in enumerate(ims): sh.paste(im, (k * 180, 0))
        sh.save('/home/claude/lgl/sheetP.jpg')
    else:
        wr = Writer('/home/claude/lgl/per_body.mp4')
        for f in range(int(D * FPS)): wr.write(np.clip(R(f / FPS), 0, 1))
        wr.close()
