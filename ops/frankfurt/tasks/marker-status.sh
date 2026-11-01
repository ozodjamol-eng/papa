#!/usr/bin/env bash
# 🏷 Маркировщик — состояние (только чтение): полки, сколько помечено/неудач, последние строки журнала.
set -uo pipefail
python3 - <<'PY'
import sqlite3
db = sqlite3.connect("file:/var/lib/papa-genplan/genplan.sqlite3?mode=ro", uri=True)
for k, v in db.execute("SELECT k, v FROM kv WHERE k LIKE 'marker_shelf_%'"):
    print("полка", k[13:], v)
print("помечено:", db.execute("SELECT count(*) FROM kv WHERE k LIKE 'marked_%' AND v='1'").fetchone()[0],
      "· опоздали:", db.execute("SELECT count(*) FROM kv WHERE k LIKE 'marked_%' AND v='late'").fetchone()[0],
      "· неудач:", db.execute("SELECT count(*) FROM kv WHERE k LIKE 'markfail_%'").fetchone()[0])
PY
journalctl -u papa-genplan --since "-2 hours" -o cat --no-pager | grep -E "🏷|morning: метка" | tail -25
echo "== MARKER_STATUS_DONE"
