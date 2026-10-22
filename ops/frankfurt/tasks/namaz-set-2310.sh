#!/usr/bin/env bash
# 22.10 владелец: новое время намаза с 23.10.2026 (Жума). Копия базы перед записью. Вышедшие посты не трогаем.
set -Eeuo pipefail
DB=/var/lib/papa-genplan/genplan.sqlite3
mkdir -p /var/backups/papa
cp -a "$DB" "/var/backups/papa/genplan-before-namaz-$(date +%Y%m%d-%H%M).sqlite3"
cd /opt/papa/modules/genplan
runuser -u papa-genplan -- /opt/papa-venv/razvedka/bin/python - <<'PY'
import datetime as dt, sqlite3, tomllib
from pathlib import Path
from genplan import namaz, plan
db = sqlite3.connect("/var/lib/papa-genplan/genplan.sqlite3", timeout=30); db.row_factory = sqlite3.Row
namaz.setup(db)
now = dt.datetime.now(plan.TZ)
day = dt.date(2026, 10, 23)
old = namaz.schedule_for(db, day)
print("было на 23.10:", {n: old[n] for n in namaz.NAMES} if old else "НЕТ")
t = {"bomdod": "05:55", "peshin": "12:45", "asr": "15:50", "shom": "17:35", "xufton": "19:00"}
namaz.save(db, [(day, t)], now)
cfg = tomllib.loads(Path("config.toml").read_text(encoding="utf-8"))
for c in cfg["channels"]:
    namaz.ensure_day(db, cfg, c, day, now)
s = namaz.schedule_for(db, day)
print("стало с 23.10:", {n: s[n] for n in namaz.NAMES})
print("сегодня (22.10) осталось по:", {n: namaz.schedule_for(db, now.date())[n] for n in namaz.NAMES})
for r in db.execute("SELECT key, at, status FROM namaz_posts WHERE channel='xojaobod' AND day=? ORDER BY at", (day.isoformat(),)):
    print(" ", r["at"][11:16], r["key"], r["status"])
PY
echo "== NAMAZ_SET_DONE"
