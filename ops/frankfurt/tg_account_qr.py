"""Вход нового аккаунта по QR-коду (без кода из СМС/приложения).
На телефоне с аккаунтом PAPA: Настройки → Устройства → «Подключить устройство» → навести камеру на QR в консоли."""
import asyncio
import getpass
import os
from pathlib import Path

import qrcode
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession

SRC = Path("/etc/papa-razvedka/telegram.env")
OUT = Path("/etc/papa-tg/publisher.env")


async def main():
    env = dict(l.split("=", 1) for l in SRC.read_text().splitlines() if "=" in l)
    api_id, api_hash = int(env["PAPA_TG_API_ID"]), env["PAPA_TG_API_HASH"]
    c = TelegramClient(StringSession(), api_id, api_hash, device_model="PAPA Server", app_version="1.0",
                       system_version="Linux")
    await c.connect()
    for attempt in range(4):
        qr = await c.qr_login()
        q = qrcode.QRCode(border=1)
        q.add_data(qr.url)
        print("\nОтсканируйте в приложении PAPA: Настройки → Устройства → Подключить устройство\n")
        q.print_ascii(invert=True)
        try:
            await qr.wait(timeout=60)
            break
        except asyncio.TimeoutError:
            print("QR устарел — показываю новый")
        except SessionPasswordNeededError:
            await c.sign_in(password=getpass.getpass("облачный пароль аккаунта PAPA (не отображается): "))
            break
    else:
        raise SystemExit("QR_TIMEOUT — запустите заново")
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
