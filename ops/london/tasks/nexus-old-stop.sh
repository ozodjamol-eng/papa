# Остановить и выключить старый NEXUS на Лондоне (службы и таймеры nexus-*, ozod-nexus-*).
# Обратимо: список сохраняется, вернуть — papa-update nexus-old-restore. Агент PAPA (nexus-london-agent) не трогается.
set -Euo pipefail
A=/var/backups/papa-archive; install -d -m 700 $A; TS=$(date +%Y%m%d_%H%M); L=$A/old-nexus-units-$TS.txt
mem(){ free -m | awk '/Mem/{m=$3} /Swap/{s=$3} END{print "память "m" МБ, swap "s" МБ"}'; }
echo "до:    $(mem)"
systemctl list-unit-files --no-legend --type=service --type=timer 2>/dev/null | awk '{print $1, $2}' \
  | grep -E '^(nexus-|ozod-nexus-)' | grep -v '^nexus-london-agent' > "$L" || true
n=0
while read -r unit state; do
  act=$(systemctl is-active "$unit" 2>/dev/null || true)
  echo "$unit $state $act" >> "$L.state"
  if [[ "$state" != static && "$state" != masked ]]; then systemctl disable --now "$unit" >/dev/null 2>&1 || true; else systemctl stop "$unit" >/dev/null 2>&1 || true; fi
  [[ "$act" == active ]] && n=$((n+1)) && echo "  остановлен: $unit"
done < "$L"
sleep 3
echo "остановлено работавших: $n из $(wc -l < "$L") юнитов (список: $L.state)"
echo "после: $(mem)"
echo "genplan=$(systemctl is-active xojaobod-genplan-v3) city24=$(systemctl is-active xojaobodcity24bot) goldwater=$(systemctl is-active goldwater-bot) postgres=$(systemctl is-active postgresql) agent=$(systemctl is-active nexus-london-agent)"
echo "== OLD_NEXUS_STOPPED (вернуть: papa-update nexus-old-restore)"
