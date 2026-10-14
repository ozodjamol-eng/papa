"""Адаптер к Telegram через официальный клиентский API (Telethon).
Только чтение: папки, информация о каналах, история сообщений. Единственная запись —
необязательная отправка отчёта в «Избранное» самого аккаунта (send_report)."""
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


async def send_report(client: TelegramClient, text: str) -> None:
    """Отправить отчёт в «Избранное» этого же аккаунта (никому другому)."""
    for i in range(0, len(text), 3900):
        await client.send_message("me", text[i:i + 3900], link_preview=False)
