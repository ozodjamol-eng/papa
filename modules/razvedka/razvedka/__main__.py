"""PAPA Razvedka.
  python -m razvedka login            — вход в Telegram (интерактивно, на сервере)
  python -m razvedka collect          — собрать посты
  python -m razvedka report [--send]  — отчёт в консоль (и в «Избранное» аккаунта с --send)
  python -m razvedka send             — отчёт в консоль и в «Избранное» аккаунта
  python -m razvedka run              — collect + send (для ежедневного таймера)
"""
from __future__ import annotations

import asyncio
import getpass
import os
import sys
import tomllib
from pathlib import Path

from . import analyze, report, store

CONFIG = Path(os.environ.get("PAPA_RAZVEDKA_CONFIG", Path(__file__).resolve().parent.parent / "config.toml"))
DB = os.environ.get("PAPA_RAZVEDKA_DB", "/var/lib/papa-razvedka/razvedka.sqlite3")


def cfg() -> dict:
    return tomllib.loads(CONFIG.read_text(encoding="utf-8"))


async def _login(env_out: str) -> None:
    from telethon import TelegramClient
    from telethon.errors import SessionPasswordNeededError
    from telethon.sessions import StringSession
    print("Ключи берутся на https://my.telegram.org → API development tools.")
    api_id = int(input("api_id: ").strip())
    api_hash = getpass.getpass("api_hash (не отображается): ").strip()
    phone = input("номер телефона аккаунта (+998...): ").strip()
    c = TelegramClient(StringSession(), api_id, api_hash, device_model="PAPA Razvedka",
                       app_version="1.0", system_version="Linux")
    await c.connect()
    await c.send_code_request(phone)
    code = input("код из Telegram: ").strip()
    try:
        await c.sign_in(phone=phone, code=code)
    except SessionPasswordNeededError:
        await c.sign_in(password=getpass.getpass("облачный пароль Telegram (не отображается): "))
    me = await c.get_me()
    session = c.session.save()
    await c.disconnect()
    old = os.umask(0o077)
    try:
        Path(env_out).parent.mkdir(parents=True, exist_ok=True)
        Path(env_out).write_text(f"PAPA_TG_API_ID={api_id}\nPAPA_TG_API_HASH={api_hash}\nPAPA_TG_SESSION={session}\n")
    finally:
        os.umask(old)
    os.chmod(env_out, 0o600)
    print(f"LOGIN_OK: {me.first_name or ''} (id {me.id}). Сессия сохранена в {env_out}.")


async def _collect() -> dict:
    from .collect import collect
    from .telegram import TelethonSource, client_from_env
    db = store.connect(DB)
    c = client_from_env()
    await c.connect()
    if not await c.is_user_authorized():
        raise SystemExit("NOT_AUTHORIZED: выполните login")
    try:
        return await collect(TelethonSource(c), db, cfg())
    finally:
        await c.disconnect()


async def _send(text: str) -> None:
    from .telegram import client_from_env, send_report
    c = client_from_env()
    await c.connect()
    try:
        await send_report(c, text)
    finally:
        await c.disconnect()


def main(argv: list[str]) -> None:
    cmd = argv[0] if argv else "report"
    if cmd == "login":
        asyncio.run(_login(argv[1] if len(argv) > 1 else "/etc/papa-razvedka/telegram.env"))
    elif cmd in ("collect", "run"):
        s = asyncio.run(_collect())
        print(f"COLLECT_DONE каналов={s['channels']} постов={s['posts']} ошибок={len(s['errors'])}")
        if cmd == "run":
            text = report.render(analyze.analyze(store.connect(DB), int(cfg().get("report_days", 7))))
            asyncio.run(_send(text))
            print("REPORT_SENT")
    elif cmd == "send":
        argv = ["report", "--send"]
        main(argv)
    elif cmd == "report":
        text = report.render(analyze.analyze(store.connect(DB), int(cfg().get("report_days", 7))))
        print(text)
        if "--send" in argv:
            asyncio.run(_send(text))
            print("REPORT_SENT")
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv[1:])
