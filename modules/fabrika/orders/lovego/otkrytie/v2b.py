import sys
from v2 import *
VO2 = [('B1', 0.3), ('B2', 2.6), ('B3', 4.4), ('B4', 9.3)]
BODY = 13.2
g_man = lambda t: fast_person(t, 4.3, MAN, T_MAN, 'L', (850, 1050, -8))
g_wom = lambda t: fast_person(t, 5.3, WOM, T_WOM, 'R', (235, 1050, 8))
g_kid = lambda t: fast_person(t, 6.15, KID, T_KID, 'B', (790, 760, -7))
def g_ulg(t): return f_ulg(t - 7.5 + 7.25)
def g_sev(t): return f_sev(t - 8.7 + 8.0)
def g_wait(t):
    lt = t - 9.2
    C = zoom_frame(LIT, 1.0 + 0.02 * lt, 0.42)
    C = np.concatenate([np.zeros((170, W, 3), np.float32), C[:H - 170]], 0)
    g = np.linspace(0.55, 0, 700)[:, None, None]; C[:700] *= (1 - g)
    CONF2.draw(C, lt - 0.2)
    place(C, KUT, W / 2, -200 + (340 + 200) * spring(t - 12.0, 0.5))
    place(C, SANA2, W / 2, 510, spring(lt - 0.1, 0.4))
    place(C, ADR, W / 2, 2200 - (2200 - 1470) * spring(lt - 0.15, 0.55))
    if t > 13.0: C *= clamp(1 - (t - 13.0) / 0.2)
    return C
def g_bugun(t): return s_bugun(t)
WHG = [(4.3, g_bugun, g_man, -1), (5.3, g_man, g_wom, -1), (6.15, g_wom, g_kid, -1), (7.5, g_kid, g_ulg, -1), (8.7, g_ulg, g_sev, -1), (9.2, g_sev, g_wait, -1)]
SCG = [(0, s_clock), (2.5, g_bugun), (4.3, g_man), (5.3, g_wom), (6.15, g_kid), (7.5, g_ulg), (8.7, g_sev), (9.2, g_wait)]
def rg(t):
    for b, fa, fb, d in WHG:
        if abs(t - b) < 0.08: return whip(fa, fb, t, b, 0.16, d) * VIG
    return [s for s0, s in SCG if t >= s0][-1](t) * VIG
if __name__ == '__main__':
    if sys.argv[1:] and sys.argv[1] == 'sheet':
        ts = [float(x) for x in sys.argv[2].split(',')]
        ims = [Image.fromarray((np.clip(rg(t), 0, 1) * 255).astype(np.uint8)).resize((270, 480)) for t in ts]
        sh = Image.new('RGB', (270 * len(ims), 480))
        for k, im in enumerate(ims): sh.paste(im, (k * 270, 0))
        sh.save(A + 'sheet2b.jpg')
    else:
        wr = Writer(A + 'v2b_body.mp4')
        for f in range(int(BODY * FPS)): wr.write(rg(f / FPS))
        wr.close()
