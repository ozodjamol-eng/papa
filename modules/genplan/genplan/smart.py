"""Умное время (по логике GENPLAN 5, с улучшениями).

Как GENPLAN 5:
- у каждого поста — ТОЧНОЕ время публикации; бот сам предлагает «🧠 Умное время», владелец подтверждает одним нажатием;
- окно публикаций 07:00–22:00; музыка — не раньше 10:00;
- между постами — минимальный промежуток (учитываются и посты, сделанные в канале вручную — «пульс»);
- хороший пост не пропадает: если сегодня мест нет — завтра и дальше (в пределах срока годности рубрики);
- срочный пост выходит сразу, а запланированные рядом с ним сдвигаются, чтобы не было двух постов подряд;
- время, выбранное владельцем вручную, автоматически не двигается.
Улучшение: умное время опирается на сетку рубрик канала (ритм дня), а не на «первое свободное место».
"""
from __future__ import annotations

import datetime as dt

from . import plan, store

DEFAULT_RULES = {"window": ["07:00", "22:00"], "music_from": "10:00", "gap": 30, "ttl_days": 3,
                 "fresh_rubrics": [], "music_rubrics": ["Мусиқа", "Қўшиқ", "Клип/премьера", "Кун хонандаси"]}
LEAD = dt.timedelta(minutes=2)          # раньше чем через 2 минуты не планируем


def rules(ch: dict) -> dict:
    return {**DEFAULT_RULES, **(ch.get("rules") or {})}


def hm(t: str) -> dt.time:
    h, m = map(int, t.split(":"))
    return dt.time(h, m)


def allowed(ch: dict, t: dt.datetime, rubric: str | None) -> bool:
    r = rules(ch)
    lo, hi = hm(r["window"][0]), hm(r["window"][1])
    if not (lo <= t.time() <= hi):
        return False
    if rubric in r["music_rubrics"] and t.time() < hm(r["music_from"]):
        return False
    return True


def occupied(db, channel: str, now: dt.datetime, exclude: int | None = None) -> list[dt.datetime]:
    from . import namaz
    out = [dt.datetime.fromisoformat(m["scheduled_at"]) for m in store.scheduled(db, channel) if m["id"] != exclude]
    from . import morning
    since = now - dt.timedelta(hours=3)
    return out + store.pulse_since(db, channel, since) + namaz.busy(db, channel, since) + morning.busy(db, channel, since)


def blocked(db, channel: str, t: dt.datetime) -> bool:
    """Тихое окно Жумы (и другие запреты модуля намаза)."""
    from . import namaz
    return namaz.locked(db, channel, t)


def is_free(ch: dict, t: dt.datetime, busy: list[dt.datetime]) -> bool:
    gap = dt.timedelta(minutes=int(rules(ch)["gap"]))
    return all(abs(t - b) >= gap for b in busy)


def grid(ch: dict, day: dt.date) -> list[tuple[dt.datetime, dict]]:
    return [(plan.slot_time(day, s["t"]), s) for s in plan.day_slots(ch, day) if s["kind"] in ("content", "music", "ad")]


def ttl(ch: dict, rubric: str | None) -> int:
    r = rules(ch)
    return 0 if rubric in r["fresh_rubrics"] else int(r["ttl_days"])


def smart_time(db, cfg: dict, channel: str, rubric: str | None, now: dt.datetime,
               exclude: int | None = None) -> tuple[dt.datetime, str] | None:
    """Лучшее время: слот своей рубрики → слот, где рубрика запасная → (на следующий день то же) → ближайшее свободное."""
    ch = cfg["channels"][channel]
    busy = occupied(db, channel, now, exclude)
    days = ttl(ch, rubric)
    for d in range(days + 1):
        day = now.date() + dt.timedelta(days=d)
        slots = [(t, s) for t, s in grid(ch, day) if t >= now + LEAD and allowed(ch, t, rubric) and is_free(ch, t, busy) and not blocked(db, channel, t)]
        for t, s in slots:
            if s["kind"] != "ad" and s.get("rubric") == rubric:
                return t, f"слот «{rubric}»"
        for t, s in slots:
            if s["kind"] != "ad" and rubric in s.get("fallback", []):
                return t, f"слот «{s['rubric']}» (подходит)"
    nxt = other_times(db, cfg, channel, rubric, now, n=1, exclude=exclude)
    return (nxt[0], "ближайшее свободное время") if nxt else None


def other_times(db, cfg: dict, channel: str, rubric: str | None, now: dt.datetime, n: int = 8,
                exclude: int | None = None) -> list[dt.datetime]:
    """Свободные моменты на сегодня и завтра: слоты сетки + каждые 30 минут, с соблюдением правил."""
    ch = cfg["channels"][channel]
    busy = occupied(db, channel, now, exclude)
    out: list[dt.datetime] = []
    for d in (0, 1):
        day = now.date() + dt.timedelta(days=d)
        cands = {t for t, s in grid(ch, day) if s["kind"] != "ad"}
        cands |= {plan.slot_time(day, f"{h:02d}:{m:02d}") for h in range(7, 23) for m in (0, 30)}
        for t in sorted(cands):
            if t >= now + LEAD and allowed(ch, t, rubric) and is_free(ch, t, busy + out) and not blocked(db, channel, t):
                out.append(t)
                if len(out) >= n:
                    return out
    return out


def guess_rubric(cfg: dict, channel: str, body: str, has_audio: bool = False) -> str:
    """Рубрика по смыслу текста: тема (ключевые слова) → рубрика канала (config guess). Иначе — guess_default."""
    from . import text as T
    ch = cfg["channels"][channel]
    g = ch.get("guess") or {}
    if has_audio and g.get("Мусиқа"):
        return g["Мусиқа"]
    body, _ = T.translit.auto(T.strip_sources(body or ""))
    t = T.topic_of(body, cfg.get("topics", []))
    if t and g.get(t.get("name")):
        return g[t["name"]]
    return ch.get("guess_default") or _first_rubric(ch)


LOCAL = ("хўжаобод", "хужаобод", "хожаобод", "xo'jaobod", "xojaobod", "андижон", "andijon", "андижан")
SHOWBIZ = ("клип", "премьера", "хонанда", "қўшиқчи", "концерт", "юлдуз", "актёр", "актриса", "шоу-бизнес", "шоу бизнес",
           "qo'shiq", "klip", "xonanda", "premyera")


def guess_channel(cfg: dict, body: str, has_audio: bool = False) -> str:
    """Бросил пост — бот сам выбирает канал (только из auto_channels; остальные — пока тест)."""
    from . import text as T
    default = cfg.get("default_channel") or next(iter(cfg["channels"]))
    allowed = [c for c in (cfg.get("auto_channels") or [default]) if c in cfg["channels"]]
    low, _ = T.translit.auto(T.strip_sources(body or ""))
    low = low.lower()
    if "xojaobod" in allowed and any(w in low for w in LOCAL):
        return "xojaobod"
    if "paparazzi" in allowed:
        t = T.topic_of(low, cfg.get("topics", []))
        if has_audio or any(w in low for w in SHOWBIZ) or (t and t.get("name") == "Мусиқа"):
            return "paparazzi"
    return default if default in allowed or not allowed else allowed[0]


def _first_rubric(ch: dict) -> str:
    return next(s["rubric"] for s in ch["slots"] if s["kind"] == "content")


def shift_after_urgent(db, cfg: dict, channel: str, at: dt.datetime, now: dt.datetime) -> list[tuple[int, dt.datetime]]:
    """После срочного поста: автоматические посты, стоящие ближе промежутка, переносятся на новое умное время."""
    ch = cfg["channels"][channel]
    gap = dt.timedelta(minutes=int(rules(ch)["gap"]))
    moved = []
    for m in store.scheduled(db, channel):
        t = dt.datetime.fromisoformat(m["scheduled_at"])
        if m["locked"] or abs(t - at) >= gap:
            continue
        st = smart_time(db, cfg, channel, m["rubric"], max(now, at), exclude=m["id"])
        if st:
            store.update(db, m["id"], scheduled_at=st[0].isoformat())
            moved.append((m["id"], st[0]))
    return moved


STOCK_DAYS = 30
STOCK_AHEAD = dt.timedelta(minutes=90)


def fill_from_stock(db, cfg: dict, channel: str, now: dt.datetime) -> list[int]:
    """Пустой слот рубрики в ближайшие 90 минут → берём из 📦 запаса материал этой рубрики (старые первыми)."""
    ch = cfg["channels"][channel]
    pool = [m for m in store.stock(db, channel)
            if dt.datetime.fromisoformat(m["created_at"]) >= now - dt.timedelta(days=STOCK_DAYS)]
    if not pool:
        return []
    used: list[int] = []
    for t, s in grid(ch, now.date()):
        if s["kind"] == "ad" or not (now + LEAD <= t <= now + STOCK_AHEAD):
            continue
        if not is_free(ch, t, occupied(db, channel, now)) or blocked(db, channel, t):
            continue
        wanted = [s.get("rubric")] + list(s.get("fallback", []))
        pick = next((m for r in wanted for m in pool if m["rubric"] == r and m["id"] not in used and allowed(ch, t, r)), None)
        if pick:
            store.update(db, pick["id"], status="queued", scheduled_at=t.isoformat(), stock=0)
            used.append(pick["id"])
    return used


def fmt(t: dt.datetime, now: dt.datetime) -> str:
    if t.date() == now.date():
        return f"сегодня {t:%H:%M}"
    if t.date() == now.date() + dt.timedelta(days=1):
        return f"завтра {t:%H:%M}"
    return f"{t:%d.%m %H:%M}"


def short(text: str, n: int = 40) -> str:
    first = next((ln.strip() for ln in (text or "").splitlines() if ln.strip()), "")
    return (first[:n] + "…") if len(first) > n else (first or "(медиа)")


def day_view(db, cfg: dict, channel: str, now: dt.datetime) -> str:
    """План дня канала: что вышло, что запланировано (точное время), какие слоты сетки пустые."""
    ch = cfg["channels"][channel]
    day = now.date()
    lines = []
    done = db.execute("SELECT p.slot, p.status, m.rubric, m.text FROM publications p LEFT JOIN materials m ON m.id=p.material_id "
                      "WHERE p.channel=? AND p.slot_date=? ORDER BY p.at", (channel, day.isoformat())).fetchall()
    items = [((r["slot"] or "сейчас"), f"{'✔️' if r['status'] == 'done' else '❌'} {r['slot'] or '🆘'}  {r['rubric'] or '—'} — {short(r['text'])}")
             for r in done]
    sched = [m for m in store.scheduled(db, channel)]
    today = [m for m in sched if dt.datetime.fromisoformat(m["scheduled_at"]).date() == day]
    busy = [dt.datetime.fromisoformat(m["scheduled_at"]) for m in today] + store.pulse_since(db, channel, now - dt.timedelta(hours=18))
    for m in today:
        t = dt.datetime.fromisoformat(m["scheduled_at"])
        items.append((f"{t:%H:%M}", f"⏳ {t:%H:%M}  {m['rubric']} — {short(m['text'])}{' 🔒' if m['locked'] else ''}"))
    empty = 0
    for t, s in grid(ch, day):
        if s["kind"] == "ad" or t < now or not is_free(ch, t, busy):
            continue
        empty += 1
        items.append((f"{t:%H:%M}", f"⚠️ {t:%H:%M}  {s['rubric']} — нет материала"))
    from . import namaz
    items += namaz.today_lines(db, channel, day)
    from . import morning
    items += morning.today_lines(db, channel, day)
    items.sort(key=lambda x: x[0])
    later = len(sched) - len(today)
    st = store.stock(db, channel)
    if st:
        by: dict[str, int] = {}
        for m in st:
            by[m["rubric"]] = by.get(m["rubric"], 0) + 1
        items.append(("99", ""))
        items.append(("99:1", "📦 В запасе: " + ", ".join(f"{r} {n}" for r, n in by.items())))
    head = f"📅 {ch['title']} — {day:%d.%m}"
    tail = []
    if empty:
        tail.append(f"⚠️ Пустых слотов впереди: {empty} — бросайте посты боту.")
    if later:
        tail.append(f"📦 Запланировано на следующие дни: {later}")
    return "\n".join([head] + [i[1] for i in items] + ([""] + tail if tail else []))
