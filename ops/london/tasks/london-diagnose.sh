#!/usr/bin/env bash
# ТОЛЬКО ЧТЕНИЕ: что сломано на Лондоне — упавшие службы (почему), просроченные посты GENPLAN 5. Ничего не меняет.
set -uo pipefail
G=/opt/xojaobod-genplan-v5; DB=$G/data/genplan_v3_production.db
hide(){ sed -E 's/[0-9]{6,12}:[A-Za-z0-9_-]{30,}/<скрыто>/g; s/(token|key|secret|password)([=: ]+)[^ ]{8,}/\1\2<скрыто>/Ig' | cut -c1-220; }
echo "== службы"
for s in xojaobod-genplan-v3 xojaobodcity24bot goldwater-bot nginx postgresql nexus-london-agent papa-runner; do printf '  %-22s %s\n' "$s" "$(systemctl is-active $s 2>/dev/null)"; done
echo "== упавшие юниты"
F=$(systemctl list-units --state=failed --no-legend --plain 2>/dev/null | awk '{print $1}')
[[ -z "$F" ]] && echo "  нет"
for u in $F; do
  echo "--- $u"
  systemctl show "$u" -p Description -p Result -p ExecMainStatus -p ExecMainExitTimestamp -p FragmentPath -p TriggeredBy -p UnitFileState --no-pager | hide | sed 's/^/  /'
  systemctl show "$u" -p ExecStart --no-pager | sed -E 's/ ; (ignore_errors|start_time|stop_time|pid|code|status).*//' | hide | sed 's/^/  /'
  for t in $(systemctl show "$u" -p TriggeredBy --value); do echo "  таймер $t: $(systemctl is-enabled $t 2>/dev/null)/$(systemctl is-active $t 2>/dev/null), след. запуск: $(systemctl show $t -p NextElapseUSecRealtime --value)"; done
  echo "  журнал (последние 25 строк):"
  journalctl -u "$u" -n 25 --no-pager -o short-iso 2>/dev/null | hide | sed 's/^/    /'
done
echo "== GENPLAN 5: просроченные посты (pending, время прошло)"
python3 - "$DB" <<'PY'
import sqlite3, sys, datetime as dt
db = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True); db.row_factory = sqlite3.Row
cols = [r[1] for r in db.execute("PRAGMA table_info(scheduled_posts)")]
print("  колонки:", ", ".join(cols))
now = (dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) + dt.timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M:%S")   # в базе — местное время Ташкента
show = [c for c in ("id", "channel_id", "rubric", "source", "post_type", "scheduled_at", "status", "attempts", "error", "last_error") if c in cols]
rows = db.execute(f"SELECT {', '.join(show)} FROM scheduled_posts WHERE status='pending' AND scheduled_at < ? ORDER BY scheduled_at", (now,)).fetchall()
print(f"  сейчас (Ташкент): {now}; просрочено: {len(rows)}")
for r in rows[:20]:
    print("  ", {k: (str(r[k])[:120] if r[k] is not None else None) for k in show})
print("  статусы очереди:", dict(db.execute("SELECT status, COUNT(*) FROM scheduled_posts GROUP BY status").fetchall()))
PY
echo "== LONDON_DIAGNOSE_DONE"
