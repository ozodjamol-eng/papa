#!/usr/bin/env bash
# Только чтение: утренние посты сегодня — с видео или текстом, ошибка, источник; журнал утра. Ничего не меняет.
set -uo pipefail
DB=/var/lib/papa-genplan/genplan.sqlite3
sudo -u papa-genplan /opt/papa-venv/razvedka/bin/python - "$DB" <<'PY'
import sqlite3, sys
db = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
for r in db.execute("SELECT channel, key, substr(at,1,16), status, prepared, tries, coalesce(source,''), coalesce(hub_msg,''), "
                    "coalesce(error,''), substr(coalesce(text,''),1,60) FROM fixed_posts "
                    "WHERE substr(at,1,10) IN (date('now','+5 hours'), date('now','+5 hours','-1 day')) ORDER BY at"):
    print(" | ".join(str(x) for x in r))
try:
    print("пул:", dict(db.execute("SELECT status, count(*) FROM morning_pool GROUP BY status").fetchall()))
except sqlite3.OperationalError as e:
    print("пул:", e)
PY
echo "== журнал утра"
journalctl -u papa-genplan -u papa-fabrika --since "-14h" --no-pager -o cat | grep -iE "morning|утр|хайрли|видео|pool|vision" | tail -40
echo "== MORNING_WHY_DONE"
