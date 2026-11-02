#!/usr/bin/env bash
# Франкфурт: обновить код бота VOLIDAM (тесты) и перезапустить службу. Токен не трогает.
set -euo pipefail
[[ -s /etc/papa-volidam/bot.env ]] || { echo "Нет токена — сначала владелец: papa-update volidam-bot-token"; exit 1; }
( cd /opt/papa/modules/volidam && python3 -m unittest discover -q -s tests 2>&1 | tail -1 )
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-volidam.service /etc/systemd/system/
systemctl daemon-reload; systemctl restart papa-volidam; sleep 5
echo "papa-volidam: $(systemctl is-active papa-volidam)"; journalctl -u papa-volidam -n 3 --no-pager -o cat
echo "== VOLIDAM_RESTARTED"
