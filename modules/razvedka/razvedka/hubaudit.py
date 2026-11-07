"""🔎 07.11 владелец: «в МОТИВАЦИИ 60% — тарбия, и много копий. Что с другими хабами?»

Только чтение. По каждому хабу KATTA BANK: сколько постов, сколько копий (тот же файл видео/фото или тот же текст),
сколько без фото/видео и сколько не по теме хаба (Gemini читает подписи одним запросом на хаб).
Итог — коротко в журнал + полный список номеров в pub/hubaudit.json (для чистки, которую утверждает владелец)."""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import hubs

TOPIC = {
    "РАЗВЛЕКАТЕЛЬНО": "юмор, приколы, смешные и развлекательные видео",
    "ФОЙДАЛИК": "полезные советы, лайфхаки, знания",
    "ФОЙДАЛИК ОВКАТ": "еда, рецепты, польза продуктов, здоровье через питание",
    "МАЪНАВИЯТ": "религия, духовность, нравственность",
    "УЙДА БИЗНЕС": "бизнес из дома, заработок, ремесло, самозанятость",
    "МОТИВАЦИЯ": "мотивация: успех, цели, сила воли, не сдаваться, вдохновение к действию (НЕ воспитание детей, НЕ семейные наставления, НЕ религиозные поучения)",
    "Jonlik ijrolar": "музыка: живое исполнение песен, клипы (только видео)",
    "ИБРАТ": "поучительные жизненные истории с выводом",
    "ТАБРИКЛАР": "поздравления: доброе утро, жума муборак, спокойной ночи",
}


def _n(s: str) -> str:
    return re.sub(r"[\W_]+", "", s or "").casefold()


def media_key(m) -> str:
    d = getattr(m, "document", None)
    if d is not None:
        return f"d{d.id}"
    p = getattr(m, "photo", None)
    if p is not None:
        return f"p{p.id}"
    return ""


def dup_groups(items: list[dict]) -> list[list[int]]:
    """Группы копий: одинаковый файл или одинаковый текст (≥ 40 букв). Первый в группе — самый старый (оставить)."""
    parent: dict[int, int] = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            x = parent[x]
        return x

    seen: dict[str, int] = {}
    for it in sorted(items, key=lambda x: x["id"]):
        keys = [k for k in it["media"] if k]
        t = _n(it["text"])[:150]
        if len(t) >= 40:
            keys.append("t" + t)
        for k in keys:
            if k in seen:
                parent[find(it["id"])] = find(seen[k])
            else:
                seen[k] = it["id"]
    groups: dict[int, list[int]] = {}
    for it in items:
        groups.setdefault(find(it["id"]), []).append(it["id"])
    return [sorted(g) for g in groups.values() if len(g) > 1]


PROMPT = """Ниже подписи постов Telegram-хаба «{hub}». Тема хаба: {topic}.
Верни JSON {{"off": [номера постов, которые НЕ по теме хаба], "note": "1 короткая фраза: что чаще всего попадает не туда"}}.
Если подпись пустая или неясная — не считай её «не по теме». Только JSON.

{lines}"""


def ask(prompt: str) -> dict:
    from . import budget
    budget.gate()
    key = os.environ["GEMINI_API_KEY"].strip().strip('"').strip("'")
    base = "http://127.0.0.1:8790" if os.path.exists("/etc/papa-gemini-proxy/on") else "https://generativelanguage.googleapis.com"
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 4096, "responseMimeType": "application/json"}}
    for attempt in range(3):
        req = urllib.request.Request(f"{base}/v1beta/models/gemini-flash-latest:generateContent", data=json.dumps(body).encode(),
                                     headers={"content-type": "application/json", "x-goog-api-key": key})
        try:
            data = json.loads(urllib.request.urlopen(req, timeout=120).read())
            parts = ((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
            raw = "".join(p.get("text", "") for p in parts if not p.get("thought"))
            return json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
        except Exception:  # noqa: BLE001
            time.sleep(30 * (attempt + 1))
    return {}


async def run(client, out: Path, log=print) -> dict:
    want = {_n(h): h for h in hubs.HUBS}
    report, full = {}, {}
    async for d in client.iter_dialogs():
        if not (d.is_channel and not d.is_group and _n(d.title) in want):
            continue
        hub = want[_n(d.title)]
        items, albums = [], {}
        async for m in client.iter_messages(d.entity, limit=2000, wait_time=1):
            if m.action:
                continue
            if m.grouped_id and m.grouped_id in albums:
                a = albums[m.grouped_id]
                a["media"].append(media_key(m))
                a["text"] = a["text"] or (m.message or "")
                a["id"] = min(a["id"], m.id)
                continue
            it = {"id": m.id, "media": [media_key(m)], "text": m.message or "",
                  "video": bool(getattr(m, "video", None))}
            if m.grouped_id:
                albums[m.grouped_id] = it
            items.append(it)
        groups = dup_groups(items)
        extra = [i for g in groups for i in g[1:]]
        bare = [it["id"] for it in items if not any(it["media"])]
        off, note = [], ""
        lines = [(it["id"], (it["text"] or "").strip().replace("\n", " ")[:140]) for it in items if it["text"].strip()]
        if lines and os.environ.get("GEMINI_API_KEY") and hub in TOPIC:
            r = ask(PROMPT.format(hub=hub, topic=TOPIC[hub], lines="\n".join(f"{i}. {t}" for i, t in lines[:400])))
            off = [int(x) for x in r.get("off", []) if str(x).isdigit()]
            note = r.get("note", "")
        n = len(items) or 1
        report[hub] = (f"{len(items)} постов · копий {len(extra)} ({100 * len(extra) // n}%) · без фото/видео {len(bare)}"
                       f" · не по теме {len(off)} ({100 * len(off) // n}%)" + (f" — {note}" if note else ""))
        full[hub] = {"total": len(items), "dups": groups, "extra": extra, "bare": bare, "off": off, "note": note}
        log(f"  {hub}: {report[hub]}")
    out.mkdir(parents=True, exist_ok=True)
    (out / "hubaudit.json").write_text(json.dumps(full, ensure_ascii=False), encoding="utf-8")
    return report
