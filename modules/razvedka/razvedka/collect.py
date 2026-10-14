"""Сбор постов. Логика не зависит от Telegram-библиотеки: источник передаётся снаружи
(TelethonSource в telegram.py или FakeSource в тестах).

Правила бережного чтения:
- только каналы из папок конфигурации и свои каналы;
- пауза между каналами; при FloodWait — честное ожидание;
- первый сбор — не глубже `first_days`, дальше — только новые посты + обновление метрик
  постов за последние `refresh_days` (просмотры растут несколько суток).
"""
from __future__ import annotations

import asyncio
import datetime as dt
import re

from . import store

LINK_RE = re.compile(r"(https?://\S+|t\.me/\S+|@[A-Za-z0-9_]{4,})")


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def normalize(channel_id: int, m: dict) -> dict:
    text = m.get("text") or ""
    return {
        "channel_id": channel_id,
        "msg_id": int(m["id"]),
        "date_utc": m["date"].astimezone(dt.timezone.utc).isoformat(timespec="seconds"),
        "views": m.get("views"),
        "forwards": m.get("forwards"),
        "replies": m.get("replies"),
        "reactions": m.get("reactions"),
        "media": m.get("media") or "text",
        "text_len": len(text),
        "text": text[:1000],
        "links": len(LINK_RE.findall(text)),
        "is_forward": 1 if m.get("is_forward") else 0,
        "grp": m.get("grp"),
    }


async def collect(source, db, cfg: dict, log=print) -> dict:
    """source: async channels(cfg) -> list[dict]; async messages(channel, since_dt, min_id) -> async iter of dict.
    Возвращает сводку прогона."""
    first_days = int(cfg.get("first_days", 7))
    refresh_days = int(cfg.get("refresh_days", 3))
    pause = float(cfg.get("pause_seconds", 3))
    now = utcnow()
    now_s = now.isoformat(timespec="seconds")
    run_id = db.execute("INSERT INTO runs(started_at) VALUES(?)", (now_s,)).lastrowid
    db.commit()
    errors, n_posts = [], 0
    channels = await source.channels(cfg)
    log(f"каналов к чтению: {len(channels)}")
    for i, ch in enumerate(channels, 1):
        try:
            store.upsert_channel(db, ch, now_s)
            have = store.last_msg_id(db, ch["id"])
            # новый канал — глубина first_days; известный — освежаем refresh_days
            since = now - dt.timedelta(days=first_days if not have else refresh_days)
            got = 0
            async for m in source.messages(ch, since):
                store.upsert_post(db, normalize(ch["id"], m), now_s)
                got += 1
            db.commit()
            n_posts += got
            log(f"[{i}/{len(channels)}] {ch['title'][:40]}: {got} постов")
        except Exception as e:  # один канал не должен ронять весь сбор
            db.rollback()
            errors.append(f"{ch.get('title', ch.get('id'))}: {type(e).__name__}")
            log(f"[{i}/{len(channels)}] {ch.get('title')}: ошибка {type(e).__name__}")
        if i < len(channels):
            await asyncio.sleep(pause)
    db.execute("UPDATE runs SET finished_at=?, channels=?, posts=?, errors=? WHERE id=?",
               (utcnow().isoformat(timespec="seconds"), len(channels), n_posts, "; ".join(errors)[:2000], run_id))
    db.commit()
    return {"channels": len(channels), "posts": n_posts, "errors": errors}
