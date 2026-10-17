"""🎬 Тренд-разведка (решение владельца 17.10): AI-видео тренды и конкуренты-«панели».

Два режима, отчёт — в PAPA TEST GROUP, по-русски, коротко:
  daily  — свежие (≤ 72 ч) вирусные AI-видео тренды и новые шаблоны (Higgsfield, PixVerse, Kling, Dreamina, Hailuo, Vidu…):
           что за тренд, где шаблон, цена ролика, подходит ли для артистов Узбекистана, срочность.
  market — раз в неделю (понедельник): блогеры и студии с «панелями» (кодовое слово → ссылка → панель с шаблонами),
           чья партнёрка или какой API под капотом, цены, сильные/слабые стороны, что берём себе; цены API-моделей.

Работает через Anthropic API с серверным веб-поиском (ключ ANTHROPIC_API_KEY из /etc/papa-genplan/ai.env).
История тем (history.json) — чтобы не повторять одни и те же тренды каждый день.
Расход: daily (Haiku, ≤ 6 поисков) ~ $0.05–0.10; market (Sonnet, ≤ 12 поисков) ~ $0.3–0.6. Итого ~ $3–5 в месяц."""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.anthropic.com/v1/messages"
DAILY_MODEL = os.environ.get("TREND_DAILY_MODEL", "claude-haiku-5-5")
MARKET_MODEL = os.environ.get("TREND_MARKET_MODEL", "claude-sonnet-5-5")
TZ = dt.timezone(dt.timedelta(hours=5))
HISTORY_KEEP = 60

CONTEXT = """Контекст владельца: Озод («Papa»), Узбекистан. Аудитория: YouTube 575K, Instagram 238K, Telegram-каналы.
Лично знаком со многими известными артистами Узбекистана. Стратегия: по свежему мировому AI-видео тренду делаем ролик
артисту БЕСПЛАТНО (с его согласия, с нашей меткой) → артист публикует → простые люди и бизнесы хотят «так же» →
продаём им ролики (бот/панель). Позже — своя панель с шаблонами на API (Kling, Veo, Wan, Seedance…) и партнёрки
(Higgsfield Ambassador до 15%). Бюджет маленький, каждый доллар на счету. Скорость важна: тренд живёт 3–7 дней."""

DAILY_TASK = """Задача: найди в интернете AI-видео тренды и новые шаблоны/эффекты, которые стали вирусными за последние 72 часа
(сегодня {today}). Ищи: новые эффекты в Higgsfield, PixVerse, Kling, Dreamina/CapCut, Hailuo, Vidu, Pika, Sora/Veo-приложениях;
вирусные ролики TikTok/Instagram/YouTube Shorts с AI-эффектами; события-поводы (запуски машин, гаджетов, фильмов, матчи),
под которые уже делают AI-ролики со знаменитостями.
Не повторяй темы, которые уже были: {seen}

Ответ — строго по-русски, коротко, для Telegram (без таблиц и markdown-заголовков), до 1800 знаков:
🎬 ТРЕНДЫ ДНЯ — {today}
Для каждого тренда (максимум 5, самые сильные первыми):
N) Название — что происходит в ролике (1 строка)
   🔧 Где сделать: сервис/шаблон · 💵 цена ролика ≈ $
   🎤 Для артистов УЗ: да/нет и идея в 1 строку
   ⏰ Срочность: делать сегодня / на этой неделе / можно подождать
   🔗 ссылка-источник
В конце: «👉 Совет:» — один тренд, который делаем первым, и почему (1–2 строки).
Если по-настоящему свежего нет — так и напиши одной строкой, не выдумывай.
Последней строкой отдельно: ТЕМЫ: тема1; тема2; … (короткие названия трендов из ответа)."""

MARKET_TASK = """Задача (недельный обзор рынка, сегодня {today}): изучи, как блогеры и студии зарабатывают на AI-видео трендах.
1) Найди 3–6 блогеров/студий/сервисов (мир, СНГ, по возможности Узбекистан — например dilivision.uz), которые ведут
   людей «кодовым словом» или ссылкой на свою панель/сайт/бот с готовыми шаблонами. Для каждого: как устроена воронка,
   чья партнёрка или какой API под капотом (если видно), цены для клиента, сильная сторона, слабая сторона.
2) Партнёрские программы AI-видео сервисов (Higgsfield, PixVerse, Kling и др.): % и условия — что изменилось.
3) Цены API за 5-секундный ролик у 4–6 ходовых моделей (Kling, Veo, Wan, Seedance, Hailuo) — только если нашёл свежие цифры.
Не повторяй уже разобранное: {seen}

Ответ — строго по-русски, коротко, для Telegram (без таблиц и markdown-заголовков), до 3000 знаков:
🕵️ РЫНОК AI-ВИДЕО — неделя до {today}
Блоки: «Конкуренты», «Партнёрки», «Цены API», и в конце «👉 Что берём себе» — 2–3 конкретных шага для Papa с расходом в $.
Ссылки-источники — у каждого пункта. Если данных нет — так и пиши, не выдумывай.
Последней строкой отдельно: ТЕМЫ: имя1; имя2; … (кого/что разобрал)."""


class TrendError(Exception):
    pass


def _post(body: dict, key: str, timeout: int = 300) -> dict:
    req = urllib.request.Request(API, data=json.dumps(body).encode(), method="POST", headers={
        "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise TrendError(f"Anthropic HTTP {e.code}: {e.read()[:300]!r}") from None
    except (urllib.error.URLError, TimeoutError) as e:
        raise TrendError(f"Anthropic недоступен: {e}") from None


def ask(prompt: str, model: str, max_searches: int, key: str | None = None, post=_post) -> tuple[str, dict]:
    """Один запрос с веб-поиском; продолжаем, если API вернул pause_turn. Возвращает (текст, usage)."""
    key = key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise TrendError("нет ANTHROPIC_API_KEY (задача genplan-ai-key)")
    messages = [{"role": "user", "content": prompt}]
    usage = {"input_tokens": 0, "output_tokens": 0, "searches": 0}
    for _ in range(4):
        d = post({"model": model, "max_tokens": 4000, "system": CONTEXT, "messages": messages,
                  "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": max_searches}]}, key)
        u = d.get("usage") or {}
        usage["input_tokens"] += int(u.get("input_tokens", 0))
        usage["output_tokens"] += int(u.get("output_tokens", 0))
        usage["searches"] += int((u.get("server_tool_use") or {}).get("web_search_requests", 0))
        if d.get("stop_reason") == "pause_turn":
            messages = [messages[0], {"role": "assistant", "content": d.get("content", [])}]
            continue
        text = "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text").strip()
        if not text:
            raise TrendError(f"пустой ответ ИИ: {str(d)[:200]}")
        return text, usage
    raise TrendError("ИИ не закончил ответ за 4 шага")


def split_topics(text: str) -> tuple[str, list[str]]:
    """Отрезать служебную строку «ТЕМЫ: …» → (текст для владельца, список тем)."""
    m = re.search(r"^\s*\**ТЕМЫ\**\s*:\s*(.+?)\s*$", text, flags=re.M | re.I)
    if not m:
        return text.strip(), []
    topics = [t.strip(" .*") for t in m.group(1).split(";") if t.strip(" .*")]
    return (text[:m.start()] + text[m.end():]).strip(), topics


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


def cost(usage: dict, model: str) -> float:
    """Примерная цена запроса в $ (вход/выход за 1М токенов + $0.01 за поиск)."""
    rin, rout = (1.0, 5.0) if "haiku" in model else (3.0, 15.0)
    return round(usage["input_tokens"] / 1e6 * rin + usage["output_tokens"] / 1e6 * rout + usage["searches"] * 0.01, 3)


def run(mode: str, out_dir: Path, now: dt.datetime | None = None, post=_post) -> str:
    """Сделать отчёт режима daily|market. Возвращает текст для отправки (с расходом в конце)."""
    if mode not in ("daily", "market"):
        raise TrendError(f"неизвестный режим: {mode}")
    today = (now or dt.datetime.now(TZ)).strftime("%d.%m.%Y")
    hist_path = out_dir / f"history-{mode}.json"
    old = load_history(hist_path)
    seen = "; ".join(old[-30:]) or "—"
    if mode == "daily":
        prompt, model, n = DAILY_TASK.format(today=today, seen=seen), DAILY_MODEL, 6
    else:
        prompt, model, n = MARKET_TASK.format(today=today, seen=seen), MARKET_MODEL, 12
    raw, usage = ask(prompt, model, n, post=post)
    text, topics = split_topics(raw)
    save_history(hist_path, old, topics)
    (out_dir / f"latest-{mode}.txt").write_text(text, encoding="utf-8")
    return f"{text}\n\n💲 расход отчёта ≈ ${cost(usage, model)} · поисков: {usage['searches']}"
