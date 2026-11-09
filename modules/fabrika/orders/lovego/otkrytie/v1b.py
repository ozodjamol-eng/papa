import sys
from v1 import *

KUT1 = txt3d('КУТАМИЗ!', 150, 'gold', maxw=900)
HB1 = txt3d('ҲАТТО БИТТА', 140, 'white', maxw=920)
HB2 = txt3d('МАҲСУЛОТ ҲАМ', 140, 'white', maxw=920)
VO1 = [('A1', 0.4), ('A2', 3.75), ('A3', 7.6), ('A4', 11.3), ('A5', 16.2), ('A6', 20.0)]
BODY1 = 26.0

def b_intro(t):
    C = bg(t)
    if t < 2.0:
        s = 0.7 * spring(t - 0.12, 0.6) + 0.02 * t
        place(C, logo_sweep(t - 0.4), W / 2, H * 0.44, s, -10 * (1 - eout((t - .12) / .5)), clamp((t - .1) * 6))
        flash(C, 0.4 * clamp(1 - (t - 0.35) / 0.25) if t > 0.35 else 0)
    else:
        p = eout((t - 2.0) / 0.45)
        place(C, logo_sweep(t), W / 2, H * 0.44 + (340 - H * .44) * p, 0.74 - 0.14 * p)
    if t > 2.3:
        for k, L in enumerate(IC):
            s = 0.95 * spring(t - 2.35 - 0.07 * k, 0.45)
            if s <= 0: continue
            place(C, L, W / 2 + (k % 3 - 1) * 292, 830 + (k // 3) * 292 + 8 * math.sin(2 * t + k), s, 6 * math.sin(t * 1.5 + k))
    return C

b_man = lambda t: s_person(t, 3.6, MAN, T_MAN, 'L', (850, 1050, -8))
b_wom = lambda t: s_person(t, 4.7, WOM, T_WOM, 'R', (235, 1050, 8))
b_kid = lambda t: s_person(t, 5.5, KID, T_KID, 'B', (790, 760, -7))

def b_ulg(t):
    C = bg(t); lt = t - 7.5
    z = 1 + 0.012 * lt
    m = eout((t - 9.45) / 0.3)
    if m < 1:
        place(C, HB1, W / 2, 780 - 180 * m, spring(t - 7.6, 0.45) * (1 - 0.4 * m), 0, 1 - m)
        place(C, HB2, W / 2, 940 - 340 * m, spring(t - 8.1, 0.45) * (1 - 0.4 * m), 0, 1 - m)
    if m > 0: place(C, HATTO, W / 2, 600, z, 0, m)
    u = t - 9.7
    if u > 0:
        place(C, ULG, W / 2, 810, (1 + 0.8 * (1 - spring(u, 0.45))) * z, 0, clamp(u * 8))
        flash(C, 0.3 * clamp(1 - (u - 0.05) / 0.2) if u > 0.05 else 0)
    n = t - 10.2
    if n > 0: place(C, NARX, W / 2, 1010 + 300 * (1 - spring(n, 0.45)), z, 0, clamp(n * 8))
    place(C, DONA, W / 2, 1220, spring(t - 10.65, 0.4) * z, -5)
    return C

def b_sev(t):
    C = bg(t)
    q = eout((t - 12.45) / 0.35)
    place(C, CHEK, W / 2, 900 + 530 * q, spring(t - 11.35, 0.45) * (1.12 - 0.12 * q))
    place(C, SEV, -300 + (330 + 300) * spring(t - 12.65, 0.5), 760, 1, -6 * (1 - spring(t - 12.65, .5)))
    place(C, KUN, W + 300 - (W + 300 - 730) * spring(t - 12.9, 0.45), 690)
    place(C, ICH, 730, 830, 1, 0, clamp((t - 13.1) * 5))
    place(C, SAB, W / 2, 1110, spring(t - 13.7, 0.4))
    place(C, QAY, W / 2, 1275, spring(t - 14.2, 0.4))
    if t > 15.65: C *= clamp(1 - (t - 15.65) / 0.15)
    return C

def b_fac(t):
    lt = t - 15.8
    i = min(int(lt * FPS), len(FAC) - 1)
    C = zoom_frame(FAC[i], 1.0 + 0.012 * lt, 0.42)
    C = np.concatenate([np.zeros((170, W, 3), np.float32), C[:H - 170]], 0)
    g = np.linspace(0.55, 0, 700)[:, None, None]; C[:700] *= (1 - g)
    if lt < 0.12: C *= lt / 0.12
    CONF.draw(C, t - 17.1)
    place(C, ERT, W / 2, -200 + (330 + 200) * spring(t - 16.2, 0.5))
    place(C, SANA, W / 2, 505, spring(t - 17.1, 0.4))
    place(C, ADR, W / 2, 2200 - (2200 - 1470) * spring(t - 20.6, 0.55))
    place(C, KUT1, W / 2, 1250, spring(t - 24.75, 0.4))
    if t > 25.8: C *= clamp(1 - (t - 25.8) / 0.2)
    return C

WHB = [(3.6, b_intro, b_man, -1), (4.7, b_man, b_wom, -1), (5.5, b_wom, b_kid, -1), (7.5, b_kid, b_ulg, -1), (11.2, b_ulg, b_sev, -1)]
SCB = [(0, b_intro), (3.6, b_man), (4.7, b_wom), (5.5, b_kid), (7.5, b_ulg), (11.2, b_sev), (15.8, b_fac)]

def renderb(t):
    for b, fa, fb, d in WHB:
        if abs(t - b) < 0.12: return whip(fa, fb, t, b, 0.24, d) * VIG
    f = [s for s0, s in SCB if t >= s0][-1]
    return f(t) * VIG

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'sheet':
        ts = [float(x) for x in sys.argv[2].split(',')]
        ims = [Image.fromarray((np.clip(renderb(t), 0, 1) * 255).astype(np.uint8)).resize((270, 480)) for t in ts]
        cols = 8; rows = (len(ims) + cols - 1) // cols
        sh = Image.new('RGB', (270 * cols, 480 * rows))
        for k, im in enumerate(ims): sh.paste(im, ((k % cols) * 270, (k // cols) * 480))
        sh.save(A + 'sheet1b.jpg')
    else:
        wr = Writer(A + 'v1b_body.mp4')
        for f in range(int(BODY1 * FPS)):
            wr.write(renderb(f / FPS))
        wr.close()
