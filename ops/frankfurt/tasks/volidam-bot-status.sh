#!/usr/bin/env bash
# Франкфурт: состояние бота VOLIDAM — служба, бот, менеджеры, заявки (без секретов). Ничего не меняет.
set -euo pipefail
echo "papa-volidam: $(systemctl is-active papa-volidam 2>/dev/null || echo нет)"
journalctl -u papa-volidam -n 5 --no-pager -o cat 2>/dev/null || true
DB=/var/lib/papa-volidam/volidam.sqlite3
[[ -f $DB ]] && python3 - "$DB" <<'PY'
import sqlite3, sys
db = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
print("менеджеров:", db.execute("SELECT count(*) FROM managers").fetchone()[0], "·",
      ", ".join(r[0] for r in db.execute("SELECT name FROM managers")))
print("пользователей:", db.execute("SELECT count(*) FROM users").fetchone()[0])
for st, n in db.execute("SELECT status, count(*) FROM leads GROUP BY status"):
    print(f"заявки {st}: {n}")
PY
echo "== VOLIDAM_STATUS_DONE"
