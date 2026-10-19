#!/usr/bin/env bash
# 🔎 Подробности ошибок за сутки (только чтение): публикации с ошибкой, Тренд-разведка, перезапуски автопилота.
set -uo pipefail
echo "== публикации с ошибкой (24 ч):"
python3 - <<'PY'
import sqlite3
db = sqlite3.connect("file:/var/lib/papa-genplan/genplan.sqlite3?mode=ro", uri=True); db.row_factory = sqlite3.Row
cols = [r[1] for r in db.execute("PRAGMA table_info(publications)")]
q = "SELECT * FROM publications WHERE status NOT IN ('done','queued','planned') AND at >= datetime('now','-1 day') ORDER BY at DESC LIMIT 10"
try:
    for r in db.execute(q):
        d = dict(r); print("  ", {k: (str(v)[:160] if v is not None else None) for k, v in d.items() if k in ("channel","slot_date","slot","status","error","at","material_id","kind")})
except Exception as e:
    print("   колонки:", cols, "ошибка:", e)
PY
echo "== Тренд-разведка (журнал, 30 ч):"
journalctl -u 'papa-razvedka@trend-auto.service' -u 'papa-razvedka@trend-now.service' --since "-30h" --no-pager -o cat | grep -iE "ошибка|error|HTTP" | cut -c1-600 | tail -5
echo "== публикации PaparazziUZ — ошибки в журнале GENPLAN (24 ч):"
journalctl -u papa-genplan --since "-24h" --no-pager -o cat | grep -iE "paparazzi.*(fail|ошиб|error)|(fail|ошиб|error).*paparazzi" | sed -E 's/bot[0-9]+:[A-Za-z0-9_-]+/bot***/g' | cut -c1-400 | tail -8
echo "== автопилот: причины перезапусков (24 ч):"
journalctl -u papa-autopilot --since "-24h" --no-pager -o cat | grep -E "перезапуск|ошибка|Traceback" | cut -c1-200 | sort | uniq -c | sort -rn | head -8
echo "== DIAG_ERRORS_DONE"
