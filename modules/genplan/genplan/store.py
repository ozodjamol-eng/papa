"""Хранилище GENPLAN PAPA (SQLite на сервере публикаций). Позже переносится в ядро PAPA (PostgreSQL, schema_v2)."""
from __future__ import annotations

import datetime as dt
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
"""


def connect(path: str) -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def add_material(db, hub_chat: int, hub_msg: int, text: str, has_media: bool) -> int | None:
    if db.execute("SELECT 1 FROM materials WHERE hub_chat=? AND hub_msg=?", (hub_chat, hub_msg)).fetchone():
        return None
    cur = db.execute("INSERT INTO materials(hub_chat,hub_msg,text,has_media,created_at) VALUES (?,?,?,?,?)",
                     (hub_chat, hub_msg, text or "", int(has_media), now_iso()))
    db.commit()
    return cur.lastrowid


def clone_for(db, mid: int, channel: str) -> int:
    r = get(db, mid)
    cur = db.execute("INSERT INTO materials(hub_chat,hub_msg,text,has_media,channel,created_at,owner_msg) "
                     "VALUES (?,?,?,?,?,?,?)", (r["hub_chat"], r["hub_msg"], r["text"], r["has_media"], channel,
                                               r["created_at"], r["owner_msg"]))
    db.commit()
    return cur.lastrowid


def get(db, mid: int):
    return db.execute("SELECT * FROM materials WHERE id=?", (mid,)).fetchone()


def update(db, mid: int, **kw) -> None:
    sets = ", ".join(f"{k}=?" for k in kw)
    db.execute(f"UPDATE materials SET {sets} WHERE id=?", (*kw.values(), mid))
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
