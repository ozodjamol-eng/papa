"""Обрезка фото для постов Хотира (19.10).

Люди часто присылают не фото, а скриншот экрана (редактор обрезки, галерея, чат): сверху строка состояния,
по краям чёрные/белые поля, внизу кнопки. Здесь:
- region(img)  — находит само фото внутри скриншота (поле = цвет краёв, текст/кнопки отбрасываются);
- auto(data)   — если это скриншот → JPEG только с фото, иначе None;
- face(data)   — портретный кадр по лицу (самое крупное лицо), иначе None.
OpenCV (opencv-python-headless) — бесплатно, работает на сервере. Если его нет — available() = False, бот работает как раньше."""
from __future__ import annotations

try:
    import cv2
    import numpy as np
    cv2.setNumThreads(1)                       # 1 vCPU, TasksMax=8 у службы
except Exception:  # noqa: BLE001 — без OpenCV бот работает, просто без обрезки
    cv2 = np = None

import os

MODEL = os.path.join(os.path.dirname(__file__), "models", "face_detection_yunet_2023mar.onnx")
WORK = 600         # анализ на уменьшенной копии (быстро и мало памяти), режем оригинал
MIN_AREA = 0.12     # фото меньше 12 % экрана — не доверяем, ничего не режем
SCREEN = 0.86       # найденное фото < 86 % картинки → это скриншот с лишним


def available() -> bool:
    return cv2 is not None


def decode(data: bytes):
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("не картинка")
    return img


def encode(img) -> bytes:
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 93])
    if not ok:
        raise ValueError("jpeg")
    return buf.tobytes()


def region(img) -> tuple[int, int, int, int] | None:
    """→ (x, y, w, h) фото внутри картинки в координатах оригинала, или None."""
    H, W = img.shape[:2]
    k = WORK / max(H, W)
    sm = cv2.resize(img, (max(1, round(W * k)), max(1, round(H * k))), interpolation=cv2.INTER_AREA) if k < 1 else img.copy()
    k = min(k, 1.0)
    h, w = sm.shape[:2]
    lab = cv2.cvtColor(sm, cv2.COLOR_BGR2LAB).astype(np.int16)
    b = max(2, round(min(h, w) * 0.02))
    border = np.concatenate([lab[:b].reshape(-1, 3), lab[-b:].reshape(-1, 3), lab[:, :b].reshape(-1, 3), lab[:, -b:].reshape(-1, 3)])
    bg = np.median(border, axis=0)
    mask = (np.abs(lab - bg).sum(axis=2) > 28).astype(np.uint8)       # всё, что отличается от поля
    r = max(3, round(w * 0.035))                                         # текст и тонкие кнопки — прочь
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (r, r)))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (r, r)))
    n, _, st, _ = cv2.connectedComponentsWithStats(mask, 8)
    if n < 2:
        return None
    i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    x, y, cw, ch = (int(v) for v in st[i, :4])
    if cw * ch < MIN_AREA * w * h:
        return None
    # поджать края: строки/столбцы, где много поля (повёрнутое фото, тени) — срезать
    sub = mask[y:y + ch, x:x + cw]
    rows, cols = sub.mean(axis=1), sub.mean(axis=0)
    t, btm = 0, ch
    while t < btm - 1 and rows[t] < 0.9:
        t += 1
    while btm - 1 > t and rows[btm - 1] < 0.9:
        btm -= 1
    lft, rgt = 0, cw
    while lft < rgt - 1 and cols[lft] < 0.9:
        lft += 1
    while rgt - 1 > lft and cols[rgt - 1] < 0.9:
        rgt -= 1
    x, y, cw, ch = x + lft, y + t, rgt - lft, btm - t
    pad = 2                                                              # пара пикселей внутрь — без полоски поля
    X, Y = int((x + pad) / k), int((y + pad) / k)
    X2, Y2 = int((x + cw - pad) / k), int((y + ch - pad) / k)
    X, Y, X2, Y2 = max(0, X), max(0, Y), min(W, X2), min(H, Y2)
    if X2 - X < 50 or Y2 - Y < 50:
        return None
    return X, Y, X2 - X, Y2 - Y


def is_screenshot(img) -> bool:
    r = region(img)
    H, W = img.shape[:2]
    return bool(r) and r[2] * r[3] < SCREEN * W * H


def auto(data: bytes) -> bytes | None:
    """Скриншот → JPEG только с самим фото. Обычное фото → None (не трогаем)."""
    img = decode(data)
    r = region(img)
    H, W = img.shape[:2]
    if not r or r[2] * r[3] >= SCREEN * W * H:
        return None
    x, y, w, h = r
    return encode(img[y:y + h, x:x + w])


def face(data: bytes) -> bytes | None:
    """Портрет 4:5 по самому крупному лицу (сначала убираем поля скриншота). Лица нет → None."""
    img = decode(data)
    r = region(img)
    if r and r[2] * r[3] < SCREEN * img.shape[0] * img.shape[1]:
        x, y, w, h = r
        img = img[y:y + h, x:x + w]
    H, W = img.shape[:2]
    k = min(1.0, 800 / max(H, W))
    sm = cv2.resize(img, (round(W * k), round(H * k)), interpolation=cv2.INTER_AREA) if k < 1 else img
    det = cv2.FaceDetectorYN.create(MODEL, "", (sm.shape[1], sm.shape[0]), 0.7, 0.3, 50)
    _, faces = det.detect(sm)
    if faces is None or len(faces) == 0:
        return None
    fx, fy, fw, fh = (float(v) / k for v in max(faces, key=lambda f: f[2] * f[3])[:4])
    cw = min(W, fw * 2.6)                       # плечи и немного фона
    ch = min(H, cw * 1.25)
    cw = min(cw, ch / 1.25)
    cx, cy = fx + fw / 2, fy + fh / 2
    x0 = int(min(max(0, cx - cw / 2), W - cw))
    y0 = int(min(max(0, cy - ch * 0.40), H - ch))   # лицо чуть выше центра, как на портрете
    return encode(img[y0:y0 + int(ch), x0:x0 + int(cw)])


def enhance(data: bytes) -> bytes:
    """«✨ Улучшить»: мягко — локальный автоконтраст (лицо в тени светлеет), снять жёлтый/синий оттенок, чуть резкости.
    Лица умерших родные знают — поэтому всё слабо, без «фильтров»."""
    img = decode(data)
    f = img.astype(np.float32)
    mean = f.reshape(-1, 3).mean(axis=0)                              # серый мир: убрать цветной оттенок лампы
    gain = np.clip(mean.mean() / np.maximum(mean, 1), 0.8, 1.25)
    f = f * (1 + (gain - 1) * 0.25)                                   # слабо — розовый платок и кожа остаются живыми
    img = np.clip(f, 0, 255).astype(np.uint8)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8)).apply(l)
    img = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.08, 0, 255)                 # чуть живее цвет (скриншоты блёклые)
    img = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    blur = cv2.GaussianBlur(img, (0, 0), 1.2)
    img = cv2.addWeighted(img, 1.3, blur, -0.3, 0)                   # лёгкая резкость
    return encode(img)


# ---------- качество фото (19.10): размытое / нет лица → боту вежливо попросить другое ----------
SHARP = 1.5        # «деталь» лица: чёткое ≈ 4–5, размытое ≈ 0.6–1.3
MIN_FACE = 40      # лицо уже 40 px — слишком мелкое, не разглядеть


def _detect(img):
    H, W = img.shape[:2]
    k = min(1.0, 800 / max(H, W))
    sm = cv2.resize(img, (round(W * k), round(H * k)), interpolation=cv2.INTER_AREA) if k < 1 else img
    det = cv2.FaceDetectorYN.create(MODEL, "", (sm.shape[1], sm.shape[0]), 0.6, 0.3, 50)
    _, faces = det.detect(sm)
    if faces is None or len(faces) == 0:
        return None
    return tuple(int(float(v) / k) for v in max(faces, key=lambda f: f[2] * f[3])[:4])


def detail(face_img) -> float:
    """Сколько мелкой детали в лице: разница с уменьшенной копией. Не зависит от размера фото."""
    g = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
    s = min(128, g.shape[1])                                   # не растягиваем мелкое — растяжка «рисует» деталь
    g = cv2.resize(g, (s, s), interpolation=cv2.INTER_AREA).astype(np.float32)
    lo = cv2.resize(cv2.resize(g, (max(8, s * 3 // 8),) * 2, interpolation=cv2.INTER_AREA), (s, s),
                    interpolation=cv2.INTER_CUBIC)
    return float(np.abs(g - lo).mean())


def quality(data: bytes) -> str | None:
    """None — фото годится; 'noface' — лица нет; 'small' — лицо крошечное; 'blur' — лицо размыто."""
    img = decode(data)
    r, area = region(img), img.shape[0] * img.shape[1]
    f = None
    if r and MIN_AREA * area <= r[2] * r[3] < SCREEN * area:     # скриншот — сначала смотрим только само фото
        x, y, w, h = r
        sub = img[y:y + h, x:x + w]
        f = _detect(sub)
        if f is not None:
            img = sub
    if f is None:                      # 20.10: обрезка ошиблась (старое фото, №97) — ищем лицо на всей картинке
        f = _detect(img)
    if f is None:
        return "noface"
    x, y, w, h = f
    if w < MIN_FACE:
        return "small"
    H, W = img.shape[:2]
    c = img[max(0, y):min(H, y + h), max(0, x):min(W, x + w)]
    return "blur" if c.size == 0 or detail(c) < SHARP else None


# ---------- отпечаток фото (21.10): повтор по самому фото, даже если ФИО и годы изменили ----------
# Опорные точки фото (ORB) + проверка геометрии (RANSAC): узнаёт то же фото после скриншота, обрезки, пересжатия,
# поворота, чёрно-белой копии и даже пересъёмки бумажного фото телефоном. Отпечаток ~12 КБ, сравнение ~2 мс.
# Пороги — по реальному каналу (21.10, 611 фото): настоящие повторы дают 59–300 точек; разные карточки с одинаковой
# рамкой/оформлением — до 33 точек. Поэтому ≥ 45 — «то же фото», 30–44 — «возможно то же фото» (проверить глазами).
FEATURES = 300
SAME_POINTS = 45
MAYBE_POINTS = 30
_orb = None
_bf = None


def fingerprint(data: bytes) -> bytes | None:
    """Фото → отпечаток (bytes для базы) или None, если зацепиться не за что."""
    global _orb
    img = decode(data)
    r, area = region(img), img.shape[0] * img.shape[1]
    if r and MIN_AREA * area <= r[2] * r[3] < SCREEN * area:     # скриншот — берём только само фото
        x, y, w, h = r
        img = img[y:y + h, x:x + w]
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    k = 480 / max(g.shape)
    g = cv2.resize(g, None, fx=k, fy=k, interpolation=cv2.INTER_AREA if k < 1 else cv2.INTER_CUBIC)
    _orb = _orb or cv2.ORB_create(FEATURES)
    kp, d = _orb.detectAndCompute(g, None)
    if d is None or len(kp) < 10:
        return None
    pts = np.float32([p.pt for p in kp])
    return np.uint16(len(kp)).tobytes() + pts.astype(np.float16).tobytes() + d.tobytes()


def unpack(blob: bytes) -> tuple:
    n = int(np.frombuffer(blob[:2], np.uint16)[0])
    pts = np.frombuffer(blob[2:2 + n * 4], np.float16).reshape(n, 2).astype(np.float32)
    return pts, np.frombuffer(blob[2 + n * 4:], np.uint8).reshape(n, 32)


def match(a: tuple, b: tuple) -> int:
    """Сколько точек двух фото сошлось геометрически (0 — ничего общего)."""
    global _bf
    _bf = _bf or cv2.BFMatcher(cv2.NORM_HAMMING)
    m = [x[0] for x in _bf.knnMatch(a[1], b[1], k=2) if len(x) == 2 and x[0].distance < 0.75 * x[1].distance]
    if len(m) < SAME_POINTS:
        return len(m) // 2                                         # мало даже кандидатов — точно не то же фото
    _, mask = cv2.findHomography(a[0][[x.queryIdx for x in m]], b[0][[x.trainIdx for x in m]], cv2.RANSAC, 6.0)
    return int(mask.sum()) if mask is not None else 0
