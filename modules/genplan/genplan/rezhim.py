"""📅 Режим дня по галочкам (06.11.2026, владелец: «даёшь мне режим дня по галочкам — поставлю галочку, значит
одобрено; не поставлю — этот пункт сегодня не работает»; выбрал путь А и пробу на неделю в КАТТА ДАВРА).

Путь А: по умолчанию все часы сетки ✅ — не открыл бот, день идёт как обычно. Снял галочку → этот час сегодня пустой:
запас и якорь его не закрывают, уже стоящий туда пост сетки возвращается в 📦 запас.
Протоколы не выключаются (🔒): намаз и Жума, оплаченная реклама, «Хайрли тонг», Муфтий 22:00, посты с твёрдым
временем владельца. Выбор вступает в силу только после «✅ Утверждаю» (правило 21.10), итог — строкой в карточке.
Карточка на завтра приходит в пульт канала в 21:30; на сегодня — кнопка «🗓 Режим дня» под «📅 СЕГОДНЯ».
Включение: [channels.<канал>] rezhim = true. Откат: удалить строку (выключенные часы сразу снова работают)."""
from __future__ import annotations

import datetime as dt
import json

from . import plan, smart, store

SEND_AT = "21:30"


def enabled(ch: dict) -> bool:
    return bool(ch.get("rezhim")) and smart.hourly(ch) is not None


def _key(kind: str, channel: str, day: dt.date) -> str:
    return f"rezhim_{kind}_{channel}_{day.isoformat()}"


def _load(db, kind: str, channel: str, day: dt.date) -> list[str]:
    try:
        return sorted(set(json.loads(store.kv_get(db, _key(kind, channel, day), "[]") or "[]")))
    except ValueError:
        return []


def _save(db, kind: str, channel: str, day: dt.date, hours) -> None:
    store.kv_set(db, _key(kind, channel, day), json.dumps(sorted(set(hours))))


def off_hours(db, channel: str, day: dt.date) -> list[str]:
    """Утверждённые выключенные часы дня («09», «13»)."""
    return _load(db, "off", channel, day)


def is_off(db, channel: str, t: dt.datetime) -> bool:
    t = t.astimezone(plan.TZ)
    return f"{t.hour:02d}" in off_hours(db, channel, t.date())


def _locked_hours(db, ch: dict, channel: str, day: dt.date) -> set[str]:
    out = {f"{t.astimezone(plan.TZ).hour:02d}" for t in smart.hour_slots(ch, day) if smart.is_minbar_hour(ch, t)}
    for m in store.scheduled(db, channel):              # пост с твёрдым временем владельца (🔒) — не снимаем
        x = dt.datetime.fromisoformat(m["scheduled_at"]).astimezone(plan.TZ)
        if x.date() == day and m["locked"] and smart.is_grid_post(m):
            out.add(f"{x.hour:02d}")
    return out


def items(db, cfg: dict, channel: str, day: dt.date, now: dt.datetime) -> list[tuple[str, str, bool]]:
    """Часы сетки, которые можно выключить: (час, рубрика, можно ли трогать). Прошедшие часы сегодня — не показываем."""
    ch = cfg["channels"][channel]
    locked = _locked_hours(db, ch, channel, day)
    out = []
    for t in smart.hour_slots(ch, day):
        if t < now:
            continue
        h = f"{t.astimezone(plan.TZ).hour:02d}"
        w = smart.hour_wants(ch, t)
        out.append((h, (w[0] if w else "пост"), h not in locked))
    return out


def card(db, cfg: dict, channel: str, day: dt.date, now: dt.datetime, note: str = "") -> tuple[str, dict]:
    ch = cfg["channels"][channel]
    draft = set(_load(db, "draft", channel, day))
    act = set(off_hours(db, channel, day))
    rows, line = [], []
    d = day.strftime("%Y%m%d")
    for h, rub, free in items(db, cfg, channel, day, now):
        mark = "🔒" if not free else ("⬜" if h in draft else "✅")
        line.append({"text": f"{mark} {h}:00 {rub}"[:30], "callback_data": f"rz:t:{channel}:{d}:{h}" if free else "rz:lk"})
        if len(line) == 2:
            rows.append(line); line = []
    if line:
        rows.append(line)
    changed = draft != act
    rows.append([{"text": "✅ Утверждаю" + (" (есть изменения)" if changed else ""), "callback_data": f"rz:ok:{channel}:{d}"}])
    rows.append([{"text": "↺ Всё включить", "callback_data": f"rz:all:{channel}:{d}"}])
    when = "сегодня" if day == now.date() else ("завтра" if day == now.date() + dt.timedelta(days=1) else f"{day:%d.%m}")
    off_txt = ", ".join(f"{h}:00" for h in sorted(act)) or "нет — всё работает"
    text = (f"📅 РЕЖИМ ДНЯ — {ch['title']} · {day:%d.%m} ({when})\n"
            "Нажмите на час: ✅ работает / ⬜ сегодня не выходит. Потом «✅ Утверждаю».\n"
            "🔒 всегда работает: намаз и Жума, оплаченная реклама, «Хайрли тонг», Муфтий 22:00, ваши посты с твёрдым временем.\n\n"
            f"Сейчас выключено: {off_txt}")
    if note:
        text += "\n\n" + note
    return text, {"inline_keyboard": rows}


def open_card(db, cfg: dict, channel: str, day: dt.date, now: dt.datetime) -> tuple[str, dict]:
    """Черновик = утверждённое: открывая карточку, начинаем с того, что действует."""
    _save(db, "draft", channel, day, off_hours(db, channel, day))
    return card(db, cfg, channel, day, now)


def _free_hours(db, channel: str, day: dt.date, hours: list[str]) -> int:
    """Выключенный час: уже стоящий туда пост сетки (не 🔒, не 🆘, не реклама) — обратно в 📦 запас. Возвращает число."""
    n = 0
    for m in store.scheduled(db, channel):
        x = dt.datetime.fromisoformat(m["scheduled_at"]).astimezone(plan.TZ)
        if x.date() == day and f"{x.hour:02d}" in hours and smart.is_grid_post(m) and not m["locked"]:
            store.update(db, m["id"], status="draft", stock=1, scheduled_at=None)
            n += 1
    return n


def approve(db, cfg: dict, channel: str, day: dt.date, now: dt.datetime) -> str:
    ch = cfg["channels"][channel]
    free = {h for h, _, ok in items(db, cfg, channel, day, now) if ok}
    draft = [h for h in _load(db, "draft", channel, day) if h in free]
    _save(db, "off", channel, day, draft)
    back = _free_hours(db, channel, day, draft)
    if not draft:
        return f"✅ Принято {now:%H:%M}: {day:%d.%m} в {ch['title']} работают все часы."
    return (f"✅ Принято {now:%H:%M}: {day:%d.%m} в {ch['title']} не выходят — " + ", ".join(f"{h}:00" for h in draft)
            + (f". В запас вернулось постов: {back}." if back else "."))


def callback(bot, db, cfg: dict, cq: dict, now: dt.datetime) -> str:
    from .hub import _edit
    chat, msg_id = cq["message"]["chat"]["id"], cq["message"]["message_id"]
    parts = cq["data"].split(":")
    if parts[1] == "lk":
        bot("answerCallbackQuery", callback_query_id=cq["id"], text="🔒 Это протокол — не выключается")
        return "rz_locked"
    kind, channel, d = parts[1], parts[2], parts[3]
    if channel not in cfg["channels"]:
        bot("answerCallbackQuery", callback_query_id=cq["id"])
        return "rz_missing"
    day = dt.datetime.strptime(d, "%Y%m%d").date()
    note = ""
    if kind == "open":
        t, kb = open_card(db, cfg, channel, day, now)
        bot("sendMessage", chat_id=chat, text=t, reply_markup=kb)
        bot("answerCallbackQuery", callback_query_id=cq["id"])
        return "rz_open"
    if kind == "t":
        h = parts[4]
        cur = set(_load(db, "draft", channel, day))
        cur.symmetric_difference_update({h})
        _save(db, "draft", channel, day, cur)
    elif kind == "all":
        _save(db, "draft", channel, day, [])
    elif kind == "ok":
        note = approve(db, cfg, channel, day, now)
    t, kb = card(db, cfg, channel, day, now, note)
    _edit(bot, chat, msg_id, t, kb)
    bot("answerCallbackQuery", callback_query_id=cq["id"])
    return "rz_" + kind


def today_button(cfg: dict, channel: str, now: dt.datetime) -> dict | None:
    """Кнопка под «📅 СЕГОДНЯ»: новых кнопок в панели не добавляем (03.11: «зачем мудришь»)."""
    if not enabled(cfg["channels"][channel]):
        return None
    return {"inline_keyboard": [[{"text": "🗓 Режим дня", "callback_data": f"rz:open:{channel}:{now:%Y%m%d}"}]]}


def evening_due(db, cfg: dict, now: dt.datetime) -> list[str]:
    """21:30–22:00 — каналы, которым пора прислать карточку на завтра (раз в день)."""
    if not (SEND_AT <= f"{now:%H:%M}" < "22:00"):
        return []
    out = []
    for c, ch in cfg["channels"].items():
        k = f"rezhim_sent_{c}_{now.date().isoformat()}"
        if enabled(ch) and not store.kv_get(db, k):
            store.kv_set(db, k, "1")
            out.append(c)
    return out


def day_lines(db, cfg: dict, channel: str, day: dt.date, now: dt.datetime) -> list[tuple[str, str]]:
    """Для «📅 СЕГОДНЯ»: выключенные часы честно видны в плане дня."""
    ch = cfg["channels"][channel]
    if not enabled(ch):
        return []
    out = []
    for h in off_hours(db, channel, day):
        t = plan.slot_time(day, f"{h}:00")
        if t >= now:
            w = smart.hour_wants(ch, t)
            out.append((f"{h}:00", f"⏸ {h}:00  {w[0] if w else 'пост'} — выключено на сегодня (режим дня)"))
    return out
