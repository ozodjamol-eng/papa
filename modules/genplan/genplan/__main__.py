"""GENPLAN PAPA.
  python -m genplan run    — служба: хаб (кнопки владельца) + публикации по сетке раз в минуту
  python -m genplan plan   — план на сегодня в консоль
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

from . import hub, menu, service, store
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
    print(f"GENPLAN PAPA запущен, режим: {cfg()['mode']}", flush=True)
    if store.kv_get(db, "menu_v") != "2":          # один раз: показать владельцу постоянную панель
        for o in str(env.get("OWNER_IDS", "")).split(","):
            try:
                bot("sendMessage", chat_id=int(o), text="Панель PAPA готова 👇\n\n" + menu.HELP, reply_markup=menu.KEYBOARD)
            except Exception as e:  # noqa: BLE001
                print(f"menu: {e}", flush=True)
        store.kv_set(db, "menu_v", "2")
    while True:
        c = cfg()
        try:
            ups = await asyncio.to_thread(bot, "getUpdates", offset=offset, timeout=20,
                                          allowed_updates=["channel_post", "callback_query", "message"])
            for u in ups:
                try:
                    r = hub.handle(bot, db, c, env, u)
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
        if time.time() >= next_tick:
            try:
                if not acc.is_connected():
                    await acc.connect()
                await service.tick(db, c, env, pubs, log=lambda s: print(s, flush=True))
            except Exception as e:  # noqa: BLE001
                print(f"tick: {type(e).__name__}: {e}", flush=True)
            next_tick = time.time() + 60


def main(argv: list[str]) -> None:
    cmd = argv[0] if argv else "plan"
    if cmd == "run":
        asyncio.run(run())
    else:
        print(service.today_text(store.connect(DB), cfg()))


if __name__ == "__main__":
    main(sys.argv[1:])
