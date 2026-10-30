"""Анализ собранного: лучшие часы, форматы, лидеры, реклама у конкурентов.
Чистые функции над SQLite — легко проверять тестами."""
from __future__ import annotations

import datetime as dt
import re
from collections import defaultdict
from statistics import median

TZ = dt.timezone(dt.timedelta(hours=5), "Tashkent")  # UTC+5, без перехода на летнее время
WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

# Признаки рекламы (узб. латиница/кириллица и рус.). Срабатывание ≥2 баллов — «вероятная реклама».
AD_STRONG = re.compile(r"#\s?(reklama|реклама|рекл|ad|promo|ҳомий|homiy)\b|\b(reklama|реклама)\b", re.I)
AD_WEAK = re.compile(
    r"\b(chegirma|чегирма|скидк\w*|aksiya|акция|akciya|buyurtma|буюртма|заказ\w*|narx\w*|нарх\w*|цена|"
    r"manzil|манзил|адрес|yetkazib|етказиб|доставк\w*|murojaat|мурожаат|bepul|бепул|бесплатн\w*|"
    r"sotiladi|сотилади|продаж\w*|продаётся|kurs|курс\w*|ro'yxat|рўйхат|запис\w*)\b", re.I)
PHONE = re.compile(r"(\+?998[\s\-]?\d{2}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2})|\b\d{2}[\s\-]\d{3}[\s\-]\d{2}[\s\-]\d{2}\b")
BOT_LINK = re.compile(r"(@\w+bot\b|t\.me/\w+bot\b|instagram\.com|wa\.me)", re.I)


def ad_score(text: str, links: int) -> int:
    t = text or ""
    s = 0
    if AD_STRONG.search(t):
        s += 2
    s += min(2, len(AD_WEAK.findall(t)))
    if PHONE.search(t):
        s += 1
    if BOT_LINK.search(t):
        s += 1
    if links >= 3:
        s += 1
    return s


def is_ad(text: str, links: int) -> bool:
    return ad_score(text, links) >= 2


def load(db, days: int, now: dt.datetime | None = None) -> tuple[list[dict], dict]:
    now = now or dt.datetime.now(dt.timezone.utc)
    since = (now - dt.timedelta(days=days)).isoformat(timespec="seconds")
    chans = {r["id"]: dict(r) for r in db.execute("SELECT * FROM channels")}
    rows = db.execute("SELECT * FROM posts WHERE date_utc>=? ORDER BY channel_id, msg_id", (since,)).fetchall()
    # альбом = один пост: берём максимум просмотров и самый длинный текст
    posts: dict[tuple, dict] = {}
    for r in rows:
        key = (r["channel_id"], r["grp"] if r["grp"] else -r["msg_id"])
        cur = posts.get(key)
        if cur is None:
            posts[key] = dict(r)
            if r["grp"]:
                posts[key]["media"] = "album"
        else:
            cur["views"] = max(cur["views"] or 0, r["views"] or 0) or None
            cur["reactions"] = max(cur["reactions"] or 0, r["reactions"] or 0)
            if (r["text_len"] or 0) > (cur["text_len"] or 0):
                cur["text"], cur["text_len"], cur["links"] = r["text"], r["text_len"], r["links"]
    out = []
    for p in posts.values():
        d = dt.datetime.fromisoformat(p["date_utc"])
        p["local"] = d.astimezone(TZ)
        p["age_h"] = (now - d).total_seconds() / 3600
        p["ad"] = is_ad(p["text"] or "", p["links"] or 0)
        out.append(p)
    return out, chans


def analyze(db, days: int = 7, now: dt.datetime | None = None) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    posts, chans = load(db, days, now)
    by_ch = defaultdict(list)
    for p in posts:
        by_ch[p["channel_id"]].append(p)

    # «созревшие» посты (≥24 ч) — для сравнения просмотров
    channel_stats, med_views = [], {}
    for cid, ps in by_ch.items():
        mature = [p["views"] for p in ps if p["age_h"] >= 24 and p["views"]]
        med = median(mature) if mature else None
        med_views[cid] = med
        ch = chans.get(cid, {})
        subs = ch.get("subscribers")
        channel_stats.append({
            "id": cid, "title": ch.get("title", str(cid)), "username": ch.get("username"),
            "folder": ch.get("folder", "?"), "is_own": ch.get("is_own", 0), "subscribers": subs,
            "posts": len(ps), "per_day": round(len(ps) / days, 1),
            "median_views": int(med) if med else None,
            # 30.10: группа (напр. Xo'jaobod City 24) — Telegram не даёт просмотров; меряем реакции на пост
            "no_views": not any(p["views"] for p in ps),
            "median_reactions": (round(median([p["reactions"] or 0 for p in ps if p["age_h"] >= 24]), 1)
                                 if any(p["age_h"] >= 24 for p in ps) else None),
            "err": round(100 * med / subs, 1) if med and subs else None,
            "ads": sum(1 for p in ps if p["ad"]),
            "ads_per_day": round(sum(1 for p in ps if p["ad"]) / days, 1),
        })
    channel_stats.sort(key=lambda c: c["median_views"] or 0, reverse=True)

    # относительная сила поста: просмотры / медиана своего канала (убирает разницу размеров)
    rel_posts = []
    for p in posts:
        med = med_views.get(p["channel_id"])
        if med and p["views"] and p["age_h"] >= 24 and len(by_ch[p["channel_id"]]) >= 5:
            p["rel"] = p["views"] / med
            rel_posts.append(p)

    def bucket(key_fn, keys, min_n=5):
        vol, rel = defaultdict(int), defaultdict(list)
        for p in posts:
            vol[key_fn(p)] += 1
        for p in rel_posts:
            rel[key_fn(p)].append(p["rel"])
        res = []
        for k in keys:
            r = rel.get(k, [])
            res.append({"key": k, "posts": vol.get(k, 0),
                        "strength": round(median(r), 2) if len(r) >= min_n else None})
        return res

    hours = bucket(lambda p: p["local"].hour, range(24))
    weekdays = bucket(lambda p: p["local"].weekday(), range(7))
    media = bucket(lambda p: p["media"], ["text", "photo", "video", "album", "poll", "doc", "other"])
    ad_hours = defaultdict(int)
    for p in posts:
        if p["ad"]:
            ad_hours[p["local"].hour] += 1

    top = sorted(rel_posts, key=lambda p: p["rel"], reverse=True)[:10]
    top_posts = [{"title": chans.get(p["channel_id"], {}).get("title", "?"), "rel": round(p["rel"], 1),
                  "views": p["views"], "media": p["media"], "when": p["local"].strftime("%d.%m %H:%M"),
                  "snippet": " ".join((p["text"] or "").split())[:90]} for p in top]
    from . import daymap   # 30.10: карта дня конкурентов по папкам-темам
    return {
        "own_week": own_week(db, now),
        "daymap": daymap.build(posts, chans),
        "days": days, "generated": now.astimezone(TZ).strftime("%d.%m.%Y %H:%M"),
        "channels": channel_stats, "posts_total": len(posts),
        "hours": hours, "weekdays": weekdays, "media": media,
        "ad_hours": dict(sorted(ad_hours.items())), "top_posts": top_posts,
    }


OWN_WEEK_DAYS = 28   # 30.10 владелец: тематические дни — только по цифрам НАШИХ каналов, 4 недели


def own_week(db, now: dt.datetime | None = None, days: int = OWN_WEEK_DAYS) -> list[dict]:
    """Сила дней недели у наших каналов: пост / медиана своего канала. Канал — просмотры; группа — реакции."""
    now = now or dt.datetime.now(dt.timezone.utc)
    posts, chans = load(db, days, now)
    out = []
    for cid, ch in chans.items():
        if not ch.get("is_own"):
            continue
        ps = [p for p in posts if p["channel_id"] == cid and p["age_h"] >= 24 and not p["ad"]]
        by_views = any(p["views"] for p in ps)
        val = (lambda p: p["views"] or 0) if by_views else (lambda p: p["reactions"] or 0)
        vals = [val(p) for p in ps if val(p)]
        if len(vals) < 7:
            continue
        med = median(vals)
        wd: dict[int, list[float]] = defaultdict(list)
        for p in ps:
            wd[p["local"].weekday()].append(val(p) / med)
        out.append({"title": ch.get("title", str(cid)), "metric": "просмотры" if by_views else "реакции",
                    "weeks": round(days / 7), "posts": len(ps),
                    "days": [{"key": k, "posts": len(wd.get(k, [])),
                              "strength": round(median(wd[k]), 2) if len(wd.get(k, [])) >= 3 else None}
                             for k in range(7)]})
    return out
