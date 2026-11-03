#!/usr/bin/env python3
"""«🕌 Намоз маркази» (03.11.2026): выгрузка времени намаза, которое владелец ввёл в PAPA, для других серверов.

Источник — база PAPA (genplan.sqlite3, таблица namaz_schedule). Выгрузка — /var/lib/papa-namaz/namaz.json (только время,
секретов нет). Её отдаёт шлюз по /api/runner/namaz исполнителю Лондона → бот XOJAOBOD CITY 24 и др. Только чтение базы.
"""
import datetime as dt
import json
import os
import sqlite3
import sys
from pathlib import Path

SRC = Path(os.getenv("PAPA_GENPLAN_DB", "/var/lib/papa-genplan/genplan.sqlite3"))
OUT = Path(os.getenv("PAPA_NAMAZ_JSON", "/var/lib/papa-namaz/namaz.json"))
NAMES = ("bomdod", "peshin", "asr", "shom", "xufton")


def export(src: Path = SRC, out: Path = OUT) -> dict:
    db = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    since = (dt.date.today() - dt.timedelta(days=45)).isoformat()
    rows = db.execute(f"SELECT day, {', '.join(NAMES)}, saved_at FROM namaz_schedule WHERE day>=? ORDER BY day", (since,)).fetchall()
    # плюс последняя запись до окна — чтобы «действует с …» не потерялось
    last = db.execute(f"SELECT day, {', '.join(NAMES)}, saved_at FROM namaz_schedule WHERE day<? ORDER BY day DESC LIMIT 1", (since,)).fetchone()
    sched = [dict(r) for r in ([last] if last else []) + list(rows)]
    data = {"source": "papa-namaz-markazi", "exported_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "schedule": sched}
    out.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(out.parent, 0o755)
    tmp = out.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.chmod(tmp, 0o644)
    tmp.replace(out)
    return data


if __name__ == "__main__":
    d = export()
    last = d["schedule"][-1] if d["schedule"] else None
    print("намоз выгружен:", len(d["schedule"]), "записей; последнее:", last and " ".join(last[n] for n in NAMES), "с", last and last["day"])
    sys.exit(0)
