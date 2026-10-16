#!/usr/bin/env bash
# Только чтение: почему пульты GENPLAN (Давра, PaparazziUZ, Хўжаобод) отвечают медленно.
set -uo pipefail
for S in papa-genplan papa-fabrika; do
  CG=/sys/fs/cgroup/system.slice/$S.service
  [[ -d $CG ]] || continue
  echo "== $S"
  grep -E 'usage_usec|nr_periods|nr_throttled|throttled_usec' $CG/cpu.stat
  echo "mem.current=$(( $(cat $CG/memory.current)/1048576 ))MB high=$(cat $CG/memory.high) max=$(cat $CG/memory.max)"
  cat $CG/memory.events | tr '\n' ' '; echo
  echo "cpu.pressure: $(head -1 $CG/cpu.pressure)"; echo "mem.pressure: $(head -1 $CG/memory.pressure)"
done
echo "== сервер"; uptime; free -m | head -3
echo "== Telegram API (connect / tls / total, сек)"
for i in 1 2 3 4 5; do curl -s -o /dev/null -w "%{time_connect} %{time_appconnect} %{time_total}\n" https://api.telegram.org/; done
echo "== журнал papa-genplan за 2 ч (без повторов)"
journalctl -u papa-genplan --since "-120min" --no-pager -o short-iso | cut -c1-220 | tail -50
echo "== GENPLAN_SPEED_DONE"
