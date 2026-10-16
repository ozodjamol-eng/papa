#!/usr/bin/env bash
# PaparazziUZ → рабочий режим (mode="live" в config.toml). Тестовые материалы из очереди PaparazziUZ, добавленные ДО перехода,
# снимаются (status=rejected), чтобы тесты не вышли в настоящий канал. Откат: mode="shadow" и genplan-restart.
set -euo pipefail
DB=/var/lib/papa-genplan/genplan.sqlite3
cp -a "$DB" "$DB.bak-$(date +%F-%H%M)"
echo "Снимаю тестовые материалы из очереди PaparazziUZ:"
/opt/papa-venv/razvedka/bin/python - "$DB" <<'PY'
import sqlite3, sys
db = sqlite3.connect(sys.argv[1])
rows = db.execute("SELECT id, rubric, substr(replace(text, char(10), ' '), 1, 50) FROM materials "
                  "WHERE channel='paparazzi' AND status IN ('queued','draft')").fetchall()
for r in rows:
    print("  -", *r)
db.execute("UPDATE materials SET status='rejected' WHERE channel='paparazzi' AND status IN ('queued','draft')")
db.commit()
print(f"  снято: {len(rows)}")
PY
( cd /opt/papa/modules/genplan && PAPA_GENPLAN_STATE=$(mktemp -d) POOL_VISION_GAP=0 /opt/papa-venv/razvedka/bin/python -m unittest discover -q -s tests 2>&1 | tail -1 )
grep -n 'mode = "live"' /opt/papa/modules/genplan/config.toml
systemctl restart papa-genplan papa-fabrika; sleep 5
systemctl is-active papa-genplan
( cd /opt/papa/modules/genplan && sudo -u papa-genplan env PAPA_GENPLAN_DB=$DB /opt/papa-venv/razvedka/bin/python -m genplan plan 2>/dev/null | head -3 ) || true
echo "== PAPARAZZI_LIVE_DONE"
