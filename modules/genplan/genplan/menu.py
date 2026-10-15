"""Постоянная панель владельца в чате с ботом (кнопки внизу; сворачивается и открывается значком ⌘ в поле ввода)."""
from __future__ import annotations

import datetime as dt

from . import plan, service, smart, store

B_DAVRA, B_PAP, B_XOJ = "🎉 Давра", "⭐ Paparazzi", "📍 Хўжаобод"
B_ALL, B_QUEUE, B_TODAY, B_HELP, B_NAMAZ = "📅 План — все", "📋 Очередь", "📊 Итог дня", "❓ Помощь", "🕌 Намоз"
BY_BUTTON = {B_DAVRA: "davra", B_PAP: "paparazzi", B_XOJ: "xojaobod",
             "🎉 План Давра": "davra", "⭐ План Paparazzi": "paparazzi", "📍 План Хўжаобод": "xojaobod"}  # старые кнопки

KEYBOARD = {"keyboard": [[{"text": B_DAVRA}, {"text": B_PAP}, {"text": B_XOJ}],
                         [{"text": B_QUEUE}, {"text": B_TODAY}, {"text": B_NAMAZ}],
                         [{"text": B_ALL}, {"text": B_HELP}]],
            "resize_keyboard": True, "is_persistent": False,   # сворачивается значком ⌘ в поле ввода
            "input_field_placeholder": "Перешлите пост сюда"}

HELP = """Как работать:
1. Бросайте готовый пост прямо сюда (можно с чужим юзернеймом, можно альбом).
2. Нажмите рубрику — и всё: умное время бот поставит сам (✓ — рубрика, которую бот угадал).
   🚨 Срочный пост — сразу. 📦 В запас — на потом: выйдет сам, когда у рубрики будет пустой слот.
   🕐 Своё время, 📺 Другой канал — если нужно иначе. ⬅️ Отмена — убрать.
   ✏️ Текст — заменить текст своим. 🤖 ИИ-текст — переписать текст ИИ.
   Всё всегда бросайте сюда, в бот. PAPA HUB — внутренний склад бота, туда заходить не нужно.

Ссылка Instagram / TikTok / YouTube Shorts → бот сам скачает видео, поставит логотип,
перепишет текст (ИИ) и пришлёт готовый пост с карточкой.
Логотип: отправьте картинку файлом с подписью /logo
3. Под каждой карточкой видно, когда пост выйдет; время можно поменять.
4. 🌅 Утренний блок бот готовит сам: вечером присылает предпросмотр завтрашних постов
   («Бугун — … куни» и «Хайрли тонг»). Под каждым — «✅ Одобрить» и «🗑 Не публиковать»; выходит только одобренное.
   /morning — обзор и ещё раз прислать предпросмотры.

Бот сам: убирает чужие @ и ссылки, переводит латиницу в кириллицу, ставит наш юзернейм и призыв по смыслу,
держит промежуток между постами, музыку — не раньше 10:00, публикует с 07:00 до 22:00, предупреждает о повторах.

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
    return f"{_mode(cfg, channel)}\n" + smart.day_view(db, cfg, channel, now)


def queue_text(db, cfg: dict, now: dt.datetime | None = None) -> str:
    now = (now or dt.datetime.now(plan.TZ)).astimezone(plan.TZ)
    parts = []
    for c, ch in cfg["channels"].items():
        rows = store.scheduled(db, c)
        lines = [f"{'🆘' if r['urgent'] else '⏳'} {smart.fmt(dt.datetime.fromisoformat(r['scheduled_at']), now)} · "
                 f"{r['rubric'] or '—'}: {smart.short(r['text'], 45)}{' 🔒' if r['locked'] else ''}" for r in rows[:15]]
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
    if t in (B_NAMAZ, "/namaz"):
        from . import namaz
        now = dt.datetime.now(plan.TZ)
        return ("🕌 Скопируйте блок, поправьте время и пришлите одним сообщением "
                "(разделитель любой: 19:10, 19 10, 19.10).\nНа несколько дней — по блоку на день, у каждого своя дата.\n\n"
                + namaz.editor_text(db, now.date()))
    if t in ("/morning", "/утро"):
        from . import morning
        return morning.overview(db, cfg, dt.datetime.now(plan.TZ))
    if t in (B_HELP, "/start", "/help"):
        return HELP
    return None
