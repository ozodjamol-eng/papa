#!/usr/bin/env bash
# Воронка Instagram → Telegram: обновить код и перезапустить (тесты → перезапуск → журнал). Токены не трогает.
set -euo pipefail
( cd /opt/papa/modules/voronka && python3 -I -m unittest discover -q -s tests 2>&1 | tail -1 )
systemctl restart papa-voronka; sleep 8
echo "voronka: $(systemctl is-active papa-voronka)"
journalctl -u papa-voronka -n 8 --no-pager -o cat | sed -E 's/bot[0-9]+:[A-Za-z0-9_-]+/bot***/g'
echo "== VORONKA_RESTART_DONE"
