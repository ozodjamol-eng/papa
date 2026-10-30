"""Отбор каналов-источников (решения владельца 26.10).

Итог 26.10 (3-я правка владельца): «система предлагает — я выбираю, так проще; и свой вывод тоже делай».
  1) Читаем ТОЛЬКО папки наших каналов: XOJAOBODCITY → Хўжаобод, KATTA DAVRA → КАТТА ДАВРА, Paparazzi UZ → PaparazziUZ;
     для рубрики «Новости» — ещё папку владельца «Новости» (там Тезкор Хабарлар, Tezkor Yangiliklar и др.).
  2) По каждому каналу за 7 дней: постов/день, обычные просмотры, доля рекламы, медиа, кириллица.
  3) Gemini смотрит кадры сильных каналов: есть ли чужой логотип / @ / водяной знак (кэш 14 дней).
  4) По каждому нашему каналу и рубрике — до 5 кандидатов с выводом Claude (⭐ рекомендую / 👍 можно / ⚠️ / 🚫).
  5) Карточка с галочками — в PAPA ШТАБ; владелец отмечает и жмёт «✅ Утверждаю» (обработка — genplan.sources_choice).
     САМО НИЧЕГО НЕ ПРИМЕНЯЕТСЯ: куратор берёт материал только из выбранных владельцем (choice.json),
     до выбора — по папке своего канала. Сам отбор ничего не публикует и не пересылает.
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
SAMPLES = 2                                                        # медиа-постов на канал
CHECK_DAYS = 14                                                    # проверка кадров канала годна столько дней
VISION_MODEL = os.environ.get("SOURCES_GEMINI_MODEL", "gemini-flash-lite-latest")
CLEAN_MIN = 2 / 3                                                  # минимум чистых кадров
VIDEO_MAX_MB = 25
SHOW = 5                                                           # кандидатов на рубрику — владелец выбирает
CHOICE = Path(os.environ.get("SOURCES_CHOICE", "/var/lib/papa-sources-choice/choice.json"))
OWN = curate.OWN | {"kattadavrauz", "paparazziuz"}
CYR = re.compile(r"[а-яёўқғҳ]", re.I)
LAT = re.compile(r"[a-z]", re.I)
BLOCK = {"shohonakulgu"}           # 20.10 владелец: ставит своё лого на все видео; сюда же — убранные владельцем

# рубрика: (код, название, темы сортировщика); порядок = приоритет, если канал подходит под несколько
THEMES = [
    ("news", "🗞 Янгиликлар", {"news", "local", "politics_official"}),
    ("useful", "💡 Фойдали", {"useful", "home_business"}),
    ("fun", "🎉 Кўнгилочар", {"interesting", "sport"}),
    ("humor", "😂 Кулги", {"humor"}),
    ("music", "🎤 Жонли ижро ва шоу", {"live_music", "music", "showbiz"}),
    ("food", "🍲 Таом ва саломатлик", {"recipes", "health"}),
    ("faith", "🕌 Маънавият", {"religion"}),
    ("warn", "⚠️ Огоҳлантириш", set()),        # 30.10: по названию канала (NAME_THEMES), не по темам сортировщика
    ("money", "💵 Курс/нарх", set()),
]
# 30.10: рубрики, которые узнаём по названию/юзернейму канала (сортировщик их не различает)
NAME_THEMES = {"warn": ("kiberjinoyat", "кибержиноят", "iiv", "иив", "ichkiishlar", "ички ишлар", "firibgar", "фирибгар"),
               "money": ("bank", "банк", "valyuta", "валюта", "kurs", "курс", "dollar", "доллар", "narx", "нарх", "cbu")}
THEME_NAME = {c: n for c, n, _ in THEMES}
# наш канал: (код, название, папки — первая основная, рубрики по порядку важности)
PROFILES = [
    ("xojaobod", "🏙 ХЎЖАОБОД CITY 24", ("XOJAOBOD CITY", "XOJAOBODCITY", "PAPA·Шаҳар"),
     ("news", "useful", "humor", "food", "faith", "warn", "money")),
    ("davra", "🎉 КАТТА ДАВРА", ("KATTA DAVRA", "PAPA·Давра", "PAPA·Спорт"), ("news", "fun", "humor", "useful", "faith", "food")),
    ("paparazzi", "⭐ PAPARAZZI UZ", ("Paparazzi UZ", "PAPA·Музыка"), ("music", "humor")),
]
NEWS_FOLDERS = ("Новости", "Yangiliklar", "Янгиликлар")           # для рубрики «Новости» — ещё эта папка владельца
NO_POLITICS = {"davra", "paparazzi"}                               # docs/CHANNELS.md: без политики
# 26.10 владелец: «помнишь эти два — Тезкор Хабарлар и …» — всегда в кандидатах новостей, если есть в папках
MUST = {"news": ("тезкорхабар", "tezkorxabar", "tezkoryangilik", "тезкорянгилик")}


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
            + (" · латиница" if r["cyr_share"] < 0.5 else "") + f"\n   {verdict(r)[1]}")


def _norm(name: str) -> str:
    """Только буквы и цифры, без регистра: «🏙 XOJAOBOD  CITY 24» → «xojaobodcity24»."""
    return re.sub(r"[\W_]+", "", str(name or "")).casefold()


def folder_match(titles: list[str], names) -> str | None:
    """Папка: сначала точное имя, потом без эмодзи/пробелов, потом «начинается с» (XOJAOBOD CITY 24)."""
    for test in (lambda t, n: curate._t(t) == curate._t(n), lambda t, n: _norm(t) == _norm(n),
                 lambda t, n: _norm(n) and _norm(t).startswith(_norm(n))):
        for n in names:
            hit = [t for t in titles if test(t, n)]
            if hit:
                return min(hit, key=len)
    return None


def theme(cats: list[str], allowed=None, politics: bool = True) -> str | None:
    """Первая подходящая рубрика; allowed — только рубрики этого канала; politics=False — пресс-службы не берём."""
    if not politics and "politics_official" in cats:
        return None
    for code, _, want in THEMES:
        if (allowed is None or code in allowed) and any(c in want for c in cats):
            return code
    return None


RARE_OK = {"music"}             # 26.10 владелец: каналы артистов пишут раз в 2–3 дня — для жонли ижро это норма


def relax_rare(r: dict) -> None:
    """Жонли ижро: «редко пишет» не отсеивает (пост редкий, но ценный) — остаётся проверка кадров и просмотров."""
    if r.get("why") == "редко пишет" and r.get("posts", 0) >= 1 and RARE_OK & set((r.get("theme_by") or {}).values()):
        r["why"] = eligible({**r, "per_day": MIN_PER_DAY})   # остальные проверки (просмотры, реклама, медиа) — как у всех
        r["rare"] = not r["why"]


def is_must(r: dict, code: str) -> bool:
    n = _norm(r.get("title")) + _norm(r.get("username"))
    return any(m in n for m in MUST.get(code, ()))


def verdict(r: dict) -> tuple[int, str]:
    """Вывод Claude по кандидату: (ранг 0 — лучший, текст)."""
    c = r.get("clean")
    if c is not None and c < CLEAN_MIN:
        return 3, "🚫 Не советую: на кадрах чужой логотип"
    if c is None:
        return 2, "⚠️ Осторожно: кадры ещё не проверены"
    notes = []
    if r.get("cyr_share", 1) < 0.5:
        notes.append("латиница — переведём в кириллицу")
    if r.get("ad_share", 0) > 0.2:
        notes.append("много рекламы — рекламу куратор не берёт")
    if r.get("why"):
        notes.append(r["why"])
    if r.get("rare"):
        notes.append("пишет редко — материал ценный, но его мало")
    if not notes and c >= 1 and r.get("median_views", 0) >= 3000:
        return 0, "⭐ Рекомендую: чистые кадры, живые просмотры"
    return 1, "👍 Можно" + (": " + ", ".join(notes) if notes else ": чистые кадры")


def candidates(rows: list[dict], ch: str, code: str, n: int = SHOW) -> list[dict]:
    """До n кандидатов рубрики: сначала по выводу, потом по счёту. Грязные и слабые — только если «обязательные»."""
    pool = [r for r in rows if (r.get("theme_by") or {}).get(ch) == code and (r.get("username") or "").lower() not in BLOCK]
    ok = [r for r in pool if (not r.get("why") and verdict(r)[0] < 3) or is_must(r, code)]
    ok.sort(key=lambda r: (verdict(r)[0], -r.get("score", 0), -r.get("median_views", 0)))
    top = ok[:n]
    for r in ok[n:]:                                      # обязательный не выпадает из пятёрки
        if is_must(r, code):
            i = next((j for j in range(len(top) - 1, -1, -1) if not is_must(top[j], code)), None)
            if i is not None:
                top[i] = r
    return top


def build(rows: list[dict]) -> dict[str, dict[str, list[dict]]]:
    """Наш канал → рубрика → кандидаты."""
    return {ch: {code: candidates(rows, ch, code) for code in rubrics} for ch, _, _, rubrics in PROFILES}


def check_order(good: list[dict]) -> list[dict]:
    """Кого проверять по кадрам: обязательные, потом по каждому каналу и рубрике сильнейшие (SHOW+2), по кругу."""
    per = [[r for r in good if r.get("clean") is None and any(is_must(r, c) for c in MUST)]]
    for ch, _, _, rubrics in PROFILES:
        for code in rubrics:
            cand = sorted((r for r in good if (r.get("theme_by") or {}).get(ch) == code
                           and (r.get("username") or "").lower() not in BLOCK), key=lambda r: -r["median_views"])[:SHOW + 2]
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


def card(ch: str, cands: dict[str, list[dict]], rows: list[dict], found: str | None, generated: str,
         chosen: set[int] | None = None) -> tuple[str, dict | None]:
    """Карточка выбора для одного нашего канала: текст + кнопки-галочки. ☑ сразу — у ⭐ (или уже выбранных)."""
    title = next(t for c, t, _, _ in PROFILES if c == ch)
    if not found:
        return f"📡 {title} · ВЫБОР ИСТОЧНИКОВ\n\n⚠️ Папка канала не найдена — источников нет.", None
    mine = [r for r in rows if ch in r.get("for", ())]
    lines = [f"📡 {title} · ВЫБОР ИСТОЧНИКОВ · {generated}",
             f"Папка «{found}»: {len(mine)} каналов. Отметьте нужные ☑ и нажмите «✅ Утверждаю».", ""]
    kb, k = [], 0
    for code, rs in cands.items():
        lines.append(f"{THEME_NAME[code]} — кандидатов: {len(rs)}")
        if not rs:
            lines.append("   ⚠️ чистых каналов нет — добавьте в папку 1–2 канала этой темы")
        for r in rs:
            k += 1
            lines.append(_line(k, r))
            on = (r["id"] in chosen) if chosen is not None else verdict(r)[0] == 0
            kb.append([{"text": f"{'☑' if on else '⬜'} {k}. {r['title'][:28]}",
                        "callback_data": f"sw:t:{ch}:{code}:{r['id']}"}])
        lines.append("")
    if [c for c in MUST if c in cands and not any(is_must(r, c) for r in cands[c])]:
        lines.append("ℹ️ Тезкор Хабарлар / Tezkor Yangiliklar не найдены в ваших папках — добавьте их в «Новости».")
    lines.append("Мой совет: берите ⭐. ⚠️ — можно, кадры проверю позже. 🚫 — лучше не брать.")
    if not kb:
        return "\n".join(lines)[:4096], None
    kb.append([{"text": "✅ Утверждаю", "callback_data": f"sw:ok:{ch}"}])
    return "\n".join(lines)[:4096], {"inline_keyboard": kb}


def load_choice(path: Path = CHOICE) -> dict | None:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def ids_for(choice: dict | None, channel: str) -> list[int]:
    """id источников, ВЫБРАННЫХ владельцем для нашего канала; [] — не выбирал (куратор работает по папке канала)."""
    out = []
    for xs in (((choice or {}).get("channels") or {}).get(channel) or {}).values():
        for x in xs:
            if x["id"] not in out and (x.get("username") or "").lower() not in BLOCK:
                out.append(x["id"])
    return out


def main_empty(choice: dict | None, channel: str) -> bool:
    """Главная рубрика канала не выбрана (напр. жонли ижро) — куратор добавляет и папку канала, как раньше."""
    main = next((rub[0] for c, _, _, rub in PROFILES if c == channel), None)
    return bool(main) and not (((choice or {}).get("channels") or {}).get(channel) or {}).get(main)


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
    titles = list(folders)
    found, plan = {}, []
    news_f = folder_match(titles, NEWS_FOLDERS)
    for ch, _, names, rubrics in PROFILES:
        name = folder_match(titles, names)
        found[ch] = name
        if name:
            plan += [(ch, name, p, False) for p in folders[name]]
        if news_f and "news" in rubrics:
            plan += [(ch, news_f, p, True) for p in folders[news_f]]
    log("папки: " + ", ".join(f"{ch}={found[ch] or 'НЕТ'}" for ch in found) + f" · новости={news_f or 'НЕТ'}"
        + f" (всего у владельца {len(folders)})")
    if not all(found.values()):
        log("  все папки владельца: " + " | ".join(repr(k) for k in folders))
    rows, ents, media, by_id = [], {}, {}, {}
    for ch, fname, p, news_only in plan:
        try:
            ent = await client.get_entity(p)
        except Exception as e:  # noqa: BLE001
            log(f"  {fname}: {type(e).__name__}")
            continue
        title = (getattr(ent, "title", "") or "")
        if ent.id in by_id:                           # канал в нескольких папках — читаем один раз
            r = by_id[ent.id]
            (r["news_for"] if news_only else r["for"]).append(ch)
            continue
        from .sklad import SKLAD
        if (not getattr(ent, "broadcast", False) or (getattr(ent, "username", "") or "").lower() in OWN
                or any(w in title.upper() for w in ("ХАБ", "XАБ", "HUB", "PAPA", "NEXUS", "ПУЛЬТ", "PULT"))
                or _norm(title) in {_norm(k) for k in SKLAD}):
            continue                                  # наши каналы, ХАБы, пульты, группы, 📦 склады — не в отборе
        try:
            posts, mm = await _channel_posts(client, ent, now)
        except Exception as e:  # noqa: BLE001 — один канал не роняет отбор
            log(f"  {title[:30]}: {type(e).__name__}")
            continue
        s = stats(posts, now)
        r = {"id": ent.id, "title": title, "username": getattr(ent, "username", None), "folder": fname,
             "for": [] if news_only else [ch], "news_for": [ch] if news_only else [],
             **s, "why": eligible(s), "texts": [x["text"].replace("\n", " ")[:140] for x in posts if x["text"]][:10],
             "checked": 0, "clean_n": 0, "clean": None, "subscribers": None, "theme_by": {}}
        rows.append(r)
        by_id[ent.id] = r
        ents[ent.id], media[ent.id] = ent, mm
        log(f"  [{len(rows)}] {ch}{'·нов' if news_only else ''} · {title[:34]}: {s['posts']} п., 👁 {s['median_views']}, "
            f"реклама {s['ad_share']} {r['why']}")
        await asyncio.sleep(1)
    # рубрики: Gemini (бесплатно), без него — по ключевым словам. Слабые тоже сортируем — обязательные могут быть среди них.
    cats = await asyncio.to_thread(sortfolders.classify, rows, 10, log)
    rub = {c: r for c, _, _, r in PROFILES}
    for r in rows:
        r["cats"] = cats.get(str(r["id"])) or cats.get(r["id"]) or sortfolders.keyword_cats(r)
        for ch in dict.fromkeys(r["for"] + r["news_for"]):
            allowed = rub[ch] if ch in r["for"] else ("news",)
            t = theme(r["cats"], allowed, ch not in NO_POLITICS)
            nm = (r.get("title") or "").lower() + " " + (r.get("username") or "").lower()
            t = next((c for c, ws in NAME_THEMES.items() if c in allowed and any(w in nm for w in ws)), t)
            if t:
                r["theme_by"][ch] = t
    for r in rows:
        relax_rare(r)
    good = [r for r in rows if not r["why"] or any(is_must(r, c) for c in MUST)]
    cache_f = out_dir / "checks.json"
    try:
        cache = json.loads(cache_f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    fresh = (now - dt.timedelta(days=CHECK_DAYS)).isoformat()
    for r in rows:
        c = cache.get(str(r["id"]))
        if c and c.get("at", "") >= fresh and c.get("checked"):
            r["clean_n"], r["checked"] = c["clean_n"], c["checked"]
            r["clean"] = r["clean_n"] / r["checked"]
        r["score"] = score(r, r["clean"]) if r["clean"] is not None else 0.0
    gemini, done = bool(os.environ.get("GEMINI_API_KEY")), 0
    for r in check_order(good):
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
    cands = build(rows)
    shown = {r["id"]: r for chs in cands.values() for rs in chs.values() for r in rs}
    for r in shown.values():                             # подписчики — только у тех, кого показываем
        try:
            r["subscribers"] = (await client(GetFullChannelRequest(ents[r["id"]]))).full_chat.participants_count
        except Exception:  # noqa: BLE001
            pass
        await asyncio.sleep(1)
    gen = now.astimezone(dt.timezone(dt.timedelta(hours=5))).strftime("%d.%m.%Y %H:%M")
    choice = load_choice()
    cards = []
    for ch, *_ in PROFILES:
        chosen = None
        if choice and (choice.get("channels") or {}).get(ch) is not None:
            chosen = set(ids_for(choice, ch))
        cards.append((ch, *card(ch, cands[ch], rows, found[ch], gen, chosen)))
    keep = ("id", "title", "username", "folder", "for", "news_for", "theme_by", "posts", "per_day", "median_views",
            "ad_share", "media_share", "cyr_share", "why", "checked", "clean_n", "clean", "score", "subscribers")
    data = {"generated": gen, "candidates": {ch: {c: [r["id"] for r in rs] for c, rs in t.items()} for ch, t in cands.items()},
            "rows": [{k: r.get(k) for k in keep} for r in rows], "cards": [c[1] for c in cards]}
    tmp = out_dir / ".latest.json.tmp"
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, out_dir / "latest.json")
    left = [r for r in check_order(good) if r.get("clean") is None]
    pending = out_dir / "pending"
    week = now.astimezone(dt.timezone(dt.timedelta(hours=5))).strftime("%G-%V")
    sent_f = out_dir / "sent_week"
    try:
        sent = sent_f.read_text(encoding="utf-8").strip()
    except OSError:
        sent = ""
    was_pending = pending.exists()
    if left:
        pending.write_text(now.isoformat(), encoding="utf-8")   # ежедневный прогон продолжит проверку кадров
    else:
        pending.unlink(missing_ok=True)
    # карточки — раз в неделю и ещё раз, когда кадры проверены до конца (⚠️ превратились в ⭐/🚫)
    send = sent != week or (was_pending and not left) or os.environ.get("SOURCES_FORCE_SEND") == "1"
    if send:
        sent_f.write_text(week, encoding="utf-8")
    return {"каналов": len(rows), "годных": len(good), "кандидатов": len(shown), "осталось проверить": len(left),
            "cards": cards if send else []}
