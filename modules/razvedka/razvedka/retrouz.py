"""🇺🇿 Архив · сборщик «БАНК · ЎЗБЕК РЕТРО» (12.11.2026, владелец: «пускай архивариус ищет узбекские — они есть и в
Paparazzi, и в Хўжаобод Сити; старые легенды, шлягеры. Пускай собирает узбекский банк»).

Старую музыку из наших каналов архивариус уже сложил в «БАНК · МУСИҚА» (чисто, без чужих лого, с нашим текстом).
Этот сборщик после каждого прохода архивариуса просматривает «БАНК · МУСИҚА» и КОПИРУЕТ старые узбекские шлягеры
в «БАНК · ЎЗБЕК РЕТРО». Ничего не удаляет и не переносит — музыкальные часы каналов не беднеют.
Решает Gemini по подписи (пачка за один запрос, бесплатный лимит); сомнение — не берём.
Прогресс — retro_uz.json (какие посты уже смотрели). Откат: убрать вызов в __main__._archive."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from . import hubgate, hubs, tozalash

SRC, DST = "Jonlik ijrolar", "ЎЗБЕК РЕТРО"
CHECK = 200                    # постов просмотреть за проход
BATCH = 20                     # подписей в одном запросе
TAKE = 40                      # копий в банк за проход
PROMPT = """Ты музыкальный редактор узбекского Telegram-канала. Ниже подписи к музыкальным видео (№ и текст).
Отметь ТОЛЬКО те, где явно СТАРАЯ УЗБЕКСКАЯ песня: шлягер или легенда узбекской эстрады прошлых лет (примерно до 2010 года) —
например Шерали Жўраев, «Ялла», Ботир Зокиров, Юлдуз Усмонова (ранние песни), Насиба Абдуллаева, Ғуломжон Ёқубов,
Охунжон Мадалиев, Ортиқ Отажонов, Муҳриддин Холиқов, Камолиддин Раҳматов, Маҳмуд Намозов, Кумуш Раззоқова, «Болалар»,
«Сетора» и подобные; либо в подписи прямо сказано: ретро, эски қўшиқ, олтин фонд, унутилмас, 80/90-йиллар.
НЕ отмечай: современные песни и премьеры, зарубежную музыку, неизвестных исполнителей, подписи без имени артиста.
Сомневаешься — не отмечай.

{posts}

Ответ только JSON: {{"yes": [номера]}}"""


def parse(r: dict, n: int) -> set[int]:
    out = set()
    for x in (r.get("yes") or []) if isinstance(r, dict) else []:
        try:
            if 1 <= int(x) <= n:
                out.add(int(x))
        except (TypeError, ValueError):
            continue
    return out


def todo(items: list[dict], seen: set[int], limit: int = CHECK) -> list[dict]:
    """Ещё не смотрели, с видео и с подписью; старые первыми."""
    xs = [it for it in items if it["id"] not in seen and (it["text"] or "").strip()
          and any(getattr(m, "video", None) for m in it["msgs"])]
    return sorted(xs, key=lambda x: x["id"])[:limit]


async def run(client, state_dir: Path, log=print, ask=None) -> dict:
    ask = ask or hubgate.ask
    cache: dict = {}
    src, dst = await hubs.entity(client, SRC, cache), await hubs.entity(client, DST, cache)
    if src is None or dst is None:
        return {"пропуск": "нет хаба «БАНК · МУСИҚА» или «БАНК · ЎЗБЕК РЕТРО»"}
    sf = state_dir / "retro_uz.json"
    try:
        st = json.loads(sf.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        st = {}
    seen = set(st.get("seen", []))
    items = todo(await tozalash.scan(client, src), seen)
    looked = copied = 0
    for i in range(0, len(items), BATCH):
        if copied >= TAKE:
            break
        part = items[i:i + BATCH]
        r = await asyncio.to_thread(ask, PROMPT.format(posts="\n".join(f"№{k}. {(it['text'] or '')[:300]}" for k, it in enumerate(part, 1))))
        if not r:                                   # лимит/ошибка ИИ — эту пачку посмотрим в следующий проход
            log("  🇺🇿 нет ответа ИИ — остановка до следующего прохода")
            break
        yes = parse(r, len(part))
        for k, it in enumerate(part, 1):
            if k in yes:
                try:
                    if await hubs.put(client, dst, sorted(it["msgs"], key=lambda x: x.id), it["text"], check=False):
                        copied += 1
                        log(f"  🇺🇿 #{it['id']} → БАНК · ЎЗБЕК РЕТРО: {(it['text'] or '')[:60]!r}")
                        await asyncio.sleep(2)
                except Exception as e:  # noqa: BLE001
                    log(f"  🇺🇿 #{it['id']}: копия не легла ({type(e).__name__})")
                    continue
            seen.add(it["id"])
            looked += 1
        await asyncio.sleep(5)
    st["seen"] = sorted(seen)[-6000:]
    state_dir.mkdir(parents=True, exist_ok=True)
    sf.write_text(json.dumps(st), encoding="utf-8")
    return {"просмотрено": looked, "в узбекский банк": copied, "осталось смотреть": max(0, len(items) - looked)}
