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
import re

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
            + extras.busy(db, channel, since) + digest_busy(ch, now))


def digest_busy(ch: dict | None, now: dt.datetime) -> list[dt.datetime]:
    """30.10 сверка №9: Кечки дайжест — протокол; умное время рекламы не ставит её вплотную к нему (как к намазу)."""
    dg = (ch or {}).get("digest") or {}
    if not dg.get("live"):
        return []
    return [plan.slot_time(now.date() + dt.timedelta(days=d), dg.get("at", "20:30")) for d in (0, 1)]


def blocked(db, channel: str, t: dt.datetime) -> bool:
    """Тихое окно Жумы (и другие запреты модуля намаза)."""
    from . import namaz
    return namaz.locked(db, channel, t)


def lock_end(db, channel: str, t: dt.datetime) -> dt.datetime | None:
    """30.10 аудит: t внутри тихого окна Жумы → время сразу после окна (конец + 1 мин), иначе None."""
    try:
        r = db.execute("SELECT end FROM namaz_locks WHERE channel=? AND start<=? AND end>=? ORDER BY end DESC LIMIT 1",
                       (channel, t.isoformat(), t.isoformat())).fetchone()
    except Exception:  # noqa: BLE001 — таблицы намаза может не быть
        return None
    if not r:
        return None
    return dt.datetime.fromisoformat(r[0]).astimezone(plan.TZ) + dt.timedelta(minutes=1)


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


def hour_wants(ch: dict, t: dt.datetime) -> list[str] | None:
    """30.10 владелец (режим дня по разведке): час сетки → рубрики по порядку (первая — главная, дальше запасные).
    config: [channels.<канал>.hour_rubrics] "10" = ["Ҳажвия", "Видео"]. Нет карты/часа — None (как раньше, любая рубрика)."""
    m = ch.get("hour_rubrics")
    if not m:
        return None
    w = m.get(f"{t.astimezone(plan.TZ).hour:02d}")
    if w is None:
        return None
    return [w] if isinstance(w, str) else list(w)


def minbar_hour(ch: dict, t: dt.datetime, rubric: str | None) -> bool:
    """01.11 разбор: час, где главная рубрика — «Муфтий минбари» (22:00), — только для Муфтия. Посты Маънавият
    вставали туда при выборе рубрики в карточке (Маънавият — запасная рубрика часа) раньше, чем запас ставил урок,
    и в КАТТА ДАВРА урок Муфтия не вышел. Запасная рубрика берётся в этот час только самим запасом (fill_from_stock)."""
    w = hour_wants(ch, t) or []
    return bool(w) and w[0] == "Муфтий минбари" and rubric != "Муфтий минбари"


def is_ad_rubric(rubric: str | None) -> bool:
    return (rubric or "").lower().startswith("реклама")


def is_grid_post(m) -> bool:
    """Пост сетки: обычный пост из рубрики — не срочный, не реклама и не твёрдый слот протокола (09.11)."""
    return not m["urgent"] and not is_ad_rubric(m["rubric"]) and not ("fixed" in m.keys() and m["fixed"])


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


def is_minbar_hour(ch: dict, t: dt.datetime) -> bool:
    """01.11 владелец, ТВЁРДЫЙ ЗАКОН: 22:00 — последний пост дня, урок Муфтия в обоих каналах. Час, где главная рубрика
    «Муфтий минбари», закреплён за Муфтием: другие посты (Маънавият и пр.) туда днём не ставятся."""
    w = hour_wants(ch, t)
    return bool(w) and w[0] == MINBAR


def free_hours(db, ch: dict, channel: str, rubric: str | None, now: dt.datetime, day: dt.date,
               exclude: int | None = None, until: dt.datetime | None = None,
               minbar: bool = False) -> list[dt.datetime]:
    """minbar=True — только для запаса/обзоров: они сами решают, кто идёт в час Муфтия."""
    return [t for t in hour_slots(ch, day)
            if t >= now + LEAD and (until is None or t < until) and allowed(ch, t, rubric)
            and (minbar or rubric == MINBAR or not is_minbar_hour(ch, t))
            and not blocked(db, channel, t) and not hour_taken(db, channel, t, exclude)
            and not _rezhim_off(db, ch, channel, t)]


def _rezhim_off(db, ch: dict, channel: str, t: dt.datetime) -> bool:
    """📅 06.11 режим дня: час выключен владельцем галочкой — запас/якорь/умное время его не занимают."""
    if not ch.get("rezhim"):
        return False
    from . import rezhim
    return rezhim.is_off(db, channel, t)


def free_at(db, cfg: dict, channel: str, t: dt.datetime, rubric: str | None, now: dt.datetime,
            exclude: int | None = None) -> bool:
    """Можно ли поставить пост на это время (промежуток / час сетки)."""
    ch = cfg["channels"][channel]
    if hourly(ch):
        if is_ad_rubric(rubric):                 # реклама — своё время; пост сетки сам уступит (+10 мин)
            return is_free(ch, t, occupied(db, channel, now, exclude, ch=ch, grid_posts=False))
        return not hour_taken(db, channel, t, exclude)
    return is_free(ch, t, occupied(db, channel, now, exclude))


def ad_hold(db, cfg: dict, channel: str, now: dt.datetime) -> dt.datetime | None:
    """30.10 владелец: вышедшая реклама держится наверху не меньше `after` минут (10) — обещание клиенту.
    Ничего (даже срочный) не выходит раньше. Возвращает время, до которого ждать, или None."""
    ch = cfg["channels"][channel]
    after = dt.timedelta(minutes=int((hourly(ch) or HOURLY_DEFAULT)["after"]))
    rows = db.execute("SELECT at FROM pulse WHERE channel=? AND source='ad' AND at>=?",
                      (channel, (now - after).isoformat())).fetchall()
    ads = [dt.datetime.fromisoformat(r[0]).astimezone(plan.TZ) for r in rows]
    ads = [a for a in ads if a <= now]
    if not ads:
        return None
    t = max(ads) + after
    return t if t > now else None


AD_CLOSE_LOOK = dt.timedelta(minutes=120)  # окно поиска рекламы: час сетки + тихое окно Жумы (55 мин)
AD_CLOSE_SKIP = dt.timedelta(minutes=10)   # пост сетки и так выйдет в ближайшие 10 мин — ничего не тянем


def ad_closer(db, cfg: dict, channel: str, now: dt.datetime) -> int | None:
    """30.10 владелец, ПРОТОКОЛ «реклама → закрывающий пост»: вышла реклама, прошло `after` (10) мин,
    после неё ничего не вышло, а пост сетки ещё не скоро — ставим пост на сейчас.
    Берём ближайший запланированный пост сетки (не 🔒, он уже прошёл вето 🗑); нет — самый старый из 📦 запаса
    (не склад — у склада вето за 30 мин). Возвращает id поставленного поста или None."""
    ch = cfg["channels"][channel]
    o = hourly(ch)
    if not o:
        return None
    after = dt.timedelta(minutes=int(o["after"]))
    rows = db.execute("SELECT at, source FROM pulse WHERE channel=? AND at>=?",
                      (channel, (now - AD_CLOSE_LOOK).isoformat())).fetchall()
    pulses = sorted((dt.datetime.fromisoformat(r[0]).astimezone(plan.TZ), r[1]) for r in rows)
    pulses = [p for p in pulses if p[0] <= now]
    ads = [t for t, s in pulses if s == "ad"]
    if not ads:
        return None
    last_ad = max(ads)
    if now < last_ad + after:                                  # реклама ещё держится свои 10 мин
        return None
    if any(t > last_ad and s != "ad" for t, s in pulses):      # уже закрыта (пост, протокол, дайджест)
        return None
    if not (hm(o["from"]) <= now.time() <= (dt.datetime.combine(now.date(), hm(o["to"])) + dt.timedelta(minutes=59)).time()):
        return None                                            # ночью не закрываем
    if blocked(db, channel, now):                              # тихое окно Жумы — закроет первый пост после окна
        return None
    soon = (now + AD_CLOSE_SKIP).isoformat()
    try:                                                       # намаз-напоминание сам закроет рекламу через минуты
        if db.execute("SELECT 1 FROM namaz_posts WHERE channel=? AND status='pending' AND at>? AND at<=?",
                      (channel, now.isoformat(), soon)).fetchone():
            return None
    except Exception:  # noqa: BLE001 — таблицы намаза может не быть
        pass
    dg = ch.get("digest") or {}
    if dg.get("live"):                                         # Кечки дайжест в ближайшие 10 мин — он и закроет
        d_at = plan.slot_time(now.date(), dg.get("at", "20:30"))
        flag = f"digest_pub_{now.date()}" if channel == "xojaobod" else f"digest_pub_{channel}_{now.date()}"
        if d_at - AD_CLOSE_SKIP <= now < d_at + dt.timedelta(minutes=6) and not store.kv_get(db, flag):   # дайджест ждёт ролик до +5
            return None
    upcoming = [m for m in store.scheduled(db, channel) if dt.datetime.fromisoformat(m["scheduled_at"]) > now]
    if any(dt.datetime.fromisoformat(m["scheduled_at"]) <= now + AD_CLOSE_SKIP for m in upcoming):
        return None                                            # что-то и так выйдет через пару минут
    if any(dt.datetime.fromisoformat(m["scheduled_at"]) <= now for m in store.scheduled(db, channel)):
        return None                                            # уже стоит на сейчас (ждёт прохода)
    pick = next((m for m in upcoming if is_grid_post(m) and not m["locked"] and not is_sklad(ch, m)
                 and m["rubric"] != MINBAR and dt.datetime.fromisoformat(m["scheduled_at"]).date() == now.date()), None)
    room = day_room(db, cfg, channel, now)                     # 30.10 сверка №10: лимит дня — запас не трогаем
    if pick is None and (room is None or room > 0):
        pool = [m for m in store.stock(db, channel)
                if dt.datetime.fromisoformat(m["created_at"]) >= now - dt.timedelta(days=STOCK_DAYS)
                and not waits_text(cfg, m) and not _stale(ch, m, now) and not is_sklad(ch, m)
                and not is_ad_rubric(m["rubric"]) and not repeat_block(db, channel, m, now)
                and not (m["auto"] and music_no_video(m)) and m["rubric"] != MINBAR]
        pick = pool[0] if pool else None
    if pick is None:   # 11.11 владелец: «через 10 минут должен быть любой пост» — реклама висела 07:30→09:00, потому что
        # в очереди был только складской пост (ФОЙДАЛИК). Последний шанс: ближайший пост сетки сегодня, склад тоже
        # (его превью с 🗑 уже ушло при постановке); Муфтий (22:00) — никогда. Откат: удалить этот блок.
        pick = next((m for m in upcoming if is_grid_post(m) and not m["locked"] and m["rubric"] != MINBAR
                     and dt.datetime.fromisoformat(m["scheduled_at"]).date() == now.date()), None)
    if pick is None:
        return None
    store.update(db, pick["id"], status="queued", scheduled_at=now.isoformat(), stock=0)
    return pick["id"]


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
    if t <= now:
        return None
    return lock_end(db, channel, t) or t                # 30.10 аудит: не внутрь тихого окна Жумы


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
        days = [[t for t in free_hours(db, ch, channel, rubric, now, now.date() + dt.timedelta(days=d), exclude)
                 if not minbar_hour(ch, t, rubric)] for d in range(max(ttl(ch, rubric), 1) + 1)]
        if ch.get("hour_rubrics") and rubric:        # 30.10: сначала час своей рубрики (главной, потом запасной)
            for rank in (0, 1):
                for hrs in days:
                    for t in hrs:
                        w = hour_wants(ch, t) or []
                        if rubric in w and (w.index(rubric) == 0) == (rank == 0):
                            return t, f"час рубрики «{w[0]}»"
        for hrs in days:
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
        hrs = [t for d in (0, 1) for t in free_hours(db, ch, channel, rubric, now, now.date() + dt.timedelta(days=d), exclude)
               if not minbar_hour(ch, t, rubric)]
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


NEWS_RUBRICS = {"Янгиликлар", "Эрталабки янгиликлар", "Тушки янгиликлар", "Кечки янгиликлар", "Хўжаобод/Андижон"}   # 01.11: местные новости — тоже новости
NEWS_CODES = {"news", "local"}


# 01.11 владелец: «отныне новостную часть на всех трёх каналах не ведём». Новость узнаём и по тексту — агенты клали
# новости в склады направлений (пример: «ТАДБИРКОРЛАРГА СОЛИҚДАН ИМТИЁЗ» в «УЙДА БИЗНЕС»). Признаки — официоз,
# ведомства, «маълум қилди», «1 ноябрдан» и т.п. (кириллица и латиница). Шоу-бизнес PaparazziUZ это не задевает.
_MON = r"(?:январ|феврал|март|апрел|май|июн|июл|август|сентябр|октябр|ноябр|декабр|yanvar|fevral|mart|aprel|may|iyun|iyul|avgust|sentyabr|oktyabr|noyabr|dekabr)"
NEWS_TEXT = re.compile(
    r"(?<![\w'ʻ’])(?:расман|rasman|фармон|farmon|қарор\w*|qaror\w*|вазирлиг|vazirlig|ҳукумат|hukumat|ҳокимият|hokimiyat|"
    r"солиқ|soliq|имтиёз|imtiyoz|жарима|jarima|қонун|qonun|прокуратур|prokuratur|ИИВ|IIV|суд(?:и|га|да|нинг)?(?![\w'ʻ’])|sud(?:i|ga|da|ning)?(?![\w'ʻ’])|"
    r"маълум қил|ma[ʼ'ʻ’]?lum qil|хабар бер|xabar ber|хабар қилин|xabar qilin|эълон қил|e[ʼ'ʻ’]?lon qil|матбуот хизмат|matbuot xizmat|"
    r"тезкор|tezkor|янгилик|yangilik|#news|ЙТҲ|YTH|йўл.транспорт ҳодиса|yo[ʻ'’]l.transport hodisa|"
    r"\d{1,2}[- ]?" + _MON + r"\w*?(?:дан|гача|да|dan|gacha|da)(?![\w'ʻ’]))",
    re.I)


def looks_news(text: str | None) -> bool:
    return bool(NEWS_TEXT.search(text or ""))


def urgent_sklad(ch: dict, source: str | None) -> bool:
    """01.11 владелец: новости — только из канала «СРОЧНО НОВОСТИ», который он сам наполняет; каждый пост — один раз."""
    return bool(source) and any(_nrm(source) == _nrm(x) for x in (ch.get("urgent_sklad") or []))


def news_banned(cfg: dict, channel: str | None, rubric: str | None, source_code: str | None,
                text: str | None = None, source: str | None = None) -> bool:
    """Канал с no_news (01.11 — все три): материал агентов/складов из новостного источника, в новостной рубрике
    или с новостным текстом не выходит. Исключение — склад «СРОЧНО НОВОСТИ» владельца."""
    ch = (cfg.get("channels") or {}).get(channel or "") or {}
    if not ch.get("no_news") or urgent_sklad(ch, source) or (rubric or "") == "Муфтий минбари":
        return False
    return (source_code or "") in NEWS_CODES or (rubric or "") in NEWS_RUBRICS or (bool(ch.get("no_news_text", True)) and looks_news(text))


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


# 07.11 владелец переименовывает хабы KATTA BANK в «БАНК · …» — новое имя = прежний склад (как razvedka.hubs.TITLES)
BANK_TITLES = {"БАНК · КУЛГИ": "РАЗВЛЕКАТЕЛЬНО", "БАНК · ФОЙДАЛИ": "ФОЙДАЛИК", "БАНК · ОВҚАТ": "ФОЙДАЛИК ОВКАТ",
               "БАНК · МАЪНАВИЯТ": "МАЪНАВИЯТ", "БАНК · УЙ БИЗНЕСИ": "УЙДА БИЗНЕС", "БАНК · МОТИВАЦИЯ": "МОТИВАЦИЯ",
               "БАНК · МУСИҚА": "Jonlik ijrolar", "БАНК · ИБРАТ": "ИБРАТ", "БАНК · ТРЕНДЛАР": "ТРЕНДЛАР"}


def sklad_rubric(ch: dict, source: str | None, n: int = 0) -> str | None:
    """Пост переслан из склада владельца (config: sklad = {название склада: рубрика или [рубрики по очереди]})
    → рубрика (n — номер поста этого склада, для очереди); иначе None."""
    source = next((old for new, old in BANK_TITLES.items() if _nrm(source) == _nrm(new)), source) if source else source
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
    if not greet_ok(m["text"], t):                   # 06.11: «Хайрли тонг»/«Жума муборак» вечером — никогда
        return False
    return not is_sklad(ch, m) or t >= now + SKLAD_LEAD


def day_room(db, cfg: dict, channel: str, now: dt.datetime) -> int | None:
    """30.10 сверка №10 (решение 16.10): не больше `day_limit.max` (20) постов в день. count="all" (КАТТА ДАВРА, PaparazziUZ) —
    считаются все посты, утро тоже; count="grid" (Хўжаобод) — только обычные посты, протоколы и реклама вне 20.
    Считаем вышедшее сегодня + стоящее на сегодня. Возвращает, сколько ещё можно; None — лимита нет.
    Лимит закрывает только запас (📦/склад): пост, утверждённый владельцем, не блокируется."""
    lim = cfg["channels"][channel].get("day_limit")
    if not lim:
        return None
    a = plan.slot_time(now.date(), "00:00")
    b = a + dt.timedelta(days=1)
    scope = lim.get("count", "all")
    q = "SELECT COUNT(*) FROM pulse WHERE channel=? AND at>=? AND at<? AND at<=?"
    args = [channel, a.isoformat(), b.isoformat(), now.isoformat()]
    if scope == "grid":
        q += " AND source='bot'"
    n = db.execute(q, args).fetchone()[0]
    for m in store.scheduled(db, channel):
        t = dt.datetime.fromisoformat(m["scheduled_at"])
        if now < t < b and (scope == "all" or not is_ad_rubric(m["rubric"])):
            n += 1
    if scope == "all":
        from . import extras, morning, namaz
        for f in (namaz.busy, morning.busy, extras.busy):
            n += sum(1 for t in f(db, channel, now) if now < t < b)
    return int(lim.get("max", 20)) - n


# 🕰 06.11 разбор (владелец: «такие вещи он должен различать»): в 20:00 в Хўжаобод из запаса МАЪНАВИЯТ вышел
# «🕌 ЖУМА МУБОРАК…» с #ХАЙРЛИ_ТОНГ в начале — утреннее поздравление вечером. Текст, привязанный ко времени дня,
# выходит только в своё время; не подходит — ждёт в запасе своего часа (утро — утро, Жума — пятница до намаза).
GREET = {
    "morning": re.compile(r"хайрли[\s_]*тонг|тонги[\s_]*муборак|тонгингиз|xayrli[\s_]*tong|tongi[\s_]*muborak|tongingiz"),
    "juma": re.compile(r"жума\w*[\s_]*(?:айём\w*[\s_]*)?муборак|juma\w*[\s_]*(?:ayyom\w*[\s_]*)?muborak"),
    "night": re.compile(r"хайрли[\s_]*(?:тун|кеч)\b|тунингиз|xayrli[\s_]*(?:tun|kech)\b|tuningiz"),
}
GREET_MORNING_TO = dt.time(10, 0)     # утреннее поздравление — только утренний блок
GREET_JUMA_TO = dt.time(12, 0)        # «Жума муборак» — пятница до Жума-намаза (Пешин 12:45)
GREET_NIGHT_FROM = dt.time(22, 0)     # 20.10: прощание раньше 22:00 — канал «закрылся»


def greet_kind(text: str | None) -> str | None:
    s = str(text or "").casefold()
    for k in ("juma", "morning", "night"):
        if GREET[k].search(s):
            return k
    return None


def greet_ok(text: str | None, t: dt.datetime) -> bool:
    """Поздравление/прощание в тексте подходит к времени выхода t? Нет таких слов — подходит всегда."""
    k = greet_kind(text)
    if k is None:
        return True
    x = t.astimezone(plan.TZ)
    if k == "morning":
        return x.time() < GREET_MORNING_TO
    if k == "juma":
        return x.weekday() == 4 and x.time() < GREET_JUMA_TO
    return x.time() >= GREET_NIGHT_FROM


MINBAR = "Муфтий минбари"


def minbar_ok(m) -> bool:
    """30.10 владелец: в слот «Муфтий минбари» (22:00) — только уроки с минбара (#muftiy_minbari).
    Поздравления Муфтия (#tabrik, «Жума муборак») туда не берём: вечером это выглядит как утренний пост.
    Нет урока — час берёт запасную рубрику сетки (Маънавият)."""
    if m["rubric"] != MINBAR:
        return True
    n = _nrm(m["text"])
    src = _nrm(m["source"]) if "source" in m.keys() else ""
    # 01.11 разбор: в Хўжаобод в 22:03 вышел пост другого шайха (склад МАЪНАВИЯТ) с рубрикой Муфтия — Муфтий у нас один
    if src and "nuriddin" not in src and "нуриддин" not in n and "nuriddin" not in n:
        return False
    return "minbar" in n or "минбар" in n


def twin_taken(db, channel: str, m) -> bool:
    """30.10 владелец: посты Муфтия в КАТТА ДАВРА и Хўжаобод Сити 24 должны отличаться —
    материал, который другой канал уже поставил или выпустил, этому каналу не берём.
    31.10 разбор: один и тот же урок вышел в Хўжаобод 30.10 и 31.10 (копии одного поста в запасе) —
    теперь урок с тем же отпечатком не берём и в СВОЁМ канале, если он уже стоит или вышел."""
    if m["rubric"] != MINBAR:
        return False
    if m["fp"] and db.execute("SELECT 1 FROM materials WHERE fp=? AND id<>? AND status IN ('queued','published') LIMIT 1",
                              (m["fp"], m["id"])).fetchone():
        return True
    # 31.10 аудит: Муфтий выкладывает тот же урок заново (другое видео — другой fp): «Одобимиз – қалқонимиз» три дня
    # выходил Якуний постом и снова лежал в запасе. Сверяем и по тексту — с вышедшими/стоящими уроками и Якуний постами.
    key = _nrm(m["text"])[:120]
    if len(key) < 20:
        return False
    rows = db.execute("SELECT text FROM materials WHERE id<>? AND (rubric=? AND status IN ('queued','published') "
                      "OR rubric='Якуний пост')", (m["id"], MINBAR)).fetchall()
    finals = [store.kv_get(db, f"final_{c}", "") for c in ("xojaobod", "davra", "paparazzi")]
    import json as _json
    texts = [r[0] for r in rows] + [(_json.loads(f).get("text") if f else "") for f in finals]
    return any(_nrm(t)[:120] == key for t in texts if t)


def twin_today(db, channel: str, m, now: dt.datetime) -> bool:
    """31.10 аудит: один и тот же пост склада вышел в обоих каналах за день («ФАРҒОНАЛИК МАҲКАМ ТОҒАМДАН…»:
    Хўжаобод 08:00, КАТТА ДАВРА 19:00). Материал запаса, который другой канал поставил/выпустил за сутки, не берём."""
    if not m["fp"]:
        return False
    since = (now - dt.timedelta(days=1)).isoformat()
    return db.execute("SELECT 1 FROM materials WHERE fp=? AND channel<>? AND status IN ('queued','published') "
                      "AND COALESCE(scheduled_at, created_at)>=? LIMIT 1", (m["fp"], channel, since)).fetchone() is not None


# 07.11 владелец: «бот кидает почти каждый день одно и то же… договаривались 15–20 дней или месяц не бросать».
# Причина: склады отсекали повтор только по номеру сообщения, а одно и то же видео лежит в складах под разными номерами.
# Теперь по СОДЕРЖИМОМУ (отпечаток видео/фото, длинный текст): в своём канале — не чаще раза в 30 дней;
# то, что владелец убрал (🗑 в пульте или «Удалить из канала»), — больше не берём никогда. Урок Муфтия — по своим правилам.
REPEAT_BLOCK_DAYS = 30
# 07.11 владелец: «нахрена он картинку бросает? это даже не клип» — музыка (песня, живое исполнение, клип, ретро)
# из складов/источников выходит сама только ВИДЕО. Фото с подписью «ЖОНЛИ ИЖРО» — не музыка, сам не выходит.
MUSIC_RUBRICS = {"Мусиқа", "Қўшиқ", "Жонли ижро", "Ретро хотира", "Кун қўшиғи", "Тунги қўшиқ", "Клип/премьера", "Премьера"}


def music_no_video(m) -> bool:
    if m["rubric"] not in MUSIC_RUBRICS:
        return False
    import json as _j
    try:
        media = _j.loads(m["media"] or "[]")
    except (TypeError, ValueError):
        media = []
    return not any((x.get("type") or "") in ("video", "animation", "video_note") for x in media)



def _txt_key(text) -> str:
    from .text import strip_sources
    k = _nrm(strip_sources(text or ""))
    return k[:120] if len(k) >= 60 else ""


def repeat_block(db, channel: str, m, now: dt.datetime) -> str:
    """Почему пост не выходит как повтор ('' — можно). Сверка по fp и по тексту (≥ 60 букв)."""
    if m["rubric"] == MINBAR:
        return ""
    fp, key = m["fp"], _txt_key(m["text"])
    if not fp and not key:
        return ""
    def same(r) -> bool:
        return bool((fp and r["fp"] == fp) or (key and _txt_key(r["text"]) == key))
    for r in db.execute("SELECT id, fp, text FROM materials WHERE id<>? AND status='rejected'", (m["id"],)):
        if same(r):
            return "🗑 такой пост уже убран"
    for r in db.execute("SELECT k FROM kv WHERE k LIKE 'xd\\_%' ESCAPE '\\'"):
        try:
            x = store.get(db, int(r[0][3:]))
        except ValueError:
            continue
        if x is not None and x["id"] != m["id"] and same(x):
            return "🗑 вы этот пост удаляли из канала"
    since = (now - dt.timedelta(days=REPEAT_BLOCK_DAYS)).isoformat()
    for r in db.execute("SELECT id, fp, text FROM materials WHERE id<>? AND channel=? AND status IN ('queued','published') "
                        "AND COALESCE(scheduled_at, created_at)>=?", (m["id"], channel, since)):
        if same(r):
            return f"🔁 такой пост уже был в канале за {REPEAT_BLOCK_DAYS} дней"
    return ""


MINBAR_LAST = dt.timedelta(minutes=20)    # 01.11: за 20 мин до 22:00 свежего урока нет → запасной вариант


def minbar_pick(db, ch: dict, channel: str, pool: list, used: list, t: dt.datetime, now: dt.datetime):
    """Кто идёт в час Муфтия. 1) свежий урок (как раньше). 2) За 20 мин свежего нет — урок Муфтия из запаса,
    уже выходивший раньше (цикл не рвётся), но не тот, что сегодня стоит/вышел в другом канале.
    3) Совсем нет уроков Муфтия — Маънавият (лучше, чем пустой финал дня)."""
    fresh = next((m for m in pool if m["id"] not in used and m["rubric"] == MINBAR), None)
    if fresh or t - now > MINBAR_LAST:
        return fresh
    a = plan.slot_time(t.date(), "00:00").isoformat()
    other = [_nrm(r[0])[:120] for r in db.execute(
        "SELECT text FROM materials WHERE channel<>? AND rubric=? AND status IN ('queued','published') "
        "AND COALESCE(scheduled_at, created_at)>=?", (channel, MINBAR, a)).fetchall()]
    rep = [m for m in store.stock(db, channel) if m["id"] not in used and m["rubric"] == MINBAR and minbar_ok(m)
           and not twin_today(db, channel, m, now) and _nrm(m["text"])[:120] not in other]
    if rep:
        return rep[-1]
    return next((m for r in (hour_wants(ch, t) or [])[1:] for m in pool
                 if m["id"] not in used and m["rubric"] == r and allowed(ch, t, r) and greet_ok(m["text"], t)), None)


# ---------- 📌 Твёрдые слоты протокола (09.11.2026, владелец) ----------
# Утро — до 08:00 (дальше люди уходят на работу): 06:30 зарядка, 06:45 здоровье, 07:15 завтрак; новости — 3 раза
# в день (07:40 / 13:00 / 19:00) только из банка «СРОЧНО НОВОСТИ». config: [[channels.<канал>.fixed]]
# t = "06:30", sklad = ["БАНК · БАДАНТАРБИЯ"], rubric = "Бадантарбия" (news = true — свежие ≤ 12 ч, сначала новейшая).
# Вне часовой сетки и вне лимита 20; карточка с 🗑 в пульте за 30–90 мин; нет материала — слот пропускается
# (пустых постов нет). Откат: удалить блоки fixed в config.toml.

def fixed_slots(ch: dict, day: dt.date) -> list[tuple[dt.datetime, dict]]:
    return [(plan.slot_time(day, s["t"]), s) for s in (ch.get("fixed") or [])]


def fixed_news(ch: dict) -> bool:
    """Новости идут только в своих твёрдых слотах — сетка их в «ближайший час» не ставит."""
    return any(s.get("news") for s in (ch.get("fixed") or []))


def _src_in(m, names) -> bool:
    src = m["source"] if "source" in m.keys() else None
    if not src:
        return False
    old = next((o for new, o in BANK_TITLES.items() if _nrm(src) == _nrm(new)), src)
    return any(_nrm(n) in (_nrm(src), _nrm(old)) for n in names)


def _base_pool(db, cfg: dict, channel: str, now: dt.datetime) -> list:
    ch = cfg["channels"][channel]
    return [m for m in store.stock(db, channel)
            if dt.datetime.fromisoformat(m["created_at"]) >= now - dt.timedelta(days=STOCK_DAYS)
            and not waits_text(cfg, m) and not _stale(ch, m, now)
            and minbar_ok(m) and not twin_taken(db, channel, m) and not twin_today(db, channel, m, now)
            and not repeat_block(db, channel, m, now) and not (m["auto"] and music_no_video(m))
            and not (m["auto"] and not m["has_media"])
            and not (urgent_sklad(ch, m["source"]) and dt.datetime.fromisoformat(m["created_at"]) < now - URGENT_TTL)]


def _fixed_cands(ch: dict, s: dict, pool: list, used, t: dt.datetime, now: dt.datetime) -> list:
    c = [m for m in pool if m["id"] not in used and _src_in(m, s.get("sklad") or []) and _fits(ch, m, t, now)]
    if s.get("news"):
        c = [m for m in c if dt.datetime.fromisoformat(m["created_at"]) >= now - URGENT_TTL]
        c.reverse()                                     # новость — самая свежая
    return c


def fill_fixed(db, cfg: dict, channel: str, now: dt.datetime, pool: list) -> list[int]:
    ch = cfg["channels"][channel]
    used: list[int] = []
    for t, s in fixed_slots(ch, now.date()) + fixed_slots(ch, now.date() + dt.timedelta(days=1)):
        if not (now + LEAD <= t <= now + STOCK_AHEAD):
            continue
        key = f"fixed_{channel}_{t:%Y%m%d%H%M}"
        if store.kv_get(db, key) or blocked(db, channel, t):   # протокол: галочки режима дня его не выключают
            continue
        pick = next(iter(_fixed_cands(ch, s, pool, used, t, now)), None)
        if not pick:
            continue
        store.update(db, pick["id"], status="queued", scheduled_at=t.isoformat(), stock=0, fixed=1,
                     rubric=s.get("rubric") or pick["rubric"], planned_at=t.isoformat())
        store.kv_set(db, key, str(pick["id"]))
        used.append(pick["id"])
    return used


def fixed_reserve(ch: dict, pool: list, now: dt.datetime) -> set[int]:
    """Сетка днём не съедает материал, отложенный под твёрдые слоты: под каждый слот — по 2 поста (сегодня + завтра)."""
    keep: set[int] = set()
    for s in (ch.get("fixed") or []):
        if s.get("news"):
            continue
        keep.update(m["id"] for m in [m for m in pool if m["id"] not in keep and _src_in(m, s.get("sklad") or [])][:2])
    return keep


URGENT_TTL = dt.timedelta(hours=12)       # 01.11: срочная новость старше 12 ч — уже не срочная, не выходит


def fill_from_stock(db, cfg: dict, channel: str, now: dt.datetime) -> list[int]:
    """Пустой слот рубрики в ближайшие 90 минут → берём из 📦 запаса материал этой рубрики (старые первыми)."""
    ch = cfg["channels"][channel]
    room = day_room(db, cfg, channel, now)              # 30.10 сверка №10: дневной лимит 20
    # 31.10 владелец: «в обоих каналах должен идти Муфтий» — час Муфтия (22:00) — протокол дня, вне лимита 20
    # (в КАТТА ДАВРА 31.10 лимит кончился к 20:30 и Муфтий не вышел). Лимит исчерпан — запас ставит только Муфтия.
    full = room is not None and room <= 0
    base = _base_pool(db, cfg, channel, now)
    fixed_ids = fill_fixed(db, cfg, channel, now, base)     # 📌 09.11: твёрдые слоты протокола — первыми, вне лимита 20
    if full and not hourly(ch):
        return fixed_ids
    reserved = fixed_reserve(ch, [m for m in base if m["id"] not in fixed_ids], now)
    pool = [m for m in base if m["id"] not in fixed_ids and m["id"] not in reserved
            and (not full or m["rubric"] == MINBAR or urgent_sklad(ch, m["source"]))]
    if not pool and not (hourly(ch) and store.stock(db, channel)):   # 01.11: час Муфтия может взять повтор урока
        return fixed_ids
    used: list[int] = list(fixed_ids)
    counted = 0
    if hourly(ch):                                   # сетка без рубрик: в пустой час — самый старый материал запаса
        for t in free_hours(db, ch, channel, None, now, now.date(), until=now + STOCK_AHEAD + dt.timedelta(seconds=1),
                            minbar=True):
            wants = hour_wants(ch, t)
            if is_minbar_hour(ch, t):                  # 01.11 ТВЁРДЫЙ ЗАКОН: 22:00 — Муфтий в обоих каналах
                pick = minbar_pick(db, ch, channel, pool, used, t, now)
                if pick:
                    store.update(db, pick["id"], status="queued", scheduled_at=t.isoformat(), stock=0)
                    used.append(pick["id"])
                continue
            hot = None if (MINBAR in (wants or [])[:1] or fixed_news(ch)) else next(
                (m for m in pool if m["id"] not in used and urgent_sklad(ch, m["source"]) and _fits(ch, m, t, now)), None)   # 01.11: «СРОЧНО НОВОСТИ» — в ближайший свободный час, любой
            if hot is not None:
                pick = hot
            elif wants is not None:                    # 30.10: в час берём только его рубрики; нет такой — час пустой
                pick = next((m for r in wants for m in pool if m["rubric"] == r and m["id"] not in used
                             and allowed(ch, t, r) and _fits(ch, m, t, now)), None)
                if pick is None and ch.get("hour_rubrics_loose"):
                    pick = next((m for m in pool if m["id"] not in used and m["rubric"] != MINBAR
                                 and allowed(ch, t, m["rubric"]) and _fits(ch, m, t, now)), None)
            else:
                pick = next((m for m in pool if m["id"] not in used and allowed(ch, t, m["rubric"]) and _fits(ch, m, t, now)), None)
            if pick:
                store.update(db, pick["id"], status="queued", scheduled_at=t.isoformat(), stock=0)
                used.append(pick["id"])
                counted += pick["rubric"] != MINBAR
                if room is not None and counted >= room:
                    break
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
            if room is not None and len(used) >= room:
                break
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
    stash: dict[str, list[str]] = {}                   # 05.11: рубрика → склады (config sklad), как в заказе needs.py
    for name, rub in (ch.get("sklad") or {}).items():
        for r in ([rub] if isinstance(rub, str) else rub):
            stash.setdefault(r, []).append(name)
    if hourly(ch):
        # 30.10: запас ставится в час только за 90 мин — дальние часы показываем честно: «возьмёт из запаса», а не «нет материала»
        left: dict[str, int] = {}
        for m in store.stock(db, channel):
            left[m["rubric"]] = left.get(m["rubric"], 0) + 1
        for t in free_hours(db, ch, channel, None, now, day, minbar=True):
            w = hour_wants(ch, t)
            got = next((r for r in (w or []) if left.get(r, 0) > 0), None)
            if got is None and w is None and left:
                got = next(iter(left))
            if got:
                left[got] -= 1
                items.append((f"{t:%H:%M}", f"📦 {t:%H:%M}  {got} — возьмёт из запаса"))
                continue
            sk = next((r for r in (w or []) if stash.get(r)), None)
            if sk:                                     # 05.11: склад этой рубрики есть — якорь закроет час за 2,5 ч до него
                items.append((f"{t:%H:%M}", f"⚓ {t:%H:%M}  {sk} — закроет якорь"))
                continue
            empty += 1
            items.append((f"{t:%H:%M}", f"⚠️ {t:%H:%M}  {w[0] + ' — нет источника' if w else 'час пустой — нет поста'}"))
    if not hourly(ch):                                 # 05.11: сетка со слотами — тоже честно: запас / якорь / нет источника
        left2: dict[str, int] = {}
        for m in store.stock(db, channel):
            left2[m["rubric"]] = left2.get(m["rubric"], 0) + 1
    for t, s in ([] if hourly(ch) else grid(ch, day)):
        if s["kind"] == "ad" or t < now or not is_free(ch, t, busy):
            continue
        w = [s["rubric"]] + list(s.get("fallback", []))
        got = next((r for r in w if left2.get(r, 0) > 0), None)
        if got:
            left2[got] -= 1
            items.append((f"{t:%H:%M}", f"📦 {t:%H:%M}  {got} — возьмёт из запаса"))
            continue
        sk = next((r for r in w if stash.get(r)), None)
        if sk:
            items.append((f"{t:%H:%M}", f"⚓ {t:%H:%M}  {sk} — закроет якорь"))
            continue
        empty += 1
        items.append((f"{t:%H:%M}", f"⚠️ {t:%H:%M}  {s['rubric']} — нет источника"))
    from . import namaz
    items += namaz.today_lines(db, channel, day)
    from . import morning
    items += morning.today_lines(db, channel, day)
    from . import rezhim
    items += rezhim.day_lines(db, cfg, channel, day, now)
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
        tail.append(f"⚠️ Часов без источника: {empty} — для них нужен склад/хаб.")
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
        hrs = [t for t in free_hours(db, ch, channel, rubric, now, day, exclude, until) if not minbar_hour(ch, t, rubric)]
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
