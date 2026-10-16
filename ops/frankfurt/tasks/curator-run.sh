#!/usr/bin/env bash
# 📡 Куратор — внеочередной запуск (обычно сам по таймеру 08:00 / 12:30 / 17:00).
set -Eeuo pipefail
run_curate(){
  systemctl start --no-block papa-razvedka@curate.service; sleep 2
  journalctl -u papa-razvedka@curate.service -f -n 0 -o cat & J=$!
  while systemctl is-active -q papa-razvedka@curate.service || [[ "$(systemctl show -p ActiveState --value papa-razvedka@curate.service)" == activating ]]; do sleep 3; done
  sleep 1; kill $J 2>/dev/null || true
  echo "результат: $(systemctl show -p Result --value papa-razvedka@curate.service)"
}
run_curate
echo "== CURATOR_RUN_DONE"
