"""Проверка: может ли бот публиковать в группе «от имени группы» (анонимный админ), без подписи бота.
Создаёт тестовую супергруппу «PAPA TEST GROUP» (один раз), делает тестового бота анонимным админом,
бот пишет сообщение, профиль владельца читает его и смотрит, от чьего имени оно видно."""
import asyncio
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, "/opt/papa/modules/razvedka")
from razvedka.telegram import client_from_env  # noqa: E402
from telethon.tl.functions.channels import CreateChannelRequest, EditAdminRequest, InviteToChannelRequest  # noqa: E402
from telethon.tl.types import ChatAdminRights  # noqa: E402

STATE = Path("/etc/papa-test/group.id")


def bot_api(token, method, **p):
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/{method}", data=json.dumps(p).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read() or b"{}")


async def main():
    env = dict(l.split("=", 1) for l in Path("/etc/papa-test/bot.env").read_text().splitlines() if "=" in l)
    token, uname = env["PAPA_TEST_BOT_TOKEN"], env["PAPA_TEST_BOT_USERNAME"]
    c = client_from_env()
    await c.connect()
    try:
        if STATE.exists():
            gid = int(STATE.read_text())
            grp = await c.get_entity(gid)
        else:
            r = await c(CreateChannelRequest(title="PAPA TEST GROUP", about="Тест PAPA. Закрытая.", megagroup=True))
            grp = r.chats[0]
            gid = int(f"-100{grp.id}")
            STATE.write_text(str(gid))
            print(f"создана тестовая группа {gid}")
        bot = await c.get_entity(uname)
        try:
            await c(InviteToChannelRequest(grp, [bot]))
        except Exception:  # noqa: BLE001
            pass
        await c(EditAdminRequest(channel=grp, user_id=bot, rank="",
                                 admin_rights=ChatAdminRights(anonymous=True, post_messages=True, delete_messages=True)))
        res = bot_api(token, "sendMessage", chat_id=gid, text="PAPA: проверка — от чьего имени видно это сообщение?")
        if not res.get("ok"):
            print(f"SEND_FAILED {res.get('description')}")
            return
        api_sender = "группа" if res["result"].get("sender_chat", {}).get("id") == gid else "бот"
        await asyncio.sleep(2)
        msg = (await c.get_messages(grp, ids=[res["result"]["message_id"]]))[0]
        seen = type(msg.from_id).__name__ if msg and msg.from_id else "нет автора"
        print(f"Bot API: отправитель = {api_sender}")
        print(f"глазами участника: from_id = {seen}")
        anon = api_sender == "группа" and seen in ("PeerChannel", "нет автора")
        print("ANON_OK — бот публикует от имени группы, без подписи бота" if anon else "ANON_NO — видно, что пишет бот")
    finally:
        await c.disconnect()


asyncio.run(main())
