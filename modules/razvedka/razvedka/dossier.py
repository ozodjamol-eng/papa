"""Досье больших каналов (решение владельца 17.10): почему у них большая аудитория — их режим дня,
сильные и слабые стороны — и сравнение с нашими каналами. Только математика по собранным постам, без ИИ.

Сила поста = просмотры / медиана своего канала (так большой и маленький канал сравнимы).
Советы — только предложения: сетку GENPLAN меняет владелец (✅), агент сам ничего не трогает."""
from __future__ import annotations

import datetime as dt
import re
from collections import Counter, defaultdict
from statistics import median

from .analyze import TZ, load

DAY_FROM, DAY_TO = 7, 22                       # дневное окно для поиска «пустых часов»
TAG = re.compile(r"#[\wЀ-ӿ]+")
MEDIA_UZ = {"text": "текст", "photo": "фото", "video": "видео", "album": "альбом", "poll": "опрос",
            "doc": "файл", "other": "другое"}


def _hm(minutes: float) -> str:
    m = int(round(minutes))
    return f"{m // 60:02d}:{m % 60:02d}"


def _mins(t: dt.datetime) -> int:
    return t.hour * 60 + t.minute


def profile(ps: list[dict], days: int, own: bool = False) -> dict | None:
    """Режим дня, сильное и слабое одного канала."""
    if not own:                                          # реклама — не их контент (у нас подпись @ и ссылки — не реклама)
        ps = [p for p in ps if not p["ad"]]
    if len(ps) < 10:
        return None
    by_day = defaultdict(list)
    for p in ps:
        by_day[p["local"].date()].append(p["local"])
    firsts = [_mins(min(v)) for v in by_day.values()]
    lasts = [_mins(max(v)) for v in by_day.values()]
    gaps = []
    for v in by_day.values():
        v = sorted(v)
        gaps += [(b - a).total_seconds() / 60 for a, b in zip(v, v[1:])]
    hours = Counter(p["local"].hour for p in ps)
    mature = [p for p in ps if p["age_h"] >= 24 and p["views"]]
    med = median([p["views"] for p in mature]) if len(mature) >= 5 else None
    for p in mature:
        p["rel"] = p["views"] / med if med else None

    def strength(key) -> list[tuple]:
        g = defaultdict(list)
        for p in mature:
            k = key(p)
            if k:
                g[k].append(p["rel"])
        return sorted(((k, round(median(v), 2), len(v)) for k, v in g.items() if len(v) >= 3),
                      key=lambda x: x[1], reverse=True)

    first_tag = lambda p: (TAG.findall(p["text"] or "")[:1] or [None])[0]   # noqa: E731
    length = lambda p: "короткий" if (p["text_len"] or 0) < 200 else ("средний" if p["text_len"] < 600 else "длинный")  # noqa: E731
    hour_str = strength(lambda p: p["local"].hour)
    return {
        "per_day": round(len(ps) / max(1, len(by_day)), 1),
        "first": _hm(median(firsts)), "last": _hm(median(lasts)),
        "gap": int(median(gaps)) if gaps else None,
        "busy_hours": [h for h, _ in hours.most_common(3)],
        "empty_hours": [h for h in range(DAY_FROM, DAY_TO) if hours.get(h, 0) <= max(1, days // 7)],
        "best_hours": [(h, s) for h, s, _ in hour_str[:3] if s >= 1.1],
        "weak_hours": [(h, s) for h, s, _ in hour_str[::-1][:3] if s <= 0.8],
        "media": strength(lambda p: p["media"]),
        "tags": strength(first_tag)[:5],
        "length": strength(length),
        "flops": round(100 * sum(1 for p in mature if p["rel"] and p["rel"] < 0.5) / len(mature)) if mature else None,
        "top": sorted((p for p in mature if p.get("rel")), key=lambda p: p["rel"], reverse=True)[:2],
    }


def build(db, days: int = 14, big: int = 6, now: dt.datetime | None = None) -> dict:
    posts, chans = load(db, days, now)
    by_ch = defaultdict(list)
    for p in posts:
        by_ch[p["channel_id"]].append(p)
    rows = []
    for cid, ps in by_ch.items():
        ch = chans.get(cid, {})
        pr = profile(ps, days, own=bool(ch.get("is_own")))
        if pr:
            rows.append({"id": cid, "title": ch.get("title", str(cid)), "username": ch.get("username"),
                         "own": bool(ch.get("is_own")), "subs": ch.get("subscribers") or 0, **pr})
    leaders = sorted((r for r in rows if not r["own"]), key=lambda r: r["subs"], reverse=True)[:big]
    own = [r for r in rows if r["own"]]
    return {"days": days, "leaders": leaders, "own": own,
            "advice": advice(leaders, own),
            "generated": (now or dt.datetime.now(dt.timezone.utc)).astimezone(TZ).strftime("%d.%m.%Y %H:%M")}


def advice(leaders: list[dict], own: list[dict]) -> list[str]:
    """Конкретные предложения по сравнению «лидеры ↔ мы». Только предложения — решает владелец."""
    if not leaders:
        return []
    out = []
    lf = median(int(r["first"][:2]) * 60 + int(r["first"][3:]) for r in leaders)
    lpd = median(r["per_day"] for r in leaders)
    empty = Counter(h for r in leaders for h in r["empty_hours"])
    free = sorted(h for h, n in empty.items() if n >= max(2, len(leaders) // 2))
    best = Counter(h for r in leaders for h, _ in r["best_hours"])
    fmt = defaultdict(list)
    for r in leaders:
        for k, s, _ in r["media"]:
            fmt[k].append(s)
    fmt_best = sorted(((k, round(median(v), 2)) for k, v in fmt.items() if len(v) >= 2), key=lambda x: x[1], reverse=True)
    for o in own:
        name = o["title"]
        of = int(o["first"][:2]) * 60 + int(o["first"][3:])
        if abs(of - lf) >= 30:
            out.append(f"⏰ {name}: первый пост у лидеров ~{_hm(lf)}, у нас ~{o['first']}.")
        if o["per_day"] < lpd * 0.6:
            out.append(f"📈 {name}: у лидеров ~{lpd:g} постов в день, у нас {o['per_day']:g}.")
        if o["gap"] and o["gap"] < 20:
            out.append(f"⏱ {name}: посты идут слишком плотно (медиана {o['gap']} мин) — аудитория не успевает.")
    if free:
        out.append("🕳 Часы, где лидеры почти молчат (свободное окно): " + ", ".join(f"{h:02d}:00" for h in free[:5]) + ".")
    if best:
        out.append("🔥 Часы, где у лидеров посты сильнее обычного: " + ", ".join(f"{h:02d}:00" for h, _ in best.most_common(3)) + ".")
    if fmt_best and fmt_best[0][1] >= 1.1:
        k, s = fmt_best[0]
        out.append(f"🎬 Сильный формат у лидеров: {MEDIA_UZ.get(k, k)} (×{s} к их обычному).")
    return out


def render(d: dict) -> str:
    L = [f"🕵️ ДОСЬЕ БОЛЬШИХ КАНАЛОВ · {d['generated']} · за {d['days']} дн.", ""]
    for r in d["leaders"]:
        L.append(f"📌 {r['title']}" + (f" (@{r['username']})" if r["username"] else "") + (f" · {r['subs']:,} подп.".replace(",", " ") if r["subs"] else ""))
        L.append(f"   Режим: {r['per_day']:g} постов/день · первый ~{r['first']} · последний ~{r['last']}"
                 + (f" · промежуток ~{r['gap']} мин" if r["gap"] is not None else ""))
        if r["best_hours"]:
            L.append("   💪 Сильные часы: " + ", ".join(f"{h:02d}:00 ×{s}" for h, s in r["best_hours"]))
        if r["media"] and r["media"][0][1] >= 1.1:
            k, s, _ = r["media"][0]
            L.append(f"   💪 Сильный формат: {MEDIA_UZ.get(k, k)} ×{s}")
        strong_tags = [f"{t} ×{s}" for t, s, _ in r["tags"][:3] if s >= 1]
        if strong_tags:
            L.append("   🏷 Рубрики-хэштеги сильнее обычного: " + ", ".join(strong_tags))
        if r["length"]:
            L.append(f"   ✍️ Лучше заходит текст: {r['length'][0][0]}")
        weak = []
        if r["weak_hours"]:
            weak.append("слабые часы " + ", ".join(f"{h:02d}:00" for h, _ in r["weak_hours"]))
        if r["flops"] is not None:
            weak.append(f"провалов (<½ обычного) {r['flops']}%")
        if r["empty_hours"]:
            weak.append("молчат в " + ", ".join(f"{h:02d}" for h in r["empty_hours"][:6]))
        if weak:
            L.append("   ⚠️ Слабое: " + "; ".join(weak))
        for p in r["top"]:
            L.append(f"   ⭐ ×{p['rel']:.1f} · {p['local']:%d.%m %H:%M} · " + " ".join((p["text"] or "").split())[:70])
        L.append("")
    if d["own"]:
        L.append("🏠 МЫ")
        for o in d["own"]:
            L.append(f"   {o['title']}: {o['per_day']:g}/день · первый ~{o['first']} · последний ~{o['last']}"
                     + (f" · промежуток ~{o['gap']} мин" if o["gap"] is not None else ""))
        L.append("")
    if d["advice"]:
        L.append("💡 ПРЕДЛОЖЕНИЯ (сетку меняем только после вашего ✅)")
        L += [f"• {a}" for a in d["advice"]]
    return "\n".join(L).strip()
