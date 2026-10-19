#!/usr/bin/env bash
# 🩺 Аудит: был ли сегодня, чем закончился, ушёл ли отчёт (только чтение).
set -uo pipefail
for t in papa-audit-full papa-audit-quick papa-audit-watch; do
  printf '%-18s %s · следующий: %s\n' "$t" "$(systemctl is-active $t.timer)" "$(systemctl show -p NextElapseUSecRealtime --value $t.timer)"
done
for u in full quick; do
  echo "== papa-audit@$u: последний запуск $(systemctl show -p ExecMainStartTimestamp --value papa-audit@$u.service) · результат $(systemctl show -p Result --value papa-audit@$u.service)"
  journalctl -u papa-audit@$u.service --since "-30h" --no-pager -o short-iso | grep -vE "systemd\[1\]: (Starting|Started|Finished|Deactivated)" | sed -E 's/bot[0-9]+:[A-Za-z0-9_-]+/bot***/g' | tail -25
done
echo "== AUDIT_STATUS_DONE"
