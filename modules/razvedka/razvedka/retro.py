"""📼 Ретро-разведчик YouTube (12.11.2026, владелец: «в Ютубе ценные видео… только в Телеграм-канал для удержания аудитории»).
Раз в день: Apify (YouTube Scraper, подписка Starter) ищет ретро-клипы по запросам из двух списков — мировые и узбекские (по кругу), отбирает
самые просматриваемые (2–8 мин, от 1 млн просмотров, не присылали раньше) и кладёт по ОДНОЙ подборке ссылок
в «БАНК · РЕТРО» (мировые) и «БАНК · ЎЗБЕК РЕТРО» (узбекские). Ничего не скачивает и не публикует: владелец выбирает и скачивает сам,
ролик оформляет Фабрика (шаблон №7). Текстовое сообщение каналы из склада не берут (sklad.VIDEO_ONLY).
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

ACTOR = os.environ.get("APIFY_YT_ACTOR", "streamers~youtube-scraper")
# 12.11 владелец: «ретро есть мировые и есть узбекские — различать». Два банка, две подборки.
GROUPS = {
    "РЕТРО КЛИПЛАР": {"title": "🌍 ЖАҲОН РЕТРО", "min_views": 1_000_000, "queries": [      # «БАНК · РЕТРО»
        "eurodance 90s hits official video", "80s disco hits official video", "italo disco 80s hits", "Modern Talking official video",
        "C.C. Catch official video", "Boney M live", "ABBA official video", "Bad Boys Blue official video", "Sandra 80s official video",
        "Dr. Alban official video", "Ace of Base official video", "Haddaway official video", "Joe Dassin live", "Adriano Celentano live",
        "70s disco hits live", "90s dance hits live tv", "ретро хиты 80-х клипы", "дискотека 80-х концерт", "хиты 90-х клипы"]},
    "ЎЗБЕК РЕТРО": {"title": "🇺🇿 ЎЗБЕК РЕТРО", "min_views": 100_000, "queries": [          # «БАНК · ЎЗБЕК РЕТРО»
        "ўзбек ретро қўшиқлар", "o'zbek retro qo'shiqlar 90-yillar", "Ялла ансамбли", "Шерали Жўраев концерт",
        "Юлдуз Усмонова 90 йиллар", "Ботир Зокиров", "Насиба Абдуллаева эски қўшиқлар", "Ғуломжон Ёқубов", "Охунжон Мадалиев",
        "Ортиқ Отажонов", "Муҳриддин Холиқов", "Маҳмуд Намозов эски қўшиқлар", "o'zbek estrada 80-yillar", "узбекская эстрада 90-х клипы"]},
}
PER_RUN, PER_QUERY, PICK = 2, 12, 6            # запросов на банк за день, видео на запрос, ссылок в подборке
MIN_VIEWS, MIN_SEC, MAX_SEC = 1_000_000, 120, 480


def _sec(v) -> int:
    if isinstance(v, (int, float)):
        return int(v)
    p = [int(x) for x in re.findall(r"\d+", str(v or ""))]
    return sum(x * 60 ** i for i, x in enumerate(reversed(p))) if p else 0


def _views(v) -> int:
    if isinstance(v, (int, float)):
        return int(v)
    d = re.sub(r"[^\d]", "", str(v or ""))
    return int(d) if d else 0


def pick(items: list[dict], seen: set[str], n: int = PICK, min_views: int = MIN_VIEWS) -> list[dict]:
    out, ids = [], set()
    for it in items:
        vid = str(it.get("id") or it.get("videoId") or "")
        views, sec = _views(it.get("viewCount") or it.get("views")), _sec(it.get("duration"))
        if not vid or vid in seen or vid in ids or views < min_views or not (MIN_SEC <= sec <= MAX_SEC):
            continue
        ids.add(vid)
        out.append({"id": vid, "title": str(it.get("title") or "")[:90], "views": views, "sec": sec,
                    "channel": str(it.get("channelName") or it.get("channel") or "")[:40],
                    "url": it.get("url") or f"https://www.youtube.com/watch?v={vid}"})
    out.sort(key=lambda x: -x["views"])
    return out[:n]


def card(picks: list[dict], day: str, title: str = "📼 РЕТРО") -> str:
    rows = [f"{title} · ҚИДИРУВ · {day}\nYouTube'дан топилган клиплар. Ёққанини юклаб, Клодга ташланг — «РЕТРО ДАВРА» қилиб беради.\n"]
    for i, p in enumerate(picks, 1):
        v = f"{p['views'] / 1e6:.1f} млн"
        rows.append(f"{i}. {p['title']}\n   👁 {v} · ⏱ {p['sec'] // 60}:{p['sec'] % 60:02d} · {p['channel']}\n   {p['url']}")
    return "\n".join(rows)[:4000]


def apify_search(queries: list[str], per_query: int, token: str) -> list[dict]:
    body = {"searchQueries": queries, "maxResults": per_query, "maxResultsShorts": 0, "maxResultStreams": 0}
    req = urllib.request.Request(f"https://api.apify.com/v2/acts/{ACTOR}/run-sync-get-dataset-items?timeout=280",
                                 data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json", "authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read() or b"[]")


async def run(client, state_dir: Path, now: dt.datetime | None = None, log=print) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    token = os.environ.get("APIFY_TOKEN", "").strip()
    if not token:
        return {"пропуск": "нет ключа Apify"}
    sf = state_dir / "retro.json"
    try:
        st = json.loads(sf.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        st = {}
    from . import hubs as H
    seen, out, cache = set(st.get("seen", [])), {}, {}
    day = (now + dt.timedelta(hours=5)).strftime("%d.%m")
    for hub, g in GROUPS.items():
        i = int((st.get("next") or {}).get(hub, 0)) if isinstance(st.get("next"), dict) else 0
        qs = [g["queries"][(i + k) % len(g["queries"])] for k in range(PER_RUN)]
        try:
            items = await asyncio.to_thread(apify_search, qs, PER_QUERY, token)
        except urllib.error.HTTPError as e:
            log(f"Apify {e.code} {e.read()[:200].decode(errors='replace')}")
            out[hub] = {"ошибка": f"Apify {e.code}"}
            continue
        picks = pick(items, seen, min_views=g["min_views"])
        st["next"] = {**(st.get("next") if isinstance(st.get("next"), dict) else {}), hub: (i + PER_RUN) % len(g["queries"])}
        sent = 0
        if picks:
            dest = await H.entity(client, hub, cache)
            if dest is None:
                out[hub] = {"пропуск": f"нет канала «{H.TITLES.get(hub, hub)}»", "найдено": len(picks)}
                continue
            await client.send_message(dest, card(picks, day, g["title"]), link_preview=False)
            seen |= {p["id"] for p in picks}
            sent = len(picks)
        out[hub] = {"запросы": qs, "видео": len(items), "в подборке": sent}
    st["seen"] = sorted(seen)[-3000:]
    st["last"] = now.isoformat()
    state_dir.mkdir(parents=True, exist_ok=True)
    sf.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    return out
