#!/usr/bin/env bash
# 🌅 Быстро применить новый код утреннего блока без повторной охоты: тесты → перезапуск → утро на завтра пересобирается.
set -euo pipefail
PY=/opt/papa-venv/razvedka/bin/python
DB=/var/lib/papa-genplan/genplan.sqlite3
cp -a "$DB" "$DB.bak-refresh-$(date +%F-%H%M)"
( cd /opt/papa/modules/genplan && PAPA_GENPLAN_STATE=$(mktemp -d) POOL_VISION_GAP=0 $PY -m unittest discover -q -s tests 2>&1 | tail -1 )
systemctl restart papa-genplan; systemctl stop papa-fabrika
sudo -u papa-genplan $PY - "$DB" <<'PY'
import sqlite3, sys
db = sqlite3.connect(sys.argv[1])
n = db.execute("UPDATE fixed_posts SET prepared=0, redo=1, tries=0, next_try=NULL, hub_msg=NULL, preview_sent=0, approved=0 "
               "WHERE status='pending' AND day=date('now','+5 hours','+1 day')").rowcount
db.execute("DELETE FROM kv WHERE k='pool_vision_pause'")      # снять паузу проверки кадров (Gemini был перегружен)
db.commit(); print(f"постов на пересборку: {n}")
PY
systemctl start papa-fabrika; sleep 180
sudo -u papa-genplan $PY - "$DB" <<'PY'
import sqlite3, sys
db = sqlite3.connect(sys.argv[1])
try:
    print("проверка кадров:", dict(db.execute("SELECT status, count(*) FROM morning_pool GROUP BY status").fetchall()))
    print("годные по дням:", dict(db.execute("SELECT coalesce(weekday,'общие'), count(*) FROM morning_pool WHERE status='ok' GROUP BY 1").fetchall()))
except sqlite3.OperationalError:
    pass
for r in db.execute("SELECT channel, key, substr(at,12,5), prepared, coalesce(source,'') FROM fixed_posts "
                    "WHERE day=date('now','+5 hours','+1 day') ORDER BY at, channel"):
    print("  ", *r)
PY
echo "== MORNING_REFRESH_DONE"
