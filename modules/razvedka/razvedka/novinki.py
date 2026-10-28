"""🆕 Новинки сервисов (решение владельца 28.10): раз в неделю — новые модели и функции у сервисов, которыми работает Фабрика.

Почему: 28.10 владелец сам заметил Eleven v4 (баннер в ElevenLabs) — узбекская озвучка сразу стала без ошибок.
GitHub-разведка такое не ловит (это не открытый код), поэтому отдельный раздел: Gemini с поиском Google смотрит
новости/changelog сервисов за последние 7 дней и честно оценивает пользу для PAPA.
Отчёт — владельцу в главный бот-пульт (как все отчёты Разведки). Ничего не ставит и не покупает — только советует.
Расход: бесплатная квота Gemini (≈ 0 $)."""
from __future__ import annotations

import datetime as dt
import json
import os
import re
from pathlib import Path

from .trend import TrendError, gemini_ask

TZ = dt.timezone(dt.timedelta(hours=5))
HISTORY_KEEP = 120

SERVICES = [
    ("ElevenLabs", "озвучка, клон голоса, музыка, звуки — у нас Starter, голоса OZOD JAMOL на eleven_v4"),
    ("Google Flow / Veo / Gemini / Nano Banana", "у нас Google AI Pro: картинки и оживление (Omni Flash), «Уши» на Gemini"),
    ("Kling", "картинка → видео"),
    ("Higgsfield", "ИИ-видео шаблоны и тренды"),
    ("Suno", "своя музыка — годовая подписка"),
    ("ByteDance Seedance / Seedream / Dreamina", "дешёвое видео и картинки"),
    ("MiniMax Hailuo, Vidu, Runway, Luma", "альтернативы для видео"),
    ("Telegram и Instagram (Meta)", "новые функции каналов, ботов, Reels, API — наши площадки"),
]

TASK = """Сегодня {today}. Найди в интернете НОВЫЕ модели, функции и изменения цен, вышедшие за последние 7 дней
(с {since}) у этих сервисов (в скобках — зачем они нам):
{services}

Бери только подтверждённое официальным источником (сайт/блог/changelog/документация сервиса). Слухи — не бери.
Не повторяй уже показанное: {seen}

Ответ строго по-русски, коротко, для Telegram (без таблиц и markdown-заголовков), до 2200 знаков:
🆕 НОВИНКИ СЕРВИСОВ — неделя до {today}
N) Сервис — что вышло (1 строка простыми словами)
   Польза для нас: где в PAPA/Фабрике и что улучшит (1 строка)
   Вердикт: ✅ пробуем сейчас / ⚠️ на заметку
   💵 Расход: $ (или «в рамках подписки»)
   🔗 ссылка на официальный источник
Максимум 6 пунктов, самые полезные первыми; бесполезное для нас — не упоминай.
Если ничего важного не вышло — так и напиши одной строкой, не выдумывай.
В конце: «👉 Совет:» — что одно пробуем первым и почему (1–2 строки).
Последней строкой отдельно: ТЕМЫ: тема1; тема2; … (короткие названия новинок из ответа)."""


def load_history(path: Path) -> list[str]:
    try:
        return [str(x) for x in json.loads(path.read_text(encoding="utf-8"))][-HISTORY_KEEP:]
    except (OSError, ValueError):
        return []


def save_history(path: Path, old: list[str], new: list[str]) -> None:
    seen = {t.lower() for t in old}
    merged = old + [t for t in new if t.lower() not in seen]
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(merged[-HISTORY_KEEP:], ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def split_topics(text: str) -> tuple[str, list[str]]:
    """Отрезать служебную строку «ТЕМЫ: …» от отчёта."""
    m = re.search(r"^\s*ТЕМЫ:\s*(.+)$", text, flags=re.M)
    if not m:
        return text.strip(), []
    topics = [t.strip() for t in m.group(1).split(";") if t.strip()]
    return (text[:m.start()] + text[m.end():]).strip(), topics


def short_err(e: Exception) -> str:
    """28.10 владелец: никаких непонятных простыней — одна понятная строка."""
    t = str(e)
    if "429" in t:
        return "бесплатный лимит Gemini на сегодня исчерпан — проверю в следующий заход."
    if "нет GEMINI_API_KEY" in t:
        return "нет ключа Gemini на сервере."
    return "не получилось (" + t[:80] + ")."


def prompt(now: dt.datetime, seen: list[str]) -> str:
    return TASK.format(today=now.strftime("%d.%m.%Y"), since=(now - dt.timedelta(days=7)).strftime("%d.%m.%Y"),
                       services="\n".join(f"- {n} ({why})" for n, why in SERVICES),
                       seen="; ".join(seen[-40:]) or "—")


def run(out_dir: Path, now: dt.datetime | None = None, ask=gemini_ask) -> str:
    now = now or dt.datetime.now(TZ)
    hist = out_dir / "history-novinki.json"
    old = load_history(hist)
    try:
        raw, _ = ask(prompt(now, old), search=True)
    except TrendError as e:
        return "🆕 Новинки сервисов: " + short_err(e)
    text, topics = split_topics(raw)
    save_history(hist, old, topics)
    (out_dir / "latest-novinki.txt").write_text(text, encoding="utf-8")
    return text
