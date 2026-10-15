"""ИИ-редактор (Fabrika): переписывает подпись к посту так, как владелец делал вручную через ChatGPT.
Ключ — ANTHROPIC_API_KEY в /etc/papa-genplan/ai.env (вводит владелец на сервере). Дневной лимит вызовов — AI_DAILY_LIMIT."""
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
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


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
    body = {"model": MODEL, "max_tokens": 800, "system": SYSTEM.format(title=title),
            "messages": [{"role": "user", "content": f"Манба матни:\n\n{text[:4000]}"}]}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json", "anthropic-version": "2023-06-01",
                                          "x-api-key": os.environ["ANTHROPIC_API_KEY"]})
    try:
        if http:
            data = http(req)
        else:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise AIError(f"ИИ ответил ошибкой {e.code}") from None
    except Exception as e:  # noqa: BLE001
        raise AIError(f"ИИ недоступен: {type(e).__name__}") from None
    out = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip()
    if not out:
        raise AIError("ИИ вернул пустой ответ")
    if out.strip().upper() in ("РАД", "RAD"):
        raise AIError("ИИ считает материал неподходящим (оскорбительный, провокационный или недостоверный)")
    return out
