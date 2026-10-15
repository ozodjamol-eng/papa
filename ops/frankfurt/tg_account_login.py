"""Вход нового рабочего аккаунта Telegram (SIM владельца) на сервер.
api_id/api_hash берутся из уже настроенной Разведки; вводятся только номер, код и облачный пароль (скрыто).
Сессия — только в /etc/papa-tg/publisher.env (0600). В чат ничего не копировать."""
import asyncio
import getpass
import os
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession

SRC = Path("/etc/papa-razvedka/telegram.env")
OUT = Path("/etc/papa-tg/publisher.env")


async def main():
    env = dict(l.split("=", 1) for l in SRC.read_text().splitlines() if "=" in l)
    api_id, api_hash = int(env["PAPA_TG_API_ID"]), env["PAPA_TG_API_HASH"]
    phone = input("номер НОВОГО аккаунта (+998...): ").strip()
    c = TelegramClient(StringSession(), api_id, api_hash, device_model="PAPA Server", app_version="1.0",
                       system_version="Linux")
    await c.connect()
    await c.send_code_request(phone)
    code = input("код из Telegram (придёт в приложение нового аккаунта): ").strip()
    try:
        await c.sign_in(phone=phone, code=code)
    except SessionPasswordNeededError:
        await c.sign_in(password=getpass.getpass("облачный пароль нового аккаунта (не отображается): "))
    me = await c.get_me()
    session = c.session.save()
    await c.disconnect()
    OUT.parent.mkdir(mode=0o700, exist_ok=True)
    old = os.umask(0o077)
    try:
        OUT.write_text(f"PAPA_TG_API_ID={api_id}\nPAPA_TG_API_HASH={api_hash}\nPAPA_TG_SESSION={session}\n"
                       f"PAPA_TG_USER_ID={me.id}\nPAPA_TG_USERNAME={me.username or ''}\n")
    finally:
        os.umask(old)
    os.chmod(OUT, 0o600)
    print(f"LOGIN_OK: {me.first_name or ''} (id {me.id})")


asyncio.run(main())
