"""Отчёт Разведки картинками (18.10, владелец: «как в Excel, по пунктам, чтобы было ясно»).

4 карточки 1080 px для телефона:
  1. ГЛАВНОЕ — «Что делать» + часы (24 клетки цветом) + дни недели
  2. ЛИДЕРЫ — таблица топ-10 конкурентов + свои каналы
  3. РЕКЛАМА — кто сколько ставит + в какие часы + форматы
  4. СИЛЬНЫЕ ПОСТЫ — топ-8
Только Pillow и шрифт DejaVu из папки fonts (кириллица + ўқғҳ). Эмодзи на картинках не рисуем.
"""
from __future__ import annotations

import io
import re
from pathlib import Path

from .analyze import WEEKDAYS
from .report import MEDIA_RU

FONTS = Path(__file__).resolve().parent / "fonts"
W = 1080
PAD = 48
NIGHT = {0, 1, 2, 3, 4}       # владелец: ночью не публикуем, день начинается в 05:00
RELIABLE = 30                 # меньше постов в часе — «мало данных»

BG, CARD, INK, MUTED, LINE = "#F3F5F9", "#FFFFFF", "#18202E", "#6B7385", "#E3E7EF"
HEAD, ACCENT = "#14213D", "#2F6FEB"
OWN = "#E8F1FF"
NIGHT_BG = "#E9EBF0"

_EMOJI = re.compile("[\U00010000-\U0010FFFF☀-➿⬀-⯿️‍⃣←-⇿⌀-⏿]")


def clean(s: str) -> str:
    return " ".join(_EMOJI.sub("", s or "").split())


def _font(size: int, bold: bool = False):
    from PIL import ImageFont
    return ImageFont.truetype(str(FONTS / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")), size)


def fit(text: str, font, width: int) -> str:
    text = clean(text)
    if font.getlength(text) <= width:
        return text
    while text and font.getlength(text + "…") > width:
        text = text[:-1]
    return text.rstrip() + "…"


def wrap(text: str, font, width: int) -> list[str]:
    out, cur = [], ""
    for w in clean(text).split():
        t = (cur + " " + w).strip()
        if font.getlength(t) <= width:
            cur = t
        else:
            if cur:
                out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    return out


def heat(s: float | None) -> str:
    """Цвет силы: зелёный — лучше обычного, красный — хуже."""
    if s is None:
        return "#EEF0F4"
    if s >= 1.15:
        return "#1F9D55"
    if s >= 1.05:
        return "#5CC27F"
    if s >= 0.98:
        return "#BFE8CC"
    if s >= 0.93:
        return "#FFD8A8"
    return "#F59E8B"


def text_on(fill: str) -> str:
    return "#FFFFFF" if fill in ("#1F9D55", "#5CC27F") else INK


def x_(s) -> str:
    return f"×{s:.2f}" if s is not None else "—"


def _n(x) -> str:
    if x is None:
        return "—"
    return f"{x:,}".replace(",", " ") if isinstance(x, int) else str(x)


# ---------- выводы ----------

def advice(a: dict) -> list[str]:
    """Короткие выводы «что делать» из цифр. Учитывает правило владельца: ночью не публикуем."""
    out: list[str] = []
    hours = [h for h in a["hours"] if h["strength"] is not None]
    day = sorted([h for h in hours if h["key"] not in NIGHT and h["posts"] >= RELIABLE],
                 key=lambda h: h["strength"], reverse=True)
    if day:
        top = day[:2]
        out.append("Главные посты ставить в " + " и ".join(f"{h['key']:02d}:00" for h in top) +
                   " (сила " + " / ".join(f"×{h['strength']}" for h in top) + ").")
    night = [h for h in hours if h["key"] in NIGHT]
    if night and day:
        n = max(night, key=lambda h: h["strength"])
        if n["strength"] > day[0]["strength"]:
            out.append(f"Ночью ({n['key']:02d}:00, ×{n['strength']}) посты сильнее, но ночью не публикуем — "
                       "самый сильный материал давать первым утром, в 05:00.")
    ad_h = a.get("ad_hours") or {}
    if ad_h and day:
        busy = sorted(ad_h, key=lambda h: ad_h[h], reverse=True)[:4]
        quiet = [h for h in day if 9 <= h["key"] <= 22 and h["strength"] >= 1.0]
        if quiet:
            q = min(quiet[:6], key=lambda h: ad_h.get(h["key"], 0))
            out.append(f"Рекламу ставить в {q['key']:02d}:00: у конкурентов там мало рекламы, а пост сильный. "
                       f"Их реклама толпится в " + ", ".join(f"{h:02d}" for h in sorted(busy)) + ":00.")
    wd = [w for w in a["weekdays"] if w["strength"] is not None]
    if len(wd) >= 3:
        s = sorted(wd, key=lambda w: w["strength"], reverse=True)
        out.append(f"Сильный контент — в {WEEKDAYS[s[0]['key']]} и {WEEKDAYS[s[1]['key']]} "
                   f"(×{s[0]['strength']} / ×{s[1]['strength']}); слабее всего {WEEKDAYS[s[-1]['key']]} "
                   f"(×{s[-1]['strength']}).")
    md = [m for m in a["media"] if m["strength"] is not None and m["posts"] >= RELIABLE]
    if len(md) >= 2:
        s = sorted(md, key=lambda m: m["strength"], reverse=True)
        if s[0]["strength"] - s[-1]["strength"] < 0.1:
            out.append("Формат почти не влияет (разница меньше 10%) — решает содержание поста.")
        else:
            out.append(f"Лучший формат — {MEDIA_RU.get(s[0]['key'], s[0]['key'])} (×{s[0]['strength']}), "
                       f"слабее — {MEDIA_RU.get(s[-1]['key'], s[-1]['key'])} (×{s[-1]['strength']}).")
    return out


# ---------- рисование ----------

class Card:
    def __init__(self, title: str, sub: str, height: int):
        from PIL import Image, ImageDraw
        self.img = Image.new("RGB", (W, height), BG)
        self.d = ImageDraw.Draw(self.img)
        self.d.rectangle([0, 0, W, 150], fill=HEAD)
        self.d.text((PAD, 34), title, font=_font(46, True), fill="#FFFFFF")
        self.d.text((PAD, 98), sub, font=_font(26), fill="#B8C4DD")
        self.y = 180

    def section(self, title: str) -> None:
        self.d.text((PAD, self.y), title, font=_font(32, True), fill=INK)
        self.y += 52

    def panel(self, h: int) -> tuple[int, int]:
        top = self.y
        self.d.rounded_rectangle([PAD - 16, top, W - PAD + 16, top + h], radius=22, fill=CARD, outline=LINE, width=2)
        return top, top + h

    def done(self) -> bytes:
        img = self.img.crop((0, 0, W, min(self.img.height, self.y + 40)))
        b = io.BytesIO()
        img.save(b, "PNG", optimize=True)
        return b.getvalue()


def card_main(a: dict) -> bytes:
    c = Card("ГЛАВНОЕ · РАЗВЕДКА", f"{a['generated']} · {a['days']} дн. · {len(a['channels'])} каналов · "
             f"{a['posts_total']} постов", 2400)
    # что делать
    c.section("ЧТО ДЕЛАТЬ")
    f = _font(29)
    lines = []
    for i, t in enumerate(advice(a) or ["Пока мало данных для выводов."], 1):
        w = wrap(t, f, W - 2 * PAD - 70)
        lines.append((i, w))
    h = sum(len(w) * 40 + 22 for _, w in lines) + 30
    top, _ = c.panel(h)
    y = top + 24
    for i, w in lines:
        c.d.ellipse([PAD + 4, y + 2, PAD + 44, y + 42], fill=ACCENT)
        c.d.text((PAD + 24, y + 22), str(i), font=_font(24, True), fill="#FFFFFF", anchor="mm")
        for ln in w:
            c.d.text((PAD + 64, y + 4), ln, font=f, fill=INK)
            y += 40
        y += 22
    c.y = top + h + 40

    # часы
    c.section("ЧАСЫ: СИЛА ПОСТА  (×1.0 = обычно)")
    hours = {h["key"]: h for h in a["hours"]}
    cw, ch, gap = (W - 2 * PAD - 5 * 12) // 6, 118, 12
    for r in range(4):
        for k in range(6):
            hr = r * 6 + k
            hh = hours.get(hr, {"strength": None, "posts": 0})
            x0, y0 = PAD + k * (cw + gap), c.y + r * (ch + gap)
            night = hr in NIGHT
            few = hh["posts"] < RELIABLE
            fill = NIGHT_BG if night else heat(hh["strength"])
            c.d.rounded_rectangle([x0, y0, x0 + cw, y0 + ch], radius=16, fill=fill,
                                  outline=("#9AA3B5" if night else None), width=2)
            col = MUTED if night else text_on(fill)
            c.d.text((x0 + cw / 2, y0 + 28), f"{hr:02d}:00", font=_font(26, True), fill=col, anchor="mm")
            s = hh["strength"]
            c.d.text((x0 + cw / 2, y0 + 64), x_(s), font=_font(30, True), fill=col,
                     anchor="mm")
            tag = "ночь" if night else ("мало данных" if few else f"{hh['posts']} постов")
            c.d.text((x0 + cw / 2, y0 + 98), tag, font=_font(18), fill=col, anchor="mm")
    c.y += 4 * (ch + gap) + 10
    lx = PAD
    for col, t in (("#1F9D55", "сильно"), ("#BFE8CC", "обычно"), ("#FFD8A8", "ниже"), ("#F59E8B", "слабо"), (NIGHT_BG, "ночь")):
        c.d.rounded_rectangle([lx, c.y, lx + 30, c.y + 30], radius=6, fill=col, outline="#9AA3B5", width=1)
        c.d.text((lx + 40, c.y + 2), t, font=_font(22), fill=MUTED)
        lx += 62 + int(_font(22).getlength(t))
    c.y += 70

    # дни
    c.section("ДНИ НЕДЕЛИ")
    wd = {w["key"]: w for w in a["weekdays"]}
    dw = (W - 2 * PAD - 6 * 10) // 7
    for k in range(7):
        s = wd.get(k, {}).get("strength")
        x0 = PAD + k * (dw + 10)
        fill = heat(s)
        c.d.rounded_rectangle([x0, c.y, x0 + dw, c.y + 110], radius=16, fill=fill)
        c.d.text((x0 + dw / 2, c.y + 34), WEEKDAYS[k], font=_font(28, True), fill=text_on(fill), anchor="mm")
        c.d.text((x0 + dw / 2, c.y + 78), x_(s), font=_font(26), fill=text_on(fill),
                 anchor="mm")
    c.y += 130
    return c.done()


def _table(c: Card, cols: list[tuple[str, int, str]], rows: list[tuple[list[str], bool]], bar: list[float] | None = None):
    """cols: (заголовок, ширина, выравнивание l/r). rows: (ячейки, своя строка)."""
    rh = 64
    top, _ = c.panel(rh * (len(rows) + 1) + 10)
    x = PAD
    hf, bf, rf = _font(22, True), _font(25), _font(25, True)
    y = top + 8
    for t, w, al in cols:
        c.d.text((x + (w - 8 if al == "r" else 4), y + 20), t, font=hf, fill=MUTED, anchor=("ra" if al == "r" else "la"))
        x += w
    y += rh
    for i, (cells, own) in enumerate(rows):
        if own:
            c.d.rectangle([PAD - 14, y - 4, W - PAD + 14, y + rh - 6], fill=OWN)
        c.d.line([PAD, y - 6, W - PAD, y - 6], fill=LINE, width=2)
        if bar is not None and bar[i]:
            x1 = PAD + cols[0][1] + cols[1][1]
            bw = int((cols[2][1] - 10) * bar[i])
            c.d.rounded_rectangle([x1 + 6, y + rh - 22, x1 + 6 + max(6, bw), y + rh - 14], radius=4,
                                  fill="#9DBBF7")
        x = PAD
        for j, ((_, w, al), v) in enumerate(zip(cols, cells)):
            f = rf if j in (0, 1) else bf
            v = fit(v, f, w - 14)
            c.d.text((x + (w - 8 if al == "r" else 4), y + 14), v, font=f, fill=INK, anchor=("ra" if al == "r" else "la"))
            x += w
        y += rh
    c.y = y + 30


def card_leaders(a: dict) -> bytes:
    rivals = [x for x in a["channels"] if not x["is_own"]][:10]
    own = [x for x in a["channels"] if x["is_own"]]
    c = Card("ЛИДЕРЫ ПО ПРОСМОТРАМ", "медиана просмотров поста · ERR = просмотры / подписчики", 2200)
    cols = [("№", 60, "l"), ("Канал", 370, "l"), ("Просм.", 180, "r"), ("ERR", 120, "r"),
            ("Пост/д", 130, "r"), ("Рекл/д", 124, "r")]
    mx = max([x["median_views"] or 0 for x in rivals + own] or [1]) or 1
    rows = [([str(i), x["title"], _n(x["median_views"]), f"{x['err']}%" if x["err"] is not None else "—",
              str(x["per_day"]), str(x["ads_per_day"])], False) for i, x in enumerate(rivals, 1)]
    c.section("КОНКУРЕНТЫ — ТОП-10")
    _table(c, cols, rows, [(x["median_views"] or 0) / mx for x in rivals])
    if own:
        c.section("НАШИ КАНАЛЫ")
        cols2 = [("", 60, "l"), ("Канал", 370, "l"), ("Просм.", 180, "r"), ("ERR", 120, "r"),
                 ("Пост/д", 130, "r"), ("Подп.", 124, "r")]
        rows2 = [(["★", x["title"], _n(x["median_views"]), f"{x['err']}%" if x["err"] is not None else "—",
                   str(x["per_day"]), _n(x["subscribers"])], True) for x in own]
        _table(c, cols2, rows2, [(x["median_views"] or 0) / mx for x in own])
    return c.done()


def card_ads(a: dict) -> bytes:
    c = Card("РЕКЛАМА У КОНКУРЕНТОВ", "вероятная реклама по признакам (номер, «реклама», цены, боты)", 2200)
    ads = sorted([x for x in a["channels"] if x["ads"]], key=lambda x: x["ads"], reverse=True)[:8]
    c.section("КТО СКОЛЬКО СТАВИТ (в день)")
    if ads:
        rh = 70
        top, _ = c.panel(rh * len(ads) + 24)
        mx = max(x["ads_per_day"] for x in ads) or 1
        y = top + 16
        nf, vf = _font(25, True), _font(25, True)
        for x in ads:
            name = fit(("★ " if x["is_own"] else "") + x["title"], nf, 360)
            c.d.text((PAD + 4, y + 16), name, font=nf, fill=ACCENT if x["is_own"] else INK)
            bx, bw = PAD + 380, W - 2 * PAD - 380 - 120
            ln = max(8, int(bw * x["ads_per_day"] / mx))
            c.d.rounded_rectangle([bx, y + 12, bx + ln, y + rh - 18], radius=10,
                                  fill=(ACCENT if x["is_own"] else "#F28C38"))
            c.d.text((W - PAD - 4, y + 16), f"{x['ads_per_day']}", font=vf, fill=INK, anchor="ra")
            y += rh
        c.y = top + rh * len(ads) + 24 + 40
    else:
        c.d.text((PAD, c.y), "Рекламы не найдено.", font=_font(26), fill=MUTED)
        c.y += 60

    ad_h = {int(k): v for k, v in (a.get("ad_hours") or {}).items()}
    if ad_h:
        c.section("В КАКИЕ ЧАСЫ СТАВЯТ РЕКЛАМУ")
        mx = max(ad_h.values()) or 1
        top, _ = c.panel(300)
        bw = (W - 2 * PAD - 23 * 6) / 24
        base = top + 230
        for hr in range(24):
            v = ad_h.get(hr, 0)
            x0 = PAD + hr * (bw + 6)
            hgt = int(170 * v / mx)
            if v:
                c.d.rounded_rectangle([x0, base - hgt, x0 + bw, base], radius=6,
                                      fill=("#F28C38" if v >= 0.6 * mx else "#F9C796"))
            if hr % 3 == 0:
                c.d.text((x0 + bw / 2, base + 30), f"{hr:02d}", font=_font(22), fill=MUTED, anchor="mm")
        top4 = sorted(ad_h, key=lambda h: ad_h[h], reverse=True)[:4]
        c.d.text((PAD + 4, top + 16), "Пик: " + ", ".join(f"{h:02d}:00" for h in sorted(top4)), font=_font(24, True),
                 fill=INK)
        c.y = top + 340

    md = sorted([m for m in a["media"] if m["strength"] is not None], key=lambda m: m["strength"], reverse=True)
    if md:
        c.section("ФОРМАТЫ ПОСТОВ (сила)")
        n = len(md)
        cw = (W - 2 * PAD - (n - 1) * 10) // n
        for i, m in enumerate(md):
            x0 = PAD + i * (cw + 10)
            fill = heat(m["strength"])
            c.d.rounded_rectangle([x0, c.y, x0 + cw, c.y + 130], radius=16, fill=fill)
            c.d.text((x0 + cw / 2, c.y + 32), MEDIA_RU.get(m["key"], m["key"]), font=_font(25, True),
                     fill=text_on(fill), anchor="mm")
            c.d.text((x0 + cw / 2, c.y + 72), x_(m['strength']), font=_font(28, True), fill=text_on(fill),
                     anchor="mm")
            c.d.text((x0 + cw / 2, c.y + 106), f"{m['posts']} постов", font=_font(19), fill=text_on(fill), anchor="mm")
        c.y += 160
    return c.done()


def card_top(a: dict) -> bytes:
    posts = a["top_posts"][:8]
    c = Card("САМЫЕ СИЛЬНЫЕ ПОСТЫ", "во сколько раз пост набрал больше обычного для своего канала", 2400)
    if not posts:
        c.d.text((PAD, c.y), "Пока нет данных.", font=_font(26), fill=MUTED)
        c.y += 60
        return c.done()
    tf, mf, bf = _font(26, True), _font(22), _font(25)
    for p in posts:
        snip = wrap(p["snippet"] or "(без текста)", bf, W - 2 * PAD - 190)[:2]
        h = 70 + 38 * len(snip) + 20
        top, _ = c.panel(h)
        fill = heat(1.2)
        c.d.rounded_rectangle([PAD, top + 18, PAD + 140, top + 90], radius=14, fill=fill)
        c.d.text((PAD + 70, top + 54), f"×{p['rel']}", font=_font(32, True), fill="#FFFFFF", anchor="mm")
        x = PAD + 170
        c.d.text((x, top + 18), fit(p["title"], tf, W - PAD - x - 10), font=tf, fill=INK)
        meta = f"{p['when']} · {MEDIA_RU.get(p['media'], p['media'])} · {_n(p['views'])} просм."
        c.d.text((x, top + 56), meta, font=mf, fill=MUTED)
        y = top + 92
        for ln in snip:
            c.d.text((x, y), ln, font=bf, fill=INK)
            y += 38
        c.y = top + h + 18
    return c.done()


def render_cards(a: dict) -> list[bytes]:
    return [card_main(a), card_leaders(a), card_ads(a), card_top(a)]


def caption(a: dict) -> str:
    L = [f"📊 PAPA · РАЗВЕДКА · {a['generated']}", "", "✅ ЧТО ДЕЛАТЬ:"]
    L += [f"{i}. {t}" for i, t in enumerate(advice(a), 1)]
    L += ["", "1 — главное · 2 — лидеры · 3 — реклама · 4 — сильные посты"]
    return "\n".join(L)[:1024]
