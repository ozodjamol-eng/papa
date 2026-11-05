"""⚡ МУҲИМ (05.11 владелец): Разведка нашла срочное полезное без политики и переслала в пульт канала.
Ключи пересланных постов — в общем файле muhim.json (пишет Разведка, читает пульт). Пост с таким ключом
не встаёт в сетку и не выходит сам: карточка «⚡ МУҲИМ» — 🆘 сразу в канал или 🗑. Новостной запрет 01.11 к нему не
применяется: это решение владельца 05.11 (срочное полезное — можно, политика/криминал/аварии — никогда)."""
from __future__ import annotations

import json
import os
from pathlib import Path

FILE = Path(os.environ.get("SOURCES_MUHIM", "/var/lib/papa-sources-choice/muhim.json"))
NOTE = "⚡ МУҲИМ — срочное полезное · 🆘 Срочно — сразу в группу · не нужно — 🗑"


def key_of(msg: dict) -> str | None:
    o = msg.get("forward_origin") or {}
    chat = o.get("chat") or msg.get("forward_from_chat") or {}
    mid = o.get("message_id") or msg.get("forward_from_message_id")
    if not chat.get("id") or not mid:
        return None
    return f"{chat['id']}:{mid}"


def hit(msgs: list[dict], path: Path | None = None) -> bool:
    """Пост (или альбом) пересылала Разведка как МУҲИМ?"""
    keys = {k for k in (key_of(m) for m in msgs) if k}
    if not keys:
        return False
    try:
        data = json.loads((path or FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return bool(keys & set((data.get("keys") or {}).keys()))
