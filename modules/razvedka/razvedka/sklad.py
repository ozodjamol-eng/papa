"""📦 Склады владельца — доверенный материал (решение владельца 26.10).

Владелец: «у нас есть готовые каналы-хабы, я собирал туда год; оттуда свободно брать, ставить нижний юзер и
публиковать — схему упрощать». Склады — его закрытые каналы: отбор, конкурс по просмотрам и проверка кадров на лого
им НЕ нужны. Каждый запуск куратора (08:00 / 12:30 / 17:00) профиль Разведки пересылает из складов в пульт канала
несколько постов; пульт кладёт их в 📦 запас (config: sklad = …), и пост сам выходит в свободный час сетки —
карточка с 🗑 в пульте даёт вето (выбрано владельцем: «сам по сетке, с вето»).

Правила: только посты с видео/фото (голые ссылки — нет); каждый пост — один раз (журнал used); КАТТА ДАВРА берёт
архив с начала, Хўжаобод — с конца (один пост не выйдет в двух каналах в один день); NEWS INBOX — только посты не
старше 2 дней; КАТТА ДАВРА — без политики. Склад почти пуст (< 10) — одна строка в ШТАБ (пополняет владелец сам).
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import math
import re
from pathlib import Path

from . import curate

TZ = dt.timezone(dt.timedelta(hours=5))
# склад → каким нашим каналам служит (26.10 владелец: «как в плане»)
SKLAD = {
    "NEWS INBOX": ("davra", "xojaobod"),
    "ФОЙДАЛИК": ("davra", "xojaobod"),
    "ФОЙДАЛИК ОВКАТ": ("xojaobod", "davra"),
    "Jonlik ijrolar": ("paparazzi",),
    "РАЗВЛЕКАТЕЛЬНО": ("davra",),
}
FRESH_DAYS = {"NEWS INBOX": 2}                     # старые новости не публикуем
PER_DAY = {"davra": 4, "xojaobod": 3, "paparazzi": 2}
FROM_END = {"xojaobod"}                            # этот канал берёт архив с конца, остальные — с начала
LOW = 10
RUNS = 3                                           # запусков куратора в день


def _norm(s: str) -> str:
    return re.sub(r"[\W_]+", "", str(s or "")).casefold()


def run_no(now: dt.datetime) -> int:
    """Какой это запуск дня (1–3) по местному времени: 08:00 / 12:30 / 17:00."""
    h = now.astimezone(TZ).hour
    return 1 if h < 10 else (2 if h < 15 else 3)


def allowed_now(channel: str, sent_today: int, now: dt.datetime) -> int:
    """Сколько можно переслать сейчас: дневная норма делится на 3 запуска (Давра 4 → 2+1+1)."""
    n = PER_DAY.get(channel, 0)
    return max(0, min(n - sent_today, math.ceil(n * run_no(now) / RUNS) - sent_today))


def eligible(item: dict, stash: str, channel: str, now: dt.datetime) -> bool:
    """Пост склада годится для канала: с медиа, не реклама, свежий (для NEWS INBOX), по политике канала."""
    if item["kind"] not in ("video", "photo") or item["ad"]:
        return False
    days = FRESH_DAYS.get(stash)
    if days and item["date"] < now - dt.timedelta(days=days):
        return False
    return not curate.off_policy(item["text"], channel)


def order(items: list[dict], channel: str) -> list[dict]:
    return sorted(items, key=lambda x: x["id"], reverse=channel in FROM_END)


def plan(stashes: dict[str, list[dict]], used: dict, sent_today: dict, now: dt.datetime) -> dict[str, list[tuple]]:
    """Что переслать: канал → [(склад, пост)]. Склады канала — по кругу; один пост — один раз на канал."""
    out: dict[str, list[tuple]] = {}
    for ch in PER_DAY:
        n = allowed_now(ch, sent_today.get(ch, 0), now)
        mine = [s for s, chs in SKLAD.items() if ch in chs and s in stashes]
        queues = [[(s, x) for x in order(stashes[s], ch) if eligible(x, s, ch, now)
                   and str(x["id"]) not in used.get(f"{ch}|{s}", [])] for s in mine]
        start = int(sent_today.get(f"rr_{ch}", 0))           # с какого склада начинать круг
        queues = queues[start % len(queues):] + queues[:start % len(queues)] if queues else []
        pick: list[tuple] = []
        while len(pick) < n and any(queues):
            for q in queues:
                if q and len(pick) < n:
                    pick.append(q.pop(0))
        out[ch] = pick
    return out


def left(stashes: dict[str, list[dict]], used: dict, now: dt.datetime) -> dict[str, int]:
    """Сколько годного осталось в складе (по самому «голодному» каналу)."""
    res = {}
    for s, items in stashes.items():
        res[s] = min(sum(1 for x in items if eligible(x, s, ch, now) and str(x["id"]) not in used.get(f"{ch}|{s}", []))
                     for ch in SKLAD[s])
    return res


# ---------- Telegram ----------
async def find(client) -> dict[str, object]:
    """Склады среди чатов профиля по названию (регистр, эмодзи и пробелы не важны)."""
    want = {_norm(k): k for k in SKLAD}
    out = {}
    async for d in client.iter_dialogs():
        if d.is_channel and not d.is_group and _norm(d.title) in want and want[_norm(d.title)] not in out:
            out[want[_norm(d.title)]] = d.entity
    return out


async def read(client, ent, limit: int = 3000) -> list[dict]:
    """Весь архив склада: пост (альбом — одним) → id первой части, все id, вид, текст, реклама, дата."""
    items, groups = [], {}
    async for m in client.iter_messages(ent, limit=limit, wait_time=1):
        if m.action:
            continue
        k = curate.kind(m)
        if m.grouped_id:
            g = groups.get(m.grouped_id)
            if g:
                g["ids"].append(m.id)
                g["id"] = min(g["id"], m.id)
                g["text"] = g["text"] or (m.message or "")
                g["kind"] = g["kind"] or k
                continue
        text = m.message or ""
        it = {"id": m.id, "ids": [m.id], "kind": k, "text": text, "date": m.date,
              "ad": curate.is_ad(text, bool(getattr(m, "reply_markup", None)))}
        if m.grouped_id:
            groups[m.grouped_id] = it
        items.append(it)
    for it in items:
        it["ids"].sort()
    return items


async def run(client, state_dir: Path, now: dt.datetime | None = None, log=print, notify=None) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    state_dir.mkdir(parents=True, exist_ok=True)
    sf = state_dir / "sklad.json"
    try:
        st = json.loads(sf.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        st = {}
    today = now.astimezone(TZ).date().isoformat()
    if st.get("day") != today:
        st["day"], st["sent"] = today, {k: v for k, v in (st.get("sent") or {}).items() if k.startswith("rr_")}
    used = st.setdefault("used", {})
    ents = await find(client)
    if not ents:
        return {"склады": "не найдены среди чатов профиля Разведки"}
    stashes = {}
    for name, ent in ents.items():
        try:
            stashes[name] = await read(client, ent)
        except Exception as e:  # noqa: BLE001 — один склад не роняет остальные
            log(f"  склад {name}: {type(e).__name__}")
        await asyncio.sleep(1)
    routes = dict(curate.BOTS)
    report = {"найдено": sorted(ents)}
    for ch, picks in plan(stashes, used, st["sent"], now).items():
        if ch == "xojaobod" and not curate.XOJAOBOD_FLAG.exists():
            continue                                    # группа ещё не на PAPA — её бот не трогаем
        sent = 0
        for stash, it in picks:
            try:                                        # подпись источника = название склада → пульт кладёт в 📦 запас
                await client.forward_messages(routes[ch], it["ids"], from_peer=ents[stash])
            except Exception as e:  # noqa: BLE001
                log(f"  склад → {ch}: {type(e).__name__}")
                continue
            used.setdefault(f"{ch}|{stash}", []).append(str(it["id"]))
            sent += 1
            log(f"  📦 {stash} → {ch}: #{it['id']} {it['text'][:50]!r}")
            await asyncio.sleep(4)
        st["sent"][ch] = st["sent"].get(ch, 0) + sent
        st["sent"][f"rr_{ch}"] = int(st["sent"].get(f"rr_{ch}", 0)) + sent
        report[ch] = sent
    rest = left(stashes, used, now)
    report["осталось"] = rest
    low = [f"{s}: {n}" for s, n in rest.items() if n < LOW and s not in FRESH_DAYS]
    if low and notify and st.get("low_day") != today:
        st["low_day"] = today
        await notify("📦 Склад почти пуст — " + ", ".join(low) + ". Пополните, когда будет время.")
    sf.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    return report
