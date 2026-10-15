"""Утренний блок — обязательные посты каждого канала (не входят в 20 постов дня).

1) «Бугун — … куни» (06:00; в Хўжаободе — Бомдод+20):
   - есть проверенный день в days.json → пост о нём (ИИ пишет текст только по данным календаря, без выдумок);
   - нет → ИИ придумывает «свой день», но ТОЛЬКО как приглашение («Бугунни … кунига айлантирайлик!»),
     никогда не выдаёт его за официальный.
2) «Хайрли тонг» (06:30; в Хўжаободе — Бомдод+45):
   - сезонное видео с Pixabay (берём только видео; текст всегда наш);
   - на видео наша надпись «ХАЙРЛИ ТОНГ!», «<день недели> ТОНГИ МУБОРАК» и @юзернейм;
   - осень (сен–ноя) → зима с 1 декабря автоматически; одно видео не повторяется 60 дней.

Кто что делает:
- Fabrika (в свободное время) готовит посты на завтра с prepare_from (18:00), кладёт видео в PAPA HUB
  и присылает владельцу предпросмотр с кнопками 🔄 Заменить / 🗑 Не публиковать;
- служба GENPLAN в точное время публикует готовое; не готово к сроку (+15 мин) → пропуск и сообщение владельцу.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import random
import shutil
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

from . import plan

DEFAULTS = {"day_post": "06:00", "greeting": "06:30", "grace": 15, "prepare_from": "18:00",
            "tag": "#Хайрли_тонг", "live": False, "max_seconds": 20}
KEYS = ("day", "greeting")
TITLE = {"day": "Бугун — … куни", "greeting": "Хайрли тонг"}
WEEKDAY = ("Душанба", "Сешанба", "Чоршанба", "Пайшанба", "Жума", "Шанба", "Якшанба")
RETRY = dt.timedelta(minutes=10)
MAX_TRIES = 3
USED_DAYS = 60

SCHEMA = """
CREATE TABLE IF NOT EXISTS fixed_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel TEXT NOT NULL, day TEXT NOT NULL, key TEXT NOT NULL,
    at TEXT NOT NULL,
    text TEXT, hub_msg INTEGER, video_id INTEGER,
    prepared INTEGER NOT NULL DEFAULT 0, tries INTEGER NOT NULL DEFAULT 0, next_try TEXT, redo INTEGER NOT NULL DEFAULT 0,
    preview_sent INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',          -- pending / done / skipped / failed / cancelled
    message_id INTEGER, error TEXT,
    UNIQUE (channel, day, key)
);
CREATE TABLE IF NOT EXISTS stock_used (source TEXT NOT NULL, item_id TEXT NOT NULL, used_at TEXT NOT NULL,
                                       PRIMARY KEY (source, item_id));
"""


def setup(db) -> None:
    db.executescript(SCHEMA)


def opts(ch: dict) -> dict | None:
    m = ch.get("morning")
    if not m or not m.get("enabled", True):
        return None
    return {**DEFAULTS, **m}


def season(day: dt.date) -> str:
    return {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring",
            6: "summer", 7: "summer", 8: "summer"}.get(day.month, "autumn")


# ---------- расписание ----------

def resolve(db, spec: str, day: dt.date) -> dt.datetime:
    """«06:00» — фиксированное время; «bomdod+20|06:10» — от Бомдода (если время намаза введено), иначе запасное."""
    main, _, fallback = spec.partition("|")
    if main.startswith("bomdod"):
        from . import namaz
        s = namaz.schedule_for(db, day)
        if s:
            return plan.slot_time(day, s["bomdod"]) + dt.timedelta(minutes=int(main[6:] or 0))
        return plan.slot_time(day, fallback or "06:15")
    return plan.slot_time(day, main)


def ensure_day(db, cfg: dict, channel: str, day: dt.date, now: dt.datetime) -> int:
    o = opts(cfg["channels"][channel])
    if not o:
        return 0
    n = 0
    for key in KEYS:
        at = resolve(db, o["day_post" if key == "day" else "greeting"], day)
        late = now - at > dt.timedelta(minutes=o["grace"])
        cur = db.execute("INSERT OR IGNORE INTO fixed_posts(channel,day,key,at,status,error) VALUES (?,?,?,?,?,?)",
                         (channel, day.isoformat(), key, at.isoformat(), "skipped" if late else "pending",
                          "служба не работала в это время" if late else None))
        n += cur.rowcount
        if not cur.rowcount:                         # время намаза поправили — сдвигаем ещё не вышедший пост
            db.execute("UPDATE fixed_posts SET at=? WHERE channel=? AND day=? AND key=? AND status='pending' AND at<>?",
                       (at.isoformat(), channel, day.isoformat(), key, at.isoformat()))
    db.commit()
    return n


def ensure_all(db, cfg: dict, now: dt.datetime) -> None:
    for c in cfg["channels"]:
        for d in (now.date(), now.date() + dt.timedelta(days=1)):
            ensure_day(db, cfg, c, d, now)


def busy(db, channel: str, since: dt.datetime) -> list[dt.datetime]:
    return [dt.datetime.fromisoformat(r[0]) for r in db.execute(
        "SELECT at FROM fixed_posts WHERE channel=? AND at>=? AND status IN ('pending','done')", (channel, since.isoformat()))]


def get(db, rid: int):
    return db.execute("SELECT * FROM fixed_posts WHERE id=?", (rid,)).fetchone()


def update(db, rid: int, **kw) -> None:
    db.execute(f"UPDATE fixed_posts SET {', '.join(k + '=?' for k in kw)} WHERE id=?", (*kw.values(), rid))
    db.commit()


def due(db, channel: str, now: dt.datetime, grace: int = 15) -> tuple[list, list]:
    """(готовые к публикации, пропущенные сейчас). Не готовый к сроку пост ждёт grace минут, потом пропуск."""
    ready, missed = [], []
    for r in db.execute("SELECT * FROM fixed_posts WHERE channel=? AND status='pending' AND at<=? ORDER BY at",
                        (channel, now.isoformat())).fetchall():
        late = now - dt.datetime.fromisoformat(r["at"]) > dt.timedelta(minutes=grace)
        if late:
            update(db, r["id"], status="skipped", error="не успели подготовить" if not r["prepared"] else "опоздание")
            missed.append(r)
        elif r["prepared"]:
            ready.append(r)
    return ready, missed


def target(cfg: dict, env: dict, channel: str):
    """Утренний блок может работать в канале раньше остального контента (morning.live = true)."""
    from . import service
    ch = cfg["channels"][channel]
    if (opts(ch) or {}).get("live"):
        return "@" + ch["username"]
    return service.target(cfg, env, channel)


# ---------- «Бугун — … куни» ----------

DAYS_FILE = Path(__file__).with_name("days.json")

DAY_SYSTEM = """Сен — «{title}» Telegram-каналининг муҳарририсан. Эрталабки «Бугун — … куни» постини ёзасан.
Қоидалар:
- Фақат ўзбек тилида, КИРИЛЛ алифбосида.
- Фақат берилган маълумотдан фойдалан: ўзингдан сана, йил, рақам, тарихий факт ТЎҚИМА.
- Хэштег, @юзернейм, ҳавола, имзо ҚЎЙМА — уларни тизим ўзи қўшади.
Тузилма:
1) Биринчи қатор: «📅 БУГУН — <КУН НОМИ БОШ ҲАРФЛАР БИЛАН>!»
2) 2 та қисқа хатбоши (ҳар бири мос эмодзи билан, 1–2 гап): кун нима ҳақида ва бизга қандай алоқаси бор.
3) Охирида — битта самимий тилак ёки ўйлантирувчи савол, эмодзи билан.
Хатбошилар орасида бўш қатор. Жами 450 белгидан ошмасин. Фақат тайёр матнни қайтар."""

CREATIVE_SYSTEM = """Сен — «{title}» Telegram-каналининг муҳарририсан. Бугун расмий нишонланадиган кун йўқ,
шунинг учун эрталаб ўқувчиларга «бугунни ўзимиз бир ёқимли кунга айлантирайлик» деган таклиф ёзасан.
Қоидалар:
- Фақат ўзбек тилида, КИРИЛЛ алифбосида.
- Мавзу оддий, ҳаётий, ҳамма бажара оладиган, самимий бўлсин (оила, меҳр, яхши сўз, саломатлик, табиат, ёрдам, илм, шукр).
  Сиёсат, дин баҳслари, реклама, пул ваъдаси — йўқ.
- МУҲИМ: бу кунни ҲЕЧ ҚАЧОН «расмий», «халқаро», «бутунжаҳон» кун деб атама ва ёлғон тарих тўқима.
- Хэштег, @юзернейм, ҳавола, имзо ҚЎЙМА.
Тузилма:
1) Биринчи қатор: «✨ БУГУННИ «<НОМ>» КУНИГА АЙЛАНТИРАЙЛИК!» (НОМ — 2–4 сўз, бош ҳарфлар билан).
2) 2 та қисқа хатбоши эмодзи билан: бугун нима қилишни таклиф қиламиз (аниқ, оддий иш).
3) Охирги қатор — реакция ёки дўстларга улашишга чақириқ. Изоҳ ёзишни сўрама.
Хатбошилар орасида бўш қатор. Жами 450 белгидан ошмасин. Фақат тайёр матнни қайтар."""

CREATIVE_FALLBACK = [
    ("ЯХШИ СЎЗ", "💬 Бугун камида уч кишига илиқ, самимий сўз айтайлик.", "🌷 Яхши сўз — энг арзон, лекин энг қимматли совға."),
    ("ОТА-ОНАГА ҚЎНҒИРОҚ", "📞 Бугун ота-онамизга ёки кексаларимизга қўнғироқ қилиб, ҳол-аҳвол сўрайлик.", "🤲 Уларнинг дуоси — бизнинг энг катта бойлигимиз."),
    ("ТАБАССУМ", "😊 Бугун учраган ҳар бир инсонга табассум ҳадя этайлик.", "☀️ Табассум юқумли — у бошқаларнинг ҳам кунини чиройли қилади."),
    ("ШУКР", "🤲 Бугун бор неъматларимиз учун шукр қилайлик: соғлиқ, оила, тинчлик.", "🌿 Шукр қилган бандага неъмат зиёда бўлади."),
    ("КИТОБ", "📖 Бугун камида 10 бет китоб ўқийлик.", "💡 Ҳар куни озгина ўқиш — йил охирида катта ўзгариш."),
    ("ЯХШИЛИК", "🤝 Бугун биров учун кичик бўлса ҳам яхшилик қилайлик.", "❤️ Яхшилик ҳеч қачон изсиз кетмайди."),
    ("САЙР", "🚶 Бугун 30 дақиқа очиқ ҳавода сайр қилайлик.", "🍃 Тоза ҳаво ва ҳаракат — кайфият учун энг яхши дори."),
    ("ДЎСТЛИК", "👋 Бугун анчадан бери гаплашмаган дўстимизга хабар ёзайлик.", "🤗 Эски дўст — янги қувонч."),
    ("ТЕЖАМКОРЛИК", "💡 Бугун ортиқча чироқ ва сувни ўчириб, исрофдан сақланайлик.", "🌍 Тежамкорлик — оилага ҳам, табиатга ҳам фойда."),
    ("СОҒЛОМ НОНУШТА", "🍳 Бугун кунни соғлом ва тўйимли нонушта билан бошлайлик.", "💪 Яхши нонушта — бутун кун учун куч."),
    ("ҚЎШНИЧИЛИК", "🏡 Бугун қўшниларимиз ҳолидан хабар олайлик.", "🤝 Яқин қўшни — узоқдаги қариндошдан яхши."),
    ("ЭЗГУ НИЯТ", "✨ Бугун бир эзгу ният қилиб, унга биринчи қадамни ташлайлик.", "🌱 Катта ишлар кичик қадамдан бошланади."),
]


def calendar_day(day: dt.date, path: Path = DAYS_FILE) -> dict | None:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get(f"{day:%m-%d}")


def _fallback_day(day: dt.date, official: dict | None) -> str:
    if official:
        return (f"📅 БУГУН — {official['name'].upper()}!\n\n🌍 Бу кун ҳақида: {official['note']}.\n\n"
                "🤝 Барчага хайрли ва баракали кун тилаймиз!")
    name, a, b = CREATIVE_FALLBACK[day.toordinal() % len(CREATIVE_FALLBACK)]
    return (f"✨ БУГУННИ «{name}» КУНИГА АЙЛАНТИРАЙЛИК!\n\n{a}\n\n{b}\n\n"
            "👍 Қўшилсангиз — реакция қолдиринг ва дўстларингизга улашинг!")


def day_text(db, title: str, day: dt.date, fresh: bool = False, http=None) -> tuple[str, str]:
    """(текст, пометка). Один текст на дату для всех каналов (экономия ИИ); 🔄 — новый вариант."""
    from . import ai, store
    k = f"morning_day_{day.isoformat()}"
    if not fresh:
        cached = store.kv_get(db, k)
        if cached:
            return cached, "из кэша"
    official = calendar_day(day)
    wd = WEEKDAY[day.weekday()]
    if official:
        system = DAY_SYSTEM.format(title=title)
        user = f"Сана: {day:%d.%m.%Y}, {wd}.\nКун: {official['name']}.\nМаълумот: {official['note']}."
    else:
        recent = [store.kv_get(db, f"morning_day_{(day - dt.timedelta(days=i)).isoformat()}") or "" for i in range(1, 15)]
        heads = [t.splitlines()[0] for t in recent if t]
        system = CREATIVE_SYSTEM.format(title=title)
        user = (f"Сана: {day:%d.%m.%Y}, {wd}." + (" Бугун Жума — хайрли кун." if day.weekday() == 4 else "")
                + ("\nЯқинда бўлган мавзуларни такрорлама:\n" + "\n".join(heads) if heads else ""))
    note = "🤖 ИИ" + (" · календарь" if official else " · свой день")
    try:
        text = ai.generate(db, system, user, http) if ai.available() else ""
    except ai.AIError as e:
        text, note = "", f"⚠️ ИИ: {e}"
    if not text:
        text = _fallback_day(day, official)
        note = (note if note.startswith("⚠️") else "") + " · шаблон"
    store.kv_set(db, k, text)
    return text, note.strip(" ·")


# ---------- «Хайрли тонг» ----------

SEASON_EMOJI = {"autumn": "🍂", "winter": "❄️", "spring": "🌸", "summer": "☀️"}
QUERIES = {
    "autumn": ["autumn morning", "autumn leaves sunlight", "autumn forest sunrise", "fall morning fog", "autumn park",
               "autumn coffee", "golden autumn trees", "autumn leaves falling"],
    "winter": ["winter morning", "snow sunrise", "snowy forest", "winter coffee", "snowfall trees", "frost morning"],
    "spring": ["spring morning", "spring flowers sunrise", "blossom tree", "spring meadow", "morning birds spring"],
    "summer": ["summer morning", "sunrise field", "morning sun nature", "summer meadow sunrise", "morning dew"],
}
# людей и всё неподходящее для местной аудитории — не берём; тексты/даты на видео — тоже
BAD_TAGS = {"woman", "women", "girl", "girls", "man", "men", "people", "person", "couple", "kiss", "bikini", "beach",
            "model", "wine", "beer", "alcohol", "halloween", "christmas", "santa", "church", "cross", "text", "date",
            "calendar", "number", "numbers", "typography", "letters", "word", "words", "sign", "logo", "dance", "party",
            "pumpkin", "skull", "fashion", "body", "lady", "female", "male", "boy", "child", "children", "baby"}
WISHES = {
    "autumn": ["Олтин куз тонги қалбингизга илиқлик олиб келсин!", "Бугунги кунингиз куз қуёшидек ёруғ ва илиқ ўтсин!",
               "Хазонрезгидек гўзал, баракали кун тилаймиз!"],
    "winter": ["Совуқ тонгда қалбингиз илиқ бўлсин!", "Қор каби оппоқ ва мусаффо кун тилаймиз!",
               "Иссиқ чой ва яхши кайфият сиз билан бўлсин!"],
    "spring": ["Баҳор тонги каби янги ва ёруғ кун тилаймиз!", "Гуллар каби очилиб кетадиган кун бўлсин!"],
    "summer": ["Ёз қуёши каби ёрқин кун тилаймиз!", "Салқин тонг ва унумли кун тилаймиз!"],
}


def greeting_caption(ch: dict, o: dict, day: dt.date) -> str:
    s = season(day)
    wd = WEEKDAY[day.weekday()]
    wish = "Жума куни барчамизга барака, хотиржамлик ва шодлик олиб келсин! 🤲" if day.weekday() == 4 else \
        WISHES[s][day.toordinal() % len(WISHES[s])]
    lines = [o["tag"]] if o.get("tag") else []
    lines += [f"{SEASON_EMOJI[s]}☀️ ХАЙРЛИ ТОНГ!", "", f"Ассалому алайкум, азизлар! {wd} тонги муборак бўлсин! 🌿", wish]
    sig = ch.get("signature", "")
    return "\n".join(lines) + (f"\n\n{sig}" if sig else "")


def _http_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "PAPA-genplan/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def video_ok(h: dict) -> bool:
    tags = {t.strip().lower() for t in (h.get("tags") or "").split(",")}
    words = {w for t in tags for w in t.split()}
    if (tags | words) & BAD_TAGS:
        return False
    if not 6 <= int(h.get("duration") or 0) <= 60:
        return False
    return bool(_file(h))


def _file(h: dict) -> dict | None:
    v = h.get("videos") or {}
    for k in ("small", "medium", "tiny"):          # small ≈ 1280×720 / 960×540 — достаточно для Telegram
        f = v.get(k) or {}
        if f.get("url") and int(f.get("width") or 0) >= 900:
            return f
    return None


def used(db, source: str, item_id) -> bool:
    lim = (dt.datetime.now(plan.TZ) - dt.timedelta(days=USED_DAYS)).isoformat()
    return db.execute("SELECT 1 FROM stock_used WHERE source=? AND item_id=? AND used_at>=?",
                      (source, str(item_id), lim)).fetchone() is not None


def mark_used(db, source: str, item_id) -> None:
    db.execute("INSERT OR REPLACE INTO stock_used(source,item_id,used_at) VALUES (?,?,?)",
               (source, str(item_id), dt.datetime.now(plan.TZ).isoformat()))
    db.commit()


def pick_video(db, key: str, day: dt.date, salt: int = 0, fetch=_http_json) -> dict:
    s = season(day)
    qs = QUERIES[s]
    rnd = random.Random(day.toordinal() * 31 + salt)
    start = rnd.randrange(len(qs))
    for i in range(len(qs)):
        q = qs[(start + i) % len(qs)]
        url = "https://pixabay.com/api/videos/?" + urllib.parse.urlencode(
            {"key": key, "q": q, "per_page": 50, "safesearch": "true", "order": "popular"})
        hits = [h for h in (fetch(url).get("hits") or []) if video_ok(h) and not used(db, "pixabay", h["id"])]
        if hits:
            h = rnd.choice(hits[:15])
            mark_used(db, "pixabay", h["id"])
            return {"id": h["id"], "url": _file(h)["url"], "query": q, "duration": int(h["duration"]),
                    "page": h.get("pageURL", "")}
    raise RuntimeError("Pixabay: нет подходящих видео (все запросы сезона исчерпаны)")


def download_file(url: str, dst: Path, limit: int = 80 * 1024 * 1024) -> Path:
    req = urllib.request.Request(url, headers={"User-Agent": "PAPA-genplan/1.0"})
    dst.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(req, timeout=120) as r, open(dst, "wb") as f:
        n = 0
        while chunk := r.read(1 << 16):
            n += len(chunk)
            if n > limit:
                raise RuntimeError("видео слишком большое")
            f.write(chunk)
    return dst


FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"


def overlay_png(w: int, h: int, day: dt.date, username: str, dst: Path) -> Path:
    """Прозрачная картинка размера видео: мягкая тень по центру + «ХАЙРЛИ ТОНГ!» + день недели; внизу — значок и @юзернейм."""
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    from . import media
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    base = min(w, h)
    big = ImageFont.truetype(FONT_SERIF, int(base * 0.13))
    small = ImageFont.truetype(FONT, int(base * 0.055))
    title = "ХАЙРЛИ ТОНГ!"
    sub = f"{WEEKDAY[day.weekday()].upper()} ТОНГИ МУБОРАК"
    while big.getlength(title) > w * 0.9:
        big = ImageFont.truetype(FONT_SERIF, int(big.size * 0.92))
    cy = int(h * 0.40)
    # мягкая тёмная подложка — текст читается на любом видео
    band = Image.new("L", (w, h), 0)
    bd = ImageDraw.Draw(band)
    bw, bh = int(big.getlength(title) * 1.15), int(big.size * 2.6)
    bd.ellipse((w // 2 - bw // 2, cy - bh // 2, w // 2 + bw // 2, cy + bh // 2), fill=120)
    band = band.filter(ImageFilter.GaussianBlur(base * 0.06))
    shade = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    shade.putalpha(band)
    img.alpha_composite(shade)
    txt = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(txt)
    d.text((w // 2, cy - int(big.size * 0.25)), title, font=big, fill=(255, 255, 255, 255), anchor="mm")
    d.text((w // 2, cy + int(big.size * 0.75)), sub, font=small, fill=(255, 226, 150, 255), anchor="mm")
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sh.putalpha(txt.getchannel("A").filter(ImageFilter.GaussianBlur(base * 0.006)).point(lambda v: int(v * 0.9)))
    img.alpha_composite(sh, (3, 3))
    img.alpha_composite(txt)
    logo = media.text_logo("@" + username, dst.with_suffix(".logo.png"), height=max(22, int(base * 0.045)))
    lg = Image.open(logo).convert("RGBA")
    lg.putalpha(lg.getchannel("A").point(lambda v: int(v * 0.9)))
    img.alpha_composite(lg, ((w - lg.width) // 2, h - lg.height - int(h * 0.05)))
    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, "PNG")
    return dst


def render_greeting(src: Path, day: dt.date, username: str, dst: Path, seconds: int = 20) -> Path:
    from . import media
    info = media.probe(src)
    portrait = (info["h"] or 720) > (info["w"] or 1280)
    w, h = (720, 1280) if portrait else (1280, 720)
    dur = max(6.0, min(info["dur"] or float(seconds), float(seconds)))
    ov = overlay_png(w, h, day, username, dst.with_suffix(".overlay.png"))
    flt = (f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps=30[v];"
           f"[1:v]format=rgba,fade=t=in:st=0.6:d=1.2:alpha=1[o];[v][o]overlay=0:0,format=yuv420p")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-loop", "1", "-framerate", "30", "-i", str(ov),
           "-filter_complex", flt, "-t", f"{dur:.2f}", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
           "-movflags", "+faststart", str(dst)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0 or not dst.exists():
        raise RuntimeError(f"ffmpeg: {(r.stderr or '').strip()[-200:]}")
    return dst


# ---------- подготовка (Fabrika) ----------

def to_prepare(db, cfg: dict, now: dt.datetime) -> list:
    rows = db.execute("SELECT * FROM fixed_posts WHERE status='pending' AND prepared=0 AND at>? ORDER BY at",
                      (now.isoformat(),)).fetchall()
    out = []
    for r in rows:
        if r["channel"] not in cfg["channels"]:
            continue
        o = opts(cfg["channels"][r["channel"]])
        if not o or (r["next_try"] and r["next_try"] > now.isoformat()):
            continue
        day = dt.date.fromisoformat(r["day"])
        if day > now.date() and now < plan.slot_time(now.date(), o["prepare_from"]):
            continue                                             # завтрашнее — готовим вечером
        out.append(r)
    return out


def prepare_one(bot, db, cfg: dict, env: dict, r, now: dt.datetime, work_root: Path, fetch=_http_json,
                upload=None) -> str:
    ch = cfg["channels"][r["channel"]]
    o = opts(ch)
    day = dt.date.fromisoformat(r["day"])
    sig = ch.get("signature", "")
    if r["key"] == "day":
        body, note = day_text(db, ch["title"], day, fresh=bool(r["redo"]))
        update(db, r["id"], text=body + (f"\n\n{sig}" if sig else ""), prepared=1, redo=0, error=None, preview_sent=0)
        return note
    key = env.get("PIXABAY_API_KEY") or os.environ.get("PIXABAY_API_KEY")
    caption = greeting_caption(ch, o, day)
    if not key:
        raise RuntimeError("нет PIXABAY_API_KEY")
    work = work_root / f"morning-{r['id']}-{r['tries']}"
    try:
        v = pick_video(db, key, day, salt=r["id"] * 7 + r["tries"] + (r["video_id"] or 0), fetch=fetch)
        src = download_file(v["url"], work / "src.mp4")
        out = render_greeting(src, day, ch["username"], work / "out.mp4", int(o["max_seconds"]))
        if upload is None:
            from .fabrika import upload_video as upload
        res = upload(env["GENPLAN_BOT_TOKEN"], int(env["HUB_CHAT_ID"]), out, caption)
        update(db, r["id"], text=caption, hub_msg=int(res["message_id"]), video_id=int(v["id"]), prepared=1, redo=0,
               error=None, preview_sent=0)
        return f"🎬 Pixabay #{v['id']} («{v['query']}», {v['duration']} с)"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def preview(bot, db, cfg: dict, env: dict, rid: int, note: str = "") -> None:
    r = get(db, rid)
    ch = cfg["channels"][r["channel"]]
    at = dt.datetime.fromisoformat(r["at"])
    from . import smart
    where = "в канал" if str(target(cfg, env, r["channel"])).startswith("@") else "в тестовый чат"
    head = f"👁 {ch['title']} · {TITLE[r['key']]} · {smart.fmt(at, dt.datetime.now(plan.TZ))} ({where})" + (f"\n{note}" if note else "")
    kb = {"inline_keyboard": [[{"text": "🔄 Заменить", "callback_data": f"mo:r:{rid}"},
                               {"text": "🗑 Не публиковать", "callback_data": f"mo:x:{rid}"}]]}
    owners = [int(x) for x in str(env.get("OWNER_IDS", "")).split(",") if x.strip()]
    for o in owners:
        if r["hub_msg"]:
            bot("copyMessage", chat_id=o, from_chat_id=int(env["HUB_CHAT_ID"]), message_id=r["hub_msg"],
                caption=(head + "\n—\n" + (r["text"] or ""))[:1024], reply_markup=kb)
        else:
            bot("sendMessage", chat_id=o, text=(head + "\n—\n" + (r["text"] or ""))[:4096], reply_markup=kb,
                disable_web_page_preview=True)
    update(db, rid, preview_sent=1)


def prepare_next(bot, db, cfg: dict, env: dict, now: dt.datetime | None = None, work_root: Path | None = None,
                 fetch=_http_json, upload=None) -> bool:
    """Один шаг подготовки (вызывается Fabrika, когда нет других заданий). True — что-то сделано."""
    now = (now or dt.datetime.now(plan.TZ)).astimezone(plan.TZ)
    ensure_all(db, cfg, now)
    work_root = work_root or Path(os.environ.get("PAPA_GENPLAN_STATE", "/var/lib/papa-genplan")) / "work"
    rows = to_prepare(db, cfg, now)
    if not rows:
        pend = db.execute("SELECT id FROM fixed_posts WHERE status='pending' AND prepared=1 AND preview_sent=0").fetchall()
        for p in pend:
            preview(bot, db, cfg, env, p["id"])
        return bool(pend)
    r = rows[0]
    try:
        note = prepare_one(bot, db, cfg, env, r, now, work_root, fetch, upload)
        preview(bot, db, cfg, env, r["id"], note)
    except Exception as e:  # noqa: BLE001
        tries = r["tries"] + 1
        if r["key"] == "greeting" and tries >= MAX_TRIES:         # видео не получилось — выходит текстом
            ch = cfg["channels"][r["channel"]]
            update(db, r["id"], tries=tries, text=greeting_caption(ch, opts(ch), dt.date.fromisoformat(r["day"])),
                   prepared=1, error=str(e)[:300], preview_sent=0)
            preview(bot, db, cfg, env, r["id"], f"⚠️ Видео не получилось ({e}) — выйдет текстом")
        else:
            update(db, r["id"], tries=tries, next_try=(now + RETRY).isoformat(), error=str(e)[:300])
    return True


# ---------- кнопки и обзор ----------

def callback(bot, db, cq: dict) -> str:
    _, act, rid = cq["data"].split(":")
    r = get(db, int(rid))
    chat, mid = cq["message"]["chat"]["id"], cq["message"]["message_id"]
    if not r:
        bot("answerCallbackQuery", callback_query_id=cq["id"], text="Пост не найден")
        return "missing"
    if r["status"] == "done":
        bot("answerCallbackQuery", callback_query_id=cq["id"], text="Уже опубликован")
        return "done"
    if act == "x":
        update(db, r["id"], status="cancelled")
        note = "🗑 Не будет опубликован. «🔄 Заменить» — вернуть с новым вариантом."
    else:
        update(db, r["id"], status="pending", prepared=0, redo=1, tries=0, next_try=None, hub_msg=None, preview_sent=0)
        note = "🔄 Готовлю новый вариант — пришлю через 1–2 минуты."
    try:
        bot("editMessageReplyMarkup", chat_id=chat, message_id=mid,
            reply_markup={"inline_keyboard": [[{"text": "🔄 Заменить", "callback_data": f"mo:r:{rid}"}]]})
    except Exception:  # noqa: BLE001
        pass
    bot("answerCallbackQuery", callback_query_id=cq["id"], text=note[:190])
    return "mo:" + act


def overview(db, cfg: dict, now: dt.datetime) -> str:
    """/morning — утренний блок на сегодня и завтра; не показанные предпросмотры Fabrika пришлёт заново."""
    icon = {"pending": "⏳", "done": "✔️", "skipped": "·", "failed": "❌", "cancelled": "🗑"}
    lines = ["🌅 Утренний блок"]
    for d in (now.date(), now.date() + dt.timedelta(days=1)):
        rows = db.execute("SELECT * FROM fixed_posts WHERE day=? ORDER BY at", (d.isoformat(),)).fetchall()
        if not rows:
            continue
        lines.append(f"\n📅 {d:%d.%m} · {WEEKDAY[d.weekday()]}")
        for r in rows:
            ch = cfg["channels"].get(r["channel"], {"title": r["channel"]})
            ready = "" if r["status"] != "pending" else (" — готов" if r["prepared"] else " — готовится")
            lines.append(f"{icon.get(r['status'], '•')} {dt.datetime.fromisoformat(r['at']):%H:%M} {ch['title']}: "
                         f"{TITLE[r['key']]}{ready}" + (f" ({r['error']})" if r["error"] and r["status"] != "done" else ""))
    db.execute("UPDATE fixed_posts SET preview_sent=0 WHERE status='pending' AND prepared=1 AND day>=?", (now.date().isoformat(),))
    db.commit()
    lines.append("\nПредпросмотры готовых постов пришлю ещё раз.")
    return "\n".join(lines)


def today_lines(db, channel: str, day: dt.date) -> list[tuple[str, str]]:
    icon = {"pending": "🌅", "done": "✔️", "skipped": "·", "failed": "❌", "cancelled": "🗑"}
    return [(f"{dt.datetime.fromisoformat(r['at']):%H:%M}",
             f"{icon.get(r['status'], '•')} {dt.datetime.fromisoformat(r['at']):%H:%M}  {TITLE[r['key']]}")
            for r in db.execute("SELECT * FROM fixed_posts WHERE channel=? AND day=? ORDER BY at", (channel, day.isoformat()))]
