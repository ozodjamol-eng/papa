"""🧹 Отдел Архив · «Тозаловчи» (06.11, владелец: «архивариус пусть прочистит все папки, найдёт такие вещи…
это должно различаться; если надо — сделаем ещё папки»).

Проходит хабы KATTA BANK (вечные направления: МАЪНАВИЯТ, ФОЙДАЛИК, РАЗВЛЕКАТЕЛЬНО…), находит посты,
привязанные ко времени («Хайрли тонг», «Жума муборак», «Хайрли тун») и ПЕРЕНОСИТ их в хаб «ТАБРИКЛАР»:
сначала копия туда, и только если копия легла — удаляем пост из хаба направления. Ничего не теряется.
Без ИИ (правило timing.kind) — бесплатно и без лимита Gemini. Прогресс не нужен: каждый раз смотрим последние SCAN."""
from __future__ import annotations

import asyncio

from . import hubs, timing

SCAN = 3000                    # постов на хаб за проход (хабы небольшие — фактически весь хаб)


def pick(items: list[dict]) -> list[dict]:
    """Какие посты хаба — поздравления по времени (альбом — целиком)."""
    return [it for it in items if timing.kind(it["text"]) or any(timing.kind(m.message or "") for m in it["msgs"])]


async def scan(client, ent) -> list[dict]:
    items, groups = [], {}
    async for m in client.iter_messages(ent, limit=SCAN, wait_time=1):
        if m.action:
            continue
        if m.grouped_id and m.grouped_id in groups:
            g = groups[m.grouped_id]
            g["msgs"].append(m)
            g["text"] = g["text"] or (m.message or "")
            continue
        it = {"id": m.id, "msgs": [m], "text": m.message or ""}
        if m.grouped_id:
            groups[m.grouped_id] = it
        items.append(it)
    return items


async def run(client, log=print, move: bool = True) -> dict:
    cache: dict = {}
    tab = await hubs.entity(client, timing.HUB, cache)
    if tab is None:
        return {"ошибка": "нет хаба ТАБРИКЛАР"}
    report: dict[str, dict] = {}
    for name in hubs.HUBS:
        if name == timing.HUB:
            continue
        try:
            ent = await hubs.entity(client, name, cache)
        except Exception as e:  # noqa: BLE001
            report[name] = {"ошибка": type(e).__name__}
            continue
        if ent is None:
            continue
        hits = pick(await scan(client, ent))
        moved, kept = 0, 0
        per: dict[str, int] = {}
        for it in sorted(hits, key=lambda x: x["id"]):           # старые первыми — порядок в ТАБРИКЛАР сохраняется
            k = timing.kind(it["text"]) or next(timing.kind(m.message or "") for m in it["msgs"] if timing.kind(m.message or ""))
            per[timing.NAMES[k]] = per.get(timing.NAMES[k], 0) + 1
            if not move:
                continue
            msgs = sorted(it["msgs"], key=lambda x: x.id)
            try:
                ok = await hubs.put(client, tab, msgs, it["text"])
            except Exception as e:  # noqa: BLE001
                log(f"  🧹 {name} #{it['id']}: копия не легла ({type(e).__name__}) — оставляю на месте")
                ok = False
            if not ok:
                kept += 1
                continue
            await client.delete_messages(ent, [m.id for m in msgs])
            moved += 1
            log(f"  🧹 {name} #{it['id']} ({timing.NAMES[k]}) → {timing.HUB}")
            await asyncio.sleep(2)
        if hits:
            report[name] = {"найдено": len(hits), "перенесено": moved, "оставлено": kept, "по видам": per}
    return report
