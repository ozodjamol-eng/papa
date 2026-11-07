#!/usr/bin/env bash
# Франкфурт: сводка всех воронок (ничего не меняет): состояние + последние 3 события каждой работающей воронки с временем.
set -uo pipefail
for s in papa-voronka papa-voronka-shodiyona papa-voronka-goldwater papa-voronka-volidam; do
  st=$(systemctl is-active $s 2>/dev/null)
  echo "■ $s: $st"
  [[ $st == active ]] && journalctl -u $s --since "-30 min" -o short-iso --no-pager 2>/dev/null \
    | grep -E "ошибка|IG:|продление|ссылка|заявка" | tail -3 | sed -E 's/bot[0-9]+:[A-Za-z0-9_-]+/bot***/g' | cut -c1-160
done
echo "== VORONKI_STATUS_DONE"
