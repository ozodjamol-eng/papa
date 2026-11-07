#!/usr/bin/env bash
# Франкфурт: сводка всех воронок одной таблицей (ничего не меняет). Справа — последнее событие за 15 мин (пусто = ошибок нет).
set -uo pipefail
for s in papa-voronka papa-voronka-shodiyona papa-voronka-goldwater papa-voronka-volidam; do
  printf '%-26s %-9s %s\n' "$s" "$(systemctl is-active $s 2>/dev/null)" "$(journalctl -u $s --since "-15 min" -o cat --no-pager 2>/dev/null | grep -E "ошибка|IG:" | tail -1 | cut -c1-110)"
done
echo "== VORONKI_STATUS_DONE"
