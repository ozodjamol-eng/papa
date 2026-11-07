"""🔎 07.11 владелец: «в МОТИВАЦИИ 60% — тарбия, и много копий. Что с другими хабами?»

Только чтение. По каждому хабу KATTA BANK: сколько постов, сколько копий (тот же файл видео/фото или тот же текст),
сколько без фото/видео и сколько не по теме хаба (Gemini читает подписи одним запросом на хаб).
Итог — коротко в журнал + полный список номеров в pub/hubaudit.json (для чистки, которую утверждает владелец)."""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import hubs

TOPIC = {
    "РАЗВЛЕКАТЕЛЬНО": "юмор, приколы, смешные и развлекательные видео",
    "ФОЙДАЛИК": "полезные советы, лайфхаки, знания",
    "ФОЙДАЛИК ОВКАТ": "еда, рецепты, польза продуктов, здоровье через питание",
    "МАЪНАВИЯТ": "религия, духовность, нравственность",
    "УЙДА БИЗНЕС": "бизнес из дома, заработок, ремесло, самозанятость",
    "МОТИВАЦИЯ": "мотивация: успех, цели, сила воли, не сдаваться, вдохновение к действию (НЕ воспитание детей, НЕ семейные наставления, НЕ религиозные поучения)",
    "Jonlik ijrolar": "музыка: живое исполнение песен, клипы (только видео)",
    "ИБРАТ": "поучительные жизненные истории с выводом",
    "ТАБРИКЛАР": "поздравления: доброе утро, жума муборак, спокойной ночи",
}


def _n(s: str) -> str:
    return re.sub(r"[\W_]+", "", s or "").casefold()


def media_key(m) -> str:
    d = getattr(m, "document", None)
    if d is not None:
        return f"d{d.id}"
    p = getattr(m, "photo", None)
    if p is not None:
        return f"p{p.id}"
    return ""


def dup_groups(items: list[dict]) -> list[list[int]]:
    """Группы копий: одинаковый файл или одинаковый длинный текст (≥ 80 букв — короткие общие подписи ИИ не в счёт).
    Первый в группе — самый старый (оставить)."""
    parent: dict[int, int] = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            x = parent[x]
        return x

    seen: dict[str, int] = {}
    for it in sorted(items, key=lambda x: x["id"]):
        keys = [k for k in it["media"] if k]
        t = _n(it["text"])[:150]
        if len(t) >= 80:
            keys.append("t" + t)
        for k in keys:
            if k in seen:
                parent[find(it["id"])] = find(seen[k])
            else:
                seen[k] = it["id"]
    groups: dict[int, list[int]] = {}
    for it in items:
        groups.setdefault(find(it["id"]), []).append(it["id"])
    return [sorted(g) for g in groups.values() if len(g) > 1]


PROMPT = """Ниже подписи постов Telegram-хаба «{hub}». Тема хаба: {topic}.
Верни JSON {{"off": [номера постов, которые НЕ по теме хаба], "note": "1 короткая фраза: что чаще всего попадает не туда"}}.
Если подпись пустая или неясная — не считай её «не по теме». Только JSON.

{lines}"""


def ask(prompt: str) -> dict:
    from . import budget
    budget.gate()
    key = os.environ["GEMINI_API_KEY"].strip().strip('"').strip("'")
    base = "http://127.0.0.1:8790" if os.path.exists("/etc/papa-gemini-proxy/on") else "https://generativelanguage.googleapis.com"
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 4096, "responseMimeType": "application/json"}}
    for attempt in range(3):
        req = urllib.request.Request(f"{base}/v1beta/models/gemini-flash-latest:generateContent", data=json.dumps(body).encode(),
                                     headers={"content-type": "application/json", "x-goog-api-key": key})
        try:
            data = json.loads(urllib.request.urlopen(req, timeout=120).read())
            parts = ((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
            raw = "".join(p.get("text", "") for p in parts if not p.get("thought"))
            return json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
        except Exception:  # noqa: BLE001
            time.sleep(30 * (attempt + 1))
    return {}


async def run(client, out: Path, log=print) -> dict:
    want = {_n(h): h for h in hubs.HUBS}
    report, full = {}, {}
    async for d in client.iter_dialogs():
        if not (d.is_channel and not d.is_group and _n(d.title) in want):
            continue
        hub = want[_n(d.title)]
        items, albums = [], {}
        async for m in client.iter_messages(d.entity, limit=2000, wait_time=1):
            if m.action:
                continue
            if m.grouped_id and m.grouped_id in albums:
                a = albums[m.grouped_id]
                a["media"].append(media_key(m))
                a["text"] = a["text"] or (m.message or "")
                a["id"] = min(a["id"], m.id)
                continue
            it = {"id": m.id, "media": [media_key(m)], "text": m.message or "",
                  "video": bool(getattr(m, "video", None))}
            if m.grouped_id:
                albums[m.grouped_id] = it
            items.append(it)
        groups = dup_groups(items)
        extra = [i for g in groups for i in g[1:]]
        bare = [it["id"] for it in items if not any(it["media"])]
        off, note = [], ""
        lines = [(it["id"], (it["text"] or "").strip().replace("\n", " ")[:140]) for it in items if it["text"].strip()]
        if lines and os.environ.get("GEMINI_API_KEY") and hub in TOPIC:
            r = ask(PROMPT.format(hub=hub, topic=TOPIC[hub], lines="\n".join(f"{i}. {t}" for i, t in lines[:400])))
            off = [int(x) for x in r.get("off", []) if str(x).isdigit()]
            note = r.get("note", "")
        n = len(items) or 1
        report[hub] = (f"{len(items)} постов · копий {len(extra)} ({100 * len(extra) // n}%) · без фото/видео {len(bare)}"
                       f" · не по теме {len(off)} ({100 * len(off) // n}%)" + (f" — {note}" if note else ""))
        full[hub] = {"total": len(items), "dups": groups, "extra": extra, "bare": bare, "off": off, "note": note}
        log(f"  {hub}: {report[hub]}")
    out.mkdir(parents=True, exist_ok=True)
    (out / "hubaudit.json").write_text(json.dumps(full, ensure_ascii=False), encoding="utf-8")
    return report


# ---------- 🧹 07.11 владелец: «архивариус пусть сам проверяет — одинаковые пусть удаляет; порядок должен быть» ----------
# После каждого прохода архивариуса (3 раза в день): по каждому хабу
#   1) копии (тот же файл или тот же текст) — УДАЛЯЕМ, оставляем самый старый (разрешение владельца 07.11);
#   2) не по теме — ПЕРЕНОСИМ в свой хаб (Gemini, 1 запрос на хаб); никуда не подходит — в «🗑 КОРЗИНА»;
#   3) без фото/видео, музыка без видео — в «🗑 КОРЗИНА».
# Корзина — закрытый канал, владелец смотрит; старше 7 дней — удаляется сама. Откат: CLEAN = False.
CLEAN = True
TRASH = "🗑 КОРЗИНА"
TRASH_DAYS = 7
MOVE_MAX = 60                      # переносов на хаб за проход (Telegram не любит много сразу)

SORT = """Ниже подписи постов из Telegram-хаба «{hub}» (тема хаба: {topic}).
Другие хабы и их темы:
{hubs}

Найди посты, которые НЕ подходят теме «{hub}». Для каждого укажи хаб, куда он подходит, или "NONE", если никуда.
Пустые и неясные подписи пропускай (не перечисляй). Ответ только JSON: {{"move": {{"<номер>": "<имя хаба или NONE>"}}}}

{lines}"""


async def _trash(client, cache: dict):
    if "trash" not in cache:
        from telethon.tl.functions.channels import CreateChannelRequest
        ent = None
        async for d in client.iter_dialogs():
            if d.is_channel and not d.is_group and _n(d.title) == _n(TRASH):
                ent = d.entity
                break
        if ent is None:
            r = await client(CreateChannelRequest(title=TRASH, about="PAPA — что убрано из хабов (копии/не по теме). Через 7 дней удаляется само.",
                                                  megagroup=False))
            ent = r.chats[0]
        cache["trash"] = ent
    return cache["trash"]


async def _to(client, target, it: dict, check_keys: bool = True) -> bool:
    """Положить пост в target (копия уже там — тоже успех), без проверки темы."""
    from . import hubgate as G
    from . import hubs as H
    msgs = sorted(it["msgs"], key=lambda x: x.id)
    if check_keys and G.keys_of(msgs, it["text"]) & await G.index(client, target):
        return True
    media = [m.media for m in msgs if getattr(m, "media", None)]
    if not media:                                   # голый текст — в корзину текстом
        await client.send_message(target, it["text"] or "(пусто)")
        return True
    return await H.put(client, target, msgs, it["text"], check=False)


async def clean(client, log=print) -> dict:
    import asyncio
    import datetime as dt
    from . import hubgate as G
    from . import hubs as H
    from . import tozalash
    if not CLEAN:
        return {}
    cache: dict = {}
    report: dict[str, str] = {}
    trash = await _trash(client, cache)
    for name in H.HUBS:
        ent = await H.entity(client, name, cache)
        if ent is None:
            continue
        items = await tozalash.scan(client, ent)
        for it in items:
            it["media"] = [G.media_key(m) for m in it["msgs"]]
        by_id = {it["id"]: it for it in items}
        dels = [i for g in dup_groups(items) for i in g[1:]]
        for i in dels:
            await client.delete_messages(ent, [m.id for m in by_id[i]["msgs"]])
            await asyncio.sleep(0.5)
        left = [it for it in items if it["id"] not in set(dels)]
        junk = [it for it in left if not any(it["media"])
                or (name in G.VIDEO_ONLY and not any(getattr(m, "video", None) for m in it["msgs"]))]
        moves: dict[int, str] = {it["id"]: "NONE" for it in junk}
        if name in G.TOPIC and os.environ.get("GEMINI_API_KEY"):
            lines = [(it["id"], it["text"].strip().replace("\n", " ")[:140]) for it in left
                     if it["text"].strip() and it["id"] not in moves]
            if lines:
                others = "\n".join(f"- {h}: {t}" for h, t in G.TOPIC.items() if h != name)
                r = G.ask(SORT.format(hub=name, topic=G.TOPIC[name], hubs=others,
                                      lines="\n".join(f"{i}. {t}" for i, t in lines[:400])))
                for k, v in (r.get("move") or {}).items():
                    if str(k).isdigit() and int(k) in by_id:
                        h = next((x for x in G.TOPIC if _n(x) == _n(str(v))), None)
                        moves[int(k)] = h if h and h != name else "NONE"
        moved, trashed = 0, 0
        G.forget(ent)
        for i, where in list(moves.items())[:MOVE_MAX]:
            it = by_id[i]
            target = trash if where == "NONE" else await H.entity(client, where, cache)
            if target is None:
                continue
            try:
                ok = await _to(client, target, it, check_keys=where != "NONE")
            except Exception as e:  # noqa: BLE001
                log(f"  🧹 {name} #{i}: перенос не вышел ({type(e).__name__}) — оставляю")
                continue
            if not ok:
                continue
            await client.delete_messages(ent, [m.id for m in it["msgs"]])
            trashed += where == "NONE"
            moved += where != "NONE"
            await asyncio.sleep(2)
        if dels or moved or trashed:
            report[name] = f"копий удалено {len(dels)} · перенесено в свой хаб {moved} · в корзину {trashed}"
            log(f"  🧹 {name}: {report[name]}")
    old = []                                          # корзина: старше 7 дней — удаляем
    cut = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=TRASH_DAYS)
    async for m in client.iter_messages(trash, limit=3000):
        if m.date < cut:
            old.append(m.id)
    for k in range(0, len(old), 100):
        await client.delete_messages(trash, old[k:k + 100])
    if old:
        report[TRASH] = f"удалено старше {TRASH_DAYS} дн.: {len(old)}"
    return report
