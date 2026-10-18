#!/usr/bin/env bash
# Обновить код бота ХОТИРА и перезапустить (тесты → перезапуск → статус).
set -euo pipefail
( cd /opt/papa/modules/xotira && python3 -m unittest discover -q -s tests 2>&1 | tail -1 )
install -m 644 /opt/papa/ops/frankfurt/systemd/papa-xotira.service /etc/systemd/system/; systemctl daemon-reload
systemctl restart papa-xotira; sleep 4
echo "papa-xotira: $(systemctl is-active papa-xotira)"; journalctl -u papa-xotira -n 5 --no-pager -o cat
echo "== XOTIRA_RESTART_DONE"
