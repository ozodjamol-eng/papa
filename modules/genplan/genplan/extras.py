"""Что было в GENPLAN 5 и переносится в PAPA при переходе Хўжаобода (20.10, владелец: «ничего не должно остаться
в старом генплане»):

1. ☀️ Утро 07:00 — погода и курс валют (в GENPLAN 5: «🌤 Ҳаво: 10°С, очиқ ҳаво / 💱 Курс: USD … | EUR …»).
   Приветствие уже дал «Хайрли тонг» — здесь только погода и курс. Каналы: channels.X.info = { at = "07:00" }.
2. 🌙 Якуний пост 22:00 — контент владельца (видео муфтия) выходит КАЖДЫЙ день, пока владелец его не сменит
   (кнопка «🌙 Якуний пост» в карточке). Каналы: channels.X.final_post = { at = "22:00" }.
3. 📣 Рекламный пакет на N дней — реклама выходит каждый день в одно время до конца пакета (campaigns GENPLAN 5).

Всё — протокол: выходит само, без ✅. Ошибка — в ERRORS (владельцу сразу) и в журнал Стража.
"""
from __future__ import annotations

import datetime as dt
import json

from . import plan, store

GRACE = dt.timedelta(minutes=15)          # сервер стоял дольше — поздно не публикуем, отмечаем «пропущено»

SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_posts (
    channel TEXT NOT NULL, day TEXT NOT NULL, key TEXT NOT NULL,      -- key: info / final
    at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',         -- pending / done / skipped / failed
    message_id INTEGER, error TEXT,
    PRIMARY KEY (channel, day, key)
);
CREATE TABLE IF NOT EXISTS ad_campaigns (
    id INTEGER PRIMARY KEY,
    material_id INTEGER NOT NULL,            -- первый (исходный) рекламный пост
    channel TEXT NOT NULL,
    at TEXT NOT NULL,                        -- HH:MM каждый день
    start_day TEXT NOT NULL,                 -- YYYY-MM-DD (день 1)
    days INTEGER NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',   -- active / done / stopped
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ad_campaign_days (
    campaign_id INTEGER NOT NULL, day TEXT NOT NULL, material_id INTEGER,
    PRIMARY KEY (campaign_id, day)
);
"""

TITLE = {"info": "☀️ Об-ҳаво ва курс", "final": "🌙 Якуний пост"}


def setup(db) -> None:
    db.executescript(SCHEMA)


def opts(ch: dict, key: str) -> dict | None:
    o = ch.get("info" if key == "info" else "final_post")
    if not o or not o.get("enabled", True):
        return None
    return {"at": "07:00" if key == "info" else "22:00", **o}


# ---------- ☀️ погода и курс ----------

# 20.10: полные фразы вместо обрывков («очиқ» → «очиқ ҳаво»)
PHRASE = {"очиқ": "очиқ ҳаво", "булутли": "булутли ҳаво", "туман": "туманли ҳаво", "ёмғир": "ёмғир ёғади",
          "қор": "қор ёғади", "шивалаб ёмғир": "шивалаб ёмғир ёғади"}


def info_text(ch: dict, w: dict | None, r: dict | None, day: dt.date) -> str | None:
    """Текст как в GENPLAN 5 (без повторного «Хайрли тонг»). Нет ни погоды, ни курса — None (пост не выходит)."""
    from .digest import _num, _signed, sky
    lines = []
    city = (w or {}).get("Хўжаобод")
    if city:
        word, icon = sky(city["code"], city.get("night", False))
        word = PHRASE.get(word, word)
        mx = (city.get("today") or {}).get("max")
        day_part = f", кундузи {_signed(mx)}° гача" if mx is not None and mx > city["t"] else ""
        lines.append(f"{icon} Хўжаобод: ҳозир {_signed(city['t'])}°{day_part}, {word}")
    if r and r.get("USD"):
        usd = f"USD — {_num(r['USD']['rate'])} сўм"
        eur = f" | EUR — {_num(r['EUR']['rate'])} сўм" if r.get("EUR") else ""
        lines.append(f"💱 Валюта курси: {usd}{eur}")
    if not lines:
        return None
    sigs = list(ch.get("signatures") or ([ch["signature"]] if ch.get("signature") else []))
    sig = sigs[day.toordinal() % len(sigs)] if sigs else ""
    tag = (ch.get("hashtags") or {}).get("Тонг/Об-ҳаво", "#ОБ_ҲАВО")
    return "\n".join([tag, ""] + lines + (["", sig] if sig else []))


# ---------- 🎬 ролик погоды (Fabrika, решение владельца 20.10) ----------
# Рендер — GitHub Actions `motion-weather` (Франкфурт с 1 ГБ браузер не тянет), MP4 лежит в ветке motion публичного репо.
VIDEO_URL = "https://raw.githubusercontent.com/ozodjamol-eng/papa/motion/xojaobod-weather-{day}.mp4"


def weather_video(day: dt.date, get=None, folder: str | None = None):
    """Готовый ролик погоды этого дня → локальный файл. Нет / не тот / битый — исключение (тогда выходит прежний текст)."""
    import tempfile
    from pathlib import Path
    from .digest import _get
    data = (get or (lambda u: _get(u, timeout=60, tries=2)))(VIDEO_URL.format(day=day.isoformat()))
    if not data or len(data) < 200_000 or data[4:8] != b"ftyp":
        raise ValueError("ролик не собран")
    if len(data) > 49_000_000:
        raise ValueError("ролик больше 49 МБ")
    path = Path(folder or tempfile.gettempdir()) / f"xojaobod-weather-{day.isoformat()}.mp4"
    path.write_bytes(data)
    return path


# ---------- 🌙 Якуний пост ----------

def final_get(db, channel: str) -> dict | None:
    raw = store.kv_get(db, f"final_{channel}", "")
    return json.loads(raw) if raw else None


def final_set(db, channel: str, m, via: str | None = None) -> dict:
    """Материал → Якуний пост канала (выходит каждый день до замены). Материал больше не ждёт обычной публикации.
    21.10: источник — там, куда владелец бросил пост (чат пульта / ХАБ канала); в PAPA HUB копия кладётся только
    на секунды публикации (service.staged), поэтому via — бот, который видит этот источник."""
    v = {"material_id": int(m["id"]), "text": m["text"] or "", "hub_chat": int(m["hub_chat"]), "hub_msg": int(m["hub_msg"]),
         "via": via,
         "hub_msgs": json.loads(m["hub_msgs"] or "[]") if "hub_msgs" in m.keys() else [],
         "has_media": bool(m["has_media"]), "set_at": dt.datetime.now(plan.TZ).isoformat()}
    store.kv_set(db, f"final_{channel}", json.dumps(v, ensure_ascii=False))
    store.update(db, int(m["id"]), status="rejected", rubric="Якуний пост", scheduled_at=None, stock=0)
    db.execute("DELETE FROM daily_posts WHERE channel=? AND key='final' AND status='pending'", (channel,))
    db.commit()
    return v


# ---------- 📣 рекламный пакет ----------

def campaign_of(db, material_id: int):
    return db.execute("SELECT c.* FROM ad_campaigns c LEFT JOIN ad_campaign_days d ON d.campaign_id=c.id "
                      "WHERE c.material_id=? OR d.material_id=? ORDER BY c.id DESC LIMIT 1",
                      (material_id, material_id)).fetchone()


def campaign_from(db, m, days: int, name: str = "") -> dict:
    """Реклама в плане (со временем) → пакет на days дней: каждый день в то же время, день 1 — этот пост."""
    if not m["scheduled_at"]:
        raise ValueError("сначала выберите время рекламы")
    t = dt.datetime.fromisoformat(m["scheduled_at"]).astimezone(plan.TZ)
    old = campaign_of(db, int(m["id"]))
    if old is not None:
        db.execute("UPDATE ad_campaigns SET days=?, at=?, status='active' WHERE id=?", (days, t.strftime("%H:%M"), old["id"]))
        cid = old["id"]
    else:
        cid = db.execute("INSERT INTO ad_campaigns(material_id,channel,at,start_day,days,name,created_at) VALUES (?,?,?,?,?,?,?)",
                         (int(m["id"]), m["channel"], t.strftime("%H:%M"), t.date().isoformat(), days,
                          name or (m["text"] or "")[:40], dt.datetime.now(plan.TZ).isoformat())).lastrowid
        db.execute("INSERT OR IGNORE INTO ad_campaign_days(campaign_id,day,material_id) VALUES (?,?,?)",
                   (cid, t.date().isoformat(), int(m["id"])))
    db.execute("UPDATE materials SET locked=1 WHERE id=?", (int(m["id"]),))
    db.commit()
    c = db.execute("SELECT * FROM ad_campaigns WHERE id=?", (cid,)).fetchone()
    return dict(c)


WD = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")


def days_word(n: int) -> str:
    return "день" if n % 10 == 1 and n % 100 != 11 else ("дня" if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else "дней")


def campaign_note(c) -> str:
    """21.10 владелец: «📅 Реклама: Ср–Сб · 4 дня · каждый день 15:10» — дни недели вместо «3/6/10 кун»."""
    start = dt.date.fromisoformat(c["start_day"])
    end = start + dt.timedelta(days=int(c["days"]) - 1)
    if c["status"] == "stopped" or int(c["days"]) <= 1:
        return "✅ Разовая реклама"
    return (f"📅 Реклама: {WD[start.weekday()]}–{WD[end.weekday()]} · {c['days']} {days_word(int(c['days']))} · "
            f"каждый день {c['at']} ({start:%d.%m}–{end:%d.%m})")


def campaign_stop(db, material_id: int) -> int:
    """✅ Разовая: пакет снят; уже созданные будущие показы (не исходный пост) — убираем. Возвращает число убранных."""
    c = campaign_of(db, material_id)
    if c is None:
        return 0
    db.execute("UPDATE ad_campaigns SET status='stopped', days=1 WHERE id=?", (c["id"],))
    rows = db.execute("SELECT d.material_id FROM ad_campaign_days d JOIN materials m ON m.id=d.material_id "
                      "WHERE d.campaign_id=? AND d.material_id IS NOT NULL AND d.material_id<>? AND m.status='queued'",
                      (c["id"], c["material_id"])).fetchall()
    for r in rows:
        db.execute("UPDATE materials SET status='rejected' WHERE id=?", (r[0],))
    db.commit()
    return len(rows)


# ---------- 🏷 кампании с названием (23.10 владелец: «верни старую схему, как в GENPLAN 5» — №, название, список) ----------

def ad_source(db, mid: int) -> int:
    """Исходный рекламный пост кампании (показы следующих дней — копии)."""
    c = campaign_of(db, mid)
    return int(c["material_id"]) if c is not None else int(mid)


def auto_name(text: str) -> str:
    """Название по первым словам рекламы (если владелец не написал своё)."""
    import re
    for ln in (text or "").splitlines():
        if ln.strip().startswith("#"):
            continue
        ln = re.sub(r"^[^\w«\"]+", "", ln.strip())
        if ln:
            words = ln.split()
            out = ""
            for w in words:
                if len(out) + len(w) + 1 > 24:
                    break
                out = f"{out} {w}".strip()
            return (out or ln[:24]).upper()
    return "РЕКЛАМА"


def ad_name(db, mid: int) -> tuple[int | None, str]:
    """(№, название) кампании; № нет — название ещё не задано."""
    src = ad_source(db, mid)
    no = store.kv_get(db, f"ad_no_{src}", "")
    return (int(no) if no else None), store.kv_get(db, f"ad_name_{src}", "")


def ad_name_set(db, mid: int, name: str) -> tuple[int, str]:
    """Название кампании; № выдаётся один раз, по порядку (в GENPLAN 5 последние были №11, №12 — продолжаем с №13)."""
    src = ad_source(db, mid)
    name = " ".join((name or "").split())[:40]
    no = store.kv_get(db, f"ad_no_{src}", "")
    if not no:
        no = int(store.kv_get(db, "ad_seq", "12")) + 1
        store.kv_set(db, "ad_seq", no)
        store.kv_set(db, f"ad_no_{src}", no)
    store.kv_set(db, f"ad_name_{src}", name)
    db.execute("UPDATE ad_campaigns SET name=? WHERE material_id=?", (name, src))
    db.commit()
    return int(no), name


def ad_name_ensure(db, mid: int) -> tuple[int, str]:
    """При «✅ Утверждаю»: названия нет — берём первые слова рекламы."""
    no, name = ad_name(db, mid)
    if no and name:
        return no, name
    src = store.get(db, ad_source(db, mid))
    return ad_name_set(db, mid, name or auto_name(src["text"] if src is not None else ""))


def ad_label(db, mid: int) -> str:
    no, name = ad_name(db, mid)
    if not name:
        return ""
    return f"№{no} · {name}" if no else name


def ad_rows(db, channel: str, now: dt.datetime) -> list[dict]:
    """📢 Мои кампании: активные пакеты и разовые рекламы канала, которые ещё не вышли."""
    out: dict[int, dict] = {}
    today = now.date()
    for c in db.execute("SELECT * FROM ad_campaigns WHERE status='active' AND channel=?", (channel,)).fetchall():
        start = dt.date.fromisoformat(c["start_day"])
        last = start + dt.timedelta(days=int(c["days"]) - 1)
        if int(c["days"]) <= 1 or today > last:
            continue
        q = db.execute("SELECT m.id, m.scheduled_at FROM ad_campaign_days d JOIN materials m ON m.id=d.material_id "
                       "WHERE d.campaign_id=? AND m.status='queued' ORDER BY m.scheduled_at LIMIT 1", (c["id"],)).fetchone()
        if q:
            nxt, show = dt.datetime.fromisoformat(q[1]).astimezone(plan.TZ), int(q[0])
        else:
            d = max(today, start)
            if plan.slot_time(d, c["at"]) < now:
                d += dt.timedelta(days=1)
            if d > last:
                continue
            nxt, show = plan.slot_time(d, c["at"]), int(c["material_id"])
        n = (min(max(today, start), last) - start).days + 1
        out[int(c["material_id"])] = {"src": int(c["material_id"]), "show": show, "next": nxt, "at": c["at"],
                                      "info": f"день {n} из {c['days']} (до {WD[last.weekday()]} {last:%d.%m})", "multi": True}
    for m in db.execute("SELECT id, scheduled_at FROM materials WHERE channel=? AND status='queued' AND rubric LIKE 'Реклама%' "
                        "AND scheduled_at IS NOT NULL ORDER BY scheduled_at", (channel,)).fetchall():
        src = ad_source(db, int(m[0]))
        if src in out:
            continue
        t = dt.datetime.fromisoformat(m[1]).astimezone(plan.TZ)
        out[src] = {"src": src, "show": int(m[0]), "next": t, "at": f"{t:%H:%M}", "info": "разовая", "multi": False}
    rows = sorted(out.values(), key=lambda r: r["next"])
    for r in rows:
        no, name = ad_name(db, r["src"])
        if not name:
            m = store.get(db, r["src"])
            name = auto_name(m["text"] if m is not None else "") + " (без названия)"
        r["no"], r["name"] = no, name
        r["clash"] = sum(1 for x in rows if x["at"] == r["at"] and (x["multi"] or r["multi"] or x["next"] == r["next"])) > 1
    return rows


def ad_stop(db, src: int, now: dt.datetime) -> int:
    """⏸ Стоп: кампания снята, все её невышедшие показы убраны. Возвращает число убранных показов."""
    ids = {int(src)}
    c = campaign_of(db, src)
    if c is not None:
        db.execute("UPDATE ad_campaigns SET status='stopped' WHERE id=?", (c["id"],))
        ids |= {int(r[0]) for r in db.execute("SELECT material_id FROM ad_campaign_days WHERE campaign_id=? "
                                               "AND material_id IS NOT NULL", (c["id"],))}
    n = 0
    for i in ids:
        n += db.execute("UPDATE materials SET status='rejected' WHERE id=? AND status IN ('queued','draft')", (i,)).rowcount
    db.commit()
    return n


def ad_extend(db, src: int) -> dict:
    """➕ +1 день: пакет на день длиннее; у разовой — становится пакетом на 2 дня в то же время."""
    c = campaign_of(db, src)
    if c is not None and c["status"] == "active" and int(c["days"]) > 1:
        db.execute("UPDATE ad_campaigns SET days=days+1 WHERE id=?", (c["id"],))
        db.commit()
        return dict(db.execute("SELECT * FROM ad_campaigns WHERE id=?", (c["id"],)).fetchone())
    m = store.get(db, src)
    days = 2
    if c is not None:
        db.execute("UPDATE ad_campaigns SET status='active' WHERE id=?", (c["id"],))
    return campaign_from(db, m, days)


def shift_time(db, cfg: dict | None, channel: str, at: dt.datetime, now: dt.datetime) -> dt.datetime:
    """Время показа занято или в тихом окне (Жума) → ближайшее свободное рекламное окно того же дня."""
    if not cfg or channel not in cfg.get("channels", {}):
        return at
    from . import smart
    ch = cfg["channels"][channel]
    busy = smart.occupied(db, channel, now, ch=ch, grid_posts=False)   # 25.10: пост часовой сетки уступит рекламе сам
    ok = lambda t: t >= now + smart.LEAD and smart.is_free(ch, t, busy) and not smart.blocked(db, channel, t)  # noqa: E731
    if ok(at):
        return at
    wins = sorted((t for t, s in smart.grid(ch, at.date()) if s["kind"] == "ad" and ok(t)), key=lambda t: abs(t - at))
    return wins[0] if wins else at


def ensure_campaigns(db, now: dt.datetime, cfg: dict | None = None) -> list[int]:
    """Сегодняшний показ каждого активного пакета → материал в плане (если время ещё не прошло)."""
    made = []
    today = now.date()
    for c in db.execute("SELECT * FROM ad_campaigns WHERE status='active'").fetchall():
        start = dt.date.fromisoformat(c["start_day"])
        last = start + dt.timedelta(days=int(c["days"]) - 1)
        if today > last:
            db.execute("UPDATE ad_campaigns SET status='done' WHERE id=?", (c["id"],))
            continue
        if today < start or db.execute("SELECT 1 FROM ad_campaign_days WHERE campaign_id=? AND day=?",
                                       (c["id"], today.isoformat())).fetchone():
            continue
        at = plan.slot_time(today, c["at"])
        if now > at + GRACE:
            db.execute("INSERT OR IGNORE INTO ad_campaign_days(campaign_id,day,material_id) VALUES (?,?,NULL)",
                       (c["id"], today.isoformat()))
            continue
        src = store.get(db, c["material_id"])
        if src is None:
            continue
        at = shift_time(db, cfg, c["channel"], at, now)
        cols = ("hub_chat", "hub_msg", "text", "has_media", "media", "hub_msgs", "channel", "rubric", "tag", "topic", "via")
        vals = [src[k] if k in src.keys() else None for k in cols]
        mid = db.execute(f"INSERT INTO materials({','.join(cols)},status,urgent,created_at,scheduled_at,locked,guessed,stock) "
                         f"VALUES ({','.join('?' * len(cols))},'queued',0,?,?,1,0,0)",
                         (*vals, store.now_iso(), at.isoformat())).lastrowid
        db.execute("INSERT INTO ad_campaign_days(campaign_id,day,material_id) VALUES (?,?,?)", (c["id"], today.isoformat(), mid))
        made.append(mid)
    db.commit()
    return made


# ---------- ежедневные посты ----------

def ensure_day(db, cfg: dict, day: dt.date, now: dt.datetime | None = None) -> None:
    """Посты дня. Время уже давно прошло (служба только что запущена) — не создаём, чтобы не было ложных «пропущен»."""
    for channel, ch in cfg["channels"].items():
        for key in ("info", "final"):
            o = opts(ch, key)
            if not o:
                continue
            if key == "final" and not final_get(db, channel):
                continue
            at = plan.slot_time(day, o["at"])
            if now is not None and now - at > GRACE:
                continue
            db.execute("INSERT OR IGNORE INTO daily_posts(channel,day,key,at) VALUES (?,?,?,?)",
                       (channel, day.isoformat(), key, at.isoformat()))
    db.commit()


def busy(db, channel: str, since: dt.datetime) -> list[dt.datetime]:
    return [dt.datetime.fromisoformat(r[0]) for r in db.execute(
        "SELECT at FROM daily_posts WHERE channel=? AND at>=? AND status IN ('pending','done')", (channel, since.isoformat()))]


def due(db, now: dt.datetime) -> tuple[list, list]:
    ready, late = [], []
    for r in db.execute("SELECT * FROM daily_posts WHERE status='pending' AND at<=? ORDER BY at", (now.isoformat(),)).fetchall():
        (late if now - dt.datetime.fromisoformat(r["at"]) > GRACE else ready).append(r)
    return ready, late


def mark(db, r, **kw) -> None:
    db.execute(f"UPDATE daily_posts SET {', '.join(k + '=?' for k in kw)} WHERE channel=? AND day=? AND key=?",
               (*kw.values(), r["channel"], r["day"], r["key"]))
    db.commit()
