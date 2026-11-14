"""📰 Агент новостей — сам наполняет банк «СРОЧНО НОВОСТИ» (шаг 2 решения 09.11: «без новостей никуда — 3 раза в день,
всё через банк»; «агент наполняет из надёжных источников + владелец добавляет свои»).

Три раза в день, за ~час до слотов 07:40 / 13:00 / 19:00, профиль Разведки читает НАДЁЖНЫЕ источники — новостные
каналы, которые владелец сам выбрал (⭐ рубрики «news»/«local»), и каналы папок «KATTA DAVRA» / «XOJAOBOD CITY» —
и кладёт в банк ОДНУ лучшую свежую новость: фото/видео с чистым кадром (Gemini) + НАШ текст (узбекская кириллица).
Никогда: политика, криминал, аварии/смерти (грустных новостей нет), реклама, шоу-бизнес.
Если в банке уже лежит свежий пост (владелец бросил свой или агент уже положил) — агент НЕ кладёт: новость владельца главнее.
Сам ничего не публикует: дальше работает прежний порядок — куратор → карточка с 🗑 в пульте → твёрдый слот.
Нет хорошей новости — ничего не кладём, слот пропускается (пустых постов нет)."""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
from pathlib import Path

from . import curate as C
from . import hubs, muhim

BANK = "СРОЧНО НОВОСТИ"
FOLDERS = ("KATTA DAVRA", "PAPA·Давра", "XOJAOBOD CITY", "XOJAOBODCITY", "PAPA·Шаҳар")
CHANNELS = ("davra", "xojaobod")          # банк общий: новость должна подходить обоим каналам (без политики — как в Давре)
PER_DAY = int(os.environ.get("NEWS_PER_DAY", "3"))
HOURS = 6                                  # новость не старше 6 часов
FRESH_BANK_H = 3                           # в банке есть пост моложе 3 ч — слот уже закрыт, не кладём
MIN_AGE_MIN, MIN_VIEWS, MIN_WORDS = 15, 500, 12

PROMPT = """Сен — Telegram-канал муҳарририсан. Янгилик матнини ўқиб, ўзимизнинг қисқа матнимизни ёз:
биринчи қатор — мос эмодзи билан қисқа сарлавҳа (БОШ ҲАРФЛАР), кейин 2–3 қисқа гап: нима бўлди, кимга тегишли, қачондан.
Фақат ўзбек тилида, КИРИЛЛ алифбосида (манба русча ёки лотинча бўлса — таржима қил). Фактлар, рақамлар, саналар,
исмлар ва ташкилот номларини ЎЗГАРТИРМА ва ўзингдан ҳеч нарса қўшма. Бошқа каналлар номи, @юзернейм, ҳавола, хэштег,
реклама, «манба» — ЙЎҚ. Юзернейм ва чақириқни тизим ўзи қўшади. Фақат тайёр матнни қайтар."""


def fits(text: str | None, trusted: bool) -> bool:
    """Новость годится в банк: понятный текст, новость (или из выбранного новостного источника), без грустного и запретного."""
    t = text or ""
    if len(C.WORD.findall(t)) < MIN_WORDS:
        return False
    if muhim.SAD.search(t) or C.POLICY["politics"].search(t) or C.POLICY["crime"].search(t) or C.POLICY["showbiz"].search(t):
        return False
    return trusted or C.is_news(t)


def news_ids(choice: dict | None) -> set[int]:
    """id новостных источников, выбранных владельцем (рубрики news / local) для КАТТА ДАВРА и Хўжаобода."""
    out = set()
    for ch in CHANNELS:
        for code, xs in (((choice or {}).get("channels") or {}).get(ch) or {}).items():
            if code in C.NEWS_CODES:
                out |= {x["id"] for x in xs if x.get("id")}
    return out


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save(data: dict, path: Path) -> None:
    p = path
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)


def sent_today(data: dict, day: str) -> int:
    return int((data.get("sent") or {}).get(day, 0))


def bank_fresh(dates: list[dt.datetime], now: dt.datetime) -> bool:
    return any(d > now - dt.timedelta(hours=FRESH_BANK_H) for d in dates)


async def _bank(client):
    want = hubs._nn(BANK)
    async for d in client.iter_dialogs():
        if d.is_channel and not d.is_group and hubs._nn(d.title) == want:
            return d.entity
    return None


async def run(client, state_dir: Path, now: dt.datetime | None = None, path: Path | None = None, log=print) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    day = (now + dt.timedelta(hours=5)).date().isoformat()
    path = path or state_dir / "news.json"          # папка куратора — профилю Разведки туда можно писать
    data = load(path)
    if sent_today(data, day) >= PER_DAY:
        return {"пропуск": f"лимит дня {PER_DAY} — выполнен"}
    if not os.environ.get("GEMINI_API_KEY"):
        return {"пропуск": "нет ключа Gemini — кадр и текст не проверить"}
    bank = await _bank(client)
    if bank is None:
        return {"ошибка": f"банк «{BANK}» не найден среди чатов профиля Разведки"}
    dates = [m.date async for m in client.iter_messages(bank, limit=5) if not m.action]
    if bank_fresh(dates, now):
        return {"пропуск": f"в банке уже есть свежая новость (моложе {FRESH_BANK_H} ч)"}
    from . import sources
    from telethon.tl.types import PeerChannel
    choice = sources.load_choice()
    trusted = news_ids(choice)
    folders = await C.folder_peers(client)
    peers = C.peers_in(folders, FOLDERS) + [PeerChannel(i) for i in trusted]
    hist = [h for h in (data.get("history") or []) if h.get("ts", "") > (now - dt.timedelta(days=3)).isoformat()]
    since = now - dt.timedelta(hours=HOURS)
    os.environ["GEMINI_MODEL"] = os.environ.get("CURATOR_GEMINI_MODEL", "gemini-flash-lite-latest")
    cands, seen = [], set()
    for p in peers:
        try:
            ent = await client.get_entity(p)
            if ent.id in seen:
                continue
            seen.add(ent.id)
            got = await C.candidates(client, ent, since, now, "davra", log, min_age=MIN_AGE_MIN, min_views=MIN_VIEWS)
            cands += [c for c in got if c["kind"] in ("photo", "video") and fits(c["text"], ent.id in trusted)]
        except Exception as e:  # noqa: BLE001
            log(f"  {type(e).__name__}: {str(e)[:80]}")
        await asyncio.sleep(1)
    report = {"источников": len(seen), "новостей": len(cands), "положено": 0}
    for c in C.pick(cands, 6, hist):
        hist.append({"key": c["key"], "sig": sorted(C.sig(c["text"])), "ts": now.isoformat()})
        try:
            ok = await C.clean_frame(client, c)
        except RuntimeError as e:
            log(f"  проверка кадра: {e}")
            break
        if not ok:                                  # чужое лого / не проверить — не берём (правило владельца)
            continue
        text = hubs.write(c["text"], PROMPT)
        if not text or not fits(text, True):        # ИИ не ответил нашим текстом — чужой текст как есть не кладём
            continue
        msgs = [m for m in await client.get_messages(c["ent"], ids=c["ids"]) if m and getattr(m, "media", None)]
        if not msgs:
            continue
        media = [m.media for m in msgs]
        try:
            try:
                await client.send_file(bank, media if len(media) > 1 else media[0], caption=text)
            except TypeError:                       # Telegram не даёт отправить медиа ссылкой — скачать и залить заново
                blob = await client.download_media(msgs[0], file=bytes)
                await client.send_file(bank, blob, caption=text, supports_streaming=True)
        except Exception as e:  # noqa: BLE001
            report["ошибка"] = f"не смог положить в банк: {type(e).__name__} (профиль Разведки должен быть админом банка)"
            log(f"  📰 {report['ошибка']}")
            break
        data.setdefault("sent", {})
        data["sent"] = {day: sent_today(data, day) + 1}
        report["положено"] = 1
        log(f"  📰 в банк: {c['source']} · {c['views']} просм. · {text[:60]!r}")
        break
    data["history"] = hist[-300:]
    save(data, path)
    log(f"📰 новости: {report}")
    return report
