#!/usr/bin/env bash
# Только чтение: что GENPLAN 5 ещё собирается опубликовать сегодня (мешает остановке genplan5-stop).
set -Eeuo pipefail
DB=/opt/xojaobod-genplan-v5/data/genplan_v3_production.db
python3 - "$DB" <<'PY'
import sqlite3, sys, datetime as d
db = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
t = (d.datetime.now(d.timezone.utc) + d.timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M:%S")
for r in db.execute("SELECT id, scheduled_at, coalesce(source,''), coalesce(rubric,''), substr(replace(coalesce(caption,''),char(10),' '),1,90) "
                    "FROM scheduled_posts WHERE status='pending' ORDER BY scheduled_at"):
    mark = "⚠️ сегодня, мешает" if r[1][:10] == t[:10] and r[1] >= t and r[2] not in ("prayer", "campaign", "fixed") else ""
    print(" | ".join(str(x) for x in r), mark)
PY
echo "== GENPLAN5_TODAY_DONE"
