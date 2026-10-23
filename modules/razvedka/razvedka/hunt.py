"""Охотник за утренними видео (для утреннего блока GENPLAN PAPA).

Ищет в каналах-источниках (папки Разведки), в своих каналах и в NEXUS MORNING POOL посты-ВИДЕО
со словами «тонг/tong» («Жума тонги», «Хайрли тонг», «Xayrli tong»…), определяет день недели по тексту,
скачивает лучшие (по просмотрам) в каталог out и пишет index.jsonl.
Только чтение каналов. Текст поста сохраняется лишь как образец стиля для ИИ (не публикуется).
Проверку кадров (даты, чужие логотипы) делает Fabrika (Gemini) при импорте."""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import re
from pathlib import Path

WEEKDAYS = {
    "Душанба": ("душанба", "dushanba"), "Сешанба": ("сешанба", "seshanba"), "Чоршанба": ("чоршанба", "chorshanba"),
    "Пайшанба": ("пайшанба", "payshanba"), "Жума": ("жума", "juma", "жумъа", "jum'a", "jumʼa"),
    "Шанба": ("шанба", "shanba"), "Якшанба": ("якшанба", "yakshanba"),
}
# только поздравление с утром, а не любое «тонгда» в новостях
MORNING = re.compile(r"хайрли\s+тонг|xayrli\s+tong|тонги\s+муборак|tongi\s+muborak|тонгингиз|tongingiz|"
                     r"субҳингиз|хайрли\s+субҳ|good\s+morning|доброе\s+утро", re.I)
QUERIES = ("тонг", "tong")
MAX_BYTES = 20 * 1024 * 1024
PER_DAY = 25            # видео на каждый день недели (23.10: больше запас — без повторов и шаблонов)
ANY = 60                # общие «Хайрли тонг» без дня
POOL_TITLES = ("morning pool",)
FORWARD_MAX = 150      # пересылок в пул за один запуск


def weekday_of(text: str) -> str | None:
    low = (text or "").lower()
    # «шанба» входит в «душанба/якшанба» — сначала длинные
    for name in ("Душанба", "Сешанба", "Чоршанба", "Пайшанба", "Якшанба", "Жума", "Шанба"):
        for v in WEEKDAYS[name]:
            for m in re.finditer(re.escape(v), low):
                if name == "Шанба" and m.start() > 0 and low[m.start() - 1].isalpha():
                    continue
                return name
    return None


def video_meta(m) -> dict | None:
    from telethon.tl.types import DocumentAttributeVideo
    doc = getattr(getattr(m, "media", None), "document", None)
    if not doc or not (doc.mime_type or "").startswith("video"):
        return None
    att = next((a for a in doc.attributes if isinstance(a, DocumentAttributeVideo)), None)
    if not att or getattr(att, "round_message", False):
        return None
    return {"duration": float(att.duration or 0), "w": att.w, "h": att.h, "size": int(doc.size or 0)}


def pick(cands: list[dict]) -> list[dict]:
    """Лучшие по просмотрам: до PER_DAY на день недели и до ANY общих; дубли (размер+длительность) — вон."""
    seen, out, per = set(), [], {}
    for c in sorted(cands, key=lambda c: -(c["views"] or 0)):
        k = (c["size"], round(c["duration"]))
        if k in seen:
            continue
        seen.add(k)
        lim = PER_DAY if c["weekday"] else ANY
        key = c["weekday"] or "any"
        if per.get(key, 0) >= lim:
            continue
        per[key] = per.get(key, 0) + 1
        out.append(c)
    return out


async def hunt(client, cfg: dict, out: Path, days: int = 400, log=print) -> dict:
    from .telegram import TelethonSource
    from telethon.tl.types import InputMessagesFilterVideo
    out.mkdir(parents=True, exist_ok=True)
    src = TelethonSource(client)
    chans = await src.channels(cfg)
    ents = [(c["title"], c["username"], src._entities[c["id"]], False) for c in chans]
    async for d in client.iter_dialogs():
        if d.is_channel and any(t in (d.title or "").lower() for t in POOL_TITLES):
            ents.append((d.title, getattr(d.entity, "username", None), d.entity, True))
            log(f"пул: {d.title}")
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    cands, msgs, where = [], {}, {}
    for title, uname, ent, is_pool in ents:
        n = 0
        # пул — наш собственный утренний склад: берём все видео (подпись может быть пустой); каналы — поиск по «тонг/tong»
        for q in ((None,) if is_pool else QUERIES):
            try:
                async for m in client.iter_messages(ent, search=q, filter=InputMessagesFilterVideo,
                                                    limit=300 if is_pool else 60, wait_time=1):
                    if m.date < since:
                        break
                    text = m.message or ""
                    meta = video_meta(m)
                    if not meta or (not is_pool and not MORNING.search(text)):
                        continue
                    if not (5 <= meta["duration"] <= 90) or meta["size"] > MAX_BYTES:
                        continue
                    key = f"{ent.id}_{m.id}"
                    if key in msgs:
                        continue
                    msgs[key] = m
                    where[key] = ent
                    cands.append({"key": key, "channel": title, "username": uname, "msg_id": m.id,
                                  "date": m.date.isoformat(), "views": m.views or 0, "weekday": weekday_of(text),
                                  "text": text[:1500], **meta})
                    n += 1
            except Exception as e:  # noqa: BLE001 — один канал не должен ронять охоту
                log(f"  {title}: {type(e).__name__}: {str(e)[:120]}")
            await asyncio.sleep(2)
        log(f"{title}: найдено {n}")
    pool = next((e for t, u, e, is_pool in ents if is_pool), None)
    if pool is None:
        raise RuntimeError("не найден канал NEXUS MORNING POOL у этого профиля")
    pool_chat = int(f"-100{pool.id}")
    own = [c for c in cands if where[c["key"]] is pool]
    ext = [c for c in cands if where[c["key"]] is not pool]
    have_sig = {(c["size"], round(c["duration"])) for c in own}
    ext = [c for c in pick(ext) if (c["size"], round(c["duration"])) not in have_sig]
    sent_f = out / "forwarded.json"
    try:
        sent = set(json.loads(sent_f.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        sent = set()
    rows = [{**c, "key": f"pool_{c['msg_id']}", "pool_chat": pool_chat, "source": c["channel"]} for c in own]
    fwd = 0
    for c in ext:
        if c["key"] in sent or fwd >= FORWARD_MAX:
            continue
        try:   # пересылка внутри Telegram, без скачивания; «без автора» — в пуле как свой пост
            res = await client.forward_messages(pool, msgs[c["key"]], from_peer=where[c["key"]], drop_author=True)
            m = res[0] if isinstance(res, list) else res
        except Exception as e:  # noqa: BLE001 — защищённые от пересылки каналы и т.п.
            log(f"  переслать {c['key']}: {type(e).__name__}: {str(e)[:100]}")
            sent.add(c["key"])
            continue
        sent.add(c["key"])
        fwd += 1
        rows.append({**c, "key": f"pool_{m.id}", "msg_id": m.id, "pool_chat": pool_chat, "source": c["channel"]})
        await asyncio.sleep(3)
    sent_f.write_text(json.dumps(sorted(sent)), encoding="utf-8")
    with (out / "index.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps({k: r[k] for k in ("key", "pool_chat", "msg_id", "source", "views", "duration", "date",
                                                  "weekday", "text")}, ensure_ascii=False) + "\n")
    # образцы текста (лучшие утренние подписи) — для тона ИИ, не для публикации
    ex = sorted((c for c in cands if len(c["text"]) > 120), key=lambda c: -(c["views"] or 0))[:40]
    (out / "examples.json").write_text(json.dumps([{"weekday": c["weekday"], "views": c["views"], "text": c["text"]}
                                                    for c in ex], ensure_ascii=False), encoding="utf-8")
    by = {}
    for r in rows:
        by[r["weekday"] or "без дня"] = by.get(r["weekday"] or "без дня", 0) + 1
    return {"channels": len(ents), "found": len(cands), "in_pool": len(own), "forwarded": fwd, "pool_total": len(rows),
            "by_day": by}
