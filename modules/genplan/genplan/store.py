"""Хранилище GENPLAN PAPA (SQLite на сервере публикаций). Позже переносится в ядро PAPA (PostgreSQL, schema_v2)."""
from __future__ import annotations

import datetime as dt
import json
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS materials (
    id          INTEGER PRIMARY KEY,
    hub_chat    INTEGER NOT NULL,
    hub_msg     INTEGER NOT NULL,
    text        TEXT NOT NULL DEFAULT '',
    has_media   INTEGER NOT NULL DEFAULT 0,
    channel     TEXT,                    -- xojaobod / paparazzi
    rubric      TEXT,
    status      TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','queued','published','rejected','failed')),
    urgent      INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    owner_msg   INTEGER                  -- сообщение с кнопками у владельца
);
CREATE INDEX IF NOT EXISTS idx_mat_pool ON materials(status, channel, rubric, created_at);
CREATE TABLE IF NOT EXISTS publications (
    id          INTEGER PRIMARY KEY,
    channel     TEXT NOT NULL,
    slot_date   TEXT NOT NULL,
    slot        TEXT,                    -- HH:MM; NULL — срочный
    material_id INTEGER,
    status      TEXT NOT NULL,           -- done / missed / failed / skipped
    message_id  INTEGER,
    error       TEXT,
    at          TEXT NOT NULL,
    UNIQUE (channel, slot_date, slot)
);
CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT NOT NULL);
-- «Пульс» канала: когда в канале вышел любой пост (наш или ручной) — чтобы держать промежуток между постами
CREATE TABLE IF NOT EXISTS pulse (channel TEXT NOT NULL, at TEXT NOT NULL, source TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_pulse ON pulse(channel, at);
-- Fabrika: задания на обработку (ссылка → видео + текст + логотип; переписать текст ИИ)
CREATE TABLE IF NOT EXISTS jobs (
    id          INTEGER PRIMARY KEY,
    kind        TEXT NOT NULL,             -- link / ai
    payload     TEXT NOT NULL,             -- JSON
    status      TEXT NOT NULL DEFAULT 'new',   -- new / working / done / failed
    error       TEXT,
    created_at  TEXT NOT NULL,
    done_at     TEXT
);
"""

# Колонки, добавленные позже (миграция только добавляет, ничего не удаляет)
EXTRA = {
    "scheduled_at": "TEXT",        # точное время публикации (ISO, Ташкент) — как в GENPLAN 5
    "media": "TEXT",               # JSON [{type, file_id, uid}] — для альбомов и проверки повторов
    "hub_msgs": "TEXT",            # JSON [id, …] — сообщения альбома в хабе
    "fp": "TEXT",                  # отпечаток содержимого (повторы)
    "locked": "INTEGER NOT NULL DEFAULT 0",   # время выбрал владелец — не двигать автоматически
    "guessed": "INTEGER NOT NULL DEFAULT 0",  # рубрика угадана ботом
    "stock": "INTEGER NOT NULL DEFAULT 0",    # 📦 в запасе: выйдет сам, когда у рубрики будет пустой слот
    "tag": "TEXT",                 # 17.10: хэштег, выбранный владельцем через подрубрику (как в Хўжаободе); NULL — не выбран
    "topic": "TEXT",               # 17.10: подрубрика (эмодзи + название) — для карточки
    "via": "TEXT",
    "hook_ai": "TEXT",             # 17.10: хук по смыслу от ИИ ("" — ИИ решил без хука), чтобы не звать ИИ повторно
    "junk": "TEXT",                # 17.10: JSON — строки с чужими ссылками-словами (из entities), убираются при публикации
    "auto": "INTEGER NOT NULL DEFAULT 0",     # 26.10: склад или выбранный владельцем источник — выходит сам, с вето 🗑
    "planned_at": "TEXT",          # 30.10 сверка №14: время, назначенное при утверждении; авто-переносы (+10, после рекламы) его не меняют — Страж считает опоздание от него
    "source": "TEXT",              # откуда переслал куратор (@канал-источник) — для отчёта и отбора источников                 # через какой бот-пульт пришёл материал ("main" / код канала) — карточки и файлы этого бота
}


def connect(path: str) -> sqlite3.Connection:
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    if path != ":memory:":
        db.execute("PRAGMA journal_mode=WAL")      # бот и Fabrika работают с базой одновременно
    db.executescript(SCHEMA)
    have = {r[1] for r in db.execute("PRAGMA table_info(materials)")}
    for col, typ in EXTRA.items():
        if col not in have:
            db.execute(f"ALTER TABLE materials ADD COLUMN {col} {typ}")
    db.execute("CREATE INDEX IF NOT EXISTS idx_mat_time ON materials(channel, status, scheduled_at)")
    from . import namaz, tails
    namaz.setup(db)
    tails.setup(db)
    from . import morning
    morning.setup(db)
    from . import extras
    extras.setup(db)
    db.execute("CREATE INDEX IF NOT EXISTS idx_mat_fp ON materials(fp)")
    db.commit()
    return db


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def add_material(db, hub_chat: int, hub_msg: int, text: str, has_media: bool, media: list | None = None,
                 hub_msgs: list | None = None, fp: str | None = None) -> int | None:
    if db.execute("SELECT 1 FROM materials WHERE hub_chat=? AND hub_msg=?", (hub_chat, hub_msg)).fetchone():
        return None
    cur = db.execute("INSERT INTO materials(hub_chat,hub_msg,text,has_media,created_at,media,hub_msgs,fp) "
                     "VALUES (?,?,?,?,?,?,?,?)",
                     (hub_chat, hub_msg, text or "", int(has_media), now_iso(), json.dumps(media or []),
                      json.dumps(hub_msgs or [hub_msg]), fp))
    db.commit()
    return cur.lastrowid


def pulse_add(db, channel: str, at: dt.datetime, source: str) -> None:
    db.execute("INSERT INTO pulse(channel, at, source) VALUES (?,?,?)", (channel, at.isoformat(), source))
    db.commit()


def pulse_since(db, channel: str, since: dt.datetime) -> list[dt.datetime]:
    return [dt.datetime.fromisoformat(r[0]) for r in db.execute(
        "SELECT at FROM pulse WHERE channel=? AND at>=?", (channel, since.isoformat()))]


def scheduled(db, channel: str) -> list:
    return db.execute("SELECT * FROM materials WHERE channel=? AND status='queued' AND scheduled_at IS NOT NULL "
                      "ORDER BY scheduled_at", (channel,)).fetchall()


def clone_for(db, mid: int, channel: str) -> int:
    r = get(db, mid)
    cur = db.execute("INSERT INTO materials(hub_chat,hub_msg,text,has_media,channel,created_at,owner_msg,media,hub_msgs,fp) "
                     "VALUES (?,?,?,?,?,?,?,?,?,?)", (r["hub_chat"], r["hub_msg"], r["text"], r["has_media"], channel,
                                                     r["created_at"], r["owner_msg"], r["media"], r["hub_msgs"], r["fp"]))
    if "via" in r.keys() and r["via"]:                     # 21.10: тот же бот видит источник (секундная копия для группы)
        db.execute("UPDATE materials SET via=? WHERE id=?", (r["via"], cur.lastrowid))
    db.commit()
    return cur.lastrowid


def get(db, mid: int):
    return db.execute("SELECT * FROM materials WHERE id=?", (mid,)).fetchone()


def update(db, mid: int, **kw) -> None:
    sets = ", ".join(f"{k}=?" for k in kw)
    vals = list(kw.values())
    if "scheduled_at" in kw and "planned_at" not in kw:     # 30.10 №14: исходное время для Стража
        if kw["scheduled_at"] is None:
            sets += ", planned_at=NULL"
        elif "urgent" in kw or "locked" in kw:               # решение владельца / новая постановка — новое исходное время
            sets += ", planned_at=?"
            vals.append(kw["scheduled_at"])
        else:                                                # авто-перенос: исходное время остаётся
            sets += ", planned_at=COALESCE(planned_at, ?)"
            vals.append(kw["scheduled_at"])
    db.execute(f"UPDATE materials SET {sets} WHERE id=?", (*vals, mid))
    db.commit()


def queued(db, channel: str) -> list:
    return db.execute("SELECT * FROM materials WHERE status='queued' AND channel=? AND urgent=0 ORDER BY created_at",
                      (channel,)).fetchall()


def published_today(db, channel: str, day: str) -> dict:
    return {r["slot"]: r["status"] for r in db.execute(
        "SELECT slot, status FROM publications WHERE channel=? AND slot_date=? AND slot IS NOT NULL", (channel, day))}


def record(db, channel: str, day: str, slot: str | None, material_id: int | None, status: str,
           message_id: int | None = None, error: str = "") -> None:
    db.execute("INSERT OR REPLACE INTO publications(channel,slot_date,slot,material_id,status,message_id,error,at) "
               "VALUES (?,?,?,?,?,?,?,?)", (channel, day, slot, material_id, status, message_id, error[:300], now_iso()))
    db.commit()


def kv_get(db, k, default=None):
    r = db.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
    return r[0] if r else default


def kv_set(db, k, v) -> None:
    db.execute("INSERT INTO kv VALUES (?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, str(v)))
    db.commit()


def stock(db, channel: str) -> list:
    return db.execute("SELECT * FROM materials WHERE channel=? AND status='draft' AND stock=1 ORDER BY created_at",
                      (channel,)).fetchall()


def job_add(db, kind: str, payload: dict) -> int:
    cur = db.execute("INSERT INTO jobs(kind, payload, created_at) VALUES (?,?,?)", (kind, json.dumps(payload), now_iso()))
    db.commit()
    return cur.lastrowid


def job_take(db):
    r = db.execute("SELECT * FROM jobs WHERE status='new' ORDER BY id LIMIT 1").fetchone()
    if r:
        db.execute("UPDATE jobs SET status='working' WHERE id=? AND status='new'", (r["id"],))
        db.commit()
    return r


def job_done(db, jid: int, error: str | None = None) -> None:
    db.execute("UPDATE jobs SET status=?, error=?, done_at=? WHERE id=?", ("failed" if error else "done", error, now_iso(), jid))
    db.commit()
