"""Только чтение: начало текста и тип медиа сообщений группы Хўжаобод по id (ops/frankfurt/group-peek.json)."""
import asyncio
import json
from pathlib import Path

from telethon import TelegramClient
from telethon.sessions import StringSession

PUB = dict(l.split("=", 1) for l in Path("/etc/papa-tg/publisher.env").read_text().splitlines() if "=" in l)
Q = json.loads(Path("/opt/papa/ops/frankfurt/group-peek.json").read_text())


async def main():
    acc = TelegramClient(StringSession(PUB["PAPA_TG_SESSION"]), int(PUB["PAPA_TG_API_ID"]), PUB["PAPA_TG_API_HASH"])
    await acc.connect()
    try:
        for m in await acc.get_messages(Q["chat"], ids=Q["ids"]):
            if not m:
                print("— нет"); continue
            media = type(m.media).__name__ if m.media else "—"
            print(f"{m.id} · {m.date:%d.%m %H:%M} · альбом={m.grouped_id or '—'} · {media} · {(m.message or '').replace(chr(10), ' ')[:90]}")
        if Q.get("search_from"):
            print("== последние посты группы с", Q["search_from"])
            async for m in acc.iter_messages(Q["chat"], min_id=Q["search_from"] - 1, reverse=True, limit=60):
                t = (m.message or "").replace(chr(10), " ")
                if any(w in t.upper() for w in Q.get("words", [])):
                    print(f"{m.id} · {m.date:%d.%m %H:%M} · альбом={m.grouped_id or '—'} · {type(m.media).__name__ if m.media else '—'} · {t[:80]}")
    finally:
        await acc.disconnect()
    print("== GROUP_PEEK_DONE")


asyncio.run(main())
