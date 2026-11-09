"""LOVE GO motion engine (PIL + OpenCV), 1080x1920 @30."""
import math, random, subprocess, glob
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
P = '/home/claude/papa/'
BLACK = P + 'modules/fabrika/motion/weather/fonts/InterDisplay-Black.otf'
XBOLD = P + 'modules/fabrika/motion/weather/fonts/InterDisplay-ExtraBold.otf'
A = '/home/claude/lg/'

def F(path, size): return ImageFont.truetype(path, size)

def premul(rgba_u8):
    a = rgba_u8.astype(np.float32) / 255.0
    a[..., :3] *= a[..., 3:4]
    return a

def pil2L(im): return premul(np.array(im.convert('RGBA')))

# ---------------- easing
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def eout(p): p = clamp(p); return 1 - (1 - p) ** 3
def einout(p): p = clamp(p); return 3 * p * p - 2 * p * p * p
def spring(t, d=0.5):
    if t <= 0: return 0.0
    p = t / d
    if p > 2.5: return 1.0
    return 1 - math.exp(-5.5 * p) * math.cos(9.5 * p)

# ---------------- compositing
def place(C, L, cx, cy, s=1.0, rot=0.0, a=1.0, blur=0):
    if a <= 0.003 or s <= 0.01: return
    h, w = L.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), rot, s)
    M[0, 2] += cx - w / 2; M[1, 2] += cy - h / 2
    pts = np.array([[0, 0, 1], [w, 0, 1], [0, h, 1], [w, h, 1]], np.float32) @ M.T
    x0 = int(max(0, math.floor(pts[:, 0].min()) - 2)); x1 = int(min(W, math.ceil(pts[:, 0].max()) + 2))
    y0 = int(max(0, math.floor(pts[:, 1].min()) - 2)); y1 = int(min(H, math.ceil(pts[:, 1].max()) + 2))
    if x1 <= x0 or y1 <= y0: return
    M2 = M.copy(); M2[0, 2] -= x0; M2[1, 2] -= y0
    R = cv2.warpAffine(L, M2, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR,
                       borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    if blur and blur > 1: R = cv2.blur(R, (int(blur), 1))
    if a < 1: R *= a
    roi = C[y0:y1, x0:x1]
    roi *= (1 - R[..., 3:4]); roi += R[..., :3]

def flash(C, a, col=(1, 1, 1)):
    if a <= 0: return
    C *= (1 - a); C += np.array(col, np.float32) * a

# ---------------- text
def grad_fill(size, top, mid, bot):
    w, h = size
    y = np.linspace(0, 1, h)[:, None]
    t, m, b = [np.array(c, np.float32) for c in (top, mid, bot)]
    g = np.where(y < 0.5, t + (m - t) * (y / 0.5), m + (b - m) * ((y - 0.5) / 0.5))
    g = np.ascontiguousarray(np.broadcast_to(g.reshape(h, 1, 3), (h, w, 3)))
    return Image.fromarray(np.clip(g, 0, 255).astype(np.uint8))

STYLES = {
    'white': ((255, 255, 255), (250, 246, 252), (226, 218, 236), (150, 120, 140), (95, 60, 70)),
    'gold':  ((255, 247, 180), (255, 205, 60), (232, 140, 0), (160, 80, 0), (105, 45, 0)),
    'blue':  ((120, 200, 255), (40, 140, 255), (20, 80, 220), (10, 40, 140), (5, 20, 80)),
}

def text_mask(s, font, track=0):
    l, t, r, b = font.getbbox(s)
    if track == 0:
        w = r - l; h = b - t
        m = Image.new('L', (w + 4, h + 4), 0)
        ImageDraw.Draw(m).text((2 - l, 2 - t), s, font=font, fill=255)
        return m
    widths = [font.getlength(c) for c in s]
    w = int(sum(widths) + track * (len(s) - 1)) + 8
    asc, desc = font.getmetrics(); h = asc + desc
    m = Image.new('L', (w, h + 4), 0); d = ImageDraw.Draw(m); x = 4
    for c, cw in zip(s, widths):
        d.text((x, 2), c, font=font, fill=255); x += cw + track
    bb = m.getbbox(); return m.crop(bb) if bb else m

def txt3d(s, size, style='white', font=BLACK, track=0, depth=None, maxw=None, shadow=True):
    if maxw:
        while size > 20 and text_mask(s, F(font, size), track).width > maxw: size -= 4
    f = F(font, size); m = text_mask(s, f, track)
    top, mid, bot, e1, e2 = STYLES[style]
    d = int(size * 0.07) if depth is None else depth
    pad = int(size * 0.25) + d
    Wd, Hd = m.width + 2 * pad, m.height + 2 * pad
    out = Image.new('RGBA', (Wd, Hd), (0, 0, 0, 0))
    if shadow:
        sh = Image.new('L', (Wd, Hd), 0); sh.paste(m, (pad, pad + d + int(size * .06)))
        sh = sh.filter(ImageFilter.GaussianBlur(size * 0.07))
        out.paste((40, 10, 0, 255), (0, 0), sh.point(lambda v: int(v * 0.45)))
    for i in range(d, 0, -1):
        k = i / max(d, 1)
        col = tuple(int(e1[j] * (1 - k) + e2[j] * k) for j in range(3))
        out.paste(col + (255,), (pad, pad + i), m)
    face = grad_fill(m.size, top, mid, bot)
    out.paste(face, (pad, pad), m)
    return pil2L(out)

def flat_txt(s, size, col, font=BLACK, track=0, maxw=None):
    if maxw:
        while size > 16 and text_mask(s, F(font, size), track).width > maxw: size -= 2
    m = text_mask(s, F(font, size), track)
    out = Image.new('RGBA', m.size, col + (0,)); out.putalpha(m)
    return pil2L(out)

def pill(s, size, bg=(255, 212, 59), fg=(90, 30, 0), font=BLACK, padx=None, pady=None, track=0, radius=None, maxw=None):
    if maxw:
        while size > 16 and text_mask(s, F(font, size), track).width + 2 * int(size * .7) > maxw: size -= 2
    m = text_mask(s, F(font, size), track)
    px = padx if padx is not None else int(size * 0.7); py = pady if pady is not None else int(size * 0.4)
    w, h = m.width + 2 * px, m.height + 2 * py
    sp = int(size * 0.25)
    out = Image.new('RGBA', (w + 2 * sp, h + 2 * sp), (0, 0, 0, 0))
    sh = Image.new('L', out.size, 0)
    ImageDraw.Draw(sh).rounded_rectangle([sp, sp + 6, sp + w, sp + h + 6], radius or h // 2, fill=120)
    sh = sh.filter(ImageFilter.GaussianBlur(8)); out.paste((60, 15, 0, 255), (0, 0), sh)
    ImageDraw.Draw(out).rounded_rectangle([sp, sp, sp + w, sp + h], radius or h // 2, fill=bg + (255,))
    out.paste(fg + (255,), (sp + px, sp + py), m)
    return pil2L(out)

# ---------------- background
_rng = random.Random(7)
def _bokeh(n, rmin, rmax, alpha, blur, size=(1500, 2500)):
    im = Image.new('RGBA', size, (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for _ in range(n):
        r = _rng.randint(rmin, rmax); x = _rng.randint(0, size[0]); y = _rng.randint(0, size[1])
        c = _rng.choice([(255, 170, 70), (255, 200, 110), (255, 140, 50), (255, 230, 160)])
        d.ellipse([x - r, y - r, x + r, y + r], fill=c + (int(255 * alpha * _rng.uniform(.5, 1)),))
    im = im.filter(ImageFilter.GaussianBlur(blur))
    return pil2L(im)

def _base():
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((x - W * .5) / W) ** 2 + ((y - H * .42) / H * 0.75) ** 2)
    c0 = np.array([250, 140, 35], np.float32) / 255; c1 = np.array([196, 62, 8], np.float32) / 255
    k = np.clip(d / 0.62, 0, 1)[..., None] ** 1.3
    return (c0 * (1 - k) + c1 * k).astype(np.float32)

BASE = _base()
BOK_FAR = _bokeh(60, 25, 70, 0.22, 10)
BOK_NEAR = _bokeh(14, 60, 140, 0.16, 22)

def _ray():
    im = Image.new('L', (420, 3200), 0); d = ImageDraw.Draw(im)
    d.polygon([(150, 0), (270, 0), (420, 3200), (0, 3200)], fill=70)
    im = im.filter(ImageFilter.GaussianBlur(60))
    a = np.array(im, np.float32) / 255
    L = np.zeros(a.shape + (4,), np.float32); L[..., :3] = a[..., None] * np.array([1, .9, .7]); L[..., 3] = a
    return L
RAY = _ray()

def bg(t):
    C = BASE.copy()
    place(C, RAY, W * .3 + 60 * math.sin(t * .5), H * .45, 1, 18 + 4 * math.sin(t * .4), .55)
    place(C, RAY, W * .78 - 50 * math.sin(t * .37), H * .5, 1, -14 + 3 * math.sin(t * .3), .4)
    ox = int(200 + 120 * math.sin(t * .25)); oy = int(300 + t * 18) % 500
    C[:] = C * (1 - BOK_FAR[oy:oy + H, ox:ox + W, 3:4]) + BOK_FAR[oy:oy + H, ox:ox + W, :3]
    ox = int(200 - 160 * math.sin(t * .3)); oy = int(500 - t * 40) % 500
    C[:] = C * (1 - BOK_NEAR[oy:oy + H, ox:ox + W, 3:4]) + BOK_NEAR[oy:oy + H, ox:ox + W, :3]
    return C

def vignette():
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((x - W / 2) / W) ** 2 + ((y - H / 2) / H) ** 2)
    return (1 - 0.35 * np.clip((d - .3) / .45, 0, 1) ** 2)[..., None].astype(np.float32)
VIG = vignette()

# ---------------- assets
def load_png(p, maxw=None, maxh=None, scale=1.0):
    im = Image.open(p).convert('RGBA')
    if maxw or maxh:
        s = min((maxw or 1e9) / im.width, (maxh or 1e9) / im.height); im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    return pil2L(im)

def sticker(L, border=10):
    """white sticker outline + soft shadow around a cut-out (premul float)."""
    a = (L[..., 3] * 255).astype(np.uint8)
    pad = border + 30
    a = cv2.copyMakeBorder(a, pad, pad, pad, pad, cv2.BORDER_CONSTANT, 0)
    Lp = cv2.copyMakeBorder(L, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=(0, 0, 0, 0))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * border + 1, 2 * border + 1))
    o = cv2.dilate(a, k).astype(np.float32) / 255
    o = cv2.GaussianBlur(o, (0, 0), 1.2)
    sh = cv2.GaussianBlur(o, (0, 0), 14)
    sh = np.roll(sh, 14, axis=0)
    out = np.zeros_like(Lp)
    out[..., 3] = sh * 0.45; out[..., :3] = np.array([.25, .06, 0]) * out[..., 3:4]
    wa = o[..., None]
    out = out * (1 - wa); out[..., :3] += wa * 1.0; out[..., 3:4] += wa
    out = out * (1 - Lp[..., 3:4]) + Lp
    return out

def make_logo():
    plate = np.array(Image.open(A + '../papa/modules/fabrika/orders/lovego/assets/logo_plate.png').convert('RGBA')).astype(np.float32)
    cart = plate[30:235, 35:280].copy()
    r, g, b = cart[..., 0], cart[..., 1], cart[..., 2]
    blu = np.clip((b - r + 20) / 80, 0, 1)
    ci = np.zeros(cart.shape, np.uint8); ci[..., :3] = cart[..., :3].astype(np.uint8); ci[..., 3] = (blu * 255).astype(np.uint8)
    cim = Image.fromarray(ci); cim = cim.crop(cim.getbbox())
    # boost cart colour
    arr = np.array(cim).astype(np.float32); arr[..., :3] = np.array([60, 170, 255]) * .55 + arr[..., :3] * .45
    cim = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    cim = cim.resize((int(cim.width * 230 / cim.height), 230), Image.LANCZOS)
    # white outline for cart
    cl = sticker(pil2L(cim), 9)
    name = txt3d('LOVE GO', 200, 'white')
    sub = flat_txt('КИЙИМ САВДО МАРКАЗИ', 50, (255, 255, 255), XBOLD, track=9)
    # assemble
    ch, cw = cl.shape[:2]; nh, nw = name.shape[:2]; sh_, sw = sub.shape[:2]
    Wt = cw + nw - 60; Ht = max(ch, nh) + sh_ + 10
    C = np.zeros((Ht, Wt, 4), np.float32)
    def put(L, x, y):
        h, w = L.shape[:2]; roi = C[y:y + h, x:x + w]; roi *= (1 - L[..., 3:4]); roi += L
    put(cl, 0, (max(ch, nh) - ch) // 2); put(name, cw - 60, (max(ch, nh) - nh) // 2)
    put(sub, (Wt - sw) // 2 + 40, max(ch, nh) - 10)
    return C

def icons():
    im = cv2.imread(A + 'ic.png')
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    m = ((hsv[..., 0] > 105) & (hsv[..., 0] < 135) & (hsv[..., 1] > 120)).astype(np.uint8)
    m = m * 255
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    f = np.zeros_like(m); cv2.drawContours(f, cs, -1, 255, -1)
    dt = cv2.distanceTransform(f, cv2.DIST_L2, 5)
    n, lab, st, cen = cv2.connectedComponentsWithStats((dt > 100).astype(np.uint8))
    out = []
    for i in range(1, n):
        cx, cy = cen[i]; r = 121
        x0, y0 = int(cx - r), int(cy - r); s = int(2 * r)
        crop = cv2.cvtColor(im[y0:y0 + s, x0:x0 + s], cv2.COLOR_BGR2RGB)
        a = np.zeros((s, s), np.float32); cv2.circle(a, (s // 2, s // 2), int(r - 3), 1.0, -1, cv2.LINE_AA)
        a = cv2.GaussianBlur(a, (0, 0), 1.0)
        L = np.zeros((s, s, 4), np.float32); L[..., :3] = crop / 255 * a[..., None]; L[..., 3] = a
        out.append((cy, cx, L))
    out.sort(key=lambda z: (round(z[0] / 150), z[1]))
    return [o[2] for o in out]

def pin_pill(line1, line2, maxw=940):
    f1 = F(BLACK, 54); f2 = F(XBOLD, 40)
    s2 = 40
    while F(XBOLD, s2).getlength(line2) > maxw - 210 and s2 > 24: s2 -= 2
    f2 = F(XBOLD, s2)
    w = int(max(f1.getlength(line1), f2.getlength(line2))) + 210; h = 190
    sp = 24
    im = Image.new('RGBA', (w + 2 * sp, h + 2 * sp), (0, 0, 0, 0))
    sh = Image.new('L', im.size, 0); ImageDraw.Draw(sh).rounded_rectangle([sp, sp + 10, sp + w, sp + h + 10], 44, fill=140)
    im.paste((50, 12, 0, 255), (0, 0), sh.filter(ImageFilter.GaussianBlur(12)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([sp, sp, sp + w, sp + h], 44, fill=(255, 255, 255, 255))
    # pin
    px, py = sp + 85, sp + 78
    d.ellipse([px - 42, py - 42, px + 42, py + 42], fill=(232, 50, 30, 255))
    d.polygon([(px - 36, py + 20), (px + 36, py + 20), (px, py + 82)], fill=(232, 50, 30, 255))
    d.ellipse([px - 16, py - 16, px + 16, py + 16], fill=(255, 255, 255, 255))
    d.text((sp + 165, sp + 30), line1, font=f1, fill=(230, 85, 10))
    d.text((sp + 165, sp + 112), line2, font=f2, fill=(30, 20, 20))
    return pil2L(im)

def clock_face(r=330):
    s = 2 * r + 80
    im = Image.new('RGBA', (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = s / 2
    sh = Image.new('L', (s, s), 0); ImageDraw.Draw(sh).ellipse([c - r, c - r + 18, c + r, c + r + 18], fill=150)
    im.paste((60, 15, 0, 255), (0, 0), sh.filter(ImageFilter.GaussianBlur(18)))
    d.ellipse([c - r, c - r, c + r, c + r], fill=(255, 255, 255, 255))
    d.ellipse([c - r + 16, c - r + 16, c + r - 16, c + r - 16], outline=(255, 140, 30, 255), width=10)
    for i in range(60):
        a = i / 60 * 2 * math.pi; big = i % 5 == 0
        r1 = r - 40; r2 = r - (90 if big else 60)
        d.line([(c + r1 * math.sin(a), c - r1 * math.cos(a)), (c + r2 * math.sin(a), c - r2 * math.cos(a))],
               fill=(60, 30, 20, 255) if big else (190, 170, 160, 255), width=12 if big else 4)
    return pil2L(im)

def hand(length, width, col):
    im = Image.new('RGBA', (width + 20, 2 * length + 20), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    cx = (width + 20) / 2; cy = length + 10
    d.rounded_rectangle([cx - width / 2, cy - length, cx + width / 2, cy + 30], width // 2, fill=col + (255,))
    return pil2L(im)

def load_facade():
    return [cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2RGB).astype(np.float32) / 255 for p in sorted(glob.glob(A + 'fac/*.jpg'))]

def zoom_frame(img, s, cy=0.5):
    if s <= 1.0001: return img.copy()
    M = np.array([[s, 0, W / 2 * (1 - s)], [0, s, H * cy * (1 - s)]], np.float32)
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

# ---------------- confetti
class Confetti:
    def __init__(self, n=140, seed=3):
        r = random.Random(seed); self.p = []
        cols = [(1, .85, .2), (1, 1, 1), (.25, .6, 1), (1, .5, .1), (1, .3, .4)]
        for _ in range(n):
            self.p.append(dict(x=r.uniform(-50, W + 50), y=r.uniform(-900, -20), vx=r.uniform(-60, 60), vy=r.uniform(250, 520),
                               w=r.uniform(10, 22), h=r.uniform(6, 12), rot=r.uniform(0, 6.28), vr=r.uniform(-8, 8),
                               ph=r.uniform(0, 6.28), c=r.choice(cols)))
    def draw(self, C, t):
        if t < 0: return
        for q in self.p:
            x = q['x'] + q['vx'] * t + 30 * math.sin(t * 3 + q['ph']); y = q['y'] + q['vy'] * t
            if y < -30 or y > H + 30: continue
            a = q['rot'] + q['vr'] * t; sq = abs(math.cos(t * 5 + q['ph']))
            w, h = q['w'], q['h'] * (0.3 + sq)
            ca, sa = math.cos(a), math.sin(a)
            pts = np.array([[x + ca * dx - sa * dy, y + sa * dx + ca * dy] for dx, dy in [(-w, -h), (w, -h), (w, h), (-w, h)]], np.int32)
            cv2.fillPoly(C, [pts], q['c'], cv2.LINE_AA)

# ---------------- whip between two scene renderers
def whip(fa, fb, t, b, d=0.24, direction=-1):
    p = clamp((t - (b - d / 2)) / d); e = einout(p)
    A_ = fa(t); B_ = fb(t)
    k = int(1 + 90 * math.sin(math.pi * p))
    off = int(direction * e * W)
    out = np.zeros_like(A_)
    def sh(img, dx):
        M = np.float32([[1, 0, dx], [0, 1, 0]])
        return cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    A2 = sh(A_, off); B2 = sh(B_, off - direction * W)
    m = (np.arange(W) < (W + off) if direction < 0 else np.arange(W) >= off)[None, :, None]
    out = np.where(m, A2, B2)
    if k > 1: out = cv2.blur(out, (k, 1))
    return out

class Writer:
    def __init__(self, path):
        self.p = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                                   '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '14', '-pix_fmt', 'yuv420p',
                                   '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', path], stdin=subprocess.PIPE)
    def write(self, C):
        self.p.stdin.write((np.clip(C, 0, 1) * 255 + .5).astype(np.uint8).tobytes())
    def close(self):
        self.p.stdin.close(); self.p.wait()
