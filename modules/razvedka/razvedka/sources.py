"""Отбор каналов-источников — «белый список» (решение владельца 26.10).

Владелец: «отберём специальные чистые каналы, откуда брать готовый текст и картинку/видео — 10–15 каналов,
по тематике». Агент сам:
  1) читает ВСЕ папки владельца (новости, Фойдалик, Жонли ижролар, кулгили, музыка…) — только чтение;
  2) по каждому каналу за 7 дней считает: постов/день, обычные просмотры, долю рекламы, долю медиа, кириллицу;
  3) у сильных каналов Gemini смотрит 3 самых популярных медиа-поста: есть ли чужой логотип / @ / водяной знак;
  4) раскладывает по темам наших каналов (квоты ниже) и отдаёт владельцу таблицу в главный пульт.
26.10 владелец: «схема должна работать непрерывно, без моего участия» — список применяется САМ (whitelist.json),
куратор берёт материал только из него, по понедельникам отбор повторяется. Владелец может лишь убрать канал (BLOCK).
Сам отбор ничего не публикует и не пересылает.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import math
import os
import re
import statistics
from pathlib import Path

from . import curate, sortfolders

DAYS = 7
MIN_PER_DAY, MIN_VIEWS, MAX_AD_SHARE, MIN_MEDIA = 0.5, 500, 0.35, 0.3
VISION_MAX = int(os.environ.get("SOURCES_VISION_MAX", "30"))      # каналов на проверку кадров за один прогон
SAMPLES = 2                                                        # медиа-постов на канал (оба должны быть чистыми)
CHECK_DAYS = 14                                                    # проверка кадров канала годна столько дней
# 26.10: дневной лимит основной модели съедают куратор и охота — отбор проверяет кадры на «лёгкой» модели (свой лимит)
VISION_MODEL = os.environ.get("SOURCES_GEMINI_MODEL", "gemini-flash-lite-latest")
CLEAN_MIN = 2 / 3                                                  # минимум чистых кадров, чтобы попасть в список
VIDEO_MAX_MB = 25
SKIP_FOLDERS = {"papa"}                                            # служебная папка (HUB, СКЛАД, POOL, тест)
OWN = curate.OWN | {"kattadavrauz", "paparazziuz"}
CYR = re.compile(r"[а-яёўқғҳ]", re.I)
LAT = re.compile(r"[a-z]", re.I)

# какие темы белого списка нужны каждому нашему каналу (политика docs/CHANNELS.md)
FOR_CHANNEL = {"xojaobod": ("news", "useful", "humor", "food", "faith"),
               "davra": ("news", "useful", "humor", "food"),
               "paparazzi": ("music", "humor")}
BLOCK = {"shohonakulgu"}           # 20.10 владелец: ставит своё лого на все видео; сюда же — убранные владельцем

# тема белого списка: (код, название, сколько брать, темы сортировщика, для каких наших каналов)
QUOTAS = [
    ("news", "🗞 Янгиликлар ва ҳудуд", 6, {"news", "local", "politics_official"}, "Хўжаобод · КАТТА ДАВРА"),
    ("useful", "💡 Фойдали ва уй-рўзғор", 3, {"useful", "home_business", "interesting"}, "КАТТА ДАВРА · Хўжаобод"),
    ("humor", "😂 Кулги", 2, {"humor"}, "КАТТА ДАВРА · Хўжаобод"),
    ("music", "🎤 Жонли ижро ва шоу", 2, {"live_music", "music", "showbiz"}, "PaparazziUZ"),
    ("food", "🍲 Таом ва саломатлик", 1, {"recipes", "health"}, "Хўжаобод · КАТТА ДАВРА"),
    ("faith", "🕌 Маънавият (Жума, дуо)", 1, {"religion"}, "Хўжаобод"),
]


# ---------- чистые функции (тесты) ----------
def stats(posts: list[dict], now: dt.datetime, days: int = DAYS) -> dict:
    """posts: {date, views, text, media(bool), ad(bool)} за период. Альбом — уже один пост."""
    since = now - dt.timedelta(days=days)
    p = [x for x in posts if x["date"] >= since]
    if not p:
        return {"posts": 0, "per_day": 0.0, "median_views": 0, "ad_share": 0.0, "media_share": 0.0, "cyr_share": 0.0}
    old = [x["views"] for x in p if x["date"] < now - dt.timedelta(hours=2)] or [x["views"] for x in p]
    texts = [x["text"] for x in p if x["text"]]
    cyr = sum(1 for t in texts if len(CYR.findall(t)) >= len(LAT.findall(t)))
    return {"posts": len(p), "per_day": round(len(p) / days, 1), "median_views": int(statistics.median(old)),
            "ad_share": round(sum(x["ad"] for x in p) / len(p), 2), "media_share": round(sum(x["media"] for x in p) / len(p), 2),
            "cyr_share": round(cyr / len(texts), 2) if texts else 0.0}


def eligible(s: dict) -> str:
    """'' — годится для проверки кадров; иначе причина отсева."""
    if s["per_day"] < MIN_PER_DAY:
        return "редко пишет"
    if s["median_views"] < MIN_VIEWS:
        return "мало просмотров"
    if s["ad_share"] > MAX_AD_SHARE:
        return "много рекламы"
    if s["media_share"] < MIN_MEDIA:
        return "мало фото/видео"
    return ""


def score(s: dict, clean: float | None) -> float:
    """Чистота важнее всего (в квадрате), дальше просмотры, меньше рекламы, регулярность."""
    if clean is None:
        return 0.0
    return round(clean ** 2 * math.log10(s["median_views"] + 10) * (1 - s["ad_share"])
                 * min(1.0, s["per_day"] / 5) ** 0.3, 3)


def theme(cats: list[str]) -> str | None:
    """Первая подходящая тема белого списка по темам сортировщика (порядок QUOTAS = приоритет)."""
    for code, _, _, want, _ in QUOTAS:
        if any(c in want for c in cats):
            return code
    return None


def shortlist(rows: list[dict]) -> dict[str, dict]:
    """По каждой теме: лучшие по квоте + 2 запасных. Канал — только в одной теме."""
    out, used = {}, set()
    for code, name, n, _, who in QUOTAS:
        cand = sorted((r for r in rows if r.get("theme") == code and r.get("clean") is not None
                       and (r.get("username") or "").lower() not in BLOCK
                       and r["clean"] >= CLEAN_MIN and r["id"] not in used), key=lambda r: -r["score"])
        top, spare = cand[:n], cand[n:n + 2]
        used |= {r["id"] for r in top}
        out[code] = {"name": name, "n": n, "who": who, "top": top, "spare": spare}
    return out


def _views(v: int) -> str:
    return f"{v / 1000:.0f}K" if v >= 10000 else (f"{v / 1000:.1f}K" if v >= 1000 else str(v))


def _subs(v: int | None) -> str:
    if not v:
        return "—"
    return f"{v / 1e6:.2f} млн" if v >= 1e6 else f"{v / 1000:.0f}K"


def _line(i: int, r: dict) -> str:
    who = "@" + r["username"] if r.get("username") else "без @"
    return (f"{i}. {r['title'][:32]} ({who})\n"
            f"   👥 {_subs(r.get('subscribers'))} · 👁 {_views(r['median_views'])} · 📝 {r['per_day']}/д · "
            f"📢 {int(r['ad_share'] * 100)}% · 🧼 {r['clean_n']}/{r['checked']}"
            + (" · латиница" if r["cyr_share"] < 0.5 else ""))


def render(sl: dict[str, dict], rows: list[dict], generated: str, folders: int) -> str:
    total = sum(len(v["top"]) for v in sl.values())
    lines = [f"📡 PAPA · ОТБОР ИСТОЧНИКОВ · {generated}",
             f"Прочитано папок: {folders} · каналов: {len(rows)} · проверено кадров у {sum(1 for r in rows if r.get('checked'))}",
             f"Предлагаю белый список: {total} каналов. 🧼 = чистых кадров из проверенных.", ""]
    k = 0
    for code, v in sl.items():
        lines.append(f"{v['name']} — {len(v['top'])}/{v['n']} (для: {v['who']})")
        if not v["top"]:
            lines.append("   ⚠️ чистых каналов этой темы нет — добавьте в папку 1–2 канала")
        for r in v["top"]:
            k += 1
            lines.append(_line(k, r))
        for r in v["spare"]:
            lines.append("   запас: " + f"{r['title'][:30]} · 👁 {_views(r['median_views'])} · 🧼 {r['clean_n']}/{r['checked']}")
        lines.append("")
    dirty = sorted((r for r in rows if r.get("checked") and r["clean"] is not None and r["clean"] < CLEAN_MIN),
                   key=lambda r: -r["median_views"])[:8]
    if dirty:
        lines.append("🚫 Сильные, но с чужим логотипом на кадрах (не берём): "
                     + ", ".join(f"{r['title'][:22]} {r['clean_n']}/{r['checked']}" for r in dirty))
    unchecked = [r for r in rows if r.get("checked") == 0 and r.get("why") == ""]
    if unchecked:
        lines.append(f"⏳ Не успели проверить кадры (лимит Gemini): {len(unchecked)} — проверятся при следующем отборе.")
    lines += ["", "Конкурентов (Водий бозор, ANDIJON BUGUN) как источник не берём — только изучаем.",
              "✅ Список применён сам: куратор берёт материал только из него, по понедельникам отбор обновляется.",
              "Убрать канал — напишите Claude его номер."]
    return "\n".join(lines)


def check_order(good: list[dict]) -> list[dict]:
    """Кого проверять по кадрам: по каждой теме сильнейшие (квота×2+2), темы по кругу — все темы продвигаются."""
    per = []
    for code, _, n, _, _ in QUOTAS:
        cand = sorted((r for r in good if r.get("theme") == code and (r.get("username") or "").lower() not in BLOCK),
                      key=lambda r: -r["median_views"])[:n * 2 + 2]
        per.append([r for r in cand if r.get("clean") is None])
    out = []
    while any(per):
        for q in per:
            if q:
                out.append(q.pop(0))
    return out


def complete_list(sl: dict[str, dict]) -> bool:
    return all(len(v["top"]) >= v["n"] for v in sl.values())


def whitelist(sl: dict[str, dict], generated: str) -> dict:
    """Белый список для куратора и утреннего блока: тема → каналы; канал → темы."""
    themes = {c: [{"id": r["id"], "title": r["title"], "username": r.get("username")} for r in v["top"]]
              for c, v in sl.items()}
    return {"generated": generated, "themes": themes, "for_channel": {k: list(v) for k, v in FOR_CHANNEL.items()}}


def load_whitelist(path: Path) -> dict | None:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def ids_for(wl: dict | None, channel: str) -> list[int]:
    """id каналов-источников белого списка для нашего канала; [] — списка нет (куратор работает по папкам)."""
    if not wl:
        return []
    themes = (wl.get("for_channel") or {}).get(channel, FOR_CHANNEL.get(channel, ()))
    if themes and not (wl.get("themes") or {}).get(themes[0]):
        return []                       # главная тема канала пуста (напр. жонли ижро) — куратор по папкам, как раньше
    out = []
    for t in themes:
        for x in (wl.get("themes") or {}).get(t, []):
            if x["id"] not in out and (x.get("username") or "").lower() not in BLOCK:
                out.append(x["id"])
    return out


# ---------- Telegram (только чтение) ----------
async def _channel_posts(client, ent, now: dt.datetime) -> tuple[list[dict], list]:
    since = now - dt.timedelta(days=DAYS)
    posts, media_msgs, seen = [], [], set()
    async for m in client.iter_messages(ent, limit=400, wait_time=1):
        if m.date < since:
            break
        if m.action or (m.grouped_id and m.grouped_id in seen):
            continue
        if m.grouped_id:
            seen.add(m.grouped_id)
        k = curate.kind(m)
        text = m.message or ""
        ad = curate.is_ad(text, bool(getattr(m, "reply_markup", None)))
        posts.append({"date": m.date, "views": m.views or 0, "text": text, "media": k in ("video", "photo"), "ad": ad})
        if k in ("video", "photo") and not ad:
            media_msgs.append(m)
    return posts, media_msgs


async def _clean(client, msgs: list) -> tuple[int, int]:
    """(чистых, проверено) по SAMPLES самым популярным медиа-постам. RuntimeError — лимит Gemini."""
    ok = n = 0
    for m in sorted(msgs, key=lambda x: -(x.views or 0))[:SAMPLES]:
        k = curate.kind(m)
        if k == "video" and (getattr(m.file, "size", 0) or 0) > VIDEO_MAX_MB * 1024 * 1024:
            continue
        c = {"kind": k, "msg": m}
        res = await curate.clean_frame(client, c)
        if res is None:
            continue
        n += 1
        ok += not c.get("foreign_logo")                    # главное — чужой логотип; реклама на кадре сюда не входит
        await asyncio.sleep(2)
    return ok, n


async def run(client, out_dir: Path, now: dt.datetime | None = None, log=print) -> dict:
    from telethon.tl.functions.channels import GetFullChannelRequest
    now = now or dt.datetime.now(dt.timezone.utc)
    if os.environ.get("GEMINI_API_KEY"):              # темы и кадры — на «лёгкой» модели (свой дневной лимит)
        os.environ["GEMINI_MODEL"] = VISION_MODEL
    folders = await curate.folder_peers(client)
    use = {k: v for k, v in folders.items() if curate._t(k) not in SKIP_FOLDERS}
    log(f"папок: {len(use)} — " + ", ".join(sorted(use)))
    rows, ents, media = [], {}, {}
    seen = set()
    for fname, peers in use.items():
        for p in peers:
            try:
                ent = await client.get_entity(p)
            except Exception as e:  # noqa: BLE001
                log(f"  {fname}: {type(e).__name__}")
                continue
            title = (getattr(ent, "title", "") or "")
            if (ent.id in seen or not getattr(ent, "broadcast", False) or (getattr(ent, "username", "") or "").lower() in OWN
                    or any(w in title.upper() for w in ("ХАБ", "XАБ", "HUB", "PAPA", "NEXUS"))):
                continue
            seen.add(ent.id)
            try:
                posts, mm = await _channel_posts(client, ent, now)
            except Exception as e:  # noqa: BLE001 — один канал не роняет отбор
                log(f"  {title[:30]}: {type(e).__name__}")
                continue
            s = stats(posts, now)
            r = {"id": ent.id, "title": title, "username": getattr(ent, "username", None), "folder": fname, **s,
                 "why": eligible(s), "texts": [x["text"].replace("\n", " ")[:140] for x in posts if x["text"]][:10],
                 "checked": 0, "clean_n": 0, "clean": None, "subscribers": None}
            rows.append(r)
            ents[ent.id], media[ent.id] = ent, mm
            log(f"  [{len(rows)}] {title[:34]}: {s['posts']} п., 👁 {s['median_views']}, реклама {s['ad_share']} {r['why']}")
            await asyncio.sleep(1)
    # темы: Gemini (бесплатно), без него — по ключевым словам
    good = [r for r in rows if not r["why"]]
    cats = await asyncio.to_thread(sortfolders.classify, good, 10, log)
    for r in good:
        r["cats"] = cats.get(str(r["id"])) or cats.get(r["id"]) or sortfolders.keyword_cats(r)
        r["theme"] = theme(r["cats"])
    # кадры: проверки прошлых прогонов (14 дней) + новые — по темам по кругу, не больше VISION_MAX за прогон
    cache_f = out_dir / "checks.json"
    try:
        cache = json.loads(cache_f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    fresh = (now - dt.timedelta(days=CHECK_DAYS)).isoformat()
    for r in good:
        c = cache.get(str(r["id"]))
        if c and c.get("at", "") >= fresh and c.get("checked"):
            r["clean_n"], r["checked"] = c["clean_n"], c["checked"]
            r["clean"] = r["clean_n"] / r["checked"]
            r["score"] = score(r, r["clean"])
    todo = check_order(good)
    gemini = bool(os.environ.get("GEMINI_API_KEY"))
    done = 0
    for r in todo:
        if not gemini or done >= VISION_MAX:
            break
        try:
            r["clean_n"], r["checked"] = await _clean(client, media[r["id"]])
        except RuntimeError as e:
            log(f"  кадры: {e} — остальные в следующий раз")
            gemini = False
            continue
        done += 1
        if r["checked"]:
            r["clean"] = r["clean_n"] / r["checked"]
            cache[str(r["id"])] = {"clean_n": r["clean_n"], "checked": r["checked"], "at": now.isoformat()}
        r["score"] = score(r, r["clean"])
        log(f"  🧼 {r['title'][:30]}: {r['clean_n']}/{r['checked']}")
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_f.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    for r in rows:
        r.setdefault("score", 0.0)
    sl = shortlist(rows)
    for v in sl.values():                                # подписчики — только у тех, кого показываем
        for r in v["top"] + v["spare"]:
            try:
                r["subscribers"] = (await client(GetFullChannelRequest(ents[r["id"]]))).full_chat.participants_count
            except Exception:  # noqa: BLE001
                pass
            await asyncio.sleep(1)
    gen = now.astimezone(dt.timezone(dt.timedelta(hours=5))).strftime("%d.%m.%Y %H:%M")
    text = render(sl, rows, gen, len(use))
    out_dir.mkdir(parents=True, exist_ok=True)
    keep = ("id", "title", "username", "folder", "posts", "per_day", "median_views", "ad_share", "media_share",
            "cyr_share", "why", "theme", "checked", "clean_n", "clean", "score", "subscribers")
    data = {"generated": gen, "proposal": {c: [r["id"] for r in v["top"]] for c, v in sl.items()},
            "rows": [{k: r.get(k) for k in keep} for r in rows], "text": text}
    tmp = out_dir / ".latest.json.tmp"
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, out_dir / "latest.json")
    wl = whitelist(sl, gen)
    n_in = sum(len(v) for v in wl["themes"].values())
    if n_in >= 5:                                     # явно неудачный прогон старый список не затирает
        tmp = out_dir / ".whitelist.json.tmp"
        tmp.write_text(json.dumps(wl, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, out_dir / "whitelist.json")
    left = [r for r in check_order(good) if r.get("clean") is None]
    complete = complete_list(sl) or not left
    pending = out_dir / "pending"
    if complete:
        pending.unlink(missing_ok=True)
    else:                                             # недобор — ежедневный прогон продолжит проверку сам
        pending.write_text(now.isoformat(), encoding="utf-8")
    # 26.10: владельцу — только готовый список; пустые/недобранные таблицы не шлём
    return {"каналов": len(rows), "годных": len(good), "в списке": n_in, "осталось проверить": len(left),
            "text": text if complete else None}
