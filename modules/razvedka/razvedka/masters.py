"""🎓 Уроки мастеров (путь Б, владелец 01.11: «Да, уши нам нужны»).

Раз в неделю (вместе с GitHub-разведкой): новые ролики выбранных мастеров YouTube (моушн, ИИ-видео, Claude) →
Gemini смотрит ролик ЦЕЛИКОМ по ссылке YouTube (кадры + речь, без скачивания на сервер) → конкретные приёмы и
правила для PAPA → отчёт в бот + очередь навыков navyki-queue.json (проверка и внедрение — скилл navyki-razvedka).

Важно: только напрямую в Google Gemini. Прокси PAPA при лимите уводит запрос в OpenRouter, а туда видео
не передаётся — модель ответила бы, не посмотрев ролик. Поэтому: лимит Google → урок ждёт следующей недели.
Защита от «пересказа без просмотра»: ответ засчитывается, только если Gemini реально принял видео (много входных
токенов) и не написал «ВИДЕО НЕДОСТУПНО».
Расход: бесплатная квота Gemini (YouTube-ролики — до 8 ч в день бесплатно), ≈ $0. Не больше 3 уроков за заход."""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

TZ = dt.timezone(dt.timedelta(hours=5))
MAX_PER_RUN = 3
FRESH_DAYS = 21
MAX_MINUTES_HINT = 40
MIN_VIDEO_TOKENS = 3000          # меньше — значит, видео не смотрели (только текст запроса)
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
GEMINI = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={k}"
FEED = "https://www.youtube.com/feeds/videos.xml?channel_id={c}"

# Мастера, у которых учимся. Канал находим по ссылке на их ролик (надёжно) или поиском (проверить в отчёте).
# Добавить мастера: строка с "video" (id любого его ролика) — лучший способ.
MASTERS = [
    {"name": "OBSION", "video": "Et9XmhBTH6Y", "why": "мультики и моушн кодом без видеомодели"},
    {"name": "Георгий Ривера", "query": "Георгий Ривера моушн Claude", "why": "моушн кодом, Remotion 2D/3D"},
    {"name": "Кайсар Курмангалиев", "query": "Кайсар Курмангалиев ИИ видео", "why": "режиссура ИИ-видео"},
    {"name": "Kaye Creatives", "query": "Kaye Creatives Claude motion graphics", "why": "моушн-монтаж, коллаж"},
    {"name": "Павел Лебедев", "query": "Павел Лебедев Claude Code", "why": "Claude Code, скиллы, агенты"},
]

PROMPT = """Ты — помощник студии PAPA (Узбекистан): моушн-графика КОДОМ (HTML/JS, Remotion, ffmpeg), ИИ-видео
(Google Flow/Veo, Kling), скиллы Claude, Telegram-каналы и реклама. Посмотри ЭТОТ ролик целиком — кадры и речь.
Если ты не можешь посмотреть видео, ответь ровно одной строкой: ВИДЕО НЕДОСТУПНО.

Ролик: «{title}» — автор {master} ({why}).
Нужны не пересказ и не реклама курса, а то, что можно ВЗЯТЬ В РАБОТУ. Ответ по-русски, для Telegram, без таблиц
и markdown-заголовков, до 1800 знаков:
🎓 {master} — «{title}»
Суть: 1–2 строки.
Приёмы (до 6, самые конкретные): «приём → как сделать у нас (инструмент/параметры/промпт)».
Ссылки из ролика/описания на скиллы, репозитории, промпты — если есть (полные адреса).
Вердикт: ✅ берём / 🧪 в проверку / ⚠️ на заметку / ❌ мимо — и одна строка почему.
Реклама и цифры дохода автора — не пересказывать."""


class MastersError(Exception):
    pass


def _fetch(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ru,en;q=0.8",
                                               "Cookie": "CONSENT=YES+1; SOCS=CAI"})   # Франкфурт: обход EU-заглушки
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError) as e:
        raise MastersError(f"YouTube недоступен: {e}") from None


CH_RE = re.compile(r'"(?:channelId|externalId|browseId)":"(UC[\w-]{22})"')


def resolve(entry: dict, fetch=_fetch) -> str:
    """id канала мастера: явный → по его ролику → поиском (первый канал в выдаче)."""
    if entry.get("channel"):
        return entry["channel"]
    if entry.get("video"):
        html = fetch("https://www.youtube.com/watch?v=" + entry["video"])
    elif entry.get("query"):
        html = fetch("https://www.youtube.com/results?" + urllib.parse.urlencode({"search_query": entry["query"]}))
    else:
        raise MastersError(f"{entry.get('name')}: нет video/query/channel")
    m = CH_RE.search(html)
    if not m:
        raise MastersError(f"{entry.get('name')}: канал не найден на странице")
    return m.group(1)


NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}


def parse_feed(xml: str) -> tuple[str, list[dict]]:
    """(название канала, ролики [{id, title, published}]) из RSS YouTube."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        raise MastersError("RSS канала не читается") from None
    author = root.findtext("a:author/a:name", "", NS) or root.findtext("a:title", "", NS)
    vids = []
    for e in root.findall("a:entry", NS):
        vid = e.findtext("yt:videoId", "", NS)
        if vid:
            vids.append({"id": vid, "title": (e.findtext("a:title", "", NS) or "").strip(),
                         "published": (e.findtext("a:published", "", NS) or "")[:10]})
    return author, vids


def is_short(title: str) -> bool:
    return "#shorts" in title.lower()


def pick(per_master: list[tuple[dict, list[dict]]], seen: set[str], today: dt.date,
         limit: int = MAX_PER_RUN) -> list[tuple[dict, dict]]:
    """Свежие непросмотренные ролики: по кругу — сначала самый новый у каждого мастера, потом следующие."""
    since = (today - dt.timedelta(days=FRESH_DAYS)).isoformat()
    queues = []
    for m, vids in per_master:
        q = [v for v in sorted(vids, key=lambda v: v["published"], reverse=True)
             if v["id"] not in seen and v["published"] >= since and not is_short(v["title"])]
        queues.append((m, q))
    out = []
    while len(out) < limit and any(q for _, q in queues):
        for m, q in queues:
            if q and len(out) < limit:
                out.append((m, q.pop(0)))
    return out


def _post(model: str, body: dict, key: str, timeout: int = 600) -> dict:
    """Строго напрямую в Google (не через прокси PAPA — см. шапку)."""
    req = urllib.request.Request(GEMINI.format(m=model, k=key), data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise MastersError(f"Gemini HTTP {e.code}") from None
    except (urllib.error.URLError, TimeoutError) as e:
        raise MastersError(f"Gemini недоступен: {e}") from None


def watch(master: dict, video: dict, key: str, post=_post) -> tuple[str, int]:
    """Gemini смотрит ролик по ссылке YouTube. Возвращает (урок, входные токены)."""
    body = {"contents": [{"role": "user", "parts": [
                {"file_data": {"file_uri": f"https://www.youtube.com/watch?v={video['id']}"}},
                {"text": PROMPT.format(title=video["title"], master=master["name"], why=master.get("why", ""))}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 8192, "mediaResolution": "MEDIA_RESOLUTION_LOW"}}
    errs = []
    for m in dict.fromkeys([os.environ.get("GEMINI_VIDEO_MODEL", "gemini-flash-latest"), "gemini-2.5-flash"]):
        try:
            d = post(m, body, key)
        except MastersError as e:
            errs.append(str(e))
            if "429" in str(e):
                break                                   # лимит Google — ждём следующей недели
            continue
        cand = (d.get("candidates") or [{}])[0]
        text = "".join(p.get("text", "") for p in ((cand.get("content") or {}).get("parts") or [])
                       if not p.get("thought")).strip()
        tokens = int((d.get("usageMetadata") or {}).get("promptTokenCount", 0))
        if not text:
            errs.append(f"пустой ответ ({cand.get('finishReason')})"); continue
        if "ВИДЕО НЕДОСТУПНО" in text.upper() or tokens < MIN_VIDEO_TOKENS:
            raise MastersError("Gemini не смог посмотреть ролик (недоступен/закрыт)")
        return text, tokens
    raise MastersError("; ".join(errs[-2:]) or "Gemini не ответил")


def _load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def run(out_dir: Path, now: dt.datetime | None = None, fetch=_fetch, post=_post) -> str:
    now = now or dt.datetime.now(TZ)
    today_s = now.strftime("%d.%m.%Y")
    ids_p, seen_p = out_dir / "masters-ids.json", out_dir / "masters-seen.json"
    ids, seen = _load(ids_p, {}), _load(seen_p, [])
    notes, per_master, found_names = [], [], []
    for m in MASTERS:
        try:
            cid = ids.get(m["name"]) or resolve(m, fetch)
            try:
                author, vids = parse_feed(fetch(FEED.format(c=cid)))
            except MastersError:
                if not ids.get(m["name"]):
                    raise
                ids.pop(m["name"], None)                 # старый id из кэша не работает — найти канал заново
                cid = resolve(m, fetch)
                author, vids = parse_feed(fetch(FEED.format(c=cid)))
            ids[m["name"]] = cid                         # в кэш — только проверенный канал (RSS открылся)
            per_master.append((m, vids))
            found_names.append(f"{m['name']} → {author or cid}")
        except MastersError as e:
            ids.pop(m["name"], None)
            notes.append(f"⚠️ {m['name']}: канал не найден ({e}) — нужна ссылка на любой его ролик")
    _save(ids_p, ids)
    key = os.environ.get("GEMINI_API_KEY", "").strip().strip('"').strip("'")
    if not key:
        return f"🎓 УРОКИ МАСТЕРОВ — {today_s}\nнет GEMINI_API_KEY — уроки не смотрел."
    chosen = pick(per_master, set(seen), now.date())
    lessons, queue_add = [], []
    for m, v in chosen:
        try:
            from . import budget
            budget.gate()
        except Exception as e:                           # общий дневной лимит Gemini — ассистент важнее
            notes.append(f"⏸ лимит Gemini — остальное на следующей неделе ({type(e).__name__})")
            break
        try:
            text, tokens = watch(m, v, key, post)
        except MastersError as e:
            notes.append(f"⚠️ {m['name']} «{v['title'][:60]}»: {e}")
            if "429" in str(e):
                break
            continue
        url = f"https://www.youtube.com/watch?v={v['id']}"
        (out_dir / "masters").mkdir(parents=True, exist_ok=True)
        (out_dir / "masters" / f"{v['id']}.txt").write_text(f"{url}\n\n{text}", encoding="utf-8")
        lessons.append(f"{text}\n🔗 {url}")
        seen.append(v["id"])
        queue_add.append({"name": f"{m['name']}: {v['title'][:80]}", "url": url, "topic": "Урок мастера",
                          "stars": 0, "license": "", "desc": text[:300], "found": today_s, "status": "ждёт проверки"})
    _save(seen_p, seen[-500:])
    if queue_add:
        qp = out_dir / "navyki-queue.json"
        q = _load(qp, [])
        have = {x.get("url") for x in q}
        q += [x for x in queue_add if x["url"] not in have]
        _save(qp, q[-60:])
    head = f"🎓 УРОКИ МАСТЕРОВ — неделя до {today_s}"
    body = "\n\n".join(lessons) if lessons else "Новых уроков у мастеров нет."
    tail = "\n".join(notes)
    text = "\n\n".join(x for x in (head, body, tail) if x)
    (out_dir / "latest-masters.txt").write_text(text + "\n\nКаналы: " + "; ".join(found_names), encoding="utf-8")
    return text


def messages(text: str, limit: int = 3900) -> list[str]:
    """Отчёт → сообщения Telegram (лимит 4096): каждый урок отдельно, длинное — режем по строкам."""
    parts, cur = [], ""
    for block in text.split("\n\n"):
        if cur and (block.startswith("🎓 ") or len(cur) + len(block) + 2 > limit):
            parts.append(cur); cur = ""
        while len(block) > limit:
            cut = block.rfind("\n", 0, limit) if block.rfind("\n", 0, limit) > 0 else limit
            parts.append(block[:cut]); block = block[cut:].lstrip("\n")
        cur = f"{cur}\n\n{block}" if cur else block
    if cur:
        parts.append(cur)
    return parts
