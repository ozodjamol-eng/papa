# Вернуть старый NEXUS в состояние до остановки (по последнему сохранённому списку).
set -Euo pipefail
S=$(ls -1t /var/backups/papa-archive/old-nexus-units-*.txt.state 2>/dev/null | head -1)
[[ -n "$S" ]] || { echo NO_SAVED_STATE; exit 1; }
while read -r unit state act; do
  [[ "$state" == enabled ]] && systemctl enable "$unit" >/dev/null 2>&1 || true
  [[ "$act" == active ]] && systemctl start "$unit" && echo "  запущен: $unit"
done < "$S"
echo "== OLD_NEXUS_RESTORED ($S)"
