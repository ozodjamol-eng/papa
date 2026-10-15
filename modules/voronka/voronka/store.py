"""Локальное состояние Voronka (SQLite): что уже обработано, кому что отправлено.
Позже события дублируются в ядро PAPA (PostgreSQL, таблица events)."""
from __future__ import annotations

import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS comments (
    comment_id  TEXT PRIMARY KEY,
    media_id    TEXT NOT NULL,
    user_id     TEXT,
    username    TEXT,
    at          TEXT NOT NULL,
    action      TEXT NOT NULL,          -- sent / dup / own / skip / error / dry
    detail      TEXT
);
CREATE INDEX IF NOT EXISTS idx_comments_media_user ON comments(media_id, user_id, action);
CREATE INDEX IF NOT EXISTS idx_comments_at ON comments(at, action);
CREATE TABLE IF NOT EXISTS joins (
    id          INTEGER PRIMARY KEY,
    chat_id     TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    invite_name TEXT,
    at          TEXT NOT NULL,
    welcomed    INTEGER NOT NULL,
    approved    INTEGER NOT NULL,
    detail      TEXT
);
CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT NOT NULL);
"""


def connect(path: str) -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


def seen(db, comment_id: str) -> bool:
    return db.execute("SELECT 1 FROM comments WHERE comment_id=?", (comment_id,)).fetchone() is not None


def already_sent(db, media_id: str, user_id: str) -> bool:
    return db.execute("SELECT 1 FROM comments WHERE media_id=? AND user_id=? AND action IN ('sent','dry')",
                      (media_id, user_id)).fetchone() is not None


def sent_since(db, since_iso: str) -> int:
    return db.execute("SELECT COUNT(*) FROM comments WHERE action='sent' AND at>=?", (since_iso,)).fetchone()[0]


def mark(db, c: dict, media_id: str, at: str, action: str, detail: str = "") -> None:
    u = c.get("from") or {}
    db.execute("INSERT OR IGNORE INTO comments VALUES (?,?,?,?,?,?,?)",
               (c["id"], media_id, u.get("id"), u.get("username"), at, action, detail[:300]))
    db.commit()


def kv_get(db, k: str, default: str | None = None) -> str | None:
    r = db.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
    return r[0] if r else default


def kv_set(db, k: str, v: str) -> None:
    db.execute("INSERT INTO kv VALUES (?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, v))
    db.commit()


def add_join(db, chat_id, user_id, invite_name, at, welcomed, approved, detail="") -> None:
    db.execute("INSERT INTO joins(chat_id,user_id,invite_name,at,welcomed,approved,detail) VALUES (?,?,?,?,?,?,?)",
               (str(chat_id), str(user_id), invite_name, at, int(welcomed), int(approved), detail[:300]))
    db.commit()


def purge(db, before_iso: str) -> int:
    """Удалить личные данные старше срока (обещано в политике конфиденциальности: 90 дней)."""
    n = db.execute("DELETE FROM comments WHERE at < ?", (before_iso,)).rowcount
    n += db.execute("DELETE FROM joins WHERE at < ?", (before_iso,)).rowcount
    db.commit()
    return n
