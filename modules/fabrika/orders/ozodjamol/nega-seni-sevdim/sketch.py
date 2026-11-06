"""Мастерская художника: фото → рисунок тушью → карта времени прорисовки (штрих за штрихом).
prep(photo) -> RGBA рисунка; tmap(line) -> для каждого пикселя линии время появления 0..1."""
import numpy as np, cv2, onnxruntime as ort
from PIL import Image
from collections import deque

_S = None
def lineart(img_rgb, width=900):
    global _S
    if _S is None: _S = ort.InferenceSession('/home/claude/song/lineart/model.onnx')
    w, h = img_rgb.size; H = int(h*width/w)//8*8
    x = np.array(img_rgb.resize((width, H), Image.LANCZOS), np.float32)/255.
    y = _S.run(None, {_S.get_inputs()[0].name: x.transpose(2, 0, 1)[None]})[0][0, 0]
    return np.clip(y, 0, 1)           # 1 = бумага, 0 = тушь

def cutout(img_rgb):
    from rembg import remove, new_session
    m = remove(img_rgb, session=new_session('u2net_human_seg'), only_mask=True)
    return np.array(m.resize(img_rgb.size))/255.

def ink_from_photo(path, width=900, keep_bg=False):
    im = Image.open(path).convert('RGB')
    la = lineart(im, width)                    # (H,W)
    ink = 1-la                                  # 1 = тушь
    if not keep_bg:
        m = cutout(im); m = cv2.resize(m.astype(np.float32), (ink.shape[1], ink.shape[0]))
        m = cv2.dilate((m > .5).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(np.float32)
        m = cv2.GaussianBlur(m, (0, 0), 3)
        ink *= m
    ink = np.clip((ink-0.12)/0.6, 0, 1)**0.9    # чистка серого шума
    return ink

def _skeleton(binm):
    sk = cv2.ximgproc.thinning(binm*255) if hasattr(cv2, 'ximgproc') else None
    if sk is None:   # морфологический скелет
        img = binm.copy()*255; sk = np.zeros_like(img); el = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
        while cv2.countNonZero(img):
            er = cv2.erode(img, el); op = cv2.dilate(er, el); sk |= cv2.subtract(img, op); img = er
    return (sk > 0).astype(np.uint8)

def tmap(ink, order='topdown', seed=0):
    """время появления для каждого пикселя туши: обход скелета компонентами, как рука художника"""
    binm = (ink > 0.25).astype(np.uint8)
    sk = _skeleton(binm)
    n, lab, st, _ = cv2.connectedComponentsWithStats(sk, connectivity=8)
    comps = [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] >= 6]
    if order == 'topdown':
        big = np.percentile([st[i, cv2.CC_STAT_AREA] for i in comps], 80) if comps else 0
        comps.sort(key=lambda i: (st[i, cv2.CC_STAT_AREA] < big, st[i, cv2.CC_STAT_TOP]//90, -st[i, cv2.CC_STAT_AREA]))
    T = np.full(sk.shape, np.inf, np.float32)
    total = sum(st[i, cv2.CC_STAT_AREA] for i in comps) or 1
    clock = 0.0
    nb = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    for i in comps:
        ys, xs = np.where(lab == i)
        start = np.argmin(ys*4+xs)              # верхняя-левая точка — начало штриха
        q = deque([(ys[start], xs[start])]); T[ys[start], xs[start]] = clock; step = 0
        while q:
            y, x = q.popleft(); step += 1
            for dy, dx in nb:
                yy, xx = y+dy, x+dx
                if 0 <= yy < sk.shape[0] and 0 <= xx < sk.shape[1] and lab[yy, xx] == i and T[yy, xx] == np.inf:
                    T[yy, xx] = clock + step/total; q.append((yy, xx))
        clock += st[i, cv2.CC_STAT_AREA]/total
    # распространить время скелета на всю толщину линии
    src = np.where(np.isfinite(T), 0, 1).astype(np.uint8)
    _, idx = cv2.distanceTransformWithLabels(src, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    ys, xs = np.where(src == 0); lut = np.zeros(idx.max()+1, np.float32); lut[idx[ys, xs]] = T[ys, xs]
    full = lut[idx]
    full[binm == 0] = np.maximum(full[binm == 0], 0)  # слабые штрихи — по ближайшему
    return np.clip(full/max(clock, 1e-6), 0, 1)

def reveal(ink, tm, p, soft=0.012):
    """доля прорисовки p (0..1) → альфа туши"""
    a = np.clip((p - tm)/soft, 0, 1)
    return ink*a
