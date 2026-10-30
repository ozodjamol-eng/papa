"""🔭 Разведчик каналов (30.10, владелец: «пускай агент сам найдёт и расширит поиск»).

Ищет в глобальном поиске Telegram большие каналы по словам темы (для XOJAOBOD RAQIB — Андижон, водий, янгиликлар,
фойдали…), убирает те, что уже есть в папках владельца, и наши. Ничего не подписывает и не пишет — только список
кандидатов (подписчики, тема) для папки-соперника. Владелец добавляет в папку сам."""
from __future__ import annotations

import asyncio

QUERIES = {
    "xojaobod": ["Андижон", "Andijon", "Andijon yangiliklari", "Хўжаобод", "Xo'jaobod", "Асака", "Asaka", "Водий",
                 "Vodiy", "Farg'ona", "Фарғона", "Наманган", "Namangan", "Тезкор хабарлар", "Tezkor xabarlar",
                 "O'zbekiston yangiliklari", "Ўзбекистон янгиликлари", "Фойдали маслаҳатлар", "Foydali maslahatlar",
                 "Соғлом турмуш", "Ish o'rinlari Andijon", "Андижон бозор"],
}
MIN_SUBS = 20000
SHOW = 15


def rank(found: list[dict], skip_ids: set[int], skip_names: set[str]) -> list[dict]:
    """Без уже известных, только каналы с аудиторией; по подписчикам."""
    out, seen = [], set()
    for c in found:
        if c["id"] in skip_ids or c["id"] in seen or (c.get("username") or "").lower() in skip_names:
            continue
        if not c.get("broadcast") or (c.get("subscribers") or 0) < MIN_SUBS:
            continue
        seen.add(c["id"])
        out.append(c)
    return sorted(out, key=lambda c: -(c.get("subscribers") or 0))[:SHOW]


async def run(client, target: str = "xojaobod", log=print) -> list[dict]:
    from telethon.tl.functions.contacts import SearchRequest
    from telethon.tl.types import Channel

    from .curate import OWN, folder_peers
    folders = await folder_peers(client)
    known = set()
    for peers in folders.values():
        for p in peers:
            cid = getattr(p, "channel_id", None)
            if cid:
                known.add(cid)
    found = []
    for q in QUERIES.get(target, []):
        try:
            res = await client(SearchRequest(q=q, limit=50))
        except Exception as e:  # noqa: BLE001
            log(f"  «{q}»: {type(e).__name__}")
            await asyncio.sleep(5)
            continue
        for ch in res.chats:
            if isinstance(ch, Channel):
                found.append({"id": ch.id, "title": ch.title, "username": ch.username, "broadcast": bool(ch.broadcast),
                              "subscribers": getattr(ch, "participants_count", None), "q": q})
        await asyncio.sleep(3)
    return rank(found, known, OWN)


def render(rows: list[dict]) -> str:
    L = ["🔭 РАЗВЕДЧИК КАНАЛОВ · кандидаты в XOJAOBOD RAQIB (нет в ваших папках)", ""]
    for i, r in enumerate(rows, 1):
        u = "@" + r["username"] if r.get("username") else "без @"
        L.append(f"{i}. {r['title'][:40]} ({u}) — {r['subscribers']:,} подп. · поиск «{r['q']}»".replace(",", " "))
    return "\n".join(L) if rows else "🔭 Новых больших каналов не нашлось."
