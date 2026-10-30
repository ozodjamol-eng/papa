"""🧹 Самоочистка источников (31.10, план выходных владельца: «источники следят за собой сами»).

Раз в неделю: каждый подключённый источник (choice.json) — живой? Убираем:
- молчит дольше DEAD_DAYS (канал заброшен);
- канал удалён / стал закрытым / @username больше не существует;
- ставит своё лого на видео (куратор поймал дважды — logo_sources в curator.json).
Убранный попадает в auto_seen — ⭐-автоподключение его не вернёт. Список убранных — choice["cleaned"] (видно, что и почему)."""
from __future__ import annotations

import asyncio
import datetime as dt
import json
from pathlib import Path

DEAD_DAYS = 21
GONE = ("ChannelPrivateError", "UsernameNotOccupiedError", "UsernameInvalidError", "ChannelInvalidError")
# ValueError — «нет в кэше» для источника без @username: это не смерть канала, такой не трогаем


def remove(choice: dict, bad: dict[int, str], now: dt.datetime) -> tuple[dict, list[str]]:
    """Убрать источники из всех рубрик всех каналов. bad: id → причина. Возвращает (новый выбор, строки отчёта)."""
    data = json.loads(json.dumps(choice or {}))
    out = []
    for ch, rubs in (data.get("channels") or {}).items():
        for code, xs in list(rubs.items()):
            keep = []
            for x in xs:
                if x["id"] in bad:
                    out.append(f"{ch}: {x.get('title', '')[:30]} — {bad[x['id']]}")
                    data.setdefault("cleaned", []).append({"id": x["id"], "title": x.get("title"), "channel": ch,
                                                           "why": bad[x["id"]], "at": now.date().isoformat()})
                    seen = data.setdefault("auto_seen", {}).setdefault(ch, [])
                    if x["id"] not in seen:
                        seen.append(x["id"])
                else:
                    keep.append(x)
            rubs[code] = keep
    data["cleaned"] = (data.get("cleaned") or [])[-200:]
    return data, out


async def check(client, choice: dict, logo: set[str], now: dt.datetime, log=print) -> dict[int, str]:
    try:
        from telethon.tl.types import PeerChannel
    except ImportError:                                        # тесты без telethon
        PeerChannel = int  # noqa: N806
    bad: dict[int, str] = {}
    seen: set[int] = set()
    for rubs in ((choice or {}).get("channels") or {}).values():
        for xs in rubs.values():
            for x in xs:
                if x["id"] in seen:
                    continue
                seen.add(x["id"])
                u = (x.get("username") or "").lower()
                if u and f"@{u}" in logo:
                    bad[x["id"]] = "ставит своё лого"
                    continue
                try:
                    ent = await client.get_entity(x["username"] if x.get("username") else PeerChannel(x["id"]))
                    last = await client.get_messages(ent, limit=1)
                    if not last or now - last[0].date > dt.timedelta(days=DEAD_DAYS):
                        bad[x["id"]] = f"молчит больше {DEAD_DAYS} дней"
                except Exception as e:  # noqa: BLE001
                    if type(e).__name__ in GONE or (type(e).__name__ == "ValueError" and x.get("username")):
                        bad[x["id"]] = "канал недоступен"
                    else:
                        log(f"  {x.get('title', '')[:30]}: {type(e).__name__} — проверю в следующий раз")
                await asyncio.sleep(1)
    return bad


async def run(client, curator_dir: Path, now: dt.datetime | None = None, log=print) -> str:
    from . import sources
    now = now or dt.datetime.now(dt.timezone.utc)
    choice = sources.load_choice()
    if not choice:
        return "🧹 нет выбора источников"
    try:
        logo = set(json.loads((curator_dir / "curator.json").read_text(encoding="utf-8")).get("logo_sources", []))
    except (OSError, ValueError):
        logo = set()
    bad = await check(client, choice, logo, now, log)
    if not bad:
        return "🧹 Источники: все живые, убирать нечего"
    data, lines = remove(sources.load_choice() or choice, bad, now)
    saved = sources.save_choice(data)
    return f"🧹 Убрал источников: {len(lines)}\n" + "\n".join(lines[:30]) + ("" if saved else "\n⚠️ не сохранилось (права папки)")
