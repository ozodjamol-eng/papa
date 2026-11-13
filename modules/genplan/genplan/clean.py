"""🧼 Тоза контент (13.11, владелец: «Исправь это, чтоб вообще такого не было»).
В Xo'jaobod City 24 под #ҲАЖВИЯ вышла картинка-твит с пошлой шуткой (18+); подписчик написал владельцу «Сизга ярашмеди».
Правило (core): в каналы не выходит пошлое — секс/интим, мат, обнажёнка, грубые оскорбления, алкоголь/наркотики как шутка,
насмешка над религией. Каналы семейные: рядом намоз вақтлари, дуо, реклама.

Последний предохранитель перед публикацией (service.publish_one), для всего, кроме рекламы и срочного 🆘 владельца:
  1) слова в подписи (без ИИ) — стоп-корни;
  2) кадры/картинка — Gemini читает и ТЕКСТ НА КАРТИНКЕ (любой язык) и смотрит изображение.
Пошлое → пост снят (rejected), владельцу строка в пульт. ИИ не ответил: юмор и «қизиқарли» из складов/источников ждут
(+1 ч, до 3 раз, потом сняты — «порядок важнее количества»); остальное выходит (проверка слов уже прошла).
Откат: `clean = false` в [channels.<канал>] или GATE = False."""
from __future__ import annotations

import re
import tempfile
import urllib.request
from pathlib import Path

GATE = True
STRICT = ("ҳажвия", "қизиқарли", "кулги", "видео")     # рубрики риска: без ответа ИИ не выходят
HOLDS = 3
MAX_IMAGES = 4

# корни: русский / узбекский (кириллица и латиница). Только однозначные — чтобы не снимать обычные посты.
BAD = re.compile(
    r"дроч|мастурб|порн|эроти|оргазм|проститу|минет|презерватив|голы[емх]\b|голая\b|сиськ|\bжоп|"
    r"\bсекс|\bинтим|бляд|\bбля\b|\bхуй|\bхуе|\bхуя|пизд|\bебат|\bебан|\bёбан|\bебал|\bсука\b|\bсуки\b|мудак|"
    r"шаҳвон|shahvon|фоҳиш|fohish|жалаб|jalab|қанжиқ|qanjiq|\bсик[иа]ш|\bsik[ia]sh|\bам[иг]нг|18\s*\+",
    re.IGNORECASE)

PROMPT = """Ты — строгий редактор семейного узбекского Telegram-канала (читают женщины, дети, старшие; рядом — время намаза и дуа).
Посмотри на кадры/картинку и ОБЯЗАТЕЛЬНО прочитай весь текст на них (русский, узбекский, английский). Подпись поста: «{text}».
Пост НЕЛЬЗЯ публиковать, если в картинке, тексте на ней или подписи есть хоть одно:
- секс, интим, мастурбация, намёки «ниже пояса», тема свиданий/постели в пошлом ключе;
- мат, грубая брань, оскорбления;
- обнажённое или откровенно одетое тело, эротика;
- алкоголь, наркотики, азартные игры как шутка или реклама;
- насмешка над религией, нацией, женщинами, больными; жестокость, кровь.
Сомневаешься — НЕЛЬЗЯ. Чистый бытовой юмор, животные, дети, полезное — можно.
Ответ — ТОЛЬКО JSON: {{"ok": true|false, "why": "<причина по-русски, до 8 слов; пусто если ok>"}}"""


def bad_words(text: str) -> str:
    """Найденный стоп-корень или ''."""
    m = BAD.search(text or "")
    return m.group(0).strip().lower() if m else ""


def applies(ch: dict, m) -> bool:
    if not GATE or ch.get("clean") is False:
        return False
    if (m["rubric"] or "").lower().startswith("реклама") or m["urgent"]:
        return False
    return True


def strict(m) -> bool:
    keys = m.keys()
    machine = bool(("auto" in keys and m["auto"]) or ("source" in keys and m["source"]))
    return machine and any((m["rubric"] or "").lower().startswith(r) for r in STRICT)


def photo_humor(m) -> bool:
    """13.11 владелец: «в БАНК · КУЛГИ фотографии нельзя». Юмор из складов/источников — только видео; фото и текст не выходят.
    Пост, который владелец сам бросил в пульт, не трогаем."""
    import json
    keys = m.keys()
    machine = bool(("auto" in keys and m["auto"]) or ("source" in keys and m["source"]))
    if not machine or not (m["rubric"] or "").lower().startswith("ҳажвия"):
        return False
    try:
        media = json.loads(m["media"] or "[]") if "media" in keys else []
    except ValueError:
        media = []
    return bool(media) and not any(x.get("type") in ("video", "animation") for x in media)


def images(pub, m) -> list[bytes]:
    """Картинки/кадры поста (до MAX_IMAGES). Пусто — файла нет или он больше 20 МБ (Bot API)."""
    import json
    from . import caption
    try:
        media = json.loads(m["media"] or "[]") if "media" in m.keys() else []
    except ValueError:
        media = []
    out: list[bytes] = []
    if pub is None:
        return out
    for md in media:
        if len(out) >= MAX_IMAGES:
            break
        if md.get("type") not in ("photo", "video", "animation", "document") or not md.get("file_id"):
            continue
        info = pub.http("getFile", {"file_id": md["file_id"]})
        fp = ((info or {}).get("result") or {}).get("file_path")
        if not fp:
            continue
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / ("p.jpg" if md["type"] == "photo" else "v.mp4")
            url = pub.base.replace("/bot", "/file/bot", 1) + "/" + fp
            with urllib.request.urlopen(url, timeout=120) as r:
                dst.write_bytes(r.read())
            out += caption._frames(dst, md["type"])[: MAX_IMAGES - len(out)]
    return out


def check(db, pub, m, look=None) -> tuple[str, str]:
    """('ok'|'bad'|'unknown', причина). look(prompt, images) -> dict — подмена ИИ в тестах."""
    from . import store
    if photo_humor(m):
        return "bad", "ҳажвия — фақат видео (расм/фото чиқмайди)"
    w = bad_words(m["text"] or "")
    if w:
        return "bad", f"слово «{w}» в подписи"
    if not m["has_media"]:
        return "ok", ""
    if db is not None and store.kv_get(db, f"clean_ok_{m['id']}"):
        return "ok", ""
    try:
        imgs = images(pub, m)
        if not imgs:
            return "unknown", "файл не скачать (больше 20 МБ?)"
        if look is None:
            from . import ai
            look = lambda p, i: ai.vision(db, p, i)   # noqa: E731
        v = look(PROMPT.format(text=(m["text"] or "")[:300]), imgs) or {}
    except Exception as e:  # noqa: BLE001 — лимит/сеть
        return "unknown", f"{type(e).__name__}: {str(e)[:60]}"
    if v.get("ok") is True:
        if db is not None:
            store.kv_set(db, f"clean_ok_{m['id']}", "1")
        return "ok", ""
    if v.get("ok") is False:
        return "bad", str(v.get("why") or "пошлое / не для семейного канала")[:80]
    return "unknown", "ИИ ответил непонятно"
