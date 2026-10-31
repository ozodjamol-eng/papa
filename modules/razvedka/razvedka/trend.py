"""🎬 Тренд-разведка (решение владельца 17.10): AI-видео тренды и конкуренты-«панели».

Два режима, отчёт — в PAPA TEST GROUP, по-русски, коротко:
  daily  — свежие (≤ 72 ч) вирусные AI-видео тренды и новые шаблоны (Higgsfield, PixVerse, Kling, Dreamina, Hailuo, Vidu…):
           что за тренд, где шаблон, цена ролика, подходит ли для артистов Узбекистана, срочность.
  market — раз в неделю (понедельник): блогеры и студии с «панелями» (кодовое слово → ссылка → панель с шаблонами),
           чья партнёрка или какой API под капотом, цены, сильные/слабые стороны, что берём себе; цены API-моделей.

Работает только через Gemini с поиском Google (ключ GEMINI_API_KEY из /etc/papa-genplan/ai.env, задача genplan-gemini-key).
30.10: путь Anthropic удалён (аккаунт владельца заблокирован); лимит Gemini общий — см. budget.py.
История тем (history.json) — чтобы не повторять одни и те же тренды каждый день.
Расход: $0 (бесплатный ключ Gemini)."""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

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


GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"


def _gpost(model: str, body: dict, key: str, timeout: int = 300) -> dict:
    url = GEMINI_URL.format(m=model)
    if os.path.exists("/etc/papa-gemini-proxy/on"):           # 31.10: через прокси (Google бесплатно → OpenRouter при лимите)
        url = url.replace("https://generativelanguage.googleapis.com", "http://127.0.0.1:8790")
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"content-type": "application/json", "x-goog-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise TrendError(f"Gemini HTTP {e.code}: {e.read()[:300]!r}") from None
    except (urllib.error.URLError, TimeoutError) as e:
        raise TrendError(f"Gemini недоступен: {e}") from None


def gemini_ask(prompt: str, search: bool = True, key: str | None = None, gpost=_gpost) -> tuple[str, dict]:
    """Запрос к Gemini (с поиском Google, если search). Возвращает (текст, usage) в том же виде, что ask()."""
    key = (key or os.environ.get("GEMINI_API_KEY", "")).strip().strip('"').strip("'")
    if not key:
        raise TrendError("нет GEMINI_API_KEY (задача genplan-gemini-key)")
    from . import budget
    try:
        budget.gate()                            # 30.10: лимит Gemini общий — отчёт подождёт, ассистент важнее
    except budget.BudgetStop as e:
        raise TrendError(str(e)) from None
    body = {"systemInstruction": {"parts": [{"text": CONTEXT}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 8192}}
    if search:
        body["tools"] = [{"google_search": {}}]
    errs = []
    for m in dict.fromkeys([os.environ.get("GEMINI_MODEL", "gemini-flash-latest").removeprefix("models/"), "gemini-flash-latest"]):
        try:
            d = gpost(m, body, key)
        except TrendError as e:
            errs.append(str(e)); continue
        cand = (d.get("candidates") or [{}])[0]
        text = "".join(p.get("text", "") for p in ((cand.get("content") or {}).get("parts") or []) if not p.get("thought")).strip()
        if not text:
            errs.append(f"пустой ответ ({cand.get('finishReason')})"); continue
        u = d.get("usageMetadata") or {}
        q = (cand.get("groundingMetadata") or {}).get("webSearchQueries") or []
        return text, {"input_tokens": int(u.get("promptTokenCount", 0)),
                      "output_tokens": int(u.get("candidatesTokenCount", 0)) + int(u.get("thoughtsTokenCount", 0)),
                      "searches": len(q), "model": "gemini"}
    raise TrendError("Gemini: " + "; ".join(errs[-2:]))


def ask(prompt: str, key: str | None = None, gpost=_gpost) -> tuple[str, dict]:
    """Один запрос с поиском Google через Gemini. 30.10: путь Anthropic удалён — аккаунт владельца заблокирован."""
    return gemini_ask(prompt, True, key, gpost=gpost)


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


def cost(usage: dict, model: str = "gemini") -> float:
    """Примерная цена запроса в $, если бы ключ был платный (Gemini Flash: ~$0.30 вход / $2.50 выход за 1М).
    Сейчас ключ бесплатный — фактически $0."""
    return round(usage["input_tokens"] / 1e6 * 0.3 + usage["output_tokens"] / 1e6 * 2.5, 3)


def run(mode: str, out_dir: Path, now: dt.datetime | None = None, gpost=_gpost) -> str:
    """Сделать отчёт режима daily|market. Возвращает текст для отправки (с расходом в конце)."""
    if mode not in ("daily", "market"):
        raise TrendError(f"неизвестный режим: {mode}")
    today = (now or dt.datetime.now(TZ)).strftime("%d.%m.%Y")
    hist_path = out_dir / f"history-{mode}.json"
    old = load_history(hist_path)
    seen = "; ".join(old[-30:]) or "—"
    if mode == "daily":
        prompt = DAILY_TASK.format(today=today, seen=seen)
    else:
        prompt = MARKET_TASK.format(today=today, seen=seen)
    raw, usage = ask(prompt, gpost=gpost)
    text, topics = split_topics(raw)
    save_history(hist_path, old, topics)
    (out_dir / f"latest-{mode}.txt").write_text(text, encoding="utf-8")
    return f"{text}\n\n💲 расход отчёта ≈ ${cost(usage)} · поисков: {usage['searches']}"
