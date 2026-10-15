"""GENPLAN PAPA — подготовка (через профиль владельца, по его решению):
закрытый канал «PAPA HUB», бот @PapaGenplanBot (кнопки владельца + публикации в каналы),
бот — админ хаба и тестового канала PAPA TEST, аккаунт PAPA — участник хаба (берёт оттуда медиа).
Рабочие каналы НЕ трогаются. Токен — только в /etc/papa-genplan/genplan.env (0600). Повтор безопасен."""
import asyncio
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, "/opt/papa/modules/razvedka")
from razvedka.telegram import client_from_env  # noqa: E402
from telethon import TelegramClient  # noqa: E402
from telethon.errors import UserAlreadyParticipantError  # noqa: E402
from telethon.sessions import StringSession  # noqa: E402
from telethon.tl.functions.channels import CreateChannelRequest, EditAdminRequest  # noqa: E402
from telethon.tl.functions.messages import ExportChatInviteRequest, ImportChatInviteRequest  # noqa: E402
from telethon.tl.types import ChatAdminRights  # noqa: E402

ENV = Path("/etc/papa-genplan/genplan.env")
TOKEN_RE = re.compile(r"(\d{6,}:[A-Za-z0-9_-]{30,})")
NAMES = ["PapaGenplanBot", "papa_genplan_bot", "papa_reja_bot", "papauz_genplan_bot"]


def rd(p):
    p = Path(p)
    return dict(l.split("=", 1) for l in p.read_text().splitlines() if "=" in l) if p.exists() else {}


async def create_bot(c):
    async with c.conversation("BotFather", timeout=40) as conv:
        await conv.send_message("/cancel"); await conv.get_response()
        await conv.send_message("/newbot"); await conv.get_response()
        await conv.send_message("PAPA Genplan"); await conv.get_response()
        for u in NAMES:
            await conv.send_message(u)
            m = TOKEN_RE.search((await conv.get_response()).raw_text)
            if m:
                return u, m.group(1)
    raise SystemExit("BOT_USERNAMES_TAKEN")


async def main():
    env = rd(ENV)
    test = rd("/etc/papa-test/bot.env")
    pub = rd("/etc/papa-tg/publisher.env")
    owner = client_from_env()
    acc = TelegramClient(StringSession(pub["PAPA_TG_SESSION"]), int(pub["PAPA_TG_API_ID"]), pub["PAPA_TG_API_HASH"])
    await owner.connect(); await acc.connect()
    try:
        me = await owner.get_me()
        env["OWNER_IDS"] = str(me.id)
        env["TEST_CHANNEL_ID"] = test["PAPA_TEST_CHANNEL_ID"]
        env["TEST_GROUP_ID"] = Path("/etc/papa-test/group.id").read_text().strip()
        if "HUB_CHAT_ID" not in env:
            r = await owner(CreateChannelRequest(title="PAPA HUB", about="Хаб PAPA: пересылайте сюда посты для публикации.",
                                                 broadcast=True))
            env["HUB_CHAT_ID"] = f"-100{r.chats[0].id}"
            print(f"создан канал PAPA HUB ({env['HUB_CHAT_ID']})")
        hubc = await owner.get_entity(int(env["HUB_CHAT_ID"]))
        if "GENPLAN_BOT_TOKEN" not in env:
            env["GENPLAN_BOT_USERNAME"], env["GENPLAN_BOT_TOKEN"] = await create_bot(owner)
            print(f"бот создан: @{env['GENPLAN_BOT_USERNAME']}")
        bot = await owner.get_entity(env["GENPLAN_BOT_USERNAME"])
        rights = ChatAdminRights(post_messages=True, edit_messages=True, delete_messages=True)
        await owner(EditAdminRequest(channel=hubc, user_id=bot, admin_rights=rights, rank="PAPA"))
        print("бот — админ PAPA HUB")
        await owner(EditAdminRequest(channel=await owner.get_entity(int(env["TEST_CHANNEL_ID"])), user_id=bot,
                                     admin_rights=rights, rank="PAPA"))
        print("бот — админ PAPA TEST (теневой режим PaparazziUZ)")
        inv = await owner(ExportChatInviteRequest(hubc))
        try:
            await acc(ImportChatInviteRequest(inv.link.rsplit("+", 1)[-1].rsplit("/", 1)[-1]))
        except UserAlreadyParticipantError:
            pass
        print("аккаунт PAPA — участник PAPA HUB")
    finally:
        await owner.disconnect(); await acc.disconnect()
    ENV.parent.mkdir(mode=0o700, exist_ok=True)
    old = os.umask(0o077)
    try:
        ENV.write_text("".join(f"{k}={v}\n" for k, v in env.items()))
    finally:
        os.umask(old)
    os.chmod(ENV, 0o600)
    print(f"GENPLAN_SETUP_OK бот @{env['GENPLAN_BOT_USERNAME']}")


asyncio.run(main())
