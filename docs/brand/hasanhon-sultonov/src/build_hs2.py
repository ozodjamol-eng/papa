import sys, os
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen

SRC, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
RED, BLACK, WHITE = "#D7141F", "#0B0B0B", "#FFFFFF"
f900 = instantiateVariableFont(TTFont(SRC), {"wght": 900})
f800 = instantiateVariableFont(TTFont(SRC), {"wght": 800})


def gb(font, ch, size):
    gs = font.getGlyphSet(); g = font.getBestCmap()[ord(ch)]
    bp = BoundsPen(gs); gs[g].draw(bp); s = size / font["head"].unitsPerEm
    return bp.bounds[0] * s, bp.bounds[2] * s


def pt(font, text, size, x, y, tr=0):
    gs = font.getGlyphSet(); cm = font.getBestCmap(); s = size / font["head"].unitsPerEm
    pen = SVGPathPen(gs); cx = x
    for ch in text:
        if ch == " ":
            cx += gs[cm[32]].width * s + tr; continue
        g = cm[ord(ch)]
        gs[g].draw(TransformPen(pen, (s, 0, 0, -s, cx, y)))
        cx += gs[g].width * s + tr
    return pen.getCommands(), cx - x - tr


def w(font, text, size, tr=0):
    return pt(font, text, size, 0, 0, tr)[1]


def mono(cx, base, size, hcol, scol, barcol, gap=None):
    gap = size * 0.08 if gap is None else gap
    hx0, hx1 = gb(f900, "H", size); sx0, sx1 = gb(f900, "S", size)
    iw = (hx1 - hx0) + gap + (sx1 - sx0); left = cx - iw / 2
    hp, _ = pt(f900, "H", size, left - hx0, base)
    sp, _ = pt(f900, "S", size, left + (hx1 - hx0) + gap - sx0, base)
    bh = size * 0.08
    return (f'<g id="mono-H"><path fill="{hcol}" d="{hp}"/></g>'
            f'<g id="mono-S"><path fill="{scol}" d="{sp}"/></g>'
            f'<rect id="mono-bar" x="{left:.2f}" y="{base + size * 0.14:.2f}" width="{iw:.2f}" height="{bh:.2f}" fill="{barcol}"/>'), iw


def svg(vw, vh, bg, body, px):
    b = f'<rect id="bg" width="{vw}" height="{vh}" fill="{bg}"/>' if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vw} {vh}" width="{vw*px}" height="{vh*px}">\n'
            f'  {b}\n  {body}\n</svg>\n')


# ---- horizontal lockup 1000x360: monogram left | divider | name stack
def lockup(bg, main, accent):
    m, mw = mono(0, 0, 1, main, accent, accent)  # dummy for width calc
    msize = 150
    _, mw = mono(0, 0, msize, main, accent, accent)
    n1, n2, sub = "HASANHON", "SULTONOV", "VOCALS + DRUMS"
    s1, s2, s3, t3 = 74, 74, 26, 7
    w1, w2, w3 = w(f900, n1, s1), w(f900, n2, s2, 0), w(f800, sub, s3, t3)
    tw = max(w1, w2, w3)
    gap = 46
    total = mw + gap * 2 + 6 + tw
    x0 = (1000 - total) / 2
    mbody, _ = mono(x0 + mw / 2, 222, msize, main, accent, accent)
    dx = x0 + mw + gap
    tx = dx + 6 + gap
    p1, _ = pt(f900, n1, s1, tx, 150)
    p2, _ = pt(f900, n2, s2, tx, 228)
    p3, _ = pt(f800, sub, s3, tx, 278, t3)
    body = (f'<g id="monogram">{mbody}</g>\n'
            f'  <rect id="divider" x="{dx:.2f}" y="82" width="6" height="210" fill="{accent}"/>\n'
            f'  <g id="name-1"><path fill="{main}" d="{p1}"/></g>\n'
            f'  <g id="name-2"><path fill="{main}" d="{p2}"/></g>\n'
            f'  <g id="subtitle"><path fill="{accent}" d="{p3}"/></g>')
    return body


# ---- stacked (centered) 600x600
def stacked(bg, main, accent):
    mbody, mw = mono(300, 250, 190, main, accent, accent)
    n, sub = "HASANHON SULTONOV", "VOCALS + DRUMS"
    s1, s3 = 44, 22
    w1, w3 = w(f900, n, s1, 1), w(f800, sub, s3, 8)
    p1, _ = pt(f900, n, s1, 300 - w1 / 2, 380, 1)
    p3, _ = pt(f800, sub, s3, 300 - w3 / 2, 428, 8)
    return (f'<g id="monogram">{mbody}</g>\n'
            f'  <g id="name"><path fill="{main}" d="{p1}"/></g>\n'
            f'  <g id="subtitle"><path fill="{accent}" d="{p3}"/></g>')


# ---- round avatar 300
def avatar(bg, main, accent, ring):
    mbody, _ = mono(150, 192, 140, main, accent, accent)
    return (f'<defs><clipPath id="c"><circle cx="150" cy="150" r="150"/></clipPath></defs>\n'
            f'  <circle id="bg" cx="150" cy="150" r="150" fill="{bg}"/>\n'
            f'  <g id="monogram">{mbody}</g>\n'
            f'  <circle id="ring" cx="150" cy="150" r="144" fill="none" stroke="{ring}" stroke-width="8"/>')


files = {
    "HS_logo_horizontal_black.svg": svg(1000, 360, BLACK, lockup(BLACK, WHITE, RED), 3),
    "HS_logo_horizontal_white.svg": svg(1000, 360, WHITE, lockup(WHITE, BLACK, RED), 3),
    "HS_logo_horizontal_transparent.svg": svg(1000, 360, None, lockup(None, BLACK, RED), 3),
    "HS_logo_stacked_black.svg": svg(600, 520, BLACK, stacked(BLACK, WHITE, RED), 2),
    "HS_logo_stacked_white.svg": svg(600, 520, WHITE, stacked(WHITE, BLACK, RED), 2),
}
av = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 300" width="1200" height="1200">\n  {}\n</svg>\n'
files["HS_avatar_black.svg"] = av.format(avatar(BLACK, WHITE, RED, RED))
files["HS_avatar_white.svg"] = av.format(avatar(WHITE, BLACK, RED, BLACK))
for n, c in files.items():
    open(os.path.join(OUT, n), "w").write(c)
print("ok")
