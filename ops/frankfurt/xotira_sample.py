"""Только чтение: образцы подписей постов канала ХОТИРА — понять форматы для проверки повторов."""
import asyncio
import collections
import os
import re
import sys

sys.path.insert(0, "/opt/papa/modules/razvedka")
from razvedka.telegram import client_from_env  # noqa: E402

CH = os.environ.get("XOTIRA_CHANNEL", "@XOTIRAXOJAOBOD").lstrip("@")


async def main():
    c = client_from_env()
    await c.connect()
    kinds = collections.Counter()
    samples = []
    i = 0
    async for m in c.iter_messages(CH):
        i += 1
        t = (m.message or "").strip()
        k = ("фото" if m.photo else "видео" if m.video else "альбом" if m.grouped_id else "медиа" if m.media else "текст")
        kinds[k + (" с текстом" if t else " без текста")] += 1
        if t and (i % 25 == 1 or len(samples) < 12):
            samples.append(f"#{m.id} {m.date:%Y-%m-%d} [{k}] " + re.sub(r"\s+", " ⏎ ", t)[:260])
    await c.disconnect()
    print("ВИДЫ:", dict(kinds))
    print("\n".join(samples[:45]))


asyncio.run(main())
