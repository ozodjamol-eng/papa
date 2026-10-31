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
    "davra": ["Uyda biznes", "Уйда бизнес", "Ayollar uchun biznes", "Аёллар учун бизнес", "Motivatsiya", "Мотивация",
              "O'z ustida ishlash", "Ўз устида ишлаш", "Biznes g'oya", "Бизнес ғоя", "Kulgili videolar", "Qiziqarli videolar",
              "Foydali maslahatlar", "Klip", "Yangi qo'shiqlar"],
}
# 31.10 владелец: «афиша — нам этого не хватает, я работал в этой сфере». Изучение рынка: какие каналы-афиши есть
# по Долине и Узбекистану (концерты, театр, билеты). Для изучения показываем ВСЕ, даже уже лежащие в папках.
QUERIES["afisha"] = ["Afisha", "Афиша", "Andijon afisha", "Андижон афиша", "Farg'ona afisha", "Namangan afisha",
                     "Konsert", "Концерт", "Konsertlar", "Концертлар", "Konsert chiptalari", "Chipta", "Билеты концерт",
                     "Andijon konsert", "Андижон концерт", "Farg'ona konsert", "Namangan konsert", "Teatr Andijon",
                     "Andijon tadbirlar", "Tadbirlar", "Тадбирлар", "Vodiy konsert", "Shou konsert", "Gastrol"]
MIN_SUBS = 20000
MIN_BY = {"afisha": 300}                            # региональные афиши маленькие — смотрим от 300
KEEP_KNOWN = {"afisha"}                             # изучение рынка: известные тоже в списке (с пометкой)
SHOW = 15
SHOW_BY = {"afisha": 40}


def rank(found: list[dict], skip_ids: set[int], skip_names: set[str], min_subs: int = MIN_SUBS,
         show: int = SHOW) -> list[dict]:
    """Без уже известных, только каналы с аудиторией; по подписчикам."""
    out, seen = [], set()
    for c in found:
        if c["id"] in skip_ids or c["id"] in seen or (c.get("username") or "").lower() in skip_names:
            continue
        if not c.get("broadcast") or (c.get("subscribers") or 0) < min_subs:
            continue
        seen.add(c["id"])
        out.append(c)
    return sorted(out, key=lambda c: -(c.get("subscribers") or 0))[:show]


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
    if target in KEEP_KNOWN:
        for c in found:
            c["known"] = c["id"] in known
        known = set()
    return rank(found, known, OWN, MIN_BY.get(target, MIN_SUBS), SHOW_BY.get(target, SHOW))


def render(rows: list[dict]) -> str:
    L = ["🔭 РАЗВЕДЧИК КАНАЛОВ · новые большие каналы (нет в ваших папках)", ""]
    for i, r in enumerate(rows, 1):
        u = "@" + r["username"] if r.get("username") else "без @"
        mark = " · уже в папках" if r.get("known") else ""
        L.append(f"{i}. {r['title'][:40]} ({u}) — {r['subscribers']:,} подп. · поиск «{r['q']}»{mark}".replace(",", " "))
    return "\n".join(L) if rows else "🔭 Новых больших каналов не нашлось."


# ---------- 😂 30.10 владелец: «смех — основа канала; найти много источников приколов, даже международных;
#            изучить, если контент чистый — подключаем» ----------
HUMOR_QUERIES = ["kulgili videolar", "prikol videolar", "кулгили видео", "приколы", "смешные видео", "ржака",
                 "funny videos", "fails", "funny animals", "comedy videos", "memes video", "lol videos", "приколы животные",
                 "смешно до слёз", "funny moments", "hazil"]
HUMOR_MIN_SUBS = 15000
HUMOR_CHECK = 18                      # сколько самых больших проверить по кадрам за раз (лимит Gemini)


async def humor(client, choice: dict | None, log=print) -> dict:
    """Найти каналы приколов → проверить кадры (чужое лого) → чистые подключить в КАТТА ДАВРА (рубрика кулги)."""
    import datetime as dt

    from telethon.tl.functions.contacts import SearchRequest
    from telethon.tl.types import Channel

    from . import sources
    from .curate import OWN, folder_peers
    folders = await folder_peers(client)
    known = {getattr(p, "channel_id", None) for ps in folders.values() for p in ps}
    known |= set(sources.ids_for(choice, "davra"))
    tried = set(((choice or {}).get("auto_seen") or {}).get("davra", [])) | set(((choice or {}).get("humor_tried") or []))
    found = []
    for q in HUMOR_QUERIES:
        try:
            res = await client(SearchRequest(q=q, limit=50))
        except Exception as e:  # noqa: BLE001
            log(f"  «{q}»: {type(e).__name__}")
            await asyncio.sleep(5)
            continue
        for ch in res.chats:
            if isinstance(ch, Channel) and ch.broadcast and ch.username:
                found.append({"id": ch.id, "title": ch.title, "username": ch.username, "broadcast": True,
                              "subscribers": getattr(ch, "participants_count", None), "q": q, "ent": ch})
        await asyncio.sleep(3)
    cands = [c for c in rank(found, known | tried, OWN | sources.BLOCK) if (c.get("subscribers") or 0) >= HUMOR_MIN_SUBS]
    cands = sorted(cands, key=lambda c: -(c["subscribers"] or 0))[:HUMOR_CHECK]
    log(f"кандидатов на проверку: {len(cands)}")
    now = dt.datetime.now(dt.timezone.utc)
    ok, bad = [], []
    for c in cands:
        ent = next((f["ent"] for f in found if f["id"] == c["id"]), None)
        try:
            posts, media = await sources._channel_posts(client, ent, now)
            st = sources.stats(posts, now)
            why = sources.eligible(st)
            if why:
                bad.append((c, why))
                continue
            clean_n, checked = await sources._clean(client, media)
        except RuntimeError as e:                     # лимит Gemini — остальные в следующий раз
            log(f"  кадры: {e}")
            break
        except Exception as e:  # noqa: BLE001
            bad.append((c, type(e).__name__))
            continue
        if checked >= 2 and clean_n == checked:
            ok.append({**c, "median_views": st["median_views"], "per_day": st["per_day"]})
        else:
            bad.append((c, f"чужое лого {checked - clean_n}/{checked}" if checked else "кадры не проверить"))
        await asyncio.sleep(2)
    return {"ok": ok, "bad": bad}


def connect(choice: dict | None, ok: list[dict], bad: list[tuple], now_iso: str) -> dict:
    """Чистые — в выбор КАТТА ДАВРА (кулги), один раз (auto_seen); проверенные грязные — больше не проверяем."""
    import json
    data = json.loads(json.dumps(choice or {}))
    humor_list = data.setdefault("channels", {}).setdefault("davra", {}).setdefault("humor", [])
    seen = data.setdefault("auto_seen", {}).setdefault("davra", [])
    for c in ok:
        if c["id"] not in seen:
            humor_list.append({"id": c["id"], "title": c["title"], "username": c["username"], "found_by": "scout"})
            seen.append(c["id"])
    data.setdefault("humor_tried", [])
    data["humor_tried"] = list(dict.fromkeys(data["humor_tried"] + [c["id"] for c, _ in bad]))[-500:]
    data["version"] = 2
    data["humor_at"] = now_iso
    return data


def render_humor(ok: list[dict], bad: list[tuple]) -> str:
    L = ["😂 РАЗВЕДЧИК ПРИКОЛОВ · подключено в КАТТА ДАВРА (кадры чистые):"]
    L += [f"  ✅ {c['title'][:36]} (@{c['username']}) — {c['subscribers']:,} подп., 👁 {c['median_views']:,}".replace(",", " ")
          for c in ok] or ["  — чистых не нашлось"]
    if bad:
        L.append("Отсеяно:")
        L += [f"  🚫 {c['title'][:30]} (@{c['username']}) — {why}" for c, why in bad[:15]]
    return "\n".join(L)
