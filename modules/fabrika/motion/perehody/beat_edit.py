"""Проба №2: монтаж в бит (librosa) + gl-transitions + приёмы PAPA. Музыка — 22 с из рефа TEN x YOU (черновик)."""
import sys, os, glob
sys.path.insert(0, '/home/claude/lg'); os.chdir('/home/claude/lg')
from eng import *
os.chdir('/home/claude/lgl')
import perehody as P, glt, librosa

MUS = '/home/claude/ref4/MUZIKA_dlya_Shazam.mp3'
y, sr = librosa.load(MUS, sr=22050)
_, bf = librosa.beat.beat_track(y=y, sr=sr)
BT = [0.0] + [float(x) for x in librosa.frames_to_time(bf, sr=sr)]
D = float(len(y) / sr)
def bt(i): return BT[i] if i < len(BT) else BT[-1] + (i - len(BT) + 1) * 0.43

U = '/mnt/user-data/uploads/'
_c = {}
def frames(c): return sorted(glob.glob(f'/home/claude/lgl/fr/{c}/*.jpg'))
def cf(c, s):
    fs = frames(c); i = int(clamp(s * FPS, 0, len(fs) - 1))
    if (c, i) not in _c:
        if len(_c) > 10: _c.clear()
        _c[(c, i)] = cv2.cvtColor(cv2.imread(fs[i]), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
    return _c[(c, i)].copy()
def ramp(lt):  # быстрый вход и замедление (speed-ramp)
    return lt * 2.2 if lt < 0.12 else 0.264 + (lt - 0.12) * 0.85
def cover(name):
    im = Image.open(U + name + '-image.jpg').convert('RGB')
    s = max(W / im.width, H / im.height); im = im.resize((int(im.width * s + 1), int(im.height * s + 1)), Image.LANCZOS)
    x = (im.width - W) // 2; yy = (im.height - H) // 2
    return np.array(im.crop((x, yy, x + W, yy + H))).astype(np.float32) / 255
FAM = cover('5af191a1'); FAM_M = P.person_mask(FAM)
LOGO = make_logo()

def clip(c, off=0.0, push=0.04):
    def f(lt): return zoom_frame(cf(c, off + ramp(lt)), 1.0 + push * lt * 2, 0.5)
    return f
def words(c, ws):
    def f(lt):
        C = cf(c, lt * 0.9)
        k = min(int(lt / 0.43), len(ws) - 1); l2 = lt - k * 0.43
        P.word_card(C, ws[k], BLACK, 170, H * 0.6, 1, 1 + 0.3 * (1 - eout(l2 / 0.12)))
        return C
    return f
def glow(c, txt, off=0.3):
    def f(lt):
        C = clip(c, off)(lt); P.glow_title(C, txt, BLACK, W / 2, H * 0.36, lt, 0.05, 1.6, 100); return C
    return f
def sil(lt):
    C = zoom_frame(FAM, 1 + 0.04 * lt, 0.6)
    if 0.43 <= lt < 0.6: return P.bw_hit(C)
    if lt >= 0.6:
        M = zoom_frame(FAM_M[..., None].repeat(3, 2), 1 + 0.04 * lt, 0.6)[..., 0]
        return P.white_silhouette(C, M)
    return C
def logo_end(lt):
    C = bg(lt + 20); place(C, LOGO, W / 2, H * 0.46, 0.85 * spring(lt, 0.5)); return C

# (бит-старт, бит-длина, функция, переход ВХОДА)
SEG = []
def add(nb, f, tr=None):
    s = SEG[-1][0] + SEG[-1][1] if SEG else 0
    SEG.append((s, nb, f, tr))
add(5, words('2880', ['ХЎЖАОБОД', 'БУГУН', 'LOVE GO', 'ОЧИЛДИ!', 'ОЧИЛДИ!']))
add(3, clip('2881', 0, 0.02), 'CrossZoom')
add(2, clip('2900', 1.0), 'WhipPan')
add(2, clip('2936', 0.5), 'TangentMotionBlur')
add(2, clip('2884', 0.3), 'WhipSpin')
add(2, clip('2888', 0.3), None)
add(2, glow('2903', 'УЛГУРЖИ НАРХ'), 'LightStreaks')
add(2, clip('2926', 0.3), 'WhipPan')
add(2, clip('2892', 0.3), 'CameraShake')
add(2, clip('2895', 0.5), 'CrossZoom')
add(2, clip('2941', 0.2), 'Overexposure')
STROBE = ['2909', '2911', '2925', '2938', '2910', '2933', '2932', '2923', '2889', '2898']
for k, c in enumerate(STROBE):
    add(1, (lambda c, k: (lambda lt: P.bw_hit(cf(c, 0.6)) if k % 3 == 2 else cf(c, 0.6 + lt)))(c, k), 'GlitchFlicker' if k == 0 else None)
add(3, sil, 'FlashFade')
add(2, clip('2902', 0.4), 'WhipTilt')
add(2, clip('2937', 0.3), 'TangentMotionBlur')
add(2, clip('2886', 0.2), 'WhipPan')
add(3, clip('2948', 0, 0.03), 'CrossZoom')
add(99, logo_end, 'CrossZoom')

TRD = 0.22
def seg_f(i, t):
    s, nb, f, tr = SEG[i]
    return f(max(0.0, t - bt(s)))
def R(t):
    i = max(k for k in range(len(SEG)) if bt(SEG[k][0]) <= t + 1e-6)
    b = bt(SEG[i][0])
    if SEG[i][3] and i > 0 and t - b < TRD / 2:  # вторая половина перехода
        p = 0.5 + (t - b) / TRD
        return glt.run(SEG[i][3], seg_f(i - 1, t), seg_f(i, t), p)
    if i + 1 < len(SEG) and SEG[i + 1][3]:
        nb_ = bt(SEG[i + 1][0])
        if nb_ - t < TRD / 2:
            p = 0.5 - (nb_ - t) / TRD
            return glt.run(SEG[i + 1][3], seg_f(i, t), seg_f(i + 1, t), p)
    C = seg_f(i, t)
    if t - b < 0.05 and not SEG[i][3]: flash(C, 0.25 * (1 - (t - b) / 0.05))  # микро-вспышка на жёсткой склейке
    return C

if __name__ == '__main__':
    if sys.argv[1] == 'sheet':
        ts = [float(x) for x in sys.argv[2].split(',')]
        ims = [Image.fromarray((np.clip(R(t), 0, 1) * 255).astype(np.uint8)).resize((180, 320)) for t in ts]
        sh = Image.new('RGB', (180 * min(12, len(ims)), 320 * ((len(ims) + 11) // 12)))
        for k, im in enumerate(ims): sh.paste(im, ((k % 12) * 180, (k // 12) * 320))
        sh.save('/home/claude/lgl/sheetB.jpg'); print(D, [round(bt(s[0]), 2) for s in SEG])
    else:
        wr = Writer('/home/claude/lgl/beat_body.mp4')
        for f in range(int(D * FPS)): wr.write(np.clip(R(f / FPS), 0, 1))
        wr.close()
