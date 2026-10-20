#!/usr/bin/env bash
# Время намаза для PAPA — из GENPLAN 5 (владелец вводил его там; последнее — с 15.10). Копия базы перед записью.
set -Eeuo pipefail
DB=/var/lib/papa-genplan/genplan.sqlite3
cp -a "$DB" "/var/backups/papa/genplan-before-namaz-$(date +%Y%m%d-%H%M).sqlite3" 2>/dev/null || { mkdir -p /var/backups/papa; cp -a "$DB" "/var/backups/papa/genplan-before-namaz-$(date +%Y%m%d-%H%M).sqlite3"; }
cd /opt/papa/modules/genplan
runuser -u papa-genplan -- /opt/papa-venv/razvedka/bin/python - <<'PY'
import datetime as dt, sqlite3
from genplan import namaz, plan
db = sqlite3.connect("/var/lib/papa-genplan/genplan.sqlite3", timeout=30); db.row_factory = sqlite3.Row
namaz.setup(db)
now = dt.datetime.now(plan.TZ)
t = {"bomdod": "05:45", "peshin": "12:45", "asr": "16:00", "shom": "17:45", "xufton": "19:10"}   # GENPLAN 5, действует с 15.10
namaz.save(db, [(dt.date(2026, 10, 15), t)], now)
s = namaz.schedule_for(db, now.date())
print("намаз на сегодня в PAPA:", dict(s) if s else "НЕТ")
PY
echo "== NAMAZ_IMPORT_DONE"
