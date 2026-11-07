"""🚪 Ворота хабов KATTA BANK (07.11, владелец: «изначально пошёл неправильный подход… серьёзный подход нужен,
мы начали большое дело, и порядок должен быть»).

Раньше агенты (архивариус, тренды, куратор) клали в хаб всё подряд — копии, чужие темы (в МОТИВАЦИЯ ~60% «тарбия»),
картинки в музыку. Теперь любой пост в хаб проходит ворота (hubs.put):
  1) копия — тот же файл видео/фото или тот же текст уже есть в хабе → не кладём;
  2) музыка (Jonlik ijrolar) — только видео;
  3) тема — Gemini решает, какому хабу пост подходит: свой → кладём; другой → кладём туда; никакой → не кладём.
     Нет ответа ИИ (лимит/ошибка) → не кладём (порядок важнее количества; агент принесёт снова).
Откат: GATE = False."""
from __future__ import annotations

import json
import os
import re
import urllib.request

GATE = True
VIDEO_ONLY = {"Jonlik ijrolar"}
NO_TOPIC = {"ТАБРИКЛАР", "ТЕКШИРУВ"}                  # поздравления сортирует timing.kind (без ИИ)
SCAN = 3000

TOPIC = {
    "РАЗВЛЕКАТЕЛЬНО": "юмор, приколы, смешные и развлекательные видео",
    "ФОЙДАЛИК": "полезные советы, лайфхаки, знания, интересные факты",
    "ФОЙДАЛИК ОВКАТ": "еда, рецепты, польза продуктов, здоровье через питание",
    "МАЪНАВИЯТ": "религия, духовность, нравственность, воспитание, наставления старших, семейные ценности",
    "УЙДА БИЗНЕС": "бизнес из дома, заработок, ремесло, самозанятость",
    "МОТИВАЦИЯ": "мотивация: успех, цели, сила воли, не сдаваться, вдохновение к действию (НЕ воспитание, НЕ семейные наставления, НЕ религия)",
    "Jonlik ijrolar": "музыка: живое исполнение песен, клипы",
    "ИБРАТ": "поучительная жизненная история (сюжет) с выводом",
    "ТРЕНДЛАР": "тренды: вирусные новинки, необычное и удивительное в мире, новые технологии и ИИ, то, что сейчас все обсуждают",
}


def n(s: str) -> str:
    return re.sub(r"[\W_]+", "", s or "").casefold()


def media_key(m) -> str:
    d = getattr(m, "document", None)
    if d is not None:
        return f"d{d.id}"
    p = getattr(m, "photo", None)
    if p is not None:
        return f"p{p.id}"
    return ""


def text_key(text: str) -> str:
    t = n(text)[:150]
    return "t" + t if len(t) >= 80 else ""     # короткие общие подписи ИИ («😂 КУЛГИЛИ ВИДЕО…») не считаем копией


def keys_of(msgs: list, text: str) -> set[str]:
    out = {media_key(m) for m in msgs} | {text_key(text)} | {text_key(getattr(m, "message", "") or "") for m in msgs}
    return {k for k in out if k}


def hub_name(ent) -> str | None:
    from .hubs import HUBS
    from .hubs import key_of_title
    return key_of_title(getattr(ent, "title", "") or "")


_INDEX: dict[int, set[str]] = {}


async def index(client, ent) -> set[str]:
    """Ключи всего, что уже лежит в хабе (строится один раз за запуск, дальше пополняется сам)."""
    k = getattr(ent, "id", id(ent))
    if k not in _INDEX:
        s: set[str] = set()
        async for m in client.iter_messages(ent, limit=SCAN, wait_time=1):
            if not m.action:
                s |= keys_of([m], m.message or "")
        _INDEX[k] = s
    return _INDEX[k]


def remember(ent, keys: set[str]) -> None:
    _INDEX.setdefault(getattr(ent, "id", id(ent)), set()).update(keys)


def forget(ent) -> None:
    _INDEX.pop(getattr(ent, "id", id(ent)), None)


PROMPT = """Ты сортируешь посты Telegram по хабам. Хабы и их темы:
{hubs}

Пост (подпись): {text}

Какому ОДНОМУ хабу он подходит лучше всего? Если не подходит ни одному — "NONE".
Ответ только JSON: {{"hub": "<точное имя хаба или NONE>"}}"""


def ask(prompt: str) -> dict:
    from . import budget
    key = os.environ.get("GEMINI_API_KEY", "").strip().strip('"').strip("'")
    if not key:
        return {}
    try:
        budget.gate()
    except Exception:  # noqa: BLE001 — лимит
        return {}
    base = "http://127.0.0.1:8790" if os.path.exists("/etc/papa-gemini-proxy/on") else "https://generativelanguage.googleapis.com"
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 2048, "responseMimeType": "application/json"}}
    for model in ("gemini-flash-lite-latest", "gemini-flash-latest"):
        req = urllib.request.Request(f"{base}/v1beta/models/{model}:generateContent", data=json.dumps(body).encode(),
                                     headers={"content-type": "application/json", "x-goog-api-key": key})
        try:
            data = json.loads(urllib.request.urlopen(req, timeout=60).read())
            parts = ((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
            raw = "".join(p.get("text", "") for p in parts if not p.get("thought"))
            return json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
        except Exception:  # noqa: BLE001
            continue
    return {}


def topic_of(text: str) -> str | None:
    """Имя хаба по смыслу; 'NONE' — никуда; None — ИИ не ответил."""
    if not (text or "").strip():
        return None
    r = ask(PROMPT.format(hubs="\n".join(f"- {h}: {t}" for h, t in TOPIC.items()), text=text.strip()[:700]))
    h = str(r.get("hub") or "").strip()
    if h.upper() == "NONE":
        return "NONE"
    return next((x for x in TOPIC if n(x) == n(h)), None)
