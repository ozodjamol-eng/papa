"""26.10 владелец: «система предлагает — я выбираю». Кнопки карточки выбора источников в PAPA ШТАБ.

Карточку присылает Разведка (razvedka.sources.card): по кнопке на кандидата `sw:t:<канал>:<рубрика>:<id>`
и «✅ Утверждаю» `sw:ok:<канал>`. Галочка переключается прямо в кнопке (☑/⬜) — состояние живёт в самом сообщении.
«✅ Утверждаю» записывает выбранных в choice.json (его читает куратор Разведки) и оставляет в сообщении
постоянную строку итога (всплывающие окна владелец не принимает). Утвердить можно повторно — список заменится.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
from pathlib import Path

CHOICE = Path(os.environ.get("SOURCES_CHOICE", "/var/lib/papa-sources-choice/choice.json"))
CHANNELS = {"xojaobod", "davra", "paparazzi"}
TZ = dt.timezone(dt.timedelta(hours=5))
_T = re.compile(r"^sw:t:([a-z]+):([a-z]+):(-?\d+)$")
_OK = re.compile(r"^sw:ok:([a-z]+)$")
_NAME = re.compile(r"^[☑⬜]\s*\d+\.\s*")


def toggle(markup: dict, data: str) -> dict:
    """Переключить галочку у кнопки с этим callback_data."""
    rows = []
    for row in markup.get("inline_keyboard", []):
        new = []
        for b in row:
            if b.get("callback_data") == data:
                t = b["text"]
                b = {**b, "text": ("⬜" + t[1:]) if t.startswith("☑") else ("☑" + t[1:])}
            new.append(b)
        rows.append(new)
    return {"inline_keyboard": rows}


def selected(markup: dict, channel: str) -> dict[str, list[dict]]:
    """Рубрика → выбранные (☑) источники этого канала."""
    out: dict[str, list[dict]] = {}
    for row in markup.get("inline_keyboard", []):
        for b in row:
            m = _T.match(b.get("callback_data", ""))
            if m and m.group(1) == channel and b.get("text", "").startswith("☑"):
                out.setdefault(m.group(2), []).append({"id": int(m.group(3)), "title": _NAME.sub("", b["text"])})
    return out


def save(channel: str, chosen: dict[str, list[dict]], path: Path = CHOICE, now: dt.datetime | None = None) -> dict:
    """Записать выбор канала (остальные каналы не трогаем). Атомарно; читать может группа (куратор Разведки)."""
    now = now or dt.datetime.now(TZ)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    data.setdefault("channels", {})[channel] = chosen
    data.setdefault("approved", {})[channel] = now.strftime("%d.%m.%Y %H:%M")
    data["version"] = 2
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name("." + path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.chmod(tmp, 0o640)
    os.replace(tmp, path)
    return data


def callback(bot, cq: dict, path: Path = CHOICE) -> str:
    data, msg = cq.get("data", ""), cq.get("message") or {}
    markup = msg.get("reply_markup") or {}
    where = {"chat_id": msg.get("chat", {}).get("id"), "message_id": msg.get("message_id")}
    m = _T.match(data)
    if m and m.group(1) in CHANNELS:
        try:
            bot("editMessageReplyMarkup", **where, reply_markup=toggle(markup, data))
        except Exception as e:  # noqa: BLE001 — двойное нажатие: «не изменилось» — не ошибка
            if "not modified" not in str(e):
                raise
        bot("answerCallbackQuery", callback_query_id=cq["id"])
        return "sw_toggle"
    m = _OK.match(data)
    if not m or m.group(1) not in CHANNELS:
        bot("answerCallbackQuery", callback_query_id=cq["id"], text="Неизвестная кнопка")
        return "bad"
    ch = m.group(1)
    chosen = selected(markup, ch)
    n = sum(len(v) for v in chosen.values())
    try:
        save(ch, chosen, path)
    except OSError as e:
        bot("answerCallbackQuery", callback_query_id=cq["id"], text="Не сохранилось — сообщу Claude")
        print(f"sources_choice save: {type(e).__name__}: {e}", flush=True)
        return "save_fail"
    text = re.sub(r"\n\n✅ УТВЕРЖДЕНО.*\Z", "", msg.get("text") or "", flags=re.S)
    stamp = dt.datetime.now(TZ).strftime("%d.%m %H:%M")
    names = "; ".join(x["title"] for v in chosen.values() for x in v) or "ничего — куратор работает по папке канала"
    text += f"\n\n✅ УТВЕРЖДЕНО {stamp} · источников: {n}\n{names}\n(можно поменять галочки и утвердить снова)"
    try:
        bot("editMessageText", **where, text=text[:4096], reply_markup=markup)
    except Exception as e:  # noqa: BLE001
        if "not modified" not in str(e):
            raise
    bot("answerCallbackQuery", callback_query_id=cq["id"])
    return "sw_ok"
