#!/usr/bin/env bash
# GENPLAN 5: старые просроченные посты (pending, время прошло больше 6 часов назад) → статус 'skipped' (как GENPLAN 5
# сам помечает пропущенные). Ничего не публикует и не удаляет, службу не перезапускает. Перед изменением —
# копия базы; откат: команда в конце вывода. Свежие просрочки (меньше 6 ч) не трогаются — их ещё может выпустить сам GENPLAN.
set -uo pipefail
G=/opt/xojaobod-genplan-v5; DB=$G/data/genplan_v3_production.db
[[ -f $DB ]] || { echo "NO_DB $DB"; exit 1; }
B=/var/backups/papa-archive/genplan5-db-$(date +%F-%H%M%S).sqlite3; install -d -m 700 /var/backups/papa-archive
python3 - "$DB" "$B" <<'PY'
import sqlite3, sys, datetime as dt
src = sqlite3.connect(sys.argv[1], timeout=30); src.execute("PRAGMA busy_timeout=30000")
dst = sqlite3.connect(sys.argv[2]); src.backup(dst); dst.close()
print("копия базы:", sys.argv[2])
cols = {r[1] for r in src.execute("PRAGMA table_info(scheduled_posts)")}
if not {"id", "status", "scheduled_at"} <= cols:
    sys.exit("нет нужных колонок — ничего не меняю")
if not src.execute("SELECT 1 FROM scheduled_posts WHERE status='skipped' LIMIT 1").fetchone():
    sys.exit("в базе нет статуса 'skipped' — не угадываю, ничего не меняю")
edge = (dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) + dt.timedelta(hours=5) - dt.timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%S")
ids = [r[0] for r in src.execute("SELECT id FROM scheduled_posts WHERE status='pending' AND scheduled_at < ?", (edge,))]
if not ids:
    print("старых просрочек нет — ничего не меняю"); sys.exit(0)
with src:
    src.executemany("UPDATE scheduled_posts SET status='skipped' WHERE id=? AND status='pending'", [(i,) for i in ids])
print(f"помечено skipped: {len(ids)} (id: {', '.join(map(str, ids[:30]))})")
PY
rc=$?
[[ $rc == 0 ]] || { echo "!! ошибка — база не менялась (или см. выше)"; exit $rc; }
echo "служба GENPLAN 5: $(systemctl is-active xojaobod-genplan-v3)"
echo "откат (только если нужно): systemctl stop xojaobod-genplan-v3 && cp $B $DB && rm -f $DB-wal $DB-shm && systemctl start xojaobod-genplan-v3"
echo "== OVERDUE_SKIP_DONE"
