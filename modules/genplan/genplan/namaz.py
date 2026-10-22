"""Намоз — главный местный модуль (перенос из GENPLAN 5, с усилением).

Как в GENPLAN 5:
- источник времени — ТОЛЬКО то, что ввёл владелец (сайты ошибались до 47 минут);
- ввод одним сообщением, все 5 времён; дата в тексте — только для показа: блок без дат действует с сегодняшнего дня;
- таблица всех 5 времён за 30 минут до Бомдода; напоминание ровно за 10 минут до каждого намаза;
  в само время намаза — ничего;
- пятница: напоминание о Жуме за 45 минут до Пешина; «тихое окно» −20/+35 минут — обычные посты туда не ставятся;
- опоздал больше чем на 15 минут (сервер стоял) — не публикуем поздно, отмечаем «пропущено».
Усиление:
- время принимается в любом виде: 19:10, 19 10, 19.10, 19-10, 1910;
- можно ввести сразу несколько дней (каждый день — со своей датой);
- если время не обновлялось больше remind_after_days дней или его нет — вечером бот напоминает владельцу.
"""
from __future__ import annotations

import datetime as dt
import re

from . import plan

NAMES = ("bomdod", "peshin", "asr", "shom", "xufton")
LABEL = {"bomdod": "Бомдод", "peshin": "Пешин", "asr": "Аср", "shom": "Шом", "xufton": "Хуфтон"}
ICON = {"bomdod": "🌅", "peshin": "☀️", "asr": "🌤", "shom": "🌇", "xufton": "🌙"}
VARIANTS = {"bomdod": ("бомдод", "bomdod"), "peshin": ("пешин", "peshin"), "asr": ("аср", "asr"),
            "shom": ("шом", "shom"), "xufton": ("хуфтон", "xufton", "xuftan", "хуфтан")}
WEEKDAY = ("Душанба", "Сешанба", "Чоршанба", "Пайшанба", "Жума", "Шанба", "Якшанба")
TIME_RE = re.compile(r"(?<!\d)(\d{1,2})\s*[:.\-,;\s]?\s*(\d{2})(?!\d)")
HEAD_RE = re.compile(r"^\W*\d{1,2}[.\-/]\d{1,2}(?:[.\-/]\d{4})?\W*(?:\w+)?\W*$")   # строка-дата: «16.10», «📅 16.10.2026 Жума»
DATE_RE = re.compile(r"(?<!\d)(\d{1,2})[.\-/](\d{1,2})(?:[.\-/](\d{4}))?(?!\d)")
DEFAULTS = {"table_before": 30, "alert_before": 10, "juma_before": 45, "juma_lock": [20, 35],
            "grace": 15, "remind_at": "20:00", "remind_after_days": 7}

SCHEMA = """
CREATE TABLE IF NOT EXISTS namaz_schedule (
    day      TEXT PRIMARY KEY,           -- с этого дня действует (до следующей записи)
    bomdod TEXT NOT NULL, peshin TEXT NOT NULL, asr TEXT NOT NULL, shom TEXT NOT NULL, xufton TEXT NOT NULL,
    saved_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS namaz_posts (
    channel TEXT NOT NULL, day TEXT NOT NULL, key TEXT NOT NULL,
    at TEXT NOT NULL, text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',      -- pending / done / skipped / failed
    message_id INTEGER, error TEXT,
    PRIMARY KEY (channel, day, key)
);
CREATE TABLE IF NOT EXISTS namaz_locks (channel TEXT NOT NULL, day TEXT NOT NULL, start TEXT NOT NULL, end TEXT NOT NULL,
                                        PRIMARY KEY (channel, day));
"""


def setup(db) -> None:
    db.executescript(SCHEMA)
    # 22.10 владелец: готовый пост намаза (баннер + его текст) на неделю — колонки добавляются, старое не трогаем
    for table, col in (("namaz_schedule", "photo"), ("namaz_schedule", "caption"), ("namaz_posts", "photo")):
        if col not in {r[1] for r in db.execute(f"PRAGMA table_info({table})")}:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {col} TEXT")
    db.commit()


def opts(ch: dict) -> dict | None:
    n = ch.get("namaz")
    if not n or not n.get("enabled", True):
        return None
    return {**DEFAULTS, **n}


# ---------- ввод ----------

def looks_like_schedule(text: str) -> bool:
    low = (text or "").lower()
    return sum(any(v in low for v in VARIANTS[n]) for n in NAMES) >= 3


def _parse_block(lines: list[str]) -> dict:
    times, errors = {}, []
    for n in NAMES:
        line = next((ln for ln in lines if any(v in ln.lower() for v in VARIANTS[n])), None)
        if line is None:
            errors.append(f"нет строки «{LABEL[n]}»")
            continue
        rest = line.lower()
        for v in VARIANTS[n]:
            rest = rest.replace(v, " ")
        m = TIME_RE.search(rest)
        if not m:
            errors.append(f"{LABEL[n]}: не вижу время")
            continue
        h, mi = int(m.group(1)), int(m.group(2))
        if h > 23 or mi > 59:
            errors.append(f"{LABEL[n]}: неверное время {h}:{mi:02d}")
            continue
        times[n] = f"{h:02d}:{mi:02d}"
    if not errors:
        order = [times[n] for n in NAMES]
        if order != sorted(order):
            errors.append("время идёт не по порядку (Бомдод < Пешин < Аср < Шом < Хуфтон) — проверьте")
    if errors:
        raise ValueError("; ".join(errors))
    return times


def parse(text: str, today: dt.date) -> list[tuple[dt.date, dict]]:
    """Один блок без дат → с сегодняшнего дня. Несколько блоков, каждый с датой → по своим дням (ввод на неделю)."""
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    def is_head(ln: str) -> bool:
        if any(v in ln.lower() for n in NAMES for v in VARIANTS[n]):
            return False
        return bool(HEAD_RE.match(ln)) or bool(re.search(r"\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4}", ln) and "намоз" in ln.lower())
    heads = [i for i, ln in enumerate(lines) if is_head(ln)]
    if len(heads) <= 1:
        return [(today, _parse_block(lines))]
    out = []
    for k, i in enumerate(heads):
        block = lines[i:heads[k + 1] if k + 1 < len(heads) else len(lines)]
        d, mo, y = DATE_RE.search(block[0]).groups()
        day = dt.date(int(y) if y else today.year, int(mo), int(d))
        try:
            out.append((day, _parse_block(block[1:])))
        except ValueError as e:
            raise ValueError(f"{day:%d.%m}: {e}") from None
    return out


MONTHS = ("январ", "феврал", "март", "апрел", "май", "июн", "июл", "август", "сентябр", "октябр", "ноябр", "декабр")
RANGE_RE = re.compile(r"(?<!\d)(\d{1,2})\s*[–—\-]\s*\d{1,2}\s+([а-яўқғҳё]+)", re.I)
MONTH_RE = re.compile(r"(?<!\d)(\d{1,2})\s+([а-яўқғҳё]+)", re.I)


def start_date(text: str, today: dt.date) -> dt.date:
    """С какого дня действует готовый пост: «23–29 октябр» / «23 октябр» / «23.10.2026» → 23.10; прошедшая дата или
    даты нет — с сегодняшнего дня. Готовый пост на следующую неделю, брошенный в четверг, не трогает сегодняшний намаз."""
    day = None
    for rx in (RANGE_RE, MONTH_RE):
        for m in rx.finditer(text or ""):
            mon = next((i + 1 for i, w in enumerate(MONTHS) if m.group(2).lower().startswith(w)), None)
            if mon:
                try:
                    day = dt.date(today.year, mon, int(m.group(1)))
                except ValueError:
                    continue
                break
        if day:
            break
    if day is None:
        m = re.search(r"(?<!\d)(\d{1,2})\.(\d{1,2})\.(\d{4})(?!\d)", text or "")
        if m:
            try:
                day = dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            except ValueError:
                day = None
    if day and day < today - dt.timedelta(days=180):          # «5 январ», брошенный в декабре, — следующий год
        day = day.replace(year=day.year + 1)
    return day if day and day > today else today


def parse_post(caption: str, today: dt.date) -> tuple[dt.date, dict]:
    """Готовый пост намаза (баннер + текст): время — из текста поста, начало — из даты в тексте."""
    return start_date(caption, today), _parse_block([ln for ln in (caption or "").splitlines() if ln.strip()])


def save(db, items: list[tuple[dt.date, dict]], now: dt.datetime, photo: str | None = None,
         caption: str | None = None) -> None:
    """photo/caption — готовый пост владельца: выходит как есть вместо нашей таблицы. Ввод одним текстом их снимает."""
    for day, t in items:
        db.execute("INSERT INTO namaz_schedule(day,bomdod,peshin,asr,shom,xufton,saved_at,photo,caption) "
                   "VALUES (?,?,?,?,?,?,?,?,?) "
                   "ON CONFLICT(day) DO UPDATE SET bomdod=excluded.bomdod, peshin=excluded.peshin, asr=excluded.asr, "
                   "shom=excluded.shom, xufton=excluded.xufton, saved_at=excluded.saved_at, "
                   "photo=excluded.photo, caption=excluded.caption",
                   (day.isoformat(), *[t[n] for n in NAMES], now.isoformat(), photo, caption))
    # ещё не вышедшие посты на эти дни пересоздаются по новому времени; вышедшие не трогаем
    for day, _ in items:
        db.execute("DELETE FROM namaz_posts WHERE day>=? AND status='pending'", (day.isoformat(),))
        db.execute("DELETE FROM namaz_locks WHERE day>=?", (day.isoformat(),))
    db.commit()


def schedule_for(db, day: dt.date):
    return db.execute("SELECT * FROM namaz_schedule WHERE day<=? ORDER BY day DESC LIMIT 1", (day.isoformat(),)).fetchone()


def editor_text(db, today: dt.date) -> str:
    s = schedule_for(db, today)
    t = {n: (s[n] if s else "00:00") for n in NAMES}
    return f"Намоз вақтлари: {today:%d.%m.%Y}\n" + "\n".join(f"{LABEL[n]} {t[n]}" for n in NAMES)


# ---------- публикации ----------

def _at(day: dt.date, hm: str, minus: int) -> dt.datetime:
    return plan.slot_time(day, hm) - dt.timedelta(minutes=minus)


def ensure_day(db, cfg: dict, channel: str, day: dt.date, now: dt.datetime) -> int:
    """Создаёт посты намаза на день (идемпотентно). Возвращает число новых."""
    ch = cfg["channels"][channel]
    o = opts(ch)
    s = schedule_for(db, day)
    if not o or not s:
        return 0
    sig = ch.get("signature", "")
    tail = f"\n\n{sig}" if sig else ""
    photo = s["photo"] if "photo" in s.keys() else None
    if photo and channel != "xojaobod":
        photo = None                                          # готовый пост намаза — только Хўжаобод (решение 15.10)
    if photo:                                                 # 22.10: готовый пост владельца — как есть, без лишних слов
        table = s["caption"] or ""
    else:
        table = (f"🕌 НАМОЗ ВАҚТЛАРИ\n📅 {day:%d.%m.%Y} · {WEEKDAY[day.weekday()]}\n\n"
                 + "\n".join(f"{ICON[n]} {LABEL[n]} — {s[n]}" for n in NAMES)
                 + "\n\n🤲 Намозларингиз қабул бўлсин." + tail)
    posts = [("table", _at(day, s["bomdod"], o["table_before"]), table)]
    for n in NAMES:
        posts.append((f"alert_{n}", _at(day, s[n], o["alert_before"]),
                      f"🕌 {LABEL[n]} намозига {o['alert_before']} дақиқа қолди ({s[n]})." + tail))
    if day.weekday() == 4:                                   # пятница — Жума
        posts.append(("juma", _at(day, s["peshin"], o["juma_before"]),
                      f"🕌 Жума намозига {s['peshin']} да тайёрланинг." + tail))
        lo, hi = o["juma_lock"]
        p = plan.slot_time(day, s["peshin"])
        db.execute("INSERT OR IGNORE INTO namaz_locks(channel,day,start,end) VALUES (?,?,?,?)",
                   (channel, day.isoformat(), (p - dt.timedelta(minutes=lo)).isoformat(),
                    (p + dt.timedelta(minutes=hi)).isoformat()))
    n_new = 0
    for key, at, text in posts:
        late = now - at > dt.timedelta(minutes=o["grace"])
        cur = db.execute("INSERT OR IGNORE INTO namaz_posts(channel,day,key,at,text,status,error,photo) "
                         "VALUES (?,?,?,?,?,?,?,?)",
                         (channel, day.isoformat(), key, at.isoformat(), text, "skipped" if late else "pending",
                          "опоздание — не публикуем поздно" if late else None, photo if key == "table" else None))
        n_new += cur.rowcount
    db.commit()
    return n_new


def busy(db, channel: str, since: dt.datetime) -> list[dt.datetime]:
    return [dt.datetime.fromisoformat(r[0]) for r in db.execute(
        "SELECT at FROM namaz_posts WHERE channel=? AND at>=? AND status IN ('pending','done')", (channel, since.isoformat()))]


def locked(db, channel: str, t: dt.datetime) -> bool:
    return db.execute("SELECT 1 FROM namaz_locks WHERE channel=? AND start<=? AND end>=?",
                      (channel, t.isoformat(), t.isoformat())).fetchone() is not None


def due(db, channel: str, now: dt.datetime, grace: int = 15) -> list:
    rows = db.execute("SELECT * FROM namaz_posts WHERE channel=? AND status='pending' AND at<=? ORDER BY at",
                      (channel, now.isoformat())).fetchall()
    out = []
    for r in rows:
        if now - dt.datetime.fromisoformat(r["at"]) > dt.timedelta(minutes=grace):
            mark(db, channel, r["day"], r["key"], "skipped", error="опоздание — не публикуем поздно")
        else:
            out.append(r)
    return out


def mark(db, channel: str, day: str, key: str, status: str, message_id: int | None = None, error: str | None = None):
    db.execute("UPDATE namaz_posts SET status=?, message_id=?, error=? WHERE channel=? AND day=? AND key=?",
               (status, message_id, error, channel, day, key))
    db.commit()


def reminder(db, cfg: dict, now: dt.datetime) -> str | None:
    """Вечернее напоминание владельцу: времени нет / давно не обновлялось. Не чаще раза в день."""
    chans = [c for c, ch in cfg["channels"].items() if opts(ch)]
    if not chans:
        return None
    o = opts(cfg["channels"][chans[0]])
    if now.time() < plan.slot_time(now.date(), o["remind_at"]).time():
        return None
    tomorrow = now.date() + dt.timedelta(days=1)
    s = schedule_for(db, tomorrow)
    if s and (tomorrow - dt.date.fromisoformat(s["day"])).days < int(o["remind_after_days"]):
        return None
    from . import store
    key = f"namaz_remind_{now.date().isoformat()}"
    if store.kv_get(db, key):
        return None
    store.kv_set(db, key, "1")
    if not s:
        return "⚠️ Намоз вақтлари киритилмаган — эртага намоз постлари чиқмайди.\nНажмите «🕌 Намоз» и пришлите время."
    days = (tomorrow - dt.date.fromisoformat(s["day"])).days
    return (f"🕌 Время намаза не обновлялось {days} дн. (с {dt.date.fromisoformat(s['day']):%d.%m}).\n"
            "Время сдвигается каждый день — пришлите свежее, нажмите «🕌 Намоз».")


def today_lines(db, channel: str, day: dt.date) -> list[tuple[str, str]]:
    icon = {"pending": "🕌", "done": "✔️", "skipped": "·", "failed": "❌"}
    name = {"table": "Намоз вақтлари (жадвал)", "juma": "Жума эслатмаси"}
    out = []
    for r in db.execute("SELECT * FROM namaz_posts WHERE channel=? AND day=? ORDER BY at", (channel, day.isoformat())):
        t = dt.datetime.fromisoformat(r["at"])
        label = name.get(r["key"]) or f"{LABEL.get(r['key'].replace('alert_', ''), r['key'])} — эслатма"
        out.append((f"{t:%H:%M}", f"{icon.get(r['status'], '•')} {t:%H:%M}  {label}"))
    return out
