"""Путь А, рабочая группа: аккаунт PAPA вступает в Хўжаобод Сити 24 и становится АНОНИМНЫМ админом
(права: только оставаться анонимным и удалять сообщения — свои ошибки). Ничего не публикует."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, "/opt/papa/modules/razvedka")
from razvedka.telegram import client_from_env  # noqa: E402
from telethon import TelegramClient  # noqa: E402
from telethon.sessions import StringSession  # noqa: E402
from telethon.tl.functions.channels import EditAdminRequest, JoinChannelRequest  # noqa: E402
from telethon.tl.types import ChatAdminRights  # noqa: E402

GROUP = "xojaobodcity24"
PUB = dict(l.split("=", 1) for l in Path("/etc/papa-tg/publisher.env").read_text().splitlines() if "=" in l)


async def main():
    owner = client_from_env()
    acc = TelegramClient(StringSession(PUB["PAPA_TG_SESSION"]), int(PUB["PAPA_TG_API_ID"]), PUB["PAPA_TG_API_HASH"])
    await owner.connect(); await acc.connect()
    try:
        me = await acc.get_me()
        await acc(JoinChannelRequest(GROUP))
        await asyncio.sleep(2)
        grp = await owner.get_entity(GROUP)
        user = next(u for u in await owner.get_participants(grp, search=me.first_name or "") if u.id == me.id)
        await owner(EditAdminRequest(channel=grp, user_id=user, rank="",
                                     admin_rights=ChatAdminRights(anonymous=True, delete_messages=True)))
        print(f"@{GROUP}: PAPA (id {me.id}) — анонимный админ (только анонимность и удаление своих ошибок)")
        print("XOJAOBOD_ADMIN_OK — ничего не опубликовано")
    finally:
        await owner.disconnect(); await acc.disconnect()


asyncio.run(main())
