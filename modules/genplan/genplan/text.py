"""Подготовка текста поста: убрать чужие подписи (@канал, t.me/…), добавить свою подпись.
Рекламу не трогаем — у рекламодателя свои контакты."""
from __future__ import annotations

import re

MENTION = re.compile(r"(?<![\w.])@[A-Za-z][A-Za-z0-9_]{3,31}\b")
TME = re.compile(r"(?:https?://)?(?:www\.)?(?:t\.me|telegram\.me)/[^\s)]+", re.I)
EMPTY_LABEL = re.compile(r"^[\s👉➡️🔗📢✅❗️|:—–-]*$")


def strip_sources(text: str, keep: tuple[str, ...] = ()) -> str:
    keep_l = {k.lower().lstrip("@") for k in keep}
    t = TME.sub(lambda m: m.group(0) if m.group(0).rsplit("/", 1)[-1].lower() in keep_l else "", text or "")
    t = MENTION.sub(lambda m: m.group(0) if m.group(0)[1:].lower() in keep_l else "", t)
    lines = [ln.rstrip() for ln in t.splitlines()]
    lines = [ln for ln in lines if not (ln.strip() and EMPTY_LABEL.match(ln))]
    out = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    return re.sub(r"[ \t]{2,}", " ", out)


def pick_hook(ch: dict, rubric: str | None, n: int) -> str:
    """Нижний хук: раз в cross.every постов — переход в соседний канал; иначе хук рубрики; иначе общий.
    n — номер материала: хуки чередуются и не повторяются подряд."""
    cross = ch.get("cross") or {}
    every = int(cross.get("every", 0) or 0)
    if every and cross.get("text") and n % every == every - 1:
        return cross["text"]
    pool = (ch.get("rubric_hooks") or {}).get(rubric or "") or ch.get("hooks") or []
    if isinstance(pool, str):
        return pool
    return pool[n % len(pool)] if pool else ""


def finalize(text: str, signature: str, is_ad: bool = False, own: tuple[str, ...] = (),
             hook: str = "", limit: int | None = None) -> str:
    """Текст поста: чужие подписи убраны, внизу — хук и наша подпись. При лимите (подпись к медиа — 1024)
    сокращается текст, а не подпись."""
    if is_ad:
        return (text or "").strip()
    body = strip_sources(text, keep=own)
    for line in (signature, hook):
        if line:
            body = "\n".join(ln for ln in body.splitlines() if ln.strip() != line.strip()).strip()
    footer = "\n".join(x for x in (hook, signature) if x)
    if limit and footer and len(body) + len(footer) + 2 > limit:
        room = limit - len(footer) - 3
        body = (body[:max(room, 0)].rstrip() + "…") if room > 0 else ""
    out = f"{body}\n\n{footer}" if body and footer else (body or footer)
    return out[:limit] if limit else out
