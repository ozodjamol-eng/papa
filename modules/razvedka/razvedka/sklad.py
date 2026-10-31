"""📦 Склады владельца — доверенный материал (решение владельца 26.10).

Владелец: «у нас есть готовые каналы-хабы, я собирал туда год; оттуда свободно брать, ставить нижний юзер и
публиковать — схему упрощать». Склады — его закрытые каналы: отбор, конкурс по просмотрам и проверка кадров на лого
им не нужны, НО проверка кадров на чужое лого — нужна всем (31.10, кроме Муфтия). Полный проход куратора в 08, 12 и 17 ч, якорь — каждый час 07–20 (30.10), профиль Разведки пересылает из складов в пульт канала
несколько постов (ФОЙДАЛИК — закреплённая норма FIXED, остальные склады — по кругу PER_DAY); пульт кладёт их в 📦 запас (config: sklad = …), и пост сам выходит в свободный час сетки —
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
import os
import re
from pathlib import Path

from . import curate

TZ = dt.timezone(dt.timedelta(hours=5))
# склад → каким нашим каналам служит (26.10 владелец: «как в плане»)
SKLAD = {
    "NEWS INBOX": ("xojaobod",),                   # 30.10 владелец: в КАТТА ДАВРА новостей минимум
    "@shayx_nuriddinxoliqnazar": ("davra", "xojaobod"),   # 30.10: «закончить день с муфтием» — якорь 22:00
    "ФОЙДАЛИК": ("davra", "xojaobod", "paparazzi"),   # 26.10 владелец: «там очень много полезного — во все три»
    "ФОЙДАЛИК ОВКАТ": ("xojaobod", "davra"),
    "Jonlik ijrolar": ("paparazzi", "davra"),          # 30.10: хаб музыки — и для КАТТА ДАВРА (музыка ×3)
    "УЙДА БИЗНЕС": ("davra", "xojaobod"),               # 30.10: хабы направлений (агенты кладут сами)
    "МОТИВАЦИЯ": ("davra",),
    "ИБРАТ": ("davra", "xojaobod"),
    "РАЗВЛЕКАТЕЛЬНО": ("davra", "xojaobod", "paparazzi"),   # 26.10 владелец: склад юмора — для всех трёх
    # склады под пустые рубрики — подключатся, когда владелец назовёт свои каналы
    "МАЪНАВИЯТ": ("xojaobod", "davra"),
    "РЕТРО КЛИПЛАР": ("paparazzi",),
    # 26.10 владелец: чужие каналы со старым материалом («@» = публичный). Не доверенные — КАЖДЫЙ пост перед
    # отправкой проверяется на чужое лого (Gemini); с лого — пропуск навсегда. ShohonaKulgu — в блоке (своё лого).
    "@AbduraxmonQiziq": ("davra", "xojaobod", "paparazzi"),
    "@sanatdunyosi": ("paparazzi",),
    "@madaniyat_marifat_tv": ("paparazzi",),
    "@madaniyatvazirligi": ("paparazzi",),
    "@RizaNovaUZ": ("paparazzi",),                  # 31.10 владелец: музыкальный лейбл, клипы; лого — проверка кадров
}
TRUSTED_EXT = {"@shayx_nuriddinxoliqnazar"}       # 30.10 владелец: Муфтий — без проверки лого (его подпись допустима)
NEWEST_FIRST = {"@shayx_nuriddinxoliqnazar"}      # якорь: сначала свежий пост, нет нового — следующий из архива
# 31.10 владелец: «в обоих каналах должен идти Муфтий, но разными постами». Склад Муфтия — один урок на ОДИН канал:
# пост, который уже взял другой канал (по id или по тому же тексту — Муфтий повторяет уроки), не берём; и только уроки
# (#muftiy_minbari) — поздравления (#tabrik) и #kun_oyati в слот 22:00 не годятся. Откат: очистить оба множества.
UNIQUE = {"@shayx_nuriddinxoliqnazar"}
LESSON_ONLY = {"@shayx_nuriddinxoliqnazar"}
FRESH_DAYS = {"NEWS INBOX": 2, "@madaniyatvazirligi": 2}   # новости: только свежие, архив не берём
# 26.10 владелец: ФОЙДАЛИК — ровно 3 в день в КАТТА ДАВРА и Хўжаобод, 2 — в PaparazziUZ (сверх остальных складов)
# 30.10 сверка: часы Давры «час = рубрика» — мотивация 07/20, музыка 12/15/21, бизнес 11, ибрат 19 — свои нормы
FIXED = {"davra": {"@shayx_nuriddinxoliqnazar": 1, "ФОЙДАЛИК": 3, "РАЗВЛЕКАТЕЛЬНО": 2, "@AbduraxmonQiziq": 1,
                   "МОТИВАЦИЯ": 2, "Jonlik ijrolar": 3, "УЙДА БИЗНЕС": 1, "ИБРАТ": 1},
         "xojaobod": {"@shayx_nuriddinxoliqnazar": 1, "ФОЙДАЛИК": 3, "РАЗВЛЕКАТЕЛЬНО": 1, "МАЪНАВИЯТ": 1, "@AbduraxmonQiziq": 1},
         "paparazzi": {"ФОЙДАЛИК": 2, "Jonlik ijrolar": 2, "РАЗВЛЕКАТЕЛЬНО": 2, "РЕТРО КЛИПЛАР": 4,
                       "@AbduraxmonQiziq": 1, "@sanatdunyosi": 2, "@madaniyat_marifat_tv": 2, "@madaniyatvazirligi": 1, "@RizaNovaUZ": 2}}
FRIDAY = {("xojaobod", "МАЪНАВИЯТ"): 3}                    # в пятницу маънавият — 3
# вечный склад: пост со словами «сегодня/вчера/в этом году», годом или датой — устарел, не берём
STALE = re.compile(r"(?<![\w'])(?:бугун|кеча|эртага|шу\s+йил|bugun|kecha|ertaga|shu\s+yil|сегодня|вчера|завтра)(?![\w'])"
                   r"|(?<!\d)20[12]\d(?!\d)|(?<!\d)\d{1,2}[./]\d{1,2}[./]\d{2,4}(?!\d)", re.I)
JUMA = re.compile(r"жума|juma|jum'a|пятниц", re.I)
PER_DAY = {"davra": 3, "xojaobod": 2, "paparazzi": 0}      # остальные склады канала — по кругу
FROM_END = {"xojaobod"}                            # этот канал берёт архив с конца
FROM_MIDDLE = {"paparazzi"}                        # этот — с середины (не повторяет Давру); остальные — с начала
LOW = 10
RUNS = 3                                           # запусков куратора в день


def external(stash: str) -> bool:
    return stash.startswith("@")


def needs_check(stash: str) -> bool:
    """31.10 владелец («не работает протокол»): в Хўжаобод вышло видео ФОЙДАЛИК с чужим @OPER_UZ.
    Правило «только чистое, без чужого лого» — для ВСЕХ складов, свои тоже. Без проверки лого — только Муфтий."""
    return stash not in TRUSTED_EXT


def _norm(s: str) -> str:
    return re.sub(r"[\W_]+", "", str(s or "")).casefold()


def text_key(text: str) -> str:
    """Отпечаток урока по тексту (первые 120 букв без знаков) — один урок Муфтий выкладывает несколько раз."""
    return _norm(text)[:120]


def taken(used: dict, stash: str, channel: str, item: dict) -> bool:
    """31.10: склад UNIQUE — урок уже взял любой канал (тот же id у другого канала или тот же текст где угодно)."""
    if stash not in UNIQUE:
        return False
    if any(str(item["id"]) in used.get(f"{c}|{stash}", []) for c in SKLAD.get(stash, ()) if c != channel):
        return True
    k = text_key(item.get("text") or "")
    return bool(k) and k in used.get(f"txt|{stash}", [])


def mark_used(used: dict, stash: str, channel: str, item: dict) -> None:
    used.setdefault(f"{channel}|{stash}", []).append(str(item["id"]))
    if stash in UNIQUE and text_key(item.get("text") or ""):
        used.setdefault(f"txt|{stash}", []).append(text_key(item.get("text") or ""))


def run_no(now: dt.datetime) -> int:
    """Какой это запуск дня (1–3) по местному времени: 08:00 / 12:30 / 17:00."""
    h = now.astimezone(TZ).hour
    return 1 if h < 10 else (2 if h < 15 else 3)


def allowed(n: int, sent: int, now: dt.datetime) -> int:
    """Сколько можно переслать сейчас: дневная норма делится на 3 запуска (3 → 1+1+1, 4 → 2+1+1)."""
    return max(0, min(n - sent, math.ceil(n * run_no(now) / RUNS) - sent))


def allowed_now(channel: str, sent_today: int, now: dt.datetime) -> int:
    return allowed(PER_DAY.get(channel, 0), sent_today, now)


def eligible(item: dict, stash: str, channel: str, now: dt.datetime) -> bool:
    """Пост склада годится для канала: с медиа, не реклама, свежий (для NEWS INBOX), по политике канала."""
    if item["kind"] not in ("video", "photo") or item["ad"]:
        return False
    if stash in LESSON_ONLY and not re.search(r"minbar|минбар", _norm(item["text"])):
        return False                                   # 31.10: в слот Муфтия — только уроки с минбара
    days = FRESH_DAYS.get(stash)
    if days and item["date"] < now - dt.timedelta(days=days):
        return False
    if not days and STALE.search(item["text"] or ""):
        return False                                   # «бугун», «шу йил», дата — для вечного склада устарел
    if JUMA.search(item["text"] or "") and now.astimezone(TZ).weekday() != 4:
        return False                                   # «Жума» — только в пятницу
    return not curate.off_policy(item["text"], channel)


def order(items: list[dict], channel: str, now: dt.datetime | None = None, stash: str = "") -> list[dict]:
    xs = sorted(items, key=lambda x: x["id"], reverse=channel in FROM_END or stash in NEWEST_FIRST)
    if channel in FROM_MIDDLE:
        xs = xs[len(xs) // 2:] + xs[:len(xs) // 2]
    if now is not None and now.astimezone(TZ).weekday() == 4:   # пятница: «Жума» — первыми
        xs = sorted(xs, key=lambda x: not JUMA.search(x.get("text") or ""))
    return xs


def plan(stashes: dict[str, list[dict]], used: dict, sent_today: dict, now: dt.datetime) -> dict[str, list[tuple]]:
    """Что переслать: канал → [(склад, пост, счётчик)]. Закреплённые склады — своя норма; остальные — по кругу.
    Один пост — один раз на канал."""
    out: dict[str, list[tuple]] = {}
    fresh = lambda ch, s: [x for x in order(stashes[s], ch, now) if eligible(x, s, ch, now)
                           and str(x["id"]) not in used.get(f"{ch}|{s}", [])
                           and str(x["id"]) not in used.get(f"bad|{s}", []) and not taken(used, s, ch, x)]
    for ch in PER_DAY:
        pick: list[tuple] = []
        for s, n in FIXED.get(ch, {}).items():
            if now.astimezone(TZ).weekday() == 4:
                n = FRIDAY.get((ch, s), n)
            if s in stashes and ch in SKLAD.get(s, ()):
                k = allowed(n, int(sent_today.get(f"{ch}|{s}", 0)), now)
                pick += [(s, x, f"{ch}|{s}") for x in fresh(ch, s)[:k]]
        n = allowed_now(ch, int(sent_today.get(ch, 0)), now)
        mine = [s for s, chs in SKLAD.items() if ch in chs and s in stashes and s not in FIXED.get(ch, {})]
        queues = [[(s, x, ch) for x in fresh(ch, s)] for s in mine]
        start = int(sent_today.get(f"rr_{ch}", 0))           # с какого склада начинать круг
        queues = queues[start % len(queues):] + queues[:start % len(queues)] if queues else []
        rr: list[tuple] = []
        while len(rr) < n and any(queues):
            for q in queues:
                if q and len(rr) < n:
                    rr.append(q.pop(0))
        out[ch] = pick + rr
    return out


def left(stashes: dict[str, list[dict]], used: dict, now: dt.datetime) -> dict[str, int]:
    """Сколько годного осталось в складе (по самому «голодному» каналу)."""
    res = {}
    for s, items in stashes.items():
        res[s] = min(sum(1 for x in items if eligible(x, s, ch, now) and str(x["id"]) not in used.get(f"{ch}|{s}", []))
                     for ch in SKLAD[s])
    return res


# ---------- Telegram ----------
async def find(client, log=print) -> dict[str, object]:
    """Свои склады — среди чатов профиля по названию (регистр, эмодзи, пробелы не важны); чужие (@) — по username."""
    want = {_norm(k): k for k in SKLAD if not external(k)}
    out = {}
    async for d in client.iter_dialogs():
        if d.is_channel and not d.is_group and _norm(d.title) in want and want[_norm(d.title)] not in out:
            out[want[_norm(d.title)]] = d.entity
    for k in SKLAD:
        if external(k):
            try:
                out[k] = await client.get_entity(k[1:])
            except Exception as e:  # noqa: BLE001
                log(f"  чужой архив {k}: {type(e).__name__}")
            await asyncio.sleep(1)
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
        it = {"id": m.id, "ids": [m.id], "kind": k, "text": text, "date": m.date, "msg": m,
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
    ents = await find(client, log)
    if not ents:
        return {"склады": "не найдены среди чатов профиля Разведки"}
    stashes = {}
    for name, ent in ents.items():
        try:
            stashes[name] = await read(client, ent, 1500 if external(name) else 3000)
        except Exception as e:  # noqa: BLE001 — один склад не роняет остальные
            log(f"  склад {name}: {type(e).__name__}")
        await asyncio.sleep(1)
    routes = dict(curate.BOTS)
    report = {"найдено": sorted(ents)}
    import os
    gemini_ok = bool(os.environ.get("GEMINI_API_KEY"))
    for ch, picks in plan(stashes, used, st["sent"], now).items():
        if ch == "xojaobod" and not curate.XOJAOBOD_FLAG.exists():
            continue                                    # группа ещё не на PAPA — её бот не трогаем
        sent = 0
        for stash, it, key in picks:
            if needs_check(stash):                     # 31.10: кадр — на чужое лого перед КАЖДОЙ отправкой (и свои склады)
                if not gemini_ok:
                    continue
                try:
                    ok = await curate.clean_frame(client, {"kind": it["kind"], "msg": it["msg"]}, background=False)
                except RuntimeError as e:               # лимит Gemini — остальные в следующий раз (без проверки не шлём)
                    log(f"  склад: {e}")
                    gemini_ok = False
                    continue
                if ok is None:
                    continue
                if not ok:
                    used.setdefault(f"bad|{stash}", []).append(str(it["id"]))
                    log(f"  🚫 {stash} #{it['id']}: чужое лого — пропуск навсегда")
                    continue
            try:                                        # подпись источника = название склада → пульт кладёт в 📦 запас
                await client.forward_messages(routes[ch], it["ids"], from_peer=ents[stash])
            except Exception as e:  # noqa: BLE001
                log(f"  склад → {ch}: {type(e).__name__}")
                continue
            mark_used(used, stash, ch, it)
            st["sent"][key] = int(st["sent"].get(key, 0)) + 1
            if key == ch:
                st["sent"][f"rr_{ch}"] = int(st["sent"].get(f"rr_{ch}", 0)) + 1
            sent += 1
            log(f"  📦 {stash} → {ch}: #{it['id']} {it['text'][:50]!r}")
            await asyncio.sleep(4)
        report[ch] = sent
    rest = left(stashes, used, now)
    report["осталось"] = rest
    low = [(s, n) for s, n in rest.items() if n < LOW and s not in FRESH_DAYS and not external(s)]
    if low and notify and st.get("low_day") != today:
        st["low_day"] = today
        for s, n in low:                              # в пульт основного канала склада (первый в SKLAD)
            await notify(f"📦 Склад «{s}» почти пуст: осталось {n}. Пополните, когда будет время.", SKLAD[s][0])
    sf.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    return report


# ---------- ⚓ 30.10: якорь — пустой час скоро, свежего нет → из архива-склада этой рубрики ----------
FULL_HOURS = {8, 12, 17}                           # полный проход складов (нормы дня) — как раньше, 3 раза в день
ANCHOR_AHEAD = dt.timedelta(hours=2, minutes=30)


def anchor_plan(needs: dict, now: dt.datetime) -> dict[str, list[list[str]]]:
    """Канал → [на каждый пустой час: склады по порядку] — нужен 1 пост: пустой час в ближайшие 2.5 ч, у рубрики есть склад.
    31.10: первый склад пуст/грязный — пробуем следующий того же часа (раньше час оставался пустым)."""
    out: dict[str, list[str]] = {}
    for ch, d in ((needs or {}).get("channels") or {}).items():
        for e in d.get("empty", []):
            try:
                at = dt.datetime.fromisoformat(e["at"])
            except (KeyError, ValueError):
                continue
            if not (now < at <= now + ANCHOR_AHEAD) or not e.get("stash"):
                continue
            out.setdefault(ch, []).append(list(dict.fromkeys(e["stash"])))   # 31.10: все склады часа по порядку, не только первый
    return out


async def anchor(client, state_dir: Path, needs: dict, now: dt.datetime | None = None, log=print) -> dict:
    """По одному посту из склада на каждый скоро пустой час (сверх дневной нормы). Читает только нужные склады."""
    now = now or dt.datetime.now(dt.timezone.utc)
    want = anchor_plan(needs, now)
    if not want:
        return {}
    sf = state_dir / "sklad.json"
    try:
        st = json.loads(sf.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        st = {}
    used = st.setdefault("used", {})
    ents = await find(client, log)
    cache: dict[str, list[dict]] = {}
    report: dict[str, int] = {}
    for ch, names in want.items():
        if ch == "xojaobod" and not curate.XOJAOBOD_FLAG.exists():
            continue
        sent = 0
        for opts in names:
          for name in (opts if isinstance(opts, list) else [opts]):
            if name not in ents or ch not in SKLAD.get(name, ()):
                continue
            if name not in cache:
                try:
                    cache[name] = await read(client, ents[name], 3000)
                except Exception as e:  # noqa: BLE001
                    log(f"  якорь {name}: {type(e).__name__}")
                    cache[name] = []
            it = None
            for x in order(cache[name], ch, now, name):
                if not eligible(x, name, ch, now) or str(x["id"]) in used.get(f"{ch}|{name}", []) \
                        or str(x["id"]) in used.get(f"bad|{name}", []) or taken(used, name, ch, x):
                    continue
                if needs_check(name) and not os.environ.get("GEMINI_API_KEY"):
                    break                              # нечем проверить — без проверки не шлём
                if needs_check(name):                  # 31.10: и якорь — только после проверки кадров на чужое лого
                    try:
                        ok = await curate.clean_frame(client, {"kind": x["kind"], "msg": x["msg"]}, background=False)
                    except RuntimeError as e:
                        log(f"  якорь {name}: {e}")
                        break
                    if ok is None:
                        continue
                    if not ok:
                        used.setdefault(f"bad|{name}", []).append(str(x["id"]))
                        log(f"  🚫 {name} #{x['id']}: чужое лого — пропуск навсегда")
                        continue
                it = x
                break
            if not it:
                continue
            try:
                await client.forward_messages(curate.BOTS[ch], it["ids"], from_peer=ents[name])
            except Exception as e:  # noqa: BLE001
                log(f"  якорь → {ch}: {type(e).__name__}")
                continue
            mark_used(used, name, ch, it)
            sent += 1
            log(f"  ⚓ {name} → {ch}: #{it['id']} {it['text'][:50]!r}")
            await asyncio.sleep(4)
            break                                      # этот час закрыт — к следующему
        report[ch] = sent
    sf.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    return report
