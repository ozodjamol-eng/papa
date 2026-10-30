"""Текстовый отчёт Разведки (для Telegram «Избранное», консоли и Pult)."""
from __future__ import annotations

from .analyze import WEEKDAYS

MEDIA_RU = {"text": "текст", "photo": "фото", "video": "видео", "album": "альбом", "poll": "опрос",
            "doc": "файл", "other": "другое"}


def _n(x) -> str:
    if x is None:
        return "—"
    return f"{x:,}".replace(",", " ") if isinstance(x, int) else str(x)


def render(a: dict) -> str:
    L = [f"PAPA · РАЗВЕДКА · {a['generated']} (Ташкент)",
         f"Период: {a['days']} дн. · каналов: {len(a['channels'])} · постов: {a['posts_total']}", ""]

    good = [h for h in a["hours"] if h["strength"] is not None]
    if good:
        best = sorted(good, key=lambda h: h["strength"], reverse=True)[:5]
        L.append("⏰ ЛУЧШИЕ ЧАСЫ (сила поста = просмотры / обычные для канала):")
        L += [f"  {h['key']:02d}:00 — ×{h['strength']}  ({h['posts']} постов)" for h in best]
        busy = sorted(a["hours"], key=lambda h: h["posts"], reverse=True)[:3]
        L.append("  Самые загруженные часы у конкурентов: " + ", ".join(f"{h['key']:02d}:00" for h in busy))
        L.append("")

    wd = [w for w in a["weekdays"] if w["strength"] is not None]
    if wd:
        L.append("📅 ДНИ НЕДЕЛИ: " + " · ".join(f"{WEEKDAYS[w['key']]} ×{w['strength']}" for w in wd))
        L.append("")

    md = [m for m in a["media"] if m["strength"] is not None]
    if md:
        L.append("🎞 ФОРМАТЫ: " + " · ".join(f"{MEDIA_RU.get(m['key'], m['key'])} ×{m['strength']} ({m['posts']})"
                                           for m in sorted(md, key=lambda m: m["strength"], reverse=True)))
        L.append("")

    L.append("🏆 ЛИДЕРЫ ПО ПРОСМОТРАМ (медиана поста):")
    for c in [c for c in a["channels"] if not c["is_own"]][:12]:
        L.append(f"  {c['title'][:28]} — {_n(c['median_views'])} просм., ERR {_n(c['err'])}%, "
                 f"{c['per_day']} пост/день, реклама {c['ads_per_day']}/день")
    L.append("")

    own = [c for c in a["channels"] if c["is_own"]]
    if own:
        L.append("🏠 СВОИ КАНАЛЫ:")
        for c in own:
            if c.get("no_views"):   # группа: просмотров в Telegram нет — показываем реакции
                L.append(f"  {c['title'][:28]} — группа: {_n(c.get('median_reactions'))} реакц./пост, "
                         f"{c['per_day']} пост/день, участников {_n(c['subscribers'])}")
                continue
            L.append(f"  {c['title'][:28]} — {_n(c['median_views'])} просм., ERR {_n(c['err'])}%, "
                     f"{c['per_day']} пост/день, подписчиков {_n(c['subscribers'])}")
        L.append("")

    ads = sorted(a["channels"], key=lambda c: c["ads"], reverse=True)
    ads = [c for c in ads if c["ads"] and not c["is_own"]][:8]
    if ads:
        L.append("💰 РЕКЛАМА У КОНКУРЕНТОВ (вероятная, по признакам):")
        L += [f"  {c['title'][:28]} — {c['ads']} за период ({c['ads_per_day']}/день)" for c in ads]
        if a["ad_hours"]:
            top_h = sorted(a["ad_hours"].items(), key=lambda kv: kv[1], reverse=True)[:4]
            L.append("  Чаще всего ставят рекламу в: " + ", ".join(f"{h:02d}:00" for h, _ in top_h))
        L.append("")

    if a["top_posts"]:
        L.append("🔥 САМЫЕ СИЛЬНЫЕ ПОСТЫ (во сколько раз выше обычного):")
        for p in a["top_posts"]:
            L.append(f"  ×{p['rel']} · {p['title'][:20]} · {p['when']} · {MEDIA_RU.get(p['media'], p['media'])} · "
                     f"{p['snippet'] or '(без текста)'}")
    L.append("")
    if a.get("daymap"):
        from .daymap import render as daymap_render
        L += daymap_render(a["daymap"])
    L.append("Сила ×1.0 = обычный пост канала. Посты моложе суток в сравнение не входят.")
    return "\n".join(L)
