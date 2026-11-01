"""✍️ 01.11 владелец: «видео без подписи лучше не выставлять, а делать с подписью» → «Действуй».
Правило (core): в канал — только пост с подписью. Медиа без своего текста → ИИ смотрит кадры и пишет короткую подпись
узбекской кириллицей. Не вышло (лимит Gemini, большой файл, музыка без кадров) — пост ЖДЁТ, пустым не выходит и не удаляется.
Реклама и альбомы (подпись у первого кадра) не затрагиваются."""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path

CYR = re.compile(r"[А-Яа-яЎўҚқҒғҲҳЁё]")
PROMPT = """Сен — «{title}» Telegram-канали муҳарририсан. Бу видео/расм кадрларига қараб, пост учун қисқа матн ёз:
биринчи қатор — мос эмодзи билан қисқа сарлавҳа (БОШ ҲАРФЛАР), кейин 1 қисқа гап. Фақат ўзбек тилида, КИРИЛЛ алифбосида.
@юзернейм, ҳавола, хэштег, сана — ЙЎҚ. Кадрда нима борлигини ўйлаб топма — кўринганини ёз.
Кадрлар тушунарсиз, ёқимсиз, реклама ёки чет эл логотипи бўлса — {{"text": "SKIP"}}.
Жавоб — ФАҚАТ JSON: {{"text": "..."}}"""


def body_letters(text: str) -> int:
    from .text import strip_sources
    return sum(1 for ch in strip_sources(text or "") if ch.isalpha())


def needs_caption(m) -> bool:
    if not m["has_media"] or (m["rubric"] or "").lower().startswith("реклама"):
        return False
    return body_letters(m["text"] or "") < 3      # нет своих слов (только @, ссылки, эмодзи)


def is_ours(text: str) -> bool:
    letters = [ch for ch in (text or "") if ch.isalpha()]
    return len(letters) >= 10 and sum(1 for ch in letters if CYR.match(ch)) >= 0.6 * len(letters)


def _first_media(m) -> dict | None:
    try:
        media = json.loads(m["media"] or "[]") if "media" in m.keys() else []
    except ValueError:
        media = []
    return next((x for x in media if x.get("type") in ("photo", "video", "animation", "document")), None)


def _frames(path: Path, kind: str) -> list[bytes]:
    if kind == "photo":
        return [path.read_bytes()]
    from .morning import frames
    return frames(path, path.parent / "fr")


def write(db, pub, title: str, m) -> str:
    """Подпись по кадрам или '' (тогда пост ждёт). pub — BotPublisher бота, получившего материал."""
    from . import ai
    md = _first_media(m)
    if not md or not md.get("file_id") or pub is None:
        return ""
    info = pub.http("getFile", {"file_id": md["file_id"]})
    fp = ((info or {}).get("result") or {}).get("file_path")
    if not fp:                                    # Bot API отдаёт файлы до 20 МБ
        return ""
    with tempfile.TemporaryDirectory() as tmp:
        dst = Path(tmp) / ("p.jpg" if md["type"] == "photo" else "v.mp4")
        url = pub.base.replace("/bot", "/file/bot", 1) + "/" + fp
        with urllib.request.urlopen(url, timeout=120) as r:
            dst.write_bytes(r.read())
        imgs = _frames(dst, md["type"])
        if not imgs:
            return ""
        v = ai.vision(db, PROMPT.format(title=title), imgs)
    t = str((v or {}).get("text") or "").strip()
    return t if t.upper() != "SKIP" and is_ours(t) and "@" not in t and "http" not in t else ""


def ensure(db, pub, title: str, m, log=print) -> bool:
    """True — подпись есть (или не нужна); False — пост должен подождать."""
    if not needs_caption(m):
        return True
    from . import store
    try:
        t = write(db, pub, title, m)
    except Exception as e:  # noqa: BLE001 — лимит/сеть: просто ждём
        log(f"  подпись ИИ: {type(e).__name__}: {str(e)[:60]}")
        t = ""
    if not t:
        return False
    store.update(db, m["id"], text=t)
    return True
