"""План дня: сетка слотов + материалы из хаба + рекламные заказы → что и когда выходит.

Правила (из Генплана Xo'jaobod City 24):
- anchor (намоз, дуо) выходит каждый день, всегда;
- рекламное окно: если есть оплаченная реклама — она; если нет — окно отдаётся контенту, НЕ самопиару;
- в воскресенье рекламных окон не больше ad_days_limit;
- content: материал нужной рубрики (старые первыми), иначе — запасные рубрики, иначе ⚠️ «нет материала»;
- один материал — только в один слот;
- срочный пост выходит сразу, вне сетки, и не сдвигает остальные.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

TZ = dt.timezone(dt.timedelta(hours=5))  # Ташкент

READY, QUEUED, EMPTY, AD, AUTO, DONE, MISSED, FREE = "ready", "queued", "empty", "ad", "auto", "done", "missed", "free"
ICON = {READY: "✅", QUEUED: "⏳", EMPTY: "⚠️", AD: "💰", AUTO: "🔁", DONE: "✔️", MISSED: "❌", FREE: "▫️"}


@dataclass
class Entry:
    at: dt.datetime
    kind: str                      # anchor / content / ad / music
    rubric: str | None
    status: str
    material_id: int | None = None
    ad_id: int | None = None
    note: str = ""


@dataclass
class Material:
    id: int
    rubric: str
    created_at: dt.datetime
    channel: str | None = None     # None — подходит любому каналу
    text: str = ""
    media: list = field(default_factory=list)


def slot_time(day: dt.date, hhmm: str) -> dt.datetime:
    h, m = map(int, hhmm.split(":"))
    return dt.datetime(day.year, day.month, day.day, h, m, tzinfo=TZ)


def day_slots(ch_cfg: dict, day: dt.date) -> list[dict]:
    wd = str(day.isoweekday())
    out = [s for s in ch_cfg["slots"] if wd in [str(d) for d in s.get("days", range(1, 8))]]
    ad_limit = (ch_cfg.get("ad_days_limit") or {}).get(wd)
    if ad_limit is not None:
        n = 0
        kept = []
        for s in out:
            if s["kind"] == "ad":
                n += 1
                if n > int(ad_limit):
                    continue
            kept.append(s)
        out = kept
    return sorted(out, key=lambda s: s["t"])


def build(ch_name: str, ch_cfg: dict, day: dt.date, materials: list[Material], ads: dict,
          published: dict | None = None, now: dt.datetime | None = None) -> list[Entry]:
    """ads: {"HH:MM": ad_id} — оплаченная реклама на этот день; published: {"HH:MM": status} — уже вышло/не вышло."""
    published = published or {}
    pool = sorted([m for m in materials if m.channel in (None, ch_name)], key=lambda m: m.created_at)
    used: set[int] = set()

    def take(rubrics: list[str]) -> Material | None:
        for r in rubrics:
            for m in pool:
                if m.id not in used and m.rubric == r:
                    used.add(m.id)
                    return m
        return None

    slots = day_slots(ch_cfg, day)
    entries: dict[int, Entry] = {}
    free_ads: list[int] = []
    # 1-й проход: якоря, проданная реклама, рубрики (рубрики важнее свободных окон)
    for i, s in enumerate(slots):
        at = slot_time(day, s["t"])
        kind, rubric = s["kind"], s.get("rubric")
        if s["t"] in published:
            entries[i] = Entry(at, kind, rubric, published[s["t"]])
        elif kind == "anchor":
            entries[i] = Entry(at, kind, rubric, AUTO)
        elif kind == "ad":
            if s["t"] in ads:
                entries[i] = Entry(at, kind, None, AD, ad_id=ads[s["t"]])
            else:
                free_ads.append(i)
        else:
            m = take([rubric] + list(s.get("fallback", [])))
            st = QUEUED if m else EMPTY
            if m and now and at - now <= dt.timedelta(minutes=30):
                st = READY
            entries[i] = Entry(at, kind, m.rubric if m else rubric, st, material_id=m.id if m else None,
                               note="" if not m or m.rubric == rubric else f"вместо «{rubric}»")
    # 2-й проход: свободные рекламные окна → лишний материал (не самопиар); нет лишнего — окно пустует
    for i in free_ads:
        at = slot_time(day, slots[i]["t"])
        rest = [m for m in pool if m.id not in used]
        if rest:
            used.add(rest[0].id)
            entries[i] = Entry(at, "content", rest[0].rubric, QUEUED, material_id=rest[0].id, note="окно рекламы свободно")
        else:
            entries[i] = Entry(at, "ad", None, FREE, note="окно рекламы свободно")
    return [entries[i] for i in range(len(slots))]


def due(plan: list[Entry], now: dt.datetime, grace_minutes: int = 20) -> list[Entry]:
    """Что пора публиковать сейчас (время наступило, но не позже grace)."""
    return [e for e in plan if e.status in (QUEUED, READY, AUTO, AD)
            and e.at <= now <= e.at + dt.timedelta(minutes=grace_minutes)]


def render(title: str, plan: list[Entry]) -> str:
    lines = [f"📅 План на сегодня — {title}"]
    for e in plan:
        what = "Реклама" if e.kind == "ad" else (e.rubric or "—")
        extra = f" ({e.note})" if e.note else ""
        if e.status == FREE:
            what, extra = "Реклама — свободно", ""
        lines.append(f"{ICON.get(e.status, '•')} {e.at:%H:%M}  {what}{extra}")
    empty = sum(1 for e in plan if e.status == EMPTY)
    if empty:
        lines.append(f"\n⚠️ Нет материала для {empty} слот(ов) — перешлите посты в PAPA HUB.")
    return "\n".join(lines)
