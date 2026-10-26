"""Отбор каналов-источников — «белый список» (решение владельца 26.10).

Владелец: «отберём специальные чистые каналы, откуда брать готовый текст и картинку/видео — 10–15 каналов,
по тематике». Агент сам:
  1) читает ТОЛЬКО три папки наших каналов (26.10, 2-я правка владельца: «3 канала = 3 папки, каналы там уже
     собраны — осталось отсортировать и брать чистое»): XOJAOBOD CITY, KATTA DAVRA, Paparazzi UZ — только чтение;
  2) по каждому каналу за 7 дней считает: постов/день, обычные просмотры, долю рекламы, долю медиа, кириллицу;
  3) у сильных каналов Gemini смотрит 3 самых популярных медиа-поста: есть ли чужой логотип / @ / водяной знак;
  4) сортирует каналы каждой папки по рубрикам ЭТОГО канала (квоты PROFILES) — три личных куратора на одном движке.
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
OWN = curate.OWN | {"kattadavrauz", "paparazziuz"}
CYR = re.compile(r"[а-яёўқғҳ]", re.I)
LAT = re.compile(r"[a-z]", re.I)

BLOCK = {"shohonakulgu"}           # 20.10 владелец: ставит своё лого на все видео; сюда же — убранные владельцем

# 26.10 (2): «3 канала = 3 папки». Один движок — три личных куратора: у каждого нашего канала своя папка-источник
# (её владелец собрал сам), свои рубрики и квоты (политика docs/CHANNELS.md). Другие папки отбор не читает.
# (код канала, название, папки — первая основная, рубрика → сколько брать)
PROFILES = [
    ("xojaobod", "🏙 ХЎЖАОБОД CITY 24", ("XOJAOBOD CITY", "PAPA·Шаҳар"),
     {"news": 4, "useful": 3, "humor": 2, "food": 1, "faith": 1}),
    ("davra", "🎉 КАТТА ДАВРА", ("KATTA DAVRA", "PAPA·Давра", "PAPA·Спорт"),
     {"useful": 4, "humor": 3, "news": 2, "food": 1}),
    ("paparazzi", "⭐ PAPARAZZI UZ", ("Paparazzi UZ", "PAPA·Музыка"),
     {"music": 5, "humor": 2}),
]
# рубрика: (код, название, темы сортировщика); порядок = приоритет, если канал подходит под несколько
THEMES = [
    ("news", "🗞 Янгиликлар", {"news", "local", "politics_official"}),
    ("useful", "💡 Фойдали", {"useful", "home_business", "interesting"}),
    ("humor", "😂 Кулги", {"humor"}),
    ("music", "🎤 Жонли ижро ва шоу", {"live_music", "music", "showbiz"}),
    ("food", "🍲 Таом ва саломатлик", {"recipes", "health"}),
    ("faith", "🕌 Маънавият", {"religion"}),
]
THEME_NAME = {c: n for c, n, _ in THEMES}


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


def theme(cats: list[str], allowed=None) -> str | None:
    """Первая подходящая рубрика по темам сортировщика; allowed — только рубрики этого нашего канала."""
    for code, _, want in THEMES:
        if (allowed is None or code in allowed) and any(c in want for c in cats):
            return code
    return None


def _ok(r: dict, ch: str, code: str) -> bool:
    return ((r.get("theme_by") or {}).get(ch) == code and r.get("clean") is not None and r["clean"] >= CLEAN_MIN
            and (r.get("username") or "").lower() not in BLOCK)


def shortlist(rows: list[dict]) -> dict[str, dict[str, dict]]:
    """Канал → рубрика → лучшие по квоте + 2 запасных. Каждый канал — только из своей папки;
    внутри канала источник стоит в одной рубрике."""
    out = {}
    for ch, _, _, quotas in PROFILES:
        used, out[ch] = set(), {}
        for code, n in quotas.items():
            cand = sorted((r for r in rows if _ok(r, ch, code) and r["id"] not in used), key=lambda r: -r["score"])
            top, spare = cand[:n], cand[n:n + 2]
            used |= {r["id"] for r in top}
            out[ch][code] = {"name": THEME_NAME[code], "n": n, "top": top, "spare": spare}
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


def render(sl: dict[str, dict], rows: list[dict], generated: str, found: dict[str, str | None]) -> str:
    total = sum(len(v["top"]) for ch in sl.values() for v in ch.values())
    lines = [f"📡 PAPA · ОТБОР ИСТОЧНИКОВ · {generated}",
             f"Только 3 папки наших каналов · каналов в них: {len(rows)} · проверено кадров у "
             f"{sum(1 for r in rows if r.get('checked'))}",
             f"Белый список: {total} каналов. 🧼 = чистых кадров из проверенных.", ""]
    k = 0
    for ch, title, folders, _ in PROFILES:
        mine = [r for r in rows if ch in r.get("for", ())]
        if not found.get(ch):
            lines += [f"━━ {title}", f"   ⚠️ папка «{folders[0]}» не найдена — источников нет", ""]
            continue
        lines.append(f"━━ {title} · папка «{found[ch]}» · каналов: {len(mine)}")
        for code, v in sl[ch].items():
            lines.append(f"{v['name']} — {len(v['top'])}/{v['n']}")
            if not v["top"]:
                lines.append("   ⚠️ чистых каналов нет — добавьте в папку 1–2 канала этой темы")
            for r in v["top"]:
                k += 1
                lines.append(_line(k, r))
            for r in v["spare"]:
                lines.append("   запас: " + f"{r['title'][:30]} · 👁 {_views(r['median_views'])} · 🧼 {r['clean_n']}/{r['checked']}")
        off = [r for r in mine if not r["why"] and (r.get("theme_by") or {}).get(ch) is None]
        if off:
            lines.append("↪️ не по рубрикам канала: " + ", ".join(r["title"][:22] for r in off[:6])
                         + (f" и ещё {len(off) - 6}" if len(off) > 6 else ""))
        weak = [r for r in mine if r["why"]]
        if weak:
            lines.append(f"💤 слабые (мало постов/просмотров, много рекламы): {len(weak)}")
        lines.append("")
    dirty = sorted((r for r in rows if r.get("checked") and r["clean"] is not None and r["clean"] < CLEAN_MIN),
                   key=lambda r: -r["median_views"])[:8]
    if dirty:
        lines.append("🚫 С чужим логотипом на кадрах (не берём, из папки не удалено): "
                     + ", ".join(f"{r['title'][:22]} {r['clean_n']}/{r['checked']}" for r in dirty))
    unchecked = [r for r in rows if r.get("checked") == 0 and r.get("why") == "" and r.get("theme_by")]
    if unchecked:
        lines.append(f"⏳ Не успели проверить кадры (лимит Gemini): {len(unchecked)} — проверятся при следующем отборе.")
    lines += ["", "✅ Список применён сам: куратор каждого канала берёт материал только из своего списка.",
              "По понедельникам отбор обновляется. Убрать канал — напишите Claude его номер."]
    return "\n".join(lines)


def check_order(good: list[dict]) -> list[dict]:
    """Кого проверять по кадрам: по каждому каналу и рубрике сильнейшие (квота×2+2), по кругу — продвигаются все."""
    per = []
    for ch, _, _, quotas in PROFILES:
        for code, n in quotas.items():
            cand = sorted((r for r in good if (r.get("theme_by") or {}).get(ch) == code
                           and (r.get("username") or "").lower() not in BLOCK), key=lambda r: -r["median_views"])[:n * 2 + 2]
            per.append([r for r in cand if r.get("clean") is None])
    out, seen = [], set()
    while any(per):
        for q in per:
            if q:
                r = q.pop(0)
                if r["id"] not in seen:
                    seen.add(r["id"])
                    out.append(r)
    return out


def complete_list(sl: dict[str, dict]) -> bool:
    return all(len(v["top"]) >= v["n"] for ch in sl.values() for v in ch.values())


def whitelist(sl: dict[str, dict], generated: str) -> dict:
    """Белый список v2: наш канал → рубрика → источники (только из папки этого канала)."""
    return {"generated": generated, "version": 2,
            "channels": {ch: {c: [{"id": r["id"], "title": r["title"], "username": r.get("username")} for r in v["top"]]
                              for c, v in themes.items()} for ch, themes in sl.items()}}


def load_whitelist(path: Path) -> dict | None:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def ids_for(wl: dict | None, channel: str) -> list[int]:
    """id источников белого списка для нашего канала; [] — списка нет или он старого вида (куратор работает
    по папке своего канала — это тоже правильно, «папка = канал»)."""
    if not wl or wl.get("version") != 2:
        return []
    mine = (wl.get("channels") or {}).get(channel) or {}
    main = next((list(q)[0] for c, _, _, q in PROFILES if c == channel), None)
    if main and not mine.get(main):
        return []                       # главная рубрика пуста (напр. жонли ижро) — куратор по папке, как раньше
    out = []
    for xs in mine.values():
        for x in xs:
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
    by = {curate._t(k): k for k in folders}
    found, plan = {}, []                              # 26.10 (2): только папки наших трёх каналов
    for ch, _, names, _ in PROFILES:
        name = next((by[curate._t(n)] for n in names if curate._t(n) in by), None)
        found[ch] = name
        if name:
            plan += [(ch, name, p) for p in folders[name]]
    log("папки: " + ", ".join(f"{ch}={found[ch] or 'НЕТ'}" for ch in found) + f" (всего у владельца {len(folders)})")
    rows, ents, media = [], {}, {}
    by_id: dict[int, dict] = {}
    for ch, fname, p in plan:
        try:
            ent = await client.get_entity(p)
        except Exception as e:  # noqa: BLE001
            log(f"  {fname}: {type(e).__name__}")
            continue
        title = (getattr(ent, "title", "") or "")
        if ent.id in by_id:                           # канал в двух папках — читаем один раз, служит обоим
            by_id[ent.id]["for"].append(ch)
            continue
        if (not getattr(ent, "broadcast", False) or (getattr(ent, "username", "") or "").lower() in OWN
                or any(w in title.upper() for w in ("ХАБ", "XАБ", "HUB", "PAPA", "NEXUS", "ПУЛЬТ", "PULT"))):
            continue                                  # наши каналы, ХАБы, пульты, группы — не источники
        try:
            posts, mm = await _channel_posts(client, ent, now)
        except Exception as e:  # noqa: BLE001 — один канал не роняет отбор
            log(f"  {title[:30]}: {type(e).__name__}")
            continue
        s = stats(posts, now)
        r = {"id": ent.id, "title": title, "username": getattr(ent, "username", None), "folder": fname, "for": [ch],
             **s, "why": eligible(s), "texts": [x["text"].replace("\n", " ")[:140] for x in posts if x["text"]][:10],
             "checked": 0, "clean_n": 0, "clean": None, "subscribers": None, "theme_by": {}}
        rows.append(r)
        by_id[ent.id] = r
        ents[ent.id], media[ent.id] = ent, mm
        log(f"  [{len(rows)}] {ch} · {title[:34]}: {s['posts']} п., 👁 {s['median_views']}, реклама {s['ad_share']} {r['why']}")
        await asyncio.sleep(1)
    # темы: Gemini (бесплатно), без него — по ключевым словам
    good = [r for r in rows if not r["why"]]
    cats = await asyncio.to_thread(sortfolders.classify, good, 10, log)
    for r in good:
        r["cats"] = cats.get(str(r["id"])) or cats.get(r["id"]) or sortfolders.keyword_cats(r)
        r["theme_by"] = {ch: t for ch in r["for"]
                         if (t := theme(r["cats"], dict((x[0], x[3]) for x in PROFILES)[ch]))}
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
    shown = {r["id"]: r for chs in sl.values() for v in chs.values() for r in v["top"] + v["spare"]}
    for r in shown.values():                             # подписчики — только у тех, кого показываем
        if True:
            try:
                r["subscribers"] = (await client(GetFullChannelRequest(ents[r["id"]]))).full_chat.participants_count
            except Exception:  # noqa: BLE001
                pass
            await asyncio.sleep(1)
    gen = now.astimezone(dt.timezone(dt.timedelta(hours=5))).strftime("%d.%m.%Y %H:%M")
    text = render(sl, rows, gen, found)
    out_dir.mkdir(parents=True, exist_ok=True)
    keep = ("id", "title", "username", "folder", "for", "theme_by", "posts", "per_day", "median_views", "ad_share", "media_share",
            "cyr_share", "why", "checked", "clean_n", "clean", "score", "subscribers")
    data = {"generated": gen, "proposal": {ch: {c: [r["id"] for r in v["top"]] for c, v in t.items()} for ch, t in sl.items()},
            "rows": [{k: r.get(k) for k in keep} for r in rows], "text": text}
    tmp = out_dir / ".latest.json.tmp"
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, out_dir / "latest.json")
    wl = whitelist(sl, gen)
    n_in = len({x["id"] for t in wl["channels"].values() for xs in t.values() for x in xs})
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
