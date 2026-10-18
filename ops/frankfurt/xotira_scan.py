"""Загрузка истории канала ХОТИРА (@XOTIRAXOJAOBOD) в базу повторов бота — профилем Разведки (только чтение канала)."""
import asyncio
import os
import sys

sys.path.insert(0, "/opt/papa/modules/razvedka")
sys.path.insert(0, "/opt/papa/modules/xotira")
from razvedka.telegram import client_from_env  # noqa: E402
from xotira import bot as B  # noqa: E402

CH = os.environ.get("XOTIRA_CHANNEL", "@XOTIRAXOJAOBOD").lstrip("@")
DB = os.environ.get("XOTIRA_DB", "/var/lib/papa-xotira/xotira.sqlite3")


async def main():
    c = client_from_env()
    await c.connect()
    if not await c.is_user_authorized():
        raise SystemExit("NOT_AUTHORIZED")
    db = B.connect(DB)
    posts = people = empty = 0
    try:
        async for m in c.iter_messages(CH):
            posts += 1
            n = B.index_post(db, m.id, m.message or "", m.date.isoformat() if m.date else None)
            people += n
            empty += not n
    finally:
        await c.disconnect()
    total = db.execute("SELECT COUNT(DISTINCT msg_id), COUNT(*) FROM posts").fetchone()
    print(f"постов в канале: {posts} · людей найдено: {people} · без имени/годов (не проверить): {empty}")
    print(f"в базе повторов: {total[0]} постов, {total[1]} записей")
    rows = db.execute("SELECT name, born, died FROM posts ORDER BY msg_id DESC LIMIT 3").fetchall()
    print("последние:", "; ".join(f"{r[0]} {r[1]}-{r[2]}" for r in rows))


asyncio.run(main())
