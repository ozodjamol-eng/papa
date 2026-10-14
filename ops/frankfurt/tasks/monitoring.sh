# Обновить watchdog и резервное копирование из репозитория (+ Connect и Разведка), включить ежедневную Разведку.
set -Eeuo pipefail
L=/usr/local/lib/nexus-v2
for f in watchdog.sh backup.sh restore-test.sh rollback.sh; do cp -p "$L/$f" "$L/$f.prev" 2>/dev/null || true; done
install -m 755 /opt/papa/ops/frankfurt/watchdog.sh /opt/papa/ops/frankfurt/backup.sh /opt/papa/ops/frankfurt/restore-test.sh /opt/papa/ops/frankfurt/rollback.sh $L/
echo "watchdog: $(runuser -u nexus-private-control -- env -u HC_PING_URL $L/watchdog.sh 2>&1 | tail -1)"
systemctl start nexus-v2-backup.service && journalctl -u nexus-v2-backup.service -n 4 -o cat --no-pager | grep BACKUP_OK || echo "backup: проверьте журнал"
systemctl enable --now papa-razvedka-daily.timer >/dev/null 2>&1
echo "разведка: следующий запуск $(systemctl show -p NextElapseUSecRealtime --value papa-razvedka-daily.timer)"
echo "== MONITORING_DONE"
