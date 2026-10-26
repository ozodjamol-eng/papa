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


def occupied(db, channel: str, now: dt.datetime, exclude: int | None = None, ch: dict | None = None,
             grid_posts: bool = True) -> list[dt.datetime]:
    """Занятые моменты. grid_posts=False (часовая сетка): посты сетки не мешают рекламе — сдвигаются сами (+10 мин)."""
    from . import namaz
    skip = not grid_posts and ch is not None and hourly(ch) is not None
    out = [dt.datetime.fromisoformat(m["scheduled_at"]) for m in store.scheduled(db, channel)
           if m["id"] != exclude and not (skip and is_grid_post(m))]
    from . import morning
    since = now - dt.timedelta(hours=3)
    from . import extras
    return (out + store.pulse_since(db, channel, since) + namaz.busy(db, channel, since) + morning.busy(db, channel, since)
            + extras.busy(db, channel, since))


def blocked(db, channel: str, t: dt.datetime) -> bool:
    """Тихое окно Жумы (и другие запреты модуля намаза)."""
    from . import namaz
    return namaz.locked(db, channel, t)


def is_free(ch: dict, t: dt.datetime, busy: list[dt.datetime]) -> bool:
    gap = dt.timedelta(minutes=int(rules(ch)["gap"]))
    return all(abs(t - b) >= gap for b in busy)


# ---------- ⏱ Часовая сетка (25.10 владелец) ----------
# Посты из рубрик — по одному в час, ровно в :00. Протоколы (утро, намоз, погода, дайджест, Якуний пост) и реклама —
# вне сетки, по своему времени. Срочный 🆘 — сразу. Совпало (реклама/срочный/протокол рядом) — плановый выходит
# через `after` минут после него (по умолчанию 10), остальные часы сетки НЕ сдвигаются.

HOURLY_DEFAULT = {"from": "07:00", "to": "22:00", "after": 10}


def hourly(ch: dict) -> dict | None:
    o = ch.get("hourly")
    if not o or o.get("enabled") is False:
        return None
    return {**HOURLY_DEFAULT, **o}


def is_ad_rubric(rubric: str | None) -> bool:
    return (rubric or "").lower().startswith("реклама")


def is_grid_post(m) -> bool:
    """Пост сетки: обычный пост из рубрики — не срочный и не реклама."""
    return not m["urgent"] and not is_ad_rubric(m["rubric"])


def hour_slots(ch: dict, day: dt.date) -> list[dt.datetime]:
    o = hourly(ch) or HOURLY_DEFAULT
    a, b = hm(o["from"]).hour, hm(o["to"]).hour
    return [plan.slot_time(day, f"{h:02d}:00") for h in range(a, b + 1)]


def hour_taken(db, channel: str, t: dt.datetime, exclude: int | None = None) -> bool:
    """Час уже занят постом сетки (в т.ч. сдвинутым на :10 после рекламы)."""
    h0 = t.astimezone(plan.TZ).replace(minute=0, second=0, microsecond=0)
    for m in store.scheduled(db, channel):
        if m["id"] == exclude or not is_grid_post(m):
            continue
        x = dt.datetime.fromisoformat(m["scheduled_at"]).astimezone(plan.TZ)
        if h0 <= x < h0 + dt.timedelta(hours=1):
            return True
    return False


def free_hours(db, ch: dict, channel: str, rubric: str | None, now: dt.datetime, day: dt.date,
               exclude: int | None = None, until: dt.datetime | None = None) -> list[dt.datetime]:
    return [t for t in hour_slots(ch, day)
            if t >= now + LEAD and (until is None or t < until) and allowed(ch, t, rubric)
            and not blocked(db, channel, t) and not hour_taken(db, channel, t, exclude)]


def free_at(db, cfg: dict, channel: str, t: dt.datetime, rubric: str | None, now: dt.datetime,
            exclude: int | None = None) -> bool:
    """Можно ли поставить пост на это время (промежуток / час сетки)."""
    ch = cfg["channels"][channel]
    if hourly(ch):
        if is_ad_rubric(rubric):                 # реклама — своё время; пост сетки сам уступит (+10 мин)
            return is_free(ch, t, occupied(db, channel, now, exclude, ch=ch, grid_posts=False))
        return not hour_taken(db, channel, t, exclude)
    return is_free(ch, t, occupied(db, channel, now, exclude))


def collision_defer(db, cfg: dict, channel: str, m, now: dt.datetime) -> dt.datetime | None:
    """Пост сетки наступил, а за последние `after` минут вышел другой пост (реклама, срочный, протокол, ручной) —
    ждём: новое время = тот пост + after. Сдвигается только этот пост, сетка остаётся."""
    ch = cfg["channels"][channel]
    o = hourly(ch)
    if not o or not is_grid_post(m):
        return None
    after = dt.timedelta(minutes=int(o["after"]))
    recent = [p.astimezone(plan.TZ) for p in store.pulse_since(db, channel, now - after) if p <= now]
    if not recent:
        return None
    t = max(recent) + after
    return t if t > now else None


def grid(ch: dict, day: dt.date) -> list[tuple[dt.datetime, dict]]:
    return [(plan.slot_time(day, s["t"]), s) for s in plan.day_slots(ch, day) if s["kind"] in ("content", "music", "ad")]


def ttl(ch: dict, rubric: str | None) -> int:
    r = rules(ch)
    return 0 if rubric in r["fresh_rubrics"] else int(r["ttl_days"])


def smart_time(db, cfg: dict, channel: str, rubric: str | None, now: dt.datetime,
               exclude: int | None = None) -> tuple[dt.datetime, str] | None:
    """Лучшее время: слот своей рубрики → слот, где рубрика запасная → (на следующий день то же) → ближайшее свободное."""
    ch = cfg["channels"][channel]
    if hourly(ch) and not is_ad_rubric(rubric):
        for d in range(max(ttl(ch, rubric), 1) + 1):
            hrs = free_hours(db, ch, channel, rubric, now, now.date() + dt.timedelta(days=d), exclude)
            if hrs:
                return hrs[0], "часовая сетка"
        return None
    busy = occupied(db, channel, now, exclude, ch=ch, grid_posts=False)
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
    if hourly(ch) and not is_ad_rubric(rubric):
        hrs = [t for d in (0, 1) for t in free_hours(db, ch, channel, rubric, now, now.date() + dt.timedelta(days=d), exclude)]
        return hrs[:n]
    busy = occupied(db, channel, now, exclude, ch=ch, grid_posts=False)
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


def policy_hits(cfg: dict, body: str) -> list[str]:
    """Какие группы политики каналов (docs/CHANNELS.md) есть в тексте: politics / crime / showbiz."""
    import re
    from . import text as T
    groups = (cfg.get("policy") or {}).get("groups") or {}
    low, _ = T.translit.auto(T.strip_sources(body or ""))
    low = low.lower()
    words = re.findall(r"[\wʼ'‘’-]+", low)
    hits = []
    for g, kws in groups.items():
        for kw in kws:
            kw = kw.lower()
            if (" " in kw and kw in low) or (" " not in kw and any(w.startswith(kw) for w in words)):
                hits.append(g)
                break
    return hits


def policy_note(cfg: dict, channel: str, body: str) -> str:
    """Предупреждение в карточку, если пост похож на запрещённое для канала. Не запрет — решает владелец."""
    rules = (cfg.get("channels", {}).get(channel) or {}).get("policy") or {}
    if not rules:
        return ""
    labels = (cfg.get("policy") or {}).get("labels") or {}
    names = {c: (ch.get("title") or c) for c, ch in cfg.get("channels", {}).items()}
    out = []
    for g in policy_hits(cfg, body):
        if g not in rules:
            continue
        to = rules[g]
        tip = f" Подходит: {names.get(to, to)} — бросьте в его пульт." if to else " Лучше не публиковать."
        out.append(f"⚠️ Похоже на «{labels.get(g, g)}» — по политике это не для {names.get(channel, channel)}.{tip}")
    return "\n".join(out)


def _first_rubric(ch: dict) -> str:
    return next(s["rubric"] for s in ch["slots"] if s["kind"] == "content")


def shift_after_urgent(db, cfg: dict, channel: str, at: dt.datetime, now: dt.datetime) -> list[tuple[int, dt.datetime]]:
    """После срочного поста: автоматические посты, стоящие ближе промежутка, переносятся на новое умное время."""
    ch = cfg["channels"][channel]
    if hourly(ch):                                   # часовая сетка не сдвигается: совпавший пост уступит сам (+10 мин)
        return []
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


def waits_text(cfg: dict, m) -> bool:
    """18.10 (владелец): в канале с stock_needs_text (PaparazziUZ — шоу-бизнес, чувствительные поводы) материал
    из запаса без текста сам не выходит — ждёт текста владельца."""
    ch = cfg["channels"].get(m["channel"]) or {}
    return bool(ch.get("stock_needs_text")) and not (m["text"] or "").strip()


SKLAD_LEAD = dt.timedelta(minutes=30)     # 26.10 владелец: пост склада виден в пульте с 🗑 не меньше чем за 30 мин


def _nrm(s) -> str:
    import re
    return re.sub(r"[\W_]+", "", str(s or "")).casefold()


def sklad_rubric(ch: dict, source: str | None, n: int = 0) -> str | None:
    """Пост переслан из склада владельца (config: sklad = {название склада: рубрика или [рубрики по очереди]})
    → рубрика (n — номер поста этого склада, для очереди); иначе None."""
    for name, rub in (ch.get("sklad") or {}).items():
        if source and _nrm(source) == _nrm(name):
            return rub[n % len(rub)] if isinstance(rub, list) else rub
    return None


def is_sklad(ch: dict, m) -> bool:
    """Выходит сам, с вето 🗑: склад владельца или канал, выбранный владельцем (auto=1)."""
    keys = m.keys()
    return bool(("auto" in keys and m["auto"]) or sklad_rubric(ch, m["source"] if "source" in keys else None))


AUTO_TTL = dt.timedelta(hours=12)        # пост выбранного чужого канала (часто новость) ждёт в запасе не дольше


def _stale(ch: dict, m, now: dt.datetime) -> bool:
    if not ("auto" in m.keys() and m["auto"]) or sklad_rubric(ch, m["source"]):
        return False
    return dt.datetime.fromisoformat(m["created_at"]) < now - AUTO_TTL


def _fits(ch: dict, m, t: dt.datetime, now: dt.datetime) -> bool:
    return not is_sklad(ch, m) or t >= now + SKLAD_LEAD


def fill_from_stock(db, cfg: dict, channel: str, now: dt.datetime) -> list[int]:
    """Пустой слот рубрики в ближайшие 90 минут → берём из 📦 запаса материал этой рубрики (старые первыми)."""
    ch = cfg["channels"][channel]
    pool = [m for m in store.stock(db, channel)
            if dt.datetime.fromisoformat(m["created_at"]) >= now - dt.timedelta(days=STOCK_DAYS)
            and not waits_text(cfg, m) and not _stale(ch, m, now)]
    if not pool:
        return []
    used: list[int] = []
    if hourly(ch):                                   # сетка без рубрик: в пустой час — самый старый материал запаса
        for t in free_hours(db, ch, channel, None, now, now.date(), until=now + STOCK_AHEAD + dt.timedelta(seconds=1)):
            pick = next((m for m in pool if m["id"] not in used and allowed(ch, t, m["rubric"]) and _fits(ch, m, t, now)), None)
            if pick:
                store.update(db, pick["id"], status="queued", scheduled_at=t.isoformat(), stock=0)
                used.append(pick["id"])
        return used
    for t, s in grid(ch, now.date()):
        if s["kind"] == "ad" or not (now + LEAD <= t <= now + STOCK_AHEAD):
            continue
        if not is_free(ch, t, occupied(db, channel, now)) or blocked(db, channel, t):
            continue
        wanted = [s.get("rubric")] + list(s.get("fallback", []))
        pick = next((m for r in wanted for m in pool if m["rubric"] == r and m["id"] not in used and allowed(ch, t, r)
                     and _fits(ch, m, t, now)), None)
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
    if hourly(ch):
        for t in free_hours(db, ch, channel, None, now, day):
            empty += 1
            items.append((f"{t:%H:%M}", f"⚠️ {t:%H:%M}  час пустой — нет поста"))
    for t, s in ([] if hourly(ch) else grid(ch, day)):
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


# ---------- карточка поста как в GENPLAN 5 (решение 17.10: пульты Давры и PaparazziUZ = пульт Хўжаобода) ----------

NOW_WARNING_GAP = 15            # GENPLAN 5: «🚀 Сейчас» спрашивает подтверждение, если прошлый пост был < 15 мин назад
OPTIONS_SPACING = 45            # GENPLAN 5: «Другие варианты» — не ближе 45 минут друг к другу


def last_post(db, channel: str, now: dt.datetime) -> dt.datetime | None:
    """Последний реальный пост канала (наш и ручной — «пульс»)."""
    r = db.execute("SELECT MAX(at) FROM pulse WHERE channel=? AND at<=?", (channel, now.isoformat())).fetchone()
    return dt.datetime.fromisoformat(r[0]).astimezone(plan.TZ) if r and r[0] else None


def next_mandatory(db, cfg: dict, channel: str, now: dt.datetime) -> tuple[dt.datetime, str] | None:
    """Ближайший обязательный пост впереди: намоз, утренний блок («Хайрли тонг», «Бугун — … куни»)."""
    from . import morning, namaz
    out: list[tuple[dt.datetime, str]] = []
    for r in db.execute("SELECT at, key FROM namaz_posts WHERE channel=? AND status='pending' AND at>?",
                        (channel, now.isoformat())).fetchall():
        out.append((dt.datetime.fromisoformat(r[0]), "намоз " + namaz.LABEL.get(r[1], r[1])))
    for r in db.execute("SELECT at, key FROM fixed_posts WHERE channel=? AND status='pending' AND at>?",
                        (channel, now.isoformat())).fetchall():
        out.append((dt.datetime.fromisoformat(r[0]), morning.TITLE.get(r[1], r[1])))
    mo = cfg["channels"][channel].get("morning") or {}
    for key, title in (("greeting", "Хайрли тонг"), ("day_post", "Бугун — … куни")):
        if mo.get(key):                                     # утро ещё не подготовлено — берём время из настроек
            for d in (0, 1):
                t = morning.resolve(db, mo[key], now.date() + dt.timedelta(days=d))   # 20.10: «bomdod-45|05:00» тоже (падало ValueError)
                if t > now and not any(abs((x - t).total_seconds()) < 60 for x, _ in out):
                    out.append((t, title))
                    break
    out = [(t.astimezone(plan.TZ), lbl) for t, lbl in out]
    return min(out, key=lambda x: x[0]) if out else None


def _part(t: dt.datetime) -> str:
    h = t.hour
    return "утреннее" if 5 <= h < 11 else "дневное" if h < 17 else "вечернее" if h < 22 else "ночное"


def context_label(db, cfg: dict, channel: str, t: dt.datetime, exclude: int | None = None) -> str:
    """Как в GENPLAN 5: почему это время — между какими постами оно стоит."""
    busy = sorted(b.astimezone(plan.TZ) for b in occupied(db, channel, t - dt.timedelta(hours=12), exclude))
    prev = [b for b in busy if b < t and t - b <= dt.timedelta(hours=3)]
    nxt = [b for b in busy if b > t and b - t <= dt.timedelta(hours=3)]
    if prev and nxt:
        return f"между постами {prev[-1]:%H:%M} и {nxt[0]:%H:%M}"
    if nxt:
        return f"до поста {nxt[0]:%H:%M}"
    if prev:
        return f"после поста {prev[-1]:%H:%M}"
    return f"свободное {_part(t)} окно"


PARTS = (("🌅", "Утро", "07:00", "11:00"), ("☀️", "День", "11:00", "16:00"), ("🌙", "Вечер", "16:00", "22:00"))   # 17.10 владелец


def part_time(db, cfg: dict, channel: str, rubric: str | None, now: dt.datetime, lo: str, hi: str,
              exclude: int | None = None, days: int = 7) -> tuple[dt.datetime, int] | None:
    """Кнопки «Утро / День / Вечер»: лучшее свободное время в этом окне. Окно сегодня прошло или занято —
    то же окно завтра и дальше (пост не пропадает). Возвращает (время, сколько постов уже стоит в этом окне в тот день)."""
    for d in range(days + 1):
        day = now.date() + dt.timedelta(days=d)
        a, b = plan.slot_time(day, lo), plan.slot_time(day, hi)
        t = day_time(db, cfg, channel, rubric, max(now, a - LEAD), day, exclude, until=b)
        if t:
            n = sum(1 for x in occupied(db, channel, a, exclude) if a <= x.astimezone(plan.TZ) < b)
            return t, n
    return None


def day_time(db, cfg: dict, channel: str, rubric: str | None, now: dt.datetime, day: dt.date,
             exclude: int | None = None, until: dt.datetime | None = None) -> dt.datetime | None:
    """Лучшее время именно в этот день (кнопки «📅 Сегодня» / «🌅 Завтра»): слот своей рубрики →
    слот, где рубрика запасная → ближайшее свободное. Окно, промежуток, музыка, Жума — соблюдаются."""
    ch = cfg["channels"][channel]
    if hourly(ch) and not is_ad_rubric(rubric):
        hrs = free_hours(db, ch, channel, rubric, now, day, exclude, until)
        return hrs[0] if hrs else None
    busy = occupied(db, channel, now, exclude, ch=ch, grid_posts=False)
    ok = lambda t: (t >= now + LEAD and (until is None or t < until) and allowed(ch, t, rubric)  # noqa: E731
                    and is_free(ch, t, busy) and not blocked(db, channel, t))
    slots = [(t, s) for t, s in grid(ch, day) if s["kind"] != "ad" and ok(t)]
    for t, s in slots:
        if s.get("rubric") == rubric:
            return t
    for t, s in slots:
        if rubric in s.get("fallback", []):
            return t
    for h in range(0, 24):
        for mnt in (0, 30):
            t = plan.slot_time(day, f"{h:02d}:{mnt:02d}")
            if ok(t):
                return t
    return None


def options(db, cfg: dict, channel: str, rubric: str | None, now: dt.datetime, n: int = 4,
            exclude: int | None = None) -> list[tuple[dt.datetime, str]]:
    """«🗓 Другие варианты» как в GENPLAN 5: несколько разных времён (не ближе 45 мин), у каждого — причина."""
    out: list[dt.datetime] = []
    for t in other_times(db, cfg, channel, rubric, now, n=40, exclude=exclude):
        if all(abs(t - x) >= dt.timedelta(minutes=OPTIONS_SPACING) for x in out):
            out.append(t)
            if len(out) >= n:
                break
    return [(t, context_label(db, cfg, channel, t, exclude)) for t in out]
