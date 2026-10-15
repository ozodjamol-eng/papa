"""Публикация: материал из хаба (PAPA HUB) → канал, без пометки «переслано» и без видимого автора.

BotPublisher     — для КАНАЛОВ: бот-админ копирует пост из хаба (copyMessage) с нашей подписью.
                   В канале пост виден от имени канала.
AccountPublisher — для ГРУППЫ: отдельный аккаунт (анонимный админ) отправляет пост — виден от имени группы.
Оба возвращают id опубликованного сообщения или бросают PublishError."""
from __future__ import annotations

import json
import urllib.error
import urllib.request


class PublishError(Exception):
    pass


class BotPublisher:
    def __init__(self, token: str, http=None):
        self.base = f"https://api.telegram.org/bot{token}"
        self.http = http or self._http

    def _http(self, method: str, payload: dict) -> dict:
        req = urllib.request.Request(f"{self.base}/{method}", data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            return json.loads(e.read() or b"{}")

    def publish(self, chat: str, text: str, hub_chat: int | None = None, hub_msg: int | None = None,
                has_media: bool = False, button: dict | None = None) -> int:
        extra = {"reply_markup": {"inline_keyboard": [[button]]}} if button else {}
        if hub_chat and hub_msg and has_media:
            r = self.http("copyMessage", {"chat_id": chat, "from_chat_id": hub_chat, "message_id": hub_msg,
                                          "caption": text[:1024], **extra})
        else:
            r = self.http("sendMessage", {"chat_id": chat, "text": text[:4096], "disable_web_page_preview": False,
                                          **extra})
        if not r.get("ok"):
            raise PublishError(r.get("description", "unknown"))
        return int(r["result"]["message_id"])


class AccountPublisher:
    """client — подключённый Telethon-клиент отдельного аккаунта (анонимный админ группы)."""

    def __init__(self, client):
        self.c = client

    async def publish(self, chat: str, text: str, hub_chat: int | None = None, hub_msg: int | None = None,
                      has_media: bool = False) -> int:
        try:
            if hub_chat and hub_msg and has_media:
                src = await self.c.get_messages(hub_chat, ids=hub_msg)
                if not src or not src.media:
                    raise PublishError("в хабе нет медиа этого поста")
                m = await self.c.send_file(chat, src.media, caption=text[:1024])
            else:
                m = await self.c.send_message(chat, text[:4096])
        except PublishError:
            raise
        except Exception as e:  # noqa: BLE001 — любая ошибка Telegram → понятная ошибка публикации
            raise PublishError(f"{type(e).__name__}: {e}") from None
        return int(m.id)
