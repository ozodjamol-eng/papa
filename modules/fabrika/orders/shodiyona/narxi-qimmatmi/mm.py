"""Мебельный моушн-модуль PAPA (Shodiyona и др.): «Чертёж → изделие» и «Журнальный разворот».
Вход: фото изделия на светлом фоне. Выход: кадры 1920×1080 (BGR numpy)."""
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont
W, H = 1920, 1080
FD = '/usr/share/fonts/opentype/inter/'
GREEN, OAK, WALNUT = (40, 58, 31), (74, 129, 184), (30, 66, 116)  # BGR
def font(n, s): return ImageFont.truetype(FD + n, s)
def eo(x): x = min(1, max(0, x)); return 1 - (1 - x) ** 3
def ei(x): x = min(1, max(0, x)); return x ** 3
def ez(x): x = min(1, max(0, x)); return 4*x**3 if x < .5 else 1 - (-2*x+2)**3/2

def background(grid=False):
    yy, xx = np.mgrid[0:H, 0:W]; r = np.clip(np.sqrt(((xx-W/2)/(W*.62))**2 + ((yy-H*.45)/(H*.62))**2), 0, 1)
    f = np.dstack([255 - 44*r, 255 - 30*r, 255 - 22*r]).astype(np.float32)
    if grid:
        g = np.zeros((H, W), np.float32); g[::40, :] = 1; g[:, ::40] = 1; g[::200, :] = 2.2; g[:, ::200] = 2.2
        f -= g[..., None] * np.array([3.0, 4.0, 6.0])
    return np.clip(f, 0, 255).astype(np.uint8)

def cutout(path):
    im = cv2.imread(path); h, w = im.shape[:2]
    border = np.concatenate([im[:4].reshape(-1, 3), im[-4:].reshape(-1, 3), im[:, :4].reshape(-1, 3), im[:, -4:].reshape(-1, 3)])
    bg = np.median(border, 0); near = (np.abs(im.astype(np.int16) - bg).max(2) < 22).astype(np.uint8)
    m = near.copy(); ffm = np.zeros((h+2, w+2), np.uint8)
    for x, y in [(0, 0), (w-1, 0), (0, h-1), (w-1, h-1), (w//2, 0), (w//2, h-1), (0, h//2), (w-1, h//2)]:
        if m[y, x] == 1: cv2.floodFill(m, ffm, (x, y), 2)
    fg = cv2.morphologyEx((m != 2).astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(fg); keep = np.zeros_like(fg)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] > 0.002*h*w: keep[lab == i] = 1
    fg = cv2.erode(keep, np.ones((3, 3), np.uint8)); a = cv2.GaussianBlur(fg.astype(np.float32), (0, 0), 1.2)
    ys, xs = np.where(fg > 0); y0, y1, x0, x1 = ys.min(), ys.max()+1, xs.min(), xs.max()+1
    return np.dstack([im, (a*255).astype(np.uint8)])[y0:y1, x0:x1]

def place(rgba, hgt):
    s = hgt / rgba.shape[0]; return cv2.resize(rgba, (int(rgba.shape[1]*s), int(hgt)), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)

def blend(f, rgba, x0, y0, alpha=1.0, mask=None):
    h, w = rgba.shape[:2]; X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(W, x0+w), min(H, y0+h)
    if X1 <= X0 or Y1 <= Y0 or alpha <= 0: return f
    sub = rgba[Y0-y0:Y1-y0, X0-x0:X1-x0]; al = sub[..., 3:4].astype(np.float32)/255*alpha
    if mask is not None: al = al * mask[Y0-y0:Y1-y0, X0-x0:X1-x0, None]
    f[Y0:Y1, X0:X1] = (f[Y0:Y1, X0:X1]*(1-al) + sub[..., :3]*al).astype(np.uint8); return f

def floor_shadow(f, cx, y, w, k):
    hh = max(8, int(w*0.06)); Y0, Y1, X0, X1 = max(0, y-hh), min(H, y+hh), max(0, cx-w//2), min(W, cx+w//2)
    yy, xx = np.mgrid[Y0:Y1, X0:X1]; e = np.exp(-(((xx-cx)/(w/2))**2 + ((yy-y)/hh)**2)*2.2)*0.24*k
    f[Y0:Y1, X0:X1] = (f[Y0:Y1, X0:X1]*(1 - e[..., None]*np.array([0.75, 0.8, 0.85]))).astype(np.uint8); return f

def overlay(f, L):
    a = np.array(L, np.float32); m = a[..., 3:4]/255; return (f[..., ::-1]*(1-m) + a[..., :3]*m)[..., ::-1].astype(np.uint8)

# ------------------------------------------------ 1. ЧЕРТЁЖ → ИЗДЕЛИЕ
class Blueprint:
    def __init__(self, photo, title, sub, dims=None, hgt=700, cx=760):
        self.p = place(cutout(photo), hgt); h, w = self.p.shape[:2]
        self.x0, self.y0 = cx - w//2, (H - h)//2 + 10; self.w, self.h = w, h
        g = cv2.cvtColor(self.p[..., :3], cv2.COLOR_BGR2GRAY); a = self.p[..., 3]
        e = cv2.Canny(cv2.GaussianBlur(g, (0, 0), 1.4), 40, 110); e[a < 128] = 0
        outline = cv2.morphologyEx((a > 128).astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))
        lines = np.maximum(e > 0, outline > 0).astype(np.float32)
        self.lines = cv2.GaussianBlur(cv2.dilate(lines, np.ones((2, 2), np.uint8)), (0, 0), 0.7)
        # порядок прорисовки: по диагонали сверху-слева → вниз-вправо с «шумом» пера
        yy, xx = np.mgrid[0:h, 0:w]; self.order = (xx/w*0.55 + yy/h*0.45) + np.random.default_rng(1).normal(0, .02, (h, w))
        self.title, self.sub, self.dims = title, sub, dims
        self.bg = background(grid=True)
    def frame(self, t, D=5.5):
        f = self.bg.copy(); h, w = self.h, self.w
        # линии чертежа
        pd = ez(t/1.9); rev = np.clip((pd*1.08 - self.order)/0.05, 0, 1); fade = 1 - 0.8*ez((t-2.4)/0.7)
        ln = self.lines*rev*fade; sl = (slice(self.y0, self.y0+h), slice(self.x0, self.x0+w))
        f[sl] = (f[sl]*(1 - ln[..., None]*0.9) + np.array(GREEN)*ln[..., None]*0.9).astype(np.uint8)
        # «перо»
        if 0.05 < t < 1.95:
            cand = np.argwhere((np.abs(self.order - pd*1.08) < 0.012) & (self.lines > 0.3))
            if len(cand):
                py, px = cand[len(cand)//2]; cv2.circle(f, (self.x0+px, self.y0+py), 7, (120, 200, 255), -1, cv2.LINE_AA)
                gl = np.zeros((H, W), np.float32); cv2.circle(gl, (self.x0+px, self.y0+py), 26, 1, -1, cv2.LINE_AA); gl = cv2.GaussianBlur(gl, (0, 0), 12)
                f = np.clip(f + gl[..., None]*np.array([30, 120, 200]), 0, 255).astype(np.uint8)
        # размерные линии
        k = eo((t-1.1)/0.9); fd = fade if t > 2.4 else 1
        L = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L); a = int(255*k*(0.35 + 0.65*fd)); col = (31, 58, 40, a)
        if k > 0:
            yb = self.y0 + h + 34; xm = self.x0 + w/2; half = w/2*k
            d.line([(xm-half, yb), (xm+half, yb)], fill=col, width=2)
            for x in (xm-half, xm+half): d.line([(x, yb-10), (x, yb+10)], fill=col, width=2)
            xr = self.x0 + w + 34; ym = self.y0 + h/2; hv = h/2*k
            d.line([(xr, ym-hv), (xr, ym+hv)], fill=col, width=2)
            for y in (ym-hv, ym+hv): d.line([(xr-10, y), (xr+10, y)], fill=col, width=2)
            if self.dims:
             fm = font('Inter-Medium.otf', 28)
             tw = d.textlength(self.dims[0], font=fm); d.text((xm - tw/2, yb + 14), self.dims[0], font=fm, fill=col)
             d.text((xr + 18, ym - 16), self.dims[1], font=fm, fill=col)
        f = overlay(f, L)
        # заливка фото снизу вверх
        if t > 2.0:
            q = ez((t-2.0)/0.9); mask = np.clip(((1 - np.arange(h)/h)[:, None] - (1 - q*1.15))/0.15 + 1, 0, 1)
            mask = np.repeat(mask, w, 1); f = floor_shadow(f, self.x0 + w//2, self.y0 + h - 6, int(w*0.85), q)
            f = blend(f, self.p, self.x0, self.y0, 1.0, mask)
        # блик
        if 3.0 < t < 3.8:
            q = (t-3.0)/0.8; band = np.zeros((h, w), np.float32); xs = np.arange(w) - (q*1.6 - 0.3)*w; yy = np.arange(h)[:, None]*0.35
            band = np.exp(-((xs[None, :] + yy - 0)/(w*0.06))**2)*0.35*(self.p[..., 3]/255)
            sl = (slice(self.y0, self.y0+h), slice(self.x0, self.x0+w)); f[sl] = np.clip(f[sl] + band[..., None]*255, 0, 255).astype(np.uint8)
        # подпись
        k2 = eo((t-3.1)/0.8)
        if k2 > 0:
            L = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L); a = int(255*k2); x = 1300 + 60*(1-k2)
            d.text((x, 430), self.title, font=font('InterDisplay-Bold.otf', 76), fill=(31, 58, 40, a))
            d.rectangle([x, 530, x + 90*k2, 533], fill=(184, 129, 74, a))
            y = 560
            for ln in self.sub.split('\n'): d.text((x, y), ln, font=font('Inter-Regular.otf', 32), fill=(70, 70, 70, a)); y += 46
            f = overlay(f, L)
        return cv2.warpAffine(f, np.float32([[1+0.02*t/D, 0, -W*0.01*t/D], [0, 1+0.02*t/D, -H*0.01*t/D]]), (W, H), borderMode=cv2.BORDER_REFLECT)

# ------------------------------------------------ 2. ЖУРНАЛЬНЫЙ РАЗВОРОТ
class Spread:
    """pages: [(photo, КАТЕГОРИЯ, Название, [(x_rel, y_rel, 'выноска'), ...])]; каждая страница dur секунд, между ними шторка."""
    def __init__(self, pages, dur=2.8, hgt=640):
        self.pages = []
        for photo, cat, name, calls in pages:
            calls = sorted(calls, key=lambda c: c[1])
            p = place(cutout(photo), hgt); self.pages.append((p, cat, name, calls))
        self.dur = dur; self.bg = background()
        self.FC = font('InterDisplay-Bold.otf', 330); self.FN = font('InterDisplay-Bold.otf', 58); self.FL = font('Inter-SemiBold.otf', 40)
    def page(self, i, t):
        p, cat, name, calls = self.pages[i]; f = self.bg.copy(); h, w = p.shape[:2]
        # огромные контурные буквы категории
        L = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
        k = eo(t/0.7); FC = self.FC; tw = d.textlength(cat, font=FC)
        if tw > W*0.92: FC = font('InterDisplay-Bold.otf', int(330*W*0.92/tw)); tw = d.textlength(cat, font=FC)
        x = (W - tw)/2 + 220*(1-k) - 30*t
        d.text((x, 190), cat, font=FC, fill=(0, 0, 0, 0), stroke_width=3, stroke_fill=(184, 129, 74, int(150*k)))
        f = overlay(f, L)
        # изделие поднимается
        k2 = eo((t-0.2)/0.7); cx = 820 + 12*t; y0 = (H-h)//2 - 10 + int(70*(1-k2))
        f = floor_shadow(f, int(cx), y0 + h - 6, int(w*0.85), k2); f = blend(f, p, int(cx - w/2), y0, k2)
        # название + выноски
        L = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
        k3 = eo((t-0.6)/0.6); a = int(255*k3)
        d.text((120, 70 + 20*(1-k3)), name, font=self.FN, fill=(31, 58, 40, a)); d.rectangle([120, 150, 120 + 120*k3, 153], fill=(184, 129, 74, a))
        for j, (xr, yr, txt) in enumerate(calls):
            kk = eo((t - 0.9 - 0.25*j)/0.5)
            if kk <= 0: continue
            px, py = cx - w/2 + xr*w, y0 + yr*h; lx = 1380; ly = 300 + j*130
            ex, ey = px + (lx - px)*kk, py + (ly - py)*kk
            d.ellipse([px-7, py-7, px+7, py+7], fill=(184, 129, 74, int(255*kk))); d.line([(px, py), (ex, ey)], fill=(184, 129, 74, int(255*kk)), width=2)
            if kk > 0.95: d.line([(lx, ly), (lx + 40, ly)], fill=(184, 129, 74, 255), width=2); d.text((lx + 52, ly - 25), txt, font=self.FL, fill=(31, 58, 40, int(255*eo((t-1.3-0.25*j)/0.4))))
        return overlay(f, L)
    def frame(self, t):
        i = min(int(t // self.dur), len(self.pages)-1); lt = t - i*self.dur; f = self.page(i, lt)
        # шторка фирменного зелёного между страницами
        if i < len(self.pages)-1 and lt > self.dur - 0.45:
            q = ez((lt - (self.dur - 0.45))/0.45); xw = int(W*q); f[:, :xw] = (31, 58, 40)[::-1] if False else (40, 58, 31)
        if i > 0 and lt < 0.45:
            q = ez(lt/0.45); xw = int(W*q); f[:, xw:] = (40, 58, 31)
        return f

def render(frames_fn, D, out, fps=30, audio=None):
    import subprocess
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-']
                          + (['-ss', '20', '-i', audio, '-shortest', '-af', f'afade=t=in:d=0.4,afade=t=out:st={D-0.6}:d=0.6', '-c:a', 'aac'] if audio else [])
                          + ['-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
    for n in range(int(D*fps)): ff.stdin.write(np.ascontiguousarray(frames_fn(n/fps)).tobytes())
    ff.stdin.close(); ff.wait()
