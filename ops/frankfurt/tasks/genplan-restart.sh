#!/usr/bin/env bash
# Обновление кода GENPLAN PAPA без настройки чатов: тесты → перезапуск → статус. Режим (shadow/live) не меняется.
set -euo pipefail
( cd /opt/papa/modules/genplan && PAPA_GENPLAN_STATE=$(mktemp -d) /opt/papa-venv/razvedka/bin/python -m unittest discover -q -s tests 2>&1 | tail -1 )
systemctl restart papa-genplan; systemctl is-enabled -q papa-fabrika 2>/dev/null && systemctl restart papa-fabrika; sleep 5
systemctl is-active papa-genplan
journalctl -u papa-genplan -n 5 --no-pager -o cat
echo "== GENPLAN_RESTART_DONE"
