#!/usr/bin/env python3
"""«🕌 Намоз обои» v2 (06.11.2026). Владелец: обои резались — шаблоны 1080×2400 были картинкой в середине с мутными
полосами. Теперь: 5 фонов на весь экран (ChatGPT, бесплатно, 9:19.5) → 1290×2796 (подходит iPhone и Android),
карточка рисуется кодом в стиле образца владельца (кремовая панель, золотая рамка, тёмно-синие плашки),
только жирный Montserrat. Карточка — в безопасной зоне: ниже часов экрана блокировки, выше нижней полоски.
В неделю уходят все 5 — альбомом."""
from __future__ import annotations

import datetime as dt
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
W, H = 1290, 2796
STYLES = ("01_Rassvet", "02_Tungi_masjid", "03_Oq_marmar", "04_Yashil_tabiat", "05_Ozbek_merosi")
NAMES = (("bomdod", "Бомдод"), ("peshin", "Пешин"), ("asr", "Аср"), ("shom", "Шом"), ("xufton", "Хуфтон"))
MONTHS = ("январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь")
NAVY, NAVY2 = (14, 32, 78), (28, 52, 112)
GOLD, GOLD_D, GOLD_L = (212, 168, 72), (150, 108, 36), (250, 222, 140)
CREAM, CREAM2 = (250, 243, 226), (238, 226, 198)
INK = (12, 22, 52)
FONT = HERE / "assets" / "Montserrat.ttf"


def font(size: int, weight: str = "ExtraBold") -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(FONT), size)
    f.set_variation_by_name(weight)
    return f


def week_label(day: dt.date) -> str:
    end = day + dt.timedelta(days=7)
    return f"{day.day} {MONTHS[day.month - 1]} – {end.day} {MONTHS[end.month - 1]} {end.year} йил"


def fit(d, s, size, maxw, weight="ExtraBold"):
    while size > 20 and d.textlength(s, font=font(size, weight)) > maxw:
        size -= 1
    return font(size, weight)


def background(src: Path) -> Image.Image:
    im = Image.open(src).convert("RGB")
    s = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 2
    im = im.crop((x, y, x + W, y + H))
    return im.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=3))


def shadow(base: Image.Image, box, r, blur=28, alpha=150, off=(0, 18)):
    sh = Image.new("L", base.size, 0)
    ImageDraw.Draw(sh).rounded_rectangle((box[0] + off[0], box[1] + off[1], box[2] + off[0], box[3] + off[1]), r, fill=alpha)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    base.paste(Image.new("RGB", base.size, (0, 0, 0)), (0, 0), sh)


def pill(d, box, fill, border=GOLD, bw=5):
    r = (box[3] - box[1]) // 2
    d.rounded_rectangle(box, r, fill=border)
    d.rounded_rectangle((box[0] + bw, box[1] + bw, box[2] - bw, box[3] - bw), r - bw, fill=fill)


def icon(d, cx, cy, r, kind):
    """Круглый значок: восход / солнце / закат / луна — золотом на тёмно-синем."""
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=GOLD)
    d.ellipse((cx - r + 6, cy - r + 6, cx + r - 6, cy + r - 6), fill=NAVY)
    g = GOLD_L
    if kind == "xufton":
        d.ellipse((cx - r * .5, cy - r * .5, cx + r * .5, cy + r * .5), fill=g)
        d.ellipse((cx - r * .28, cy - r * .62, cx + r * .62, cy + r * .28), fill=NAVY)
        d.ellipse((cx + r * .3, cy - r * .45, cx + r * .4, cy - r * .35), fill=g)
        return
    if kind == "peshin":
        d.ellipse((cx - r * .3, cy - r * .3, cx + r * .3, cy + r * .3), fill=g)
        for k in range(8):
            a = k * math.pi / 4
            d.line((cx + math.cos(a) * r * .42, cy + math.sin(a) * r * .42, cx + math.cos(a) * r * .62,
                    cy + math.sin(a) * r * .62), fill=g, width=6)
        return
    hy = cy + r * .18                                     # горизонт
    d.pieslice((cx - r * .34, hy - r * .34, cx + r * .34, hy + r * .34), 180, 360, fill=g)
    for k in (-60, -30, 0, 30, 60):
        a = math.radians(k - 90)
        d.line((cx + math.cos(a) * r * .45, hy + math.sin(a) * r * .45, cx + math.cos(a) * r * .62,
                hy + math.sin(a) * r * .62), fill=g, width=5)
    d.line((cx - r * .55, hy + 2, cx + r * .55, hy + 2), fill=g, width=6)
    d.line((cx - r * .38, hy + r * .2, cx + r * .38, hy + r * .2), fill=g, width=5)


def crest(d, cx, top, w, h):
    """Орнамент-корона над карточкой (как в образце владельца)."""
    pts = [(cx - w / 2, top + h), (cx - w * .28, top + h * .55), (cx - w * .12, top + h * .35), (cx, top),
           (cx + w * .12, top + h * .35), (cx + w * .28, top + h * .55), (cx + w / 2, top + h)]
    d.polygon(pts, fill=GOLD)
    inner = [(x + (cx - x) * .1, y + (top + h - y) * .12 + 6) for x, y in pts]
    d.polygon(inner, fill=NAVY)
    s = h * .26
    cy = top + h * .58
    for a in range(0, 360, 45):                            # цветок-розетка
        r = math.radians(a)
        d.ellipse((cx + math.cos(r) * s * .55 - s * .28, cy + math.sin(r) * s * .55 - s * .28,
                   cx + math.cos(r) * s * .55 + s * .28, cy + math.sin(r) * s * .55 + s * .28), fill=GOLD)
    d.ellipse((cx - s * .3, cy - s * .3, cx + s * .3, cy + s * .3), fill=GOLD_L)


def render_one(bg: Path, row: dict, out: Path) -> Path:
    im = background(bg)
    x0, x1 = round(W * .085), round(W * .915)
    y0, y1 = round(H * .335), round(H * .885)            # безопасная зона: ниже часов, выше нижней полоски
    shadow(im, (x0, y0, x1, y1), 70)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((x0, y0, x1, y1), 70, fill=GOLD)
    d.rounded_rectangle((x0 + 10, y0 + 10, x1 - 10, y1 - 10), 62, fill=GOLD_D)
    d.rounded_rectangle((x0 + 18, y0 + 18, x1 - 18, y1 - 18), 56, fill=CREAM)
    d.rounded_rectangle((x0 + 30, y0 + 30, x1 - 30, y1 - 30), 46, outline=GOLD, width=3)
    crest(d, W // 2, y0 - 120, 360, 150)
    cx, cw = W // 2, x1 - x0
    y = y0 + 95
    d.text((cx, y), "ХЎЖАОБОД ТУМАНИ", font=fit(d, "ХЎЖАОБОД ТУМАНИ", 92, cw - 140, "Black"), fill=INK, anchor="mm")
    y += 105
    wk = week_label(dt.date.fromisoformat(row["day"]))
    pill(d, (x0 + 70, y - 46, x1 - 70, y + 46), NAVY)
    d.text((cx, y), wk, font=fit(d, wk, 42, cw - 220, "Bold"), fill=(255, 246, 222), anchor="mm")
    y += 115
    d.text((cx, y), "НАМОЗ ВАҚТЛАРИ", font=fit(d, "НАМОЗ ВАҚТЛАРИ", 96, cw - 140, "Black"), fill=INK, anchor="mm")
    d.line((cx - 230, y + 64, cx + 230, y + 64), fill=GOLD, width=4)
    d.regular_polygon((cx, y + 64, 12), 4, fill=GOLD)
    y += 150
    rh, gap = 116, 22
    for key, name in NAMES:
        top, bot = y, y + rh
        split = x0 + round(cw * .64)
        pill(d, (x0 + 60, top, x1 - 60, bot), NAVY)
        d.rounded_rectangle((split, top + 5, x1 - 65, bot - 5), (rh - 10) // 2, fill=CREAM2)
        d.rectangle((split, top + 5, split + 40, bot - 5), fill=CREAM2)
        d.line((split, top + 5, split, bot - 5), fill=GOLD, width=5)
        icon(d, x0 + 60 + rh // 2, (top + bot) // 2, rh // 2 - 4, key)
        d.text((x0 + 60 + rh + 40, (top + bot) // 2), name, font=font(64, "ExtraBold"), fill=(255, 250, 238), anchor="lm")
        d.text(((split + x1 - 65) // 2, (top + bot) // 2), row[key], font=font(74, "Black"), fill=INK, anchor="mm")
        y = bot + gap
    y += 4
    bt, bb = y, y1 - 60
    assert bb - bt >= 260, "нижняя плашка не влезает — текст обрежется"
    d.rounded_rectangle((x0 + 60, bt, x1 - 60, bb), 50, fill=GOLD)
    d.rounded_rectangle((x0 + 66, bt + 6, x1 - 66, bb - 6), 44, fill=NAVY)
    my = (bt + bb) // 2
    d.text((cx, my - 72), "Аллоҳ ибодатларимизни", font=font(50, "ExtraBold"), fill=(255, 246, 222), anchor="mm")
    d.text((cx, my - 14), "қабул қилсин!", font=font(50, "ExtraBold"), fill=(255, 246, 222), anchor="mm")
    d.line((cx - 200, my + 34, cx + 200, my + 34), fill=GOLD, width=3)
    d.text((cx, my + 84), "@XOJAOBODCITY24", font=font(46, "Black"), fill=GOLD_L, anchor="mm")
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, quality=95)
    return out


def render(row: dict, out_dir: Path, bg_dir: Path | None = None) -> list[Path]:
    bg_dir = bg_dir or HERE / "assets" / "v2"
    return [render_one(bg_dir / f"{st}.png", row, out_dir / f"{i:02d}_{st}.jpg") for i, st in enumerate(STYLES, 1)]
