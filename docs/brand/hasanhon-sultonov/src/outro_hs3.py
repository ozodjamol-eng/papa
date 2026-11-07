"""Концовка HASANHON SULTONOV — 2,3 с, удары барабана: H (бочка) → S (малый) → черта (палочка) → имя → тарелка (волна) → сжатие в точку."""
import sys, os, math, subprocess
sys.path.insert(0, os.path.dirname(__file__))
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen

SRC, OUT, BGMODE = sys.argv[1], sys.argv[2], sys.argv[3]  # black|white
W, H = 1080, 1920
FPS, N = 30, 70
RED = "#D7141F"
BG, MAIN = ("#0B0B0B", "#FFFFFF") if BGMODE == "black" else ("#FFFFFF", "#0B0B0B")
os.makedirs(OUT, exist_ok=True)
f900 = instantiateVariableFont(TTFont(SRC), {"wght": 900})
f800 = instantiateVariableFont(TTFont(sys.argv[4]), {"wght": 700, "opsz": 24})


def gb(font, ch, size):
    gs = font.getGlyphSet(); g = font.getBestCmap()[ord(ch)]
    bp = BoundsPen(gs); gs[g].draw(bp); s = size / font["head"].unitsPerEm
    return bp.bounds[0] * s, bp.bounds[2] * s


def pt(font, text, size, x, y, tr=0):
    gs = font.getGlyphSet(); cm = font.getBestCmap(); s = size / font["head"].unitsPerEm
    pen = SVGPathPen(gs); cx = x
    for ch in text:
        g = cm[ord(ch)]
        if ch != " ":
            gs[g].draw(TransformPen(pen, (s, 0, 0, -s, cx, y)))
        cx += gs[g].width * s + tr
    return pen.getCommands(), cx - x - tr


CX = W / 2
MS, MB = 400, 960
hx0, hx1 = gb(f900, "H", MS); sx0, sx1 = gb(f900, "S", MS)
gap = MS * 0.08
iw = (hx1 - hx0) + gap + (sx1 - sx0); left = CX - iw / 2
HP, _ = pt(f900, "H", MS, left - hx0, MB)
SP, _ = pt(f900, "S", MS, left + (hx1 - hx0) + gap - sx0, MB)
hc = (left + (hx1 - hx0) / 2, MB - MS * 0.36)
sc = (left + (hx1 - hx0) + gap + (sx1 - sx0) / 2, MB - MS * 0.36)
BAR = (left, MB + MS * 0.14, iw, MS * 0.08)
NAME = "Hasanhon Sultonov"; NS = 70; NT = 1
_, nw = pt(f900, NAME, NS, 0, 0, NT); NP, _ = pt(f900, NAME, NS, CX - nw / 2, 1210, NT)
SUB = "DRUMS & SINGER"; SS = 36; ST = 10
_, sw = pt(f800, SUB, SS, 0, 0, ST); SUBP, _ = pt(f800, SUB, SS, CX - sw / 2, 1285, ST)
MC = (CX, MB - MS * 0.2)  # центр знака


def clamp(x): return max(0.0, min(1.0, x))
def prog(f, a, b): return clamp((f - a) / (b - a))
def out_back(t, s=1.9): t -= 1; return t * t * ((s + 1) * t + s) + 1
def out_cubic(t): return 1 - (1 - t) ** 3
def in_back(t, s=1.7): return t * t * ((s + 1) * t - s)


def shake(f, hits):
    dx = dy = 0.0
    for h, amp in hits:
        k = f - h
        if 0 <= k < 6:
            a = amp * (0.55 ** k)
            dx += a * math.sin(k * 2.7 + h); dy += a * math.cos(k * 3.1 + h)
    return dx, dy


def ring(f, at, col, maxr, dur, width, alpha):
    t = prog(f, at, at + dur)
    if t <= 0 or t >= 1: return ""
    r = maxr * out_cubic(t); o = alpha * (1 - t)
    return f'<circle cx="{MC[0]}" cy="{MC[1]}" r="{r:.1f}" fill="none" stroke="{col}" stroke-width="{width*(1-t*0.6):.1f}" opacity="{o:.3f}"/>'


HIT_H, HIT_S, HIT_BAR, CRASH = 6, 13, 20, 36


def frame(f):
    els = []
    # H — бочка: падает сверху
    th = prog(f, 0, HIT_H)
    if th > 0:
        y = -900 * (1 - out_back(th, 1.2)) if th < 1 else 0
        sq = 1.0
        if HIT_H <= f < HIT_H + 4: sq = [0.9, 0.95, 1.02, 1.0][f - HIT_H]
        els.append(f'<g transform="translate(0 {y:.1f}) translate({hc[0]} {MB}) scale({2-sq:.3f} {sq:.3f}) translate({-hc[0]} {-MB})"><path fill="{MAIN}" d="{HP}"/></g>')
    # S — малый: влетает справа
    ts = prog(f, HIT_H + 2, HIT_S)
    if ts > 0:
        x = 900 * (1 - out_back(ts, 1.3)) if ts < 1 else 0
        rot = 14 * (1 - ts)
        els.append(f'<g transform="translate({x:.1f} 0) rotate({rot:.2f} {sc[0]} {sc[1]})"><path fill="{RED}" d="{SP}"/></g>')
    # черта — палочка, прочерк слева направо
    tb = prog(f, HIT_S + 2, HIT_BAR)
    if tb > 0:
        bw = BAR[2] * out_back(tb, 1.4)
        els.append(f'<rect x="{BAR[0]:.1f}" y="{BAR[1]:.1f}" width="{max(bw,0):.1f}" height="{BAR[3]:.1f}" fill="{RED}"/>')
    # имя и подпись
    tn = prog(f, HIT_BAR, HIT_BAR + 9)
    if tn > 0:
        e = out_cubic(tn)
        els.append(f'<g opacity="{e:.3f}" transform="translate(0 {40*(1-e):.1f})"><path fill="{MAIN}" d="{NP}"/></g>')
    tu = prog(f, HIT_BAR + 5, HIT_BAR + 14)
    if tu > 0:
        e = out_cubic(tu)
        els.append(f'<g opacity="{e:.3f}" transform="translate(0 {30*(1-e):.1f})"><path fill="{RED}" d="{SUBP}"/></g>')
    body = "".join(els)
    # волны ударов (за знаком)
    rings = (ring(f, HIT_H, RED, 520, 10, 14, 0.55) + ring(f, HIT_S, RED, 560, 10, 14, 0.55) +
             ring(f, CRASH, RED, 1300, 16, 26, 0.85) + ring(f, CRASH + 2, MAIN, 1100, 14, 6, 0.35))
    # тарелка: лёгкий «пульс» знака
    pulse = 1.0
    if CRASH <= f < CRASH + 6: pulse = 1 + 0.06 * math.sin(math.pi * (f - CRASH) / 6)
    # финал: сжатие в точку
    to = prog(f, 54, N - 1)
    scale = pulse * (1 - in_back(to, 1.6)) if to > 0 else pulse
    op = 1 - prog(f, 64, N - 1)
    dx, dy = shake(f, [(HIT_H, 22), (HIT_S, 16), (HIT_BAR, 8), (CRASH, 14)])
    g = (f'<g opacity="{op:.3f}" transform="translate({dx:.1f} {dy:.1f}) translate({MC[0]} {MC[1]}) '
         f'scale({max(scale,0):.4f}) translate({-MC[0]} {-MC[1]})">{body}</g>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
            f'<rect width="{W}" height="{H}" fill="{BG}"/>{rings}{g}</svg>')


for f in range(N):
    p = os.path.join(OUT, f"f{f:03d}.svg")
    open(p, "w").write(frame(f))
    subprocess.run(["rsvg-convert", p, "-o", p[:-4] + ".png"], check=True)
    os.remove(p)
print("frames", N)
