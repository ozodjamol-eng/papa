#!/usr/bin/env bash
# 📅 План дня КАТТА ДАВРА и Хўжаобода (только чтение: база открывается read-only) — для проверки часовой сетки ИИ.
set -Eeuo pipefail
cd /opt/papa/modules/genplan
DB="${PAPA_GENPLAN_DB:-/var/lib/papa-genplan/genplan.sqlite3}" /opt/papa-venv/razvedka/bin/python - <<'PY'
import datetime as dt, os, sqlite3, tomllib
from genplan import plan, smart, store
cfg = tomllib.loads(open("config.toml", encoding="utf-8").read())
db = sqlite3.connect(f"file:{os.environ['DB']}?mode=ro", uri=True)
db.row_factory = sqlite3.Row
now = dt.datetime.now(plan.TZ)
for c in ("davra", "xojaobod"):
    ch = cfg["channels"][c]
    print(f"===== {ch['title']} · часовая сетка: {'ДА ' + str(smart.hourly(ch)) if smart.hourly(ch) else 'НЕТ'}")
    print(smart.day_view(db, cfg, c, now))
    print("-- в очереди (все дни):")
    for m in store.scheduled(db, c):
        t = dt.datetime.fromisoformat(m["scheduled_at"]).astimezone(plan.TZ)
        kind = "🆘" if m["urgent"] else ("📣" if smart.is_ad_rubric(m["rubric"]) else "⏱")
        print(f"  {kind} {t:%d.%m %H:%M} {'🔒' if m['locked'] else '  '} {m['rubric'] or '—'}")
    print()
print("== PLAN_TODAY_DONE")
PY
