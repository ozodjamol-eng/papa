"""ИИ-редактор (Fabrika): переводит и переписывает подпись к посту так, как владелец делал вручную через ChatGPT.
Основной — Google Gemini (бесплатный тариф, GEMINI_API_KEY + GEMINI_MODEL). Запасной — Anthropic Claude (ANTHROPIC_API_KEY, платный):
если Gemini недоступен или исчерпан лимит — пробуем Claude (если ключ есть), иначе остаётся оригинал + кнопка ✏️.
Ключи — в /etc/papa-genplan/ai.env (вводит владелец на сервере). Дневной лимит вызовов — AI_DAILY_LIMIT."""
from __future__ import annotations

import datetime as dt
import json
import os
import urllib.error
import urllib.request

MODEL = os.environ.get("AI_MODEL", "claude-haiku-5-5")
LIMIT = int(os.environ.get("AI_DAILY_LIMIT", "150"))

SYSTEM = """Сен — «{title}» Telegram-каналининг муҳарририсан. Вазифа: манба матнини канал учун қайта ёзиш.
Қоидалар:
- Фақат ўзбек тилида, КИРИЛЛ алифбосида ёз (лотинча ёки русча манба бўлса ҳам).
- Фактларни ўзгартирма: исмлар, саналар, рақамлар, нархлар, манзиллар — айнан қолсин. Ўзингдан факт қўшма, ваҳима ёки муболаға қилма.
- Бошқа каналларнинг номлари, @юзернеймлари, ҳаволалари, «обуна бўлинг», хэштеглари, рекламаси — олиб ташла.
- Тузилма: биринчи қатор — қисқа, жонли сарлавҳа (битта мос эмодзи билан); кейин 1–3 қисқа хатбоши. Жами 600 белгидан ошмасин.
- Изоҳ ёзишни сўрама. Охирига имзо, юзернейм ёки чақириқ қўшма — уларни тизим ўзи қўшади.
- Янгилик бўлса — холис ва аниқ оҳангда; кўнгилочар бўлса — енгил ва самимий.
- Матн ҳақоратли, сиёсий-провокацион ёки ишончсиз бўлса, фақат битта сўз қайтар: РАД.
Фақат тайёр матнни қайтар, изоҳсиз."""


class AIError(Exception):
    pass


def available() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"))


def _gemini(system: str, user: str, http=None) -> str:
    model = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
    body = {"systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"maxOutputTokens": 2048, "temperature": 0.6}}
    req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                 data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]})
    data = http(req) if http else json.loads(urllib.request.urlopen(req, timeout=60).read())
    parts = ((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
    return "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()


def _claude(system: str, user: str, http=None) -> str:
    body = {"model": MODEL, "max_tokens": 800, "system": system, "messages": [{"role": "user", "content": user}]}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json", "anthropic-version": "2023-06-01",
                                          "x-api-key": os.environ["ANTHROPIC_API_KEY"]})
    data = http(req) if http else json.loads(urllib.request.urlopen(req, timeout=60).read())
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip()


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
    if _count(db) > LIMIT:
        raise AIError(f"дневной лимит ИИ ({LIMIT}) исчерпан")
    system, user = SYSTEM.format(title=title), f"Манба матни:\n\n{text[:4000]}"
    providers = [(n, f) for n, f, k in (("Gemini", _gemini, "GEMINI_API_KEY"), ("Claude", _claude, "ANTHROPIC_API_KEY"))
                 if os.environ.get(k)]
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
