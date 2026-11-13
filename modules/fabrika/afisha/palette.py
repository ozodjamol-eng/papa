"""Анализ фона → палитра надписей (скилл koncert-afisha, шаг «цвет по фону»).
python3 -I palette.py <видео|картинка> [t1,t2 t3,t4 ...]   — отрезки клипа, которые идут в ролик
Печатает главные цвета фона и рекомендацию: цвет текста, акцент, плашка, чего избегать."""
import sys, subprocess, colorsys
import numpy as np, cv2


def frames(path, spans):
    out = []
    if path.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
        return [cv2.imread(path)[:, :, ::-1]]
    for a, b in spans:
        for t in np.linspace(a, b, 4)[:-1] + 0.05:
            raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", path, "-frames:v", "1", "-vf", "scale=96:170",
                                  "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
            if len(raw) == 96 * 170 * 3:
                out.append(np.frombuffer(raw, np.uint8).reshape(170, 96, 3))
    return out


def analyse(fs):
    px = np.concatenate([f.reshape(-1, 3) for f in fs]).astype(np.float32)
    lab = cv2.cvtColor(px.reshape(-1, 1, 3).astype(np.uint8), cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(np.float32)
    _, lbl, cen = cv2.kmeans(lab, 5, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5), 3, cv2.KMEANS_PP_CENTERS)
    share = np.bincount(lbl.ravel(), minlength=5) / len(lbl)
    rgb = cv2.cvtColor(cen.reshape(-1, 1, 3).astype(np.uint8), cv2.COLOR_LAB2RGB).reshape(-1, 3)
    order = np.argsort(-share)
    cols = [(float(share[i]), tuple(int(v) for v in rgb[i])) for i in order]
    L = float(lab[:, 0].mean() / 255 * 100)
    # главный ЦВЕТНОЙ тон: взвешиваем насыщенностью, тёмное/серое не считаем
    hsv = np.array([colorsys.rgb_to_hsv(*(np.array(c) / 255)) for _, c in cols])
    w = np.array([s for s, _ in cols]) * hsv[:, 1] * np.clip(hsv[:, 2] * 2, 0, 1)
    ang = hsv[:, 0] * 2 * np.pi
    hue = (np.arctan2((np.sin(ang) * w).sum(), (np.cos(ang) * w).sum()) / (2 * np.pi)) % 1.0
    sat = float((hsv[:, 1] * [s for s, _ in cols]).sum())
    return cols, L, hue, sat


def hx(rgb): return "#%02x%02x%02x" % tuple(int(round(v * 255)) for v in rgb)


def recommend(L, hue, sat):
    deg = hue * 360
    name = ("красный" if deg < 20 or deg >= 340 else "оранжево-золотой" if deg < 55 else "жёлто-зелёный" if deg < 90 else "зелёный" if deg < 160
            else "бирюзовый" if deg < 200 else "синий" if deg < 255 else "фиолетовый" if deg < 300 else "малиновый")
    warm = deg < 70 or deg >= 330
    text = (1, 1, 1) if L < 62 else (0.07, 0.07, 0.09)
    if sat < 0.12:                                   # фон почти бесцветный → акцент свободный
        rule = "фон нейтральный: акцент любой один (золото допустимо)"
        accent = (0.93, 0.72, 0.33)
    else:                                            # цветной фон → акцент = светлый оттенок того же тона (родственный), не спорит с кадром
        rule = "фон цветной: акцент — светлый оттенок его же тона; противоположный тёплый/холодный цвет не брать"
        accent = colorsys.hsv_to_rgb(hue, 0.42, 1.0)
    plate = colorsys.hsv_to_rgb(hue, 0.75 if sat >= 0.12 else 0.2, 0.13)
    avoid = "золото/жёлтый (спорит с холодным фоном)" if not warm and sat >= 0.12 else "холодный синий (спорит с тёплым фоном)" if sat >= 0.12 else "больше одного акцента"
    return dict(ton=name, gradus=round(deg), text=hx(text), accent=hx(accent), accent_rgb=tuple(round(v, 3) for v in accent),
                plate=hx(plate), plate_rgb=tuple(round(v, 3) for v in plate), rule=rule, avoid=avoid)


if __name__ == "__main__":
    spans = [tuple(float(x) for x in a.split(",")) for a in sys.argv[2:]] or [(0, 10)]
    cols, L, hue, sat = analyse(frames(sys.argv[1], spans))
    print("Главные цвета фона:")
    for s, c in cols: print(f"  {s * 100:4.1f}%  #{c[0]:02x}{c[1]:02x}{c[2]:02x}")
    print(f"Средняя яркость: {L:.0f}/100, насыщенность: {sat:.2f}")
    for k, v in recommend(L, hue, sat).items(): print(f"{k}: {v}")
