"""SQLite-хранилище Разведки. Только наши данные: каналы, посты, метрики."""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY,            -- Telegram channel id
    username TEXT,
    title TEXT NOT NULL,
    folder TEXT NOT NULL,              -- тема/папка-источник
    is_own INTEGER NOT NULL DEFAULT 0, -- наш канал (для сравнения)
    subscribers INTEGER,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS posts (
    channel_id INTEGER NOT NULL,
    msg_id INTEGER NOT NULL,
    date_utc TEXT NOT NULL,            -- ISO, UTC
    views INTEGER,
    forwards INTEGER,
    replies INTEGER,
    reactions INTEGER,
    media TEXT,                        -- text|photo|video|album|doc|poll|other
    text_len INTEGER NOT NULL DEFAULT 0,
    text TEXT,                         -- первые 1000 символов, для анализа тем
    links INTEGER NOT NULL DEFAULT 0,  -- число ссылок/упоминаний
    is_forward INTEGER NOT NULL DEFAULT 0,
    grp INTEGER,                       -- id альбома (несколько сообщений = один пост)
    collected_at TEXT NOT NULL,
    PRIMARY KEY (channel_id, msg_id)
);
CREATE INDEX IF NOT EXISTS idx_posts_date ON posts(date_utc);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    channels INTEGER,
    posts INTEGER,
    errors TEXT
);
"""


def connect(path: str | Path) -> sqlite3.Connection:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(p), timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=30000")
    c.executescript(SCHEMA)
    return c


def upsert_channel(c, ch: dict, now: str) -> None:
    c.execute(
        """INSERT INTO channels(id, username, title, folder, is_own, subscribers, updated_at)
           VALUES(:id, :username, :title, :folder, :is_own, :subscribers, :now)
           ON CONFLICT(id) DO UPDATE SET username=excluded.username, title=excluded.title,
             folder=excluded.folder, is_own=excluded.is_own,
             subscribers=COALESCE(excluded.subscribers, channels.subscribers), updated_at=excluded.updated_at""",
        {**ch, "now": now},
    )


def upsert_post(c, p: dict, now: str) -> None:
    # метрики (просмотры, реакции) растут — обновляем при повторном сборе
    c.execute(
        """INSERT INTO posts(channel_id, msg_id, date_utc, views, forwards, replies, reactions, media,
                             text_len, text, links, is_forward, grp, collected_at)
           VALUES(:channel_id, :msg_id, :date_utc, :views, :forwards, :replies, :reactions, :media,
                  :text_len, :text, :links, :is_forward, :grp, :now)
           ON CONFLICT(channel_id, msg_id) DO UPDATE SET views=excluded.views, forwards=excluded.forwards,
             replies=excluded.replies, reactions=excluded.reactions, collected_at=excluded.collected_at""",
        {**p, "now": now},
    )


def last_msg_id(c, channel_id: int) -> int:
    r = c.execute("SELECT MAX(msg_id) FROM posts WHERE channel_id=?", (channel_id,)).fetchone()
    return int(r[0] or 0)
