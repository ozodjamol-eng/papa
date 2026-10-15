"""Создать тестовый контур PAPA через профиль владельца (по его разрешению):
закрытый канал «PAPA TEST» + тестовый бот (через @BotFather) администратором канала + пробный пост.
Токен бота пишется только в /etc/papa-test/bot.env (0600) и никогда не печатается.
Повторный запуск ничего не пересоздаёт."""
import asyncio
import json
import os
import re
import secrets
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, "/opt/papa/modules/razvedka")
from razvedka.telegram import client_from_env  # noqa: E402
from telethon.tl.functions.channels import CreateChannelRequest, EditAdminRequest  # noqa: E402
from telethon.tl.types import ChatAdminRights  # noqa: E402

ENV = Path("/etc/papa-test/bot.env")
TOKEN_RE = re.compile(r"(\d{6,}:[A-Za-z0-9_-]{30,})")


def bot_api(token: str, method: str, **params) -> dict:
    data = urllib.parse.urlencode(params).encode()
    with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/{method}", data=data, timeout=20) as r:
        return json.loads(r.read())


async def create_bot(c) -> tuple[str, str]:
    async with c.conversation("BotFather", timeout=40) as conv:
        await conv.send_message("/cancel")
        await conv.get_response()
        await conv.send_message("/newbot")
        await conv.get_response()
        await conv.send_message("PAPA Test")
        await conv.get_response()
        for _ in range(4):
            username = f"papa_test_{secrets.token_hex(3)}_bot"
            await conv.send_message(username)
            resp = (await conv.get_response()).raw_text
            m = TOKEN_RE.search(resp)
            if m:
                return username, m.group(1)
        raise SystemExit("BOTFATHER_NO_TOKEN: не удалось получить токен (имя занято или лимит BotFather)")


async def main() -> None:
    if ENV.exists():
        env = dict(l.split("=", 1) for l in ENV.read_text().splitlines() if "=" in l)
        print(f"уже создано: канал {env.get('PAPA_TEST_CHANNEL_ID')}, бот @{env.get('PAPA_TEST_BOT_USERNAME')}")
        r = bot_api(env["PAPA_TEST_BOT_TOKEN"], "sendMessage", chat_id=env["PAPA_TEST_CHANNEL_ID"],
                    text="PAPA TEST ✓ повторная проверка связи")
        print("TEST_POST_OK" if r.get("ok") else f"TEST_POST_FAILED {r.get('description')}")
        return
    c = client_from_env()
    await c.connect()
    if not await c.is_user_authorized():
        raise SystemExit("NOT_AUTHORIZED")
    try:
        r = await c(CreateChannelRequest(title="PAPA TEST", about="Тестовый канал PAPA. Закрытый. Только для проверок.",
                                         broadcast=True))
        ch = r.chats[0]
        chat_id = int(f"-100{ch.id}")
        print(f"канал создан: PAPA TEST (id {chat_id})")
        username, token = await create_bot(c)
        print(f"бот создан: @{username}")
        bot = await c.get_entity(username)
        rights = ChatAdminRights(post_messages=True, edit_messages=True, delete_messages=True, invite_users=True)
        await c(EditAdminRequest(channel=ch, user_id=bot, admin_rights=rights, rank="PAPA"))
        print("бот назначен администратором канала")
    finally:
        await c.disconnect()
    ENV.parent.mkdir(mode=0o700, exist_ok=True)
    old = os.umask(0o077)
    try:
        ENV.write_text(f"PAPA_TEST_CHANNEL_ID={chat_id}\nPAPA_TEST_BOT_USERNAME={username}\nPAPA_TEST_BOT_TOKEN={token}\n")
    finally:
        os.umask(old)
    os.chmod(ENV, 0o600)
    r = bot_api(token, "sendMessage", chat_id=chat_id, text="PAPA TEST ✓ тестовый контур работает")
    print("TEST_POST_OK" if r.get("ok") else f"TEST_POST_FAILED {r.get('description')}")


if __name__ == "__main__":
    asyncio.run(main())
