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
    sent = await c.send_code_request(phone)
    print(f"код отправлен: {type(sent.type).__name__.replace('SentCodeType', '')}  (App — в приложение Telegram, Sms — СМС, Email — на почту)")
    code = input("код (или напишите sms — прислать заново другим способом): ").strip()
    while code.lower() in ("sms", "смс"):
        from telethon.tl.functions.auth import ResendCodeRequest
        sent = await c(ResendCodeRequest(phone_number=phone, phone_code_hash=sent.phone_code_hash))
        print(f"код отправлен заново: {type(sent.type).__name__.replace('SentCodeType', '')}")
        code = input("код: ").strip()
    from telethon.errors import PhoneCodeInvalidError, PhoneCodeExpiredError
    for attempt in range(3):
        try:
            await c.sign_in(phone=phone, code=code.replace(" ", ""), phone_code_hash=sent.phone_code_hash)
            break
        except PhoneCodeInvalidError:
            code = input("код не подошёл — введите САМЫЙ ПОСЛЕДНИЙ код из чата «Telegram»: ").strip()
        except PhoneCodeExpiredError:
            raise SystemExit("CODE_EXPIRED — запустите команду заново")
        except SessionPasswordNeededError:
            await c.sign_in(password=getpass.getpass("облачный пароль нового аккаунта (не отображается): "))
            break
    else:
        raise SystemExit("CODE_INVALID — запустите команду заново")
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
