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
PER_DAY = 14            # видео на каждый день недели
ANY = 24                # общие «Хайрли тонг» без дня
POOL_TITLES = ("morning pool",)


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


async def _download(client, m, ent, path: Path, log=print) -> bool:
    """Скачать видео; при ошибке — повтор со свежим сообщением (у старых ссылок на файл истекает срок)."""
    for attempt in range(2):
        try:
            if attempt:
                m = await client.get_messages(ent, ids=m.id)
            res = await client.download_media(m.media.document if attempt else m, file=str(path))
            if res and path.exists() and path.stat().st_size > 10_000:
                return True
            if res and Path(res).exists() and Path(res) != path:      # библиотека сохранила под своим именем
                Path(res).replace(path)
                return True
        except Exception as e:  # noqa: BLE001
            log(f"  скачать {ent.id}_{m.id} (попытка {attempt + 1}): {type(e).__name__}: {str(e)[:150]}")
        await asyncio.sleep(2)
    path.unlink(missing_ok=True)
    return False


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
    chosen = pick(cands)
    idx = out / "index.jsonl"
    have = set()
    if idx.exists():
        have = {json.loads(ln)["key"] for ln in idx.read_text(encoding="utf-8").splitlines() if ln.strip()}
    got = 0
    with idx.open("a", encoding="utf-8") as f:
        for c in chosen:
            if c["key"] in have:
                continue
            path = out / f"{c['key']}.mp4"
            ok = await _download(client, msgs[c["key"]], where[c["key"]], path, log)
            if not ok:
                continue
            c["file"] = path.name
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
            got += 1
            await asyncio.sleep(1)
    # образцы текста (лучшие утренние подписи) — для тона ИИ, не для публикации
    ex = sorted((c for c in cands if len(c["text"]) > 120), key=lambda c: -(c["views"] or 0))[:40]
    (out / "examples.json").write_text(json.dumps([{"weekday": c["weekday"], "views": c["views"], "text": c["text"]}
                                                    for c in ex], ensure_ascii=False), encoding="utf-8")
    by = {}
    for c in chosen:
        by[c["weekday"] or "без дня"] = by.get(c["weekday"] or "без дня", 0) + 1
    return {"channels": len(ents), "found": len(cands), "chosen": len(chosen), "downloaded": got, "by_day": by}
