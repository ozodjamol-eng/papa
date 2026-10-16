"""Подготовка текста поста: убрать чужие подписи (@канал, t.me/…), добавить свою подпись.
Рекламу не трогаем — у рекламодателя свои контакты."""
from __future__ import annotations

import re

from . import translit

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


CTA = re.compile(r"(?i)(реакция|улашинг|обуна бўлинг|юборинг|қолдиринг|ёзинг|reaksiya|ulashing|obuna bo)")


def _stem_hit(text: str, words) -> bool:
    low = (text or "").lower()
    return any(re.search(r"(?<![\w])" + re.escape(w.lower()), low) if w[0].isalnum() else w in low for w in words)


def topic_of(text: str, topics: list[dict]) -> dict | None:
    """Первая подходящая тема по смыслу текста (по ключевым словам). Порядок в настройках = приоритет."""
    return next((t for t in topics or [] if _stem_hit(text, t.get("words", []))), None)


def pick_hook(ch: dict, rubric: str | None, n: int, body: str = "", topics: list[dict] | None = None) -> str:
    """Нижний хук по смыслу текста.
    1) печальная тема (вафот, фожиа…) — без хука; 2) в конце текста уже есть призыв — свой не добавляем;
    3) раз в cross.every — переход в соседний канал; 4) тема текста; 5) рубрика; 6) общий. Хуки чередуются (n)."""
    t = topic_of(body, topics or [])
    if t and t.get("silent"):
        return ""
    lines = [ln for ln in (body or "").splitlines() if ln.strip() and not ln.strip().startswith("#")]
    tail = "\n".join(lines[-3:])                       # последние строки текста, без хэштегов
    if body and CTA.search(tail):
        return ""
    if t and t.get("hooks"):
        topic_pool = t["hooks"]
    else:
        topic_pool = None
    cross = ch.get("cross") or {}
    every = int(cross.get("every", 0) or 0)
    if every and cross.get("text") and n % every == every - 1:
        return cross["text"]
    pool = topic_pool or (ch.get("rubric_hooks") or {}).get(rubric or "") or ch.get("hooks") or []
    if isinstance(pool, str):
        return pool
    return pool[n % len(pool)] if pool else ""


HASHTAG_LINE = re.compile(r"^\s*(#[\w\u0400-\u04FF_]+[\s,]*)+$")


def strip_hashtags(text: str, keep: tuple[str, ...] = ()) -> str:
    """Строки, состоящие только из чужих хэштегов, убираем (наш канал хэштеги не ставит)."""
    keep_l = {k.lower() for k in keep}
    out = [ln for ln in (text or "").splitlines()
           if not (HASHTAG_LINE.match(ln) and not any(t.lower().lstrip("#") in keep_l for t in ln.split()))]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


TAG = re.compile(r"#([\w\u0400-\u04FF]+)")
TRAIL_TAGS = re.compile(r"(?:\s*#[\w\u0400-\u04FF]+)+[\s.,!]*$")


def clean_hashtags(text: str) -> str:
    """Утверждено 16.10: все чужие хэштеги убираем. Строка из одних хэштегов и хэштеги в конце строки — целиком;
    хэштег внутри фразы — только «#» (подчёркивания → пробелы), слово остаётся."""
    out = []
    for ln in strip_hashtags(text).splitlines():
        ln = TRAIL_TAGS.sub("", ln) if TAG.search(ln) and not HASHTAG_LINE.match(ln) else ln
        ln = TAG.sub(lambda m: m.group(1).replace("_", " "), ln)
        out.append(ln.rstrip())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def finalize(text: str, signature: str, is_ad: bool = False, own: tuple[str, ...] = (),
             hook: str = "", limit: int | None = None, tag: str = "") -> str:
    """Текст поста: чужие подписи и хэштеги убраны, первой строкой — наш хэштег рубрики, внизу — хук и наша подпись.
    При лимите (подпись к медиа — 1024) сокращается текст, а не подпись."""
    if is_ad:
        body = (text or "").strip()
        return f"{tag}\n{body}" if tag and not body.startswith(tag) else body
    body = strip_sources(text, keep=own)
    body, _ = translit.auto(body)
    body = clean_hashtags(body)
    if tag:
        body = f"{tag}\n{body}".strip()
    if not hook:                                   # свой призыв в конце текста (ИИ или автор) — переносим под юзернейм
        lines = body.rstrip().splitlines()
        if lines and len(lines[-1]) <= 90 and CTA.search(lines[-1]):
            hook, body = lines[-1].strip(), "\n".join(lines[:-1]).rstrip()
    for line in (signature, hook):
        if line:
            body = "\n".join(ln for ln in body.splitlines() if ln.strip() != line.strip()).strip()
    footer = "\n".join(x for x in (signature, hook) if x)      # как в GENPLAN 5: текст → @юзернейм → призыв
    if limit and footer and len(body) + len(footer) + 2 > limit:
        room = limit - len(footer) - 3
        body = (body[:max(room, 0)].rstrip() + "…") if room > 0 else ""
    out = f"{body}\n\n{footer}" if body and footer else (body or footer)
    return out[:limit] if limit else out
