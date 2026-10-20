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

def info_text(ch: dict, w: dict | None, r: dict | None, day: dt.date) -> str | None:
    """Текст как в GENPLAN 5 (без повторного «Хайрли тонг»). Нет ни погоды, ни курса — None (пост не выходит)."""
    from .digest import sky
    lines = []
    city = (w or {}).get("Хўжаобод")
    if city:
        word, icon = sky(city["code"], city.get("night", False))
        lines.append(f"{icon} Хўжаободда ҳаво: {city['t']}°С, {word}")
    if r and r.get("USD"):
        usd = f"USD: {r['USD']['rate']:.2f} сўм"
        eur = f" | EUR: {r['EUR']['rate']:.2f} сўм" if r.get("EUR") else ""
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


def final_set(db, channel: str, m) -> dict:
    """Материал → Якуний пост канала (выходит каждый день до замены). Материал больше не ждёт обычной публикации."""
    v = {"material_id": int(m["id"]), "text": m["text"] or "", "hub_chat": int(m["hub_chat"]), "hub_msg": int(m["hub_msg"]),
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


def campaign_note(c) -> str:
    start = dt.date.fromisoformat(c["start_day"])
    end = start + dt.timedelta(days=int(c["days"]) - 1)
    return f"🔁 Пакет: {c['days']} кун · ҳар куни {c['at']} · {start:%d.%m}–{end:%d.%m}"


def ensure_campaigns(db, now: dt.datetime) -> list[int]:
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
