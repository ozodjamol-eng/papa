#!/usr/bin/env bash
# 🤖 ИИ-ассистент: обновить код и перезапустить (тесты → перезапуск → статус). Токен не трогает.
set -euo pipefail
( cd /opt/papa/modules/reklama && python3 -I -m unittest discover -q -s tests 2>&1 | tail -1 )
install -m 0644 /opt/papa/ops/frankfurt/systemd/papa-assistant.service /etc/systemd/system/papa-assistant.service
systemctl daemon-reload; systemctl restart papa-assistant; sleep 5
echo "assistant: $(systemctl is-active papa-assistant)"
journalctl -u papa-assistant -n 3 --no-pager -o cat | sed -E 's/bot[0-9]+:[A-Za-z0-9_-]+/bot***/g'
echo "== ASSISTANT_RESTART_DONE"
