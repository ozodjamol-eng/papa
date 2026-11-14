"""📸 Только чтение: что владелец собрал в «INSTAGRAM · ХАБ» (последние посты) — чтобы понять, какой контент он ищет.
Печатает по посту: дата, вид, длительность, откуда переслано, начало текста; в конце — сводка (@аккаунты, ссылки, хэштеги).
Ничего не публикует, не пересылает и не удаляет."""
import asyncio
import collections
import re
import sys

sys.path.insert(0, "/opt/papa/modules/razvedka")
from razvedka.telegram import client_from_env  # noqa: E402

TITLE = "INSTAGRAM · ХАБ"
LIMIT = 150


def norm(s: str) -> str:
    return re.sub(r"[^\w]+", "", (s or "").lower())


async def main():
    c = client_from_env()
    await c.connect()
    if not await c.is_user_authorized():
        raise SystemExit("NOT_AUTHORIZED")
    try:
        ent = None
        async for d in c.iter_dialogs():
            if d.is_channel and not d.is_group and norm(d.title) == norm(TITLE):
                ent = d.entity
                break
        if ent is None:
            print("канал не найден среди чатов профиля"); return
        ats, tags, links, fwd, days = (collections.Counter() for _ in range(5))
        rows, n_agent, n_own = [], 0, 0
        async for m in c.iter_messages(ent, limit=LIMIT):
            if m.action:
                continue
            t = m.message or ""
            agent = "к обычным" in t and "🔗" in t          # журнал остановленного агента (12.11)
            n_agent += agent; n_own += not agent
            dur = ""
            if m.video and m.file and m.file.duration:
                dur = f"{int(m.file.duration)}с"
            src = ""
            if m.forward:
                ch = getattr(m.forward, "chat", None)
                src = getattr(ch, "title", None) or getattr(ch, "username", None) or (m.forward.from_name or "?")
                fwd[src] += 1
            for a in re.findall(r"@([A-Za-z0-9_.]{3,})", t):
                ats[a.lower()] += 1
            for h in re.findall(r"#(\w{3,})", t):
                tags[h.lower()] += 1
            for u in re.findall(r"instagram\.com/[^\s)]+", t):
                links[u[:60]] += 1
            days[f"{m.date:%d.%m}"] += 1
            kind = "видео" if m.video else ("фото" if m.photo else ("—" if not m.media else type(m.media).__name__))
            rows.append(f"{m.id} · {m.date:%d.%m %H:%M} · {'АГЕНТ' if agent else 'ВЛАДЕЛЕЦ'} · {kind} {dur} · "
                        f"{('⤴ ' + src + ' · ') if src else ''}{t.replace(chr(10), ' / ')[:170]}")
        print(f"== {TITLE}: постов {len(rows)} (владелец {n_own}, агент {n_agent}); по дням: {dict(days)}")
        own = [r for r in rows if "· ВЛАДЕЛЕЦ ·" in r]
        for r in own[:70]:
            print(r)
        print("== откуда переслано:", dict(fwd.most_common(25)))
        print("== @ в текстах:", dict(ats.most_common(40)))
        print("== хэштеги:", dict(tags.most_common(30)))
        print("== ссылки Instagram:", list(links)[:25])
    finally:
        await c.disconnect()
    print("== INSTA_HUB_PEEK_DONE")


asyncio.run(main())
