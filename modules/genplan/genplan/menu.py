"""Постоянная панель владельца в чате с ботом (кнопки внизу; сворачивается и открывается значком ⌘ в поле ввода)."""
from __future__ import annotations

import datetime as dt

from . import plan, service, store

B_DAVRA, B_PAP, B_XOJ = "🎉 Давра", "⭐ Paparazzi", "📍 Хўжаобод"
B_ALL, B_QUEUE, B_TODAY, B_HELP = "📅 План — все", "📋 Очередь", "📊 Итог дня", "❓ Помощь"
BY_BUTTON = {B_DAVRA: "davra", B_PAP: "paparazzi", B_XOJ: "xojaobod",
             "🎉 План Давра": "davra", "⭐ План Paparazzi": "paparazzi", "📍 План Хўжаобод": "xojaobod"}  # старые кнопки

KEYBOARD = {"keyboard": [[{"text": B_DAVRA}, {"text": B_PAP}, {"text": B_XOJ}],
                         [{"text": B_QUEUE}, {"text": B_TODAY}],
                         [{"text": B_ALL}, {"text": B_HELP}]],
            "resize_keyboard": True, "is_persistent": False,   # сворачивается значком ⌘ в поле ввода
            "input_field_placeholder": "Перешлите пост сюда"}

HELP = """Как работать:
1. Пересылайте хорошие посты прямо сюда, в этот чат (или в канал PAPA HUB — тоже работает).
2. Под постом появятся кнопки: канал → рубрика. Пост встанет в ближайший слот по плану.
3. 🆘 Срочно — публикуется сразу. 🗑 Убрать — не публикуется.

Бот сам: убирает чужие @ и ссылки, переводит латиницу в кириллицу, ставит хук по смыслу и наш юзернейм.

Кнопки панели:
🎉 ⭐ 📍 — план канала на сегодня
⌘ — свернуть / открыть панель
📋 Очередь — что ждёт публикации
📊 Итог дня — что уже вышло
📅 План — все каналы сразу"""


def _mode(cfg, ch):
    return "🟢 работа" if service.channel_mode(cfg, ch) == "live" else "🧪 тест"


def plan_one(db, cfg: dict, channel: str, now: dt.datetime | None = None) -> str:
    now = (now or dt.datetime.now(plan.TZ)).astimezone(plan.TZ)
    ch = cfg["channels"][channel]
    entries = plan.build(channel, ch, now.date(), service.to_materials(store.queued(db, channel)), ads={},
                         published=store.published_today(db, channel, now.date().isoformat()), now=now)
    return f"{_mode(cfg, channel)}\n" + plan.render(ch["title"], entries)


def queue_text(db, cfg: dict) -> str:
    parts = []
    for c, ch in cfg["channels"].items():
        rows = db.execute("SELECT rubric, text, urgent FROM materials WHERE status='queued' AND channel=? ORDER BY created_at",
                          (c,)).fetchall()
        lines = [f"{'🆘' if r['urgent'] else '•'} {r['rubric'] or '—'}: {(r['text'] or '(медиа)').strip().splitlines()[0][:50]}"
                 for r in rows[:15]]
        more = f"\n… ещё {len(rows) - 15}" if len(rows) > 15 else ""
        parts.append(f"📋 {ch['title']} — {len(rows)}\n" + ("\n".join(lines) + more if rows else "пусто"))
    return "\n\n".join(parts)


def today_summary(db, cfg: dict, now: dt.datetime | None = None) -> str:
    day = (now or dt.datetime.now(plan.TZ)).astimezone(plan.TZ).date().isoformat()
    parts = [f"📊 Итог дня — {day}"]
    for c, ch in cfg["channels"].items():
        n = {r["status"]: r["k"] for r in db.execute(
            "SELECT status, COUNT(*) k FROM publications WHERE channel=? AND slot_date=? GROUP BY status", (c, day))}
        q = db.execute("SELECT COUNT(*) FROM materials WHERE status='queued' AND channel=?", (c,)).fetchone()[0]
        parts.append(f"{ch['title']} ({_mode(cfg, c)}): ✅ {n.get('done', 0)} вышло · ❌ {n.get('failed', 0)} ошибок · ⏳ {q} в очереди")
    return "\n".join(parts)


def reply(db, cfg: dict, text: str) -> str | None:
    t = (text or "").strip()
    if t in BY_BUTTON:
        return plan_one(db, cfg, BY_BUTTON[t])
    if t in (B_ALL, "/plan", "/today"):
        return service.today_text(db, cfg)
    if t == B_QUEUE or t == "/queue":
        return queue_text(db, cfg)
    if t == B_TODAY:
        return today_summary(db, cfg)
    if t in (B_HELP, "/start", "/help"):
        return HELP
    return None
