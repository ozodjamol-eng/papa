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


def finalize(text: str, signature: str, is_ad: bool = False, own: tuple[str, ...] = ()) -> str:
    if is_ad:
        return (text or "").strip()
    body = strip_sources(text, keep=own)
    if signature and signature not in body:
        body = f"{body}\n\n{signature}" if body else signature
    return body
