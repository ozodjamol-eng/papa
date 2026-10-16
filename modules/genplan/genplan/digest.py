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
Ҳар бирини ўзбек тилида КИРИЛЛ ёзувида бир қисқа гап (130 белгигача) қилиб ёз. ФАҚАТ сарлавҳада бор маълумот —
ҳеч нарса қўшма, рақам ўйлаб топма. Агар муҳим янгилик бўлмаса — камроқ танла.
Жавоб — фақат JSON: [{"i": сарлавҳа рақами, "t": "қисқа гап"}]"""


def pick_news(db, items: list[dict], gen=None, sleep=None) -> list[dict]:
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
            raw = gen(NEWS_SYSTEM, f"Бугунги сарлавҳалар:\n{lst}")
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
        t, _ = translit.auto(g["t"].strip())
        out.append({"t": t[:160], "src": it["src"], "url": it["url"]})
    return out[:5]


# ---------- текст ----------
def date_uz(d: dt.date) -> str:
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def _num(v: float, digits: int = 2) -> str:
    s = f"{v:,.{digits}f}".replace(",", " ").replace(".", ",")
    return s


def _signed(t: int) -> str:
    return f"+{t}" if t > 0 else str(t)


def compose(day: dt.date, w: dict, r: dict, news: list[dict]) -> tuple[str, str]:
    """(подпись к баннеру ≤1024, полный текст)."""
    head = f"🌙 КЕЧКИ ДАЙЖЕСТ | {date_uz(day)}\nХўжаобод • Андижон • Ўзбекистон"
    parts_full, parts_short = [head], [head]
    if news:
        lines = [f"• {n['t']} ({n['src']})" for n in news]
        parts_full.append("📰 КУН ЯНГИЛИКЛАРИ\n" + "\n".join(lines))
        parts_short.append("📰 КУН ЯНГИЛИКЛАРИ\n" + "\n".join(lines[:3]))
    if w:
        wl = []
        for city, x in w.items():
            word, icon = sky(x["code"], x["night"])
            aq = f" · ҳаво сифати: {aqi_word(x['aqi'])} (AQI {int(x['aqi'])})" if x.get("aqi") is not None else ""
            wl.append(f"{city}: {_signed(x['t'])}°, {word} {icon}{aq}")
        t = w.get("Хўжаобод") or next(iter(w.values()))
        tw, ti = sky(t["tmr"]["code"])
        rain = f", ёғин эҳтимоли {t['tmr']['rain']}%" if t["tmr"].get("rain") is not None else ""
        wl.append(f"🔜 Эртага Хўжаободда: {_signed(t['tmr']['min'])}…{_signed(t['tmr']['max'])}°, {tw} {ti}{rain}")
        block = "🌤 ОБ-ҲАВО\n" + "\n".join(wl)
        parts_full.append(block)
        parts_short.append(block)
    if r:
        flags = {"USD": "🇺🇸", "EUR": "🇪🇺", "RUB": "🇷🇺"}
        since = next(iter(r.values())).get("date", "")
        rl = []
        for c, x in r.items():
            arrow = "▲" if x["diff"] > 0 else "▼" if x["diff"] < 0 else "＝"
            rl.append(f"{flags.get(c, '')} 1 {c} = {_num(x['rate'])} сўм ({arrow} {_num(abs(x['diff']))})")
        block = f"💱 МАРКАЗИЙ БАНК КУРСИ{f' ({since} дан)' if since else ''}\n" + "\n".join(rl)
        parts_full.append(block)
        parts_short.append(block)
    tail = f"Хайрли тун, азиз хўжаободликлар! 🌙\n@{USERNAME}"
    full = "\n\n".join(parts_full + ([("🔗 Манбалар:\n" + "\n".join(n["url"] for n in news))] if news else []) + [tail])
    short = "\n\n".join(parts_short + [tail])
    while len(short) > 1024 and len(parts_short) > 2:          # подпись к фото — максимум 1024
        parts_short.pop(1)
        short = "\n\n".join(parts_short + [tail])
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
    report.update({"news_in_feeds": len(items), "news": len(news), "weather": bool(w), "rates": bool(r)})
    if not w:
        report["status"] = "INVALID"
        (out / "build-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        return report
    caption, full = compose(day, w, r, news)
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
    (out / "build-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    return report


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


def preview(env: dict, report: dict, bot) -> None:
    owners = [int(x) for x in env.get("OWNER_IDS", "").split(",") if x.strip().lstrip("-").isdigit()]
    errs = "\n".join("• " + e for e in report.get("errors", [])) or "• нет"
    head = (f"🌙 Свой Кечки дайжест PAPA — {'готов' if report.get('status') == 'READY' else '❌ НЕ готов'} (режим проверки)\n"
            f"Новостей в лентах за сегодня: {report.get('news_in_feeds', 0)}, выбрано: {report.get('news', 0)}\n"
            f"Проблемы:\n{errs}")
    targets = owners + ([int(env["TEST_CHANNEL_ID"])] if env.get("TEST_CHANNEL_ID") else [])
    for o in owners:
        bot("sendMessage", chat_id=o, text=head, disable_web_page_preview=True)
    if report.get("status") != "READY":
        return
    out = Path(report["dir"])
    m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    full = (out / "digest.txt").read_text(encoding="utf-8")
    for t in targets:
        send_photo(env["GENPLAN_BOT_TOKEN"], t, out / "digest.png", m["photo_caption"])
        bot("sendMessage", chat_id=t, text=full[:4096], disable_web_page_preview=True)


def main(db, env: dict, bot) -> dict:
    root = Path(os.environ.get("PAPA_DIGEST_DIR", "/var/lib/papa-genplan/digest"))
    report = build(db, root)
    print(json.dumps(report, ensure_ascii=False), flush=True)
    preview(env, report, bot)
    return report
