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
