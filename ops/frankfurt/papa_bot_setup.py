"""Боевой бот PAPA (по решению владельца): создать через @BotFather, сделать админом обоих каналов
с одним правом «Приглашать пользователей», поставить описания каналов, создать ссылки-заявки для панели.
Токен пишется только в /etc/papa-voronka/bot.env (0600) и никогда не печатается. Повторный запуск безопасен."""
import asyncio
import json
import os
import re
import sys
import urllib.parse
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, "/opt/papa/modules/razvedka")
from razvedka.telegram import client_from_env  # noqa: E402
from telethon.tl.functions.channels import EditAdminRequest  # noqa: E402
from telethon.tl.functions.messages import EditChatAboutRequest  # noqa: E402
from telethon.tl.types import ChatAdminRights  # noqa: E402

ENV = Path("/etc/papa-voronka/bot.env")
TOKEN_RE = re.compile(r"(\d{6,}:[A-Za-z0-9_-]{30,})")
NAME = "PAPA"
USERNAMES = ["PapaUzBot", "papa_kanal_bot", "papa_media_bot", "papauz_rasmiy_bot"]
SITE = "ozodjamol-eng.github.io/papa-site"
CHATS = {
    "ozodjamoll": "⭐ Шоу-бизнес янгиликлари ва юлдузлар ҳаёти\n"
                  "🎵 Янги қўшиқлар, клиплар ва премьералар — биринчи бўлиб шу ерда!\n"
                  f"🔥 Барча каналларимиз: {SITE}\n📩 Реклама: @Ozodjamol",
    "xojaobodcity24": "📍 Хўжаобод Сити 24 — ҳар куни фойдали ва қизиқарли!\n"
                      "📰 Энг долзарб янгиликлар • 🎬 фойдали видеолар • 😂 ҳажвия • 🩺 соғлиқ • 🎶 жонли мусиқа ва премьералар\n"
                      f"🔥 Барча каналларимиз: {SITE}\n📩 Реклама: @Ozodjamol",
}
BOT_DESC = ("PAPA — Хўжаобод Сити 24 ва PaparazziUZ каналларининг расмий боти. "
            "Ўзбекистондаги энг долзарб янгиликлар, фойдали ва қизиқарли видеолар 🔥")


def api(token, method, **p):
    data = json.dumps(p).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/{method}", data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read() or b"{}")


async def create_bot(c):
    async with c.conversation("BotFather", timeout=40) as conv:
        await conv.send_message("/cancel"); await conv.get_response()
        await conv.send_message("/newbot"); await conv.get_response()
        await conv.send_message(NAME); await conv.get_response()
        for u in USERNAMES:
            await conv.send_message(u)
            m = TOKEN_RE.search((await conv.get_response()).raw_text)
            if m:
                return u, m.group(1)
        raise SystemExit("BOT_USERNAMES_TAKEN: все варианты имени заняты — нужен другой")


def read_env():
    return dict(l.split("=", 1) for l in ENV.read_text().splitlines() if "=" in l) if ENV.exists() else {}


async def main():
    c = client_from_env()
    await c.connect()
    if not await c.is_user_authorized():
        raise SystemExit("NOT_AUTHORIZED")
    try:
        env = read_env()
        if not env.get("VORONKA_BOT_TOKEN"):
            username, token = await create_bot(c)
            ENV.parent.mkdir(mode=0o700, exist_ok=True)
            old = os.umask(0o077)
            try:
                ENV.write_text(f"VORONKA_BOT_USERNAME={username}\nVORONKA_BOT_TOKEN={token}\n")
            finally:
                os.umask(old)
            os.chmod(ENV, 0o600)
            print(f"бот создан: @{username}")
        env = read_env()
        token, username = env["VORONKA_BOT_TOKEN"], env["VORONKA_BOT_USERNAME"]
        print(f"бот: @{username}")
        api(token, "setMyName", name=NAME)
        api(token, "setMyDescription", description=BOT_DESC)
        api(token, "setMyShortDescription", short_description="Хўжаобод Сити 24 • PaparazziUZ")
        bot = await c.get_entity(username)
        rights = ChatAdminRights(invite_users=True)
        links = {}
        for chat, about in CHATS.items():
            ent = await c.get_entity(chat)
            try:
                await c(EditAdminRequest(channel=ent, user_id=bot, admin_rights=rights, rank="PAPA"))
                print(f"@{chat}: бот — админ (только приглашения)")
            except Exception as e:  # noqa: BLE001
                print(f"@{chat}: ADMIN_FAILED {type(e).__name__}: {e}")
            try:
                await c(EditChatAboutRequest(peer=ent, about=about))
                print(f"@{chat}: описание обновлено")
            except Exception as e:  # noqa: BLE001
                print(f"@{chat}: описание — {type(e).__name__}")
            if os.environ.get("PAPA_NEW_LINKS") != "1":
                continue  # ссылки уже созданы; новые — только PAPA_NEW_LINKS=1
            r = api(token, "createChatInviteLink", chat_id=f"@{chat}", name="panel", creates_join_request=True)
            if r.get("ok"):
                links[chat] = r["result"]["invite_link"]
                print(f"PANEL_LINK {chat} {links[chat]}")
            else:
                print(f"@{chat}: INVITE_FAILED {r.get('description')}")
    finally:
        await c.disconnect()


asyncio.run(main())
