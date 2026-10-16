"""GENPLAN PAPA.
  python -m genplan run    — служба: хаб (кнопки владельца) + публикации по сетке раз в минуту
  python -m genplan plan   — план на сегодня в консоль
  python -m genplan fabrika — обработчик ссылок, логотипа и ИИ-текста (служба papa-fabrika)
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
import sys
import time
import tomllib
import urllib.error
import urllib.request
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


def make_bot(token: str):
    base = f"https://api.telegram.org/bot{token}"

    def call(method: str, **p):
        req = urllib.request.Request(f"{base}/{method}", data=json.dumps(p).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                data = json.loads(r.read())
        except urllib.error.HTTPError as e:
            data = json.loads(e.read() or b"{}")
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
    bot = make_bot(env["GENPLAN_BOT_TOKEN"])
    acc = TelegramClient(StringSession(env["PAPA_TG_SESSION"]), int(env["PAPA_TG_API_ID"]), env["PAPA_TG_API_HASH"])
    await acc.connect()
    pubs = {"account": AccountPublisher(acc), "bot": BotPublisher(env["GENPLAN_BOT_TOKEN"])}
    offset = int(store.kv_get(db, "offset", "0"))
    next_tick = 0.0
    next_health, last_health = 0.0, None
    print(f"GENPLAN PAPA запущен, режим: {cfg()['mode']}", flush=True)
    if store.kv_get(db, "menu_v") != "4":          # один раз: показать владельцу постоянную панель
        for o in str(env.get("OWNER_IDS", "")).split(","):
            try:
                bot("sendMessage", chat_id=int(o), text="Панель PAPA готова 👇\n\n" + menu.HELP, reply_markup=menu.KEYBOARD)
            except Exception as e:  # noqa: BLE001
                print(f"menu: {e}", flush=True)
        store.kv_set(db, "menu_v", "4")
    while True:
        c = cfg()
        try:
            ups = await asyncio.to_thread(bot, "getUpdates", offset=offset, timeout=1 if hub.ALBUMS else 20,
                                          allowed_updates=["channel_post", "callback_query", "message"])
            for u in ups:
                try:
                    r = hub.handle(bot, db, c, env, u)
                    if r == "ur":
                        next_tick = 0.0                      # 🆘 — публикуем сразу, не ждём минуту
                    msg = u.get("message") or {}
                    if r and r.startswith("cmd:"):
                        ans = menu.reply(db, c, msg.get("text", ""))
                        if ans:
                            bot("sendMessage", chat_id=msg["chat"]["id"], text=ans[:4096], reply_markup=menu.KEYBOARD)
                except Exception as e:  # noqa: BLE001 — одно сообщение не должно ронять службу
                    print(f"hub: {type(e).__name__}: {e}", flush=True)
                offset = u["update_id"] + 1
                store.kv_set(db, "offset", offset)
        except Exception as e:  # noqa: BLE001
            print(f"getUpdates: {e}", flush=True)
            await asyncio.sleep(10)
        try:
            hub.flush_albums(bot, db, c, env)
        except Exception as e:  # noqa: BLE001
            print(f"albums: {e}", flush=True)
        if time.time() >= next_tick:
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
                        for o in owners:
                            try:
                                bot("editMessageText", chat_id=o, message_id=m["owner_msg"], text=t, reply_markup=kb)
                            except Exception:  # noqa: BLE001 — карточка могла быть в другом чате
                                pass
                from . import namaz
                rem = namaz.reminder(db, c, dt.datetime.now(plan.TZ))
                if rem:
                    service.ERRORS.append(rem)
                while service.ERRORS:
                    err = service.ERRORS.pop(0)
                    for o in owners:
                        bot("sendMessage", chat_id=o, text=err)
            except Exception as e:  # noqa: BLE001
                print(f"tick: {type(e).__name__}: {e}", flush=True)
            next_tick = time.time() + 60


def main(argv: list[str]) -> None:
    cmd = argv[0] if argv else "plan"
    if cmd == "run":
        asyncio.run(run())
    elif cmd == "fabrika":
        from . import fabrika
        fabrika.loop(make_bot(os.environ["GENPLAN_BOT_TOKEN"]), store.connect(DB), cfg, dict(os.environ))
    else:
        print(service.today_text(store.connect(DB), cfg()))


if __name__ == "__main__":
    main(sys.argv[1:])
