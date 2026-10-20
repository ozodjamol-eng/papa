#!/usr/bin/env bash
# Решение владельца 20.10 07:23: реклама «УТИН» (кампания 12) — в 17:30 каждый день; ИЖАРА остаётся 18:30.
# Сегодняшний пропущенный пост УТИН — вернуть в очередь на 17:30. Перед изменением — копия базы.
# Откат: копия базы /var/backups/genplan5-before-utin-*.db (остановить GENPLAN 5, вернуть файл, запустить).
set -Eeuo pipefail
G=/opt/xojaobod-genplan-v5; DB=$G/data/genplan_v3_production.db
B=/var/backups/genplan5-before-utin-$(date +%Y%m%d-%H%M).db
mkdir -p /var/backups
sqlite3 "$DB" ".backup '$B'" 2>/dev/null || python3 -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d)" "$DB" "$B"
echo "копия базы: $B"
python3 - "$DB" <<'PY'
import sqlite3, sys, datetime as dt
db = sqlite3.connect(sys.argv[1], timeout=30)
today = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=5)).date().isoformat()
c = db.execute("SELECT id, name, slot_time FROM campaigns WHERE id=12").fetchone()
assert c and "ТИН" in c[1].upper(), f"кампания 12 не УТИН: {c}"
db.execute("UPDATE campaigns SET slot_time='17:30' WHERE id=12")
n = db.execute("UPDATE scheduled_posts SET status='pending', scheduled_at=?, original_scheduled_at=?, last_error=NULL, claimed_at=NULL "
               "WHERE slot_key=? AND status IN ('skipped','failed','pending')",
               (f"{today}T17:30:00", f"{today}T17:30:00", f"campaign_12_{today}")).rowcount
db.commit()
print(f"УТИН: время 17:30; сегодняшний пост возвращён в очередь: {n}")
for r in db.execute("SELECT id, slot_key, scheduled_at, status FROM scheduled_posts WHERE rubric='ad' AND substr(scheduled_at,1,10)=?", (today,)):
    print("  ", r)
PY
echo "== GENPLAN5_UTIN_1730_DONE"
