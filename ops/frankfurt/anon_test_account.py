"""Проверка пути А в ТЕСТОВОЙ группе: новый аккаунт — анонимный админ, пишет сообщение;
владелец читает и смотрит, от чьего имени оно видно. Рабочие каналы не трогаются."""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, "/opt/papa/modules/razvedka")
from razvedka.telegram import client_from_env  # noqa: E402
from telethon import TelegramClient  # noqa: E402
from telethon.sessions import StringSession  # noqa: E402
from telethon.errors import UserAlreadyParticipantError  # noqa: E402
from telethon.tl.functions.channels import EditAdminRequest  # noqa: E402
from telethon.tl.functions.messages import ExportChatInviteRequest, ImportChatInviteRequest  # noqa: E402
from telethon.tl.types import ChatAdminRights, PeerChannel  # noqa: E402

GID = int(Path("/etc/papa-test/group.id").read_text())
PUB = dict(l.split("=", 1) for l in Path("/etc/papa-tg/publisher.env").read_text().splitlines() if "=" in l)


async def main():
    owner = client_from_env()
    acc = TelegramClient(StringSession(PUB["PAPA_TG_SESSION"]), int(PUB["PAPA_TG_API_ID"]), PUB["PAPA_TG_API_HASH"])
    await owner.connect(); await acc.connect()
    try:
        grp = await owner.get_entity(GID)
        me = await acc.get_me()
        inv = await owner(ExportChatInviteRequest(grp))           # аккаунт вступает сам по ссылке
        try:
            await acc(ImportChatInviteRequest(inv.link.rsplit("+", 1)[-1].rsplit("/", 1)[-1]))
        except UserAlreadyParticipantError:
            pass
        await asyncio.sleep(2)
        user = next(u for u in await owner.get_participants(grp) if u.id == me.id)
        await owner(EditAdminRequest(channel=grp, user_id=user, rank="",
                                     admin_rights=ChatAdminRights(anonymous=True, delete_messages=True)))
        await asyncio.sleep(2)
        m = await acc.send_message(GID, "PAPA: проверка — от чьего имени видно это сообщение?")
        await asyncio.sleep(2)
        seen = (await owner.get_messages(grp, ids=[m.id]))[0]
        frm = seen.from_id
        as_group = frm is None or (isinstance(frm, PeerChannel) and int(f"-100{frm.channel_id}") == GID)
        print(f"глазами участника: {'группа' if as_group else 'аккаунт ' + str(me.id)}")
        print("ANON_OK — новый аккаунт публикует от имени группы" if as_group else "ANON_NO — виден аккаунт")
    finally:
        await owner.disconnect(); await acc.disconnect()


asyncio.run(main())
