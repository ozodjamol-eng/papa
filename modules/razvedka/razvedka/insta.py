"""📸 Агент Instagram-трендов (30.10, схема «Штаб → отделы», отдел Разведки).

Владелец: «Telegram — дом аудитории; тренды Instagram берём для Telegram, в Instagram чужое не постим».
Раз в день Apify (бесплатный план, $5/мес) отдаёт последние рилсы из списка аккаунтов (config.toml [insta]).
Агент выбирает те, что «выстрелили» у своего автора (просмотры против его обычных), проверяет кадры на
чужое лого/@ (Gemini), пишет наш текст (узбекский кириллицей) и отправляет видео в пульт канала —
владелец видит обычную карточку и решает сам (✅ / 🗑). Каждый рилс — один раз (insta.json)."""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
import statistics
import urllib.error
import urllib.request
from pathlib import Path

from . import curate

ACTOR = os.environ.get("APIFY_REEL_ACTOR", "apify~instagram-reel-scraper")
TAG_ACTOR = os.environ.get("APIFY_TAG_ACTOR", "apify~instagram-hashtag-scraper")
# 30.10 владелец: «ты сам знаешь, на что ориентироваться» — агент сам ищет тренды по узбекским хэштегам
# и сам учит аккаунты, которые чаще всего «стреляют» (state["found"]).
TAGS = ["kulgili", "kulgu", "qiziqarli", "ozbekcha", "uzbekistan", "foydali", "vaynlar", "prikol_uz", "toshkent",
        "andijon"]
FRESH = dt.timedelta(days=4)
VIDEO_MAX = 45 * 1024 * 1024
TEXT_PROMPT = """Сен — «{title}» Telegram-каналининг муҳарририсан. Instagram рилсининг тагидаги матнни ўқиб, канал учун
қисқа пост матни ёз: биринчи қатор — эмодзи билан қисқа сарлавҳа (БОШ ҲАРФЛАР), кейин 1–2 қисқа гап, охирида
реакция қолдиришга чақириқ. Фақат ўзбек тилида, КИРИЛЛ алифбосида. Бошқа @юзернейм, ҳавола, хэштег ҚЎЙМА.
Фактларни ўзгартирма, ўзингдан қўшма. Матн бўлмаса — видео мавзусига мос умумий енгил сарлавҳа ёз.
Фақат тайёр матнни қайтар."""


def ratio(views: int, history: list[int]) -> float:
    """Во сколько раз рилс сильнее обычных у автора (медиана прошлых просмотров)."""
    base = statistics.median(history) if history else 0
    return views / base if base else 1.0


def choose(items: list[dict], state: dict, n: int, min_views: int, min_ratio: float) -> list[dict]:
    seen = set(state.get("seen", []))
    hist = state.setdefault("views", {})
    scored = []
    for it in items:
        code = it.get("shortCode") or it.get("id")
        views = int(it.get("videoPlayCount") or it.get("videoViewCount") or 0)
        owner = (it.get("ownerUsername") or "").lower()
        if not code or not it.get("videoUrl") or not owner:
            continue
        r = ratio(views, hist.get(owner, []))
        it["_ratio"], it["_views"], it["_code"], it["_owner"] = r, views, code, owner
        if code in seen or views < min_views or r < min_ratio:
            continue
        dur = float(it.get("videoDuration") or 0)
        if dur and not 5 <= dur <= 180:
            continue
        scored.append(it)
    for it in items:                                   # история автора — после выбора (сравниваем с прошлым)
        if it.get("_owner") and it.get("_views"):
            h = hist.setdefault(it["_owner"], [])
            if it["_code"] not in state.get("seen", []):
                h.append(it["_views"])
            del h[:-30]
    scored.sort(key=lambda x: (-x["_ratio"], -x["_views"]))
    out, owners = [], set()
    for it in scored:                                  # не больше одного рилса от автора за раз
        if it["_owner"] in owners:
            continue
        owners.add(it["_owner"])
        out.append(it)
        if len(out) >= n:
            break
    return out


def apify_reels(accounts: list[str], per_account: int, token: str, http=None) -> list[dict]:
    body = {"username": accounts, "resultsLimit": per_account}
    url = f"https://api.apify.com/v2/acts/{ACTOR}/run-sync-get-dataset-items?timeout=280"
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json", "authorization": f"Bearer {token}"})
    if http:
        return http(req)
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.loads(r.read())
    return data if isinstance(data, list) else []


def apify_tags(tags: list[str], per_tag: int, token: str, http=None) -> list[dict]:
    body = {"hashtags": tags, "resultsType": "reels", "resultsLimit": per_tag}
    url = f"https://api.apify.com/v2/acts/{TAG_ACTOR}/run-sync-get-dataset-items?timeout=280"
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json", "authorization": f"Bearer {token}"})
    if http:
        return http(req)
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.loads(r.read())
    return data if isinstance(data, list) else []


def fresh(items: list[dict], now: dt.datetime) -> list[dict]:
    out = []
    for it in items:
        ts = it.get("timestamp")
        try:
            t = dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00")) if ts else None
        except ValueError:
            t = None
        if t is None or now - t <= FRESH:
            out.append(it)
    return out


def learn(state: dict, items: list[dict]) -> list[str]:
    """Аккаунты, которые попадают в тренды чаще всего (по хэштегам) — агент запоминает их сам."""
    f = state.setdefault("found", {})
    for it in items:
        o = (it.get("ownerUsername") or "").lower()
        v = int(it.get("videoPlayCount") or it.get("videoViewCount") or 0)
        if o and v >= 20000:
            f[o] = f.get(o, 0) + 1
    return [o for o, n in sorted(f.items(), key=lambda kv: -kv[1]) if n >= 2][:20]


def write_text(caption: str, title: str) -> str:
    """Наш текст (Gemini, бесплатно). Без ключа/ошибка — пусто (владелец напишет сам ✏️ или нажмёт 🤖)."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        return ""
    body = {"systemInstruction": {"parts": [{"text": TEXT_PROMPT.format(title=title)}]},
            "contents": [{"role": "user", "parts": [{"text": f"Рилс матни:\n{(caption or '(матн йўқ)')[:2000]}"}]}],
            "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.6}}
    for model in dict.fromkeys([os.environ.get("INSTA_TEXT_MODEL", "gemini-flash-latest"), "gemini-flash-lite-latest"]):
        req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                     data=json.dumps(body).encode(), headers={"content-type": "application/json", "x-goog-api-key": key})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
            parts = ((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
            text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
            if text:
                return text[:900]
        except Exception:  # noqa: BLE001
            continue
    return ""


def download(url: str) -> bytes | None:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"user-agent": "Mozilla/5.0"}), timeout=90) as r:
            data = r.read(VIDEO_MAX + 1)
        return data if len(data) <= VIDEO_MAX else None
    except Exception:  # noqa: BLE001
        return None


async def run(client, cfg: dict, state_dir: Path, now: dt.datetime | None = None, log=print) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    ic = cfg.get("insta") or {}
    accounts = [a.strip().lstrip("@") for a in ic.get("accounts", []) if a.strip()]
    token = os.environ.get("APIFY_TOKEN", "").strip()
    if not token:
        return {"пропуск": "нет ключа Apify (papa-update apify-token)"}
    channel = ic.get("channel", "davra")
    sf = state_dir / "insta.json"
    try:
        st = json.loads(sf.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        st = {}
    tags = ic.get("tags") or TAGS
    items = fresh(await asyncio.to_thread(apify_tags, tags, int(ic.get("per_tag", 12)), token), now)
    learned = learn(st, items)
    log(f"Apify: хэштеги {len(tags)} → {len(items)} свежих рилсов; агент запомнил аккаунтов: {len(learned)}")
    accounts = list(dict.fromkeys(accounts + learned))[:20]
    if accounts:                                       # свои/выученные аккаунты — сравнение с их обычными просмотрами
        acc = await asyncio.to_thread(apify_reels, accounts, int(ic.get("per_account", 2)), token)
        log(f"Apify: аккаунты {len(accounts)} → {len(acc)} рилсов")
        items = fresh(acc, now) + items
    picks = choose(items, st, int(ic.get("max_send", 4)), int(ic.get("min_views", 30000)), float(ic.get("min_ratio", 0)))
    sent, skipped = 0, 0
    gemini = bool(os.environ.get("GEMINI_API_KEY"))
    if gemini:
        os.environ["GEMINI_MODEL"] = os.environ.get("CURATOR_GEMINI_MODEL", "gemini-flash-lite-latest")
    for it in picks:
        st.setdefault("seen", []).append(it["_code"])
        video = await asyncio.to_thread(download, it["videoUrl"])
        if not video:
            skipped += 1
            continue
        if gemini:                                     # чужое лого/@ на кадрах — не берём (правило владельца)
            try:
                grid = await asyncio.to_thread(curate.frames_grid, video, float(it.get("videoDuration") or 15))
                v = await asyncio.to_thread(curate.vision, grid) if grid else {}
                if v.get("foreign_logo") or v.get("ad") or v.get("bad"):
                    skipped += 1
                    log(f"  🚫 @{it['_owner']} {it['_code']}: лого/реклама на кадрах")
                    continue
            except RuntimeError as e:
                log(f"  кадры: {e}")
        title = ic.get("title", "КАТТА ДАВРА")
        text = await asyncio.to_thread(write_text, it.get("caption") or "", title)
        try:
            await client.send_file(curate.BOTS[channel], video, caption=text or None, supports_streaming=True,
                                   attributes=None)
        except Exception as e:  # noqa: BLE001
            log(f"  отправка: {type(e).__name__}")
            continue
        sent += 1
        log(f"  📸 @{it['_owner']} ×{it['_ratio']:.1f} · {it['_views']} просм. → {channel}")
        await asyncio.sleep(5)
    st["seen"] = st.get("seen", [])[-2000:]
    st["last"] = now.isoformat()
    state_dir.mkdir(parents=True, exist_ok=True)
    sf.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    return {"рилсов": len(items), "выбрано": len(picks), "отправлено": sent, "пропущено": skipped,
            "аккаунты_агента": learned[:10]}
