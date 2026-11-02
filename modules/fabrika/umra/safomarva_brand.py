# Бренд Safo Marva: эмблема-арка (перерисовка по фото вывески — заглушка до оригинала логотипа) и цвета.
import math
from PIL import Image, ImageDraw
RED, WHITE, GOLD, GOLD2 = (227, 16, 30), (255, 255, 255), (214, 170, 92), (246, 214, 150)
# ---------- эмблема (арка) ----------
def emblem(sz=520):
    S = sz * 2; im = Image.new("RGBA", (S, int(S * 1.18)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    w, h = S, int(S * 1.18); lw = int(S * 0.035)
    arch = [(lw, w // 2), (w - lw, h - lw)]
    d.rounded_rectangle([lw, w // 2, w - lw, h - lw], radius=int(S * 0.04), fill=(120, 14, 24, 255))
    d.pieslice([lw, lw, w - lw, w - lw], 180, 360, fill=(120, 14, 24, 255))
    d.rectangle([lw, w // 2, w - lw, w // 2 + lw], fill=(120, 14, 24, 255))
    # контур
    d.arc([lw, lw, w - lw, w - lw], 180, 360, fill=GOLD + (255,), width=lw)
    d.line([(lw + lw // 2, w // 2), (lw + lw // 2, h - lw)], fill=GOLD + (255,), width=lw)
    d.line([(w - lw - lw // 2, w // 2), (w - lw - lw // 2, h - lw)], fill=GOLD + (255,), width=lw)
    d.line([(lw, h - lw - lw // 2), (w - lw, h - lw - lw // 2)], fill=GOLD + (255,), width=lw)
    c = GOLD2 + (255,)
    # полумесяц
    cx, cy, r = int(w * 0.27), int(h * 0.27), int(S * 0.07)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c); d.ellipse([cx - r + r // 2, cy - r - r // 5, cx + r + r // 2, cy + r - r // 5], fill=(120, 14, 24, 255))
    # холмы
    base = int(h * 0.86)
    d.polygon([(int(w * .12), base), (int(w * .40), int(h * .58)), (int(w * .58), base)], fill=c)
    d.polygon([(int(w * .42), base), (int(w * .70), int(h * .64)), (int(w * .90), base)], fill=c)
    d.rectangle([int(w * .1), base, int(w * .9), base + lw], fill=c)
    # пальмы
    def palm(x, y, hgt, sc):
        top = (x + hgt * 0.10, y - hgt)
        # ствол — сужающийся, слегка изогнутый
        pts_l, pts_r = [], []
        for i in range(21):
            u = i / 20; px = x + (top[0] - x) * u + math.sin(u * math.pi) * hgt * 0.04; py = y + (top[1] - y) * u
            wdt = sc * (0.075 - 0.04 * u); pts_l.append((px - wdt, py)); pts_r.append((px + wdt, py))
        d.polygon(pts_l + pts_r[::-1], fill=c)
        # листья — изогнутые сужающиеся «перья»
        for a, L in ((-170, .95), (-140, 1.0), (-110, .8), (-75, .8), (-40, 1.0), (-10, .95), (150, .7), (30, .7)):
            L *= sc; ra = math.radians(a); up, dn = [], []
            for i in range(25):
                u = i / 24; dx = math.cos(ra) * L * u; dy = math.sin(ra) * L * u + (L * 0.55) * u * u   # провисание
                nx, ny = -math.sin(ra), math.cos(ra); wdt = sc * 0.11 * math.sin(math.pi * min(1, u * 1.15)) + 1
                up.append((top[0] + dx + nx * wdt, top[1] + dy + ny * wdt)); dn.append((top[0] + dx - nx * wdt, top[1] + dy - ny * wdt))
            d.polygon(up + dn[::-1], fill=c)
    palm(int(w * .55), int(h * .68), int(h * .40), S * 0.20)
    palm(int(w * .30), int(h * .74), int(h * .25), S * 0.13)
    return im.resize((sz, int(sz * 1.18)), Image.LANCZOS)
