"""GENPLAN PAPA.
  python -m genplan run    — служба: хаб (кнопки владельца) + публикации по сетке раз в минуту
  python -m genplan plan   — план на сегодня в консоль
  python -m genplan fabrika — обработчик ссылок, логотипа и ИИ-текста (служба papa-fabrika)
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import datetime as dt
import http.client
import json
import os
import sys
import threading
import time
import tomllib
from pathlib import Path

from . import hub, menu, plan, service, store
from .publish import AccountPublisher, BotPublisher

ROOT = Path(__file__).resolve().parent.parent
CONFIG = Path(os.environ.get("PAPA_GENPLAN_CONFIG", ROOT / "config.toml"))
DB = os.environ.get("PAPA_GENPLAN_DB", "/var/lib/papa-genplan/genplan.sqlite3")


def cfg() -> dict:
    c = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
    c["mode"] = os.environ.get("GENPLAN_MODE", c.get("mode", "shadow"))
    return c


_TL = threading.local()


def make_bot(token: str):
    """Вызов Bot API. Соединение с api.telegram.org держится открытым (keep-alive, своё в каждом потоке):
    раньше каждый вызов заново делал TCP+TLS — лишние доли секунды на каждую кнопку и карточку."""
    path = f"/bot{token}/"

    def conn(fresh: bool = False) -> http.client.HTTPSConnection:
        pool = getattr(_TL, "pool", None)
        if pool is None:
            pool = _TL.pool = {}
        c = pool.get(token)
        if c is None or fresh:
            if c is not None:
                c.close()
            c = pool[token] = http.client.HTTPSConnection("api.telegram.org", timeout=45)
        return c

    def call(method: str, **p):
        body = json.dumps(p).encode()
        for attempt in (0, 1):
            c = conn(fresh=attempt > 0)
            try:
                c.request("POST", path + method, body=body, headers={"Content-Type": "application/json"})
                r = c.getresponse()
                raw = r.read()
                break
            except (http.client.HTTPException, OSError):
                c.close()
                if attempt:
                    raise
        data = json.loads(raw or b"{}")
        if not data.get("ok"):
            raise RuntimeError(f"{method}: {data.get('description')}")
        return data["result"]
    return call


async def account_health(acc, c: dict, env: dict) -> str | None:
    """Аккаунт PAPA (публикует в группу): не разлогинен ли Telegram'ом, есть ли права публиковать. None — всё в порядке."""
    chans = [k for k, ch in c["channels"].items() if ch.get("publisher") == "account"]
    if not chans:
        return None
    try:
        if not await acc.is_user_authorized():
            return ("🔴 Аккаунт PAPA отключён Telegram'ом — посты в группу не выйдут.\n"
                    "Франкфурт: papa-update tg-account-qr (вход по QR), затем papa-update genplan-restart")
        for k in chans:
            to = service.target(c, env, k)
            p = await acc.get_permissions(to, "me")
            if not (getattr(p, "is_admin", False) or getattr(p, "is_creator", False)):
                return f"🔴 У аккаунта PAPA нет прав админа в «{c['channels'][k]['title']}» ({to}) — добавьте админом."
    except Exception as e:  # noqa: BLE001
        name = type(e).__name__
        if "AuthKey" in name or "Unauthorized" in name or "SessionRevoked" in name:
            return ("🔴 Аккаунт PAPA отключён Telegram'ом — посты в группу не выйдут.\n"
                    "Франкфурт: papa-update tg-account-qr, затем papa-update genplan-restart")
        return f"⚠️ Проверка аккаунта PAPA: {name}: {str(e)[:120]}"
    return None


async def run() -> None:
    from telethon import TelegramClient
    from telethon.sessions import StringSession
    env = dict(os.environ)
    db = store.connect(DB)
    from . import bots
    reg = bots.setup(cfg(), env, make_bot)               # главный бот + боты-пульты каналов
    bot = reg["main"]
    acc = TelegramClient(StringSession(env["PAPA_TG_SESSION"]), int(env["PAPA_TG_API_ID"]), env["PAPA_TG_API_HASH"])
    await acc.connect()
    pubs = {"account": AccountPublisher(acc), "bot": BotPublisher(env["GENPLAN_BOT_TOKEN"])}
    for k, tok in bots.TOKENS.items():
        if k != "main":
            pubs[f"bot:{k}"] = BotPublisher(tok)
    try:                                                  # 21.10: один раз убрать из PAPA HUB старые служебные копии
        hc = service.hub_clean_once(db, cfg(), env, pubs, log=lambda t: print(t, flush=True))
        if hc["moved"] or hc["deleted"] or hc["errors"]:
            gb = bots.for_channel(next((c for c, ch in cfg()["channels"].items() if ch["publisher"] == "account"), None), bot)
            for o in str(env.get("OWNER_IDS", "")).split(","):
                gb("sendMessage", chat_id=int(o), text=(
                    f"🧹 PAPA HUB очищен: убрано {hc['deleted']} служебных копий"
                    + (f", {hc['moved']} нужных поста (в плане / Якуний) теперь хранятся здесь, в пульте" if hc["moved"] else "")
                    + (f"\n⚠️ Не получилось: {hc['errors']} — попробую при следующем запуске" if hc["errors"] else "")
                    + "\nДальше в PAPA HUB пост попадает только на секунды публикации и сразу удаляется."))
    except Exception as e:  # noqa: BLE001
        print(f"hub_clean: {e}", flush=True)
    offsets = {k: int(store.kv_get(db, "offset" if k == "main" else f"offset_{k}", "0")) for k in reg}
    next_tick = 0.0
    next_health, last_health = 0.0, None
    print(f"GENPLAN PAPA запущен, режим: {cfg()['mode']}", flush=True)
    if store.kv_get(db, "menu_v") != "5":          # один раз: панель пульта как в GENPLAN 5
        for o in str(env.get("OWNER_IDS", "")).split(","):
            try:
                bot("sendMessage", chat_id=int(o), reply_markup=menu.PANEL,
                    text="🎉 Пульт КАТТА ДАВРА — новая панель 👇\n➕ ПОСТ · 🚨 СРОЧНО · 📅 СЕГОДНЯ · 📣 РЕКЛАМА · 📁 КОНТЕНТ · ⚙️ НАСТРОЙКИ")
            except Exception as e:  # noqa: BLE001
                print(f"menu: {e}", flush=True)
        store.kv_set(db, "menu_v", "5")
    if bots.SHTAB and store.kv_get(db, "shtab_hello") != "1":   # 23.10: главный пульт подключён — один раз сказать, что он делает
        for o in str(env.get("OWNER_IDS", "")).split(","):
            try:
                bots.shtab()("sendMessage", chat_id=int(o), text=(
                    "🏛 PAPA ШТАБ подключён — главный пульт всех каналов.\n"
                    "Сюда приходят: тревоги (что не вышло и почему), напоминания, проверка Жумы в четверг.\n"
                    "Утренние видео в PAPA HUB теперь загружает он.\n"
                    "Предпросмотр утра и кнопка 🗑 — в пульте своего канала (КАТТА ДАВРА, PaparazziUZ, Хўжаобод)."))
                store.kv_set(db, "shtab_hello", "1")
            except Exception as e:  # noqa: BLE001
                print(f"shtab hello: {e}", flush=True)
    for k, b in reg.items():                          # новый бот-пульт: один раз показать панель и что он делает
        if k != "main" and store.kv_get(db, f"menu_v_{k}") != "2":
            title = c0["channels"][k]["title"] if (c0 := cfg())["channels"].get(k) else k
            sent = False
            for o in str(env.get("OWNER_IDS", "")).split(","):
                try:
                    b("sendMessage", chat_id=int(o), reply_markup=menu.PANEL,
                      text=f"Пульт «{title}» 👇\nВсё, что бросите сюда, пойдёт в {title}.\n"
                           "➕ ПОСТ · 🚨 СРОЧНО · 📅 СЕГОДНЯ · 📣 РЕКЛАМА · 📁 КОНТЕНТ · ⚙️ НАСТРОЙКИ")
                    sent = True
                except Exception as e:  # noqa: BLE001 — владелец ещё не нажал «Старт» в этом боте
                    print(f"menu {k}: {e}", flush=True)
            if sent:
                store.kv_set(db, f"menu_v_{k}", "2")

    async def poll(k, b):
        try:
            ups = await asyncio.to_thread(b, "getUpdates", offset=offsets[k], timeout=1 if hub.ALBUMS else 20,
                                          allowed_updates=["channel_post", "edited_channel_post", "callback_query", "message",
                                                           "my_chat_member"])
            return k, b, ups
        except Exception as e:  # noqa: BLE001
            print(f"getUpdates {k}: {e}", flush=True)
            return k, b, None
    state = {"next_tick": next_tick}
    # Пульты отвечают в своём потоке со своим подключением к базе: публикация видео и минутный проход по сетке
    # больше не задерживают ответ на брошенный пост или нажатую кнопку.
    work = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="pult")
    hdb_box: dict = {}

    def hdb():
        if "db" not in hdb_box:
            hdb_box["db"] = store.connect(DB)
        return hdb_box["db"]

    def handle_update(k, b, u):
        c = cfg()
        db = hdb()
        t0 = time.monotonic()
        try:
            r = hub.handle(b, db, c, env, u)
            msg = u.get("message") or {}
            if r == "ur":
                state["next_tick"] = 0.0                     # 🆘 — публикуем сразу, не ждём минуту
            if r and r.startswith("panel:"):                 # панель пульта — про свой канал
                chan = bots.channel_of(b) or c.get("default_channel") or "davra"
                ans = menu.panel_reply(db, c, chan, r[6:])
                if ans:
                    b("sendMessage", chat_id=msg["chat"]["id"], text=ans[:4096],
                      reply_markup=menu.panel_markup(c, chan, r[6:]))
            if r and r.startswith("cmd:"):
                ans = menu.reply(db, c, msg.get("text", ""))
                if ans:
                    b("sendMessage", chat_id=msg["chat"]["id"], text=ans[:4096], reply_markup=menu.PANEL)
        except Exception as e:  # noqa: BLE001 — одно сообщение не должно ронять службу
            print(f"hub: {type(e).__name__}: {e}", flush=True)
        took = time.monotonic() - t0
        if took > 1.5:
            print(f"slow {k}: {took:.1f} с ({next((x for x in u if x != 'update_id'), '?')})", flush=True)
        offsets[k] = u["update_id"] + 1
        store.kv_set(db, "offset" if k == "main" else f"offset_{k}", offsets[k])

    async def bot_loop(k, b):
        """Каждый пульт слушает Telegram сам по себе: нажатие в одном боте не ждёт долгого опроса другого (было до 20 с)."""
        while True:
            _, _, ups = await poll(k, b)
            if ups is None:
                await asyncio.sleep(10)
                continue
            loop = asyncio.get_running_loop()
            for u in ups:
                await loop.run_in_executor(work, handle_update, k, b, u)

    def flush_albums():
        hub.flush_albums(bot, hdb(), cfg(), env)

    async def album_loop():
        """Альбомы собирает тот же поток, что и пульты, — и не ждёт минутный проход по сетке."""
        while True:
            await asyncio.sleep(0.5)
            if hub.ALBUMS:
                try:
                    await asyncio.get_running_loop().run_in_executor(work, flush_albums)
                except Exception as e:  # noqa: BLE001
                    print(f"albums: {e}", flush=True)

    async def tick_loop():
        nonlocal next_health, last_health
        while True:
            c = cfg()
            if time.time() < state["next_tick"]:
                await asyncio.sleep(0.5)
                continue
            try:
                if not acc.is_connected():
                    await acc.connect()
                if time.time() >= next_health:                # аккаунт PAPA жив и с правами? — раз в 30 минут
                    next_health = time.time() + 1800
                    msg = await account_health(acc, c, env)
                    if msg and msg != last_health:
                        service.ERRORS.append(msg)
                    last_health = msg
                res = await service.tick(db, c, env, pubs, log=lambda s: print(s, flush=True))
                owners = [int(o) for o in str(env.get("OWNER_IDS", "")).split(",") if o.strip()]
                for mid in res["ids"]:                       # карточка у владельца: «опубликовано»
                    m = store.get(db, mid)
                    if m and m["owner_msg"]:
                        t, kb = hub.card(db, c, mid)
                        cb = reg.get(m["via"] or "main") or bot           # карточку правит тот бот, что её прислал
                        for o in owners:
                            try:
                                cb("editMessageText", chat_id=o, message_id=m["owner_msg"], text=t, reply_markup=kb)
                            except Exception:  # noqa: BLE001 — карточка могла быть в другом чате
                                pass
                try:                                          # 🌙 Кечки дайжест → группа Хўжаобод (20:30)
                    from . import digest as _dg
                    pub = await _dg.publish_live(db, c, env, acc)
                    if pub:
                        service.ERRORS.append(pub)
                except Exception as e:  # noqa: BLE001
                    service.ERRORS.append(f"⚠️ Кечки дайжест не вышел в группу: {type(e).__name__}: {str(e)[:150]}")
                try:                                          # 🎬 05:00–06:30: заказать утренний ролик погоды (раз в день)
                    _now = dt.datetime.now(plan.TZ)
                    _f = f"weather_req_{_now.date()}"
                    if "05:00" <= _now.strftime("%H:%M") < "06:30" and not store.kv_get(db, _f):
                        from . import digest as _dg
                        _r = await asyncio.to_thread(_dg.trigger_weather, _now.date())
                        if _r == "ok":
                            store.kv_set(db, _f, "ok")
                        elif _now.strftime("%H:%M") >= "06:00":
                            service.ERRORS.append(f"⚠️ Ролик погоды не заказан ({_r}) — в 07:00 выйдет текст, если GitHub не соберёт сам")
                            store.kv_set(db, _f, "fail")
                except Exception as e:  # noqa: BLE001
                    print(f"weather-req: {e}", flush=True)
                try:                                          # 🎉 Кечки дайжест → КАТТА ДАВРА (20:30, решение 20.10)
                    from . import digest as _dg
                    pub = await _dg.publish_live_davra(db, c, env, pubs["bot"])
                    if pub:
                        service.ERRORS.append(pub)
                except Exception as e:  # noqa: BLE001
                    service.ERRORS.append(f"⚠️ Кечки дайжест не вышел в КАТТА ДАВРА: {type(e).__name__}: {str(e)[:150]}")
                try:                                          # 🛡 20:45 сторож: дайджест не вышел — сразу владельцу (21.10)
                    from . import digest as _dg
                    wm = _dg.watch(db, c)
                    if wm:
                        service.ERRORS.append(wm)
                except Exception as e:  # noqa: BLE001
                    print(f"digest-watch: {e}", flush=True)
                from . import namaz
                rem = namaz.reminder(db, c, dt.datetime.now(plan.TZ))
                if rem:
                    service.ERRORS.append(rem)
                sb = bots.shtab(bot)                       # 23.10: тревоги и отчёты — в главный пульт PAPA ШТАБ
                while service.ERRORS:
                    err = service.ERRORS.pop(0)
                    for o in owners:
                        try:
                            sb("sendMessage", chat_id=o, text=err)
                        except Exception:  # noqa: BLE001 — штаб недоступен (не нажат «Старт») — главный бот
                            bot("sendMessage", chat_id=o, text=err)
            except Exception as e:  # noqa: BLE001
                print(f"tick: {type(e).__name__}: {e}", flush=True)
            state["next_tick"] = time.time() + 60

    async def shtab_loop():
        """23.10: PAPA ШТАБ слушает только кнопки (разрешения, утро) и личные сообщения владельца — обзор."""
        sb = bots.SHTAB.get("bot")
        if not sb:
            return
        off = int(store.kv_get(db, "offset_shtab", "0"))
        loop = asyncio.get_running_loop()
        while True:
            try:
                ups = await asyncio.to_thread(sb, "getUpdates", offset=off, timeout=20,
                                              allowed_updates=["callback_query", "message"])
            except Exception as e:  # noqa: BLE001
                print(f"getUpdates shtab: {e}", flush=True)
                await asyncio.sleep(10)
                continue
            for u in ups:
                try:
                    await loop.run_in_executor(work, lambda u=u: hub.shtab_handle(sb, hdb(), cfg(), env, u))
                except Exception as e:  # noqa: BLE001
                    print(f"shtab: {type(e).__name__}: {e}", flush=True)
                off = u["update_id"] + 1
                store.kv_set(db, "offset_shtab", off)

    await asyncio.gather(tick_loop(), album_loop(), shtab_loop(), *(bot_loop(k, b) for k, b in reg.items()))


def main(argv: list[str]) -> None:
    cmd = argv[0] if argv else "plan"
    if cmd == "run":
        asyncio.run(run())
    elif cmd == "digest":                          # 🌙 свой Кечки дайжест (таймер papa-digest 19:50)
        from . import bots, digest
        reg = bots.setup(cfg(), dict(os.environ), make_bot)
        digest.main(store.connect(DB), dict(os.environ), reg["main"])
    elif cmd == "fabrika":
        from . import bots, fabrika
        reg = bots.setup(cfg(), dict(os.environ), make_bot)
        fabrika.loop(reg["main"], store.connect(DB), cfg, dict(os.environ))
    else:
        print(service.today_text(store.connect(DB), cfg()))


if __name__ == "__main__":
    main(sys.argv[1:])
