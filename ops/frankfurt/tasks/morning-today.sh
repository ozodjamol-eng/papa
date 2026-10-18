#!/usr/bin/env bash
# 🌅 Только чтение: что сегодня и завтра в утреннем блоке по каждому каналу (вышло / пропущено и почему),
# пул NEXUS MORNING POOL и ошибки GENPLAN/Fabrika за утро. Ничего не публикует и не перезапускает.
set -uo pipefail
PY=/opt/papa-venv/razvedka/bin/python
DB=/var/lib/papa-genplan/genplan.sqlite3
echo "genplan: $(systemctl is-active papa-genplan) · fabrika: $(systemctl is-active papa-fabrika)"
sudo -u papa-genplan $PY - "$DB" <<'PY'
import sqlite3, sys
db = sqlite3.connect(sys.argv[1])
db.row_factory = sqlite3.Row
cols = [c[1] for c in db.execute("PRAGMA table_info(fixed_posts)")]
print("== утро сегодня и завтра (канал, пост, время, статус, готов, одобрен, ошибка):")
for r in db.execute("SELECT * FROM fixed_posts WHERE day>=date('now','+5 hours') AND day<=date('now','+5 hours','+1 day') "
                    "ORDER BY day, at, channel"):
    d = dict(r)
    print("  ", d["day"], d["channel"], d["key"], d["at"][11:16], d["status"],
          "prep=%s" % d.get("prepared"), "ok=%s" % d.get("approved"), d.get("error") or "")
try:
    print("== пул:", dict(db.execute("SELECT status, count(*) FROM morning_pool GROUP BY status").fetchall()))
except sqlite3.OperationalError as e:
    print("== пул: нет таблицы", e)
PY
echo "== журнал GENPLAN с 04:00 (утро, ошибки):"
journalctl -u papa-genplan --since "$(date -d '04:00 today' '+%F %T' 2>/dev/null || echo today)" --no-pager -o cat \
  | grep -iE "morning|утр|greeting|paparazzi|ozodjamoll|error|ошиб|traceback|skip|пропуск" | tail -40
echo "== журнал Fabrika (последние 15):"
journalctl -u papa-fabrika -n 15 --no-pager -o cat
echo "== MORNING_TODAY_DONE"
