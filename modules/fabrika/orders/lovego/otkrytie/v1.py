import sys
from eng import *

LOGO = make_logo()
IC = icons()
def person(name, h):
    L = load_png(A + f'a/{name}.png')
    L = sticker(L, 9)
    s = h / L.shape[0]
    return cv2.resize(L, (int(L.shape[1] * s), int(h)), interpolation=cv2.INTER_AREA)
MAN = person('man', 1330); WOM = person('woman', 1330); KID = person('kids', 1020)
T_MAN = txt3d('ЭРКАКЛАР', 170, 'white', maxw=900)
T_WOM = txt3d('АЁЛЛАР', 170, 'white', maxw=900)
T_KID = txt3d('БОЛАЛАР', 170, 'white', maxw=900)
P_KIY = pill('КИЙИМЛАРИ', 58, track=4)
TAG = pill('УЛГУРЖИ НАРХ', 44, bg=(255, 212, 59), fg=(200, 30, 20))
HATTO = flat_txt('ҲАТТО БИТТА МАҲСУЛОТ ҲАМ', 62, (255, 255, 255), BLACK, maxw=900)
ULG = txt3d('УЛГУРЖИ', 230, 'gold', maxw=920)
NARX = txt3d('НАРХДА', 200, 'white', maxw=900)
DONA = pill('1 ДОНА = УЛГУРЖИ НАРХ', 54, bg=(255, 212, 59), fg=(150, 30, 10))
SEV = txt3d('7', 620, 'gold')
KUN = txt3d('КУН', 190, 'white')
ICH = flat_txt('ИЧИДА', 66, (255, 255, 255), BLACK, track=8)
SAB = txt3d('САБАБСИЗ', 160, 'white', maxw=900)
QAY = txt3d('ҚАЙТАРИШ', 160, 'white', maxw=900)
CHEK = pill('ХАРИД ЧЕКИ КЎРСАТИЛИШИ ШАРТ', 40, bg=(255, 255, 255), fg=(220, 70, 10), maxw=900)
ERT = txt3d('ЭРТАГА', 200, 'white', maxw=900)
SANA = txt3d('10-НОЯБРЬ · СОАТ 10:00', 84, 'gold', maxw=960)
ADR = pin_pill('ХЎЖАОБОД МАРКАЗИ', '«МАЛИКА» САВДО МАРКАЗИ РЎПАРАСИДА')
FAC = load_facade()[9:]
CONF = Confetti(160)

def logo_sweep(t):
    L = LOGO.copy()
    p = (t - 0.9) / 0.6
    if 0 < p < 1:
        h, w = L.shape[:2]
        y, x = np.mgrid[0:h, 0:w].astype(np.float32)
        c = -0.3 * w + p * 1.6 * w
        band = np.exp(-((x + y * 0.5 - c) / 60) ** 2) * 0.8
        L[..., :3] += band[..., None] * L[..., 3:4]
    return L

def s_intro(t):  # 0..4  logo + icons
    C = bg(t)
    if t < 1.75:
        s = 0.7 * spring(t - 0.12, 0.55) + 0.025 * t
        place(C, logo_sweep(t), W / 2, H * 0.44, s, -10 * (1 - eout((t - .12) / .5)), clamp((t - .1) * 6))
        flash(C, 0.45 * clamp(1 - (t - 0.35) / 0.25) if t > 0.35 else 0)
    else:
        p = eout((t - 1.75) / 0.4)
        place(C, logo_sweep(t), W / 2, H * 0.44 + (340 - H * .44) * p, 0.74 - 0.14 * p)
    if t > 1.95:
        for k, L in enumerate(IC):
            tk = t - 2.0 - 0.07 * k
            s = 0.95 * spring(tk, 0.45)
            if s <= 0: continue
            x = W / 2 + (k % 3 - 1) * 292; y = 830 + (k // 3) * 292 + 8 * math.sin(2 * t + k)
            place(C, L, x, y, s, 6 * math.sin(t * 1.5 + k))
    flash(C, 0.35 * clamp(1 - (t - 2.0) / 0.2) if t >= 2.0 else 0)
    return C

def s_person(t, t0, P, T, side, tagpos):
    C = bg(t); lt = t - t0
    ty = -250 + (350 + 250) * spring(lt - 0.05, 0.5)
    place(C, T, W / 2, ty)
    place(C, P_KIY, W / 2, 505, spring(lt - 0.25, 0.4))
    h, w = P.shape[:2]
    if side == 'L':
        x = -w + (470 + w) * spring(lt, 0.55) + 18 * lt; y = H - h / 2 + 30
    elif side == 'R':
        x = W + w - (W + w - 610) * spring(lt, 0.55) - 18 * lt; y = H - h / 2 + 30
    else:
        x = W / 2; y = H + h - (h + h / 2 - 40) * spring(lt, 0.55) * 1.0 - 10 * lt
        y = max(y, H - h / 2 - 30 - 10 * lt)
    place(C, P, x, y, 1 + 0.02 * lt)
    tx, ty2, rot = tagpos
    place(C, TAG, tx, ty2, spring(lt - 0.45, 0.4), rot)
    return C

s_man = lambda t: s_person(t, 4.0, MAN, T_MAN, 'L', (850, 1050, -8))
s_wom = lambda t: s_person(t, 5.5, WOM, T_WOM, 'R', (235, 1050, 8))
s_kid = lambda t: s_person(t, 7.0, KID, T_KID, 'B', (790, 760, -7))

def s_ulg(t):
    C = bg(t); lt = t - 9.0
    z = 1 + 0.015 * lt
    place(C, HATTO, W / 2, 600 + 30 * (1 - eout((lt - .1) / .4)), z, 0, clamp((lt - .1) * 4))
    if lt > 0.45:
        s = 1 + 0.8 * (1 - spring(lt - 0.45, 0.45)); place(C, ULG, W / 2, 810, s * z, 0, clamp((lt - .45) * 8))
        flash(C, 0.3 * clamp(1 - (lt - 0.5) / 0.2) if lt > 0.5 else 0)
    if lt > 0.95: place(C, NARX, W / 2, 1010 + 300 * (1 - spring(lt - 0.95, 0.45)), z, 0, clamp((lt - .95) * 8))
    place(C, DONA, W / 2, 1220, spring(lt - 1.45, 0.4) * z, -5)
    return C

def s_seven(t):
    C = bg(t); lt = t - 12.0
    place(C, SEV, -300 + (330 + 300) * spring(lt, 0.5), 760, 1, -6 * (1 - spring(lt, .5)))
    place(C, KUN, W + 300 - (W + 300 - 730) * spring(lt - 0.2, 0.45), 690)
    place(C, ICH, 730, 830, 1, 0, clamp((lt - .35) * 5))
    place(C, SAB, W / 2, 1110, spring(lt - 0.55, 0.4))
    place(C, QAY, W / 2, 1275, spring(lt - 0.75, 0.4))
    place(C, CHEK, W / 2, 1430, 1, 0, clamp((lt - 1.0) * 4))
    if lt > 2.35: C *= clamp(1 - (lt - 2.35) / 0.15)
    return C

def s_fac(t):
    lt = t - 14.5
    i = min(int(lt * FPS), len(FAC) - 1)
    C = zoom_frame(FAC[i], 1.0 + 0.03 * lt, 0.42)
    C = np.concatenate([np.zeros((170, W, 3), np.float32), C[:H - 170]], 0)
    g = np.linspace(0.55, 0, 700)[:, None, None]; C[:700] *= (1 - g)
    if lt < 0.12: C *= lt / 0.12
    CONF.draw(C, lt - 0.9)
    place(C, ERT, W / 2, -200 + (330 + 200) * spring(lt - 0.55, 0.5))
    place(C, SANA, W / 2, 505, spring(lt - 0.85, 0.4))
    place(C, ADR, W / 2, 2200 - (2200 - 1470) * spring(lt - 1.1, 0.55))
    if lt > 3.3: C *= clamp(1 - (lt - 3.3) / 0.2)
    return C

WH = [(4.0, s_intro, s_man, -1), (5.5, s_man, s_wom, -1), (7.0, s_wom, s_kid, -1), (9.0, s_kid, s_ulg, -1), (12.0, s_ulg, s_seven, -1)]
SC = [(0, s_intro), (4.0, s_man), (5.5, s_wom), (7.0, s_kid), (9.0, s_ulg), (12.0, s_seven), (14.5, s_fac)]

def render(t):
    for b, fa, fb, d in WH:
        if abs(t - b) < 0.12: return whip(fa, fb, t, b, 0.24, d) * VIG
    f = [s for s0, s in SC if t >= s0][-1]
    return f(t) * VIG

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'sheet':
        ts = [float(x) for x in sys.argv[2].split(',')]
        ims = [Image.fromarray((np.clip(render(t), 0, 1) * 255).astype(np.uint8)).resize((270, 480)) for t in ts]
        cols = 8; rows = (len(ims) + cols - 1) // cols
        sh = Image.new('RGB', (270 * cols, 480 * rows))
        for k, im in enumerate(ims): sh.paste(im, ((k % cols) * 270, (k // cols) * 480))
        sh.save(A + 'sheet1.jpg')
    else:
        wr = Writer(A + 'v1_body.mp4')
        for f in range(int(18.0 * FPS)):
            wr.write(render(f / FPS))
        wr.close()
