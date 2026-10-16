"""Агент-куратор PAPA (решение владельца 16.10): папка-источник → лучшее → карточка в пульт ЭТОГО канала.

  PAPA·Давра (+ PAPA·Спорт) → 🎉 КАТТА ДАВРА Пульт;  PAPA·Музыка → ⭐ PaparazziUZ Пульт.
Профиль Разведки (= профиль владельца) читает каналы папки за время с прошлого запуска, отбирает посты,
которые «выстрелили» у своего канала (просмотры против обычных), без рекламы, без повторов одной новости,
с медиа; кадр проверяет Gemini (чужой логотип/@, реклама). Лучшие ПЕРЕСЫЛАЕТ боту-пульту — владелец
видит обычную карточку с ✓ рубрикой («📡 Куратор нашёл · @источник») и решает сам.
Без Gemini видео/фото не берём (лого не проверить) — дождутся следующего запуска."""
from __future__ import annotations

import asyncio
import base64
import datetime as dt
import json
import os
import re
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path

# Папки владельца (16.10: «я уже создал и собрал там нужные каналы»); PAPA·… — старые папки, на случай если появятся снова.
ROUTES = {"davra": ("KATTA DAVRA", "PAPA·Давра", "PAPA·Спорт"), "paparazzi": ("Paparazzi UZ", "PAPA·Музыка")}
BOTS = dict(x.split("=", 1) for x in os.environ.get(
    "CURATOR_BOTS", "davra=PapaGenplanBot,paparazzi=PaparazziUZ_PultBot").split(",") if "=" in x)
PER_RUN = {k: int(v) for k, v in (x.split("=", 1) for x in os.environ.get(
    "CURATOR_PER_RUN", "davra=5,paparazzi=4").split(",") if "=" in x)}
MAX_HOURS, MIN_AGE_MIN, MIN_VIEWS = 12, 40, 300
AD = re.compile(r"#?реклама|#?reklama|ҳамкорлик|hamkorlik|sotiladi|сотилади|нархи|narxi|скидк|chegirma|"
                r"чегирма|буюртма|buyurtma|доставка|yetkazib|📞|☎️|\+998[\s\d-]{9,}|t\.me/\+|joinchat|aksiya|акция", re.I)
URL = re.compile(r"https?://|t\.me/", re.I)
# Политика каналов (docs/CHANNELS.md, 16.10): политика и криминал — ни в КАТТА ДАВРА, ни в PaparazziUZ;
# шоу-бизнес и клипы — только в PaparazziUZ. Признаки — начало слова, кириллица и латиница.
_P = {
    "politics": r"сиёс|siyos|президент|prezident|парламент|parlament|депутат|deputat|сенатор|senator|сайлов|saylov|"
                r"мирзиёев|mirziyoyev|путин|putin|трамп|tramp|trump|зеленск|zelensk|уруш|urush|санкци|sanksiya|политик|выбор|войн",
    "crime": r"жиноят|jinoyat|қотил|qotil|ўлдир|o'ldir|ўғирла|o'g'irla|қамоқ|qamoq|ҳибсга|hibsga|зўрла|zo'rla|пичоқла|"
             r"pichoqla|убий|преступ|арестован|мурда|murda",
    "showbiz": r"клип|klip|премьер|premyer|premer|хонанда|xonanda|қўшиқчи|qo'shiqchi|концерт|konsert|актёр|aktyor|актрис|"
               r"aktris|шоу.?бизнес|shou.?biznes",
}
POLICY = {g: re.compile(r"(?<![\w'])(?:" + rx + ")", re.I) for g, rx in _P.items()}
FORBID = {"davra": ("politics", "crime", "showbiz"), "paparazzi": ("politics", "crime")}


def off_policy(text: str, channel: str) -> str:
    """Имя нарушенной группы политики канала или ''."""
    return next((g for g in FORBID.get(channel, ()) if POLICY[g].search(text or "")), "")
WORD = re.compile(r"[^\W\d_]{4,}")
VISION = """Это кадр из поста Telegram-канала. Ответь ТОЛЬКО JSON:
{"foreign_logo": true/false — на кадре есть логотип/водяной знак/@имя/название чужого канала или СМИ,
 "ad": true/false — это реклама (товар, цена, телефон, магазин),
 "bad": true/false — кровь, жестокость, 18+, мертвые}"""


def sig(text: str) -> set[str]:
    return {w.lower() for w in WORD.findall(text or "")}


def similar(a: set[str], b: set[str]) -> bool:
    if len(a) < 4 or len(b) < 4:
        return False
    return len(a & b) / len(a | b) >= 0.4


def score(views: int, median: float, age_h: float) -> float:
    """Насколько пост «выстрелил» у своего канала: просмотры против обычных, с поправкой на молодость поста."""
    return views / max(median, 1.0) / max(0.3, min(1.0, age_h / 12))


def is_ad(text: str, has_buttons: bool) -> bool:
    t = text or ""
    return bool(AD.search(t)) or len(URL.findall(t)) > 1 or (has_buttons and bool(URL.search(t)))


def pick(cands: list[dict], n: int, history: list[dict]) -> list[dict]:
    """Лучшие по score; одна новость — один раз (за этот запуск и последние 3 дня)."""
    seen = [set(h["sig"]) for h in history]
    out = []
    for c in sorted(cands, key=lambda c: -c["score"]):
        if len(out) >= n:
            break
        s = sig(c["text"])
        if any(similar(s, x) for x in seen) or c["key"] in {h["key"] for h in history}:
            continue
        seen.append(s)
        out.append(c)
    return out


# ---------- Gemini: проверка кадра ----------
def vision(jpeg: bytes) -> dict:
    key = os.environ["GEMINI_API_KEY"].strip().strip('"').strip("'")
    model = os.environ.get("GEMINI_MODEL", "gemini-flash-latest").strip().strip('"').removeprefix("models/") or "gemini-flash-latest"
    body = {"contents": [{"role": "user", "parts": [{"text": VISION},
                                                     {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(jpeg).decode()}}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 2048, "responseMimeType": "application/json"}}
    errs = []
    for attempt in range(3):                     # 503 «модель перегружена» — подождать и повторить
        for m in dict.fromkeys([model, "gemini-flash-latest"]):
            req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
                                         data=json.dumps(body).encode(), headers={"content-type": "application/json", "x-goog-api-key": key})
            try:
                data = json.loads(urllib.request.urlopen(req, timeout=60).read())
                parts = ((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
                raw = "".join(p.get("text", "") for p in parts if not p.get("thought"))
                return json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    if attempt == 2:                 # минутный лимит ждём, дневной — сдаёмся до следующего запуска
                        raise RuntimeError("лимит Gemini") from None
                    errs.append(f"{m}: 429")
                    time.sleep(65)
                    break
                errs.append(f"{m}: HTTP {e.code}")
            except Exception as e:  # noqa: BLE001
                errs.append(f"{m}: {type(e).__name__}")
        time.sleep(20 * (attempt + 1))
    raise RuntimeError("Gemini недоступен: " + "; ".join(errs[-2:]))


# ---------- Telegram ----------
async def folder_peers(client) -> dict[str, list]:
    from telethon.tl.functions.messages import GetDialogFiltersRequest
    res = await client(GetDialogFiltersRequest())
    out = {}
    for f in getattr(res, "filters", res):
        t = getattr(f, "title", "")
        out[str(getattr(t, "text", t)).strip()] = list(getattr(f, "include_peers", []) or [])
    return out


def _t(name: str) -> str:
    return re.sub(r"\s+", " ", str(name or "")).strip().casefold()


def peers_in(folders: dict[str, list], names) -> list:
    """Каналы из папок с этими названиями; регистр и лишние пробелы не важны."""
    by = {_t(k): v for k, v in folders.items()}
    return [p for n in names for p in by.get(_t(n), [])]


def kind(m) -> str | None:
    if m.video and not getattr(m.video, "round_message", False):
        return "video"
    if m.photo:
        return "photo"
    if m.audio:
        return "audio"
    return None


async def candidates(client, ent, since: dt.datetime, now: dt.datetime, channel: str, log=print) -> list[dict]:
    msgs = [m async for m in client.iter_messages(ent, limit=60, wait_time=1)]
    posts = [m for m in msgs if not m.action]
    views = [m.views or 0 for m in posts if m.date < now - dt.timedelta(hours=2)]
    median = statistics.median(views) if views else 0
    groups: dict[int, list] = {}
    for m in posts:
        if m.grouped_id:
            groups.setdefault(m.grouped_id, []).append(m)
    out, done = [], set()
    for m in posts:
        if m.date < since or m.date > now - dt.timedelta(minutes=MIN_AGE_MIN) or (m.grouped_id and m.grouped_id in done):
            continue
        part = sorted(groups.get(m.grouped_id, [m]), key=lambda x: x.id) if m.grouped_id else [m]
        if m.grouped_id:
            done.add(m.grouped_id)
        text = next((x.message for x in part if x.message), "") or ""
        k = kind(part[0])
        if not k or (k == "audio" and channel != "paparazzi"):
            continue
        if k == "video" and not (5 <= (part[0].file.duration or 0) <= 600):
            continue
        v = max(x.views or 0 for x in part)
        if v < MIN_VIEWS or is_ad(text, bool(getattr(part[0], "reply_markup", None))) or off_policy(text, channel):
            continue
        age = (now - m.date).total_seconds() / 3600
        out.append({"key": f"{ent.id}_{part[0].id}", "ent": ent, "ids": [x.id for x in part], "msg": part[0],
                    "text": text, "kind": k, "views": v, "score": score(v, median, age),
                    "source": "@" + ent.username if getattr(ent, "username", None) else (getattr(ent, "title", "") or "")})
    return out


async def clean_frame(client, c: dict) -> bool | None:
    """True — кадр чистый; False — чужое лого/реклама/жестокость; None — проверить нельзя (Gemini)."""
    if c["kind"] == "audio":
        return True
    try:
        jpeg = await client.download_media(c["msg"], file=bytes, thumb=-1)
    except Exception:  # noqa: BLE001
        jpeg = None
    if not jpeg:
        return None
    v = await asyncio.to_thread(vision, jpeg)
    return not (v.get("foreign_logo") or v.get("ad") or v.get("bad"))


async def run(client, state_dir: Path, now: dt.datetime | None = None, log=print) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    state_dir.mkdir(parents=True, exist_ok=True)
    sf = state_dir / "curator.json"
    try:
        st = json.loads(sf.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        st = {}
    hist = [h for h in st.get("history", []) if h["ts"] > (now - dt.timedelta(days=3)).isoformat()]
    folders = await folder_peers(client)
    report = {}
    gemini_ok = bool(os.environ.get("GEMINI_API_KEY"))
    for channel, names in ROUTES.items():
        since = dt.datetime.fromisoformat(st.get(f"last_{channel}", (now - dt.timedelta(hours=8)).isoformat()))
        since = max(since, now - dt.timedelta(hours=MAX_HOURS))
        peers = peers_in(folders, names)
        if not peers:
            report[channel] = "нет папки " + " / ".join(names) + " · есть: " + ", ".join(sorted(folders)) [:200]
            continue
        cands = []
        for p in peers:
            try:
                ent = await client.get_entity(p)
                cands += await candidates(client, ent, since, now, channel, log)
            except Exception as e:  # noqa: BLE001 — один канал не роняет куратора
                log(f"  {type(e).__name__}: {str(e)[:80]}")
            await asyncio.sleep(1)
        want = PER_RUN.get(channel, 4)
        sent, checked, skipped = 0, 0, 0
        for c in pick(cands, want * 3, hist):
            if sent >= want:
                break
            ok = None
            if gemini_ok:
                try:
                    ok = await clean_frame(client, c)
                    checked += 1
                except RuntimeError as e:
                    log(f"  проверка кадра: {e}")
                    gemini_ok = False
            if ok is None:                     # не проверить лого — не берём (правило владельца)
                continue
            if not ok:
                skipped += 1
                hist.append({"key": c["key"], "sig": sorted(sig(c["text"])), "ts": now.isoformat()})
                continue
            try:     # с подписью источника: в карточке пульта видно «📡 Куратор нашёл · @источник»
                await client.forward_messages(BOTS[channel], c["ids"], from_peer=c["ent"])
            except Exception as e:  # noqa: BLE001 — защищённые от пересылки каналы и т.п.
                log(f"  переслать {c['key']}: {type(e).__name__}")
                continue
            hist.append({"key": c["key"], "sig": sorted(sig(c["text"])), "ts": now.isoformat()})
            sent += 1
            log(f"  → {channel}: {c['source']} · {c['views']} просм. · ×{c['score']:.1f} · {c['text'][:50]!r}")
            await asyncio.sleep(4)
        if gemini_ok or not cands:             # без проверки кадров окно не сдвигаем — посты дождутся Gemini
            st[f"last_{channel}"] = now.isoformat()
        report[channel] = {"источников": len(peers), "кандидатов": len(cands), "переслано": sent,
                           "кадров_проверено": checked, "отбраковано": skipped}
        log(f"{channel}: {report[channel]}")
    st["history"] = hist[-600:]
    sf.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    return report
