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


def bot_send_kb(token: str, chat_id: int, text: str, markup: dict | None, urlopen=None) -> bool:
    """26.10: одно сообщение с кнопками (карточка выбора источников). Текст ≤ 4096."""
    import json
    import urllib.parse
    import urllib.request
    urlopen = urlopen or urllib.request.urlopen
    q = {"chat_id": chat_id, "text": text[:4096], "disable_web_page_preview": "true"}
    if markup:
        q["reply_markup"] = json.dumps(markup, ensure_ascii=False)
    try:
        with urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data=urllib.parse.urlencode(q).encode(),
                     timeout=30) as r:
            return bool(json.loads(r.read()).get("ok"))
    except Exception as e:                      # токен в тексте ошибки не печатаем
        print(f"BOT_SEND_FAIL: {type(e).__name__}", flush=True)
        return False


async def reports_channel_id(client: TelegramClient) -> int | None:
    """id канала «PAPA ОТЧЁТЫ» (ищем по названию среди чатов аккаунта) или PAPA_REPORTS_CHANNEL_ID."""
    import os
    if os.environ.get("PAPA_REPORTS_CHANNEL_ID"):
        return int(os.environ["PAPA_REPORTS_CHANNEL_ID"])
    async for d in client.iter_dialogs():
        if d.is_channel and not d.is_group and REPORTS_CHANNEL in (d.title or "").lower().replace("ë", "ё"):
            return int(f"-100{d.entity.id}")
    return None


def owner_bot() -> tuple[str, list[int]]:
    """20.10 владелец: отчёты — прямо в бот (главный пульт), без отдельных каналов.
    Токен и id владельца — /etc/papa-owner-bot.env (OWNER_BOT_TOKEN, OWNER_IDS)."""
    import os
    tok = os.environ.get("OWNER_BOT_TOKEN", "")
    ids = [int(x) for x in os.environ.get("OWNER_IDS", "").split(",") if x.strip().lstrip("-").isdigit()]
    return tok, ids


async def send_report(client: TelegramClient, text: str) -> bool:
    """Отчёт → владельцу в главный бот-пульт (20.10). Нет — по-старому: «PAPA ОТЧЁТЫ» / PAPA TEST GROUP. «Избранное» — НИКОГДА."""
    import os
    tok, ids = owner_bot()
    if tok and ids and all(bot_send(tok, o, text) for o in ids):
        return True
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


def bot_send_album(token: str, chat_id: int, images: list[bytes], caption: str = "", urlopen=None) -> bool:
    """18.10: отчёт картинками — одним альбомом (sendMediaGroup), подпись у первой картинки."""
    import json
    import urllib.request
    import uuid
    urlopen = urlopen or urllib.request.urlopen
    b = uuid.uuid4().hex
    media, parts = [], []
    for i, img in enumerate(images[:10]):
        m = {"type": "photo", "media": f"attach://p{i}"}
        if i == 0 and caption:
            m["caption"] = caption[:1024]
        media.append(m)
        parts.append((f"p{i}", f"p{i}.png", "image/png", img))
    body = bytearray()

    def field(name: str, value: bytes, filename: str | None = None, ctype: str | None = None):
        body.extend(f"--{b}\r\n".encode())
        disp = f'form-data; name="{name}"' + (f'; filename="{filename}"' if filename else "")
        body.extend(f"Content-Disposition: {disp}\r\n".encode())
        if ctype:
            body.extend(f"Content-Type: {ctype}\r\n".encode())
        body.extend(b"\r\n" + value + b"\r\n")

    field("chat_id", str(chat_id).encode())
    field("media", json.dumps(media, ensure_ascii=False).encode())
    for name, fn, ct, data in parts:
        field(name, data, fn, ct)
    body.extend(f"--{b}--\r\n".encode())
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMediaGroup", data=bytes(body),
                                 headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    try:
        with urlopen(req, timeout=60) as r:
            return bool(json.loads(r.read()).get("ok"))
    except Exception as e:                      # токен в тексте ошибки не печатаем
        print(f"BOT_ALBUM_FAIL: {type(e).__name__}", flush=True)
        return False


async def send_report_cards(client: TelegramClient, images: list[bytes], caption: str) -> bool:
    """Картинки → владельцу в главный бот-пульт (20.10); нет — «PAPA ОТЧЁТЫ» / PAPA TEST GROUP. «Избранное» — НИКОГДА."""
    import io
    import os
    tok, ids = owner_bot()
    if tok and ids and all(bot_send_album(tok, o, images, caption) for o in ids):
        return True
    token = os.environ.get("PAPA_TEST_BOT_TOKEN", "")
    if token:
        ch = await reports_channel_id(client)
        if ch is not None and bot_send_album(token, ch, images, caption):
            return True
        print("REPORTS_CHANNEL_FAIL: альбом в «PAPA ОТЧЁТЫ» не ушёл — шлю в PAPA TEST GROUP", flush=True)
    to = await report_target(client)
    if to is None:
        print("REPORT_NOT_SENT: PAPA TEST GROUP не найдена среди чатов аккаунта Разведки", flush=True)
        return False
    files = []
    for i, img in enumerate(images):
        f = io.BytesIO(img)
        f.name = f"razvedka_{i + 1}.png"
        files.append(f)
    await client.send_file(to, files, caption=caption[:1024])
    return True
