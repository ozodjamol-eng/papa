"""🏷 МАРКИРОВЩИК (01.11.2026, владелец: «ты перестал маркировать… сделать одного агента, который только этим занимается»).

Один агент — одна работа: ставит НАШУ метку (@юзернейм канала) на видео и фото перед выходом в канал.
Политика — docs/MARKIROVKA.md. Здесь — решение «метить или нет» и сама отрисовка.

Видео: метка «подъём» (решение владельца): выходит снизу по центру, поднимается и растворяется до середины кадра,
повторяется раз в 15 с. Фото: небольшая метка в правом верхнем углу, полупрозрачная.
Без надписей-заголовков (23.10: «дёшево») — только @юзернейм.
"""
from __future__ import annotations

from pathlib import Path

from . import media as M

# Рубрики, которые НЕ метим никогда
NEVER_RUBRICS = ("реклама", "муфтий минбари")
# Уже наше (метка вшита при сборке) — второй раз не метим
OWN_SOURCES = ("fabrika", "digest", "дайжест")
KINDS = ("video", "animation", "photo")
MAX_BOT_FILE = 20 * 1024 * 1024        # Bot API скачивает до 20 МБ
MAX_UPLOAD = 50 * 1024 * 1024          # и отправляет до 50 МБ


def mark_text(ch: dict) -> str:
    return ch.get("watermark") or "@" + ch["username"]


def decide(ch: dict, m) -> tuple[str | None, str]:
    """(вид медиа или None, причина). None — пост выходит без метки, причина — для отчёта Штаба."""
    import json
    keys = m.keys()
    rubric = (m["rubric"] or "").lower()
    if not m["has_media"]:
        return None, "текст"
    if any(rubric.startswith(r) for r in NEVER_RUBRICS):
        return None, "реклама/Муфтий — не метим"
    src = (m["source"] if "source" in keys else "") or ""
    if any(s in src.lower() for s in OWN_SOURCES):
        return None, "уже с нашей меткой"
    try:
        media = json.loads(m["media"] or "[]") if "media" in keys else []
    except ValueError:
        media = []
    if len(media) > 1:
        return None, "альбом — пока без метки"
    kind = media[0].get("type") if media else None
    if kind not in KINDS:
        return None, "не видео/фото"
    return kind, "метим"


def render(kind: str, src: Path, dst: Path, text: str) -> Path:
    """Нарисовать метку. Видео — без сжатия качества (crf 20), звук как есть."""
    logo = M.text_logo(text, dst.with_suffix(".wm.png"))
    try:
        if kind == "photo":
            return M.watermark_photo(src, logo, dst.with_suffix(".jpg"))
        out = M.watermark_video(src, logo, dst.with_suffix(".mp4"), crf=20, style="rise")
        if out.stat().st_size > MAX_UPLOAD:
            out = M.watermark_video(src, logo, dst.with_suffix(".mp4"), crf=26, style="rise")
        return out
    finally:
        dst.with_suffix(".wm.png").unlink(missing_ok=True)
