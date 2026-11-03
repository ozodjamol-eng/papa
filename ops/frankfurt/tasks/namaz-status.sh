#!/usr/bin/env bash
# Только чтение (03.11, «🕌 Намоз маркази», шаг 1): какое время намаза знает PAPA, когда владелец его последний раз вводил.
set -uo pipefail
python3 - <<'PY'
import sqlite3
db = sqlite3.connect("file:/var/lib/papa-genplan/genplan.sqlite3?mode=ro", uri=True); db.row_factory = sqlite3.Row
for r in db.execute("SELECT day, bomdod, peshin, asr, shom, xufton, saved_at, (photo IS NOT NULL) ph FROM namaz_schedule ORDER BY day DESC LIMIT 6"):
    print(f"с {r['day']}: {r['bomdod']} {r['peshin']} {r['asr']} {r['shom']} {r['xufton']} · введено {r['saved_at'][:16]} · баннер: {'да' if r['ph'] else 'нет'}")
print("постов намаза за 7 дней:", db.execute("SELECT channel, status, count(*) FROM namaz_posts WHERE day>=date('now','-7 day') GROUP BY channel, status").fetchall())
PY
echo "== NAMAZ_STATUS_DONE"
