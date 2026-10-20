"""Диагностика (только чтение): почему аккаунт PAPA не может писать в Хўжаобод Сити 24.
Показывает: участник ли, админ ли, какие права, ограничения группы для всех. Ничего не публикует и не меняет."""
import asyncio
from pathlib import Path

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import GetFullChannelRequest, GetParticipantRequest
from telethon.errors import UserNotParticipantError

GROUP = "xojaobodcity24"
PUB = dict(l.split("=", 1) for l in Path("/etc/papa-tg/publisher.env").read_text().splitlines() if "=" in l)


async def main():
    acc = TelegramClient(StringSession(PUB["PAPA_TG_SESSION"]), int(PUB["PAPA_TG_API_ID"]), PUB["PAPA_TG_API_HASH"])
    await acc.connect()
    try:
        if not await acc.is_user_authorized():
            print("СЕССИЯ PAPA НЕДЕЙСТВИТЕЛЬНА — аккаунт вышел/сессия сброшена"); return
        me = await acc.get_me()
        print(f"аккаунт: {me.first_name} @{me.username} id {me.id}")
        g = await acc.get_entity(GROUP)
        print(f"группа: {g.title} id {g.id}; megagroup={getattr(g, 'megagroup', None)}; left={getattr(g, 'left', None)}")
        print(f"admin_rights(видно аккаунту)={g.admin_rights}")
        print(f"banned_rights(для аккаунта)={g.banned_rights}")
        print(f"default_banned_rights(для всех)={g.default_banned_rights}")
        try:
            p = await acc(GetParticipantRequest(g, me.id))
            print(f"участник: {type(p.participant).__name__}")
            for k in ("admin_rights", "banned_rights", "rank"):
                if hasattr(p.participant, k):
                    print(f"  {k}={getattr(p.participant, k)}")
        except UserNotParticipantError:
            print("НЕ УЧАСТНИК группы")
        full = await acc(GetFullChannelRequest(g))
        fc = full.full_chat
        print(f"slowmode={getattr(fc, 'slowmode_seconds', None)} participants={getattr(fc, 'participants_count', None)}")
    finally:
        await acc.disconnect()
    print("XOJAOBOD_CHECK_DONE — ничего не изменено")


asyncio.run(main())
