import sys
from v1 import *

FACE = clock_face(330)
HM = hand(210, 26, (60, 30, 20)); MM = hand(290, 16, (232, 70, 20))
QOLDI = txt3d('1 СОАТ ҚОЛДИ!', 130, 'gold', maxw=920)
_dig = {}
def dig(s):
    if s not in _dig: _dig[s] = txt3d(s, 200, 'white')
    return _dig[s]
BUGUN = txt3d('БУГУН', 270, 'gold', maxw=920)
OCH = txt3d('ОЧИЛАМИЗ!', 190, 'white', maxw=930)
SOAT = pill('СОАТ 10:00 ДА', 64, track=3)
KUT = txt3d('КУТАМИЗ!', 200, 'white', maxw=900)
SANA2 = txt3d('БУГУН · СОАТ 10:00', 90, 'gold', maxw=960)
SEV2 = txt3d('7 КУН', 300, 'gold', maxw=900)
ICHQ = txt3d('ИЧИДА ҚАЙТАРИШ', 120, 'white', maxw=920)
H1 = flat_txt('ҲАТТО 1 ДОНА ҲАМ', 70, (255, 255, 255), BLACK, maxw=900)
LIT = FAC[-1]
CONF2 = Confetti(170, seed=11)

def s_clock(t):
    C = bg(t)
    place(C, QOLDI, W / 2, -200 + (360 + 200) * spring(t - 0.05, 0.5))
    p = einout((t - 0.3) / 1.7)
    cs = spring(t, 0.5) * (1 + (0.06 * math.sin(math.pi * clamp((t - 2.0) / 0.3)) if t > 2.0 else 0))
    cy = 880
    place(C, FACE, W / 2, cy, cs)
    if cs > 0.2:
        place(C, HM, W / 2, cy, cs, -(270 + 30 * p))
        place(C, MM, W / 2, cy, cs, -(360 * p))
        cv2.circle(C, (W // 2, cy), int(22 * cs), (0.9, 0.3, 0.08), -1, cv2.LINE_AA)
    m = int(round(60 * p)); s = '10:00' if m >= 60 else f'09:{m:02d}'
    place(C, dig(s), W / 2, 1420, spring(t - 0.2, 0.45) * (1.12 if s == '10:00' and t < 2.25 else 1.0),
          0, 1)
    flash(C, 0.4 * clamp(1 - (t - 2.0) / 0.2) if t > 2.0 else 0)
    return C

def s_bugun(t):
    C = bg(t); lt = t - 2.5
    place(C, LOGO, W / 2, 470, 0.7 * spring(lt, 0.45))
    if lt > 0.25:
        place(C, BUGUN, W / 2, 870, (1 + 0.9 * (1 - spring(lt - 0.25, 0.45))), 0, clamp((lt - .25) * 8))
    place(C, OCH, W / 2, 1090 + 300 * (1 - spring(lt - 0.55, 0.45)), 1, 0, clamp((lt - .55) * 8))
    place(C, SOAT, W / 2, 1290, spring(lt - 0.9, 0.4))
    flash(C, 0.45 * clamp(1 - lt / 0.2))
    flash(C, 0.3 * clamp(1 - (lt - 0.3) / 0.2) if lt > 0.3 else 0)
    return C

def fast_person(t, t0, P, T, side, tag):
    return s_person(t0 + (t - t0) * 1.6, t0, P, T, side, tag)
f_man = lambda t: fast_person(t, 5.0, MAN, T_MAN, 'L', (850, 1050, -8))
f_wom = lambda t: fast_person(t, 5.75, WOM, T_WOM, 'R', (235, 1050, 8))
f_kid = lambda t: fast_person(t, 6.5, KID, T_KID, 'B', (790, 760, -7))

def f_ulg(t):
    C = bg(t); lt = t - 7.25
    place(C, H1, W / 2, 700, 1, 0, clamp(lt * 8))
    place(C, ULG, W / 2, 900, 1 + 0.7 * (1 - spring(lt - 0.05, 0.35)), 0, clamp(lt * 10))
    place(C, NARX, W / 2, 1100, spring(lt - 0.2, 0.35))
    return C

def f_sev(t):
    C = bg(t); lt = t - 8.0
    place(C, SEV2, W / 2, 860, 1 + 0.7 * (1 - spring(lt, 0.35)), 0, clamp(lt * 10))
    place(C, ICHQ, W / 2, 1110, spring(lt - 0.2, 0.35))
    return C

def s_wait(t):
    lt = t - 9.0
    C = zoom_frame(LIT, 1.0 + 0.02 * lt, 0.42)
    C = np.concatenate([np.zeros((170, W, 3), np.float32), C[:H - 170]], 0)
    g = np.linspace(0.55, 0, 700)[:, None, None]; C[:700] *= (1 - g)
    CONF2.draw(C, lt - 0.2)
    place(C, KUT, W / 2, -200 + (340 + 200) * spring(lt - 0.1, 0.5))
    place(C, SANA2, W / 2, 510, spring(lt - 0.4, 0.4))
    place(C, ADR, W / 2, 2200 - (2200 - 1470) * spring(lt - 0.6, 0.55))
    if lt > 3.5: C *= clamp(1 - (lt - 3.5) / 0.2)
    return C

WH2 = [(5.0, s_bugun, f_man, -1), (5.75, f_man, f_wom, -1), (6.5, f_wom, f_kid, -1), (7.25, f_kid, f_ulg, -1),
       (8.0, f_ulg, f_sev, -1), (9.0, f_sev, s_wait, -1)]
SC2 = [(0, s_clock), (2.5, s_bugun), (5.0, f_man), (5.75, f_wom), (6.5, f_kid), (7.25, f_ulg), (8.0, f_sev), (9.0, s_wait)]
BODY2 = 12.7

def render2(t):
    for b, fa, fb, d in WH2:
        if abs(t - b) < 0.08: return whip(fa, fb, t, b, 0.16, d) * VIG
    f = [s for s0, s in SC2 if t >= s0][-1]
    return f(t) * VIG

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'sheet':
        ts = [float(x) for x in sys.argv[2].split(',')]
        ims = [Image.fromarray((np.clip(render2(t), 0, 1) * 255).astype(np.uint8)).resize((270, 480)) for t in ts]
        cols = 8; rows = (len(ims) + cols - 1) // cols
        sh = Image.new('RGB', (270 * cols, 480 * rows))
        for k, im in enumerate(ims): sh.paste(im, ((k % cols) * 270, (k // cols) * 480))
        sh.save(A + 'sheet2.jpg')
    else:
        wr = Writer(A + 'v2_body.mp4')
        for f in range(int(BODY2 * FPS)):
            wr.write(render2(f / FPS))
        wr.close()
