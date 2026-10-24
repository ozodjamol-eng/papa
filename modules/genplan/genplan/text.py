"""Подготовка текста поста: убрать чужие подписи (@канал, t.me/…), добавить свою подпись.
Рекламу не трогаем — у рекламодателя свои контакты."""
from __future__ import annotations

import re

from . import human, translit

MENTION = re.compile(r"(?<![\w.])@[A-Za-z][A-Za-z0-9_]{3,31}\b")
TME = re.compile(r"(?:https?://)?(?:www\.)?(?:t\.me|telegram\.me)/[^\s)]+", re.I)
EMPTY_LABEL = re.compile(r"^[\s👉➡️🔗📢✅❗️|:—–-]*$")
# 17.10: строки-«хвосты» источника без @: «Батафсил 👉 Тезкор24», «Подробнее: …»
MORE_LINE = re.compile(r"^\W*(батафсил|batafsil|подробнее|тўлиқ|to['ʻ’]?liq)\b", re.I)
# 18.10 владелец: «MANBA — izohlarda 👇», «Источник: …» и строки из одних названий соцсетей — хвост источника
SOURCE_LINE = re.compile(r"^\W*(manba|манба|источник|source|manbaa)\b|(izohlarda|изоҳларда|изохларда|в комментариях|"
                         r"комментарийда|izohda|изоҳда)", re.I)
SOCIAL = {"instagram", "инстаграм", "insta", "youtube", "ютуб", "tiktok", "тикток", "telegram", "телеграм", "facebook",
          "фейсбук", "vk", "вк", "veb", "веб", "web", "sayt", "сайт", "site", "website", "mediabank", "медиабанк",
          "ok.ru", "whatsapp", "ватсап", "tg", "twitter", "x", "threads", "ok", "одноклассники", "rutube", "likee", "va", "и", "ва"}


def source_tail(line: str) -> bool:
    """Строка — хвост источника: «Манба — изоҳларда», «Instagram | YouTube | Tiktok»."""
    t = line.strip()
    if not t:
        return False
    words = re.findall(r"[^\W\d_]+", t.lower())
    if words and all(w in SOCIAL for w in words) and any(w not in ("va", "и", "ва") for w in words):
        return True
    return len(t) <= 70 and bool(SOURCE_LINE.search(t))


LINK_WORDS = re.compile(r"(батафсил|batafsil|подробнее|бот\b|bot\b|instagram|инстаграм|youtube|ютуб|tiktok|тикток|facebook|сайт|"
                        r"sayt|канал|kanal|обуна|obuna|қўшил|qo['ʻ’]?shil|подпис|юклаб|yuklab|топувчи|topuvchi)", re.I)


def _u16(text: str, off: int, length: int) -> tuple[int, int]:
    """Смещения Telegram (UTF-16) → индексы строки Python."""
    b = (text or "").encode("utf-16-le")
    start = len(b[:off * 2].decode("utf-16-le", "ignore"))
    return start, start + len(b[off * 2:(off + length) * 2].decode("utf-16-le", "ignore"))


def link_junk(text: str, entities: list | None, own: tuple[str, ...] = ()) -> list[str]:
    """Решение 17.10 (А): чужие ссылки, спрятанные в слово («Тезкор24», «Инстаграм», «Yuklovchibot»), регулярка не видит —
    смотрим ссылки Telegram (entities). Строка с чужой ссылкой уходит целиком, если это «хвост»: короткая, рекламная
    или ссылка занимает её большую часть. Ссылка внутри обычной фразы — слово остаётся (ссылка всё равно пропадёт)."""
    own_l = {o.lower().lstrip("@") for o in own}
    lines = (text or "").split("\n")
    starts, pos = [], 0
    for ln in lines:
        starts.append(pos)
        pos += len(ln) + 1
    junk = []
    for e in entities or []:
        typ = e.get("type")
        if typ not in ("text_link", "url", "mention", "text_mention"):
            continue
        a, b = _u16(text, int(e.get("offset", 0)), int(e.get("length", 0)))
        word = text[a:b]
        target = (e.get("url") or word).strip().lower().split("?")[0].rstrip("/")
        name = target.rsplit("/", 1)[-1].lstrip("@")
        if name in own_l:                                   # наш канал — ссылку оставляем
            continue
        i = max(k for k, st in enumerate(starts) if st <= a)
        line = lines[i]
        rest = re.sub(r"[\W_]+", " ", line.replace(word, " ")).strip()
        if len(rest) <= 40 or LINK_WORDS.search(line) or len(word.strip()) >= 0.5 * len(line.strip()):
            if line.strip() and line not in junk:
                junk.append(line)
    return junk


def drop_lines(text: str, junk) -> str:
    if not junk:
        return text or ""
    bad = {j.strip() for j in junk if j.strip()}
    out = [ln for ln in (text or "").split("\n") if ln.strip() not in bad]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def strip_sources(text: str, keep: tuple[str, ...] = ()) -> str:
    keep_l = {k.lower().lstrip("@") for k in keep}
    t = TME.sub(lambda m: m.group(0) if m.group(0).rsplit("/", 1)[-1].lower() in keep_l else "", text or "")
    t = MENTION.sub(lambda m: m.group(0) if m.group(0)[1:].lower() in keep_l else "", t)
    lines = [ln.rstrip() for ln in t.splitlines()]
    lines = [ln for ln in lines if not (ln.strip() and (EMPTY_LABEL.match(ln) or (MORE_LINE.match(ln) and len(ln) <= 60)
                                                        or source_tail(ln)))]
    out = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    return re.sub(r"[ \t]{2,}", " ", out)


CTA = re.compile(r"(?i)(реакция|улашинг|обуна бўлинг|юборинг|қолдиринг|ёзинг|reaksiya|ulashing|obuna bo)")


def _stem_hit(text: str, words) -> bool:
    low = (text or "").lower()
    return any(re.search(r"(?<![\w])" + re.escape(w.lower()), low) if w[0].isalnum() else w in low for w in words)


def _topic_hit(text: str, t: dict) -> bool:
    """Тема совпала: есть её слово или шаблон (pattern, regex) — и нет слов-исключений (not_words: «совуқчилик» ≠ погода)."""
    low = (text or "").lower()
    clean = low
    for w in t.get("not_words", []):
        clean = re.sub(r"(?<![\w])" + re.escape(w.lower()) + r"\w*", " ", clean)
    if t.get("pattern") and re.search(t["pattern"], low, re.M):
        return True
    return _stem_hit(clean, t.get("words", []))


def topic_of(text: str, topics: list[dict]) -> dict | None:
    """Первая подходящая тема по смыслу текста (по ключевым словам). Порядок в настройках = приоритет."""
    return next((t for t in topics or [] if _topic_hit(text, t)), None)


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


PROMO = re.compile(r"(канал|kanal|обуна|obuna|қўшил|qo['ʻ’]?shil|подпис|кузатиб бор|kuzatib bor|бизни кузат|bizni kuzat|"
                   r"тезкор хабар|tezkor xabar|расмий саҳифа|rasmiy sahifa|ТВ ДА|TV DA|ҳаволани|havolani|улашинг|ulashing|tarqating|тарқатинг)", re.I)


def _caps_share(s: str) -> float:
    letters = [c for c in s if c.isalpha()]
    return sum(c.isupper() for c in letters) / len(letters) if letters else 0.0


def strip_promo(text: str) -> str:
    """Решение 16.10: главное — текст сверху; чужой «хвост» снизу (реклама источника: «… ХАБАРЛАР КАНАЛИ!», «обуна бўлинг»,
    название канала заглавными) убираем — внизу будут наши подпись и хук. Строки-рекламу чужого канала убираем и в середине."""
    paras = [p for p in re.split(r"\n\s*\n", (text or "").strip()) if p.strip()]
    def promo(p: str) -> bool:
        p = p.strip()
        return len(p) <= 220 and (bool(PROMO.search(p)) or (_caps_share(p) > 0.75 and len(p) <= 120 and len(paras) > 1))
    while len(paras) > 1 and promo(paras[-1]):            # хвост источника — снизу вверх
        paras.pop()
    out = []
    for p in paras:
        lines = [ln for ln in p.splitlines() if not (PROMO.search(ln) and re.search(r"(канал|kanal)", ln, re.I)
                                                       and (_caps_share(ln) > 0.6 or "!" in ln or len(ln) < 80))]
        if lines:
            out.append("\n".join(lines))
    return "\n\n".join(out).strip()


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


AD_TAG = re.compile(r"(?i)(reklama|реклама|ads?$|promo)")
LEAD_TAG = re.compile(r"^\s*(#[\wЀ-ӿ]+)")


def author_tag(text: str) -> tuple[str, str]:
    """24.10 владелец: «верх поста — мой, низ чистим». Хэштег, с которого начинается пост (первая непустая строка),
    поставил автор — его не убираем. Возвращает (хэштег, текст без него). Правило «один хэштег»: берём первый,
    остальные хэштеги той же строки уходят обычной чисткой. Латиница → кириллица (каналы кириллические)."""
    lines = (text or "").split("\n")
    i = next((k for k, ln in enumerate(lines) if ln.strip()), None)
    if i is None:
        return "", text or ""
    m = LEAD_TAG.match(lines[i])
    if not m or len(m.group(1)) < 3:
        return "", text or ""
    tag = m.group(1)
    if re.search(r"[A-Za-z]", tag):
        tag = "#" + translit.to_cyrillic(tag[1:]).upper()
    rest = lines[i][m.end():].strip()
    lines[i] = rest
    if not rest:
        del lines[i]
    return tag, "\n".join(lines)


def finalize(text: str, signature: str, is_ad: bool = False, own: tuple[str, ...] = (),
             hook: str = "", limit: int | None = None, tag: str = "", junk=(), signatures=(),
             author_first: bool = False) -> str:
    """Текст поста: чужие подписи и хэштеги убраны, первой строкой — наш хэштег рубрики, внизу — хук и наша подпись.
    При лимите (подпись к медиа — 1024) сокращается текст, а не подпись."""
    if is_ad:
        body = (text or "").strip()
        return f"{tag}\n{body}" if tag and not body.startswith(tag) else body
    if author_first:                              # 24.10: пост из пульта — хэштег автора сверху важнее хэштега бота
        atag, text = author_tag(text)
        if atag and not AD_TAG.search(atag):
            tag = atag
    body = strip_sources(human.clean(drop_lines(text, junk)), keep=own)
    body, _ = translit.auto(body)
    body = clean_hashtags(body)
    body = strip_promo(body)
    if tag:
        body = f"{tag}\n{body}".strip()
    if not hook:                                   # свой призыв в конце текста (ИИ или автор) — переносим под юзернейм
        lines = body.rstrip().splitlines()
        if lines and len(lines[-1]) <= 90 and CTA.search(lines[-1]):
            hook, body = lines[-1].strip(), "\n".join(lines[:-1]).rstrip()
    for line in (signature, hook, *signatures):          # наша подпись (любой из вариантов) не дублируется
        if line:
            body = "\n".join(ln for ln in body.splitlines() if ln.strip() != line.strip()).strip()
    footer = "\n".join(x for x in (signature, hook) if x)      # как в GENPLAN 5: текст → @юзернейм → призыв
    if limit and footer and len(body) + len(footer) + 2 > limit:
        room = limit - len(footer) - 3
        body = (body[:max(room, 0)].rstrip() + "…") if room > 0 else ""
    out = f"{body}\n\n{footer}" if body and footer else (body or footer)
    return out[:limit] if limit else out
