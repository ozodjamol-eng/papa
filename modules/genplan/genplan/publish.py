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


def _bot_file(self, chat: str, path: str, caption: str = "") -> int:
    """Локальное видео (ролик погоды Fabrika) → канал через sendVideo (multipart)."""
    import uuid
    from pathlib import Path
    bnd = uuid.uuid4().hex
    parts = [f"--{bnd}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
             for k, v in (("chat_id", chat), ("caption", caption[:1024]), ("supports_streaming", "true"),
                          ("width", "1080"), ("height", "1920"), ("duration", "15"))]
    parts.append(f"--{bnd}\r\nContent-Disposition: form-data; name=\"video\"; filename=\"{Path(path).name}\"\r\n"
                 f"Content-Type: video/mp4\r\n\r\n".encode() + Path(path).read_bytes() + b"\r\n")
    parts.append(f"--{bnd}--\r\n".encode())
    req = urllib.request.Request(f"{self.base}/sendVideo", data=b"".join(parts),
                                 headers={"Content-Type": f"multipart/form-data; boundary={bnd}"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            res = json.loads(r.read())
    except urllib.error.HTTPError as e:
        res = json.loads(e.read() or b"{}")
    except Exception as e:  # noqa: BLE001
        raise PublishError(f"{type(e).__name__}: {e}") from None
    if not res.get("ok"):
        raise PublishError(res.get("description", "unknown"))
    return int(res["result"]["message_id"])


BotPublisher.publish_file = _bot_file


def _album_payload(media: list[dict], caption: str) -> list[dict]:
    kinds = {"photo": "photo", "video": "video", "document": "document", "audio": "audio"}
    out = [{"type": kinds.get(m["type"], "photo"), "media": m["file_id"]} for m in media if m["type"] in kinds][:10]
    if out:
        out[0]["caption"] = caption[:1024]
    return out


def _bot_album(self, chat: str, media: list[dict], caption: str) -> int:
    r = self.http("sendMediaGroup", {"chat_id": chat, "media": _album_payload(media, caption)})
    if not r.get("ok"):
        raise PublishError(r.get("description", "unknown"))
    return int(r["result"][0]["message_id"])


BotPublisher.publish_album = _bot_album


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

    async def publish_file(self, chat: str, path: str, caption: str = "") -> int:
        """Локальное видео (ролик погоды Fabrika) → группа от имени группы, как обычное видео (не файлом)."""
        try:
            from telethon.tl.types import DocumentAttributeVideo
            m = await self.c.send_file(chat, path, caption=caption[:1024], supports_streaming=True, mime_type="video/mp4",
                                       attributes=[DocumentAttributeVideo(duration=15, w=1080, h=1920, supports_streaming=True)])
        except Exception as e:  # noqa: BLE001
            raise PublishError(f"{type(e).__name__}: {e}") from None
        return int(m.id)

    async def publish_album(self, chat: str, hub_chat: int, hub_ids: list[int], caption: str) -> int:
        try:
            msgs = [m for m in await self.c.get_messages(hub_chat, ids=hub_ids) if m and m.media]
            if not msgs:
                raise PublishError("в хабе нет медиа альбома")
            res = await self.c.send_file(chat, [m.media for m in msgs], caption=[caption[:1024]] + [""] * (len(msgs) - 1))
        except PublishError:
            raise
        except Exception as e:  # noqa: BLE001
            raise PublishError(f"{type(e).__name__}: {e}") from None
        first = res[0] if isinstance(res, list) else res
        return int(first.id)
