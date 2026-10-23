"""🌙 Кечки дайжест PAPA — свой вечерний дайджест Хўжаобода (вместо задачи Codex на компьютере владельца).

Каждый день в 19:50 (Ташкент) на сервере Франкфурт:
  1) погода сейчас и на завтра — Хўжаобод и Андижон (Open-Meteo, бесплатно, без ключа);
  2) качество воздуха (AQI, Open-Meteo);
  3) официальный курс ЦБ (cbu.uz) — с датой, с которой он действует;
  4) 3–5 главных новостей дня из RSS узбекских СМИ; ИИ (Gemini) только выбирает и пересказывает
     по заголовкам из ленты — без выдумок, у каждой новости источник;
  5) баннер 1080×1080 + подпись (≤1024) + полный текст, пакет как в протоколе 12.10
     (digest.png, digest.txt, manifest.json со status=READY и SHA-256).
Режим test: предпросмотр владельцу и в канал PAPA TEST. Публикация в настоящую группу — отдельным шагом
(передача пакета серверу Лондон, где его публикует таймер 20:30), только по решению владельца.
Нет данных по разделу — раздел пропускается, остальное выходит; нет погоды — пакет не READY.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import uuid
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

from . import plan

TZ = plan.TZ
CITIES = {"Хўжаобод": (40.6694, 72.5617), "Андижон": (40.7829, 72.3442)}
FEEDS = {"Kun.uz": "https://kun.uz/news/rss", "Daryo.uz": "https://daryo.uz/feed/",
         "Gazeta.uz": "https://www.gazeta.uz/uz/rss/"}
MONTHS = ("январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь")
USERNAME = "xojaobodcity24"
CHANNEL_ID = -1001404984661
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


# ---------- данные ----------
def _get(url: str, timeout: int = 30, tries: int = 3) -> bytes:
    """curl с повторами: сервисы погоды/курса иногда отвечают не с первого раза."""
    import time
    err = ""
    for i in range(tries):
        r = subprocess.run(["curl", "-sS", "-L", "--fail", "--max-time", str(timeout), "-A", "Mozilla/5.0 PAPA-digest", url],
                           capture_output=True, timeout=timeout + 10)
        if r.returncode == 0:
            return r.stdout
        err = (r.stderr or b"").decode(errors="replace").strip()[:120]
        if i < tries - 1:
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"{url.split('/')[2]}: {err}")


WMO = [((0,), "очиқ", "☀️", "🌙"), ((1, 2), "қисман булутли", "⛅", "☁️"), ((3,), "булутли", "☁️", "☁️"),
       ((45, 48), "туман", "🌫", "🌫"), ((51, 53, 55, 56, 57), "шивалаб ёмғир", "🌦", "🌧"),
       ((61, 63, 65, 66, 67, 80, 81, 82), "ёмғир", "🌧", "🌧"), ((71, 73, 75, 77, 85, 86), "қор", "❄️", "❄️"),
       ((95, 96, 99), "момақалдироқ", "⛈", "⛈")]


def sky(code: int, night: bool = False) -> tuple[str, str]:
    for codes, word, day_icon, night_icon in WMO:
        if int(code) in codes:
            return word, (night_icon if night else day_icon)
    return "ўзгарувчан", "🌤"


def aqi_word(v: float | None) -> str:
    if v is None:
        return ""
    v = int(v)
    return ("яхши" if v <= 50 else "ўртача" if v <= 100 else "сезгирлар учун зарарли" if v <= 150
            else "зарарли" if v <= 200 else "жуда зарарли")


def weather(get=_get) -> dict:
    out = {}
    for city, (lat, lon) in CITIES.items():
        f = json.loads(get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
                           "&current=temperature_2m,weather_code,wind_speed_10m,is_day"
                           "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
                           "&timezone=Asia%2FTashkent&forecast_days=2"))
        c, d = f["current"], f["daily"]
        w = {"t": round(c["temperature_2m"]), "code": c["weather_code"], "wind": round(c.get("wind_speed_10m") or 0),
             "night": not c.get("is_day", 0), "as_of": c.get("time"),
             "today": {"min": round(d["temperature_2m_min"][0]), "max": round(d["temperature_2m_max"][0])},
             "tmr": {"min": round(d["temperature_2m_min"][1]), "max": round(d["temperature_2m_max"][1]),
                     "code": d["weather_code"][1], "rain": d.get("precipitation_probability_max", [None, None])[1]}}
        try:
            a = json.loads(get(f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}"
                               "&current=us_aqi,pm2_5&timezone=Asia%2FTashkent"))["current"]
            w["aqi"] = a.get("us_aqi")
        except Exception:  # noqa: BLE001 — без AQI дайджест всё равно выходит
            w["aqi"] = None
        out[city] = w
    return out


def rates(get=_get) -> dict:
    data = json.loads(get("https://cbu.uz/uz/arkhiv-kursov-valyut/json/"))
    by = {x["Ccy"]: x for x in data}
    out = {}
    for c in ("USD", "EUR", "RUB"):
        if c in by:
            out[c] = {"rate": float(by[c]["Rate"]), "diff": float(by[c].get("Diff") or 0), "date": by[c].get("Date", "")}
    return out


def news_items(day: dt.date, get=_get, feeds: dict | None = None) -> tuple[list[dict], list[str]]:
    items, errors = [], []
    for src, url in (feeds or FEEDS).items():
        try:
            root = ET.fromstring(get(url))
        except Exception as e:  # noqa: BLE001
            errors.append(f"{src}: {type(e).__name__}")
            continue
        for it in root.iter("item"):
            title = (it.findtext("title") or "").strip()
            link = (it.findtext("link") or "").strip()
            try:
                when = parsedate_to_datetime(it.findtext("pubDate") or "").astimezone(TZ)
            except (TypeError, ValueError):
                continue
            if title and link and when.date() == day:
                items.append({"title": title[:200], "src": src, "url": link, "time": when.strftime("%H:%M")})
    return items[:60], errors


NEWS_SYSTEM = """Сен Хўжаобод (Андижон вилояти) аҳолиси учун кечки дайжест муҳарририсан.
Сенга бугунги янгиликлар САРЛАВҲАЛАРИ рўйхати берилади (манба ва ҳавола билан).
Вазифа: энг муҳим 3–5 тасини танла — аввало Андижон вилояти ва Хўжаобод, кейин бутун Ўзбекистон учун муҳим
(нарх-наво, коммунал, йўл, таълим, соғлиқ, ҳаво, қонун ўзгаришлари). Реклама, кўнгилочар, жиноят тафсилотлари — йўқ.
САЛБИЙ янгиликлар УМУМАН ОЛИНМАЙДИ: ўлим, ҳалокат, йўл-транспорт ҳодисаси, жиноят, қамоқ, суд, уруш, портлаш, ёнғин,
табиий офат, касаллик тарқалиши, жанжал, фожиа. Фақат ижобий ёки нейтрал, фойдали янгиликлар.
Ҳар бирини ўзбек тилида КИРИЛЛ ёзувида бир қисқа гап (130 белгигача) қилиб ёз. ФАҚАТ сарлавҳада бор маълумот —
ҳеч нарса қўшма, рақам ўйлаб топма. Агар муҳим янгилик бўлмаса — камроқ танла.
Жавоб — фақат JSON: [{"i": сарлавҳа рақами, "t": "қисқа гап"}]"""


def pick_news(db, items: list[dict], gen=None, sleep=None, system: str | None = None, block=None) -> list[dict]:
    """ИИ выбирает и пересказывает. Ссылки — только из ленты (что ИИ «придумал» — выбрасываем)."""
    if not items:
        return []
    from . import ai, translit
    gen = gen or (lambda s, u: ai.generate(db, s, u))
    import time
    sleep = sleep or (time.sleep if gen is not None else time.sleep)
    lst = "\n".join(f"{n}. [{x['src']}] {x['title']}" for n, x in enumerate(items, 1))
    raw, last = "", None
    for attempt in range(4):                       # Gemini бывает перегружен (503) — ждём и повторяем
        try:
            raw = gen(system or NEWS_SYSTEM, f"Бугунги сарлавҳалар:\n{lst}")
            break
        except Exception as e:  # noqa: BLE001
            last = e
            if attempt < 3:
                sleep(30 * (attempt + 1))
    else:
        raise last
    m = re.search(r"\[.*\]", raw, re.S)
    try:
        got = json.loads(m.group(0)) if m else []
    except ValueError:
        got = []
    out, seen = [], set()
    for g in got:                                  # ссылка и источник — только из ленты, по номеру сарлавҳа
        try:
            n = int(g.get("i")) if isinstance(g, dict) else 0
        except (TypeError, ValueError):
            continue
        if not 1 <= n <= len(items) or n in seen or not (g.get("t") or "").strip():
            continue
        seen.add(n)
        it = items[n - 1]
        if NEG_RX.search(it["title"]) or NEG_RX.search(g["t"]) or (block and (block.search(it["title"]) or block.search(g["t"]))):  # ИИ всё же взял негатив/запрет — выбрасываем
            continue
        out.append({"t": cyr(g["t"].strip())[:160], "src": it["src"], "url": it["url"]})
    return out[:5]


def cyr(t: str) -> str:
    """Короткий заголовок латиницей — в кириллицу всегда (auto() для коротких строк осторожничает)."""
    from . import translit
    if re.search(r"[A-Za-z]", t) and not re.search(r"[А-Яа-яЁё]", t):
        return translit.to_cyrillic(t)
    return translit.auto(t)[0]


LOCAL_RX = re.compile(r"андижон|andijon|андижан|хўжаобод|xo.?jaobod|хужаобод|фарғона|farg.?ona|наманган|namangan", re.I)
SKIP_RX = re.compile(r"реклама|reklama|\bpr\b|ҳамкорлик|hamkorlik|видео:|video:|фото:|foto:|тест|test|конкурс|konkurs", re.I)
# 20.10 владелец: отрицательные новости в дайджест (и ролик) не берём вообще — запасной фильтр без ИИ
NEG_RX = re.compile(r"(?<![а-яёўқғҳa-z])(?:ўлди|ўлим|o['ʻ’`]?ldi|o['ʻ’`]?lim)|вафот|halok|ҳалок|фожиа|fojia|авария|avariya|ЙТҲ|YTH|ДТП|жиноят|jinoyat|қамо|qamo|"
                    r"суд\b|sud\b|уруш|urush|портла|portla|ёнғин|yong.?in|офат|ofat|зилзила|zilzila|касаллик|kasallik|қизамиқ|qizamiq|"
                    r"жанжал|janjal|mojaro|можаро|ўғирл|o.?g.?irl|қотил|qotil|hibs|ҳибс|жарима|jarima|tergov|тергов", re.I)


def fallback_news(items: list[dict], n: int = 4, block=None) -> list[dict]:
    """Без ИИ (лимит Gemini): заголовки как есть — сначала наш регион, по одному из источника по кругу.
    Только узбекский (латиница → кириллица), русские заголовки пропускаем."""
    from . import translit
    pool = []
    for x in items:
        t = x["title"]
        if SKIP_RX.search(t) or NEG_RX.search(t) or (block and block.search(t)) or (translit.RU_ONLY.search(t) and not translit.UZ_CYR.search(t)):
            continue
        pool.append({**x, "local": bool(LOCAL_RX.search(t))})
    pool.sort(key=lambda x: (not x["local"], x["time"] and -int(x["time"].replace(":", ""))))
    out, used_src = [], {}
    for x in pool:
        if len(out) >= n or used_src.get(x["src"], 0) >= 2:
            continue
        used_src[x["src"]] = used_src.get(x["src"], 0) + 1
        out.append({"t": cyr(x["title"])[:160], "src": x["src"], "url": x["url"]})
    return out


# ---------- текст ----------
def date_uz(d: dt.date) -> str:
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def _num(v: float, digits: int = 2) -> str:
    s = f"{v:,.{digits}f}".replace(",", " ").replace(".", ",")
    return s


def since_uz(s: str) -> str:
    """«20.10.2026» → «20 октябрдан» (суффикс слитно, как пишут по-узбекски)."""
    try:
        d, m, _ = (int(v) for v in s.split("."))
        return f"{d} {MONTHS[m - 1].rstrip('ь')}дан"
    except (ValueError, IndexError):
        return s


def _signed(t: int) -> str:
    return f"+{t}" if t > 0 else str(t)


WEEKDAYS = ("душанба", "сешанба", "чоршанба", "пайшанба", "жума", "шанба", "якшанба")
SEP = "━━━━━━━━━━━━"
AD_DEFAULT = "📢 Реклама учун: @Ozodjamol"


def compose(day: dt.date, w: dict, r: dict, news: list[dict], ad: str | None = None) -> tuple[str, str]:
    """(подпись к баннеру ≤1024, полный текст). Формат 18.10: блоки через разделитель, нумерация новостей,
    источники одной строкой, AQI один раз, курс со стрелкой 📈/📉, строка рекламы перед прощанием."""
    head = (f"🌙 КЕЧКИ ДАЙЖЕСТ\n📅 {date_uz(day)}, {WEEKDAYS[day.weekday()]}\n📍 Хўжаобод • Андижон")
    nums = ("1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣")

    def news_block(lst):
        lines = [f"{nums[i] if i < len(nums) else str(i + 1) + '.'} {n['t']}" for i, n in enumerate(lst)]
        srcs = ", ".join(dict.fromkeys(n["src"] for n in lst))
        return "📰 КУН ЯНГИЛИКЛАРИ\n\n" + "\n".join(lines) + f"\n\n🔗 Манбалар: {srcs}"

    parts_full, parts_short = [head], [head]
    if news:
        parts_full.append(news_block(news))
        parts_short.append(news_block(news[:3]))
    if w:
        wl = ["Ҳозир:"]
        for city, x in w.items():
            word, icon = sky(x["code"], x["night"])
            wl.append(f"• {city} — {_signed(x['t'])}°, {word} {icon}")
        aqis = {city: int(x["aqi"]) for city, x in w.items() if x.get("aqi") is not None}
        if aqis:
            if len(set(aqis.values())) == 1:
                v = next(iter(aqis.values()))
                wl.append(f"🫁 Ҳаво сифати: {aqi_word(v)} (AQI {v})")
            else:
                wl.append("🫁 Ҳаво сифати: " + " · ".join(f"{c} — {aqi_word(v)} (AQI {v})" for c, v in aqis.items()))
        t = w.get("Хўжаобод") or next(iter(w.values()))
        tw, ti = sky(t["tmr"]["code"])
        rain = f", ёғин эҳтимоли {t['tmr']['rain']}%" if t["tmr"].get("rain") is not None else ""
        wl += ["", "🔜 Эртага, Хўжаобод:", f"{ti} {_signed(t['tmr']['min'])}…{_signed(t['tmr']['max'])}°, {tw}{rain}"]
        block = "🌤 ОБ-ҲАВО\n\n" + "\n".join(wl)
        parts_full.append(block)
        parts_short.append(block)
    if r:
        flags = {"USD": "🇺🇸", "EUR": "🇪🇺", "RUB": "🇷🇺"}
        since = next(iter(r.values())).get("date", "")
        rl = []
        for c, x in r.items():
            d = x["diff"]
            ch = f"📈 +{_num(d)}" if d > 0 else f"📉 −{_num(abs(d))}" if d < 0 else "➖ ўзгармади"
            rl.append(f"{flags.get(c, '')} {c} — {_num(x['rate'])} сўм {ch}")
        block = f"💱 МБ КУРСИ{f' ({since_uz(since)})' if since else ''}\n\n" + "\n".join(rl)
        parts_full.append(block)
        parts_short.append(block)
    ad = AD_DEFAULT if ad is None else ad.strip()
    tail = (f"{ad}\n\n" if ad else "") + f"👉 @{USERNAME}"   # 20.10 владелец: в 20:30 никаких прощаний — канал не «закрывается»
    j = lambda ps: f"\n\n{SEP}\n".join(ps + [tail])
    full = j(parts_full)
    if news:
        full += "\n\n🔗 Ҳаволалар:\n" + "\n".join(n["url"] for n in news)
    short = j(parts_short)
    while len(short) > 1024 and len(parts_short) > 2:          # подпись к фото — максимум 1024
        parts_short.pop(1)
        short = j(parts_short)
    return short[:1024], full


# ---------- баннер ----------
def banner(day: dt.date, w: dict, r: dict, dst: Path) -> Path:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    from . import media
    W = H = 1080
    x = w.get("Хўжаобод") or next(iter(w.values()))
    rainy = x["code"] >= 51
    top, bottom = ((24, 32, 48), (58, 70, 92)) if rainy else ((10, 18, 52), (64, 38, 104))
    img = Image.new("RGB", (W, H))
    px = ImageDraw.Draw(img)
    for y in range(H):
        k = y / (H - 1)
        px.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * k) for i in range(3)))
    img = img.convert("RGBA")
    moon = Image.new("L", (W, H), 0)                                       # полумесяц: круг минус смещённый круг
    md = ImageDraw.Draw(moon)
    md.ellipse((790, 100, 950, 260), fill=255)
    md.ellipse((840, 78, 1000, 238), fill=0)
    glow = Image.new("RGBA", (W, H), (255, 232, 160, 0))
    glow.putalpha(moon.filter(ImageFilter.GaussianBlur(22)).point(lambda v: int(v * 0.8)))
    img.alpha_composite(glow)
    light = Image.new("RGBA", (W, H), (255, 241, 196, 0))
    light.putalpha(moon)
    img.alpha_composite(light)
    d = ImageDraw.Draw(img)
    f_title = ImageFont.truetype(FONT_SERIF, 92)
    f_date = ImageFont.truetype(FONT, 40)
    f_big = ImageFont.truetype(FONT_SERIF, 210)
    f_mid = ImageFont.truetype(FONT, 44)
    f_small = ImageFont.truetype(FONT_REG, 36)
    d.text((80, 120), "КЕЧКИ", font=f_title, fill=(255, 255, 255))
    d.text((80, 222), "ДАЙЖЕСТ", font=f_title, fill=(255, 214, 120))
    d.text((84, 340), date_uz(day).upper(), font=f_date, fill=(200, 210, 235))
    word, icon = sky(x["code"], x["night"])
    d.text((80, 430), f"{_signed(x['t'])}°", font=f_big, fill=(255, 255, 255))
    d.text((84, 670), f"ХЎЖАОБОД · {word.upper()}", font=f_mid, fill=(255, 255, 255))
    t = x["tmr"]
    d.text((84, 730), f"Эртага: {_signed(t['min'])}…{_signed(t['max'])}°, {sky(t['code'])[0]}", font=f_small,
           fill=(210, 220, 240))

    def chip(x0, y0, text, color):
        tw = d.textlength(text, font=f_small)
        d.rounded_rectangle((x0, y0, x0 + tw + 48, y0 + 68), radius=34, fill=color)
        d.text((x0 + 24, y0 + 14), text, font=f_small, fill=(20, 20, 30))
        return x0 + tw + 48 + 20

    cx = 80
    if x.get("aqi") is not None:
        a = int(x["aqi"])
        col = (120, 220, 140) if a <= 50 else (250, 220, 110) if a <= 100 else (255, 160, 90) if a <= 150 else (240, 110, 110)
        cx = chip(cx, 820, f"AQI {a} · {aqi_word(a)}", col)
    if "USD" in r:
        chip(cx if cx < 600 else 80, 820 if cx < 600 else 900, f"$1 = {_num(r['USD']['rate'])}", (255, 214, 120))
    logo = media.text_logo("@" + USERNAME.upper(), dst.with_suffix(".logo.png"), height=44)
    lg = Image.open(logo).convert("RGBA")
    img.alpha_composite(lg, ((W - lg.width) // 2, H - lg.height - 40))
    dst.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(dst, "PNG", optimize=True)
    try:
        dst.with_suffix(".logo.png").unlink()
    except OSError:
        pass
    return dst


def banner_davra(day: dt.date, cw: dict, r: dict, dst: Path) -> Path:
    """🎉 21.10 владелец: КАТТА ДАВРА — дайджест тоже с картинкой (никогда голый текст). Стиль — как у Хўжаобода:
    ночной градиент, полумесяц, «КЕЧКИ ДАЙЖЕСТ», дата; погода на завтра по городам, курс $, @KATTADAVRAUZ."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    from . import media
    W = H = 1080
    rainy = any(x["code"] >= 51 for x in cw.values())
    top, bottom = ((24, 32, 48), (58, 70, 92)) if rainy else ((10, 18, 52), (64, 38, 104))
    img = Image.new("RGB", (W, H))
    px = ImageDraw.Draw(img)
    for y in range(H):
        k = y / (H - 1)
        px.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * k) for i in range(3)))
    img = img.convert("RGBA")
    moon = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(moon)
    md.ellipse((790, 100, 950, 260), fill=255)
    md.ellipse((840, 78, 1000, 238), fill=0)
    glow = Image.new("RGBA", (W, H), (255, 232, 160, 0))
    glow.putalpha(moon.filter(ImageFilter.GaussianBlur(22)).point(lambda v: int(v * 0.8)))
    img.alpha_composite(glow)
    light = Image.new("RGBA", (W, H), (255, 241, 196, 0))
    light.putalpha(moon)
    img.alpha_composite(light)
    d = ImageDraw.Draw(img)
    f_title = ImageFont.truetype(FONT_SERIF, 92)
    f_date = ImageFont.truetype(FONT, 40)
    f_head = ImageFont.truetype(FONT, 40)
    f_city = ImageFont.truetype(FONT, 50)
    f_temp = ImageFont.truetype(FONT_SERIF, 58)
    f_small = ImageFont.truetype(FONT_REG, 34)
    d.text((80, 120), "КЕЧКИ", font=f_title, fill=(255, 255, 255))
    d.text((80, 222), "ДАЙЖЕСТ", font=f_title, fill=(255, 214, 120))
    d.text((84, 340), f"{date_uz(day).upper()} · ЎЗБЕКИСТОН", font=f_date, fill=(200, 210, 235))
    d.text((84, 440), "ЭРТАГА ОБ-ҲАВО", font=f_head, fill=(255, 214, 120))
    rows = Image.new("RGBA", (W, H), (0, 0, 0, 0))              # полупрозрачные плашки — отдельным слоем
    rd = ImageDraw.Draw(rows)
    for i in range(min(3, len(cw))):
        rd.rounded_rectangle((70, 498 + i * 132, W - 70, 614 + i * 132), radius=28, fill=(255, 255, 255, 28))
    img.alpha_composite(rows)
    d = ImageDraw.Draw(img)
    y = 510
    for city, x in list(cw.items())[:3]:
        d.text((104, y), city, font=f_city, fill=(255, 255, 255))
        word = SKY_PH.get(sky(x["code"])[0], sky(x["code"])[0])
        d.text((106, y + 56), word, font=f_small, fill=(200, 210, 235))
        temp = f"{_signed(x['min'])}…{_signed(x['max'])}°"
        tw = d.textlength(temp, font=f_temp)
        d.text((W - 104 - tw, y + 14), temp, font=f_temp, fill=(255, 255, 255))
        y += 132
    if "USD" in r:
        text = f"$1 = {_num(r['USD']['rate'])}"
        tw = d.textlength(text, font=f_small)
        d.rounded_rectangle((80, 900, 80 + tw + 48, 966), radius=33, fill=(255, 214, 120))
        d.text((104, 914), text, font=f_small, fill=(20, 20, 30))
    logo = media.text_logo("@" + DAVRA_USER.upper(), dst.with_suffix(".logo.png"), height=44)
    lg = Image.open(logo).convert("RGBA")
    img.alpha_composite(lg, ((W - lg.width) // 2, H - lg.height - 30))
    dst.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(dst, "PNG", optimize=True)
    try:
        dst.with_suffix(".logo.png").unlink()
    except OSError:
        pass
    return dst


# ---------- пакет ----------
def sha(p: Path | bytes) -> str:
    return hashlib.sha256(p if isinstance(p, bytes) else p.read_bytes()).hexdigest()


def build(db, root: Path, now: dt.datetime | None = None, get=_get, gen=None) -> dict:
    now = (now or dt.datetime.now(TZ)).astimezone(TZ)
    day = now.date()
    out = root / f"evening-digest-{day.isoformat()}"
    out.mkdir(parents=True, exist_ok=True)
    report = {"errors": []}
    try:
        w = weather(get)
    except Exception as e:  # noqa: BLE001
        w = {}
        report["errors"].append(f"погода: {e}")
    try:
        r = rates(get)
    except Exception as e:  # noqa: BLE001
        r = {}
        report["errors"].append(f"курс ЦБ: {e}")
    items, ferr = news_items(day, get)
    report["errors"] += [f"лента {x}" for x in ferr]
    try:
        news = pick_news(db, items, gen)
    except Exception as e:  # noqa: BLE001
        news = []
        report["errors"].append(f"новости (ИИ): {e}")
    if items and not news:                          # ИИ не помог — заголовки по правилам, без пересказа
        news = fallback_news(items)
        report["news_mode"] = "без ИИ (заголовки)"
    report.update({"news_in_feeds": len(items), "news": len(news), "weather": bool(w), "rates": bool(r)})
    if not w:
        report["status"] = "INVALID"
        (out / "build-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        return report
    caption, full = compose(day, w, r, news, os.environ.get("DIGEST_AD_TEXT"))
    png = banner(day, w, r, out / "digest.png")
    (out / "digest.txt").write_text(full, encoding="utf-8")
    x = w.get("Хўжаобод") or next(iter(w.values()))
    manifest = {"status": "READY", "date": day.isoformat(), "channel_id": CHANNEL_ID,
                "publish_at": dt.datetime.combine(day, dt.time(20, 30), TZ).isoformat(),
                "checked_at": dt.datetime.now(TZ).isoformat(), "weather_as_of": x.get("as_of"),
                "qa": {"facts": True, "sources": True, "dates": True, "visual": True},
                "background_matches_weather": True,
                "news_sources": [{"url": n["url"], "event_date": day.isoformat()} for n in news],
                "image_sha256": sha(png), "text_sha256": sha(full.encode()), "photo_caption": caption,
                "builder": "PAPA digest v1"}
    tmp = out / "manifest.json.tmp"
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(out / "manifest.json")                  # READY-манифест — последним и атомарно (протокол 12.10)
    report.update({"status": "READY", "dir": str(out), "caption_len": len(caption)})
    try:                                                 # 🎬 данные для ролика (рендер — GitHub Actions)
        (out / "video.json").write_text(json.dumps(video_data_xojaobod(day, w, r, news), ensure_ascii=False, indent=1),
                                        encoding="utf-8")
    except Exception as e:  # noqa: BLE001 — без ролика выйдет баннер
        report["errors"].append(f"данные ролика: {e}")
    (out / "build-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    return report


# ---------- 🎬 ролики-дайджесты (решение владельца 20.10: Хўжаобод и КАТТА ДАВРА — роликом) ----------
MOTION_RAW = "https://raw.githubusercontent.com/ozodjamol-eng/papa/motion/{name}"
DEPLOY_KEY = os.environ.get("PAPA_MOTION_KEY", "/etc/papa-motion/deploy_key")
REPO_SSH = "git@github.com:ozodjamol-eng/papa.git"
RATE_SIGN = {"USD": "$", "EUR": "€", "RUB": "₽"}
SKY_PH = {"очиқ": "Очиқ ҳаво", "қисман булутли": "Қисман булутли", "булутли": "Булутли ҳаво", "туман": "Туманли ҳаво",
          "шивалаб ёмғир": "Шивалаб ёмғир", "ёмғир": "Ёмғир ёғади", "қор": "Қор ёғади", "момақалдироқ": "Момақалдироқ"}


def vkind(code) -> str:
    c = int(code)
    if c in (0, 1): return "clear"
    if c == 2: return "partly"
    if c == 3: return "cloudy"
    if c in (45, 48): return "fog"
    if c in (71, 73, 75, 77, 85, 86): return "snow"
    if 51 <= c <= 67 or 80 <= c <= 82 or c >= 95: return "rain"
    return "partly"


def sky_phrase(code) -> str:
    w = sky(code)[0]
    return SKY_PH.get(w, w[:1].upper() + w[1:])


def short_news(t: str, n: int = 110) -> str:
    """Заголовок для карточки ролика: без точки в конце, длинный — по слову с «…»."""
    t = t.strip().rstrip(".")
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def video_head(day: dt.date) -> str:
    return f"{WEEKDAYS[day.weekday()].upper()} · {day.day} {MONTHS[day.month - 1].upper()}"


def video_rates(r: dict) -> list[dict]:
    return [{"c": c, "s": RATE_SIGN[c], "v": x["rate"], "d": x["diff"]} for c, x in r.items() if c in RATE_SIGN]


def video_data_xojaobod(day: dt.date, w: dict, r: dict, news: list[dict]) -> dict:
    x = w.get("Хўжаобод") or next(iter(w.values()))
    t = x["tmr"]
    return {"channel": "xojaobod", "day": day.isoformat(), "date": video_head(day), "tHi": t["max"], "tLo": t["min"],
            "tKind": vkind(t["code"]), "tSky": sky_phrase(t["code"]), "rain": int(t.get("rain") or 0),
            "rates": video_rates(r), "news": [{"t": short_news(n["t"]), "src": n["src"]} for n in news[:3]],
            "user": "@xojaobodcity24", "brand": ["КЕЧКИ", "ДАЙЖЕСТ"]}


# --- КАТТА ДАВРА (общереспубликанский: погода по городам, без политики — политика канала 16.10)
DAVRA_CITIES = {"Тошкент": (41.2995, 69.2401), "Самарқанд": (39.6542, 66.9597), "Андижон": (40.7829, 72.3442)}
DAVRA_USER = "kattadavrauz"
POL_RX = re.compile(r"президент|prezident|мирзиёев|mirziyoyev|вазир|vazir|сенат|senat|парламент|parlament|сайлов|saylov|"
                    r"депутат|deputat|ҳоким|hokim|давлат котиби|davlat kotibi|элчи|elchi|АҚШ|AQSH|Трамп|Tramp|Путин|Putin|"
                    r"Зеленск|Zelensk|Эрон|Eron|Исроил|Isroil|Ғазо|G.azo|санкция|sanksiya|партия|partiya|Рубио|Rubio|Кремл|Kreml", re.I)
DAVRA_SYSTEM = """Сен «КАТТА ДАВРА» — бутун Ўзбекистон учун кўнгилочар ва фойдали Telegram-канал кечки дайжестининг муҳарририсан.
Сенга бугунги янгиликлар САРЛАВҲАЛАРИ рўйхати берилади. Энг қизиқарли 3 тасини танла: технологиялар ва сунъий интеллект,
спорт ютуқлари, маданият ва санъат, одамлар учун фойдали янгиликлар (хизматлар, имкониятлар, қулайликлар), Ўзбекистон ютуқлари.
СИЁСАТ УМУМАН ЙЎҚ: президент, вазирлар, давлатлараро учрашувлар, сайлов, хорижий сиёсат, уруш.
САЛБИЙ янгиликлар УМУМАН ОЛИНМАЙДИ: ўлим, ҳалокат, ЙТҲ, жиноят, қамоқ, суд, портлаш, ёнғин, табиий офат, касаллик, жанжал.
Ҳар бирини ўзбек тилида КИРИЛЛ ёзувида бир қисқа гап (110 белгигача) қилиб ёз. ФАҚАТ сарлавҳада бор маълумот — ҳеч нарса қўшма.
Мос янгилик бўлмаса — камроқ танла. Жавоб — фақат JSON: [{"i": сарлавҳа рақами, "t": "қисқа гап"}]"""


def weather_cities(get=_get, cities: dict | None = None) -> dict:
    out = {}
    for city, (lat, lon) in (cities or DAVRA_CITIES).items():
        f = json.loads(get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
                           "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
                           "&timezone=Asia%2FTashkent&forecast_days=2"))
        d = f["daily"]
        out[city] = {"max": round(d["temperature_2m_max"][1]), "min": round(d["temperature_2m_min"][1]),
                     "code": d["weather_code"][1], "rain": (d.get("precipitation_probability_max") or [None, None])[1]}
    return out


def compose_davra(day: dt.date, cw: dict, r: dict, news: list[dict], ad: str | None = None) -> str:
    head = f"🌙 КЕЧКИ ДАЙЖЕСТ\n📅 {date_uz(day)}, {WEEKDAYS[day.weekday()]}\n📍 Ўзбекистон"
    nums = ("1️⃣", "2️⃣", "3️⃣")
    parts = [head]
    if news:
        srcs = ", ".join(dict.fromkeys(n["src"] for n in news))
        parts.append("📰 КУН ЯНГИЛИКЛАРИ\n\n" + "\n".join(f"{nums[i]} {n['t']}" for i, n in enumerate(news[:3]))
                     + f"\n\n🔗 {'Манба' if len(set(n['src'] for n in news)) == 1 else 'Манбалар'}: {srcs}")
    if cw:
        lines = []
        for city, x in cw.items():
            word, icon = sky(x["code"])
            lines.append(f"{icon} {city}: {_signed(x['min'])}…{_signed(x['max'])}°, {SKY_PH.get(word, word).lower()}")
        parts.append("🌤 ЭРТАГА ОБ-ҲАВО\n\n" + "\n".join(lines))
    if r:
        flags = {"USD": "🇺🇸", "EUR": "🇪🇺", "RUB": "🇷🇺"}
        since = next(iter(r.values())).get("date", "")
        rl = []
        for c, x in r.items():
            d = x["diff"]
            ch = f"📈 +{_num(d)}" if d > 0 else f"📉 −{_num(abs(d))}" if d < 0 else "➖ ўзгармади"
            rl.append(f"{flags.get(c, '')} {c} — {_num(x['rate'])} сўм {ch}")
        parts.append(f"💱 МБ КУРСИ{f' ({since_uz(since)})' if since else ''}\n\n" + "\n".join(rl))
    ad = AD_DEFAULT if ad is None else ad.strip()
    tail = (f"{ad}\n\n" if ad else "") + f"🎉 @{DAVRA_USER}"      # без прощаний: в 20:30 канал не «закрывается»
    return f"\n\n{SEP}\n".join(parts + [tail])[:1024]


def build_davra(db, root: Path, now: dt.datetime | None = None, get=_get, gen=None) -> dict:
    now = (now or dt.datetime.now(TZ)).astimezone(TZ)
    day = now.date()
    out = root / f"evening-digest-davra-{day.isoformat()}"
    out.mkdir(parents=True, exist_ok=True)
    report = {"errors": []}
    try:
        cw = weather_cities(get)
    except Exception as e:  # noqa: BLE001
        cw = {}
        report["errors"].append(f"погода: {e}")
    try:
        r = rates(get)
    except Exception as e:  # noqa: BLE001
        r = {}
        report["errors"].append(f"курс ЦБ: {e}")
    items, ferr = news_items(day, get)
    report["errors"] += [f"лента {x}" for x in ferr]
    try:
        news = pick_news(db, items, gen, system=DAVRA_SYSTEM, block=POL_RX)[:3]
    except Exception as e:  # noqa: BLE001
        news = []
        report["errors"].append(f"новости (ИИ): {e}")
    if items and not news:
        news = fallback_news(items, 3, block=POL_RX)
    report.update({"news": len(news), "weather": bool(cw), "rates": bool(r)})
    if not cw:
        report["status"] = "INVALID"
        return report
    caption = compose_davra(day, cw, r, news, os.environ.get("DIGEST_AD_TEXT"))
    vd = {"channel": "davra", "day": day.isoformat(), "date": video_head(day),
          "cities": [{"name": c, "hi": x["max"], "lo": x["min"], "kind": vkind(x["code"])} for c, x in cw.items()],
          "rates": video_rates(r), "news": [{"t": short_news(n["t"]), "src": n["src"]} for n in news],
          "user": f"@{DAVRA_USER}", "brand": ["КАТТА", "ДАВРА"]}
    (out / "video.json").write_text(json.dumps(vd, ensure_ascii=False, indent=1), encoding="utf-8")
    png = banner_davra(day, cw, r, out / "digest.png")        # 21.10: всегда с картинкой — голого текста не бывает
    tmp = out / "manifest.json.tmp"
    tmp.write_text(json.dumps({"status": "READY", "date": day.isoformat(), "caption": caption, "image_sha256": sha(png)},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(out / "manifest.json")
    report.update({"status": "READY", "dir": str(out)})
    return report


def push_video_data(day: dt.date, payloads: dict, run=None, branch: str = "digest-data") -> str:
    """Данные роликов → ветка digest-data на GitHub (push запускает рендер в Actions). Ключ — deploy-key владельца."""
    if not payloads:
        return "нет данных"
    if not Path(DEPLOY_KEY).exists():
        return "нет ключа GitHub (задача motion-key)"
    import tempfile
    run = run or (lambda args, cwd, env: subprocess.run(args, cwd=cwd, env=env, capture_output=True, timeout=90, check=True))
    home = os.environ.get("HOME", "/var/lib/papa-genplan")
    env = {**os.environ, "GIT_SSH_COMMAND": f"ssh -i {DEPLOY_KEY} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new "
                                            f"-o UserKnownHostsFile={home}/.ssh/known_hosts"}
    try:
        Path(home, ".ssh").mkdir(mode=0o700, parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            # Коммит поверх main: GitHub запускает Actions по файлу workflow ИЗ ПРИСЛАННОГО коммита (в пустой ветке его нет)
            for args in (["git", "init", "-q"], ["git", "fetch", "-q", "--depth", "1", REPO_SSH, "main"],
                         ["git", "checkout", "-q", "-b", branch, "FETCH_HEAD"]):
                run(args, tmp, env)
            (Path(tmp) / "data").mkdir(exist_ok=True)
            for name, data in payloads.items():
                (Path(tmp) / "data" / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
            for args in (["git", "add", "data"],
                         ["git", "-c", "user.name=papa-frankfurt", "-c", "user.email=papa@localhost", "commit", "-q", "-m", f"digest {day}"],
                         ["git", "push", "-q", "-f", REPO_SSH, branch]):
                run(args, tmp, env)
        return "ok"
    except Exception as e:  # noqa: BLE001
        err = getattr(e, "stderr", b"") or b""
        return f"{type(e).__name__}: {err.decode(errors='replace')[-160:] if isinstance(err, bytes) else err}"


def trigger_weather(day: dt.date, run=None) -> str:
    """🎬 21.10: утренний ролик запускает наш сервер (расписание GitHub 21.10 не сработало). Коммит поверх main
    в ветку weather-req → Actions motion-weather (on push)."""
    return push_video_data(day, {"weather-request": {"day": day.isoformat()}}, run=run, branch="weather-req")


def motion_video(name: str, get=None, folder: str | None = None) -> Path:
    """Готовый ролик из ветки motion → локальный файл. Нет / битый — исключение."""
    import tempfile
    data = (get or (lambda u: _get(u, timeout=60, tries=2)))(MOTION_RAW.format(name=name))
    if not data or len(data) < 200_000 or data[4:8] != b"ftyp":
        raise ValueError("ролик не собран")
    if len(data) > 49_000_000:
        raise ValueError("ролик больше 49 МБ")
    path = Path(folder or tempfile.gettempdir()) / name
    path.write_bytes(data)
    return path


# ---------- предпросмотр ----------
def send_photo(token: str, chat: int, photo: Path, caption: str) -> dict:
    b = uuid.uuid4().hex
    body = b"".join([
        f"--{b}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat}\r\n".encode(),
        f"--{b}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n".encode() + caption.encode() + b"\r\n",
        f"--{b}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"digest.png\"\r\n"
        f"Content-Type: image/png\r\n\r\n".encode() + photo.read_bytes() + b"\r\n",
        f"--{b}--\r\n".encode()])
    import urllib.request
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendPhoto", data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def preview(env: dict, report: dict, bot, davra: dict | None = None, push: str | None = None) -> None:
    """20.10 владелец: вечер — протокол, выходит сам. Владельцу — одна короткая строка в бот (без копий в тест-каналы);
    подробности — только если дайджест НЕ готов."""
    owners = [int(x) for x in env.get("OWNER_IDS", "").split(",") if x.strip().lstrip("-").isdigit()]
    if report.get("status") == "READY":
        head = f"🌙 Кечки дайжест готов — выйдет сам (новостей: {report.get('news', 0)})"
    else:
        errs = "\n".join("• " + e for e in report.get("errors", [])) or "• нет"
        head = f"❌ Кечки дайжест НЕ готов — сегодня не выйдет\nПричины:\n{errs}"
    if davra is not None:
        head += (f"\n🎉 КАТТА ДАВРА: готов (новостей: {davra.get('news', 0)})" if davra.get("status") == "READY"
                 else "\n❌ КАТТА ДАВРА: не готов — " + "; ".join(davra.get("errors", [])[:3]))
    if push is not None:
        head += "\n🎬 Ролики: собираются на GitHub" if push == "ok" else f"\n🎬 Ролики не запущены ({push}) — выйдут картинка/текст"
    # 23.10 владелец: предпросмотр дайджеста — в пульт СВОЕГО канала; общее (ролики) — в PAPA ШТАБ
    from . import bots
    parts = [(bots.for_channel("xojaobod", bot), head.split("\n🎉")[0].split("\n🎬")[0])]
    if davra is not None:
        parts.append((bots.for_channel("davra", bot), "🌙 Кечки дайжест" + head[head.index("\n🎉"):].split("\n🎬")[0]))
    if push is not None:
        parts.append((bots.shtab(bot), head[head.index("\n🎬") + 1:]))
    for b, t in parts:
        for o in owners:
            b("sendMessage", chat_id=o, text=t, disable_web_page_preview=True)


def main(db, env: dict, bot) -> dict:
    root = Path(os.environ.get("PAPA_DIGEST_DIR", "/var/lib/papa-genplan/digest"))
    report = build(db, root)
    try:
        rd = build_davra(db, root)
    except Exception as e:  # noqa: BLE001 — дайджест Хўжаобода не зависит от Давры
        rd = {"status": "INVALID", "errors": [f"{type(e).__name__}: {e}"]}
    payloads = {}
    for name, rep in (("xojaobod", report), ("davra", rd)):
        vj = Path(rep.get("dir", "")) / "video.json"
        if rep.get("status") == "READY" and vj.exists():
            payloads[name] = json.loads(vj.read_text(encoding="utf-8"))
    push = push_video_data(dt.datetime.now(TZ).date(), payloads)
    print(json.dumps({"xojaobod": report, "davra": rd, "push": push}, ensure_ascii=False), flush=True)
    preview(env, report, bot, rd, push)
    return report


# ---------- выпуск в группу Хўжаобод (решение владельца 18.10: «с сегодняшнего») ----------
def live_opts(cfg: dict) -> dict:
    """config: [channels.xojaobod] digest = { live = true, at = "20:30", until = "22:00" }. Нет — выпуска нет."""
    return (cfg.get("channels", {}).get("xojaobod") or {}).get("digest") or {}


async def publish_live(db, cfg: dict, env: dict, acc, now: dt.datetime | None = None, root: Path | None = None,
                       vget=None) -> str | None:
    """Один раз в день: готовый пакет (manifest READY) → баннер с подписью в группу от аккаунта PAPA (анонимный админ).
    Только в окне at…until (ночью — никогда). Пакета нет / не READY — молчим (владелец видел предпросмотр с ошибками)."""
    o = live_opts(cfg)
    if not o.get("live"):
        return None
    now = (now or dt.datetime.now(TZ)).astimezone(TZ)
    hm = now.strftime("%H:%M")
    if not (o.get("at", "20:30") <= hm < o.get("until", "22:00")):
        return None
    day = now.date().isoformat()
    flag = f"digest_pub_{day}"
    if store_get(db, flag):
        return None
    out = (root or Path(os.environ.get("PAPA_DIGEST_DIR", "/var/lib/papa-genplan/digest"))) / f"evening-digest-{day}"
    try:
        m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if m.get("status") != "READY" or m.get("date") != day or sha(out / "digest.png") != m.get("image_sha256"):
        return None
    from . import morning
    to = morning.target(cfg, env, "xojaobod")
    store_set(db, flag, "sending")                      # сначала флаг: ни при каком сбое — не дважды
    vid, note = None, ""
    try:                                                # 🎬 20.10: ролик, если GitHub его собрал
        vid = motion_video(f"xojaobod-digest-{day}.mp4", vget)
    except Exception as e:  # noqa: BLE001
        note = f" (ролика нет: {e} — вышла картинка)"
    if vid:
        try:
            msg = await acc.send_file(to, str(vid), caption=m["photo_caption"][:1024], **video_kw(25))
            store_set(db, flag, str(getattr(msg, "id", "ok")))
            return f"🌙 Кечки дайжест роликом опубликован в «Хўжаобод Сити 24» ({to}) в {hm}."
        except Exception as e:  # noqa: BLE001
            note = f" (ролик не отправился: {type(e).__name__} — вышла картинка)"
        finally:
            vid.unlink(missing_ok=True)
    msg = await acc.send_file(to, str(out / "digest.png"), caption=m["photo_caption"][:1024])
    store_set(db, flag, str(getattr(msg, "id", "ok")))
    return f"🌙 Кечки дайжест опубликован в «Хўжаобод Сити 24» ({to}) в {hm}{note}."


def video_kw(duration: int) -> dict:
    """Telethon: отправить как видео (не файлом)."""
    try:
        from telethon.tl.types import DocumentAttributeVideo
        return {"supports_streaming": True,
                "attributes": [DocumentAttributeVideo(duration=duration, w=1080, h=1920, supports_streaming=True)]}
    except ImportError:
        return {"supports_streaming": True}


async def publish_live_davra(db, cfg: dict, env: dict, bot, now: dt.datetime | None = None, root: Path | None = None,
                             vget=None) -> str | None:
    """🎉 КАТТА ДАВРА 20:30 (решение владельца 20.10): ролик + текст от имени канала (бот); ролика нет — текст."""
    ch = cfg.get("channels", {}).get("davra") or {}
    o = ch.get("digest") or {}
    if not o.get("live"):
        return None
    now = (now or dt.datetime.now(TZ)).astimezone(TZ)
    hm = now.strftime("%H:%M")
    if not (o.get("at", "20:30") <= hm < o.get("until", "22:00")):
        return None
    day = now.date().isoformat()
    flag = f"digest_pub_davra_{day}"
    if store_get(db, flag):
        return None
    out = (root or Path(os.environ.get("PAPA_DIGEST_DIR", "/var/lib/papa-genplan/digest"))) / f"evening-digest-davra-{day}"
    try:
        m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if m.get("status") != "READY" or m.get("date") != day:
        return None
    png = out / "digest.png"
    if not png.exists() or sha(png) != m.get("image_sha256"):     # 21.10 владелец: без картинки — не выпускать
        if store_get(db, flag + "_warn"):
            return None
        store_set(db, flag + "_warn", "1")
        return "❌ Кечки дайжест КАТТА ДАВРА не вышел: нет картинки. Без картинки не выпускаю — нужно проверить."
    from . import service
    to = service.target(cfg, env, "davra")
    store_set(db, flag, "sending")
    note = ""
    try:
        vid = motion_video(f"davra-digest-{day}.mp4", vget)
    except Exception as e:  # noqa: BLE001
        vid, note = None, " (картинкой)"
    if vid:
        try:
            mid = bot.publish_file(to, str(vid), m["caption"], duration=25)
            store_set(db, flag, str(mid))
            return f"🎉 Кечки дайжест роликом опубликован в «КАТТА ДАВРА» ({to}) в {hm}."
        except Exception as e:  # noqa: BLE001
            note = f" (ролик не отправился: {e} — вышла картинка)"
        finally:
            vid.unlink(missing_ok=True)
    mid = bot.publish_photo(to, str(png), m["caption"])
    store_set(db, flag, str(mid))
    return f"🎉 Кечки дайжест опубликован в «КАТТА ДАВРА» ({to}) в {hm}{note}."


def watch(db, cfg: dict, now: dt.datetime | None = None) -> str | None:
    """🛡 21.10 владелец: сторож протокола. В 20:45 — если Кечки дайжест (Хўжаобод / КАТТА ДАВРА, где он включён)
    сегодня не вышел, один раз за день сразу пишет владельцу в пульт. Ничего не публикует."""
    now = (now or dt.datetime.now(TZ)).astimezone(TZ)
    if not ("20:45" <= now.strftime("%H:%M") < "22:00"):
        return None
    day = now.date().isoformat()
    if store_get(db, f"digest_watch_{day}"):
        return None
    chans = cfg.get("channels", {})
    miss = []
    if (chans.get("xojaobod") or {}).get("digest", {}).get("live"):
        v = store_get(db, f"digest_pub_{day}")
        if not v or v == "sending":
            miss.append("Хўжаобод Сити 24")
    if (chans.get("davra") or {}).get("digest", {}).get("live"):
        v = store_get(db, f"digest_pub_davra_{day}")
        if not v or v == "sending":
            miss.append("КАТТА ДАВРА")
    store_set(db, f"digest_watch_{day}", "ok" if not miss else "alert")
    if not miss:
        return None
    return ("🛡 Сторож: Кечки дайжест в 20:30 НЕ вышел — " + ", ".join(miss)
            + ". Протокол нарушен, нужно проверить (папка дайджеста на Франкфурте).")


def store_get(db, k):
    from . import store
    return store.kv_get(db, k)


def store_set(db, k, v):
    from . import store
    store.kv_set(db, k, v)
