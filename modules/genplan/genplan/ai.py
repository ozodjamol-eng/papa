"""ИИ-редактор (Fabrika): переводит и переписывает подпись к посту так, как владелец делал вручную через ChatGPT.
Основной (с 17.10, AI_PRIMARY=claude) — Anthropic Claude (ANTHROPIC_API_KEY); запасной — Google Gemini (GEMINI_API_KEY).
Если основной недоступен — пробуем запасной, иначе остаётся оригинал + кнопка ✏️.
Ключи — в /etc/papa-genplan/ai.env (вводит владелец на сервере). Дневной лимит вызовов — AI_DAILY_LIMIT."""
from __future__ import annotations

import datetime as dt
import json
import os
import urllib.error
import urllib.request

MODEL = os.environ.get("AI_MODEL", "claude-haiku-5-5")
LIMIT = int(os.environ.get("AI_DAILY_LIMIT", "150"))

SYSTEM = """Сен — «{title}» Telegram-каналининг тажрибали муҳарририсан. Вазифа: манба матнини канал учун жонли, ўқишли пост қилиб қайта ёзиш.
Қоидалар:
- Фақат ўзбек тилида, КИРИЛЛ алифбосида ёз (манба форсча, инглизча, русча ёки лотинча бўлса ҳам — таржима қил).
- Фактларни ўзгартирма: исмлар, саналар, рақамлар, нархлар, манзиллар айнан қолсин. Ўзингдан факт қўшма, ваҳима ва муболаға йўқ.
- Бошқа каналларнинг номлари, @юзернеймлари, ҳаволалари, хэштеглари, рекламаси — олиб ташла. ХЭШТЕГ ҚЎЙМА.
- Юзернейм ва имзо қўшма — уларни тизим ўзи қўшади.
Тузилма (намунадаги каби):
1) Биринчи қатор — БОШ ҲАРФЛАР билан қисқа сарлавҳа, олдида 1–2 мос эмодзи.
2) Кейин 2–3 қисқа хатбоши, ҳар бири мос эмодзи билан бошланади, 1–2 гапдан иборат.
3) Битта самимий савол-қатор (ўқувчини ўйлантирадиган), эмодзи билан.
4) Энг охирги қатор — мазмунга мос қисқа чақириқ: реакция қолдириш ёки дўстларга улашиш (масалан «👍 Ёққан бўлса, реакция қолдиринг!»). Изоҳ ЁЗИШНИ СЎРАМА.
Хатбошилар орасида бўш қатор. Жами 700 белгидан ошмасин.
Янгилик бўлса — холис ва аниқ, кўнгилочар бўлса — енгил ва самимий. Қайғули хабарда чақириқ ва ҳазил йўқ.
Матн ҳақоратли, сиёсий-провокацион ёки ишончсиз бўлса, фақат битта сўз қайтар: РАД.

Намуна (услуб учун):
🌧🤍 ЁМҒИРЛИ КУНЛАРНИНГ ЎЗГАЧА ГАШТИ БОР!

🚪 Эшик ортидаги манзарага бир қаранг… Худди жаннатнинг бир гўшасидек! 😍

☕ Ёмғирнинг майин шовқини, шинам муҳит ва қалбга ором берадиган сокинлик… 🌿

❤️ Сиз ҳам шундай жойда бир пиёла чой ичиб ўтиришни истармидингиз?

👍 Ёққан бўлса, реакция қолдиринг!

Фақат тайёр матнни қайтар, изоҳсиз."""


class AIError(Exception):
    pass


def available() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"))


def _gemini(system: str, user: str, http=None) -> str:
    body = {"systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"maxOutputTokens": 2048, "temperature": 0.6}}
    models = list(dict.fromkeys([os.environ.get("GEMINI_MODEL", "gemini-flash-latest"), "gemini-flash-latest"]))
    for i, model in enumerate(models):          # перегрузка (503) — следующая бесплатная модель Gemini
        req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                     data=json.dumps(body).encode(),
                                     headers={"content-type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]})
        try:
            data = http(req) if http else json.loads(urllib.request.urlopen(req, timeout=60).read())
            break
        except urllib.error.HTTPError as e:
            if e.code not in (500, 503, 404) or i == len(models) - 1:
                raise
    parts = ((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
    return "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()


def _claude(system: str, user: str, http=None) -> str:
    body = {"model": MODEL, "max_tokens": 800, "system": system, "messages": [{"role": "user", "content": user}]}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json", "anthropic-version": "2023-06-01",
                                          "x-api-key": os.environ["ANTHROPIC_API_KEY"]})
    data = http(req) if http else json.loads(urllib.request.urlopen(req, timeout=60).read())
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip()


def _order():
    """Порядок ИИ для текста. Решение владельца 17.10: основной — Anthropic Claude (AI_PRIMARY=claude),
    Gemini — запасной. Без AI_PRIMARY — как раньше (Gemini → Claude). Просмотр кадров (vision) — только Gemini."""
    g, c = ("Gemini", _gemini, "GEMINI_API_KEY"), ("Claude", _claude, "ANTHROPIC_API_KEY")
    return (c, g) if os.environ.get("AI_PRIMARY", "").strip().lower() == "claude" else (g, c)


def _count(db) -> int:
    from . import store
    k = "ai_calls_" + dt.date.today().isoformat()
    n = int(store.kv_get(db, k, "0")) + 1
    store.kv_set(db, k, n)
    return n


def rewrite(db, text: str, title: str, http=None) -> str:
    if not available():
        raise AIError("нет ключа ИИ")
    if not (text or "").strip():
        raise AIError("нет исходного текста — напишите текст кнопкой ✏️")
    return generate(db, SYSTEM.format(title=title), f"Манба матни:\n\n{text[:4000]}", http)


def generate(db, system: str, user: str, http=None) -> str:
    """Общий вызов: основной ИИ → (если не вышло) запасной. Для рерайта и утреннего блока."""
    if not available():
        raise AIError("нет ключа ИИ")
    if _count(db) > LIMIT:
        raise AIError(f"дневной лимит ИИ ({LIMIT}) исчерпан")
    providers = [(n, f) for n, f, k in _order() if os.environ.get(k)]
    out, errs = "", []
    for name, fn in providers:
        try:
            out = fn(system, user, http)
            if out:
                break
            errs.append(f"{name}: пустой ответ")
        except urllib.error.HTTPError as e:
            errs.append(f"{name}: {'лимит исчерпан' if e.code == 429 else f'ошибка {e.code}'}")
        except Exception as e:  # noqa: BLE001
            errs.append(f"{name}: недоступен ({type(e).__name__})")
    if not out and errs:
        raise AIError("; ".join(errs))
    if not out:
        raise AIError("ИИ вернул пустой ответ")
    if out.strip().upper() in ("РАД", "RAD"):
        raise AIError("ИИ считает материал неподходящим (оскорбительный, провокационный или недостоверный)")
    return out


VISION_LIMIT = int(os.environ.get("AI_VISION_LIMIT", "300"))


def vision(db, prompt: str, images: list[bytes], http=None) -> dict:
    """Gemini смотрит кадры (JPEG) и отвечает JSON. Только Gemini (бесплатный тариф); отдельный дневной лимит."""
    import base64
    from . import store
    if not os.environ.get("GEMINI_API_KEY"):
        raise AIError("нет ключа Gemini")
    k = "ai_vision_" + dt.date.today().isoformat()
    n = int(store.kv_get(db, k, "0")) + 1
    store.kv_set(db, k, n)
    if n > VISION_LIMIT:
        raise AIError(f"дневной лимит проверки кадров ({VISION_LIMIT}) исчерпан")
    parts = [{"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(b).decode()}} for b in images]
    body = {"contents": [{"role": "user", "parts": parts + [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.1, "responseMimeType": "application/json"}}
    # основная модель перегружена (503) — пробуем запасные модели Gemini (тоже бесплатные)
    models = list(dict.fromkeys([os.environ.get("GEMINI_MODEL", "gemini-flash-latest"), "gemini-flash-latest"]))
    data, err = None, None
    for model in models:
        req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                     data=json.dumps(body).encode(),
                                     headers={"content-type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]})
        try:
            data = http(req) if http else json.loads(urllib.request.urlopen(req, timeout=60).read())
            break
        except urllib.error.HTTPError as e:
            err = "лимит Gemini исчерпан" if e.code == 429 else f"Gemini: ошибка {e.code}"
            if e.code not in (500, 503, 404):
                break
        except Exception as e:  # noqa: BLE001
            err = f"Gemini недоступен ({type(e).__name__})"
    if data is None:
        raise AIError(err or "Gemini: нет ответа")
    parts = ((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
    raw = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
    raw = raw.strip("`").removeprefix("json").strip()
    try:
        return json.loads(raw)
    except ValueError:
        raise AIError(f"Gemini: непонятный ответ ({raw[:80]})") from None
