"""🧠 Штаб: заказ на материал (30.10, схема «Штаб → отделы» утверждена владельцем).

GENPLAN знает сетку «час = рубрика» и запас — пишет, какие часы сегодня ещё пустые и что в них нужно.
Куратор Разведки читает этот заказ и приносит именно эти рубрики (свежее из выбранных источников),
а если до пустого часа мало времени — берёт из архива-склада этой рубрики (якорь: цикл не прерывается).
Файл: /var/lib/papa-sources-choice/needs.json (пишет genplan, читает Разведка)."""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

from . import plan, smart, store

NEEDS = Path(os.environ.get("SOURCES_NEEDS", "/var/lib/papa-sources-choice/needs.json"))
EVERY = dt.timedelta(minutes=5)
_LAST: dict = {}


def build(db, cfg: dict, now: dt.datetime) -> dict:
    out = {}
    for channel, ch in cfg["channels"].items():
        if not ch.get("hour_rubrics") or not smart.hourly(ch):
            continue
        inv: dict[str, list[str]] = {}
        for code, rub in (ch.get("source_rubrics") or {}).items():
            inv.setdefault(rub, []).append(code)
        stash: dict[str, list[str]] = {}
        for name, rub in (ch.get("sklad") or {}).items():
            for r in ([rub] if isinstance(rub, str) else rub):
                stash.setdefault(r, []).append(name)
        stock: dict[str, int] = {}
        for m in store.stock(db, channel):
            stock[m["rubric"]] = stock.get(m["rubric"], 0) + 1
        left = dict(stock)
        empty = []
        for t in smart.free_hours(db, ch, channel, None, now, now.date()):
            want = smart.hour_wants(ch, t) or []
            have = next((r for r in want if left.get(r, 0) > 0), None)
            if have:                                   # запас этой рубрики закроет час — не заказываем
                left[have] -= 1
                continue
            empty.append({"h": f"{t.astimezone(plan.TZ):%H}", "at": t.isoformat(), "want": want,
                          "codes": [c for r in want for c in inv.get(r, [])],
                          "stash": [s for r in want for s in stash.get(r, [])]})
        out[channel] = {"empty": empty, "stock": stock}
    return {"at": now.isoformat(), "channels": out}


def write(db, cfg: dict, now: dt.datetime, path: Path | None = None, force: bool = False) -> bool:
    p = path or NEEDS
    if not force and _LAST.get(str(p)) and now - _LAST[str(p)] < EVERY:
        return False
    if not p.parent.is_dir():
        return False
    data = build(db, cfg, now)
    tmp = p.with_name("." + p.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.chmod(tmp, 0o640)
    os.replace(tmp, p)
    _LAST[str(p)] = now
    return True
