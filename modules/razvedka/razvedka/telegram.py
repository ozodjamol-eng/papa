"""Адаптер к Telegram через официальный клиентский API (Telethon).
Только чтение: папки, информация о каналах, история сообщений. Единственная запись —
необязательная отправка отчёта в PAPA TEST GROUP (send_report)."""
from __future__ import annotations

import asyncio
import os

from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.sessions import StringSession
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.chatlists import CheckChatlistInviteRequest
from telethon.tl.types import (Channel, MessageMediaDocument, MessageMediaPhoto, MessageMediaPoll,
                               MessageMediaWebPage)


def client_from_env() -> TelegramClient:
    api_id = int(os.environ["PAPA_TG_API_ID"])
    api_hash = os.environ["PAPA_TG_API_HASH"]
    session = os.environ.get("PAPA_TG_SESSION", "")
    c = TelegramClient(StringSession(session), api_id, api_hash,
                       device_model="PAPA Razvedka", app_version="1.0", system_version="Linux")
    c.flood_sleep_threshold = 120  # короткие FloodWait библиотека переждёт сама
    return c


def _media(m) -> str:
    if m.grouped_id:
        return "album"
    md = m.media
    if md is None or isinstance(md, MessageMediaWebPage):
        return "text"
    if isinstance(md, MessageMediaPhoto):
        return "photo"
    if isinstance(md, MessageMediaPoll):
        return "poll"
    if isinstance(md, MessageMediaDocument):
        mime = getattr(getattr(md, "document", None), "mime_type", "") or ""
        return "video" if mime.startswith("video") else "doc"
    return "other"


def _reactions(m) -> int:
    r = getattr(m, "reactions", None)
    if not r or not getattr(r, "results", None):
        return 0
    return sum(int(x.count) for x in r.results)


class TelethonSource:
    def __init__(self, client: TelegramClient):
        self.c = client
        self._entities = {}

    async def _subscribers(self, ent) -> int | None:
        try:
            full = await self.c(GetFullChannelRequest(ent))
            return full.full_chat.participants_count
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds + 1)
            return None
        except Exception:
            return None

    async def channels(self, cfg: dict) -> list[dict]:
        found: dict[int, dict] = {}
        for f in cfg.get("folders", []):
            res = await self.c(CheckChatlistInviteRequest(slug=f["slug"]))
            for ch in getattr(res, "chats", []):
                if isinstance(ch, Channel) and ch.id not in found:
                    self._entities[ch.id] = ch
                    found[ch.id] = {"id": ch.id, "username": ch.username, "title": ch.title or str(ch.id),
                                    "folder": f.get("topic", "?"), "is_own": 0, "subscribers": None}
            await asyncio.sleep(2)
        for u in cfg.get("own_channels", []):
            try:
                ent = await self.c.get_entity(u)
            except Exception:
                continue
            self._entities[ent.id] = ent
            found[ent.id] = {"id": ent.id, "username": getattr(ent, "username", None),
                             "title": getattr(ent, "title", u), "folder": "свои", "is_own": 1, "subscribers": None}
        for ch in found.values():
            ch["subscribers"] = await self._subscribers(self._entities[ch["id"]])
            await asyncio.sleep(1)
        return list(found.values())

    async def messages(self, ch: dict, since):
        ent = self._entities[ch["id"]]
        async for m in self.c.iter_messages(ent, limit=None, wait_time=1):
            if m.date < since:
                break
            if m.action is not None:  # служебные сообщения (закреп, смена названия)
                continue
            yield {
                "id": m.id, "date": m.date, "views": m.views, "forwards": m.forwards,
                "replies": m.replies.replies if m.replies else None, "reactions": _reactions(m),
                "media": _media(m), "text": m.message or "", "is_forward": m.fwd_from is not None, "grp": m.grouped_id,
            }


REPORT_TITLE = "papa test group"     # 17.10 владелец: отчёты — в PAPA TEST GROUP, не в «Избранное»


async def report_target(client: TelegramClient):
    """Куда слать отчёты: PAPA TEST GROUP (ищем по названию среди чатов аккаунта) или PAPA_REPORT_CHAT."""
    import os
    if os.environ.get("PAPA_REPORT_CHAT"):
        return int(os.environ["PAPA_REPORT_CHAT"])
    async for d in client.iter_dialogs():
        if (d.is_group or d.is_channel) and REPORT_TITLE in (d.title or "").lower():
            return d.entity
    return None


REPORTS_CHANNEL = "papa отчёты"      # 17.10 владелец: все отчёты — в отдельный канал «PAPA ОТЧЁТЫ», шлёт бот, не профиль


def bot_send(token: str, chat_id: int, text: str, urlopen=None) -> bool:
    """Отправить текст ботом (Bot API) кусками по 3900. True — всё ушло."""
    import json
    import urllib.parse
    import urllib.request
    urlopen = urlopen or urllib.request.urlopen
    for i in range(0, len(text), 3900):
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": text[i:i + 3900],
                                       "disable_web_page_preview": "true"}).encode()
        try:
            with urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data=data, timeout=30) as r:
                if not json.loads(r.read()).get("ok"):
                    return False
        except Exception as e:                  # токен в тексте ошибки не печатаем
            print(f"BOT_SEND_FAIL: {type(e).__name__}", flush=True)
            return False
    return True


async def reports_channel_id(client: TelegramClient) -> int | None:
    """id канала «PAPA ОТЧЁТЫ» (ищем по названию среди чатов аккаунта) или PAPA_REPORTS_CHANNEL_ID."""
    import os
    if os.environ.get("PAPA_REPORTS_CHANNEL_ID"):
        return int(os.environ["PAPA_REPORTS_CHANNEL_ID"])
    async for d in client.iter_dialogs():
        if d.is_channel and not d.is_group and REPORTS_CHANNEL in (d.title or "").lower().replace("ë", "ё"):
            return int(f"-100{d.entity.id}")
    return None


async def send_report(client: TelegramClient, text: str) -> bool:
    """Отчёт → канал «PAPA ОТЧЁТЫ» ботом. Нет канала/бота — в PAPA TEST GROUP. В «Избранное» — НИКОГДА."""
    import os
    token = os.environ.get("PAPA_TEST_BOT_TOKEN", "")
    if token:
        ch = await reports_channel_id(client)
        if ch is not None and bot_send(token, ch, text):
            return True
        print("REPORTS_CHANNEL_FAIL: канал «PAPA ОТЧЁТЫ» не найден или бот не админ — шлю в PAPA TEST GROUP", flush=True)
    to = await report_target(client)
    if to is None:
        print("REPORT_NOT_SENT: PAPA TEST GROUP не найдена среди чатов аккаунта Разведки", flush=True)
        return False
    for i in range(0, len(text), 3900):
        await client.send_message(to, text[i:i + 3900], link_preview=False)
    return True
