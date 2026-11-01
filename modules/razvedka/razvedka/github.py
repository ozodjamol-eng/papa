"""🧭 GitHub-разведка (решение владельца 18.10): раз в неделю — новые полезные инструменты для PAPA.

Как работает:
  1) GitHub Search API (бесплатно, без ключа; если есть GITHUB_TOKEN — лимит выше) по темам PAPA:
     Telegram-боты и автопостинг, Instagram, монтаж видео, ИИ-видео, навыки Claude, узбекский язык.
  2) Отсев мусора: форки, архив, заброшенные (> 60 дней без коммитов), мало звёзд, уже показанные раньше.
  3) ИИ (Gemini, без веб-поиска) оценивает кандидатов по правилу «Копилки фишек»: берём / на заметку / не нужно,
     где применить в PAPA и какой расход. Нет ключа Gemini или лимит дня — короткий список без оценки.
  4) Отчёт → бот-пульт владельца (20.10: отчёты в бот, без отдельных каналов). Код с GitHub сам ничего НЕ ставит — только советует.
Расход: $0 (GitHub и бесплатный Gemini).

01.11 владелец: «новинки всегда надо изучать — мы упускаем многое». Разведка навыков:
  + темы «Скиллы Claude» и «Моушн кодом» (главный рост — навыки, а не просто инструменты);
  + находки этих тем всегда попадают в отчёт (бронь до 4 мест) и в очередь navyki-queue.json;
  + вердикт «🧪 в проверку» = в сессии по скиллу navyki-razvedka: skill-check → пробный рендер → в PAPA Motion.
  Задача github-show показывает отчёт и очередь ассистенту (только чтение)."""
from __future__ import annotations

import datetime as dt
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .trend import TrendError, _gpost, cost, gemini_ask

SEARCH = "https://api.github.com/search/repositories"
TZ = dt.timezone(dt.timedelta(hours=5))
HISTORY_KEEP = 600
MAX_CANDIDATES = 14
SKILL_TOPICS = ("Скиллы Claude", "Моушн кодом")   # 01.11: разведка навыков — бронь в отчёте + очередь
SKILL_RESERVE = 4
QUEUE_KEEP = 60

# (тема для отчёта, запрос GitHub). Звёзды/свежесть добавляются в search_queries().
TOPICS = [
    # 01.11: навыки — ПЕРВЫМИ: при лимите GitHub (403) до последних тем не доходит
    ("Скиллы Claude", "claude skills OR claude code skill OR agent skills OR SKILL.md"),
    ("Моушн кодом", "remotion OR hyperframes OR motion graphics OR kinetic typography"),
    ("Telegram-боты", "telegram bot"),
    ("Автопостинг", "telegram autopost OR telegram scheduler OR channel autoposting"),
    ("Instagram", "instagram automation OR instagram graph api"),
    ("Монтаж видео", "ffmpeg video editing automation OR auto video editor"),
    ("ИИ-видео", "ai video generation OR text-to-video OR image-to-video"),
    ("Узбекский язык", "uzbek"),
]

CONTEXT = """Контекст: PAPA — система владельца (Озод, «Papa», Узбекистан) для роста своих Telegram-каналов
(КАТТА ДАВРА, PaparazziUZ, Xo'jaobod City 24) и дохода с рекламы. Модули: Razvedka (анализ конкурентов, тренды),
Voronka (Instagram комментарий → директ → Telegram), GENPLAN (боты-пульты, автопостинг по расписанию, ИИ-хуки),
Reklama, Fabrika (ИИ-контент, монтаж видео на Python+ffmpeg, клипы на заказ), Pult (управление).
Стек: Python, Telegram Bot API и Telethon, серверы DigitalOcean по 1 ГБ RAM, Gemini (Flash) для текстов.
Бюджет маленький. Правило «Копилки фишек»: не копируем — оцениваем, берём как есть / дорабатываем / берём часть, честно."""

TASK = """Ниже кандидаты с GitHub (сегодня {today}). Оцени, какие РЕАЛЬНО полезны PAPA прямо сейчас.
Выбери максимум 6 (самые полезные первыми); остальное — не упоминай. Если полезного нет — так и напиши одной строкой.
Темы «Скиллы Claude» и «Моушн кодом» — ГЛАВНОЕ (владелец 01.11: так ассистент растёт как режиссёр/аниматор):
если там есть хоть что-то стоящее — минимум 2 места им, с вердиктом «🧪 в проверку» (проверим на нашем ролике).
Опасайся: заброшенных проектов, непонятной лицензии, инструментов, требующих видеокарту/много памяти,
сервисов, запрещённых правилами Telegram/Instagram (накрутки, спам, парсинг личных данных) — такие не советуй.

Ответ строго по-русски, коротко, для Telegram (без таблиц и markdown-заголовков), до 2200 знаков:
🧭 GITHUB-РАЗВЕДКА — неделя до {today}
N) owner/repo ⭐ звёзды · лицензия
   Что это: 1 строка простыми словами
   Вердикт: ✅ берём / 🧪 в проверку (скиллы, моушн) / ⚠️ на заметку
   Где у нас: модуль PAPA и зачем (1 строка)
   💵 Расход: $
   🔗 ссылка
В конце: «👉 Совет:» — что одно делаем первым и почему (1–2 строки).

Кандидаты:
{items}"""


class GithubError(Exception):
    pass


def search_queries(today: dt.date) -> list[tuple[str, str]]:
    """Два прохода на тему: «растут сейчас» (созданы ≤ 45 дн., ★ ≥ 30) и «живые сильные» (обновлены ≤ 30 дн., ★ ≥ 300)."""
    new_since = (today - dt.timedelta(days=45)).isoformat()
    push_since = (today - dt.timedelta(days=30)).isoformat()
    out = []
    for label, q in TOPICS:
        out.append((label, f"{q} created:>={new_since} stars:>=30 fork:false archived:false"))
        out.append((label, f"{q} pushed:>={push_since} stars:>=300 fork:false archived:false"))
    return out


def _get(url: str, token: str = "", timeout: int = 30) -> dict:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "papa-razvedka",
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise GithubError(f"GitHub HTTP {e.code}") from None
    except (urllib.error.URLError, TimeoutError) as e:
        raise GithubError(f"GitHub недоступен: {e}") from None


def search(query: str, get=_get, token: str = "", per_page: int = 8) -> list[dict]:
    url = SEARCH + "?" + urllib.parse.urlencode({"q": query, "sort": "stars", "order": "desc", "per_page": per_page})
    return get(url, token).get("items", []) or []


def _license(r: dict) -> str:
    lic = (r.get("license") or {}).get("spdx_id") or ""
    return "" if lic in ("", "NOASSERTION") else lic


def collect(today: dt.date, seen: set[str], get=_get, token: str = "") -> tuple[list[dict], list[str]]:
    """Кандидаты (без повторов и мусора) + ошибки запросов. Лучшие по звёздам, свежие проекты — с бонусом."""
    found: dict[str, dict] = {}
    errors = []
    stale = today - dt.timedelta(days=60)
    pace = get is _get and not token        # без токена GitHub даёт 10 поисков в минуту — идём шагом
    for i, (label, q) in enumerate(search_queries(today)):
        if pace and i:
            time.sleep(7.5)
        try:
            items = search(q, get, token)
        except GithubError as e:
            if pace and ("403" in str(e) or "429" in str(e)):
                time.sleep(65)                          # лимит GitHub — минута паузы и одна повторная попытка
                try:
                    items = search(q, get, token)
                except GithubError as e2:
                    errors.append(f"{label}: {e2}")
                    break
            else:
                errors.append(f"{label}: {e}")
                if "403" in str(e) or "429" in str(e):  # лимит GitHub — дальше не долбим
                    break
                continue
        for r in items:
            name = r.get("full_name") or ""
            if not name or name.lower() in seen or name in found:
                continue
            if r.get("fork") or r.get("archived") or r.get("disabled"):
                continue
            pushed = (r.get("pushed_at") or "")[:10]
            if pushed and pushed < stale.isoformat():
                continue
            created = (r.get("created_at") or "")[:10]
            found[name] = {
                "name": name, "topic": label, "stars": int(r.get("stargazers_count") or 0),
                "desc": (r.get("description") or "").strip()[:220], "license": _license(r),
                "lang": r.get("language") or "", "pushed": pushed, "created": created,
                "url": r.get("html_url") or f"https://github.com/{name}",
                "new": bool(created and created >= (today - dt.timedelta(days=45)).isoformat()),
            }
    ranked = sorted(found.values(), key=lambda x: x["stars"] * (3 if x["new"] else 1), reverse=True)
    # бронь навыков: лучшие находки «Скиллы Claude»/«Моушн кодом» не вытесняются большими Telegram-проектами
    key = lambda x: x["stars"] * (3 if x["new"] else 1)
    skills = [c for c in ranked if c["topic"] in SKILL_TOPICS][:SKILL_RESERVE]
    others = [c for c in ranked if c not in skills]
    top = sorted(skills + others[:MAX_CANDIDATES - len(skills)], key=key, reverse=True)
    return top, errors


def save_queue(path: Path, cands: list[dict], today: str) -> list[dict]:
    """Очередь навыков на проверку в сессии (скилл navyki-razvedka). Новые — в конец, без повторов."""
    try:
        q = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        q = []
    have = {x.get("name", "").lower() for x in q}
    for c in cands:
        if c["topic"] in SKILL_TOPICS and c["name"].lower() not in have:
            q.append({"name": c["name"], "url": c["url"], "topic": c["topic"], "stars": c["stars"],
                      "license": c["license"], "desc": c["desc"], "found": today, "status": "ждёт проверки"})
    q = q[-QUEUE_KEEP:]
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(q, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)
    return q


def stars_h(n: int) -> str:
    return f"{n / 1000:.1f}k".replace(".0k", "k") if n >= 1000 else str(n)


def items_text(cands: list[dict]) -> str:
    return "\n".join(
        f"- {c['name']} | тема: {c['topic']} | ★ {c['stars']} | лицензия: {c['license'] or 'нет/неясно'} | "
        f"язык: {c['lang'] or '—'} | создан {c['created']} | обновлён {c['pushed']} | {c['url']}\n  {c['desc'] or '(без описания)'}"
        for c in cands)


def plain_report(cands: list[dict], today: str, note: str = "") -> str:
    """Без ИИ: короткий список (для запасного случая)."""
    if not cands:
        return f"🧭 GITHUB-РАЗВЕДКА — неделя до {today}\nНового полезного не найдено."
    lines = [f"🧭 GITHUB-РАЗВЕДКА — неделя до {today} (без ИИ-оценки{': ' + note if note else ''})"]
    for i, c in enumerate(cands[:7], 1):
        lines.append(f"{i}) {c['name']} ⭐ {stars_h(c['stars'])} · {c['license'] or 'лицензия неясна'} · {c['topic']}\n"
                     f"   {c['desc'] or '—'}\n   🔗 {c['url']}")
    return "\n".join(lines)


def run(out_dir: Path, now: dt.datetime | None = None, get=_get, gpost=_gpost) -> str:
    """Сделать недельный отчёт. Возвращает текст для отправки."""
    now = now or dt.datetime.now(TZ)
    today_s = now.strftime("%d.%m.%Y")
    hist = out_dir / "history-github.json"
    old = load_history_all(hist)
    cands, errors = collect(now.date(), {x.lower() for x in old}, get, os.environ.get("GITHUB_TOKEN", ""))
    err_line = "\n⚠️ GitHub ответил не на все запросы (лимит) — список неполный." if errors else ""
    if not cands:
        return plain_report([], today_s) + err_line
    if not os.environ.get("GEMINI_API_KEY"):          # 30.10: только Gemini (Anthropic владельца заблокирован)
        text = plain_report(cands, today_s, "нет GEMINI_API_KEY")
    else:
        try:
            prompt = TASK.format(today=today_s, items=items_text(cands))
            text, usage = gemini_ask(f"{CONTEXT}\n\n{prompt}", search=False, gpost=gpost)
            text += f"\n\n💲 расход отчёта ≈ ${cost(usage)} · кандидатов: {len(cands)}"
        except TrendError as e:
            from .novinki import short_err
            text = plain_report(cands, today_s, "ИИ: " + short_err(e))
    # показанных кандидатов больше не предлагаем (даже если ИИ их отсеял) — история на 600 названий
    old_keep = old[-(HISTORY_KEEP - len(cands)):]
    save_history_n(hist, old_keep, [c["name"] for c in cands])
    queue = save_queue(out_dir / "navyki-queue.json", cands, today_s)
    waiting = sum(1 for x in queue if x.get("status") == "ждёт проверки")
    if waiting:
        text += f"\n🧪 Навыков в очереди на проверку: {waiting} — проверю в ближайшей сессии"
    (out_dir / "latest-github.txt").write_text(text, encoding="utf-8")
    return text + err_line


def save_history_n(path: Path, old: list[str], new: list[str]) -> None:
    """Как trend.save_history, но с собственным лимитом истории."""
    seen = {t.lower() for t in old}
    merged = old + [t for t in new if t.lower() not in seen]
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(merged[-HISTORY_KEEP:], ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def load_history_all(path: Path) -> list[str]:
    try:
        return [str(x) for x in json.loads(path.read_text(encoding="utf-8"))][-HISTORY_KEEP:]
    except (OSError, ValueError):
        return []
